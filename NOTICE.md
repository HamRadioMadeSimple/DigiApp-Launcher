# Notices and credits

DigiApp Launcher is Copyright (c) 2026 KW3KW and is free software under the MIT License
(see [LICENSE](LICENSE)).

## Programs it starts (not included)

DigiApp Launcher only starts and closes programs you already have. Names such as **flrig** and **fldigi**
(W1HKJ and contributors), **JS8Call** (KN4CRD), **WSJT-X** (K1JT and the WSJT team), CommStat, LocalSend and
the other KW3KW apps appear in the guide and screenshots as examples. DigiApp Launcher is an independent
project and is not part of, or endorsed by, any of them.

## Included in the ready-built downloads

- **Windows** (`DigiAppLauncher.exe`, made with **PyInstaller**) carries its own copy of:
  - **Python** (Python Software Foundation License), <https://www.python.org/>
  - **Tcl/Tk** (BSD-style Tcl/Tk license), <https://www.tcl-lang.org/>
  - **psutil** (BSD-3-Clause), <https://github.com/giampaolo/psutil>
  - **comtypes** (MIT), <https://github.com/enthought/comtypes>
  - **tkinterdnd2** (MIT) with **tkdnd** (BSD-style), for drag and drop,
    <https://github.com/Eliav2/tkinterdnd2>

  The PyInstaller bootloader is GPL with an exception that allows it in programs under any license,
  <https://pyinstaller.org/>. The installer is made with **Inno Setup** by Jordan Russell,
  <https://jrsoftware.org/isinfo.php>.
- **Linux** (`.tar.gz`) holds only DigiApp Launcher's own Python files and scripts. It uses the system's
  Python 3, Tk, `wmctrl` and `xdotool`, which your package manager installs; the optional drag-and-drop
  add-on (tkinterdnd2) comes from PyPI only if you say yes during the install.

## Icon and screenshots

The gold radio-tower icon is drawn by `tools/make_icon.py`. The screenshots in `tools/guide_shots` and the
guides show sample setups and hold no personal data.
