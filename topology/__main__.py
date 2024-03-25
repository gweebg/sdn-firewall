#!/usr/bin/env python
""" Mininet Topology for TechSecure Network """

""" Mininet required libraries """
from mininet.topo import Topo # type: ignore
from mininet.net import Mininet # type: ignore
from mininet.node import OVSKernelSwitch # type: ignore
from mininet.cli import CLI # type: ignore
from mininet.log import setLogLevel # type: ignore

""" Default libraries """
import argparse as argument_parsing


""" User defined libraries """
from config.toml import devices
from p4.mininet import P4Switch, P4Host

cls_dict = {"P4Host": P4Host, "P4Switch": P4Switch, "OVSKernelSwitch": OVSKernelSwitch}


class TechSecure(Topo):
    def __init__(self, nodes, links, **opts):
        if not "switch" in nodes:
            nodes["switch"] = []
        if not "host" in nodes:
            nodes["host"] = []
        if not "router" in nodes:
            nodes["router"] = []
        hosts_ = {}
        switches_ = {}
        routers_ = {}
        Topo.__init__(self,**opts)
        
        # Add hosts
        for host_ in nodes["host"]:
            hosts_[host_.name] = self.addHost(host_.name, cls=cls_dict[host_.cls], ip=host_.ip, mac=host_.mac)

        # Add switches
        for switch_ in nodes["switch"]:
            switches_[switch_.name] = self.addSwitch(switch_.name, cls=cls_dict[switch_.cls])
            
        # Add routers
        for router_ in nodes["router"]:
            ips = {}
            for i in range(len(router_.ip_ports)):
                ips["ip"+str(i+1)] = router_.ip_ports[i]
            routers_[router_.name] = self.addSwitch(router_.name, cls=cls_dict[router_.cls], sw_path=router_.bvmodel, json_path=router_.json_path, thrift_port=router_.thrift_port, **ips)

        # Add links
        tmp_dict = {}
        tmp_dict.update(hosts_)
        tmp_dict.update(switches_)
        tmp_dict.update(routers_)
        for link in links:
            if link.device1.startswith("r") and link.device2.startswith("s"):
                self.addLink(tmp_dict[link.device1], tmp_dict[link.device2], port1=link.port1, port2=link.port2, addr1=link.mac1, param1={"ip":link.ip1})
            elif link.device1.startswith("r") and link.device2.startswith("r"):
                self.addLink(tmp_dict[link.device1], tmp_dict[link.device2], port1=link.port1, port2=link.port2, addr1=link.mac1, addr2=link.mac2)
            else:
                self.addLink(tmp_dict[link.device1], tmp_dict[link.device2], port1=link.port1, port2=link.port2, addr1=link.mac1, addr2=link.mac2)


def main(arguments):
    try:
        (devices_, links) = devices(arguments.config_file)
    except Exception as e:
        print(f"Error: {e}")
        return
    topology = TechSecure(devices_, links)

    net = Mininet(topo = topology, controller= None)
    net.start()

    for host_ in devices_["host"]:
        node = net.get(host_.name)
        node.setARP(host_.switch_ip, host_.switch_mac)
        node.setDefaultRoute("dev eth0 via " + host_.switch_ip)

    CLI(net)
    net.stop()


if __name__ == "__main__":
    parser = argument_parsing.ArgumentParser(description="TechSecure Network Mininet")
    parser.add_argument("config_file",nargs='?' , default="config/network.toml", help="Path to the network configuration file", type=str)

    args = parser.parse_args()
    setLogLevel( 'info' )
    main(args)
