// Rebuilds docs/DigiApp-Launcher-Guide.docx (Word).   Needs Node.js and:  npm install docx
//   node tools/make_guide.js
// Screenshots live in tools/guide_shots (taken on Linux with sample apps - no personal data).
const fs = require('fs');
const path = require('path');
const {
  Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, ShadingType,
  AlignmentType, HeadingLevel, BorderStyle, LevelFormat, PageBreak, Header, Footer, PageNumber,
  TableOfContents, TabStopType,
} = require('docx');

const INIT = fs.readFileSync(path.join(__dirname, '..', 'digiapp', '__init__.py'), 'utf8');
const VER = (INIT.match(/__version__ = '([^']+)'/) || [])[1] || '?';
const BUILD = (INIT.match(/BUILD_DATE = '([^']+)'/) || [])[1] || '';
const SHOTS = path.join(__dirname, 'guide_shots');
const img = (f) => fs.readFileSync(path.join(SHOTS, f));

const NAVY = '0D1626', GOLD = 'C99A00', GREEN = '1E8F4E', GREY = '5A6780', LIGHT = 'EEF1F6', AMBER = 'FFF4D6';
const FONT = 'Arial';
const CONTENT = 9360; // 6.5in in DXA
const REPO = 'github.com/HamRadioMadeSimple/DigiApp-Launcher';

// ---------- helpers
const t = (text, o = {}) => new TextRun({ text, font: FONT, ...o });
const b = (text, o = {}) => t(text, { bold: true, ...o });
const code = (text) => new TextRun({ text, font: 'Consolas', size: 20, color: '1F3A5F' });

function runs(parts) {
  // parts: string or [text, 'b'|'c'|'i']
  return parts.map((p) => {
    if (typeof p === 'string') return t(p);
    if (p[1] === 'b') return b(p[0]);
    if (p[1] === 'c') return code(p[0]);
    if (p[1] === 'i') return t(p[0], { italics: true });
    return t(p[0]);
  });
}
const P = (...parts) => new Paragraph({ children: runs(parts), spacing: { after: 120, line: 276 } });
const H1 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [t(text)], pageBreakBefore: true });
const H1first = (text) => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [t(text)] });
const H2 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [t(text)] });
const H3 = (text) => new Paragraph({ heading: HeadingLevel.HEADING_3, children: [t(text)] });

let listId = 0;
function steps(items) {
  const ref = 'steps' + (listId++);
  numberingConfigs.push({
    reference: ref,
    levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT,
      style: { paragraph: { indent: { left: 540, hanging: 360 } }, run: { bold: true, color: NAVY } } }],
  });
  return items.map((it) => new Paragraph({ numbering: { reference: ref, level: 0 },
    children: runs(Array.isArray(it) ? it : [it]), spacing: { after: 100, line: 276 } }));
}
function steps2(items) {     // a numbered list that carries on from the one before it
  const ref = 'steps' + (listId - 1);
  return items.map((it) => new Paragraph({ numbering: { reference: ref, level: 0 },
    children: runs(Array.isArray(it) ? it : [it]), spacing: { after: 100, line: 276 } }));
}
const bullets = (items) => items.map((it) => new Paragraph({ numbering: { reference: 'bullets', level: 0 },
  children: runs(Array.isArray(it) ? it : [it]), spacing: { after: 80, line: 276 } }));

function picture(file, w, h, caption) {
  const out = [new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: !!caption,
    children: [new ImageRun({ type: 'png', data: img(file), transformation: { width: w, height: h },
      altText: { title: caption, description: caption, name: file } })] })];
  if (caption) out.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 },
    children: [t(caption, { italics: true, size: 18, color: GREY })] }));
  return out;
}

