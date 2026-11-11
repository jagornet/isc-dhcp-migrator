import argparse
import sys
from pathlib import Path
import yaml

from .parser import IscDhcpdConfParser
from .converter import IscToJagConfigConverter


def main():
    parser = argparse.ArgumentParser(
        description='Migrate ISC DHCP configuration (dhcpd.conf) to Jagornet DHCP server configuration (YAML).'
    )
    parser.add_argument(
        'config_file',
        nargs='?',
        default='dhcpd.conf',
        help='Path to the ISC dhcpd.conf file (default: dhcpd.conf)'
    )
    parser.add_argument(
        '-o', '--output',
        dest='output_file',
        help='Output path for the generated Jagornet YAML configuration file (default: stdout)'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate generated YAML with PyYAML before saving or outputting'
    )
    parser.add_argument(
        '-s', '--summary',
        action='store_true',
        help='Print migration summary to stderr'
    )

    args = parser.parse_args()

    input_path = Path(args.config_file)
    if not input_path.exists():
        sys.stderr.write(f"Error: input file '{args.config_file}' not found.\n")
        sys.exit(1)

    try:
        confparser = IscDhcpdConfParser(str(input_path))
        isc_config = confparser.parse()
    except Exception as e:
        sys.stderr.write(f"Error parsing ISC DHCP configuration: {e}\n")
        sys.exit(2)

    try:
        converter = IscToJagConfigConverter(isc_config)
        rendered_yaml = converter.render()
    except Exception as e:
        sys.stderr.write(f"Error converting configuration: {e}\n")
        sys.exit(3)

    if args.validate:
        try:
            yaml.safe_load(rendered_yaml)
            sys.stderr.write("Validation: Generated YAML is valid.\n")
        except Exception as e:
            sys.stderr.write(f"Validation Error: Generated YAML could not be parsed: {e}\n")
            sys.exit(4)

    if args.summary or args.output_file:
        jag_config = converter.map_config()
        num_links = len(jag_config.get('links', []))
        total_pools = sum(len(l.get('v4pools', [])) for l in jag_config.get('links', []))
        total_bindings = sum(len(l.get('v4addrbindings', [])) for l in jag_config.get('links', []))
        sys.stderr.write(
            f"Successfully processed {args.config_file}:\n"
            f"  - Subnets/Links: {num_links}\n"
            f"  - Address Pools: {total_pools}\n"
            f"  - Static Bindings: {total_bindings}\n"
            f"  - Global Policies: {len(jag_config.get('policies', []))}\n"
            f"  - Global Options: {len(jag_config.get('v4options', []))}\n"
        )

    if args.output_file:
        out_path = Path(args.output_file)
        try:
            out_path.write_text(rendered_yaml, encoding='utf-8')
            sys.stderr.write(f"Saved configuration to: {args.output_file}\n")
        except Exception as e:
            sys.stderr.write(f"Error writing output file: {e}\n")
            sys.exit(5)
    else:
        sys.stdout.write(rendered_yaml)
        if not rendered_yaml.endswith('\n'):
            sys.stdout.write('\n')


if __name__ == '__main__':
    main()
