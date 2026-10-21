# Build both entry points against the same bundled libraries.
from pathlib import Path
import sys
from PyInstaller.utils.hooks import collect_all
terrain_datas, terrain_binaries, terrain_imports = collect_all("rasterio")

root = Path(SPECPATH)
a = Analysis(
    [str(root / 'tools/cli_entry.py'), str(root / 'tools/gui_entry.py')],
    pathex=[str(root / 'src')],
    datas=[(str(root / 'src/veilbreaker/assets'), 'veilbreaker/assets')] + terrain_datas,
    binaries=terrain_binaries,
    hiddenimports=['serial.tools.list_ports', 'veilbreaker.map_web', 'PySide6.QtWebChannel', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets'] + terrain_imports,
    excludes=['tkinter'],
)
pyz = PYZ(a.pure)
icon = str(root / 'src/veilbreaker/assets/app.ico') if sys.platform == 'win32' else None
cli = EXE(pyz, [s for s in a.scripts if s[0] != 'gui_entry'], [], exclude_binaries=True, name='veilbreaker', console=True, icon=icon)
gui = EXE(pyz, [s for s in a.scripts if s[0] != 'cli_entry'], [], exclude_binaries=True, name='VeilbreakerDesktop', console=False, icon=icon)
coll = COLLECT(cli, gui, a.binaries, a.datas, name='Veilbreaker')
