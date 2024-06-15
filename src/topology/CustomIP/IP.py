def cidr_to_netmask(cidr) -> str:
    cidr = int(cidr)
    mask_bin = f"{'1'*cidr}{'0'*(32-cidr)}"
    out = f"{int(mask_bin[0:8], 2)}.{int(mask_bin[8:16], 2)}.{int(mask_bin[16:24], 2)}.{int(mask_bin[24:32], 2)}"
    return out

class IP():
    def __init__(self, network: int, host: int, mask=24, subnetwork=0):
        self.network = f"10.{network}.{subnetwork}"
        self.networkId = network
        self.host = host
        self.mask = mask
    def GetIp(self) -> str:
        return f"{self.network}.{self.host}"

    def GetNetworkCIDR(self, isTuple = False) -> str | tuple[str, str]:
        ip = f"{self.network}.0"
        mask = f"{self.mask}"
        if isTuple:
            return (ip, self.mask)
        else:
            return f"{ip}/{mask}"

    def GetIpWithMask(self, isTuple = False) -> str | tuple[str, str]:
        ip = f"{self.network}.{self.host}"
        mask = f"{self.mask}"
        if isTuple:
            return (ip, self.mask)
        else:
            return f"{ip}/{mask}"

    def GetNetworkTernaryFormat(self, isTuple = False) -> str | tuple[str, str]:
        ip = f"{self.network}.0"
        mask = cidr_to_netmask(self.mask)
        if isTuple:
            return (ip, mask)
        else:
            return f"{ip}&&&{mask}"

    def GetTernaryFormat(self, isTuple = False) -> str | tuple[str, str]:
        ip = f"{self.network}.{self.host}"
        mask = cidr_to_netmask(self.mask)
        if isTuple:
            return (ip, mask)
        else:
            return f"{ip}&&&{mask}"

    def GetTernaryFormatCustomMask(self, customMask: int, isTuple = False) -> str | tuple[str, str]:
        ip = f"{self.network}.{self.host}"
        mask = cidr_to_netmask(customMask)
        if isTuple:
            return (ip, mask)
        else:
            return f"{ip}&&&{mask}"

    def __repr__(self):
        return self.GetIpWithMask()
    def __eq__(self, other):
        return self.GetIp() == other.GetIp()
    def __hash__(self):
        return hash(self.GetIpWithMask())