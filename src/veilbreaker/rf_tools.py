"""Offline RF planning calculations. Outputs are estimates, never capture evidence."""
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class Field:
    key: str
    label: str
    default: float
    minimum: float
    maximum: float


@dataclass(frozen=True)
class Tool:
    key: str
    title: str
    purpose: str
    fields: tuple[Field, ...]
    method: str
    limitations: str


FREQUENCY = Field('frequency', 'Frequency (MHz)', 2400, .001, 1_000_000)
TX = (Field('tx_power', 'Transmitter power (dBm)', 20, -300, 100),
      Field('tx_gain', 'Transmit antenna gain (dBi)', 6, -100, 100),
      Field('tx_loss', 'Transmit cable / connector loss (dB)', 1, 0, 300))
TOOLS = (
    Tool('power_dbm', 'Power: dBm to mW / W', 'Convert absolute RF power into linear units.',
         (Field('power', 'Power (dBm)', 20, -300, 100),),
         'mW = 10^(dBm / 10); W = mW / 1000.', 'Power alone does not describe signal quality or receiver performance.'),
    Tool('power_mw', 'Power: mW to dBm / W', 'Convert milliwatts into logarithmic power.',
         (Field('power', 'Power (mW)', 100, 1e-30, 1e10),),
         'dBm = 10 log10(mW); W = mW / 1000.', 'Zero power has no finite dBm representation.'),
    Tool('power_w', 'Power: W to dBm / mW', 'Convert watts into logarithmic power.',
         (Field('power', 'Power (W)', 1, 1e-33, 1e7),),
         'dBm = 10 log10(W × 1000).', 'Zero power has no finite dBm representation.'),
    Tool('wavelength', 'Wavelength', 'Estimate wavelength and ideal quarter-wave length.',
         (FREQUENCY,), 'Wavelength = 299792458 / frequency in Hz.',
         'Vacuum wavelength. Physical antenna length also depends on construction, velocity factor and tuning.'),
    Tool('fspl', 'Free-space path loss', 'Estimate spreading loss between two isotropic antennas.',
         (FREQUENCY, Field('distance', 'Distance (km)', 1, .000001, 100000)),
         'Loss = 20 log10(4π × distance in m × frequency in Hz / 299792458).',
         'Ideal far-field free space only. Excludes terrain, buildings, foliage, weather and multipath. Does not establish LOS.'),
    Tool('eirp', 'EIRP', 'Combine transmitter power, feed loss and antenna gain.', TX,
         'EIRP = transmitter dBm − feed loss dB + antenna gain dBi.',
         'Peak directional estimate. Not a regulatory limit check; gain must be dBi, not dBd.'),
    Tool('link_budget', 'Link budget / fade margin', 'Estimate received power and margin above a chosen sensitivity.',
         TX + (Field('path_loss', 'Path loss (dB)', 100, 0, 500),
               Field('rx_gain', 'Receive antenna gain (dBi)', 6, -100, 100),
               Field('rx_loss', 'Receive cable / connector loss (dB)', 1, 0, 300),
               Field('other_loss', 'Additional loss (dB)', 0, 0, 300),
               Field('sensitivity', 'Receiver sensitivity (dBm)', -90, -300, 100)),
         'Received dBm = EIRP − path loss + receive gain − receive loss − additional loss. Margin = received dBm − sensitivity dBm.',
         'One-way estimate. Positive margin does not guarantee service, throughput or availability. Use sensitivity for the intended bandwidth/rate; include losses only once.'),
)
REGISTRY = {tool.key: tool for tool in TOOLS}


def calculate(tool_id, inputs):
    """Return a detached, JSON-compatible calculation snapshot with validated units."""
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
        values[field.key] = value
    v = values
    if tool_id.startswith('power_'):
        mw = 10 ** (v['power'] / 10) if tool_id == 'power_dbm' else v['power'] * (1000 if tool_id == 'power_w' else 1)
        outputs = {'Power (dBm)': 10 * math.log10(mw), 'Power (mW)': mw, 'Power (W)': mw / 1000}
    elif tool_id == 'wavelength':
        wavelength = 299792458 / (v['frequency'] * 1e6)
        outputs = {'Wavelength (m)': wavelength, 'Quarter wavelength (m)': wavelength / 4}
    elif tool_id == 'fspl':
        loss = 20 * math.log10(4 * math.pi * v['distance'] * 1000 * v['frequency'] * 1e6 / 299792458)
        if loss < 0:
            raise ValueError('Distance is too short for this free-space model at the selected frequency. Check far-field applicability.')
        outputs = {'Free-space path loss (dB)': loss}
    else:
        eirp = v['tx_power'] + v['tx_gain'] - v['tx_loss']
        outputs = {'EIRP (dBm)': eirp}
        if tool_id == 'link_budget':
            received = eirp - v['path_loss'] + v['rx_gain'] - v['rx_loss'] - v['other_loss']
            outputs.update({'Estimated received power (dBm)': received,
                            'Margin above sensitivity (dB)': received - v['sensitivity']})
    return {'tool_id': tool_id, 'version': 1, 'title': tool.title, 'kind': 'calculated estimate',
            'inputs': values, 'input_labels': {f.key: f.label for f in tool.fields},
            'outputs': outputs, 'method': tool.method, 'limitations': tool.limitations}


def format_snapshot(snapshot):
    lines = [snapshot['title'], 'Calculated estimate · calculator version ' + str(snapshot['version']), '', 'Inputs']
    lines += [f"{snapshot['input_labels'][key]}: {value:.8g}" for key, value in snapshot['inputs'].items()]
    lines += ['', 'Results']
    lines += [f'{label}: {value:.8g}' for label, value in snapshot['outputs'].items()]
    lines += ['', 'Method', snapshot['method'], '', 'Interpretation / limitations', snapshot['limitations']]
    return '\n'.join(lines)
