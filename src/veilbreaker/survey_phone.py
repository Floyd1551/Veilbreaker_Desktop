"""Validate transient USB input; never place credentials in survey settings."""
import re


def validate_phone(selection):
    fields = {'adb_path', 'serial', 'token', 'duration_s', 'cellular', 'location'}
    if not isinstance(selection, dict) or set(selection) - fields:
        raise ValueError('Invalid live phone input. Connect the phone again.')
    value = dict(selection)
    if not isinstance(value.get('adb_path'), str) or not value['adb_path'].strip():
        raise ValueError('Choose the ADB executable before connecting.')
    for key, pattern in [('serial', r'[A-Za-z0-9_-]{1,128}'), ('token', r'[a-f0-9]{32}')]:
        if not isinstance(value.get(key), str) or not re.fullmatch(pattern, value[key]):
            raise ValueError('Select and approve the USB phone again.')
    if type(value.get('duration_s')) is not int or not 5 <= value['duration_s'] <= 300:
        raise ValueError('Phone captures must last 5–300 seconds.')
    value.setdefault('cellular', True); value.setdefault('location', False)
    if any(type(value[k]) is not bool for k in ('cellular', 'location')) or not (value['cellular'] or value['location']):
        raise ValueError('Choose cellular observations, location, or both on the phone.')
    return value
