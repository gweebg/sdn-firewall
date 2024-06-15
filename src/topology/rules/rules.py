from CustomIP.IP import IP

class Rule():
    def __init__(self, TableName: str, ActionName: str, Keys: list[str], ActionArgs: list[str], values: dict[str, str],hasPrio: bool):
        self.TableName = TableName
        self.ActionName = ActionName
        self.Keys = Keys
        self.ActionArgs = ActionArgs
        self.values = values
        self.hasPrio = hasPrio
        self.IsSettingDefault = False
    def __str__(self):
        rList = []
        if self.IsSettingDefault:
            rList += ["table_set_default"]
        else:
            rList += ["table_add"]
        rList += [self.TableName, self.ActionName]
        
        if not self.IsSettingDefault:
            for k in self.Keys:
                if type(self.values[k]) is tuple:
                    rList.append(self.values[k][0])
                else:
                    rList.append(self.values[k])    
        
        if len(self.ActionArgs) > 0:
            if not self.IsSettingDefault:
                rList.append("=>")
            for a in self.ActionArgs:
                if type(self.values[a]) is tuple:
                    rList.append(self.values[a][0])
                else:
                    rList.append(self.values[a])
        
        if self.hasPrio and not self.IsSettingDefault:
            rList.append("1")
        
        return " ".join([str(v) for v in rList])

class setEnabledFuncsRule(Rule):
    def __init__(self, enabledICMP: bool, enabledNAT: bool):
        self.TableName = "MyIngress.EnabledFuncsTable"
        self.ActionName = "MyIngress.setEnabledFuncs"
        # self.Keys = ["hdr.ipv4.srcAddr"]
        self.ActionArgs = ["enabledICMP", "enabledNAT"]
        self.values = {"enabledICMP": int(enabledICMP), "enabledNAT": int(enabledNAT)}
        self.IsSettingDefault = True
        self.hasPrio = False
    def __str__(self):
        return super().__str__()

class ipv4FWDRule(Rule):
    def __init__(self, dstIp: IP, Port: int):
        self.dstIp = dstIp
        self.Port = Port
        self.TableName = "MyIngress.ipv4_lpm"
        self.ActionName = "MyIngress.ipv4_fwd"
        self.Keys = ["hdr.ipv4.dstAddr"]
        self.ActionArgs = ["nxt_hop", "port"]
        dstIpToWrite = (dstIp.GetIpWithMask(), dstIp.GetIpWithMask(True))
        if dstIp.mask == 24:
            dst_tuple = (f"{dstIp.network}.0", dstIp.mask)
            dstIpToWrite = (f"{dstIp.network}.0/{dstIp.mask}", dst_tuple)
        self.values = {"hdr.ipv4.dstAddr": dstIpToWrite, "nxt_hop": dstIp.GetIp(), "port": Port}
        self.hasPrio = False
        self.IsSettingDefault = False
    def __str__(self):
        return super().__str__()

class srcMacRule(Rule):
    def __init__(self, port: int, src_mac: str):
        self.TableName = "MyIngress.src_mac"
        self.ActionName = "MyIngress.rewrite_src_mac"
        self.Keys = ["standard_metadata.egress_spec"]
        self.ActionArgs = ["src_mac"]
        self.port = port
        self.src_mac = src_mac
        self.values = {"standard_metadata.egress_spec": port, "src_mac": src_mac}
        self.hasPrio = False
        self.IsSettingDefault = False
    def __str__(self):
        return super().__str__()

class dstMacRule(Rule):
    def __init__(self, nxtHopIP: IP, dst_mac: str):
        self.TableName = "MyIngress.dst_mac"
        self.ActionName = "MyIngress.rewrite_dst_mac"
        self.Keys = ["meta.next_hop_ipv4"]
        self.ActionArgs = ["dst_mac"]
        self.nxtHopIP = nxtHopIP
        self.dst_mac = dst_mac
        self.values = {"meta.next_hop_ipv4": nxtHopIP.GetIp(), "dst_mac": dst_mac}
        self.hasPrio = False
        self.IsSettingDefault = False
    def __str__(self):
        return super().__str__()

class icmpRule(Rule):
    def __init__(self, selfAddr: IP):
        self.selfAddr = selfAddr
        self.TableName = "MyIngress.self_icmp"
        self.ActionName = "MyIngress.reply_to_icmp"
        self.Keys = ["hdr.ipv4.dstAddr"]
        self.ActionArgs = []
        selfIpTuple = (selfAddr.GetIpWithMask(), selfAddr.GetIpWithMask(True))
        if selfAddr.mask == 24:
            dst_tuple = (f"{selfAddr.network}.1", 32)
            selfIpTuple = (f"{selfAddr.network}.1/{32}", dst_tuple)
        self.values = {"hdr.ipv4.dstAddr": selfIpTuple}
        self.hasPrio = True
        self.IsSettingDefault = False
    def __str__(self):
        return super().__str__()

