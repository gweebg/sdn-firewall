#!/usr/bin/env python
""" Mininet Topology for TechSecure Network """

""" Mininet required libraries """
from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import Host, Node
from mininet.node import OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info

""" Default libraries """
import argparse as argument_parsing
from time import sleep


""" User defined libraries """
from config.toml import devices
from p4.mininet import P4Switch, P4Host




def get_class_of_cls(cls):
    match cls:
        case "P4Host":
            return P4Host
        case "P4Switch":
            return P4Switch
        case "OVSKernelSwitch":
            return OVSKernelSwitch
        case _:
            return None


class TechSecure(Topo):
    def __init__(self, nodes, links, **opts):
        hosts_ = {}
        switches_ = {}
        routers_ = {}
        Topo.__init__(self,**opts)
        
        # Add hosts
        info("*** Add hosts\n")
        for host_ in nodes["host"]:
            print("Adding host ", host_.name)
            hosts_[host_.name] = self.addHost(host_.name, cls=get_class_of_cls(host_.cls), ip=host_.ip, mac=host_.mac)

        # Add switches
        info("*** Add switches\n")
        for switch_ in nodes["switch"]:
            print("Adding switch ", switch_.name)
            switches_[switch_.name] = self.addSwitch(switch_.name, cls=get_class_of_cls(switch_.cls))
        # Add routers
        info("*** Add routers\n")
        for router_ in nodes["router"]:
            print("Adding router ", router_.name)
            routers_[router_.name] = self.addSwitch(router_.name, cls=get_class_of_cls(router_.cls), sw_path=router_.bvmodel, json_path=router_.json_path, thrift_port=router_.thrift_port)


        # Add links
        info("*** Add links\n")
        tmp_dict = {}
        tmp_dict.update(hosts_)
        tmp_dict.update(switches_)
        tmp_dict.update(routers_)
        for link in links:
            print("Adding link between ", link.device1, " and ", link.device2)
            self.addLink(tmp_dict[link.device1], tmp_dict[link.device2], port1=link.port1, port2=link.port2, addr1=link.mac1, addr2=link.mac2)



def main(arguments):
    (devices_, links) = devices(arguments.config_file)
    topology = TechSecure(devices_, links)

    net = Mininet(topo = topology, controller= None)
    net.start()

    for host_ in devices_["host"]:
        node = net.get(host_.name)

        if (int(host_.name.replace("h","")) <= 3):
            router_name = "r1"
        elif (int(host_.name.replace("h","")) <= 6):
            router_name = "r2"
        else:
            router_name = "r3"

        router = net.get(router_name)
        node.setARP(router.defaultIntf().IP(), router.defaultIntf().MAC())
        node.setDefaultRoute("dev eth0 via " + router.defaultIntf().IP())
        node.describe()

    CLI(net)
    net.stop()


if __name__ == "__main__":
    parser = argument_parsing.ArgumentParser(description="TechSecure Network Mininet")
    parser.add_argument("config_file", help="Path to the network configuration file", type=str)

    args = parser.parse_args()


    main(args)
