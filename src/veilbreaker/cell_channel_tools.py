"""Offline channel arithmetic and candidate band lookup; never cell attribution."""
import math

from .cell_visibility import channel_plan


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


def inspect_channel(radio, channel):
    if radio not in ('LTE', 'NR'):
        raise ValueError('Choose LTE or NR.')
    if type(channel) is not int or channel < 0 or (radio == 'NR' and channel > 3279165):
        raise ValueError('Enter a nonnegative whole channel number in the radio range.')
    plan = channel_plan()
    bands = tuple(sorted({row['band'] for row in plan['ranges']
                          if row['radio'] == radio and row['min'] <= channel <= row['max']}))
    return {'radio': radio, 'channel': channel, 'bands': bands,
            'center_mhz': nr_arfcn_to_mhz(channel) if radio == 'NR' else None,
            'source': 'channel-derived candidates' if bands else 'no candidate in bundled table',
            'reference_version': plan['version'], 'reference_source': plan['source'],
            'kind': 'calculated/reference context',
            'limitations': ('Candidate bands are not a carrier, tower, or live connection identification. '
                            'NR conversion is the global frequency raster, not validation of a band-specific channel raster. '
                            'LTE frequency is not computed because it requires the band-specific EARFCN offset. '
                            'A modem-reported band takes precedence; verify current standards and equipment support.')}