class packetDirectionRule(Rule):
    def __init__(self, firstIP: IP, secondIP: IP, direction: int):
        self.firstIP = firstIP
        self.secondIP = secondIP
        self.direction = direction
        self.TableName = "MyIngress.checkPacketDirection"
        self.ActionName = "MyIngress.setPacketDirection"
        self.Keys = ["hdr.ipv4.srcAddr", "hdr.ipv4.dstAddr"]
        self.ActionArgs = ["dir"]
        srcIpToWrite = (firstIP.GetNetworkTernaryFormat(), firstIP.GetNetworkTernaryFormat(True))
        dstIpToWrite = (secondIP.GetNetworkTernaryFormat(), secondIP.GetNetworkTernaryFormat(True))
        if (srcIpToWrite[1][1] == "0.0.0.0"):
            srcIpToWrite_TMP = (srcIpToWrite[1][0],"255.0.0.0")
            srcIpToWrite = (srcIpToWrite[0],srcIpToWrite_TMP)
        if (dstIpToWrite[1][1] == "0.0.0.0"):
            dstIpToWrite_TMP = (dstIpToWrite[1][0],"255.0.0.0")
            dstIpToWrite = (dstIpToWrite[0],dstIpToWrite_TMP)
        self.values = {"hdr.ipv4.srcAddr": srcIpToWrite, "hdr.ipv4.dstAddr": dstIpToWrite, "dir": direction}
        self.hasPrio = True
        self.IsSettingDefault = False
    def __str__(self):
        return super().__str__()

class serverLookUpRule(Rule):
    def __init__(self, currServerID: int, privateIp: IP, publicIp: IP, nextServerID: int):
        self.currServerID = currServerID
        self.privateIp = privateIp
        self.publicIp = publicIp
        self.nextServerID = nextServerID
        self.TableName = "MyEgress.ServerLookup"
        self.ActionName = "MyEgress.setCurrentServer"
        self.Keys = ["meta.cServerID"]
        self.ActionArgs = ["privAddr", "publicAddr", "nextSID"]
        self.values = {"meta.cServerID": currServerID, "privAddr": privateIp.GetIp(), "publicAddr": publicIp.GetIp(), "nextSID": nextServerID}
        self.hasPrio = False
        self.IsSettingDefault = False
    def __str__(self):
        return super().__str__()

class fwallNatRule(Rule):
    def __init__(self, srcIp: IP, dstIp: IP, protocol: str, Port: int, PrivatePort: int):
        self.srcIp = srcIp
        self.dstIp = dstIp
        self.Port = Port
        self.protocol = protocol
        self.PrivatePort = PrivatePort
        self.TableName = "MyEgress.fwall_rules"
        self.ActionName = "MyEgress.RulesSuccess"
        self.Keys = ["hdr.ipv4.srcAddr", "hdr.ipv4.dstAddr", "hdr.ipv4.protocol", "hdr.ports.dstPort"]
        self.ActionArgs = ["privPort"]
        srcIpToWrite = (srcIp.GetTernaryFormat(), srcIp.GetTernaryFormat(True))
        dstIpToWrite = (dstIp.GetTernaryFormat(), dstIp.GetTernaryFormat(True))
        self.values = {"hdr.ipv4.srcAddr": srcIpToWrite, "hdr.ipv4.dstAddr": dstIpToWrite, "hdr.ipv4.protocol": protocol, "hdr.ports.dstPort": Port, "privPort": PrivatePort}
        self.hasPrio = True
        self.IsSettingDefault = False
    def __str__(self):
        return super().__str__()


class fwallRule(Rule):
    def __init__(self, srcIp: IP, dstIp: IP, protocol: str, Port: int):
        self.srcIp = srcIp
        self.dstIp = dstIp
        self.Port = Port
        self.protocol = protocol
        self.TableName = "MyEgress.fwall_rules"
        self.ActionName = "MyEgress.RulesSuccess"
        self.Keys = ["hdr.ipv4.srcAddr", "hdr.ipv4.dstAddr", "hdr.ipv4.protocol", "hdr.ports.dstPort"]
        self.ActionArgs = []
        srcIpToWrite = (srcIp.GetTernaryFormat(), srcIp.GetTernaryFormat(True))
        dstIpToWrite = (dstIp.GetTernaryFormat(), dstIp.GetTernaryFormat(True))
        self.values = {"hdr.ipv4.srcAddr": srcIpToWrite, "hdr.ipv4.dstAddr": dstIpToWrite, "hdr.ipv4.protocol": protocol, "hdr.ports.dstPort": Port}
        self.hasPrio = True
        self.IsSettingDefault = False
    def __str__(self):
        return super().__str__() + " 1"

class privateToPublicPortRule(Rule):
    def __init__(self, privatePort: int, publicPort: int):
        self.privatePort = privatePort
        self.publicPort = publicPort
        self.TableName = "MyEgress.privateToPublicPort"
        self.ActionName = "MyEgress.setPublicPort"
        self.Keys = ["meta.outboundPrivatePort"]
        self.ActionArgs = ["pubPort"]
        self.values = {"meta.outboundPrivatePort": privatePort, "pubPort": publicPort}
        self.hasPrio = False
        self.IsSettingDefault = False
    def __str__(self):
        return super().__str__()