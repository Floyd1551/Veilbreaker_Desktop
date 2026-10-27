"""Local vector icons for the desktop field workspace."""
from pathlib import Path

from PySide6.QtGui import QIcon


ICON_NAMES = frozenset({
    'overview', 'investigate', 'evidence', 'surveys', 'configuration',
    'tools', 'settings', 'network', 'guided', 'cellular', 'starlink',
    'sdr', 'throughput',
})
ASSETS = Path(__file__).parent / 'assets'


def ui_icon(name):
    if name not in ICON_NAMES:
        raise ValueError(f'Unknown workspace icon: {name}')
    return QIcon(str(ASSETS / 'icons' / f'{name}.svg'))


def brand_icon():
    return QIcon(str(ASSETS / 'app.svg'))