function note(label, parts, fill = AMBER, edge = GOLD) {
  return new Table({
    width: { size: CONTENT, type: WidthType.DXA }, columnWidths: [CONTENT],
    rows: [new TableRow({ cantSplit: true, children: [new TableCell({
      width: { size: CONTENT, type: WidthType.DXA },
      shading: { fill, type: ShadingType.CLEAR, color: 'auto' },
      margins: { top: 100, bottom: 100, left: 160, right: 160 },
      borders: { top: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, bottom: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
        right: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' }, left: { style: BorderStyle.SINGLE, size: 24, color: edge } },
      children: [new Paragraph({ children: [b(label + '  ', { color: NAVY }), ...runs(parts)], spacing: { line: 276 } })],
    })] })],
  });
}
// commands to type: grey box, one paragraph per line
const cmds = (lines) => lines.map((l, i) => new Paragraph({ children: [code(l)], indent: { left: 360 },
  shading: { fill: 'F2F2F2', type: ShadingType.CLEAR, color: 'auto' },
  spacing: { before: i === 0 ? 60 : 0, after: i === lines.length - 1 ? 160 : 0, line: 240 }, keepNext: i < lines.length - 1 }));
const LINUX_BLOCK = [
  'F="$(ls -t ~/Downloads/DigiApp-Launcher-*-Linux*.tar.gz | head -n 1)"',
  'tar -xzf "$F" -C ~/Downloads',
  'bash ~/Downloads/"$(tar -tzf "$F" | head -n 1 | cut -d/ -f1)"/update_linux.sh',
];
const gap = () => new Paragraph({ children: [], spacing: { after: 60 } });

const isPart = (c) => Array.isArray(c) && c.length === 2 && typeof c[0] === 'string' && ['b', 'c', 'i'].includes(c[1]);
function table(widths, header, rows) {
  const border = { style: BorderStyle.SINGLE, size: 4, color: 'C5CCD8' };
  const borders = { top: border, bottom: border, left: border, right: border };
  const cell = (content, i, head, shade) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA }, borders,
    shading: { fill: head ? NAVY : (shade ? 'F5F7FA' : 'FFFFFF'), type: ShadingType.CLEAR, color: 'auto' },
    margins: { top: 70, bottom: 70, left: 110, right: 110 },
    children: [new Paragraph({ spacing: { line: 260 }, children: head ? [b(content, { color: 'FFFFFF', size: 20 })]
      : runs(isPart(content) ? [content] : (Array.isArray(content) ? content : [content])) })],
  });
  return new Table({
    width: { size: widths.reduce((a, c) => a + c, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, i, true)) }),
      ...rows.map((r, ri) => new TableRow({ children: r.map((c, i) => cell(c, i, false, ri % 2 === 1)) }))],
  });
}

const numberingConfigs = [
  { reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 540, hanging: 300 } } } }] },
];

// ---------- content
const body = [];

// Title page
body.push(new Paragraph({ spacing: { before: 1800 }, alignment: AlignmentType.CENTER,
  children: [new ImageRun({ type: 'png', data: img('icon.png'), transformation: { width: 120, height: 120 },
    altText: { title: 'DigiApp Launcher icon', description: 'Gold radio tower icon', name: 'icon' } })] }));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 360, after: 120 },
  children: [b('DigiApp Launcher', { size: 64, color: NAVY })] }));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120 },
  children: [t('Install and User Guide', { size: 36, color: GOLD, bold: true })] }));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
  children: [t('Version ' + VER + ' for Windows and Linux  •  Build ' + BUILD, { size: 22, color: GREY })] }));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 120, line: 300 },
  children: [t('Opens your digital-mode radio programs in order, waiting between each one so every program is ready before the next one starts — all from one click on a gold taskbar or dock icon.', { size: 24 })] }));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 480, after: 60 },
  children: [t('Download: ', { size: 20, color: GREY }), t(REPO + '/releases/latest', { size: 20, bold: true })] }));
body.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
  children: [t('Questions and problems: ', { size: 20, color: GREY }), t(REPO + '/issues', { size: 20, bold: true })] }));

// Contents
body.push(new Paragraph({ pageBreakBefore: true, children: [b('Contents', { size: 32, color: NAVY })], spacing: { after: 200 } }));
body.push(new TableOfContents('Contents', { hyperlink: true, headingStyleRange: '1-2' }));
body.push(new Paragraph({ children: [t('(If the contents list is empty, right-click it in Word and choose Update Field.)', { italics: true, size: 18, color: GREY })] }));

