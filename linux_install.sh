#!/bin/bash
# DigiApp Launcher - Linux installer (Ubuntu, Mint, Debian, Fedora, Arch, openSUSE...)
#
#   bash linux_install.sh                 install in ~/Applications/DigiApp-Launcher
#   bash linux_install.sh --radio         install in ~/Radio/DigiApp-Launcher (AmRRON-style setup)
#   bash linux_install.sh --dest FOLDER   install somewhere else
#
# Run it again (with or without --radio) to update or move an existing install; profiles are kept.
# Installs for your user only - no system files are changed except the optional packages.

HERE="$(cd "$(dirname "$0")" && pwd)"
STD="$HOME/Applications/DigiApp-Launcher"
DEST="$STD"
case "$1" in
    --radio) DEST="$HOME/Radio/DigiApp-Launcher";;
    --dest)  [ -n "$2" ] || { echo "Usage: bash linux_install.sh --dest FOLDER"; exit 1; }
             DEST="${2/#\~/$HOME}";;
esac
VERSION="$(sed -n "s/^__version__ = '\(.*\)'/\1/p" "$HERE/digiapp/__init__.py" 2>/dev/null)"

echo ""
echo "=== DigiApp Launcher ${VERSION} installer ==="
echo ""
if [ ! -f "$HERE/run_digiapp.py" ] || [ ! -f "$HERE/digiapp/app.py" ]; then
    echo "Run this from the extracted DigiApp Launcher folder."
    exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 is needed (for example: sudo apt install python3)"
    exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 3) else 1)'; then
    echo "Python 3.3 or newer is needed (found $(python3 --version 2>&1))."
    exit 1
fi

# Packages: Tk for Python (required), wmctrl + xdotool (for Minimize and closing apps politely)
if command -v apt-get >/dev/null 2>&1; then
    PM="apt";    TKPKG="python3-tk";      INSTALL="sudo apt-get install -y"
elif command -v dnf >/dev/null 2>&1; then
    PM="dnf";    TKPKG="python3-tkinter"; INSTALL="sudo dnf install -y"
elif command -v pacman >/dev/null 2>&1; then
    PM="pacman"; TKPKG="tk";              INSTALL="sudo pacman -S --needed --noconfirm"
elif command -v zypper >/dev/null 2>&1; then
    PM="zypper"; TKPKG="python3-tk";      INSTALL="sudo zypper install -y"
else
    PM="";       TKPKG="python3-tk";      INSTALL=""
fi
missing=""
python3 -c "import tkinter" >/dev/null 2>&1 || missing="$missing $TKPKG"
command -v wmctrl  >/dev/null 2>&1 || missing="$missing wmctrl"
command -v xdotool >/dev/null 2>&1 || missing="$missing xdotool"
if [ -n "$missing" ]; then
    echo "These packages are needed:$missing"
    if [ -n "$INSTALL" ]; then
        read -r -p "Install them now with $PM? [Y/n] " answer
        case "$answer" in
            n*|N*) echo "Skipped. (Install later with: $INSTALL$missing)";;
            *)  if [ "$PM" = "apt" ]; then
                    $INSTALL $missing || { sudo apt-get update && $INSTALL $missing; }
                else
                    $INSTALL $missing
                fi;;
        esac
    else
        echo "Please install them with your system's package manager, then run this installer again."
    fi
fi
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo ""
    echo "Tk for Python ($TKPKG) is still missing, so the launcher can't open its window."
    echo "Install it, then run this installer again."
    exit 1
fi

# An earlier install (found from the menu entry), so updating or moving keeps just one copy
MENU="${XDG_DATA_HOME:-$HOME/.local/share}/applications/digiapp-launcher.desktop"
OLD=""
if [ -f "$MENU" ]; then
    OLD="$(grep -m1 '^Exec=' "$MENU" | sed -e 's/^Exec=[^ ]* //' -e 's/ --run$//' -e 's/^"//' -e 's/"$//')"
    OLD="$(dirname "$OLD")"
fi
is_digiapp_folder() {      # only ever remove DigiApp's own folder
    [ -f "$1/run_digiapp.py" ] && [ -f "$1/digiapp/app.py" ] && return 0
    [ -f "$1/digiapp_launcher.py" ] && [ -f "$1/plat_linux.py" ] && return 0      # version 3.0 layout
    return 1
}

