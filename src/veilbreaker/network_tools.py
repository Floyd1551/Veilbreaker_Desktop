"""Bounded offline address arithmetic; never enumerate or probe a subnet."""
import ipaddress


def inspect_subnet(value):
    if not isinstance(value, str) or len(value) > 128 or '/' not in value or '%' in value:
        raise ValueError('Enter an IPv4 or IPv6 address with a prefix, such as 192.168.1.20/24.')
    try:
        interface = ipaddress.ip_interface(value.strip())
    except ValueError:
        raise ValueError('Invalid address or prefix length.') from None
    network = interface.network
    result = {'Address': str(interface.ip), 'Network': str(network), 'IP version': str(network.version),
              'Netmask': str(network.netmask), 'Address count': str(network.num_addresses),
              'First address': str(network.network_address), 'Last address': str(network.broadcast_address)}
    if network.version == 4:
        usable = network.num_addresses if network.prefixlen >= 31 else network.num_addresses - 2
        first = network.network_address if network.prefixlen >= 31 else network.network_address + 1
        last = network.broadcast_address if network.prefixlen >= 31 else network.broadcast_address - 1
        result['Usable address count'] = str(usable)
        result['Host range'] = f'{first} – {last}'
        if network.prefixlen < 31:
            result['Broadcast'] = str(network.broadcast_address)
        result['Interpretation'] = ('/31 assumes a point-to-point link (RFC 3021).' if network.prefixlen == 31 else
                                    '/32 identifies one address.' if network.prefixlen == 32 else
                                    'Conventional subnet host count excludes network and broadcast. This does not establish assignability or reachability.')
    else:
        result['Interpretation'] = 'IPv6 has no broadcast address. Total address count is not a usable-host claim; address roles and deployment policy still apply.'
    return result