// 1 Overview
body.push(H1('1. What DigiApp Launcher does'));
body.push(P('Most digital-mode stations run several programs together — a rig control program such as Flrig, then JS8Call or Fldigi, then helper programs such as maps, messaging and logging. Many of them need the one before them to be fully running first. DigiApp Launcher does the starting (and stopping) for you:'));
body.push(...bullets([
  [['Opens your programs in order', 'b'], ', waiting the number of seconds you choose after each one.'],
  [['Profiles', 'b'], ' hold different combinations — for example a JS8 net profile and an Fldigi messaging profile.'],
  [['One click', 'b'], ' on the taskbar (Windows) or dock (Linux) icon opens your default profile. Right-click the icon to pick another profile.'],
  [['Minimize', 'b'], ' chosen programs to the taskbar as they open.'],
  [['Close Open Apps', 'b'], ' shuts everything down in reverse order (rig control last) and waits for any “Save changes?” questions.'],
]));
body.push(H2('What you need'));
body.push(table([1900, 3730, 3730], ['', 'Windows', 'Linux'], [
  [['System', 'b'], 'Windows 10 or 11', 'Ubuntu 16.04 or newer, Linux Mint, Debian, Fedora, Arch, openSUSE, Raspberry Pi OS and other Linux systems with Python 3'],
  [['Extra software', 'b'], 'None — the program is self-contained', 'Tk for Python, wmctrl and xdotool (the installer offers to add them)'],
  [['Download', 'b'], [['DigiAppLauncher-' + VER + '-Setup.exe', 'c'], ' (or the portable zip)'], [['DigiApp-Launcher-' + VER + '-Linux.tar.gz', 'c']]],
  [['Your settings', 'b'], [['%APPDATA%\\DigiApp Launcher', 'c']], [['~/.config/digiapp-launcher', 'c']]],
]));
body.push(P('Get the downloads from the Releases page: ', [REPO + '/releases/latest', 'b'], '. It always has the newest version.'));
body.push(note('Privacy:', ['your app list and profiles are saved in your own user folder, never in the program folder. You can share the program with others without sharing your setup, and a new user always starts with one empty “My Profile”.'], 'EAF6EE', GREEN));

// 2 Windows install
body.push(H1('2. Installing on Windows'));
body.push(H2('Install'));
body.push(...steps([
  ['Double-click ', ['DigiAppLauncher-' + VER + '-Setup.exe', 'b'], '.'],
  ['If Windows shows “Windows protected your PC”, click ', ['More info', 'b'], ' then ', ['Run anyway', 'b'], '. The program is not code-signed, which is normal for small ham-radio tools.'],
  ['Click ', ['Yes', 'b'], ' when Windows asks for permission. The program installs to ', ['C:\\Program Files\\DigiApp Launcher', 'c'], ' for everyone on the PC; your profiles are still kept separately for each user.'],
  ['On the icons page leave both boxes ticked: ', ['Put a DigiApp Launcher icon on the desktop', 'b'], ' (one click launches your default profile) and ', ['Put a DigiApp Launcher - Edit icon on the desktop', 'b'], ' (opens the editor without launching anything).'],
  ['Leave ', ['Open DigiApp Launcher to set up your apps', 'b'], ' ticked and click ', ['Finish', 'b'], '. A welcome message explains the first steps; continue with section 4 to add your programs.'],
]));
body.push(note('No-install option:', ['', ['DigiApp-Launcher-' + VER + '-Windows-Portable.zip', 'c'], ' holds the same program without an installer. Unzip it to a folder you will keep, double-click ', ['DigiAppLauncher.exe', 'b'], ', and click the gold ', ['Desktop Icon', 'b'], ' button to create the desktop icon.']));
body.push(H2('Put the gold icon on your taskbar'));
body.push(...steps([
  ['Right-click the gold DigiApp Launcher icon on the desktop, choose ', ['Show more options', 'b'], ', then ', ['Pin to taskbar', 'b'], '. (Or right-click it in the Start menu > ', ['Pin to taskbar', 'b'], '.)'],
  ['Click the taskbar icon to open your default profile. Right-click it to choose another profile, ', ['Close Open Apps', 'b'], ', or ', ['Edit apps and profiles', 'b'], '.'],
  ['To change your apps without launching any, double-click the ', ['DigiApp Launcher - Edit', 'b'], ' icon on the desktop (also in the Start menu).'],
]));
body.push(note('Tip:', ['the editor’s icon button shows “✔ Icon Up to Date”. Each time you open the editor it quietly refreshes the icon and its right-click list, which keeps the taskbar pin working after updates.']));
body.push(H2('Updating to a newer version'));
body.push(P('Run the new ', ['Setup.exe', 'c'], '. It closes DigiApp Launcher if it is open, replaces the program, and keeps your profiles. (Portable version: replace ', ['DigiAppLauncher.exe', 'c'], ' and open it once.) If the taskbar right-click ever stops listing your profiles: unpin the icon, click ', ['Desktop Icon', 'b'], ' in the program, and pin the new desktop icon.'));
body.push(H2('Moving from the older PowerShell version'));
body.push(P('At the end of the setup, untick “Open DigiApp Launcher”. Press Win+R, type ', ['%APPDATA%\\DigiApp Launcher', 'c'], ' and press Enter (create the folder if Windows says it doesn’t exist). Copy your old ', ['DigiAppLauncher.json', 'c'], ' into it and rename the copy to ', ['settings.json', 'c'], ' (replace the file if asked). Then open DigiApp Launcher: your profiles, default profile and settings are brought across. Unpin the old taskbar icon and pin the new one.'));
body.push(H2('Uninstalling'));
body.push(P('Open ', ['Settings > Apps > Installed apps', 'b'], ', find ', ['DigiApp Launcher', 'b'], ', and choose ', ['Uninstall', 'b'], '. Your profiles stay in ', ['%APPDATA%\\DigiApp Launcher', 'c'], ' in case you reinstall; delete that folder to remove them too. (Portable version: unpin the icon and delete the program folder and desktop icon.)'));

