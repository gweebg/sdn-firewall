#!/usr/bin/env python
"""
Mininet Topology for TechSecure Network
"""

# Default libraries
import argparse as argument_parsing

# Mininet required libraries
from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import OVSKernelSwitch
from mininet.topo import Topo
from mininet.clean import Cleanup

# User defined libraries
from config.loader import getState, State, Host, Router, Switch, PortL3, FirewallRule
from CustomIP.IP import IP
from p4.mininet import P4Host, P4Switch, P4RuntimeSwitch
from autotest.test import testFirewall, testICMP

class TechSecure(Topo):
    CLS_DICT = {
        "P4Host": P4Host,
        "P4Switch": P4Switch,
        "P4RuntimeSwitch": P4RuntimeSwitch,
        "OVSKernelSwitch": OVSKernelSwitch,
    }

    def __init__(self, state: State, **opts):

        self.__state = state
        self.__hosts = {}
        self.__switches = {}
        self.__routers = {}
        Topo.__init__(self, **opts)

        self.__setup_hosts()
        self.__setup_switches()
        self.__setup_routers()
        self.__setup_links()

    def __setup_hosts(self):
        hosts: list[Host] = self.__state.hosts.values()
        for host in hosts:
            host_mac = host.ports[1].mac
            print(host.ip.GetIpWithMask())
            self.__hosts[host.nodeName] = self.addHost(
                host.nodeName, cls=self.CLS_DICT["P4Host"], ip=host.ip.GetIpWithMask(), mac=host_mac
            )

    def __setup_switches(self):
        switches: list[Switch] = self.__state.switches.values()
        for switch in switches:
            self.__switches[switch.nodeName] = self.addSwitch(
                switch.nodeName, cls=self.CLS_DICT["OVSKernelSwitch"]
            )

    def __setup_routers(self):
        routers: list[Router] = self.__state.routers.values()
        for router_ in routers:
            ips = {}
            ips["ip1"] = router_.ip.GetIpWithMask()
            self.__routers[router_.nodeName] = self.addSwitch(
                router_.nodeName,
                cls=self.CLS_DICT["P4RuntimeSwitch"],
                sw_path=router_.bvmodel,
                json_path=None,
                thrift_port=router_.thrift_port,
                grpc_port=router_.grpc_port,
                cpu_port=router_.cpu_port,
                device_id=router_.macDeviceId,
                **ips,
            )

    def __setup_links(self):
        # Add links
        tmp_dict = {}
        tmp_dict.update(self.__hosts)
        tmp_dict.update(self.__switches)
        tmp_dict.update(self.__routers)
        for devicesNames, link in self.__state.linksL2.items():
            deviceName1, deviceName2 = devicesNames
            port1 = link.ports[deviceName1]
            port2 = link.ports[deviceName2]
            param1 = {}
            param2 = {}
            if isinstance(port1, PortL3):
                param1["ip"] = port1.ip.GetIpWithMask()
            if isinstance(port2, PortL3):
                param2["ip"] = port2.ip.GetIpWithMask()
            self.addLink(
                tmp_dict[deviceName1],
                tmp_dict[deviceName2],
                port1=port1.portId,
                port2=port2.portId,
                addr1=port1.mac,
                addr2=port2.mac,
                param1=param1,
                param2=param2,
            )

def injectSrcMacRules(router: Router) -> str:
    res = "table_set_default src_mac drop\n"
    for p in router.ports.values():
        res += f"table_add src_mac rewrite_src_mac {p.portId} => {p.mac}\n"
    return res

def injectDstMacRules(router: Router) -> str:
    res = "table_set_default dst_mac drop\n"
    generatedIps = set()
    localPortToRemoteMac: dict[int, str] = {}
    for l in router.linksL3.values():
        remotePort: PortL3 = l.getOtherPortFromLocalName(router.nodeName)
        res += f"table_add dst_mac rewrite_dst_mac {remotePort.ip.GetIp()} => {remotePort.mac}\n"
        generatedIps.add(remotePort.ip.GetIp())
        localPortToRemoteMac[l.ports[router.nodeName].portId] = remotePort.mac
    for l in router.forwardingLinks.values():
        remotePort: PortL3 = l.getOtherPortFromLocalName(router.nodeName)
        remIP = remotePort.ip.GetIp()
        if not remIP in generatedIps:
            res += f"table_add dst_mac rewrite_dst_mac {remIP} => {localPortToRemoteMac[l.ports[router.nodeName].portId]}\n"
            generatedIps.add(remIP)
    return res

