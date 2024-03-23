import toml

devices = ["router", "switch", "host"]

class EthPort:
    def __init__(self, port,mac):
        self.port = port
        self.mac = mac

    def __str__(self):
        return f"Port: {self.port}, Mac: {self.mac}"


class Link:
    def __init__(self, device1, port1, device2, port2, mac1, mac2):
        self.device1 = device1
        self.port1 = port1
        self.mac1 = mac1
        self.device2 = device2
        self.port2 = port2
        self.mac2 = mac2

    def __str__(self):
        return f"Link {self.device1} <-> {self.device2}\n\tPort {self.port1}: Mac {self.mac1}\n\tPort {self.port2}: Mac {self.mac2}\n"

    def __repr__(self):
        return self.__str__()


class Device:
    def __init__(self, device):
        self.device = device
        self.ports = []
    def __str__(self):
        string = f"Device {self.device}"

        self__dict__ = self.__dict__
        for atribute in self__dict__:
            if not (atribute == "device" or atribute == "ports"):
                string += f"\n\t{atribute}: {self__dict__[atribute]}"


        string += "\n\tPorts:"
        for port in self.ports:
            string += f"\n\t\t{port}"

        return (string + "\n")

    def __repr__(self):
        return self.__str__()

class Router(Device):
    def __init__(self, device):
        super().__init__(device)

    def __str__(self):
        string = f"Router {self.device}"

        self__dict__ = self.__dict__
        for atribute in self__dict__:
            if not (atribute == "device" or atribute == "ports"):
                string += f"\n\t{atribute}: {self__dict__[atribute]}"


        string += "\n\tPorts:"
        for port in self.ports:
            string += f"\n\t\t{port}"

        return (string + "\n")


class Switch(Device):
    def __init__(self, device):
        super().__init__(device)

    def __str__(self):
        string = f"Switch {self.device}"

        self__dict__ = self.__dict__
        for atribute in self__dict__:
            if not (atribute == "device" or atribute == "ports"):
                string += f"\n\t{atribute}: {self__dict__[atribute]}"


        string += "\n\tPorts:"
        for port in self.ports:
            string += f"\n\t\t{port}"

        return (string + "\n")


class Host(Device):
    def __init__(self, device):
        super().__init__(device)

    def __str__(self):
        string = f"Host {self.device}"

        self__dict__ = self.__dict__
        for atribute in self__dict__:
            if not (atribute == "device" or atribute == "ports"):
                string += f"\n\t{atribute}: {self__dict__[atribute]}"


        string += "\n\tPorts:"
        for port in self.ports:
            string += f"\n\t\t{port}"

        return (string + "\n")

def parse_links(data):
    links = []
    for link_data in data:
        link = Link(link_data['device1'], link_data['port1'], link_data['device2'], link_data['port2'], link_data['mac1'], link_data['mac2'])       
        links.append(link)
    return links



def parser(device_type, data):
    device_list = []
    for device_data in data:
        device = mapper(device_type, device_data.get("name", "Unknown"))
        for key, value in device_data.items():
            if key == "ports":
                port_num = 0
                for port_mac in value:
                    # Assuming the format "00:00:00:02:00:01" for MAC, can adjust if needed
                    port_num += 1  # Adjust based on your specific needs or keep dynamic
                    device.ports.append(EthPort(port_num, port_mac))
            else:
                setattr(device, key, value)
        device_list.append(device)
    return device_list

def mapper(device_type,data):
    match device_type:
        case "router":
            return Router(data)
        case "switch":
            return Switch(data)
        case "host":
            return Host(data)
        case _:
            return None


def apply_common_settings(devices, common_settings):
    for device_type, device_list in devices.items():
        for device in device_list:
            # Apply 'cls_host' to hosts
            if device_type == 'host' and 'cls_host' in common_settings:
                device.cls = common_settings['cls_host']
            
            # Apply 'bvmodel' to routers
            if device_type == 'router' and 'bvmodel' in common_settings:
                device.bvmodel = common_settings['bvmodel']
            
            # Apply 'cls_switch' to switches
            if device_type == 'switch' and 'cls_switch' in common_settings:
                device.cls = common_settings['cls_switch']
            
            # Apply 'cls_router' (assuming you might want this for customization)
            # Adjust this part based on how you intend to use 'cls_router'
            if device_type == 'router' and 'cls_router' in common_settings:
                device.cls = common_settings['cls_router']


def devices(path):
    with open(path) as f:
        data = toml.load(f)

    devices_dict = {}
    common_settings = data.get('common', {})

    # Parsing each device type
    if 'hosts' in data:
        devices_dict['host'] = parser("host", data['hosts'])
    if 'routers' in data:
        devices_dict['router'] = parser("router", data['routers'])
    if 'switches' in data:
        devices_dict['switch'] = parser("switch", data['switches'])
    
    # Apply common settings
    apply_common_settings(devices_dict, common_settings)

    # Parse links
    if 'links' in data:
        links = parse_links(data['links'])

    return devices_dict, links


if __name__ == "__main__":
    print(devices('network.toml'))

