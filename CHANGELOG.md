# Changelog

## 1.3.3 - 2026-11-18 - first release on GitHub
DigiApp Launcher opens your digital-mode radio programs (flrig, JS8Call, Fldigi, WSJT-X, maps, chat and logging
helpers) in order, waiting between each one so every program is ready before the next starts - all from one click
on a gold taskbar or panel icon. Close Open Apps shuts them down again in reverse order, so each one can save.
This is its first release on GitHub; the list below is what changed since the last test build.

- Close Open Apps no longer waits ~25 s on JS8Call (and similar programs). Once the program that had the window
  has ended, a leftover process that never had a window gets 3 seconds and then closing moves on - it ends by
  itself; nothing is forced. close-log.txt now names each process found (program, options, parent). 33 self-tests.

## 1.3.2 - 2026-11-18
- One font family everywhere (Segoe UI on Windows): program locations, status line, header and wait times no
  longer use a typewriter font. Program locations bold and easier to read; white Minimize tick in the light theme.

## 1.3.1 - 2026-11-18 (not released)
- Windows: no more "Failed to remove temporary directory" warning. Programs started by the launcher no longer
  inherit the one-file exe's temporary folder (Tk programs such as CommStat used and locked it).
- Windows Setup install: the installer's Start menu and desktop icons are the only ones - the program no longer
  adds its own copies to your desktop when the editor opens (they appeared late and could show twice).
- Theme button moved next to Find Missing Apps, same style as the other buttons; status text is bold.

## 1.3 - 2026-11-18
- **Light theme.** A Light / Dark button switches the look (moved next to Find Missing Apps in 1.3.1); the editor reopens in
  the new colours in about a second and the choice is remembered (new `Theme` setting; older settings files open
  in Dark). The launching and closing windows, and the Windows title bar, follow it. Colours live in one table
  per theme (`THEMES` in `app.py`); text colours are kept apart from button colours so both themes stay readable.
- Guide: arrows on the screenshots, closing from the taskbar and programs that ask before closing, a full
  Find Missing Apps section, and the theme button.
- New `docs/THEMES.md`: the light/dark standard shared with the other station apps. 32 self-tests.

## 1.2 - 2026-11-16 - first public version number
DigiApp Launcher V1.2 is the first version with a public version number (MIT license). It is the same program as
the last test build (3.2.3 below). (Its first release on GitHub is 1.3.3.)
- Windows: Setup installer (Program Files, Start menu, two desktop icons, taskbar right-click profile list) and a
  portable zip. Linux: `.tar.gz` installed with three pasted commands into `~/Applications/DigiApp-Launcher`.
- Guide: new Windows editor screenshot; drag and drop explained with pictures.

## Before the public release - test versions

### Test version 3.2.3 - 2026-11-16
- A settings file that can't be read (for example after a hand edit) is no longer replaced by an empty one:
  it is kept as `settings-unreadable-<date>.json` and the editor says so. New self-test (30 tests).
- Linux installer: the clean-up of version 3.0 files runs only in a folder that holds a 3.0 install, and only
  DigiApp's own scripts are made executable - so `--dest` into a shared folder never touches other programs' files.
  The uninstaller removes the standard folder only if it holds DigiApp Launcher.

### Test version 3.2.2 - 2026-11-02
- Linux: installs into the visible `~/Applications/DigiApp-Launcher` (was the hidden `~/.local/share/digiapp-launcher`),
  like the other apps. `update_linux.sh` moves an old install there; `~/Radio` and `--dest` installs stay where they are.
  `linux_uninstall.sh` removes either location.
- Guide and README: the Linux install, update and remove steps are three lines to paste from Downloads.

### Test version 3.2.1 - 2026-10-30
- Linux: `linux_uninstall.sh` now removes the program folder wherever it was installed (`--radio` installs in
  `~/Radio/DigiApp-Launcher` were left behind); a custom `--dest` folder is left in place and named.
- `.gitattributes`: `DigiAppLauncher.iss` kept CRLF.

