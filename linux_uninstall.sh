#!/bin/bash
# DigiApp Launcher - remove it from this user account.   Run:  bash linux_uninstall.sh

HERE="$(cd "$(dirname "$0")" && pwd)"
STD="$HOME/Applications/DigiApp-Launcher"
OLDSTD="$HOME/.local/share/digiapp-launcher"     # test versions before 1.2
MENU="${XDG_DATA_HOME:-$HOME/.local/share}/applications/digiapp-launcher.desktop"
# The installed copy, found from the menu entry (standard folder, ~/Radio, or --dest) - as update_linux.sh does
CUR=""
if [ -f "$MENU" ]; then
    CUR="$(grep -m1 '^Exec=' "$MENU" | sed -e 's/^Exec=[^ ]* //' -e 's/ --run$//' -e 's/^"//' -e 's/"$//')"
    CUR="$(dirname "$CUR")"
fi
is_digiapp_folder() {      # only ever remove DigiApp's own folder
    [ -f "$1/run_digiapp.py" ] && [ -f "$1/digiapp/app.py" ]
}
echo "Removing DigiApp Launcher..."
pkill -f "run_digiapp.py" >/dev/null 2>&1
for f in "$CUR/run_digiapp.py" "$HERE/run_digiapp.py" "$STD/run_digiapp.py"; do
    [ -f "$f" ] && { python3 "$f" --unpin >/dev/null 2>&1; break; }
done
is_digiapp_folder "$STD" && rm -rf "$STD"
is_digiapp_folder "$OLDSTD" && rm -rf "$OLDSTD"
LEFT=""
if [ -n "$CUR" ] && [ -d "$CUR" ] && is_digiapp_folder "$CUR"; then
    case "$(basename "$CUR")" in
        DigiApp-Launcher|digiapp-launcher) rm -rf "$CUR" && echo "Removed ${CUR/#$HOME/\~}";;
        *) LEFT="$CUR";;      # a folder chosen with --dest: leave it to the user
    esac
fi
rm -f  "$HOME/.local/bin/digiapp-launcher"
rm -f  "${XDG_DATA_HOME:-$HOME/.local/share}/applications/digiapp-launcher.desktop"
rm -f  "${XDG_DATA_HOME:-$HOME/.local/share}/applications/digiapp-launcher-edit.desktop"
DESK="$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")"
rm -f  "$DESK/digiapp-launcher.desktop" "$DESK/digiapp-launcher-edit.desktop"
command -v update-desktop-database >/dev/null 2>&1 && \
    update-desktop-database "${XDG_DATA_HOME:-$HOME/.local/share}/applications" >/dev/null 2>&1

read -r -p "Also delete your saved profiles and app lists? [y/N] " a
case "$a" in
    y*|Y*) rm -rf "${XDG_CONFIG_HOME:-$HOME/.config}/digiapp-launcher"; echo "Settings deleted.";;
    *) echo "Settings kept in ~/.config/digiapp-launcher (used again if you reinstall).";;
esac
echo "Done. If the icon is still on your panel or dock, right-click it > Remove / Unpin."
[ -n "$LEFT" ] && echo "The program folder ${LEFT/#$HOME/\~} was left in place - delete it if you no longer need it."
[ "$HERE" != "$STD" ] && [ "$HERE" != "$CUR" ] && [ -f "$HERE/run_digiapp.py" ] && \
    echo "You can now delete the folder ${HERE/#$HOME/\~}"