def genSingleRuleForForwarding(strIp: str, mask: int, localPortID: int):
    return f"table_add ipv4_lpm ipv4_fwd {strIp}/{mask} => {strIp} {localPortID}\n"

def injectIPV4FwdRules(router: Router, state: State, stage: int) -> str:
    res = "table_set_default ipv4_lpm drop\n"
    for netID, network in state.networks.items():
        if netID == router.network:
            links = [(nl3Name, nl3.linksL3[router.nodeName]) for nl3Name, nl3 in network.nodesl3.items() if nl3Name != router.nodeName]
            for remoteName, l3 in links:
                remotePort: PortL3 = l3.ports[remoteName]
                res += genSingleRuleForForwarding(remotePort.ip.GetIp(), 32, l3.ports[router.nodeName].portId)
        else:
            forwardingLink = router.forwardingLinks[netID]
            remoteIP = forwardingLink.getOtherPortFromLocalName(router.nodeName).ip.GetIp()
            mask = 32 if network.NATted and stage>1 else 24
            res += genSingleRuleForForwarding(remoteIP, mask, forwardingLink.ports[router.nodeName].portId)
    return res

def injectFwallRules(router: Router, stage: int) -> str:
    res = "table_set_default fwall drop\n"
    for rule in router.rules:
        if stage > 1:
            res += f"table_add fwall_rules RulesSuccess {rule.srcIp.GetTernaryFormat()} {rule.dstIp.GetTernaryFormat()} {rule.protocol} {rule.Port} => {rule.LocalPort} 1\n"
            res += f"table_add privateToPublicPort setPublicPort {rule.LocalPort} => {rule.Port}\n"
        else:
            res += f"table_add fwall_rules RulesSuccess {rule.srcIp.GetTernaryFormat()} {rule.dstIp.GetTernaryFormat()} {rule.protocol} {rule.Port} 1 1\n"
    return res

def injectPacketDirectionRules(router:Router) -> str:
    wildcardIP = IP(0, 0, mask=0)
    wildcardIPStr = wildcardIP.GetNetworkTernaryFormat()
    routerIPStr = router.ip.GetNetworkTernaryFormat()
    res = f"table_add MyIngress.checkPacketDirection setPacketDirection {routerIPStr} {wildcardIPStr} => 1 1\n"
    res += f"table_add MyIngress.checkPacketDirection setPacketDirection  {wildcardIPStr} {routerIPStr} => 2 1\n"
    res += f"table_add MyIngress.checkPacketDirection setPacketDirection  {wildcardIPStr} {wildcardIPStr} => 3 1\n"
    return res

def injectNatRules(router: Router, state: State) -> str:
    publicIp = router.ip.GetIp()
    serverId = 0
    res = f""
    hosts = state.networks[router.network].hosts.values()
    maxServerID = sum([h.weight for h in hosts]) - 1
    for host in state.networks[router.network].hosts.values():
        w = host.weight
        hIP = host.ip.GetIp()
        while w > 0:
            nextServerId = serverId+1
            if maxServerID <= serverId or maxServerID == 1:
                nextServerId = 0
            res += f"table_add MyEgress.ServerLookup setCurrentServer {serverId} => {hIP} {publicIp} {nextServerId}\n"
            serverId = nextServerId
            w-=1
    return res

def generateCommandsForRouterEtapa1(router: Router, state: State) -> str:
    res = "reset_state\n"
    res += injectIPV4FwdRules(router, state, 1) + "\n"
    res += injectSrcMacRules(router) + "\n"
    res += injectDstMacRules(router) + "\n"
    res += injectPacketDirectionRules(router) + "\n"
    res += injectFwallRules(router, 1)
    return res
        

