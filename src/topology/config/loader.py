import yaml, re
import rules.rules as rules
from CustomIP.IP import IP

class Defaults():
    def __init__(self, data):
        print(data)
        self.dict = data
    def get(self, key, value=None):
        return value if not value is None else self.dict[key]

class PortL2():
    def __init__(self, portId: int, nodeType: int, nodeId: int, nodeName):
        self.portId = portId
        self.mac = f"00:00:00:{nodeType:02}:{nodeId:02}:{portId:02}"
        self.nodeName = nodeName
    def __repr__(self):
        return f"[{self.nodeName}.{self.portId}: {self.mac}]"
        # return f"[{self.nodeName}.{self.portId}]"


class Link():
    def __init__(self, nodeName1: str, port1: PortL2, nodeName2: str, port2: PortL2):
        self.ports: dict[str, PortL2] = {nodeName1: port1, nodeName2: port2}
    def getOtherPortFromLocalName(self, localName: str) -> PortL2:
        for name, port in self.ports.items():
            if name != localName:
                return port
    def __repr__(self):
        return f"\n                 ({self.ports})"

class NodeL2():
    def __init__(self, nodeName, macDeviceType, macDeviceId, networkId: int):
        self.network = networkId
        self.nodeName = nodeName
        self.nextPort = 1
        self.macDeviceType = macDeviceType
        self.macDeviceId = macDeviceId
        self.ports: dict[int, PortL2] = {}
        self.linksL2: dict[str, Link] = {}
    def addPort(self) -> PortL2:
        newPort = PortL2(self.nextPort, self.macDeviceType, self.macDeviceId, self.nodeName)
        self.ports[self.nextPort] = newPort
        self.nextPort += 1
        return newPort
    def addLink(self, linkL2: Link):
        if self.nodeName in linkL2.ports.keys():
            for name, _ in linkL2.ports.items():
                if name != self.nodeName:
                    self.linksL2[name] = linkL2
                    break
    def __repr__(self):
        res = f"{self.__class__.__name__} {self.nodeName}:\n         LinksL2:"
        for link in self.linksL2.values():
            ownPort = link.ports[self.nodeName]
            res += f"\n             {ownPort} <-> "
            for node, port in link.ports.items():
                if node != self.nodeName:
                    res += f" {port}"
        return res
    
class Switch(NodeL2):
    def __init__(self, nodeName: str, networkId: int):
        capture = re.match(r"s(\d+)", nodeName)
        self.macDeviceId = int(capture.group(1))
        super().__init__(nodeName, 3, self.macDeviceId, networkId)

class PortL3(PortL2):
    def __init__(self, portId: int, nodeType: int, nodeId: int, nodeName, ip: IP):
        self.ip = ip
        super().__init__(portId, nodeType, nodeId, nodeName)
    def __repr__(self):
        return f"[{self.nodeName}.{self.portId}: {self.mac} ({self.ip})]"

class NodeL3(NodeL2):
    def __init__(self, nodeName: str, macDeviceType: int, macDeviceId: int, ip: IP, networkId: int):
        self.ip = ip
        self.linksL3: dict[str, Link] = {}
        super().__init__(nodeName, macDeviceType, macDeviceId, networkId)
    def addPort(self) -> PortL3:
        newPort = PortL3(self.nextPort, self.macDeviceType, self.macDeviceId, self.nodeName, self.ip)
        self.ports[self.nextPort] = newPort
        self.nextPort += 1
        return newPort
    def addLinkL3(self, linkL3: Link):
        if self.nodeName in linkL3.ports.keys():
            for name, _ in linkL3.ports.items():
                if name != self.nodeName:
                    self.linksL3[name] = linkL3
                    break
    def __repr__(self):
        res = super().__repr__()
        spl = res.split("\n", 1)
        res = f"{spl[0]}"
        res += f"\n         IP: {self.ip}"
        res += f"\n         LinksL3:"
        for link in self.linksL3.values():
            ownPort = link.ports[self.nodeName]
            res += f"\n             {ownPort} <-> "
            for node, port in link.ports.items():
                if node != self.nodeName:
                    res += f" {port}"
        res += f"\n{spl[1]}"
        return res

