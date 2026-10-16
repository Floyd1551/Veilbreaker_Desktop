"""Presentation labels only: persisted collector IDs remain unchanged."""
import re

SOURCES = {
    'windows_network': 'Network', 'linux_network': 'Network', 'generic_network': 'Network',
    'windows_wifi': 'Wi-Fi', 'wifi': 'Wi-Fi', 'system': 'Computer',
    'cellular_modem': 'Cellular modem', 'starlink': 'Starlink', 'gpsd': 'GPS',
    'active_network': 'Connectivity tests', 'iperf3': 'Throughput test',
    'hackrf': 'SDR · HackRF', 'guided_path': 'Network path test',
    'guided_pmtu': 'Packet size test', 'imported_metrics': 'Imported measurements',
    'android_usb': 'Android phone · USB', 'android_input': 'Android phone · Saved capture',
    'android_import': 'Android phone · Imported capture', 'starting': 'Preparing test',
}
STATES = {'collected':'Collected', 'no_data':'No data', 'partial':'Incomplete',
          'error':'Failed', 'running':'Collecting', 'complete':'Complete',
          'interrupted':'Interrupted', 'not_run':'Not run', 'planned':'Planned'}


def source_label(value):
    return SOURCES.get(value, str(value).replace('_', ' ').capitalize())


def status_label(value):
    return STATES.get(value, str(value).replace('_', ' ').capitalize())


def readable_text(value):
    # Whole technical IDs or collector prefixes only; do not rewrite ordinary prose.
    ids = '|'.join(re.escape(key) for key in SOURCES if '_' in key)
    prefixes = '|'.join(re.escape(key) for key in SOURCES if '_' not in key)
    pattern = r'(?<![\w/\\.])(?:(?:' + ids + r')(?![\w/\\]|\.[A-Za-z0-9])|(?:' + prefixes + r')(?=:))'
    return re.sub(pattern, lambda match: SOURCES[match.group(0)], str(value))