# Close any running copy first (an old copy left open would point the icons back at itself)
pkill -f "run_digiapp.py" >/dev/null 2>&1
pkill -f "digiapp_launcher.py" >/dev/null 2>&1

# Copy the program
mkdir -p "$DEST" || exit 1
DEST="$(cd "$DEST" && pwd)"
if [ "$DEST" != "$HERE" ]; then
    rm -rf "$DEST/digiapp"
    mkdir -p "$DEST/digiapp"
    cp "$HERE"/digiapp/*.py "$DEST/digiapp/" || exit 1
    cp "$HERE/run_digiapp.py" "$HERE/icon.png" "$DEST/" || exit 1
    for f in linux_install.sh install_linux_launcher.sh update_linux.sh linux_uninstall.sh digiapp.sh \
             README.txt CHANGELOG.md DigiApp_Launcher_Quick_Start.pdf DigiApp-Launcher-Guide.pdf DigiApp-Launcher-Guide.docx; do
        [ -f "$HERE/$f" ] && cp "$HERE/$f" "$DEST/"
    done
fi
chmod +x "$DEST/run_digiapp.py" 2>/dev/null
for f in linux_install.sh install_linux_launcher.sh update_linux.sh linux_uninstall.sh digiapp.sh; do
    [ -f "$DEST/$f" ] && chmod +x "$DEST/$f"
done
# tidy files left by version 3.0 - only in a folder that really holds a 3.0 install
if [ -f "$DEST/digiapp_launcher.py" ]; then
    rm -f "$DEST/digiapp_launcher.py" "$DEST/plat_linux.py" "$DEST/DigiApp.png" \
          "$DEST/install.sh" "$DEST/uninstall.sh"
    rm -rf "$DEST/__pycache__"
fi
echo "Program folder: ${DEST/#$HOME/\~}"

# Moved somewhere new? Remove the earlier copy.
if [ -n "$OLD" ] && [ -d "$OLD" ] && [ "$(cd "$OLD" && pwd)" != "$DEST" ] && is_digiapp_folder "$OLD"; then
    case "$(basename "$OLD")" in
        DigiApp-Launcher|digiapp-launcher)
            rm -rf "$OLD" && echo "Moved from ${OLD/#$HOME/\~} (old copy removed; your profiles are kept).";;
    esac
fi

# A command you can type in a terminal: digiapp-launcher
mkdir -p "$HOME/.local/bin"
printf '#!/bin/sh\nexec python3 "%s/run_digiapp.py" "$@"\n' "$DEST" > "$HOME/.local/bin/digiapp-launcher"
chmod +x "$HOME/.local/bin/digiapp-launcher"

# Optional: drag-and-drop of program icons onto the list
if ! python3 -c "import tkinterdnd2" >/dev/null 2>&1; then
    read -r -p "Add optional drag-and-drop support (downloads a small Python add-on)? [y/N] " dnd
    case "$dnd" in
        y*|Y*) python3 -m pip install --user tkinterdnd2 >/dev/null 2>&1 \
                 || python3 -m pip install --user --break-system-packages tkinterdnd2 >/dev/null 2>&1 \
                 || echo "  Drag-and-drop add-on couldn't be installed; everything else still works.";;
    esac
fi

# Menu + desktop icon (its right-click menu lists your profiles), then pin it to the panel / dock
python3 "$DEST/run_digiapp.py" --install-icon
PIN_MSG="$(python3 "$DEST/run_digiapp.py" --pin 2>/dev/null)"

echo ""
echo "Installed!"
echo "  - Panel / dock: ${PIN_MSG:-add DigiApp Launcher from your applications menu.}"
echo "  - Click the icon to launch your default profile; right-click it for your other"
echo "    profiles, Close Open Apps, and Edit apps and profiles."
echo "  - To change your apps without launching any, use the \"DigiApp Launcher - Edit\" icon"
echo "    on your desktop or in the menu."
case "$XDG_CURRENT_DESKTOP" in
    *Cinnamon*) echo "  - Linux Mint: if the right-click doesn't list your profiles, press Ctrl+Alt+Esc once.";;
esac
echo "  - Your settings are kept in ~/.config/digiapp-launcher (never in the program folder)."
echo ""
read -r -p "Open DigiApp Launcher now to set up your apps? [Y/n] " go
case "$go" in
    n*|N*) ;;
    *) (nohup python3 "$DEST/run_digiapp.py" >/dev/null 2>&1 &) ;;
esac