def generateCommandsForRouterEtapa2(router: Router, state: State) -> str:
    natted = state.networks[router.network].NATted
    res = "reset_state\n"
    res += f"table_set_default MyIngress.EnabledFuncsTable setEnabledFuncs 1 {1 if natted else 0}\n"
    res += injectIPV4FwdRules(router, state, 2) + "\n"
    res += injectSrcMacRules(router) + "\n"
    res += injectDstMacRules(router) + "\n"
    res += f"table_add self_icmp reply_to_icmp {router.ip.GetIp()} 1\n"
    res += injectPacketDirectionRules(router) + "\n"
    if natted:
        res += injectNatRules(router, state) + "\n"
    res += injectFwallRules(router, 2)
    return res

def writeCommands(r: Router, strCommands: str):
    with open(f"config/{r.nodeName}.txt", "w") as f:
        f.write(strCommands)

def init_topology(net: Mininet, state: State, stage: int) -> None:

    print("=" * 25 + " Topology Initialization " + "=" * 25)

    for node in state.nodes.values():
        mn_node = net.get(node.nodeName)
        match node.macDeviceType:
            case 1: # Router
                r: Router = node
                writeCommands(r, r.getTableEntriesInText())
                # mn_node.cmd(f"simple_switch_CLI --thrift-port {mn_node.thrift_port} < src/p4/commands/{mn_node.name}.txt")
                mn_node.cmd(f"simple_switch_CLI --thrift-port {mn_node.thrift_port} < config/{mn_node.name}.txt")
                print(f"{mn_node.name}:injected autogenerated config/{mn_node.name}.txt into router '{mn_node.name}'")
            case 2: # Host
                h: Host = node
                for otherNodeName, linkl3 in h.linksL3.items():
                    otherPort: PortL3 = linkl3.getOtherPortFromLocalName(h.nodeName)
                    mn_node.setARP(otherPort.ip.GetIp(), otherPort.mac)
                    log = f"{h.nodeName}:set ARP for {otherPort.ip.GetIp()} to {otherPort.mac}"
                    if state.networks[h.network].gateway == otherNodeName:
                        mn_node.setDefaultRoute("dev eth0 via " + otherPort.ip.GetIp())
                        log += f"    AND    set dev eth0 via {otherPort.ip.GetIp()}"
                    print(log)
            case 3: # Switch
                mn_node.cmd(f"ovs-ofctl add-flow {mn_node.name} action=normal")
                print(f"{mn_node.name}: ovs-ofctl add-flow {mn_node.name} action=normal")
    print("=" * 75)

                
def main(arguments):
    stage: int = arguments.stage
    try:
        state = getState(arguments.config, stage)
    except Exception as e:
        print(f"Error: {e}")
        return

    Cleanup.cleanup() 
    topology = TechSecure(state)

    net = Mininet(topo=topology, controller=None)
    net.start()
    init_topology(net, state, stage)

    test: bool = arguments.test
    if test:
        testFirewall(net, state)
        if stage > 1:
            testICMP(net, state)

    CLI(net)
    net.stop()


if __name__ == "__main__":
    ## Clean old mn files
    import os
    os.system("mn -c")
    ## clear screen
    os.system("clear")
    ## Parse arguments
    parser = argument_parsing.ArgumentParser(description="TechSecure Network Mininet")
    parser.add_argument(
        "-c",
        "--config",
        default="config/network.yml",
        help="path to the network configuration file",
        type=str,
    )
    parser.add_argument(
        "-s",
        "--stage",
        default=1,
        help="stage of the project to run",
        type=int,
    )
    parser.add_argument(
        "-t",
        "--test",
        help="test everything on start",
        action='store_true'
    )
    parser.add_argument(
        "-ll",
        "--log-level",
        choices=["info", "debug", "error", "critical", "warning"],
        default="info",
        help="log level",
        type=str,
    )
    
    args = parser.parse_args()
    setLogLevel(args.log_level)
    SystemExit(main(args))
