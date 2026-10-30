"""Phone optional-location values must stay within the desktop capture contract."""
import unittest
from veilbreaker.android_capture import validate_location


class AndroidLocationOptionalContractTests(unittest.TestCase):
    def test_unavailable_location_cannot_include_altitude(self):
        unavailable = dict(status='unavailable', source='phone', provider='gps')
        validate_location(unavailable)
        with self.assertRaisesRegex(ValueError, 'Unavailable location'):
            validate_location(dict(unavailable, altitude_m=120.0, altitude_reference='ellipsoid'))

    def test_optional_motion_bounds_match_phone_serializer(self):
        fix = dict(status='available', source='phone', provider='gps', latitude_deg=40.0, longitude_deg=-90.0,
                   horizontal_accuracy_m=5.0, fix_utc='2026-10-30T12:00:00Z', fix_age_ms=100,
                   altitude_m=120.5, altitude_reference='ellipsoid', vertical_accuracy_m=6.0,
                   speed_mps=2.0, bearing_deg=359.5)
        validate_location(fix)
        for bad in (dict(speed_mps=-1), dict(vertical_accuracy_m=-1), dict(bearing_deg=360),
                    dict(altitude_m=10000001), dict(horizontal_accuracy_m=1000000001)):
            with self.assertRaises(ValueError): validate_location(dict(fix, **bad))


if __name__ == '__main__': unittest.main()