class FirewallRule():
    def __init__(self, data):
        srcIp_yaml = data["srcIp"]
        self.srcIp = IP(srcIp_yaml["network"], srcIp_yaml["host"], srcIp_yaml["mask"])
        dstIp_yaml = data["dstIp"]
        self.dstIp = IP(dstIp_yaml["network"], dstIp_yaml["host"], dstIp_yaml["mask"])
        self.protocol: str = data["protocol"]
        self.Port: int = data["port"]
        self.LocalPort: int = data.get("localPort", self.Port)
    def __repr__(self):
        return f"\n             src:{self.srcIp} dst:{self.dstIp} proto:{self.protocol} port:{self.Port}"

class Router(NodeL3):
    def __init__(self, nodeName: str, ip: IP, jsonPath: str, bvModel: str, base_ports: dict[str, int], networkId: int, isGateway: bool = False, isNatter=False, rules: list[FirewallRule] = []):
        capture = re.match(r"r(\d+)", nodeName)
        self.macDeviceId = int(capture.group(1))
        super().__init__(nodeName, 1, self.macDeviceId, ip, networkId)
        self.json_path = jsonPath
        self.bvmodel = bvModel
        self.thrift_port = base_ports['base_thrift_port'] + self.macDeviceId - 1
        self.grpc_port = base_ports['base_grpc_port'] + self.macDeviceId - 1
        self.cpu_port = base_ports['base_cpu_port'] + self.macDeviceId - 1
        self.isGateway = isGateway
        self.rules = rules
        self.forwardingLinks: dict[int, Link] = {}
        self.natter = isNatter

    def __repr__(self):
        res = super().__repr__()
        spl = res.split("\n", 1)
        res = f"{spl[0]}"
        res += f"\n         JSON path: {self.json_path}"
        res += f"\n         BV model: {self.bvmodel}"
        res += f"\n         Thrift port: {self.thrift_port}"
        res += f"\n         GRPC port: {self.grpc_port}"
        res += f"\n         CPU port: {self.cpu_port}"
        res += f"\n         Gateway: {self.isGateway}"
        res += f"\n         Rules: {self.rules}"
        res += f"\n         ForwardingLinks:"
        for net, link in self.forwardingLinks.items():
            ownPort = link.ports[self.nodeName]
            res += f"\n             {ownPort} <{self.network}-{net}> "
            for node, port in link.ports.items():
                if node != self.nodeName:
                    res += f" {port}"
        res += f"\n{spl[1]}"
        return res

    def genEnabledFuncsRule(self) -> rules.setEnabledFuncsRule:
        enabledICMP = True
        enabledNAT = self.natter
        return rules.setEnabledFuncsRule(enabledICMP, enabledNAT)
    
    def genIPV4FwdRules(self, state, stage: int) -> list[rules.ipv4FWDRule]:
        res = []
        for netID, network in state.networks.items():
            if netID == self.network:
                links = [(nl3Name, nl3.linksL3[self.nodeName]) for nl3Name, nl3 in network.nodesl3.items() if nl3Name != self.nodeName]
                for remoteName, l3 in links:
                    remotePort: PortL3 = l3.ports[remoteName]
                    fwdIp = IP(remotePort.ip.networkId, remotePort.ip.host, 32)
                    res.append(rules.ipv4FWDRule(fwdIp, l3.ports[self.nodeName].portId))
            else:
                forwardingLink = self.forwardingLinks[netID]
                ipToCopy = forwardingLink.getOtherPortFromLocalName(self.nodeName).ip
                mask = 32 if network.NATted and stage>1 else 24
                fwdIp = IP(ipToCopy.networkId, ipToCopy.host, mask)
                if (ipToCopy.host == 1 and mask == 24):
                    fwdIp = IP(ipToCopy.networkId, ipToCopy.host, mask)
                res.append(rules.ipv4FWDRule(fwdIp, forwardingLink.ports[self.nodeName].portId))
        return res

    def genSrcMacRules(self) -> list[rules.srcMacRule]:
        res = []
        for p in self.ports.values():
            # res += f"table_add src_mac rewrite_src_mac {p.portId} => {p.mac}\n"
            res.append(rules.srcMacRule(p.portId, p.mac))
        return res

    def genDstMacRules(self) -> list[rules.dstMacRule]:
        res = []
        generatedIps = set()
        localPortToRemoteMac: dict[int, str] = {}
        for l in self.linksL3.values():
            remotePort: PortL3 = l.getOtherPortFromLocalName(self.nodeName)
            # res += f"table_add dst_mac rewrite_dst_mac {remotePort.ip.GetIp()} => {remotePort.mac}\n"
            res.append(rules.dstMacRule(remotePort.ip, remotePort.mac))
            generatedIps.add(remotePort.ip.GetIp())
            localPortToRemoteMac[l.ports[self.nodeName].portId] = remotePort.mac
        for l in self.forwardingLinks.values():
            remotePort: PortL3 = l.getOtherPortFromLocalName(self.nodeName)
            remIP = remotePort.ip
            if not remIP.GetIp() in generatedIps:
                # res += f"table_add dst_mac rewrite_dst_mac {remIP} => {localPortToRemoteMac[l.ports[self.nodeName].portId]}\n"
                res.append(rules.dstMacRule(remIP, localPortToRemoteMac[l.ports[self.nodeName].portId]))
                generatedIps.add(remIP.GetIp())
        return res

    def genICMPRules(self) -> rules.icmpRule:
        ipToCopy = IP(self.ip.networkId, self.ip.host, 32)
        return rules.icmpRule(ipToCopy)

    def genPacketDirectionRules(self) -> list[rules.packetDirectionRule]:
        wildcardIP = IP(0, 0, mask=0)
        routerIP = self.ip
        res = []
        res.append(rules.packetDirectionRule(routerIP, wildcardIP, 1))
        res.append(rules.packetDirectionRule(wildcardIP, routerIP, 2))
        res.append(rules.packetDirectionRule(wildcardIP, wildcardIP, 3))
        return res

    def genServerLookupRules(self, state) -> list[rules.serverLookUpRule]:
        publicIp = self.ip
        serverId = 0
        res = []
        hosts = state.networks[self.network].hosts.values()
        maxServerID = sum([h.weight for h in hosts]) - 1
        for host in state.networks[self.network].hosts.values():
            w = host.weight
            hIP = host.ip
            while w > 0:
                nextServerId = serverId+1
                if maxServerID <= serverId or maxServerID == 1:
                    nextServerId = 0
                # res += f"table_add MyEgress.ServerLookup setCurrentServer {serverId} => {hIP} {publicIp} {nextServerId}\n"
                res.append(rules.serverLookUpRule(serverId, hIP, publicIp, nextServerId))
                serverId = nextServerId
                w-=1
        return res

    def genFwallRules(self, stage: int) -> list[rules.Rule]:
        res = []
        for rule in self.rules:
            if stage > 1:
                # res += f"table_add fwall_rules RulesSuccess {rule.srcIp.GetTernaryFormat()} {rule.dstIp.GetTernaryFormat()} {rule.protocol} {rule.Port} => {rule.LocalPort} 1\n"
                # res += f"table_add privateToPublicPort setPublicPort {rule.LocalPort} => {rule.Port}\n"
                res.append(rules.fwallNatRule(rule.srcIp, rule.dstIp, rule.protocol, rule.Port, rule.LocalPort))
                res.append(rules.privateToPublicPortRule(rule.LocalPort, rule.Port))
            else:
                # res += f"table_add fwall_rules RulesSuccess {rule.srcIp.GetTernaryFormat()} {rule.dstIp.GetTernaryFormat()} {rule.protocol} {rule.Port} 1 1\n"
                res.append(rules.fwallRule(rule.srcIp, rule.dstIp, rule.protocol, rule.Port))
        return res

    def setTableEntriesForRouter(self, state, stage: int):
        res = []
        res.append(self.genEnabledFuncsRule())
        res += self.genIPV4FwdRules(state, stage)
        res += self.genSrcMacRules()
        res += self.genDstMacRules()
        res += self.genPacketDirectionRules()
        if stage > 1:
            res.append(self.genICMPRules())
            if self.natter:
                res += self.genServerLookupRules(state)
        res += self.genFwallRules(stage)
        self.TableEntries = res

    def getTableEntriesInText(self) -> str:
        return "\n".join(["reset_state"] + [str(rule) for rule in self.TableEntries])

