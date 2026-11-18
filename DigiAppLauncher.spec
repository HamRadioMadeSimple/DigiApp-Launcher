# -*- mode: python ; coding: utf-8 -*-
# PyInstaller recipe for DigiAppLauncher.exe  (build_windows.bat runs this)
#   python -m PyInstaller DigiAppLauncher.spec
# Makes one self-contained program file: users don't need Python installed.
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

WINDOWS = sys.platform.startswith('win')

datas = [('icon.ico', '.'), ('icon.png', '.')]
binaries = []
hiddenimports = ['digiapp.plat_windows' if WINDOWS else 'digiapp.plat_linux']
excludes = ['digiapp.plat_linux'] if WINDOWS else ['digiapp.plat_windows']

if WINDOWS:
    hiddenimports += collect_submodules('comtypes')

try:                                   # optional: drag and drop of program icons
    d, b, h = collect_all('tkinterdnd2')
    datas += d
    binaries += b
    hiddenimports += h
except Exception:
    pass

a = Analysis(
    ['run_digiapp.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='DigiAppLauncher',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon='icon.ico' if WINDOWS else None,
)
