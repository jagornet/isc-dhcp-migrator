# ISC DHCP to Jagornet DHCP Migrator

A migration utility to automatically convert legacy ISC DHCP (`dhcpd.conf`) configurations into modern YAML configuration files for the [Jagornet DHCP Server](https://github.com/jagornet/dhcp).

With the deprecation and end-of-life of ISC DHCP, network administrators require a reliable, automated path to modernize their DHCP infrastructure. `isc-dhcp-migrator` parses your existing `dhcpd.conf` and maps statements, options, subnets, pools, and static host reservations into Jagornet DHCP Server YAML configuration format.

---

## Features

- **Subnet & Shared Network Mapping:** Converts `subnet` and `shared-network` declarations into Jagornet client `links` with proper network prefix addresses.
- **Address Pools:** Migrates standard and `dynamic-bootp` address `range` declarations into `v4AddrPools`.
- **Static Host Reservations:** Maps both subnet-level and global `host` declarations (with MAC address and `fixed-address`) to their corresponding link `v4AddrBindings`.
- **Policies & Lease Times:** Automatically maps `default-lease-time`, `max-lease-time`, `filename`, `server-name`, and `ping-timeout` to Jagornet server policies.
- **Standard DHCPv4 Options:** Translates standard ISC options to Jagornet `v4ConfigOptions`:
  - `subnet-mask` $\rightarrow$ `v4SubnetMaskOption`
  - `routers` $\rightarrow$ `v4RoutersOption`
  - `domain-name-servers` $\rightarrow$ `v4DomainServersOption`
  - `domain-name` $\rightarrow$ `v4DomainNameOption`
  - `time-offset` $\rightarrow$ `v4TimeOffsetOption`
  - `time-servers` / `ntp-servers` $\rightarrow$ `v4TimeServersOption`
  - `netbios-name-servers` $\rightarrow$ `v4NetbiosNameServersOption`
  - `netbios-node-type` $\rightarrow$ `v4NetbiosNodeTypeOption`
  - `tftp-server-name` $\rightarrow$ `v4TftpServerNameOption`
  - `bootfile-name` $\rightarrow$ `v4BootFileNameOption`
- **Extensible Mapping:** Option and policy mappings are defined in YAML map files, making it easy to add or customize option translations.

---

## Installation

### Prerequisites
- Python 3.8 or later

### Install from source
```bash
git clone https://github.com/jagornet/isc-dhcp-migrator.git
cd isc-dhcp-migrator
pip install -r requirements.txt
pip install -e .
```

---

## Quick Start

### Command Line Interface

Convert an ISC `dhcpd.conf` to a Jagornet YAML configuration:

```bash
# Direct output to a file
isc-dhcp-migrator /etc/dhcp/dhcpd.conf -o jagornet-dhcpserver-config.yml

# Or pipe to stdout
isc-dhcp-migrator /etc/dhcp/dhcpd.conf > jagornet-dhcpserver-config.yml

# Validate generated YAML and print summary to stderr
isc-dhcp-migrator /etc/dhcp/dhcpd.conf -o jagornet-dhcpserver-config.yml --validate --summary
```

You can also run directly without installing:
```bash
python migrate.py /etc/dhcp/dhcpd.conf -o jagornet-dhcpserver-config.yml
```

### Python API

```python
from isc_dhcp_migrator import IscDhcpdConfParser, IscToJagConfigConverter

# Parse ISC dhcpd.conf
parser = IscDhcpdConfParser("/etc/dhcp/dhcpd.conf")
isc_conf = parser.parse()

# Convert and render Jagornet YAML configuration
converter = IscToJagConfigConverter(isc_conf)
jagornet_yaml = converter.render()

print(jagornet_yaml)
```

---

## Running Tests

To run the automated test suite:

```bash
python -m unittest discover tests
```

---

## About Jagornet DHCP

[Jagornet DHCP](https://github.com/jagornet/dhcp) is an open-source, standards-compliant, high-performance DHCPv4 and DHCPv6 server built on Java and Netty. It supports high availability clustering, REST APIs, dynamic DNS updates, and flexible configuration in XML, JSON, or YAML.

- **GitHub:** [https://github.com/jagornet/dhcp](https://github.com/jagornet/dhcp)
- **Website:** [https://jagornet.com](https://jagornet.com)

---

## License

This project is licensed under the Mozilla Public License, v. 2.0 (MPL-2.0).
