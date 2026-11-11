import argparse
import netaddr
import pprint
import re

SUBNET = 'subnet'
RANGE = 'range'
SHARED_NETWORK = 'shared_network'
NAME = 'name'
TYPE = 'type'
VALUE = 'value'
ADDRESS = 'address'
NETMASK = 'netmask'
HOST = 'host'
POOL = 'pool'

CLOSE_CURLY = '}'
CLOSE_CURLY_SEMICOLON = '};'

TYPE_BOOLEAN = 'boolean'
TYPE_DATA = 'data'
TYPE_TEXT = 'text'
TYPE_INT = 'int'
TYPE_IPADDR = 'ipaddr'
TYPE_ARRAY_OF = 'array_of '

BOOLEAN_TRUE_STRINGS = ['true', 'yes', 'on']
BOOLEAN_FALSE_STRINGS = ['false', 'no', 'off']


class IscDhcpdConf():
    def __init__(self):
        self.option_defs = []
        self.policies = []
        self.options = []
        self.subnets = []
        self.shared_networks = []
        self.hosts = []

    def __repr__(self):
        return str(vars(self))


class IscDhcpdPolicy():
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def __repr__(self):
        return str(vars(self))


class IscDhcpdOption():
    def __init__(self, name, type, value):
        self.name = name
        self.type = type
        self.value = value

    def __repr__(self):
        return str(vars(self))


class IscDhcpdSubnet():
    def __init__(self, addr, mask):
        self.subnet = netaddr.IPNetwork(f'{addr}/{mask}')
        self.policies = []
        self.options = []
        self.ranges = []
        self.hosts = []

    def __repr__(self):
        return str(vars(self))


class IscDhcpdSharedNetwork():
    def __init__(self, name):
        self.name = name
        self.policies = []
        self.options = []
        self.subnets = []

    def __repr__(self):
        return str(vars(self))


class IscDhcpdHost():
    def __init__(self, name):
        self.name = name
        self.ipaddr = None
        self.hwtype = None
        self.hwaddr = None
        self.policies = []
        self.options = []

    def __repr__(self):
        return str(vars(self))


