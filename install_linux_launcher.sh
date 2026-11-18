#!/bin/bash
# DigiApp Launcher - (re)create the menu, desktop and panel/dock icons for THIS folder.
# Handy when running from a source folder, or if the icons were removed.
#   bash install_linux_launcher.sh
HERE="$(cd "$(dirname "$0")" && pwd)"
python3 "$HERE/run_digiapp.py" --install-icon || exit 1
MSG="$(python3 "$HERE/run_digiapp.py" --pin 2>/dev/null)"
echo "${MSG:-Add DigiApp Launcher to your panel or dock from your applications menu.}"
