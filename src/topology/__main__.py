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
from config.toml import devices
from p4.mininet import P4Host, P4Switch


class TechSecure(Topo):
    CLS_DICT = {
        "P4Host": P4Host,
        "P4Switch": P4Switch,
        "OVSKernelSwitch": OVSKernelSwitch,
    }

    def __init__(self, nodes, links, **opts):
        if "switch" not in nodes:
            nodes["switch"] = []
        if "host" not in nodes:
            nodes["host"] = []
        if "router" not in nodes:
            nodes["router"] = []

        self.__nodes = nodes
        self.__links = links
        self.__hosts = {}
        self.__switches = {}
        self.__routers = {}

        Topo.__init__(self, **opts)

        self.__setup_hosts()
        self.__setup_switches()
        self.__setup_routers()
        self.__setup_links()

    def __setup_hosts(self):
        for host in self.__nodes["host"]:
            self.__hosts[host.name] = self.addHost(
                host.name, cls=self.CLS_DICT[host.cls], ip=host.ip, mac=host.mac
            )

    def __setup_switches(self):
        for switch in self.__nodes["switch"]:
            self.__switches[switch.name] = self.addSwitch(
                switch.name, cls=self.CLS_DICT[switch.cls]
            )

    def __setup_routers(self):
        for router_ in self.__nodes["router"]:
            ips = {}
            for i in range(len(router_.ip_ports)):
                ips["ip" + str(i + 1)] = router_.ip_ports[i]
                self.__routers[router_.name] = self.addSwitch(
                    router_.name,
                    cls=self.CLS_DICT[router_.cls],
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
        for link in self.__links:
            if link.device1.startswith("r") and link.device2.startswith("s"):
                self.addLink(
                    tmp_dict[link.device1],
                    tmp_dict[link.device2],
                    port1=link.port1,
                    port2=link.port2,
                    addr1=link.mac1,
                    param1={"ip": link.ip1},
                )
            elif link.device1.startswith("r") and link.device2.startswith("r"):
                self.addLink(
                    tmp_dict[link.device1],
                    tmp_dict[link.device2],
                    port1=link.port1,
                    port2=link.port2,
                    addr1=link.mac1,
                    addr2=link.mac2,
                )
            else:
                self.addLink(
                    tmp_dict[link.device1],
                    tmp_dict[link.device2],
                    port1=link.port1,
                    port2=link.port2,
                    addr1=link.mac1,
                    addr2=link.mac2,
                )


def init_topology(net: Mininet, devs: dict) -> None:

    print("=" * 25 + " Topology Initialization " + "=" * 25)

    # Initialize ARP and default routes
    for host in devs["host"]:
        node = net.get(host.name)
        node.setARP(host.switch_ip, host.switch_mac)
        node.setDefaultRoute("dev eth0 via " + host.switch_ip)

    # Define OpenVSwitch rules for each switch
    for switch in devs["switch"]:
        sw = net.get(switch.name)
        sw.cmd(f"ovs-ofctl add-flow {sw.name} action=normal")
        print(f"ovs-ofctl add-flow {sw.name} action=normal")

    # Inject commands into P4 routers
    for router in devs["router"]:
        r = net.get(router.name)
        r.cmd(f"simple_switch_CLI --thrift-port {router.thrift_port} < src/p4/commands/{router.name}.txt")
        print(f"injected {router.name}.txt into router '{router.name}'")

    print("=" * 75)


def main(arguments):
    try:
        (devices_, links) = devices(arguments.config)

    except Exception as e:
        print(f"Error: {e}")
        return

    topology = TechSecure(devices_, links)

    net = Mininet(topo=topology, controller=None)
    net.start()

    init_topology(net, devices_)

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
