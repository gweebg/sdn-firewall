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

# User defined libraries
from config.loader import getState, State, Host, Router, Switch, PortL3, Rule
from p4.mininet import P4Host, P4Switch
from autotest.test import testFirewall, testICMP

class TechSecure(Topo):
    CLS_DICT = {
        "P4Host": P4Host,
        "P4Switch": P4Switch,
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
            self.__hosts[host.nodeName] = self.addHost(
                host.nodeName, cls=self.CLS_DICT["P4Host"], ip=host.ip.getCompleteIpWithMask(), mac=host_mac
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
            ips["ip1"] = router_.ip.getCompleteIpWithMask()
            self.__routers[router_.nodeName] = self.addSwitch(
                router_.nodeName,
                cls=self.CLS_DICT["P4Switch"],
                sw_path=router_.bvmodel,
                json_path=router_.json_path,
                thrift_port=router_.thrift_port,
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
                param1["ip"] = port1.ip.getCompleteIpWithMask()
            if isinstance(port2, PortL3):
                param2["ip"] = port2.ip.getCompleteIpWithMask()
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
    for l in router.linksL3.values():
        remotePort: PortL3 = l.getOtherPortFromLocalName(router.nodeName)
        res += f"table_add dst_mac rewrite_dst_mac {remotePort.ip.getCompleteIp()} => {remotePort.mac}\n"
    return res

def injectIPV4FwdRules(router: Router) -> str:
    res = "table_set_default ipv4_lpm drop\n"
    for l in router.linksL3.values():
        remotePort: PortL3 = l.getOtherPortFromLocalName(router.nodeName)
        mask = 24 if remotePort.ip.host == 1 else 32
        strIp = remotePort.ip.getCompleteIp()
        res += f"table_add ipv4_lpm ipv4_fwd {strIp}/{mask} => {strIp} {l.ports[router.nodeName].portId}\n"
    return res

def injectFwallRules(router: Router) -> str:
    res = "table_set_default fwall drop\n"
    for rule in router.rules:
        res += f"table_add fwall_rules RulesSuccess {rule.srcIp.GetCompleteTernaryFormat()} {rule.dstIp.GetCompleteTernaryFormat()} {rule.protocol} {rule.Port} 1 1\n"
    return res

def generateCommandsForRouter(router: Router) -> str:
    res = "reset_state\n"
    res += injectIPV4FwdRules(router) + "\n"
    res += injectSrcMacRules(router) + "\n"
    res += injectDstMacRules(router) + "\n"
    res += f"table_add self_icmp reply_to_icmp {router.ip.getCompleteIp()} 1\n"
    res += "table_set_default check_controlled_networks set_return_allowed\n"
    res += f"table_add check_controlled_networks set_needs_fw {router.ip.getNetworkTernaryFormat()} 1 1\n\n"
    res += injectFwallRules(router)
    return res
        

def init_topology(net: Mininet, state: State) -> None:

    print("=" * 25 + " Topology Initialization " + "=" * 25)

    for node in state.nodes.values():
        mn_node = net.get(node.nodeName)
        match node.macDeviceType:
            case 1: # Router
                r: Router = node
                s = generateCommandsForRouter(r)
                with open(f"config/{r.nodeName}.txt", "w") as f:
                    f.write(s)
                # mn_node.cmd(f"simple_switch_CLI --thrift-port {mn_node.thrift_port} < src/p4/commands/{mn_node.name}.txt")
                mn_node.cmd(f"simple_switch_CLI --thrift-port {mn_node.thrift_port} < config/{mn_node.name}.txt")
                print(f"{mn_node.name}:injected autogenerated config/{mn_node.name}.txt into router '{mn_node.name}'")
            case 2: # Host
                h: Host = node
                for otherNodeName, linkl3 in h.linksL3.items():
                    otherPort: PortL3 = linkl3.getOtherPortFromLocalName(h.nodeName)
                    mn_node.setARP(otherPort.ip.getCompleteIp(), otherPort.mac)
                    log = f"{h.nodeName}:set ARP for {otherPort.ip.getCompleteIp()} to {otherPort.mac}"
                    if state.networks[h.network].gateway == otherNodeName:
                        mn_node.setDefaultRoute("dev eth0 via " + otherPort.ip.getCompleteIp())
                        log += f"    AND    set dev eth0 via {otherPort.ip.getCompleteIp()}"
                    print(log)
            case 3: # Switch
                mn_node.cmd(f"ovs-ofctl add-flow {mn_node.name} action=normal")
                print(f"{mn_node.name}: ovs-ofctl add-flow {mn_node.name} action=normal")
    print("=" * 75)


            
                
def main(arguments):
    try:
        s = getState(arguments.config)

    except Exception as e:
        print(f"Error: {e}")
        return

    topology = TechSecure(s)

    net = Mininet(topo=topology, controller=None)
    net.start()

    init_topology(net, s)
    testFirewall(net, s)
    testICMP(net, s)

    CLI(net)
    net.stop()


if __name__ == "__main__":
    parser = argument_parsing.ArgumentParser(description="TechSecure Network Mininet")
    parser.add_argument(
        "-c",
        "--config",
        default="config/network.toml",
        help="path to the network configuration file",
        type=str,
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
