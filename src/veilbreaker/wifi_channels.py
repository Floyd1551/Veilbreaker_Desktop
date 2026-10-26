"""Offline 20 MHz Wi-Fi channel geometry for comparison, not compliance checking."""

BANDS = ('2.4 GHz', '5 GHz', '6 GHz')

# Common 20 MHz channel centers for a U.S.-focused planning view. Availability
# still depends on regulatory domain, DFS/AFC, operating class and equipment.
_CHANNELS = {
    '2.4 GHz': tuple(range(1, 12)),
    '5 GHz': tuple(range(36, 65, 4)) + tuple(range(100, 145, 4)) + tuple(range(149, 166, 4)),
    '6 GHz': tuple(range(1, 234, 4)),
}


def channels(band):
    try:
        return _CHANNELS[band]
    except (KeyError, TypeError):
        raise ValueError('Choose 2.4, 5, or 6 GHz.') from None


def _channel(band, number):
    if isinstance(number, bool) or not isinstance(number, int) or number not in channels(band):
        raise ValueError(f'Channel {number!r} is not in this planning list for {band}.')
    base = {'2.4 GHz': 2407, '5 GHz': 5000, '6 GHz': 5950}[band]
    center = base + 5 * number
    return {'channel': number, 'center_mhz': center,
            'lower_mhz': center - 10, 'upper_mhz': center + 10}


def inspect_pair(band, first, second):
    """Return labeled, nominal 20 MHz intervals for two channels."""
    a, b = _channel(band, first), _channel(band, second)
    overlap = max(0, min(a['upper_mhz'], b['upper_mhz']) - max(a['lower_mhz'], b['lower_mhz']))
    return {'band': band, 'first': a, 'second': b,
            'center_separation_mhz': abs(a['center_mhz'] - b['center_mhz']),
            'nominal_overlap_mhz': overlap,
            'kind': 'calculated planning geometry',
            'limitations': 'Nominal 20 MHz footprints only. Adjacent emissions, traffic, DFS/AFC, device support and current rules are not assessed.'}
