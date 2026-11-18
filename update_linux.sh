#!/bin/bash
# DigiApp Launcher - update an existing Linux install from a newly downloaded package.
# Run it from the extracted NEW package folder:   bash update_linux.sh
# Keeps the install where it already is (standard folder, ~/Radio, or elsewhere) and keeps your profiles.

HERE="$(cd "$(dirname "$0")" && pwd)"
MENU="${XDG_DATA_HOME:-$HOME/.local/share}/applications/digiapp-launcher.desktop"
CUR=""
if [ -f "$MENU" ]; then
    CUR="$(grep -m1 '^Exec=' "$MENU" | sed -e 's/^Exec=[^ ]* //' -e 's/ --run$//' -e 's/^"//' -e 's/"$//')"
    CUR="$(dirname "$CUR")"
fi
if [ -z "$CUR" ] || [ ! -d "$CUR" ]; then
    echo "No existing install found - doing a normal install instead."
    exec bash "$HERE/linux_install.sh" "$@"
fi
# test versions before 1.2 installed in the hidden ~/.local/share/digiapp-launcher; move that to ~/Applications
if [ "$CUR" = "$HOME/.local/share/digiapp-launcher" ]; then
    echo "Moving DigiApp Launcher to ~/Applications/DigiApp-Launcher ..."
    exec bash "$HERE/linux_install.sh"
fi
echo "Updating the DigiApp Launcher in ${CUR/#$HOME/\~} ..."
exec bash "$HERE/linux_install.sh" --dest "$CUR"