// 3 Linux install
body.push(H1('3. Installing on Linux'));
body.push(H2('Install'));
body.push(...steps([
  ['Save ', ['DigiApp-Launcher-' + VER + '-Linux.tar.gz', 'c'], ' in your ', ['Downloads', 'b'], ' folder. Don’t unpack it yourself; the commands do that.'],
  ['Open a terminal with ', ['Ctrl+Alt+T', 'b'], '.'],
  ['Copy the three lines below, paste them into the terminal (all at once) and press ', ['Enter', 'b'], ':'],
]));
body.push(...cmds(LINUX_BLOCK));
body.push(...steps2([
  ['If it lists missing packages, press ', ['Enter', 'b'], ' to install them and type your password when asked. (It knows Ubuntu, Mint and Debian, Fedora, Arch and openSUSE.)'],
  ['It asks whether to add optional drag-and-drop support. Press Enter to skip, or type ', ['y', 'c'], ' to add it (needs internet).'],
  ['Press Enter when asked to open DigiApp Launcher now, then continue with section 4.'],
]));
body.push(P('The program is placed in your ', ['Applications', 'b'], ' folder (', ['~/Applications/DigiApp-Launcher', 'c'], ').'));
body.push(H2('AmRRON-style setup: keeping it in your Radio folder'));
body.push(P('If you keep your radio programs in a ', ['Radio', 'b'], ' folder in your home folder, DigiApp Launcher can live there too:'));
body.push(table([2200, 7160], ['Situation', 'Command (type in a terminal)'], [
  [['New or already installed', 'b'], [['bash ~/Applications/DigiApp-Launcher/linux_install.sh --radio', 'c']]],
]));
body.push(gap());
body.push(P('Either way the program moves to ', ['~/Radio/DigiApp-Launcher', 'c'], ', the menu, desktop and panel icons are updated to the new place, the old copy is removed, and your profiles are kept. Don’t move or rename that folder by hand afterwards — run the command again instead.'));
body.push(H2('The panel or dock icon'));
body.push(P('The installer puts DigiApp Launcher in your applications menu, on the desktop, and on your panel or dock:'));
body.push(...bullets([
  [['Linux Mint (Cinnamon), Ubuntu and other GNOME desktops:', 'b'], ' added to the panel or dock automatically.'],
  [['KDE, XFCE, MATE and others:', 'b'], ' the installer prints the one step to pin it yourself (for example on KDE: right-click it in the menu > Pin to Task Manager).'],
]));
body.push(P('Click the panel/dock icon to open your default profile. Right-click it for your other profiles, ', ['Close Open Apps', 'b'], ', and ', ['Edit apps and profiles', 'b'], '.'));
body.push(P('The installer also adds a second icon, ', ['DigiApp Launcher - Edit', 'b'], ', to your desktop and menu. Double-click it to change your apps and profiles — it opens the editor only and doesn’t start any of your programs.'));
body.push(note('Linux Mint:', ['if right-clicking the panel icon doesn’t list your profiles yet, press ', ['Ctrl + Alt + Esc', 'b'], ' once to refresh Cinnamon (your open windows are not affected).']));
body.push(gap());
body.push(note('Desktop icon:', ['if it shows as “Untrusted”, right-click it and choose ', ['Allow Launching', 'b'], '. On Linux Mint, double-click it and choose ', ['Mark as Trusted', 'b'], '.']));
body.push(gap());
body.push(note('Minimize and Wayland:', ['Linux Mint uses an Xorg (X11) desktop, where everything works. Ubuntu 22.04+, Fedora and KDE often start a “Wayland” desktop instead, which can stop Minimize from working for some programs. If that happens, log out and pick the ', ['Xorg / X11', 'b'], ' session on the login screen (on Ubuntu: the gear icon > ', ['Ubuntu on Xorg', 'b'], ').']));
body.push(H2('Updating and uninstalling'));
body.push(P('To update, close DigiApp Launcher, save the new package in ', ['Downloads', 'b'], ' and paste the same three lines again (section 3, Install).'));
body.push(P(['update_linux.sh', 'c'], ' updates DigiApp Launcher wherever it is installed (standard folder or ', ['~/Radio', 'c'], ') and keeps your profiles. To check the installed version (the editor\u2019s title bar shows it too):'));
body.push(...cmds(['grep __version__ ~/Applications/DigiApp-Launcher/digiapp/__init__.py']));
body.push(P('(With the ', ['~/Radio', 'c'], ' setup the folder is ', ['~/Radio/DigiApp-Launcher', 'c'], '.)'));
body.push(P('To remove the program, paste this in a terminal. It removes the program (from the standard folder or ', ['~/Radio', 'c'], ') with its menu, desktop and panel icons, and asks whether to keep your saved profiles \u2014 Enter keeps them:'));
body.push(...cmds(['bash "$(ls -d ~/Applications/DigiApp-Launcher ~/Radio/DigiApp-Launcher ~/.local/share/digiapp-launcher 2>/dev/null | head -n 1)"/linux_uninstall.sh']));
body.push(P('Terminal users can also start it with ', ['digiapp-launcher', 'c'], ' (editor), ', ['digiapp-launcher --run', 'c'], ' (default profile) or ', ['digiapp-launcher --close', 'c'], '.'));

