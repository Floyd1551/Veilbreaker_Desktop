"""Offline network and physical planning arithmetic, never measured evidence."""
import math
from decimal import Decimal

from .rf_tools import Field, Tool


TOOLS = (
    Tool('mtu_mss', 'MTU / TCP MSS', 'Find TCP payload size after IP, TCP and tunnel overhead.',
         (Field('mtu', 'Link MTU (bytes)', 1500, 68, 65535),
          Field('ip_header', 'IP header (bytes; IPv4 20, IPv6 40)', 20, 20, 60),
          Field('tcp_header', 'TCP header including options (bytes)', 20, 20, 60),
          Field('encapsulation', 'Outer encapsulation overhead (bytes)', 0, 0, 512)),
         'Effective IP MTU = link MTU − outer encapsulation; TCP MSS = effective IP MTU − IP header − TCP header.',
         'Header sizes and encapsulation are operator inputs. This does not discover path MTU or account for every extension/tunnel header.'),
    Tool('tcp_bdp', 'TCP bandwidth-delay product', 'Estimate in-flight data needed to fill a path.',
         (Field('bandwidth', 'Target path rate (Mbit/s)', 100, .001, 1_000_000),
          Field('rtt', 'Round-trip time (ms)', 40, .001, 1_000_000)),
         'Bandwidth-delay product (bytes) = Mbit/s × 10^6 × RTT ms / (1000 × 8).',
         'Uses the target rate and round-trip time entered. It is not a throughput prediction; loss, congestion, protocol behavior and overhead may reduce throughput.'),
    Tool('fiber_budget', 'Fiber optical power budget', 'Estimate receiver power and margin from specified component losses.',
         (Field('tx_min', 'Minimum transmitter power (dBm)', -3, -60, 40),
          Field('rx_sensitivity', 'Receiver sensitivity (dBm)', -20, -80, 20),
          Field('length', 'Fiber length (km)', 10, 0, 1000),
          Field('attenuation', 'Fiber attenuation (dB/km)', .35, 0, 100),
          Field('connectors', 'Connector count', 2, 0, 1000),
          Field('connector_loss', 'Loss per connector (dB)', .5, 0, 20),
          Field('splices', 'Splice count', 4, 0, 1000),
          Field('splice_loss', 'Loss per splice (dB)', .1, 0, 20),
          Field('reserve', 'Engineering reserve (dB)', 3, 0, 100)),
         'Total loss = length × attenuation + connectors × loss + splices × loss; receive power = minimum transmitter power − total loss; margin = receive power − sensitivity − reserve.',
         'Planning estimate from entered component specifications. It does not measure the installed fiber or verify dispersion, wavelength compatibility or transceiver limits.'),
    Tool('poe_budget', 'PoE source power budget', 'Check source capacity against connected and planned device demand.',
         (Field('supply', 'Total PSE supply budget (W)', 180, 0, 100000),
          Field('allocated', 'Existing committed power (W)', 100, 0, 100000),
          Field('target', 'New device PSE demand (W)', 30, .001, 100000),
          Field('reserve', 'Unallocated reserve (W)', 20, 0, 100000)),
         'Available budget = supply − existing committed power − reserve; headroom = available − new device demand; additional same-demand devices after target = floor(max(0, headroom) / device demand).',
         'Source-side aggregate budget only. Enter PSE-side device demand; per-port limits, standards class negotiation, cable voltage drop and actual PD delivery are not assessed.'),
)

REGISTRY = {tool.key: tool for tool in TOOLS}


def calculate(tool_id, inputs):
    if tool_id not in REGISTRY:
        raise ValueError('Unknown calculator.')
    tool = REGISTRY[tool_id]
    values = {}
    for field in tool.fields:
        raw = inputs.get(field.key)
        try:
            value = float(raw)
        except (TypeError, ValueError, OverflowError):
            raise ValueError(f'{field.label}: enter a number.') from None
        if isinstance(raw, bool) or not math.isfinite(value) or not field.minimum <= value <= field.maximum:
            raise ValueError(f'{field.label}: enter a finite value from {field.minimum:g} to {field.maximum:g}.')
        if field.key in ('mtu', 'ip_header', 'tcp_header', 'encapsulation', 'connectors', 'splices') and not value.is_integer():
            raise ValueError(f'{field.label}: enter a whole number.')
        values[field.key] = value
    v = values
    if tool_id == 'mtu_mss':
        if any(v[name] % 4 for name in ('ip_header', 'tcp_header')):
            raise ValueError('IP and TCP header sizes must be multiples of four bytes.')
        effective = v['mtu'] - v['encapsulation']
        mss = effective - v['ip_header'] - v['tcp_header']
        if mss <= 0:
            raise ValueError('Overhead leaves no TCP payload; increase MTU or correct header and tunnel sizes.')
        outputs = {'Effective IP MTU (bytes)': effective, 'TCP MSS (bytes)': mss}
    elif tool_id == 'tcp_bdp':
        count = v['bandwidth'] * v['rtt'] * 125
        outputs = {'Bandwidth-delay product (bytes)': count, 'Bandwidth-delay product (MiB)': count / 1048576}
    elif tool_id == 'fiber_budget':
        loss = v['length'] * v['attenuation'] + v['connectors'] * v['connector_loss'] + v['splices'] * v['splice_loss']
        receive = v['tx_min'] - loss
        outputs = {'Estimated path loss (dB)': loss, 'Estimated receive power (dBm)': receive,
                   'Margin after reserve (dB)': receive - v['rx_sensitivity'] - v['reserve']}
    else:
        # Use the operator's decimal inputs for the discrete device count. Binary
        # floats can turn exactly 0.3 - 0.1 into 0.199999..., losing one device.
        decimal = {key: Decimal(str(inputs[key])) for key in ('supply', 'allocated', 'reserve', 'target')}
        available = decimal['supply'] - decimal['allocated'] - decimal['reserve']
        headroom = available - decimal['target']
        outputs = {'Available before target (W)': float(available),
                   'Headroom after target (W)': float(headroom),
                   'Additional same-demand devices after target': int(max(Decimal(0), headroom) // decimal['target'])}
    return {'tool_id': tool_id, 'version': 1, 'title': tool.title, 'kind': 'calculated estimate',
            'inputs': values, 'input_labels': {field.key: field.label for field in tool.fields},
            'outputs': outputs, 'method': tool.method, 'limitations': tool.limitations}
