#!/bin/bash
# Run DigiApp Launcher straight from this folder (no install needed).
#   bash digiapp.sh            editor
#   bash digiapp.sh --run      launch the default profile
HERE="$(cd "$(dirname "$0")" && pwd)"
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "Tk for Python is missing. On Ubuntu/Mint: sudo apt install python3-tk wmctrl xdotool"
    exit 1
fi
exec python3 "$HERE/run_digiapp.py" "$@"