// 4 Using
body.push(H1('4. Using DigiApp Launcher'));
body.push(P(['The screenshots come from Windows and Linux; DigiApp Launcher looks and works the same on both.', 'i']));
body.push(H2('The main window'));
body.push(...picture('editor.png', 624, 419, 'The DigiApp Launcher editor (Windows, dark theme)'));
body.push(table([2300, 7060], ['Part', 'What it does'], [
  [['Default (top)', 'b'], 'The profile that a plain click on the taskbar/dock icon opens.'],
  [['Light Theme / Dark Theme', 'b'], 'Switches between the dark and the light look. The window reopens in the new colours in about a second; your choice is remembered.'],
  [['Profile list', 'b'], 'Choose which profile to view and edit. The default has a ★ star.'],
  [['Open', 'b'], 'Green tick = this program opens with the profile. Untick to leave it out without removing it.'],
  [['App', 'b'], 'The name shown in messages. Click to type a different name.'],
  [['Program location', 'b'], 'Where the program is. Double-click to browse for it. A red row means the program can’t be found.'],
  [['Options', 'b'], 'Optional extra settings passed to the program (most people leave this empty).'],
  [['Wait (sec)', 'b'], 'Seconds to wait after this program opens, before opening the next one.'],
  [['Minimize', 'b'], 'Blue tick = the program starts minimized to the taskbar.'],
]));
body.push(gap());
body.push(P('Prefer a light window? Click ', ['Light Theme', 'b'], ' at the right of the row of buttons under the list; click ', ['Dark Theme', 'b'], ' to go back.'));
body.push(...picture('editor_light.png', 500, 318, 'The light theme (Linux shown)'));
body.push(H2('Adding your programs'));
body.push(P('Click ', ['+ Add App', 'b'], ' and choose one of:'));
body.push(...picture('addmenu_arrow.png', 522, 120, 'The + Add App menu'));
body.push(...bullets([
  [['Browse for a program…', 'b'], ' — pick the program file yourself (.exe on Windows; a program, AppImage, .py or .sh script on Linux).'],
  [['Pick from installed apps…', 'b'], ' — a searchable list of the programs in your Start menu (Windows) or Applications menu (Linux). Type a few letters, then double-click the one you want.'],
]));
body.push(...picture('picker.png', 276, 312, 'Pick from installed apps — type to search'));
body.push(H3('Drag and drop'));
body.push(P(['The quickest way to add a program', 'b'], ' you already have an icon for: drag its icon from the desktop and drop it anywhere on the list of programs.'));
body.push(...picture('dragdrop_arrow.png', 560, 181, 'Drag a desktop icon (here JS8FastChat) onto the list: it is added at the bottom'));
body.push(...bullets([
  ['The program is added at the bottom of the list, ticked, with a 2-second wait. Its ', ['App', 'b'], ' name is the icon\u2019s name, and the program location and any options are read from the icon itself.'],
  ['Several icons can be dropped at once; each becomes its own row.'],
  ['Then click the name to change it, use ', ['Move Up', 'b'], ' / ', ['Move Down', 'b'], ' to put it in order, and set its wait time.'],
  [['Windows:', 'b'], ' works with desktop and Start-menu shortcuts, and with .exe files dragged from File Explorer.'],
  [['Linux:', 'b'], ' works with desktop launchers and menu entries (.desktop files), AppImages and scripts dragged from the file manager \u2014 if you said yes to the drag-and-drop add-on when installing. To add it later: ', ['python3 -m pip install --user tkinterdnd2', 'c'], ', then reopen DigiApp Launcher.'],
]));
body.push(H2('Order, wait times and minimize'));
body.push(...bullets([
  ['Click a program in the list (it turns blue), then use ', ['Move Up', 'b'], ' / ', ['Move Down', 'b'], ' to set the order. Put rig control (for example Flrig) first.'],
  ['Click the number in ', ['Wait (sec)', 'b'], ' and type a new value. Give rig control enough time to connect to the radio — 15 seconds is a good start.'],
  ['Tick ', ['Minimize', 'b'], ' for programs you don’t need to see. If a program pops itself back up while starting, the launcher minimizes it again for a few seconds.'],
  [['Remove App', 'b'], ' (or the Delete key) takes the selected program out of this profile. It never deletes the program itself.'],
  [['Check All', 'b'], ' / ', ['Uncheck All', 'b'], ' tick or untick every program’s Open box.'],
]));
body.push(note('Saving:', ['there is no Save button — every change is saved automatically as you make it.'], 'EAF6EE', GREEN));

