import yaml, re

def cidr_to_netmask(cidr) -> str:
    cidr = int(cidr)
    mask_bin = f"{'1'*cidr}{'0'*(32-cidr)}"
    out = f"{int(mask_bin[0:8], 2)}.{int(mask_bin[8:16], 2)}.{int(mask_bin[16:24], 2)}.{int(mask_bin[24:32], 2)}"
    return out

class IP():
    def __init__(self, network: int, host: int, mask=24):
        self.network = f"10.{network}.0"
        self.networkId = network
        self.host = host
        self.mask = mask
    def getCompleteIp(self) -> str:
        return f"{self.network}.{self.host}"
    def getNetworkCIDR(self) -> str:
        return f"{self.network}.0/{self.mask}"
    def getCompleteIpWithMask(self) -> str:
        return f"{self.network}.{self.host}/{self.mask}"
    def getNetworkTernaryFormat(self) -> str:
        return f"{self.network}.0&&&{cidr_to_netmask(self.mask)}"
    def GetCompleteTernaryFormat(self) -> str:
        return f"{self.network}.{self.host}&&&{cidr_to_netmask(self.mask)}"
    def GetCompleteTernaryFormatCustomMask(self, customMask: int) -> str:
        return f"{self.network}.{self.host}&&&{cidr_to_netmask(customMask)}"
    def __repr__(self):
        return self.getCompleteIpWithMask()
    def __eq__(self, other):
        return self.getCompleteIp() == other.getCompleteIp()

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

class Rule():
    def __init__(self, data):
        srcIp_yaml = data["srcIp"]
        self.srcIp = IP(srcIp_yaml["network"], srcIp_yaml["host"], srcIp_yaml["mask"])
        dstIp_yaml = data["dstIp"]
        self.dstIp = IP(dstIp_yaml["network"], dstIp_yaml["host"], dstIp_yaml["mask"])
        self.protocol: str = data["protocol"]
        self.Port: int = data["port"]
    def __repr__(self):
        return f"\n             src:{self.srcIp} dst:{self.dstIp} proto:{self.protocol} port:{self.Port}"

class Router(NodeL3):
    def __init__(self, nodeName: str, ip: IP, jsonPath: str, bvModel: str, base_thrift_port: int, networkId: int, isGateway: bool = False, rules: list[Rule] = []):
        capture = re.match(r"r(\d+)", nodeName)
        self.macDeviceId = int(capture.group(1))
        super().__init__(nodeName, 1, self.macDeviceId, ip, networkId)
        self.json_path = jsonPath
        self.bvmodel = bvModel
        self.thrift_port = base_thrift_port + self.macDeviceId - 1
        self.isGateway = isGateway
        self.rules = rules
    def __repr__(self):
        res = super().__repr__()
        spl = res.split("\n", 1)
        res = f"{spl[0]}"
        res += f"\n         JSON path: {self.json_path}"
        res += f"\n         BV model: {self.bvmodel}"
        res += f"\n         Thrift port: {self.thrift_port}"
        res += f"\n         Gateway: {self.isGateway}"
        res += f"\n         Rules: {self.rules}"
        res += f"\n{spl[1]}"
        return res

class Host(NodeL3):
    def __init__(self, nodeName: str, ip: str, networkId: int):
        capture = re.match(r"h(\d+)", nodeName)
        self.macDeviceId = int(capture.group(1))
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
        devices = data["nodes"]
        for s_yaml in devices["switches"]:
            s = Switch(s_yaml, self.netId)
            self.nodes[s.nodeName] = s
            self.switches[s.nodeName] = s
        for r_name, r_body in devices["routers"].items():
            if r_body.get("gateway", False):
                self.gateway = r_name
            rules: list[Rule] = []
            for rule in r_body.get("rules", []):
                rules.append(Rule(rule))
            json_path = r_body.get("json_path", defaults["json_path"])
            bvmodel = r_body.get("bvmodel", defaults["bvmodel"])
            base_thrift_port = r_body.get("base_thrift_port", defaults["base_thrift_port"])
            isGateway = r_body.get("gateway", False)
            r = Router(r_name, IP(self.netId, 1), json_path, bvmodel, base_thrift_port, self.netId, isGateway, rules)
            self.nodes[r.nodeName] = r
            self.nodesl3[r.nodeName] = r
            self.routers[r.nodeName] = r
            for l in r_body["links"]:
                self.linksL2[frozenset([r_name, l])] = None
        for h_name, h_body in devices["hosts"].items():
            h = Host(h_name, IP(self.netId, h_body["hostIp"]), self.netId)
            self.nodes[h.nodeName] = h
            self.nodesl3[h.nodeName] = h
            self.hosts[h.nodeName] = h
            for l in h_body["links"]:
                self.linksL2[frozenset([h_name, l])] = None

    def __repr__(self):
        res = f"\n{self.__class__.__name__}{self.netId}:"
        for node in self.nodes.values():
            res += f"\n    {node}"
        return res
    
    

class State():
    def __init__(self, data):
        self.networks: dict[int, Network] = {}
        self.nodes: dict[str, NodeL2] = {}
        self.nodesl3: dict[str, NodeL3] = {}
        self.routers: dict[str, Router] = {}
        self.hosts: dict[str, Host] = {}
        self.switches: dict[str, Switch] = {}
        self.linksL2: dict[frozenset[str, str], Link] = {}
        self.linksL3: dict[frozenset[str, str], Link] = {}
        self.defaults: dict[str, any] = data["defaults"]
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
                            
    def getHostByIP(self, ip: IP) -> Host:
        for hName, host in self.hosts.items():
            if host.ip == ip:
                return host
                        

    def __repr__(self):
        res = f""
        for net in self.networks.values():
            res += f"    {net}"
        return res

def getState(path: str) -> State:
    f = open(path, "r")
    network = yaml.load(f, Loader=yaml.FullLoader)
    f.close()
    # Example usage (assuming you have the YAML data in a variable called 'yaml_data')
    state = State(network)
    return state

print(getState("./config/network.yml"))