
from threading import Thread
from config.loader import State, Rule
from mininet.net import Mininet

def serverCMD(dstNode, command):
    result = dstNode.cmd(command)
    print(result)
def testRule(mnet: Mininet, s:State, r: Rule):
    udpFlag = "-u" if r.protocol == "0x11" else ""
    dstHosts = []
    srcHosts = []
    print(f"\n====================Testing rule from: {r.srcIp} to: {r.dstIp} with proto: {r.protocol} on port: {r.Port}====================") 
    if r.dstIp.host == 0 and r.dstIp.mask == 24:
        dstHosts = [h for _,h in s.networks[r.dstIp.networkId].hosts.items()]
    else:
        dstHosts = [s.getHostByIP(r.dstIp)]
    if r.srcIp.host == 0 and r.srcIp.mask == 24:
        srcHosts = [h for _,h in s.networks[r.srcIp.networkId].hosts.items()] 
    else:
        srcHosts = [s.getHostByIP(r.srcIp)]
    for h in dstHosts:
        dstNode = mnet.get(h.nodeName)
        serverCommand = f"iperf -s -p {r.Port} {udpFlag} -P {len(srcHosts)} --connect-only"
        clientCommand = f"nc -z {h.ip.getCompleteIp()} {r.Port} {udpFlag} -v"
        clientWrongCommand = f"nc {h.ip.getCompleteIp()} {r.Port+1} {udpFlag} -w 2 -v"
        t = Thread(target=serverCMD, args=(dstNode, serverCommand))
        t.start()
        print(f"{h.nodeName} running iperf server: {serverCommand}")
        for sH in srcHosts:
            srcNode = mnet.get(sH.nodeName)
            print(f"Testing {sH.nodeName} <-> {h.nodeName}:")
            print(f"    {sH.nodeName} running wrong command: {clientWrongCommand} -> ", end="")
            wrongResult = srcNode.cmd(clientWrongCommand)
            print("connection timed out correctly" if "timed out" in wrongResult else "WARNING: connection not timed out wrongly(possible problems in firewall rules)")
            print(f"    {sH.nodeName} running correct command: {clientCommand}")
            result = srcNode.cmd(clientCommand)
        t.join()
        print(f"===================={h.nodeName} iperf server stopped====================")

def testFirewall(mnet: Mininet, s:State):
    print("========================================")
    print("=============Testing Fwall==============")
    print("========================================")
    for _, network in s.networks.items():
        for _, router in network.routers.items():
            for rule in router.rules:
                testRule(mnet, s, rule)
    print("========================================")
    print("========================================")
    print("========================================\n")

def testICMP(mnet: Mininet, s: State):
    print("========================================")
    print("=============Testing Ping===============")
    print("========================================")
    for _, network in s.networks.items():
        for router in network.routers.values():
            print(f"===Testing ICMP for {router.nodeName}===")
            rIp = router.ip.getCompleteIp()
            command = f"ping {rIp} -c 5 | grep received"
            for hName in network.hosts:
                hNode = mnet.get(hName)
                print(f"Testing ICMP {hName} <-> {router.nodeName} ({command}): ", end="")
                print(hNode.cmd(command), end="")
            print(f"========================================")
    print("========================================")
    print("========================================")
    print("========================================\n")