body.push(H2('Profiles'));
body.push(table([2300, 7060], ['Button', 'What it does'], [
  [['New Profile', 'b'], 'Starts a new, empty profile.'],
  [['Clone', 'b'], 'Copies the current profile (programs, order, wait times) so you can change the copy — the quickest way to make a variation.'],
  [['Rename', 'b'], 'Renames the current profile.'],
  [['Delete Profile', 'b'], 'Deletes the whole profile and its program list (asks first, with No pre-selected). To take out just one program, use Remove App instead.'],
  [['★ Set as Default', 'b'], 'Makes the current profile the one a plain icon click opens. Shows “★ Default” when you are viewing the default.'],
]));

body.push(H2('Launching'));
body.push(P('There are three ways to start a profile:'));
body.push(...bullets([
  [['Click the taskbar/dock icon', 'b'], ' — opens the default profile.'],
  [['Right-click the icon', 'b'], ' and choose a profile name — opens that profile.'],
  [['LAUNCH', 'b'], ' in the editor — opens the profile you are looking at.'],
]));
body.push(P('A small window shows each program opening and counts down the wait before the next one. ', ['STOP', 'b'], ' halts the sequence; programs already open stay open. The window closes itself when everything is running.'));
body.push(...picture('launching.png', 354, 147, 'Launching: counting down before the next program'));
body.push(note('Skip apps that are already open:', ['when ticked (recommended), programs that are already running are not opened a second time.']));

