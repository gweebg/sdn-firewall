
from threading import Thread
from config.loader import State, Rule, Host, Router, IP
from mininet.net import Mininet

def serverCMD(dstNode, command, globalRes):
    result = dstNode.cmd(command)
    globalRes += [result]

def getHostsList(s: State, ip: IP) -> list[Host]:
    net = s.networks[ip.networkId]
    if ip.host == 0 or (net.NATted and ip.host == 1 and ip.mask == 32):
        return net.hosts.values()
    else:
        return [s.getHostByIP(ip)]
        
def testRule(mnet: Mininet, s:State, r: Rule):
    udpFlag = "-u" if r.protocol == "0x11" else ""
    dstHosts = getHostsList(s, r.dstIp)
    srcHosts = getHostsList(s, r.srcIp)
    print(f"\n====================Testing rule from: {r.srcIp} to: {r.dstIp} with proto: {r.protocol} on port: {r.Port}====================")
    for h in dstHosts:
        dstNode = mnet.get(h.nodeName)
        serverCommand = f"nc -nl {r.Port} {udpFlag} -v"
        clientCommand = f"nc -z {h.ip.getCompleteIp()} {r.Port} {udpFlag} -w 2 -v"
        clientWrongCommand = f"nc {h.ip.getCompleteIp()} {r.Port+1} {udpFlag} -w 2 -v"
        serverResult = []
        print(f"{h.nodeName} running nc server: {serverCommand}")
        for sH in srcHosts:
            t = Thread(target=serverCMD, args=(dstNode, serverCommand, serverResult))
            t.start()
            srcNode = mnet.get(sH.nodeName)
            print(f"\nTesting {sH.nodeName} <-> {h.nodeName}:")
            print(f"    {sH.nodeName} running wrong command: {clientWrongCommand} -> ", end="")
            wrongResult = srcNode.cmd(clientWrongCommand)
            print("connection timed out correctly" if "timed out" in wrongResult else "WARNING: connection not timed out wrongly(possible problems in firewall rules)")
            print(f"    {sH.nodeName} running correct command: {clientCommand}")
            result = srcNode.cmd(clientCommand)
            t.join()
        serverResult = [element for sublist in [s.split('\n') for s in serverResult] for element in sublist]
        print(f"\n{h.nodeName} command result:", end="\n   ")
        print('\n   '.join([serverResult[0]] + [s for s in serverResult if not "Listening on" in s and s != ""]))
        print(f"===================={h.nodeName} nc server stopped====================")


def testFirewall(mnet: Mininet, s:State):
    print("========================================")
    print("=============Testing Fwall==============")
    print("========================================")
    for _, network in s.networks.items():
        for _, router in network.routers.items():
            if not network.NATted:
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