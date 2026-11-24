# Helping with DigiApp Launcher

Thanks for helping! Bug reports, ideas and code are all welcome.

## Reporting a problem

Open an issue on the [Issues page](https://github.com/HamRadioMadeSimple/DigiApp-Launcher/issues) with:
- the DigiApp Launcher version (in the editor's title bar) and your Windows or Linux version
- what you clicked, what you expected, and what happened (a screenshot helps a lot)
- for problems while closing: `close-log.txt` from the settings folder
  (`%APPDATA%\DigiApp Launcher` on Windows, `~/.config/digiapp-launcher` on Linux)

Please don't attach your `settings.json` unless asked: it lists the programs on your PC.

## Running from source

Python 3.5 or newer with Tk (Linux: `sudo apt install python3-tk wmctrl xdotool`).

```
python3 run_digiapp.py          # Windows: python run_digiapp.py, or DigiApp.bat
```

`tools/mock_radio_app.py` is a fake radio program for trying launching, minimizing and closing without
touching your real station programs (`python3 tools/mock_radio_app.py --help`).

## Tests and checks

```
python3 -m unittest discover -s tests -v     # 33 self-tests; "OK (skipped=33)" means Tk is missing
bash tools/check_code.sh                     # pyflakes, Python 3.5 check, line endings, tests
```

GitHub runs the self-tests on Linux and Windows on every push and pull request.

## Where things are

How the program is put together: [ARCHITECTURE.md](ARCHITECTURE.md). Building the downloads:
[dev/BUILDING.md](dev/BUILDING.md). Light/dark colours: [dev/THEMES.md](dev/THEMES.md).

Keep `.sh` files with LF line endings and `.bat` / `.iss` files with CRLF (`.gitattributes` does this).

## Making a release

Raise `__version__` and `BUILD_DATE` in `digiapp/__init__.py` (the only place the version lives) and add a
`## <version> - <date>` section at the top of `CHANGELOG.md`, written for users. Then create a release with
the tag `v<version>` on GitHub: the Release workflow builds and attaches the Setup.exe, the portable zip and
the Linux `.tar.gz`, with the CHANGELOG section as the release notes.