body.push(H2('Closing apps'));
body.push(P(['Close Open Apps', 'b'], ' closes the programs of the profile you launched last, one at a time in ', ['reverse order', 'b'], ', so rig control closes last. Start it either way:'));
body.push(...bullets([
  [['From the taskbar or panel:', 'b'], ' right-click the gold DigiApp Launcher icon and choose ', ['Close Open Apps', 'b'], '. The editor doesn\u2019t need to be open.'],
  [['From the editor:', 'b'], ' click ', ['CLOSE APPS', 'b'], '.'],
]));
body.push(...picture('taskbar_menu_arrows.png', 254, 320, 'Right-click the gold icon (Windows taskbar shown; the Linux panel is the same) and choose Close Open Apps'));
body.push(P('Then, for each program:'));
body.push(...bullets([
  'Each program is closed the normal way (like clicking its X), so it can save its settings.',
  ['If a program asks a question such as “Save changes?” or “Confirm quit?”, the launcher brings it to the front and waits up to a minute for your answer (see below).'],
  'Some programs take a few seconds to finish after their window disappears; the status line says so and moves on when they are done.',
  'If a program still won’t close, you are asked whether to force it closed (it won’t get to save) or leave it open.',
  'Programs that only hide in the system tray when their window closes (LocalSend, for example) are asked to stop about 10 seconds later.',
  ['Web pages a program opens in your browser (such as JS8Map Spotter’s map) are ', ['not', 'b'], ' closed, so your other browser tabs are never touched.'],
]));
body.push(note('Tip:', ['the launcher recognises a program most reliably when it started it itself. Open your programs with DigiApp Launcher, and Close Open Apps will find them even when they run under a different name (programs started through a small script, and Flatpak apps such as LocalSend).']));
body.push(...picture('closing.png', 354, 147, 'Closing: each finished program is ticked off'));
body.push(H3('Programs that ask before closing'));
body.push(P('Some programs (Fldigi, for example) ask you to confirm before they close, or whether to save changes. DigiApp Launcher brings that program\u2019s window to the front and waits for your answer:'));
body.push(...picture('confirm_quit_arrow.png', 366, 130, 'A program asking before it closes: click Yes'));
body.push(...bullets([
  [['Yes', 'b'], ' (or ', ['Save', 'b'], ') \u2014 the program closes, and DigiApp Launcher carries on closing the rest of the profile.'],
  [['No', 'b'], ' or ', ['Cancel', 'b'], ' \u2014 the program stays open. After about a minute DigiApp Launcher asks whether to force it closed or leave it open, then carries on with the next one.'],
  'While a program is waiting for your answer, DigiApp Launcher never clicks anything for you and never forces it closed without asking.',
]));
body.push(note('Didn\u2019t close?', ['the window lists what happened to each program. The full record is in ', ['close-log.txt', 'c'], ' in the settings folder (Windows ', ['%APPDATA%\\DigiApp Launcher', 'c'], ', Linux ', ['~/.config/digiapp-launcher', 'c'], ') \u2014 attach it when you report a problem at ', [REPO + '/issues', 'b'], '.']));

body.push(H2('The Desktop Icon button'));
body.push(table([2600, 6760], ['Button shows', 'Meaning'], [
  [['Desktop Icon (gold)', 'b'], 'No icon yet. Click to create the desktop/menu icon, then pin it (sections 2 and 3).'],
  [['✔ Icon Up to Date', 'b'], 'The icon and its right-click profile list match your current setup. Click any time to refresh it.'],
]));
body.push(H2('Finding missing programs'));
body.push(P('Rows turn ', ['red', 'b'], ' when the program can\u2019t be found \u2014 for example after a program was reinstalled somewhere else, or when you copied your settings to another PC. Fix one row by double-clicking its program location and browsing to the program, or fix them all at once with ', ['Find Missing Apps', 'b'], '.'));
body.push(P(['Find Missing Apps', 'b'], ' goes through ', ['every profile', 'b'], ', not only the one showing:'));
body.push(...steps([
  'If another profile already has a program with the same name and a working location, that location is used.',
  ['Otherwise it searches the usual places for a program whose file name starts with the name in the ', ['App', 'b'], ' column. Windows: Program Files, Program Files (x86), your Programs, Desktop, Documents and Downloads folders, and the top of C:\\. Linux: the programs on your system\u2019s path, then ~/Applications, ~/Downloads, ~/bin, ~/.local/bin, /opt and your home folder.'],
  'Every program it finds is saved straight away. The status line then says All apps located, or lists the ones it couldn\u2019t find \u2014 double-click those red rows and browse to them.',
]));
body.push(note('Tip:', ['it searches by the ', ['App', 'b'], ' name, ignoring spaces and punctuation. ', ['JS8Call', 'b'], ' finds JS8Call.exe, but ', ['flrig 2.0.09', 'b'], ' won\u2019t find flrig.exe \u2014 rename that row to just flrig first. If more than one version of a program is installed, check the location it picked.']));

