"""Offline RF planning calculations. Outputs are estimates, never capture evidence."""
from dataclasses import dataclass
import math
from .terrain_profile import assess_profile


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
PATH = (Field('distance', 'Total path length (km)', 1, .000001, 100),
        Field('position', 'Distance from first endpoint (km)', .5, .0000001, 100))
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
    Tool('fresnel', 'Fresnel clearance', 'Find the first Fresnel zone radius at a point along a path.',
         (FREQUENCY,) + PATH,
         'Radius = sqrt(wavelength × d1 × d2 / (d1 + d2)); clearance guide = 0.6 × radius.',
         'Paraxial radius approximation around the direct ray, requiring distances large relative to wavelength. No obstacle heights are supplied; this does not establish clearance or LOS. Uses the same geometry as the terrain engine.'),
    Tool('curvature', 'Earth curvature / bulge', 'Compare geometric and 4/3 effective Earth bulge at a path point.',
         PATH, 'Bulge = d1 × d2 / (2 × k × Earth radius); radius = 6371008.8 m.',
         'Small-angle path approximation, limited to 100 km. k=1 is geometric; k=4/3 is an explicit refraction assumption, not observed weather. Terrain and obstacles are excluded.'),
    Tool('noise', 'Thermal noise floor', 'Estimate thermal and input-referred receiver noise for a bandwidth.',
         (Field('bandwidth', 'Noise bandwidth (MHz)', 20, .000001, 100000),
          Field('temperature', 'Source temperature (K)', 290, 1, 10000),
          Field('noise_figure', 'Receiver noise figure (dB)', 5, 0, 100)),
         'Thermal noise = 10 log10(kBTB × 1000) dBm, kB = 1.380649e-23 J/K. Receiver equivalent noise temperature Te = 290 × (10^(NF/10) − 1) K; input-referred noise uses T + Te.',
         'Classical thermal model, excluding interference, receiver gain and implementation losses. Noise figure is referenced to 290 K. Use equivalent noise bandwidth; this is not a measured SDR noise floor.'),
    Tool('cable_loss', 'Cable / feed loss', 'Estimate feed loss using a cable specification at your operating frequency.',
         (Field('length', 'Cable length (m)', 10, 0, 100000),
          Field('attenuation', 'Cable attenuation (dB / 100 m)', 12, 0, 10000),
          Field('connector_loss', 'Total connector / adapter loss (dB)', 1, 0, 300)),
         'Total loss = length / 100 × specified attenuation + connector loss. Delivered power percent = 100 × 10^(−loss/10).',
         'Enter manufacturer attenuation for the operating frequency. Excludes mismatch, damage, temperature variation and unspecified connectors. Do not add this feed loss twice in a link budget.'),
    Tool('return_loss', 'Return loss / VSWR', 'Interpret a measured or specified positive return loss as reflection and mismatch.',
         (Field('return_loss', 'Return loss (dB; positive)', 20, .01, 120),),
         '|Γ| = 10^(−RL/20); reflected power fraction = |Γ|²; VSWR = (1+|Γ|)/(1−|Γ|); mismatch loss = −10 log10(1−|Γ|²).',
         'A scalar magnitude at one frequency only. This does not measure an antenna, include feedline effects, reveal reflection phase, or establish delivered power at a remote load. An ideal match has infinite return loss and is outside the finite input range. Reference: Keysight application note 5952-3706.'),
    Tool('cascade_nf', 'Two-stage cascaded noise figure', 'Estimate receiver-chain noise figure from two specified stages.',
         (Field('nf1', 'First-stage noise figure (dB)', 2, 0, 50),
          Field('gain1', 'First-stage available gain (dB)', 15, -60, 100),
          Field('nf2', 'Second-stage noise figure (dB)', 8, 0, 50)),
         'F_total = F1 + (F2−1)/G1, with F1/F2 and available G1 converted from dB to linear ratios; NF_total = 10 log10(F_total).',
         'Two matched stages with conventional noise-factor definitions referenced to 290 K. Mixer sideband conventions, impedance mismatch, compression, bandwidth dependence and later stages are excluded. Reference: Analog Devices MT-006.'),
    Tool('vswr', 'VSWR to return loss / reflection', 'Convert a voltage standing wave ratio into return loss and reflected power.',
         (Field('vswr', 'VSWR (ratio to 1)', 2, 1, 10000),),
         '|Γ| = (VSWR − 1)/(VSWR + 1); return loss = −20 log10(|Γ|); reflected power = |Γ|²; mismatch loss = −10 log10(1 − |Γ|²).',
         'Scalar magnitude at one frequency. This does not measure an antenna or reveal reflection phase. Ideal VSWR 1:1 has infinite return loss. Source: Keysight application note 5952-3706, https://go.keysight.com/us/en/assets/7018-06829/application-notes/5952-3706.pdf.'),
    Tool('aperture', 'Antenna gain / effective aperture', 'Estimate effective receiving aperture from antenna gain and frequency.',
         (FREQUENCY, Field('gain', 'Antenna gain (dBi)', 0, -100, 100)),
         'Effective aperture = linear gain × vacuum wavelength² / (4π), with gain = 10^(dBi/10).',
         'Assumes a far-field plane wave, matched polarization and gain in the incoming direction. Effective aperture is not physical antenna area and this does not measure an antenna. Source: NIST SP 300-4, https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nbsspecialpublication300v4.pdf.'),
    Tool('polarization', 'Linear polarization mismatch', 'Estimate loss from an angle between ideal linear polarizations.',
         (Field('angle', 'Polarization angle difference (degrees)', 0, 0, 90),),
         'Relative power = cos²(angle); polarization mismatch loss = −10 log10(relative power).',
         'Ideal linearly polarized plane waves only. Excludes depolarization, reflections, antenna cross-polar response and circular or elliptical polarization. A 90° mismatch has infinite ideal loss, not a finite measured value. Source: Naval Postgraduate School, https://faculty.nps.edu/jenn/EC3630/Systems_and_Noise%28v1.5.4%29.pdf.'),
    Tool('receiver_sensitivity', 'Receiver sensitivity estimate', 'Estimate a receiver input threshold from noise and an assumed required SNR.',
         (Field('bandwidth', 'Equivalent noise bandwidth (MHz)', 20, .000001, 100000),
          Field('temperature', 'Source temperature (K)', 290, 1, 10000),
          Field('noise_figure', 'Receiver noise figure (dB)', 5, 0, 100),
          Field('required_snr', 'Required output SNR (dB)', 10, -100, 100),
          Field('implementation_loss', 'Additional implementation margin (dB)', 2, 0, 100)),
         'Equivalent noise temperature Te = 290 × (10^(NF/10) − 1) K; input-referred noise = 10 log10(kB × (T + Te) × B × 1000) dBm. Sensitivity estimate = input-referred noise + required SNR + implementation margin.',
         'Not a measured receiver sensitivity or a guarantee of connectivity. Enter equivalent noise bandwidth and the required output SNR for the specified waveform and error rate. Do not double-count implementation loss already included in the SNR. Excludes interference, mismatch, compression and gain variation. Source: Analog Devices, https://www.analog.com/en/resources/analog-dialogue/articles/receiver-design-simplified-by-if-digitizing-subsystem.html.'),
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
    limitations = tool.limitations
    result_notes = []
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
    elif tool_id in ('fresnel', 'curvature'):
        if not 0 < v['position'] < v['distance']:
            raise ValueError('Point distance must be greater than zero and less than the total path length.')
        distances = [0, v['position'] * 1000, v['distance'] * 1000]
        profile = assess_profile(distances, [0, 0, 0], 0, 0, v.get('frequency'))
        if tool_id == 'fresnel':
            radius = profile['fresnel_radius_m'][1]
            outputs = {'First Fresnel radius (m)': radius, '60% clearance radius (m)': .6 * radius}
            # Compare with the first Fresnel ellipsoid at this axial position.
            wavelength = 299792458 / (v['frequency'] * 1e6)
            length, position = distances[-1], distances[1]
            major = (length + wavelength / 2) / 2
            minor_squared = wavelength * length / 4 + wavelength ** 2 / 16
            axial = position - length / 2
            exact = math.sqrt(minor_squared * ((major - axial) / major) * ((major + axial) / major))
            if abs(radius - exact) / exact > .01:
                limitations = ('WARNING: This approximation differs from exact first-ellipsoid geometry by more than 1% at these inputs. '
                               'Do not use this result for clearance decisions; the path is too short relative to wavelength at this position. ' + limitations)
        else:
            refracted = assess_profile(distances, [0, 0, 0], 0, 0, earth_factor=4/3)
            outputs = {'Geometric Earth bulge (m)': profile['terrain_effective_m'][1],
                       '4/3 effective Earth bulge (m)': refracted['terrain_effective_m'][1]}
    elif tool_id in ('noise', 'receiver_sensitivity'):
        scale = 1.380649e-23 * v['bandwidth'] * 1e6 * 1000
        equivalent_temperature = 290 * (10 ** (v['noise_figure'] / 10) - 1)
        outputs = {'Thermal noise (dBm)': 10 * math.log10(scale * v['temperature']),
                   'Input-referred receiver noise (dBm)': 10 * math.log10(scale * (v['temperature'] + equivalent_temperature))}
        if tool_id == 'receiver_sensitivity':
            outputs['Estimated receiver sensitivity (dBm)'] = outputs['Input-referred receiver noise (dBm)'] + v['required_snr'] + v['implementation_loss']
    elif tool_id == 'cable_loss':
        loss = v['length'] / 100 * v['attenuation'] + v['connector_loss']
        outputs = {'Total feed loss (dB)': loss, 'Power delivered (%)': 100 * 10 ** (-loss / 10)}
    elif tool_id == 'return_loss':
        gamma = 10 ** (-v['return_loss'] / 20)
        reflected = gamma ** 2
        outputs = {'Reflection coefficient magnitude': gamma,
                   'Reflected power (%)': reflected * 100,
                   'VSWR': (1 + gamma) / (1 - gamma),
                   'Mismatch loss (dB)': -10 * math.log10(1 - reflected)}
    elif tool_id == 'cascade_nf':
        first_factor = 10 ** (v['nf1'] / 10)
        first_gain = 10 ** (v['gain1'] / 10)
        second_factor = 10 ** (v['nf2'] / 10)
        total_factor = first_factor + (second_factor - 1) / first_gain
        outputs = {'First-stage gain (linear)': first_gain,
                   'Cascaded noise factor (linear)': total_factor,
                   'Cascaded noise figure (dB)': 10 * math.log10(total_factor)}
    elif tool_id == 'vswr':
        gamma = (v['vswr']-1)/(v['vswr']+1)
        reflected = gamma*gamma
        outputs = {'Reflection coefficient magnitude': gamma, 'Reflected power (%)': reflected*100,
                   'Mismatch loss (dB)': 0.0 if not reflected else -10*math.log1p(-reflected)/math.log(10)}
        if gamma > 0:
            outputs['Return loss (dB)'] = -20*math.log10(gamma)
        else:
            result_notes.append('Return loss (dB): infinite (ideal)')
    elif tool_id == 'aperture':
        wavelength = 299792458/(v['frequency']*1e6)
        outputs = {'Wavelength (m)': wavelength,
                   'Effective aperture (m²)': 10**(v['gain']/10)*wavelength*wavelength/(4*math.pi)}
    elif tool_id == 'polarization':
        fraction = 0.0 if v['angle']==90 else math.cos(math.radians(v['angle']))**2
        outputs = {'Relative received power (%)': fraction*100}
        if fraction > 0:
            outputs['Polarization mismatch loss (dB)'] = 0.0 if fraction == 1 else -10*math.log10(fraction)
        else:
            result_notes.append('Polarization mismatch loss (dB): infinite (ideal)')
    else:
        eirp = v['tx_power'] + v['tx_gain'] - v['tx_loss']
        outputs = {'EIRP (dBm)': eirp}
        if tool_id == 'link_budget':
            received = eirp - v['path_loss'] + v['rx_gain'] - v['rx_loss'] - v['other_loss']
            outputs.update({'Estimated received power (dBm)': received,
                            'Margin above sensitivity (dB)': received - v['sensitivity']})
    snapshot = {'tool_id': tool_id, 'version': 1, 'title': tool.title, 'kind': 'calculated estimate',
                'inputs': values, 'input_labels': {f.key: f.label for f in tool.fields},
                'outputs': outputs, 'method': tool.method, 'limitations': limitations}
    if result_notes:
        snapshot['result_notes'] = result_notes
    return snapshot


def format_snapshot(snapshot):
    lines = [snapshot['title'], 'Calculated estimate · calculator version ' + str(snapshot['version']), '', 'Results']
    lines += [f'{label}: {value:.8g}' for label, value in snapshot['outputs'].items()]
    lines += snapshot.get('result_notes', [])
    lines += ['', 'Inputs']
    lines += [f"{snapshot['input_labels'][key]}: {value:.8g}" for key, value in snapshot['inputs'].items()]
    if source := snapshot.get('source'):
        lines += ['', 'Input source · calculated estimate',
                  f"{source['output']}: {source['value']:.8g} from {source['title']} (version {source['version']})"]
        lines += [f"Source {key}: {value:.8g}" for key, value in source['inputs'].items()]
        lines += ['Source method: ' + source['method'], 'Source limitations: ' + source['limitations']]
    lines += ['', 'Method', snapshot['method'], '', 'Interpretation / limitations', snapshot['limitations']]
    return '\n'.join(lines)
