# Building DigiApp Launcher

All builds come from this project folder. Set the version in **one place**: `digiapp/__init__.py`
(`__version__` and `BUILD_DATE`). Add a line to `CHANGELOG.md` for each release.

## Windows  ->  `output\DigiAppLauncher-<ver>-Setup.exe` and `...-Windows-Portable.zip`

1. Needs Python 3 on the build PC (python.org, tick "Add python.exe to PATH").
   For the installer also install **Inno Setup 6** (free, https://jrsoftware.org/isdl.php).
2. Double-click `build_windows.bat`. It:
   - installs the build tools (`requirements.txt` + PyInstaller),
   - runs the self-tests,
   - builds `dist\DigiAppLauncher.exe` from `DigiAppLauncher.spec` (one file, no Python needed by users),
   - makes the portable zip, and the installer from `DigiAppLauncher.iss` if Inno Setup is installed,
   - opens the `output` folder.

The installer asks for administrator permission and installs to `C:\Program Files\DigiApp Launcher`
(Start menu and desktop icons for all users),
gives its shortcuts the AppUserModelID `DigiApp.Launcher` (so the taskbar button, pin and right-click
profile list all belong together) and keeps `%APPDATA%\DigiApp Launcher` (the profiles) on uninstall.

## Linux  ->  `output/DigiApp-Launcher-<ver>-Linux.tar.gz`

    bash build_linux.sh

Runs the self-tests, then packages the Python files with the Linux scripts. Nothing is compiled:
Linux users run the Python files with the system's Python 3, which keeps it working on old releases.

## Trying changes without building

| | |
|---|---|
| Windows | `DigiApp.bat` (or `python run_digiapp.py`) |
| Linux   | `bash digiapp.sh` (or `python3 run_digiapp.py`); `bash install_linux_launcher.sh` adds menu/panel icons for this folder |

## Sending the project (to a new session, a helper, a backup)

    python3 tools/make_project_zip.py          # Windows: py tools\make_project_zip.py

Makes `DigiApp_Launcher-<ver>-Project.zip` next to the project folder. Use it instead of Windows
Explorer's "Compressed folder", which drops the executable mark on `.sh` files. It also:

- leaves out `build/`, `dist/` and `output/` (big, and a stale copy can make a launcher start an old version),
- stores `.sh` files with LF and `.bat` files with CRLF line endings,
- never includes a user's own `settings.json`, `close-log.txt` or `DigiAppLauncher.json`.

Line endings matter: a `.sh` saved with Windows (CRLF) endings gives confusing errors on Linux.
`.gitattributes` enforces them once the project is in git; `build_linux.sh` fixes them in the download
and warns, and `tools/check_code.sh` reports any wrong file.

## Releasing

Raise the version in `digiapp/__init__.py` for **every** build that leaves your PC - two builds with the same
number can't be told apart (testers end up installing an older copy). Then:

1. Add a `CHANGELOG.md` entry for the new version.
2. `bash tools/check_code.sh` - pyflakes, Python 3.5 check, line endings, tests. Make sure the tests are not all
   skipped (`OK (skipped=N)` means Tk is missing and nothing was tested).
3. Guide changed? `node tools/make_guide.js` (needs `npm install docx`) -> `docs/DigiApp-Launcher-Guide.docx`, then save it as
   `docs/DigiApp-Launcher-Guide.pdf` (Word: File > Save As > PDF, after updating the contents list). Only the PDF goes in git
   and in the downloads; the Word file stays with the owner as the master.
4. Windows: `build_windows.bat` -> `output\DigiAppLauncher-<ver>-Setup.exe` and `...-Windows-Portable.zip`
   (Setup needs Inno Setup 6). Linux: `bash build_linux.sh` -> `output/DigiApp-Launcher-<ver>-Linux.tar.gz`.
5. `python3 tools/make_project_zip.py` -> the source zip (`--github` leaves out private notes).

## Checks

    python3 -m unittest discover -s tests      # self-tests (also run by both build scripts)
                                                # needs Tk (Linux: sudo apt install python3-tk) - without it
                                                # every test is skipped and "OK (skipped=N)" proves nothing
    bash tools/check_code.sh                    # pyflakes + Python 3.5 compatibility + line endings + tests
    python3 tools/mock_radio_app.py --help      # a fake radio program for testing launch/minimize/close

## Docs

`docs/DigiApp-Launcher-Guide.pdf` is made from the Word file that `node tools/make_guide.js` generates (needs `npm install docx`);
its screenshots are in `tools/guide_shots`. Both build scripts include the PDF guide in their downloads, and the
Linux download also carries `Installing_DigiApp_Launcher_on_Linux.pdf`.

On GitHub, making a release tag (`v<version>`) runs `.github/workflows/release.yml`: it runs these same build
scripts on Windows and on Ubuntu 22.04 and attaches the Setup.exe, portable zip and Linux `.tar.gz` to the release.