// 5 Troubleshooting
body.push(H1('5. Troubleshooting'));
body.push(table([3300, 6060], ['Problem', 'What to do'], [
  [['Windows: “Windows protected your PC”', 'b'], 'Click More info > Run anyway. This appears because the program isn’t code-signed.'],
  [['Taskbar right-click shows no profiles', 'b'], 'Open the editor once. If still missing: unpin the icon, click Desktop Icon, and pin the new desktop icon.'],
  [['A program opens before the radio is ready', 'b'], 'Increase the Wait (sec) value for the program before it (usually the rig control program).'],
  [['Minimize doesn’t work (Linux)', 'b'], 'Make sure wmctrl and xdotool are installed. On Wayland desktops (Ubuntu 22.04+, Fedora, KDE), log in with the Xorg / X11 session.'],
  [['Linux: icon not on the panel', 'b'], 'Open the applications menu, right-click DigiApp Launcher and choose Add to panel / Pin to Dash / Add to Favorites.'],
  [['Linux Mint: right-click shows no profiles, or old wording', 'b'], 'Press Ctrl + Alt + Esc once to refresh Cinnamon.'],
  [['Right-click Edit doesn’t open the editor', 'b'], 'Double-click the DigiApp Launcher - Edit icon on the desktop or in the menu instead.'],
  [['A program won’t close (Windows)', 'b'], 'If it runs “as administrator”, Windows blocks other programs from closing it — the launcher tells you when this happens. Turn off “Run this program as an administrator” in that program’s shortcut Properties > Compatibility.'],
  [['A row is red', 'b'], 'The program has moved or been removed. Double-click its location to browse for it, or use Find Missing Apps.'],
  [['Linux: desktop icon says Untrusted', 'b'], 'Right-click it > Allow Launching.'],
  [['Close Open Apps says a program is “Not running”, but it is open', 'b'], 'Close it yourself this time, then open it with DigiApp Launcher from now on, so the launcher remembers it. Make the program’s name in the list match the words in its window title. If it still happens, report it with the close log (next row).'],
  [['Something else odd while closing', 'b'], ['Open an issue at ', [REPO + '/issues', 'b'], ' and attach the close log: ', ['close-log.txt', 'c'], ' in your settings folder (Windows: press Win+R, type ', ['%APPDATA%\\DigiApp Launcher', 'c'], '; Linux: ', ['~/.config/digiapp-launcher', 'c'], ').']],
]));

// 6 Quick reference
body.push(H1('6. Quick reference'));
body.push(table([3400, 5960], ['I want to…', 'Do this'], [
  ['Start my usual programs', 'Click the gold taskbar/dock icon'],
  ['Start a different combination', 'Right-click the icon > choose the profile'],
  ['Shut everything down', 'Right-click the icon > Close Open Apps'],
  ['Change programs or wait times', 'Right-click the icon > Edit apps and profiles (or double-click the DigiApp Launcher - Edit icon)'],
  ['Make a variation of a profile', 'Clone, then edit the copy'],
  ['Change which profile one click opens', 'View that profile > ★ Set as Default'],
  ['Take one program out of a profile', 'Select it > Remove App'],
  ['Keep a program off the screen', 'Tick its Minimize box'],
  ['Get the newest version', 'Download it from ' + REPO + '/releases/latest'],
  ['Report a problem or ask a question', 'Open an issue at ' + REPO + '/issues'],
]));
body.push(gap());
body.push(P(['73 and enjoy the one-click startup!', 'i']));

// ---------- document
const doc = new Document({
  creator: 'DigiApp Launcher', title: 'DigiApp Launcher ' + VER + ' - Install and User Guide',
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 36, bold: true, font: FONT, color: NAVY },
        paragraph: { spacing: { before: 120, after: 200 }, outlineLevel: 0,
          border: { bottom: { style: BorderStyle.SINGLE, size: 12, color: GOLD, space: 4 } } } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 28, bold: true, font: FONT, color: '1F3A5F' },
        paragraph: { spacing: { before: 280, after: 120 }, outlineLevel: 1, keepNext: true } },
      { id: 'Heading3', name: 'Heading 3', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 24, bold: true, font: FONT, color: '1F3A5F' },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2, keepNext: true } },
    ],
  },
  numbering: { config: numberingConfigs },
  features: { updateFields: true },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1300, bottom: 1300, left: 1440, right: 1440 } },
      titlePage: true },
    headers: {
      default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
        children: [t('DigiApp Launcher ' + VER + ' — Install and User Guide', { size: 16, color: GREY })] })] }),
      first: new Header({ children: [new Paragraph({ children: [] })] }),
    },
    footers: {
      default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER,
        children: [t('Page ', { size: 16, color: GREY }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: GREY, font: FONT })] })] }),
      first: new Footer({ children: [new Paragraph({ children: [] })] }),
    },
    children: body,
  }],
});

Packer.toBuffer(doc).then((buf) => {
  const out = process.argv[2] || path.join(__dirname, '..', 'docs', 'DigiApp-Launcher-Guide.docx');
  fs.writeFileSync(out, buf);
  console.log('wrote', out);
});
