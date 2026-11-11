import unittest
from pathlib import Path
import yaml
import netaddr

from isc_dhcp_migrator.parser import IscDhcpdConfParser
from isc_dhcp_migrator.converter import IscToJagConfigConverter

TESTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = TESTS_DIR.parent
SAMPLE_CONF = REPO_ROOT / 'examples' / 'dhcpd.conf.sample'


class TestIscDhcpMigrator(unittest.TestCase):

    def setUp(self):
        self.parser = IscDhcpdConfParser(str(SAMPLE_CONF))
        self.isc_conf = self.parser.parse()
        self.converter = IscToJagConfigConverter(self.isc_conf)

    def test_parser_extracts_elements(self):
        self.assertGreater(len(self.isc_conf.subnets), 0)
        self.assertGreater(len(self.isc_conf.policies), 0)
        self.assertGreater(len(self.isc_conf.options), 0)
        self.assertGreater(len(self.isc_conf.shared_networks), 0)

    def test_shared_network_subnets_migrated(self):
        jag_config = self.converter.map_config()
        # Ensure subnets from shared-network 224-29 are included
        link_addresses = [str(link['address']) for link in jag_config['links']]
        self.assertIn('10.17.224.0/24', link_addresses)
        self.assertIn('10.0.29.0/24', link_addresses)

    def test_dynamic_bootp_range_migrated(self):
        # 10.254.239.32/27 has dynamic-bootp range 10.254.239.40 10.254.239.60
        jag_config = self.converter.map_config()
        target_link = None
        for link in jag_config['links']:
            if str(link['address']) == '10.254.239.32/27':
                target_link = link
                break
        self.assertIsNotNone(target_link)
        self.assertGreater(len(target_link['v4pools']), 0)
        self.assertEqual(str(target_link['v4pools'][0]['range']), '10.254.239.40-10.254.239.60')

    def test_global_host_mapping(self):
        # Sample contains fixed-address 10.5.6.7 in subnet 10.5.6.0
        jag_config = self.converter.map_config()
        target_link = None
        for link in jag_config['links']:
            if str(link['address']) == '10.5.6.0/24':
                target_link = link
                break
        self.assertIsNotNone(target_link)
        self.assertGreater(len(target_link['v4addrbindings']), 0)
        binding = target_link['v4addrbindings'][0]
        self.assertEqual(binding['ipaddr'], '10.5.6.7')
        self.assertEqual(binding['hwaddr'], '0a:1b:2c:3d:4e:5f')

    def test_render_valid_yaml(self):
        rendered = self.converter.render()
        parsed = yaml.safe_load(rendered)
        self.assertIn('links', parsed)
        self.assertIn('policies', parsed)
        self.assertIn('v4ConfigOptions', parsed)

        # Check v4AddrBindings tag name (not v4AddressBindings)
        found_bindings = False
        for link in parsed['links']['linkList']:
            if 'v4AddrBindings' in link:
                found_bindings = True
                self.assertIn('bindingList', link['v4AddrBindings'])
        self.assertTrue(found_bindings, "v4AddrBindings should be present in at least one link")


if __name__ == '__main__':
    unittest.main()
