#!/usr/bin/env python

from mininet.net import Mininet
from mininet.node import Host, Node
from mininet.node import OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info


def topology():
    net = Mininet(topo=None, build=False, ipBase="10.0.0.0/8")

    info("*** Adding controller\n")

    info("*** Add switches\n")
    s4 = net.addSwitch("s4", cls=OVSKernelSwitch)
    s5 = net.addSwitch("s5", cls=OVSKernelSwitch)
    s6 = net.addSwitch("s6", cls=OVSKernelSwitch)

    info("*** Add routers\n")
    r1 = net.addHost("r1", cls=Node, ip="0.0.0.0")
    r1.cmd("sysctl -w net.ipv4.ip_forward=1")
    r2 = net.addHost("r2", cls=Node, ip="0.0.0.0")
    r2.cmd("sysctl -w net.ipv4.ip_forward=1")
    r3 = net.addHost("r3", cls=Node, ip="0.0.0.0")
    r3.cmd("sysctl -w net.ipv4.ip_forward=1")

    info("*** Add hosts\n")
    h1 = net.addHost("h1", cls=Host, ip="10.0.0.1", defaultRoute=None)
    h2 = net.addHost("h2", cls=Host, ip="10.0.0.2", defaultRoute=None)
    h3 = net.addHost("h3", cls=Host, ip="10.0.0.3", defaultRoute=None)
    h4 = net.addHost("h4", cls=Host, ip="10.0.0.4", defaultRoute=None)
    h5 = net.addHost("h5", cls=Host, ip="10.0.0.5", defaultRoute=None)
    h6 = net.addHost("h6", cls=Host, ip="10.0.0.6", defaultRoute=None)
    h7 = net.addHost("h7", cls=Host, ip="10.0.0.7", defaultRoute=None)
    h8 = net.addHost("h8", cls=Host, ip="10.0.0.8", defaultRoute=None)
    h9 = net.addHost("h9", cls=Host, ip="10.0.0.9", defaultRoute=None)

    info("*** Add links\n")
    net.addLink(h1, s4)
    net.addLink(h2, s4)
    net.addLink(h3, s4)
    net.addLink(s4, r1)
    net.addLink(r1, r2)
    net.addLink(r2, r3)
    net.addLink(r3, r1)
    net.addLink(r2, s5)
    net.addLink(s5, h4)
    net.addLink(s5, h5)
    net.addLink(s5, h6)
    net.addLink(r3, s6)
    net.addLink(s6, h7)
    net.addLink(s6, h8)
    net.addLink(s6, h9)

    info("*** Starting network\n")
    net.build()

    info("*** Starting controllers\n")
    for controller in net.controllers:
        controller.start()

    info("*** Starting switches\n")
    net.get("s4").start([])
    net.get("s5").start([])
    net.get("s6").start([])

    info("*** Post configure switches and hosts\n")

    CLI(net)
    net.stop()


if __name__ == "__main__":
    setLogLevel("info")
    SystemExit(topology())
