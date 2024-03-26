import re
from datetime import datetime
import toml


class EthPort:
    def __init__(self, port, mac):
        self.port = port
        self.mac = mac

    def __str__(self):
        return f"Port: {self.port}, Mac: {self.mac}"


class Link:
    def __init__(self, data):
        # ignore data field
        self.initialized = True

    def __str__(self):
        string = "Link"
        for atribute in self.__dict__:
            if not atribute == "initialized":
                string += f"\n\t{atribute}: {self.__dict__[atribute]}"
        return string

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

        return string + "\n"

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

        return string + "\n"


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

        return string + "\n"


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

        return string + "\n"


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


def mapper(device_type, data):
    map_ = {"router": Router, "switch": Switch, "host": Host, "link": Link}
    return map_[device_type](data)


def apply_dynamic_common_settings(devices, common_settings):
    # Regular expression to find placeholders like ${common.entry}
    placeholder_pattern = re.compile(r"\$\{common\.(\w+)\}")

    def replace_placeholders(value):
        """Replace placeholders in a given value with the corresponding common setting."""
        if isinstance(value, str):
            matches = placeholder_pattern.findall(value)
            for match in matches:
                if match in common_settings:
                    replacement = common_settings[match]
                    # If the replacement is not a string, convert it appropriately
                    if not isinstance(replacement, str):
                        if isinstance(replacement, (int, float, bool)):
                            replacement = str(replacement)
                        elif isinstance(replacement, datetime):
                            replacement = replacement.isoformat()
                        # Lists and dictionaries are not expected to be interpolated into strings directly
                    # Replace the whole placeholder string if it's the only thing in the value
                    if value == f"${{common.{match}}}":
                        return replacement
                    else:
                        value = value.replace(f"${{common.{match}}}", replacement)
            return value
        elif isinstance(value, list):
            # If the value is a list, iterate over each item
            return [replace_placeholders(item) for item in value]
        else:
            # Non-string, non-list values are returned as is
            return value

    for device_type, device_list in devices.items():
        for device in device_list:
            for attribute in list(vars(device)):
                original_value = getattr(device, attribute)
                replaced_value = replace_placeholders(original_value)
                setattr(device, attribute, replaced_value)


def devices(path):
    with open(path) as f:
        data = toml.load(f)

    devices_dict = {}
    links = []
    common_settings = data.get("common", {})

    # Parsing each device type
    if "hosts" in data:
        devices_dict["host"] = parser("host", data["hosts"])
    if "routers" in data:
        devices_dict["router"] = parser("router", data["routers"])
    if "switches" in data:
        devices_dict["switch"] = parser("switch", data["switches"])
    if "links" in data:
        links = parser("link", data["links"])

    # Apply common settings
    apply_dynamic_common_settings(devices_dict, common_settings)

    # Validate number of devices and links
    ## Validate hosts
    host_numbers = data.get("network", {}).get("hosts", 0)
    if host_numbers != len(devices_dict.get("host", [])):
        raise ValueError(
            f"Number of hosts in the configuration ({host_numbers}) does not match the number of hosts generated ({len(devices_dict.get('host', []))})"
        )

    ## Validate routers
    router_numbers = data.get("network", {}).get("routers", 0)
    if router_numbers != len(devices_dict.get("router", [])):
        raise ValueError(
            f"Number of routers in the configuration ({router_numbers}) does not match the number of routers generated ({len(devices_dict.get('router', []))})"
        )

    ## Validate switches
    switch_numbers = data.get("network", {}).get("switches", 0)
    if switch_numbers != len(devices_dict.get("switch", [])):
        raise ValueError(
            f"Number of switches in the configuration ({switch_numbers}) does not match the number of switches generated ({len(devices_dict.get('switch', []))})"
        )

    links_numbers = data.get("network", {}).get("links", 0)
    if links_numbers != len(links):
        raise ValueError(
            f"Number of links in the configuration ({links_numbers}) does not match the number of links generated ({len(links)})"
        )

    return devices_dict, links


if __name__ == "__main__":
    print(devices("network.toml"))
