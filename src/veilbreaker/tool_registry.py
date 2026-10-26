"""Offline discovery metadata for tools and references; no calculation state."""
from dataclasses import dataclass
import html
import re

from .field_tools import TOOLS
from .toolbox_reference import REFERENCES


CATEGORIES = ('RF', 'Cellular', 'Wi-Fi', 'Networking', 'Fiber & Power', 'References')


@dataclass(frozen=True)
class ToolRecord:
    record_id: str
    title: str
    category: str
    kind: str
    description: str
    keywords: tuple[str, ...]
    target_id: str

    @property
    def search_text(self):
        return ' '.join((self.title, self.category, self.description, *self.keywords)).casefold()


def _plain_text(markup):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', markup))).strip()


def _slug(value):
    return re.sub(r'[^a-z0-9]+', '-', value.casefold()).strip('-')


def _reference_category(title):
    value = title.casefold()
    if any(term in value for term in ('rsrp', 'rsrq', 'sinr', 'cellular')) or value.startswith('wireless measurements'):
        return 'Cellular'
    if any(term in value for term in ('wi-fi', 'wifi', 'survey coverage', 'das')):
        return 'Wi-Fi'
    if any(term in value for term in ('ipv4', 'ipv6', 'networking', 'ethernet', 'dns', 'dhcp', 'mtu')):
        return 'Networking'
    if any(term in value for term in ('rf ', 'radio', 'propagation', 'fresnel', 'antenna')):
        return 'RF'
    return 'References'


def build_registry(extra=()):
    records = [ToolRecord('calculator:' + tool.key, tool.title,
                          'Networking' if tool.key in ('mtu_mss', 'tcp_bdp') else
                          'Fiber & Power' if tool.key in ('fiber_budget', 'poe_budget') else 'RF', 'calculator', tool.purpose,
                          tuple(field.label for field in tool.fields) + (tool.method, tool.limitations), tool.key)
               for tool in TOOLS]
    records.append(ToolRecord('inspector:subnet', 'IPv4 / IPv6 subnet inspector', 'Networking', 'inspector',
                              'Inspect network, address range, host capacity and prefix semantics offline.',
                              ('CIDR', 'prefix', 'route', 'subnet', 'IPv4', 'IPv6'), 'subnet'))
    records.append(ToolRecord('inspector:cell_channel', 'LTE / NR ARFCN channel inspector', 'Cellular', 'inspector',
                              'Look up channel-derived band candidates and convert NR-ARFCN on the global frequency raster.',
                              ('EARFCN', 'NR ARFCN', 'n77', 'band', 'frequency', 'cellular'), 'cell_channel'))
    records.append(ToolRecord('planner:wifi_channels', 'Wi-Fi channel overlap inspector', 'Wi-Fi', 'planner',
                              'Compare nominal 20 MHz Wi-Fi channels by frequency with a schematic diagram.',
                              ('wifi', '2.4 GHz', '5 GHz', '6 GHz', 'channel', 'overlap', 'frequency'), 'wifi_channels'))
    for title, body in REFERENCES:
        category = _reference_category(title)
        records.append(ToolRecord('reference:' + _slug(title), title, category, 'reference',
                                  _plain_text(body)[:240], ('offline reference',), title))
    records.extend(extra)
    seen = set()
    for record in records:
        if record.record_id in seen:
            raise ValueError('Duplicate tool registry identity: ' + record.record_id)
        if record.category not in CATEGORIES:
            raise ValueError('Unknown tool category: ' + record.category)
        seen.add(record.record_id)
    return tuple(records)


def search_registry(records, query='', category='All'):
    if category != 'All' and category not in CATEGORIES:
        return ()
    tokens = tuple(query.casefold().split())
    return tuple(record for record in records
                 if (category == 'All' or (category == 'References' and record.kind == 'reference')
                     or record.category == category)
                 and all(token in record.search_text for token in tokens))
