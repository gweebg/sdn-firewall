
![Logo](.extra/firewall.png)
# TechSecure Firewall

A firewall implemented in p4.

This project was developed as a study case for Software Defined Networks course in Universidade do Minho's Computer and Software Engineering Master's degree.

## Installation

Clone the repository

```bash
  git clone https://github.com/gweebg/sdn-firewall.git
  cd sdn-firewall
```


Install all required packages with pip

```bash
  venv .env
  source .env/bin/activate
  pip install -r requirements.txt
```
    
## Usage/Examples

Config file `config/network.toml` layout example

```toml
# Network summary
[network]
hosts = 9
switches = 3
routers = 3

# Common configuration settings
[common]
cls_host = "P4Host"

# Host configurations
[[hosts]]
name = "h9"
ip = "10.0.3.100"
cls = "${common.cls_host}"
mac = "00:00:00:02:00:09"
ports = ["00:00:00:02:00:09"]

# Router configurations
[[routers]]
name = "r1"
json_path = "json/simple-router.json"
thrift_port = 9090
bvmodel = "${common.bvmodel}"
cls = "${common.cls_router}"
range = 5
ip_ports = ["10.0.1.1"]
ports = ["00:00:00:01:01:01", "00:00:00:01:01:02", "00:00:00:01:01:03"]

# Switch configurations
[[switches]]
name = "s1"
range = 5
cls = "${common.cls_switch}"
ports = ["00:00:a1:01:01:01", "00:00:a1:02:00:01", "00:00:a1:02:00:02", "00:00:a1:02:00:03"]

# Links configuration
[[links]]
device1 = "h3"
port1 = 1
mac1 = "00:00:00:02:00:03"
device2 = "s1"
port2 = 4
mac2 = "00:00:a1:02:00:03"

```

Running the program requires `sudo` due to how [Mininet](http://mininet.org/) works.

```bash
  sudo python3 topology config/network.toml
```


## Authors

- [@Guilherme Sampaio](https://github.com/gweebg)
- [@Miguel Gomes](https://www.github.com/MayorX500)
- [@Rodrigo Pereira ](https://github.com/eivarin)

## License

[MIT](https://choosealicense.com/licenses/mit/)

