import toml

class EthPort:
    def __init__(self, port,mac):
        self.port = port
        self.mac = mac

    def __str__(self):
        return f"Port: {self.port}, Mac: {self.mac}"

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


def load_config(path):
    device_list = []
    with open(path) as f:
        data = toml.load(f)

        devices = data['router']
        devices.update(data['switch'])

        for device in devices:
            stuff = Device(device)
            for key,value in devices[device].items():
                if key == "ports":
                    for port,value in value.items():
                        port_num = port.replace("port","")
                        port_num = int(port_num)
                        stuff.ports.append(EthPort(port_num,value))
                else:
                    setattr(stuff, key, value)
                
            device_list.append(stuff)

    return device_list





if __name__ == "__main__":
    print(load_config('network.toml'))