class Host(NodeL3):
    def __init__(self, nodeName: str, ip: str, networkId: int, weight:int):
        capture = re.match(r"h(\d+)", nodeName)
        self.macDeviceId = int(capture.group(1))
        self.weight = weight
        super().__init__(nodeName, 2, self.macDeviceId, ip, networkId)

class Network():
    def __init__(self, data, defaults: dict[str, any]):
        self.defaults: Defaults = defaults
        self.netId: int = data["id"]
        self.nodes: dict[str, NodeL2] = {}
        self.nodesl3: dict[str, NodeL3] = {}
        self.routers: dict[str, Router] = {}
        self.hosts: dict[str, Host] = {}
        self.switches: dict[str, Switch] = {}
        self.linksL2: dict[frozenset[str, str], Link] = {}
        self.gateway = "not-set"
        self.NATted = data.get("NATted", False)
        devices = data["nodes"]
        if "switches" in devices:
            for s_yaml in devices["switches"]:
                s = Switch(s_yaml, self.netId)
                self.nodes[s.nodeName] = s
                self.switches[s.nodeName] = s
        if "routers" in devices:
            for r_name, r_body in devices["routers"].items():
                if r_body.get("gateway", False):
                    self.gateway = r_name
                rules: list[FirewallRule] = []
                for rule in r_body.get("rules", []):
                    rules.append(FirewallRule(rule))
                json_path = r_body.get("json_path", defaults["json_path"])
                bvmodel = r_body.get("bvmodel", defaults["bvmodel"])
                base_thrift_port = r_body.get("base_thrift_port", defaults["base_thrift_port"])
                isGateway = r_body.get("gateway", False)
                base_ports = {}
                base_ports['base_thrift_port'] = r_body.get("base_thrift_port", defaults["base_thrift_port"])
                base_ports['base_grpc_port'] = r_body.get("base_grpc_port", defaults["base_grpc_port"])
                base_ports['base_cpu_port'] = r_body.get("base_cpu_port", defaults["base_cpu_port"])
                r = Router(r_name, IP(self.netId, 1), json_path, bvmodel, base_ports, self.netId, isGateway, self.NATted,  rules)
                self.nodes[r.nodeName] = r
                self.nodesl3[r.nodeName] = r
                self.routers[r.nodeName] = r
                for l in r_body["links"]:
                    self.linksL2[frozenset([r_name, l])] = None
        if "hosts" in devices:
            for h_name, h_body in devices["hosts"].items():
                weight = h_body.get("weight", 1)
                h = Host(h_name, IP(self.netId, h_body["hostIp"]), self.netId, weight)
                self.nodes[h.nodeName] = h
                self.nodesl3[h.nodeName] = h
                self.hosts[h.nodeName] = h
                for l in h_body["links"]:
                    self.linksL2[frozenset([h_name, l])] = None

    def __repr__(self):
        res = f"\n{self.__class__.__name__}{self.netId}(gateway:{self.gateway}):"
        for node in self.nodes.values():
            res += f"\n    {node}"
        return res
    
    

