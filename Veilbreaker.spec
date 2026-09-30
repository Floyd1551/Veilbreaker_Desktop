# Build both entry points against the same bundled libraries.
from pathlib import Path
import sys

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'tools/cli_entry.py'), str(root / 'tools/gui_entry.py')],
    pathex=[str(root / 'src')],
    datas=[(str(root / 'src/veilbreaker/assets'), 'veilbreaker/assets')],
    hiddenimports=['serial.tools.list_ports'],
    excludes=['tkinter', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets'],
)
pyz = PYZ(a.pure)
icon = str(root / 'src/veilbreaker/assets/app.ico') if sys.platform == 'win32' else None
cli = EXE(pyz, [s for s in a.scripts if s[0] != 'gui_entry'], [], exclude_binaries=True, name='veilbreaker', console=True, icon=icon)
gui = EXE(pyz, [s for s in a.scripts if s[0] != 'cli_entry'], [], exclude_binaries=True, name='VeilbreakerDesktop', console=False, icon=icon)
coll = COLLECT(cli, gui, a.binaries, a.datas, name='Veilbreaker')