### Test version 3.2 - 2026-10-30
- New **DigiApp Launcher - Edit** icon on the desktop and in the Start menu / app menu, on Windows and
  Linux. It opens the editor only, so you can change apps and profiles without launching a profile. (On
  Linux Mint Cinnamon the panel right-click "Edit apps and profiles" item didn't always open the editor.)
  Windows: the Setup installer has its own "DigiApp Launcher - Edit" desktop checkbox (ticked by default, also
  on upgrades) and always adds it to the Start menu; the portable version makes it with the Desktop Icon
  button; the uninstaller removes it. Linux: made with the main icon; `linux_uninstall.sh` removes it.
- **Close Open Apps finds more kinds of programs** (they were reported "not running" and left open):
  - Programs started through a helper script that hands over to another program (e.g. `~/.local/bin/fcc-lookup`
    running `python3 FCC_Lookup.py`): the launcher now remembers the process it started (`launched.json` next
    to the settings, with the start time so a reused process id is never mistaken for the app).
  - **Flatpak apps** (e.g. LocalSend, started with `flatpak run ...` but running as `bwrap ...`): found by their
    Flatpak app group. "Skip apps that are already open" works for them too.
  - If no process is found but a window carrying the app's name is open, that window is closed.
  - Apps that only hide in the system tray when their window closes are asked to stop 10 seconds later.
- Picking a Flatpak app from "installed apps" no longer copies Flatpak's `@@u @@` markers into Options.
- The launcher's own menu entries stay out of "Pick from installed apps".
- Self-tests for the Edit icon, Flatpak apps, helper scripts and tray apps (29 tests); README, both readmes and
  the guide updated (Windows readme said 3.1).
- Guide: Windows install steps match the real installer (Program Files, administrator prompt, two desktop
  checkboxes); simpler move from 2.0 (copy the old file to `%APPDATA%\DigiApp Launcher\settings.json`); notes on
  tray apps, browser pages and "Not running"; a "Making a release" checklist.
- New `docs/ARCHITECTURE.md` for contributors (with diagrams).

### Test version 3.1 - 2026-10-29
- Project restructured like RigPanel: `digiapp/` package, `run_digiapp.py`, build scripts for both systems,
  docs, tests and tools folders.
- **Windows installer** (Inno Setup): installs to C:\Program Files\DigiApp Launcher (admin prompt), no folder question, Start menu + desktop icons tied to the
  taskbar right-click list; portable zip still built. Profiles kept on update/uninstall.
- Linux: `linux_install.sh` (with `--radio` / `--dest`), `update_linux.sh` keeps the current location,
  `linux_uninstall.sh`, `install_linux_launcher.sh`; updating from 3.0 tidies the old files.
- Apps started through a script (e.g. `sh start.sh`) are now found by their window title / list name, so
  they minimize and close properly; if no window is found, everything the script started is closed.
- Self-tests for app matching, settings, menu entries and panel pinning.
- Packaging safety: `.gitattributes` (LF for .sh, CRLF for .bat); `build_linux.sh` fixes and warns about
  Windows line endings; `check_code.sh` checks them; `tools/make_project_zip.py` zips the project without
  build/dist/output, keeping .sh files executable.
- Windows build: portable zip made by `tools/make_portable_zip.py`, which retries while Defender scans the
  new exe (was "file in use" with Compress-Archive) and stops the build if it still fails.

### Test version 3.0 - 2026-10-16 to 2026-10-27  (Python, Windows + Linux)
- One Python program for both systems; Windows build as a single DigiAppLauncher.exe (no Python needed).
- Linux: menu/desktop icon whose right-click lists profiles; automatic pin to the panel/dock on Cinnamon,
  GNOME and Unity; installer for apt, dnf, pacman and zypper; `--radio` option for `~/Radio`.
- Close in reverse order: second polite try, "run as administrator" detection, brings up apps that ask
  "Save changes?", status shows each app closed; close-log.txt for troubleshooting.
- Programs started with `bash -c '...'` are recognised (running/closing/skip-if-open).
- Gold taskbar icon fix; "Close Open Apps" wording; default wait 2 seconds.
- Word install & user guide.

### Test version 2.0 - 2026-10-15  (PowerShell, Windows)
- Renamed DigiApp Launcher; dark theme; gold icon; taskbar right-click profile list; default profile;
  clone; minimize; close apps in reverse order; desktop icon status button.

### Test version 1.0 - 2026-10-15  (PowerShell, Windows)
- First version ("Ham Radio App Launcher"): apps in order with a wait between each; profiles.
