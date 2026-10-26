"""Offline channel arithmetic and candidate band lookup; never cell attribution."""
import math

from .cell_visibility import channel_plan


# Selected U.S.-relevant LTE downlink band base frequencies (MHz). EARFCN
# offsets and valid ranges come from the same bundled AOSP channel table.
# Base values: AOSP AccessNetworkConstants.EutranBandArfcnFrequency,
# reflecting 3GPP TS 36.101 table 5.7.3-1. This deliberately excludes
# unreviewed bands; it is not an operator or deployment catalog.
LTE_DL_LOW_MHZ = {
    2: 1930, 4: 2110, 5: 869, 12: 729, 13: 746, 14: 758,
    17: 734, 25: 1930, 26: 859, 29: 717, 30: 2350,
    41: 2496, 46: 5150, 48: 3550, 53: 2483.5,
    66: 2110, 70: 1995, 71: 617, 85: 728,
}
LTE_OFFSET_SOURCE = ('https://android.googlesource.com/platform/frameworks/base/+/master/'
                     'telephony/java/android/telephony/AccessNetworkConstants.java')
LTE_OFFSET_REVIEWED = '2026-10-26'


def nr_arfcn_to_mhz(number):
    """3GPP TS 38.104 global NR frequency raster, in MHz."""
    if type(number) is not int or not 0 <= number <= 3279165:
        raise ValueError('NR-ARFCN must be a whole number from 0 to 3279165.')
    if number < 600000:
        return number * .005
    if number < 2016667:
        return 3000 + (number - 600000) * .015
    return 24250.08 + (number - 2016667) * .06


def nr_mhz_to_arfcn(mhz):
    """Return the exact NR raster channel for a frequency, or reject off-grid input."""
    try:
        frequency = float(mhz)
    except (TypeError, ValueError, OverflowError):
        raise ValueError('Enter a finite NR center frequency in MHz.') from None
    if isinstance(mhz, bool) or not math.isfinite(frequency) or not 0 <= frequency <= nr_arfcn_to_mhz(3279165):
        raise ValueError('Enter a finite NR center frequency on the global raster.')
    if frequency < 3000:
        number = round(frequency / .005)
    elif frequency < 24250.08:
        number = round(600000 + (frequency - 3000) / .015)
    else:
        number = round(2016667 + (frequency - 24250.08) / .06)
    if not 0 <= number <= 3279165 or abs(nr_arfcn_to_mhz(number) - frequency) > .000001:
        raise ValueError('Frequency is not on the NR global raster; check the value and units.')
    return number


def lte_earfcn_to_mhz(band, channel):
    """Selected LTE downlink center frequency; reject unsupported band/range."""
    if type(band) is not int or type(channel) is not int or band not in LTE_DL_LOW_MHZ:
        raise ValueError('Choose a supported LTE band and whole downlink EARFCN.')
    rows = [row for row in channel_plan()['ranges']
            if row['radio'] == 'LTE' and row['band'] == band and row['min'] <= channel <= row['max']]
    if len(rows) != 1:
        raise ValueError('EARFCN is outside the selected LTE downlink band range.')
    return round(LTE_DL_LOW_MHZ[band] + .1 * (channel - rows[0]['min']), 6)


def lte_mhz_to_earfcn(band, mhz):
    """Reverse selected LTE downlink base/offset on its exact 100 kHz grid."""
    if type(band) is not int or band not in LTE_DL_LOW_MHZ:
        raise ValueError('Choose a supported LTE downlink band.')
    try:
        frequency = float(mhz)
    except (TypeError, ValueError, OverflowError):
        raise ValueError('Enter a finite LTE downlink center frequency in MHz.') from None
    if isinstance(mhz, bool) or not math.isfinite(frequency):
        raise ValueError('Enter a finite LTE downlink center frequency in MHz.')
    rows = [row for row in channel_plan()['ranges'] if row['radio'] == 'LTE' and row['band'] == band]
    if len(rows) != 1:
        raise ValueError('Selected LTE band is not in the bundled channel table.')
    channel = round(rows[0]['min'] + (frequency - LTE_DL_LOW_MHZ[band]) * 10)
    if not rows[0]['min'] <= channel <= rows[0]['max'] or abs(lte_earfcn_to_mhz(band, channel) - frequency) > .000001:
        raise ValueError('Frequency is outside this LTE downlink band or off its 100 kHz channel grid.')
    return channel


def inspect_channel(radio, channel):
    if radio not in ('LTE', 'NR'):
        raise ValueError('Choose LTE or NR.')
    if type(channel) is not int or channel < 0 or (radio == 'NR' and channel > 3279165):
        raise ValueError('Enter a nonnegative whole channel number in the radio range.')
    plan = channel_plan()
    bands = tuple(sorted({row['band'] for row in plan['ranges']
                          if row['radio'] == radio and row['min'] <= channel <= row['max']}))
    lte_frequency = (lte_earfcn_to_mhz(bands[0], channel)
                     if radio == 'LTE' and len(bands) == 1 and bands[0] in LTE_DL_LOW_MHZ else None)
    return {'radio': radio, 'channel': channel, 'bands': bands,
            'center_mhz': nr_arfcn_to_mhz(channel) if radio == 'NR' else lte_frequency,
            'source': 'channel-derived candidates' if bands else 'no candidate in bundled table',
            'reference_version': plan['version'], 'reference_source': plan['source'],
            'frequency_reference_source': LTE_OFFSET_SOURCE if lte_frequency is not None else None,
            'frequency_reference_reviewed': LTE_OFFSET_REVIEWED if lte_frequency is not None else None,
            'kind': 'calculated/reference context',
            'limitations': ('Candidate bands are not a carrier, tower, or live connection identification. '
                            'NR conversion is the global frequency raster, not validation of a band-specific channel raster. '
                            'LTE downlink conversion covers selected U.S.-relevant bands only; unsupported or ambiguous bands remain unresolved. Uplink is not computed. '
                            'A modem-reported band takes precedence; verify current standards and equipment support.')}
