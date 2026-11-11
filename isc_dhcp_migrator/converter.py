import jinja2
from pathlib import Path
from typing import Dict, List, Optional
import netaddr
import yaml

from .parser import IscDhcpdConf, IscDhcpdConfParser

PACKAGE_DIR = Path(__file__).resolve().parent

ISC_POLICIES = 'isc_policies'
ISC_OPTIONS = 'isc_options'
JAG_NAME = 'jag-name'
JAG_TYPE = 'jag-type'
LIST = 'list'

POLICIES = 'policies'
V4OPTIONS = 'v4options'
FILTERS = 'filters'
LINKS = 'links'
V4ADDRBINDINGS = 'v4addrbindings'

NAME = 'name'
TYPE = 'type'
VALUE = 'value'
ADDRESS = 'address'
V4POOLS = 'v4pools'
POOL = 'pool'
RANGE = 'range'
HOST = 'host'


class IscToJagConfigConverter:
    DEFAULT_POLICY_MAP = PACKAGE_DIR / 'maps' / 'isc_to_jag_policy_map.yml'
    DEFAULT_OPTION_MAP = PACKAGE_DIR / 'maps' / 'isc_to_jag_option_map.yml'
    DEFAULT_TEMPLATE_DIR = PACKAGE_DIR / 'templates'
    DEFAULT_TEMPLATE_FILE = 'jagornet_dhcpserver_config.yml.j2'

    def __init__(
        self,
        isc_config: IscDhcpdConf,
        policy_map_path: Optional[Path] = None,
        option_map_path: Optional[Path] = None
    ):
        self.isc_config = isc_config
        policy_path = policy_map_path or self.DEFAULT_POLICY_MAP
        option_path = option_map_path or self.DEFAULT_OPTION_MAP

        with open(policy_path, 'r', encoding='utf-8') as f:
            policy_map = yaml.safe_load(f)
            self.isc_policy_map = policy_map.get(ISC_POLICIES, {})

        with open(option_path, 'r', encoding='utf-8') as f:
            option_map = yaml.safe_load(f)
            self.isc_option_map = option_map.get(ISC_OPTIONS, {})

    def map_config(self) -> Dict:
        jag_config = {
            POLICIES: [],
            V4OPTIONS: [],
            FILTERS: [],
            LINKS: []
        }
        self.map_policies(self.isc_config.policies, jag_config[POLICIES])
        self.map_v4options(self.isc_config.options, jag_config[V4OPTIONS])

        # Gather all subnets, including those nested in shared-networks
        all_subnets = list(self.isc_config.subnets)
        for shared_net in self.isc_config.shared_networks:
            for s in shared_net.subnets:
                # Inherit shared-network policies/options if not already defined on the subnet
                for p in shared_net.policies:
                    if not any(sp.name == p.name for sp in s.policies):
                        s.policies.append(p)
                for opt in shared_net.options:
                    if not any(so.name == opt.name for so in s.options):
                        s.options.append(opt)
                all_subnets.append(s)

        self.map_links(all_subnets, jag_config[LINKS])

        # Map global/top-level hosts to their matching subnet links
        if self.isc_config.hosts:
            self.map_global_hosts(self.isc_config.hosts, jag_config[LINKS])

        return jag_config

    def map_policies(self, isc_policies, jag_policies: List[Dict]):
        for isc_policy in isc_policies:
            if isc_policy.name in self.isc_policy_map:
                map_entry = self.isc_policy_map[isc_policy.name]
                jag_policies.append({
                    NAME: map_entry[JAG_NAME],
                    VALUE: isc_policy.value
                })

    def map_v4options(self, isc_options, jag_v4options: List[Dict]):
        for isc_option in isc_options:
            if isc_option.name in self.isc_option_map:
                map_entry = self.isc_option_map[isc_option.name]
                is_list = map_entry.get(LIST, False)
                val = isc_option.value
                if is_list and not isinstance(val, list):
                    val = [val]
                jag_v4options.append({
                    NAME: map_entry[JAG_NAME],
                    TYPE: map_entry[JAG_TYPE],
                    VALUE: val,
                    LIST: is_list
                })

    def map_links(self, isc_subnets, jag_links: List[Dict]):
        for isc_subnet in isc_subnets:
            jag_link = {
                NAME: f'subnet-{isc_subnet.subnet}',
                ADDRESS: isc_subnet.subnet,
                POLICIES: [],
                V4OPTIONS: [],
                V4POOLS: [],
                V4ADDRBINDINGS: []
            }
            self.map_policies(isc_subnet.policies, jag_link[POLICIES])
            self.map_v4options(isc_subnet.options, jag_link[V4OPTIONS])
            self.map_v4pools(isc_subnet.ranges, jag_link[V4POOLS])
            self.map_v4addrbindings(isc_subnet.hosts, jag_link[V4ADDRBINDINGS])
            jag_links.append(jag_link)

    def map_v4pools(self, isc_ranges, jag_pools: List[Dict]):
        for isc_range in isc_ranges:
            jag_pool = {
                RANGE: isc_range,
                POLICIES: [],
                V4OPTIONS: []
            }
            jag_pools.append(jag_pool)

    def map_v4addrbindings(self, isc_hosts, jag_bindings: List[Dict]):
        for isc_host in isc_hosts:
            if not isc_host.ipaddr:
                continue
            jag_binding = {
                'ipaddr': isc_host.ipaddr,
                'hwaddr': isc_host.hwaddr or '',
                POLICIES: [],
                V4OPTIONS: []
            }
            self.map_policies(isc_host.policies, jag_binding[POLICIES])
            self.map_v4options(isc_host.options, jag_binding[V4OPTIONS])
            jag_bindings.append(jag_binding)

    def map_global_hosts(self, isc_hosts, jag_links: List[Dict]):
        """Assign global host statements to the link whose subnet contains their IP."""
        for isc_host in isc_hosts:
            if not isc_host.ipaddr:
                continue

            target_link = None
            try:
                host_ip = netaddr.IPAddress(isc_host.ipaddr)
                for link in jag_links:
                    link_net = link.get(ADDRESS)
                    if isinstance(link_net, netaddr.IPNetwork) and host_ip in link_net:
                        target_link = link
                        break
            except Exception:
                pass

            if target_link is None and jag_links:
                # If no direct subnet matched, attach to first link
                target_link = jag_links[0]

            if target_link is not None:
                jag_binding = {
                    'ipaddr': isc_host.ipaddr,
                    'hwaddr': isc_host.hwaddr or '',
                    POLICIES: [],
                    V4OPTIONS: []
                }
                self.map_policies(isc_host.policies, jag_binding[POLICIES])
                self.map_v4options(isc_host.options, jag_binding[V4OPTIONS])
                target_link[V4ADDRBINDINGS].append(jag_binding)

    def render(self, template_dir: Optional[Path] = None, template_name: Optional[str] = None) -> str:
        t_dir = template_dir or self.DEFAULT_TEMPLATE_DIR
        t_name = template_name or self.DEFAULT_TEMPLATE_FILE

        jag_config = self.map_config()

        fsloader = jinja2.FileSystemLoader(searchpath=str(t_dir))
        env = jinja2.Environment(loader=fsloader)
        template = env.get_template(t_name)
        return template.render(
            global_policies=jag_config[POLICIES],
            global_v4options=jag_config[V4OPTIONS],
            global_links=jag_config[LINKS]
        )