class State():
    def __init__(self, data, stage: int = 1):
        self.networks: dict[int, Network] = {}
        self.nodes: dict[str, NodeL2] = {}
        self.nodesl3: dict[str, NodeL3] = {}
        self.routers: dict[str, Router] = {}
        self.hosts: dict[str, Host] = {}
        self.switches: dict[str, Switch] = {}
        self.linksL2: dict[frozenset[str, str], Link] = {}
        self.linksL3: dict[frozenset[str, str], Link] = {}
        self.defaults: dict[str, any] = data["defaults"]
        self.stage = stage
        for net in data["networks"]:
            net = Network(net, self.defaults)
            self.networks[net.netId] = net
            self.nodes.update(net.nodes)
            self.nodesl3.update(net.nodesl3)
            self.routers.update(net.routers)
            self.hosts.update(net.hosts)
            self.switches.update(net.switches)
            self.linksL2.update(net.linksL2)
        for srcName, dstName in self.linksL2.keys():
            srcNode = self.nodes[srcName]
            dstNode = self.nodes[dstName]
            srcPort = srcNode.addPort()
            dstPort = dstNode.addPort()
            link = Link(srcName, srcPort, dstName, dstPort)
            srcNode.addLink(link)
            dstNode.addLink(link)
            self.linksL2[frozenset([srcName, dstName])] = link
            if srcNode.network != dstNode.network:
                self.networks[srcNode.network].linksL2[frozenset([srcName, dstName])] = link
            self.networks[dstNode.network].linksL2[frozenset([srcName, dstName])] = link
        for router in self.routers.values():
            for remoteNodeName, link in router.linksL2.items():
                localPort = link.ports[router.nodeName]
                remoteNode = self.nodes[remoteNodeName]
                if isinstance(remoteNode, NodeL3):
                    remotePort = link.getOtherPortFromLocalName(router.nodeName)
                    linkL3 = Link(router.nodeName, localPort, remoteNodeName, remotePort)
                    router.addLinkL3(linkL3)
                    remoteNode.addLinkL3(linkL3)
                    self.linksL3[frozenset([router.nodeName, remoteNodeName])] = linkL3
                else:
                    for remoteNodeName2, link2 in remoteNode.linksL2.items():
                        remoteNode2 = self.nodes[remoteNodeName2]
                        remotePort = link2.getOtherPortFromLocalName(remoteNodeName)
                        linkL3 = Link(router.nodeName, localPort, remoteNodeName2, remotePort)
                        router.addLinkL3(linkL3)
                        remoteNode2.addLinkL3(linkL3)
                        self.linksL3[frozenset([router.nodeName, remoteNodeName2])] = linkL3
        for router in self.routers.values():
            for netID, network in self.networks.items():
                if netID != router.network:
                    gatewayRouter: Router = self.routers[network.gateway]
                    linksIter = [(remoteName, l.ports[remoteName], l.ports[router.nodeName]) for remoteName, l in router.linksL3.items()]
                    checkedNodes = set([router.nodeName])
                    result: tuple[str, PortL2, PortL2] = ("", None, None)
                    while result[0] == "" and len(linksIter):
                        tryingNodeName, tryingPort, originalPort = linksIter.pop(0)
                        if tryingNodeName == gatewayRouter.nodeName:
                            result = (tryingNodeName, tryingPort, originalPort)
                            continue
                        elif tryingNodeName in self.routers:
                            linksIter += [(newRemoteName, newRemote.ports[newRemoteName], originalPort) for newRemoteName, newRemote in self.routers[tryingNodeName].linksL3.items() if newRemoteName not in checkedNodes]
                            checkedNodes.add(tryingNodeName)
                    router.forwardingLinks[netID] = Link(router.nodeName, result[2], result[0], result[1])
        for r in self.routers.values():
            r.setTableEntriesForRouter(self, stage)
    
    def getHostByIP(self, ip: IP) -> Host:
        for hName, host in self.hosts.items():
            if host.ip == ip:
                return host
                        
    

    def __repr__(self):
        res = f""
        for net in self.networks.values():
            res += f"    {net}"
        return res

def getState(path: str, stage: int) -> State:
    f = open(path, "r")
    network = yaml.load(f, Loader=yaml.FullLoader)
    f.close()
    # Example usage (assuming you have the YAML data in a variable called 'yaml_data')
    state = State(network, stage)
    return state


if __name__ == "__main__":
    print(getState("./config/network.yml", 2))