class IscDhcpdConfParser():
    RX_OPTION = re.compile(r'^option\s+(?P<name>\S+)\s+(?P<value>.+)\s*;')
    RX_SUBNET = re.compile(r'^subnet\s+(?P<address>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+netmask\s+(?P<netmask>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*{\s*')
    RX_RANGE = re.compile(r'^range\s+(?:dynamic-bootp\s+)?(?P<low>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+(?P<high>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s*;')
    RX_HOST = re.compile(r'^host\s+(?P<name>\S+)\s*{\s*')
    RX_HARDWARE = re.compile(r'^hardware\s+(?P<hwtype>\S+)\s+(?P<hwaddr>[0-9a-fA-F]{1,2}\:[0-9a-fA-F]{1,2}\:[0-9a-fA-F]{1,2}\:[0-9a-fA-F]{1,2}\:[0-9a-fA-F]{1,2}\:[0-9a-fA-F]{1,2})\s*;')
    RX_FIXED_ADDRESS = re.compile(r'^fixed-address\s+(?P<address>[^;]+)\s*;')
    RX_SHARED_NETWORK = re.compile(r'^shared-network\s+(?P<name>\S+)\s*{\s*')
    RX_POLICY = re.compile(r'^(?P<name>\S+)\s+(?P<value>.+)\s*;')
    RX_DIRECTIVE = re.compile(r'^(?P<name>\S+)\s*;')

    def __init__(self, filepath):
        self.filepath = filepath
        self.conffile = None
        self.line = None
        self.confobj = None

    def parse(self) -> IscDhcpdConf:
        with open(self.filepath, 'r', encoding='utf-8', errors='replace') as f:
            self.conffile = f
            self.line = None
            self.confobj = IscDhcpdConf()
            self.parse_conf()
        return self.confobj

    @staticmethod
    def strip_comment(line: str) -> str:
        """Strip inline comments while preserving comments inside quotes."""
        in_quote = False
        quote_char = None
        for i, char in enumerate(line):
            if char in ('"', "'"):
                if not in_quote:
                    in_quote = True
                    quote_char = char
                elif quote_char == char:
                    in_quote = False
            elif char == '#' and not in_quote:
                return line[:i]
        return line

    def read_next_line(self) -> bool:
        while True:
            raw_line = self.conffile.readline()
            if not raw_line:
                self.line = None
                return False
            stripped = self.strip_comment(raw_line).strip()
            if stripped:
                self.line = stripped
                return True

    def parse_conf(self):
        while self.read_next_line():
            if match := self.RX_OPTION.search(self.line):
                option = self.build_option(match)
                self.confobj.options.append(option)
            elif match := self.RX_SUBNET.search(self.line):
                addr = match.group(ADDRESS)
                mask = match.group(NETMASK)
                subnet = self.parse_subnet(addr, mask)
                self.confobj.subnets.append(subnet)
            elif match := self.RX_SHARED_NETWORK.search(self.line):
                name = match.group(NAME)
                shared_network = self.parse_shared_network(name)
                self.confobj.shared_networks.append(shared_network)
            elif match := self.RX_HOST.search(self.line):
                name = match.group(NAME)
                host = self.parse_host(name)
                self.confobj.hosts.append(host)
            elif match := self.RX_POLICY.search(self.line):
                policy = self.build_policy(match)
                self.confobj.policies.append(policy)
            elif match := self.RX_DIRECTIVE.search(self.line):
                directive = self.build_directive(match)
                self.confobj.policies.append(directive)

    def parse_host(self, name) -> IscDhcpdHost:
        host = IscDhcpdHost(name)
        done = False
        while not done and self.read_next_line():
            if match := self.RX_HARDWARE.search(self.line):
                host.hwtype = match.group('hwtype')
                host.hwaddr = match.group('hwaddr')
            elif match := self.RX_FIXED_ADDRESS.search(self.line):
                host.ipaddr = match.group(ADDRESS).strip()
            elif match := self.RX_OPTION.search(self.line):
                option = self.build_option(match)
                host.options.append(option)
            elif match := self.RX_POLICY.search(self.line):
                policy = self.build_policy(match)
                host.policies.append(policy)
            elif match := self.RX_DIRECTIVE.search(self.line):
                directive = self.build_directive(match)
                host.policies.append(directive)

            if self.line.endswith(CLOSE_CURLY) or self.line.endswith(CLOSE_CURLY_SEMICOLON):
                done = True
        return host

    def parse_subnet(self, addr, mask) -> IscDhcpdSubnet:
        subnet = IscDhcpdSubnet(addr, mask)
        done = False
        while not done and self.read_next_line():
            if match := self.RX_OPTION.search(self.line):
                option = self.build_option(match)
                subnet.options.append(option)
            elif match := self.RX_RANGE.search(self.line):
                low = match.group('low')
                high = match.group('high')
                ip_range = netaddr.IPRange(low, high)
                subnet.ranges.append(ip_range)
            elif match := self.RX_HOST.search(self.line):
                name = match.group(NAME)
                host = self.parse_host(name)
                subnet.hosts.append(host)
            elif match := self.RX_POLICY.search(self.line):
                policy = self.build_policy(match)
                subnet.policies.append(policy)
            elif match := self.RX_DIRECTIVE.search(self.line):
                policy = self.build_directive(match)
                subnet.policies.append(policy)

            if self.line.endswith(CLOSE_CURLY) or self.line.endswith(CLOSE_CURLY_SEMICOLON):
                done = True
        return subnet

    def parse_shared_network(self, name) -> IscDhcpdSharedNetwork:
        sharednet = IscDhcpdSharedNetwork(name)
        done = False
        while not done and self.read_next_line():
            if match := self.RX_OPTION.search(self.line):
                option = self.build_option(match)
                sharednet.options.append(option)
            elif match := self.RX_SUBNET.search(self.line):
                addr = match.group(ADDRESS)
                mask = match.group(NETMASK)
                subnet = self.parse_subnet(addr, mask)
                sharednet.subnets.append(subnet)
                continue
            elif match := self.RX_POLICY.search(self.line):
                policy = self.build_policy(match)
                sharednet.policies.append(policy)
            elif match := self.RX_DIRECTIVE.search(self.line):
                directive = self.build_directive(match)
                sharednet.policies.append(directive)

            if self.line.endswith(CLOSE_CURLY) or self.line.endswith(CLOSE_CURLY_SEMICOLON):
                done = True
        return sharednet

    def build_directive(self, match):
        name = match.group(NAME)
        return IscDhcpdPolicy(name, True)

    def build_policy(self, match):
        name = match.group(NAME)
        value = match.group(VALUE)
        return IscDhcpdPolicy(name, value)

    def build_option(self, match):
        name = match.group(NAME)
        val = match.group(VALUE)

        # first check for data string (colon separated hex string)
        x = self.parse_hex(val)
        if x:
            return IscDhcpdOption(name, TYPE_DATA, x)

        # check for a list of double-quoted strings
        texts = [s.strip() for s in re.split(r',(?=\s*")', val)]
        if len(texts) > 1:
            return IscDhcpdOption(name, TYPE_ARRAY_OF + TYPE_TEXT, texts)

        t = texts[0]
        vals = [s.strip() for s in t.split(',')]
        if vals[0].isdigit():
            type = self.build_type('int', vals)
            value = self.build_value(vals)
        else:
            b = self.parse_boolean(vals[0])
            if b is not None:
                type = self.build_type(TYPE_BOOLEAN, vals)
                value = self.build_value(vals)
            else:
                ip = self.parse_ipaddress(vals[0])
                if ip:
                    type = self.build_type(TYPE_IPADDR, vals)
                    value = self.build_value(vals)
                else:
                    type = self.build_type(TYPE_TEXT, vals)
                    value = self.build_value(vals)

        return IscDhcpdOption(name, type, value)

    def build_type(self, type, vals):
        prefix = ''
        if len(vals) > 1:
            prefix = TYPE_ARRAY_OF
        return prefix + type

    def build_value(self, vals):
        if len(vals) == 1:
            return vals[0]
        value_list = []
        for v in vals:
            if v.isdigit():
                value_list.append(int(v))
            else:
                b = self.parse_boolean(v)
                if b is not None:
                    value_list.append(b)
                else:
                    ip = self.parse_ipaddress(v)
                    if ip:
                        value_list.append(ip)
                    else:
                        value_list.append(v)
        return value_list

    def parse_hex(self, val):
        try:
            return bytes.fromhex(val.replace(':', ''))
        except Exception:
            return None

    def parse_boolean(self, val):
        if val.lower() in BOOLEAN_TRUE_STRINGS:
            return True
        elif val.lower() in BOOLEAN_FALSE_STRINGS:
            return False
        return None

    def parse_ipaddress(self, val):
        try:
            return netaddr.IPAddress(val)
        except Exception:
            return None


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Parse ISC DHCP configuration')
    argparser.add_argument('filename', nargs='?', default='dhcpd.conf')
    args = argparser.parse_args()

    confparser = IscDhcpdConfParser(args.filename)
    conf = confparser.parse()
    pprint.pprint(conf)
