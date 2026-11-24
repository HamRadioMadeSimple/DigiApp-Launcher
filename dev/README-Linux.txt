DigiApp Launcher for Linux
==============================
Opens your digital-mode radio programs in order, waiting between each one.
Works on Ubuntu 16.04 and newer, Linux Mint, Debian, Fedora, Arch, openSUSE,
Raspberry Pi OS and other Linux systems with Python 3.
(Quick Start: DigiApp_Launcher_Quick_Start.pdf. The full illustrated guide is DigiApp-Launcher-Guide.pdf.)

INSTALL
1. Extract this package (for example in your Downloads folder).
2. Open a terminal in the extracted folder and run:     bash linux_install.sh
   - It offers to install three small packages if they're missing:
     Tk for Python (the window), wmctrl + xdotool (for Minimize and closing apps).
     Works with apt (Ubuntu, Mint, Debian), dnf (Fedora), pacman (Arch), zypper (openSUSE).
   - The program goes in your Applications folder (~/Applications/DigiApp-Launcher).
   - It adds DigiApp Launcher to your menu, desktop, and panel or dock (automatic on
     Cinnamon/Linux Mint, GNOME/Ubuntu and Unity; on KDE, XFCE and MATE it tells you the
     one step to pin it yourself).
3. Linux Mint: if right-clicking the panel icon doesn't list your profiles yet,
   press Ctrl+Alt+Esc once to refresh Cinnamon.
4. If the desktop icon says "Untrusted", right-click it > Allow Launching
   (Linux Mint: double-click it > Mark as Trusted).

AmRRON-STYLE SETUP: KEEP IT IN YOUR ~/Radio FOLDER
- New install:            bash linux_install.sh --radio
- Already installed:      bash ~/Applications/DigiApp-Launcher/linux_install.sh --radio
  Either way the program goes to ~/Radio/DigiApp-Launcher, the icons are updated,
  and your profiles are kept.

SET UP
- Double-click the "DigiApp Launcher - Edit" icon on your desktop (also in the menu).
  It opens the editor only - none of your apps are started.
  (Right-clicking the panel/dock icon > "Edit apps and profiles" also works.)
- "+ Add App" > "Pick from installed apps..." lists the programs in your menu
  (fldigi, flrig, JS8Call, WSJT-X...). Or "Browse for a program..." for AppImages,
  scripts (.py / .sh) and anything else.
- Move Up / Move Down for the order, a wait time for each app (seconds before the
  NEXT one opens), and tick "Minimize" for apps that should start minimized.
- Programs started through a script: name them in the list the way their window title
  reads (e.g. "JS8Map Spotter") - that's how the launcher recognises their window.
- Flatpak apps (for example LocalSend) work: pick them from "Pick from installed apps".
  Apps that hide in the system tray when closed are asked to stop after 10 seconds.
- Pages an app opens in your web browser (such as a map) are not closed, so your
  other browser tabs are never touched.

EVERY DAY
- Click the panel/dock icon: opens your default profile (marked with a star).
- Right-click the panel/dock icon: pick another profile, "Close Open Apps" (closes them
  in reverse order and waits for any "Save changes?" questions), or edit your apps.
- Change your apps any time with the "DigiApp Launcher - Edit" icon.

UPDATING
Extract the new package and run:   bash update_linux.sh
It updates the program wherever it is installed (standard folder or ~/Radio) and keeps
your profiles.

NOTES
- Minimize and polite closing work best on an Xorg (X11) session - Linux Mint
  Cinnamon, MATE and XFCE normally are. Ubuntu 22.04+, Fedora and KDE often start a
  "Wayland" session instead: launching still works, but if Minimize doesn't, choose
  the Xorg / X11 session from the login screen.
- Your settings are in ~/.config/digiapp-launcher/settings.json (never in the
  program folder). A record of recent closes is in close-log.txt in the same folder.
- Terminal command:  digiapp-launcher   (or digiapp-launcher --run / --close)
- To remove it:      bash linux_uninstall.sh   (in the program folder)

HELP
Newest version: https://github.com/HamRadioMadeSimple/DigiApp-Launcher/releases/latest
Problems or questions: https://github.com/HamRadioMadeSimple/DigiApp-Launcher/issues

73!
