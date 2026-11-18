# -*- coding: utf-8 -*-
"""
DigiApp Launcher - opens your digital-mode radio apps in order, waiting between each one.
One program for Windows and Linux (Ubuntu 16.04 and newer). Python 3.5+.

Started through run_digiapp.py (or "python3 -m digiapp", or DigiAppLauncher.exe):
    (no options)              -> editor (set up apps and profiles)
    --run [--profile X]       -> launch the default profile (or profile X)
    --close [--profile X]     -> close the last-launched profile's apps, last one first
    --install-icon            -> create the menu / desktop icon
    --pin / --unpin           -> add / remove the panel or dock icon (Linux)

Settings live in your own user folder (never next to the program), so the program
folder can be shared without any of your data:
    Linux:   ~/.config/digiapp-launcher/settings.json
    Windows: %APPDATA%\\DigiApp Launcher\\settings.json
"""

import json
import os
import re
import shlex
import sys
import time

from digiapp import APP_TITLE, BUILD_DATE, __version__ as VERSION
DEFAULT_WAIT = 2
SETTLE_SECONDS = 8          # keep a minimized app down this long, in case it pops itself back up
TRAY_WAIT = 10              # an app whose window closed but that still runs this long is asked to stop
HELPER_GRACE = 3            # the program that owned the window has ended: leftover windowless helpers get this long

IS_WINDOWS = sys.platform.startswith('win')
if IS_WINDOWS:
    from digiapp import plat_windows as plat
else:
    from digiapp import plat_linux as plat

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog
except ImportError:
    sys.stderr.write('DigiApp Launcher needs Tkinter.\nOn Ubuntu: sudo apt install python3-tk\n')
    sys.exit(1)

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES      # optional: drag and drop
except Exception:
    TkinterDnD = None
    DND_FILES = None

FROZEN = getattr(sys, 'frozen', False)
# HERE = the folder holding run_digiapp.py and the icons (one level above this package),
# or the folder of DigiAppLauncher.exe in a Windows build.
HERE = os.path.dirname(os.path.abspath(sys.executable)) if FROZEN else \
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = getattr(sys, '_MEIPASS', HERE)
ICON_ICO, ICON_PNG = 'icon.ico', 'icon.png'
SUN, MOON = '\u2600', '\u263E'
STAR = u'★'
CHECK = u'✔'


def res_path(name):
    for d in (RES, HERE):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return os.path.join(HERE, name)


def launch_cmd():
    """Command line that starts this program again (used by the menu/taskbar icon)."""
    if FROZEN:
        return [sys.executable]
    script = os.path.join(HERE, 'run_digiapp.py')
    if IS_WINDOWS:
        pyw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
        return [pyw if os.path.exists(pyw) else sys.executable, script]
    py = '/usr/bin/python3' if os.path.exists('/usr/bin/python3') else sys.executable
    return [py, script]


def icon_for_menu():
    if IS_WINDOWS:
        return sys.executable if FROZEN else res_path(ICON_ICO)
    if FROZEN:      # a packaged build unpacks to a temporary folder, so keep a lasting copy of the icon
        keep = os.path.join(plat.config_dir(), ICON_PNG)
        try:
            if not os.path.exists(keep):
                import shutil
                if not os.path.isdir(plat.config_dir()):
                    os.makedirs(plat.config_dir())
                shutil.copyfile(res_path(ICON_PNG), keep)
            return keep
        except Exception:
            pass
    return res_path(ICON_PNG)


# ======================================================================== settings
class Store(object):
    def __init__(self):
        self.dir = plat.config_dir()
        self.path = os.path.join(self.dir, 'settings.json')
        self.profiles = []
        self.default = ''
        self.last_launched = ''
        self.skip_running = True
        self.theme = 'Dark'
        self.first_run = False
        self.welcomed = True
        self.bad_copy = ''
        self.load()

    @staticmethod
    def clean_app(a):
        try:
            d = int(a.get('Delay', DEFAULT_WAIT))
        except Exception:
            d = DEFAULT_WAIT
        return {'Enabled': bool(a.get('Enabled', True)), 'Name': str(a.get('Name') or ''),
                'Path': str(a.get('Path') or ''), 'Args': str(a.get('Args') or ''),
                'Delay': max(0, d), 'Minimize': bool(a.get('Minimize', False))}

    def load(self):
        data = None
        sources = [self.path]
        if IS_WINDOWS:   # one-time import of the older PowerShell version's settings, if copied next to the exe
            sources.append(os.path.join(HERE, 'DigiAppLauncher.json'))
        for src in sources:
            if data is None and os.path.exists(src):
                try:
                    with open(src, 'r', encoding='utf-8-sig') as f:
                        data = json.load(f)
                except Exception:
                    data = None
                    if src == self.path:
                        self.keep_bad_copy()
        if not data or not data.get('Profiles'):
            data = {'DefaultProfile': 'My Profile', 'SkipRunning': True,
                    'Profiles': [{'Name': 'My Profile', 'Apps': []}]}
            self.first_run = True
        for p in data.get('Profiles') or []:
            if p and p.get('Name'):
                apps = p.get('Apps') or []
                if isinstance(apps, dict):
                    apps = [apps]
                self.profiles.append({'Name': str(p['Name']), 'Apps': [self.clean_app(a) for a in apps if a]})
        if not self.profiles:
            self.profiles.append({'Name': 'My Profile', 'Apps': []})
        names = [p['Name'] for p in self.profiles]
        self.default = data.get('DefaultProfile') or data.get('LastProfile') or names[0]
        if self.default not in names:
            self.default = names[0]
        self.last_launched = data.get('LastLaunched') or self.default
        if self.last_launched not in names:
            self.last_launched = self.default
        self.skip_running = data.get('SkipRunning', True) is not False
        self.theme = 'Light' if data.get('Theme') == 'Light' else 'Dark'
        self.welcomed = bool(data.get('Welcomed', not self.first_run))
        if self.first_run or not os.path.exists(self.path):
            self.save()

    def keep_bad_copy(self):
        """settings.json can't be read (edited by hand, disk trouble): keep it as settings-unreadable-<time>.json
        before a fresh one is written, so the profiles in it are never lost."""
        try:
            bad = os.path.join(self.dir, 'settings-unreadable-%s.json' % time.strftime('%Y%m%d-%H%M%S'))
            os.replace(self.path, bad)
            self.bad_copy = bad
        except Exception:
            pass

    def save(self):
        data = {'DefaultProfile': self.default, 'LastLaunched': self.last_launched,
                'SkipRunning': self.skip_running, 'Welcomed': self.welcomed, 'Theme': self.theme,
                'Profiles': self.profiles}
        try:
            if not os.path.isdir(self.dir):
                os.makedirs(self.dir)
            tmp = self.path + '.tmp'
            with open(tmp, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, self.path)
            return True
        except Exception:
            return False

    def get(self, name):
        for p in self.profiles:
            if p['Name'] == name:
                return p
        return None

    def menu_entries(self):
        entries = []
        for p in self.profiles:
            title = p['Name']
            if p['Name'] == self.default:
                title = STAR + ' ' + p['Name'] + '   (default)'
            entries.append((title, ['--run', '--profile', p['Name']]))
        entries.append(('-', None))
        entries.append(('Close Open Apps', ['--close']))
        entries.append(('Edit apps and profiles...', []))
        return entries

    def refresh_menu(self, write_icons=False):
        try:
            if write_icons or plat.icon_installed():
                plat.refresh_menu(launch_cmd(), icon_for_menu(), self.menu_entries(), write_icons)
            return True
        except Exception:
            return False


# ======================================================================== finding running apps
def split_args(args):
    try:
        return shlex.split(args or '', posix=not IS_WINDOWS)
    except Exception:
        return (args or '').split()


def is_interpreter(name):
    """python3, python3.12, bash, sh, java, wine... (name is a lower-case file name)."""
    return name in plat.INTERPRETERS or bool(re.match(r'^pythonw?[\d.]*(\.exe)?$', name))


def first_program_arg(args):
    """First argument that isn't an option or a VAR=value setting."""
    for a in args:
        a = a.strip('"')
        if not a or a.startswith('-') or re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', a):
            continue
        return a
    return ''


def target_from_command(cmd):
    """For  bash -c 'cd /some/dir && python3 app.py'  -> /some/dir/app.py"""
    cwd, last = None, []
    for part in re.split(r'&&|\|\||;|\|', cmd):
        try:
            toks = shlex.split(part, posix=not IS_WINDOWS)
        except Exception:
            toks = part.split()
        while toks and (toks[0] in ('exec', 'nohup', 'env', 'command') or
                        (re.match(r'^[A-Za-z_][A-Za-z0-9_]*=', toks[0]))):
            toks = toks[1:]
        if not toks:
            continue
        if toks[0] == 'cd' and len(toks) > 1:
            cwd = os.path.expanduser(toks[1].strip('"'))
            continue
        last = toks
    if not last:
        return ''
    t = first_program_arg(last[1:]) if is_interpreter(plat.base(last[0])) else last[0]
    if t and cwd and not os.path.isabs(os.path.expanduser(t)):
        t = os.path.join(cwd, t)
    return os.path.normpath(os.path.expanduser(t)) if t else ''


def flatpak_app_id(app):
    """org.localsend.localsend_app for  flatpak run [options] org.localsend.localsend_app ...  , else ''."""
    if plat.base(app.get('Path', '')) not in ('flatpak', 'flatpak.exe'):
        return ''
    args = split_args(app.get('Args', ''))
    if 'run' not in args:
        return ''
    for a in args[args.index('run') + 1:]:
        if a.startswith('-') or a in ('@@', '@@u'):
            continue
        return a
    return ''


def app_target(app):
    """The file that identifies a running copy of this app (the script, for interpreters;
    the app id, for Flatpak apps)."""
    fid = flatpak_app_id(app)
    if fid:
        return fid
    path = plat.resolve(app.get('Path', ''))
    if not path:
        return ''
    if is_interpreter(plat.base(path)):
        args = split_args(app.get('Args', ''))
        for flag in ('-c', '/c', '/C', '/k', '/K'):        # bash -c '...'  /  cmd /c ...
            if flag in args:
                i = args.index(flag)
                rest = ' '.join(args[i + 1:]) if flag.startswith('/') else (args[i + 1] if i + 1 < len(args) else '')
                t = target_from_command(rest)
                if t:
                    return t
        t = first_program_arg(args)
        if t:
            return t
    return path


class Launched(object):
    """Remembers the process id of each app the launcher started (launched.json next to the settings).
    Finds apps that run under a different name than the one in the list - for example a small script
    such as ~/.local/bin/fcc-lookup that hands over to  python3 FCC_Lookup.py . The process's start time
    is kept too, so a later, unrelated program that gets the same process id is never mistaken for the app."""

    @staticmethod
    def _path():
        return os.path.join(plat.config_dir(), 'launched.json')

    @staticmethod
    def key(app):
        return (app.get('Path') or '') + '\n' + (app.get('Args') or '')

    @classmethod
    def _load(cls):
        try:
            with open(cls._path(), 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @classmethod
    def record(cls, app, pid):
        if not pid:
            return
        started = plat.start_time(pid)
        if started is None:
            return
        data = cls._load()
        data = dict((k, v) for k, v in data.items() if cls._alive(v))       # forget programs that ended
        data[cls.key(app)] = [pid, started]
        try:
            if not os.path.isdir(plat.config_dir()):
                os.makedirs(plat.config_dir())
            with open(cls._path(), 'w', encoding='utf-8') as f:
                json.dump(data, f)
        except Exception:
            pass

    @staticmethod
    def _alive(entry):
        try:
            pid, started = entry
            return plat.start_time(pid) == started
        except Exception:
            return False

    @classmethod
    def pids(cls, app):
        """[pid] if the copy the launcher started is still running, else []."""
        entry = cls._load().get(cls.key(app))
        return [entry[0]] if entry and cls._alive(entry) else []


def running_pids(app, procs):
    """Processes of this app: found by program name, plus the copy the launcher started."""
    pids = find_app_pids(app, procs)
    return pids + [p for p in Launched.pids(app) if p not in pids]


SCRIPT_EXTS = ('.py', '.pyw', '.sh', '.jar', '.exe', '.appimage', '.bat', '.cmd', '.pl', '.rb', '.js')


def find_app_pids(app, procs):
    fid = flatpak_app_id(app)
    if fid:     # a running Flatpak app shows up as "bwrap ...", so it is found by its Flatpak app group
        finder = getattr(plat, 'flatpak_pids', None)
        return finder(fid) if finder else []
    tgt = app_target(app)
    if not tgt:
        return []
    tnorm = plat.norm(tgt)
    tbase = plat.base(tgt)
    use_norm = plat.base(tnorm) not in ('snap', 'env')
    is_script = tbase.endswith(SCRIPT_EXTS)
    hits = []
    for p in procs:
        if p.state in ('Z', 'X'):
            continue
        if use_norm and p.exe and plat.norm(p.exe) == tnorm:
            hits.append(p.pid)
            continue
        if not p.cmdline:
            continue
        if plat.base(p.cmdline[0]) == tbase:
            hits.append(p.pid)
            continue
        for a in p.cmdline[1:]:
            if (use_norm and plat.norm(a) == tnorm) or (is_script and plat.base(a) == tbase):
                hits.append(p.pid)
                break
    # Two apps can run the same program or script with different options (e.g. two copies of a
    # script with different --config). Then a process only counts if it has this app's options too.
    need = app_options(app)
    if need and hits:
        by_pid = dict((p.pid, p) for p in procs)
        hits = [h for h in hits if h in by_pid and
                all(opt in [c.strip('"') for c in by_pid[h].cmdline] for opt in need)]
    return hits


def app_options(app):
    """The options that set this app apart: everything after the program (or after the script, for
    an interpreter). None for  bash -c '...'  style commands, whose running program looks different."""
    args = [a.strip('"') for a in split_args(app.get('Args', ''))]
    if not args:
        return []
    path = plat.resolve(app.get('Path', ''))
    if is_interpreter(plat.base(path)):
        if any(f in args for f in ('-c', '/c', '/C', '/k', '/K')):
            return []
        tgt = first_program_arg(args)
        if tgt in args:
            return [a for a in args[args.index(tgt) + 1:] if a]
        return []
    return [a for a in args if a]


def window_key(app):
    """Lower-case program name, used to recognise windows that don't report their process."""
    b = plat.base(app_target(app))
    for ext in SCRIPT_EXTS:
        if b.endswith(ext):
            b = b[:-len(ext)]
            break
    return b if len(b) >= 3 else ''


def _flat(text):
    return re.sub(r'[^a-z0-9]', '', (text or '').lower())


def app_windows(app, fam, wins):
    """The app's windows: by process, or - for windows that don't say which process owns them -
    by the program's file name or the app's name in the list (e.g. "JS8Map Spotter" in its title)."""
    key = window_key(app)
    name = _flat(app.get('Name', ''))
    if len(name) < 5:
        name = ''
    own = 'digiapplauncher'
    found = []
    for wid, pid, cls in wins:
        if pid and pid in fam:
            found.append(wid)
        elif not pid and own not in _flat(cls) and ((key and key in cls) or (name and name in _flat(cls))):
            found.append(wid)
    return found


def family(roots, procs):
    fam = set(r for r in roots if r)
    grew = True
    while grew:
        grew = False
        for p in procs:
            if p.pid not in fam and p.ppid in fam:
                fam.add(p.pid)
                grew = True
    return fam


# ======================================================================== look and feel
# Two looks. Every colour the program draws comes from one of these tables (same keys in both).
# Fill colours (buttons, tick boxes) can be bright in both; *Text colours are for text on the window
# background and must stay readable on it - that is why the light theme darkens them.
THEMES = {
    'Dark': {
        'Header': '#070B14', 'Bg': '#0D1626', 'Field': '#0A1220', 'RowAlt': '#101B2E',
        'Line': '#22314A', 'Grid': '#5A6780', 'Head': '#2B3649', 'Select': '#2F6DB5',
        'Text': '#E8ECF3', 'Dim': '#8E9AB0', 'PathText': '#CFD8E6', 'Green': '#3DF58A',
        'Blue': '#2EA8E6', 'Orange': '#F5A524', 'Yellow': '#F5DC4E', 'Red': '#E5484D',
        'Halt': '#A51D1D', 'Missing': '#4A1D27', 'MissText': '#FFB8B8', 'Black': '#05080F',
        'Light': '#EEF1F6', 'White': '#FFFFFF',
        'GreenText': '#3DF58A', 'YellowText': '#F5DC4E', 'OrangeText': '#F5A524', 'BlueTick': '#05080F',
    },
    'Light': {
        'Header': '#DCE3EE', 'Bg': '#F3F5F9', 'Field': '#FFFFFF', 'RowAlt': '#EEF2F8',
        'Line': '#D3DAE5', 'Grid': '#98A3B5', 'Head': '#D5DCE8', 'Select': '#2F6DB5',
        'Text': '#141C2B', 'Dim': '#5B6678', 'PathText': '#1E2A40', 'Green': '#3DDC84',
        'Blue': '#1F7FBF', 'Orange': '#F5A524', 'Yellow': '#F5D53B', 'Red': '#C62828',
        'Halt': '#B42318', 'Missing': '#FBE1E4', 'MissText': '#A3161D', 'Black': '#05080F',
        'Light': '#FFFFFF', 'White': '#FFFFFF',
        'GreenText': '#0B7A3B', 'YellowText': '#7A5C00', 'OrangeText': '#A85A00', 'BlueTick': '#FFFFFF',
    },
}
COLORS = dict(THEMES['Dark'])
C = COLORS


def set_theme(name):
    """Use the 'Dark' or 'Light' colours for every window made after this call."""
    C.clear()
    C.update(THEMES.get(name, THEMES['Dark']))


def shade(hex_color, amount):
    """amount > 0 lightens, < 0 darkens."""
    h = hex_color.lstrip('#')
    rgb = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    if amount > 0:
        rgb = [int(v + (255 - v) * amount) for v in rgb]
    else:
        rgb = [int(v * (1 + amount)) for v in rgb]
    return '#%02x%02x%02x' % tuple(rgb)


class Fonts(object):
    def __init__(self, root):
        import tkinter.font as tkfont
        fams = set(f.lower() for f in tkfont.families(root))

        def pick(*names):
            for n in names:
                if n.lower() in fams:
                    return n
            return names[-1]
        ui = pick('Segoe UI', 'Ubuntu', 'DejaVu Sans', 'Liberation Sans', 'Helvetica')
        self.ui = (ui, 10)
        self.bold = (ui, 10, 'bold')
        self.big = (ui, 13, 'bold')
        self.title = (ui, 20, 'bold')
        self.profile = (ui, 11, 'bold')
        self.tip = (ui, 11, 'bold')
        # one font family everywhere (Segoe UI on Windows); these names are kept for the header/readouts,
        # the program locations and the status line
        self.mono = (ui, 11, 'bold')
        self.mono_small = (ui, 10, 'bold')
        self.status = (ui, 10, 'bold')
        self.row = (ui, 10)
        self.row_bold = (ui, 10, 'bold')


def make_button(parent, text, command, bg=None, fg=None, font=None, width=None, padx=12, pady=5):
    bg = bg or C['Head']
    fg = fg or C['Text']
    b = tk.Button(parent, text=text, command=command, bg=bg, fg=fg, font=font,
                  activebackground=shade(bg, 0.25), activeforeground=fg, relief='flat', bd=0,
                  highlightthickness=1, highlightbackground=shade(bg, 0.35), highlightcolor=shade(bg, 0.35),
                  padx=padx, pady=pady, cursor='hand2', disabledforeground=shade(fg, -0.4))
    if width:
        b.configure(width=width)
    return b


def restyle_button(b, bg, fg):
    b.configure(bg=bg, fg=fg, activebackground=shade(bg, 0.25), activeforeground=fg,
                highlightbackground=shade(bg, 0.35), highlightcolor=shade(bg, 0.35))


class CheckBox(tk.Canvas):
    """Colored square checkbox: filled with a check mark when on."""

    def __init__(self, parent, var, color, bg, command=None, size=20, tick=None):
        tk.Canvas.__init__(self, parent, width=size + 4, height=size + 4, bg=bg, highlightthickness=0,
                           bd=0, cursor='hand2')
        self.var, self.color, self.size, self.command = var, color, size, command
        self.tick = tick
        self.bind('<Button-1>', self._toggle)
        self.draw()

    def _toggle(self, _e=None):
        if str(self.cget('state')) == 'disabled':
            return
        self.var.set(not self.var.get())
        self.draw()
        if self.command:
            self.command()

    def set_bg(self, bg):
        self.configure(bg=bg)

    def draw(self):
        self.delete('all')
        s, o = self.size, 2
        if self.var.get():
            self.create_rectangle(o, o, o + s, o + s, fill=self.color, outline=self.color)
            self.create_line(o + 4, o + s * 0.52, o + s * 0.42, o + s - 5, o + s - 4, o + 5,
                             fill=self.tick or C['Black'], width=3, capstyle='round', joinstyle='round')
        else:
            self.create_rectangle(o, o, o + s, o + s, outline=C['Dim'], width=2)


def trace_var(var, cb):
    if hasattr(var, 'trace_add'):
        var.trace_add('write', lambda *a: cb())
    else:
        var.trace('w', lambda *a: cb())


def new_root():
    plat.prepare_process()
    if TkinterDnD is not None:
        try:
            root = TkinterDnD.Tk(className='DigiAppLauncher')
            root.dnd_ok = True
            _new_root_clean()
            return root
        except Exception:
            pass
    root = tk.Tk(className='DigiAppLauncher')
    root.dnd_ok = False
    _new_root_clean()
    return root


def _new_root_clean():
    """Tk has read its settings now; clear the one-file exe's temporary-folder settings so programs we start
    (and our own --close / theme restarts) don't use or lock that folder."""
    tidy = getattr(plat, 'clean_child_env', None)
    if tidy:
        tidy()


def set_icon(root):
    try:
        if IS_WINDOWS and os.path.exists(res_path(ICON_ICO)):
            root.iconbitmap(default=res_path(ICON_ICO))
        if os.path.exists(res_path(ICON_PNG)):
            img = tk.PhotoImage(file=res_path(ICON_PNG))
            root.iconphoto(True, img)
            root._icon_img = img
    except Exception:
        pass


# ======================================================================== launching / minimizing / closing
class MinimizeWatcher(object):
    """Many apps ignore 'start minimized'. Watch for each app's window and minimize it once it appears."""

    def __init__(self, root):
        self.root = root
        self.watches = []
        self.job = None

    def active(self):
        return bool(self.watches)

    def add(self, pid, app):
        if not plat.windows_supported():
            return
        try:
            wins = plat.list_windows()
            procs = plat.list_processes()
        except Exception:
            return
        self.watches.append({'pid': pid, 'app': app, 'until': time.time() + 45, 'seen': {},
                             'base_wins': set(w[0] for w in wins), 'base_pids': set(p.pid for p in procs)})
        if not self.job:
            self.job = self.root.after(400, self.tick)

    def tick(self):
        self.job = None
        now = time.time()
        try:
            wins = plat.list_windows()
            procs = plat.list_processes()
        except Exception:
            wins, procs = [], []
        for w in list(self.watches):
            roots = [w['pid']] + [p for p in find_app_pids(w['app'], procs) if p not in w['base_pids']]
            fam = family(roots, procs)
            # only windows that appeared after this app was started
            cands = [wid for wid in app_windows(w['app'], fam, wins) if wid not in w['base_wins'] or wid in w['seen']]
            for wid in cands:
                if wid not in w['seen']:
                    w['seen'][wid] = now
                    plat.minimize_window(wid)
                elif now - w['seen'][wid] < SETTLE_SECONDS:
                    plat.minimize_window(wid)         # the app put itself back up; minimize again
            settled = w['seen'] and all(now - t > SETTLE_SECONDS + 2 for t in w['seen'].values())
            if settled or now > w['until']:
                self.watches.remove(w)
        if self.watches:
            self.job = self.root.after(400, self.tick)


class LaunchJob(object):
    def __init__(self, root, apps, skip_running, watcher, status, progress, done):
        self.root, self.watcher = root, watcher
        self.queue = [a for a in apps if a.get('Enabled')]
        self.skip_running = skip_running
        self.status, self.progress, self.done = status, progress, done
        self.idx = 0
        self.launched, self.skipped, self.errors = [], [], []
        self.job = None
        self.running = False

    def start(self):
        self.running = True
        self.next_app()

    def stop(self):
        if self.job:
            self.root.after_cancel(self.job)
            self.job = None
        self.running = False

    def next_app(self):
        self.job = None
        while self.idx < len(self.queue):
            app = self.queue[self.idx]
            self.idx += 1
            self.progress(self.idx, len(self.queue))
            label = app['Name'] or os.path.basename(app['Path'])
            if not plat.path_exists(app['Path']):
                self.errors.append(label + ' - location not set or file not found')
                continue
            if self.skip_running:
                try:
                    if running_pids(app, plat.list_processes()):
                        self.skipped.append(label)
                        continue
                except Exception:
                    pass
            self.status('Opening ' + label + '...')
            try:
                pid = plat.launch(app['Path'], app['Args'], app['Minimize'])
            except Exception as e:
                self.errors.append(label + ' - ' + str(e))
                continue
            self.launched.append(label)
            Launched.record(app, pid)
            if app['Minimize'] and self.watcher:
                self.watcher.add(pid, app)
            if self.idx >= len(self.queue):
                break
            if app['Delay'] > 0:
                self.last_label = label
                self.remaining = app['Delay']
                self.countdown()
                return
        self.running = False
        msg = 'Done. Opened %d app(s).' % len(self.launched)
        if self.skipped:
            msg += ' Already open: ' + ', '.join(self.skipped) + '.'
        self.status(msg)
        self.done(self)

    def countdown(self):
        if not self.running:
            return
        if self.remaining <= 0:
            self.next_app()
            return
        nxt = self.queue[self.idx]['Name']
        self.status('Opened %s. Waiting %d sec, then opening %s...' % (self.last_label, self.remaining, nxt))
        self.remaining -= 1
        self.job = self.root.after(1000, self.countdown)


class CloseJob(object):
    """Closes apps one at a time, last-opened first, letting each one save and ask its questions."""

    def __init__(self, root, apps, status, progress, ask_force, done, inform=None):
        self.root = root
        self.queue = list(reversed([a for a in apps if a.get('Enabled')]))
        self.status, self.progress, self.ask_force, self.done = status, progress, ask_force, done
        self.inform = inform
        self.idx = 0
        self.closed, self.not_running, self.left_open = [], [], []
        self.phase = 'next'
        self.job = None
        self.running = False
        self.last_done = ''
        self.log = ['', '=== Close apps %s ===' % time.strftime('%Y-%m-%d %H:%M:%S')]

    def start(self):
        self.running = True
        self.job = self.root.after(100, self.tick)

    def stop(self):
        if self.job:
            self.root.after_cancel(self.job)
        self.job = None
        self.running = False
        self.write_log()

    def ask_windows(self, method):
        """Sends the close request to the app's windows; returns (windows asked, all blocked?)."""
        procs = plat.list_processes()
        alive = [p for p in self.pids if plat.is_alive(p)]
        fam = family(alive, procs)
        winlist = plat.list_windows()
        wins = app_windows(self.app, fam, winlist)
        if method == 'close':
            # the processes that own the app's windows - the program itself, as opposed to helpers it runs
            self.win_owners = set(pid for wid, pid, _t in winlist if wid in wins and pid)
        if method == 'syscommand':
            # don't knock again if the app is already showing a question (it would ask twice)
            if any(plat.window_busy(w) for w in wins) or len(wins) > self.first_count:
                self.log.append('  second try skipped: the app is showing a question')
                return len(wins), False
        else:
            self.first_count = len(wins)
        results = []
        for wid in wins:
            r = plat.close_window(wid, method)
            results.append(r)
            try:
                info = plat.window_info(wid)
            except Exception:
                info = ''
            self.log.append('  %s window %s %s -> %s' % (method, wid, info, r))
        if not wins:
            self.log.append('  %s: no windows found for processes %s' % (method, sorted(fam)))
        return len(wins), bool(results) and all(r == 'denied' for r in results)

    def tick(self):
        self.job = None
        if not self.running:
            return
        now = time.time()
        if self.phase == 'next':
            if self.idx >= len(self.queue):
                return self.finish()
            app = self.queue[self.idx]
            self.progress(self.idx, len(self.queue))
            procs = plat.list_processes()
            pids = running_pids(app, procs)
            self.log.append('%s: target %s, processes %s' % (app['Name'], app_target(app), pids))
            byid = dict((p.pid, p) for p in procs)
            for pid in pids:                      # which program each process is, for the log
                p = byid.get(pid)
                if p:
                    self.log.append('    %s = %s %s (started by %s)' % (pid, plat.base(p.exe or '') or '?',
                                                                   ' '.join((p.cmdline or [])[1:])[:80], p.ppid))
            self.window_only = False
            self.win_owners = set()
            self.gone_at = None
            self.stopped_tray = False
            if not pids:
                # No process found, but its window may still be open (a program started through a
                # helper script, or opened outside the launcher): close windows that carry its name.
                named = []
                if plat.windows_supported():
                    try:
                        named = app_windows(app, set(), plat.list_windows())
                    except Exception:
                        named = []
                if not named:
                    self.not_running.append(app['Name'])
                    self.idx += 1
                    self.job = self.root.after(50, self.tick)
                    return
                self.log.append('  no process found - closing its windows found by name: %s' % named)
                self.window_only = True
            self.pids, self.name, self.app = pids, app['Name'], app
            self.say('Closing %s...' % app['Name'])
            asked, blocked = 0, False
            if plat.windows_supported():
                asked, blocked = self.ask_windows('close')
            if blocked:
                self.log.append('  blocked by Windows (app runs as administrator)')
                if self.inform:
                    self.inform('Can\'t close ' + self.name,
                                "Windows won't let DigiApp Launcher close %s, because %s is running as "
                                "administrator.\n\nClose it yourself this time. To fix it for good, either "
                                "turn off \"Run as administrator\" for %s (its shortcut > Properties > "
                                "Compatibility), or run DigiApp Launcher as administrator too."
                                % (self.name, self.name, self.name))
                self.left_open.append(self.name)
                self.idx += 1
                self.gap_end = time.time() + 2
                self.phase = 'gap'
                self.job = self.root.after(500, self.tick)
                return
            self.pids = sorted(family(pids, procs))       # the app plus anything it started
            if not asked and not self.window_only:
                self.log.append('  no window found - asking processes %s to stop' % self.pids)
                plat.terminate(sorted(self.pids, reverse=True))
            self.started = now
            self.deadline = now + (60 if asked else 6)
            self.retry_at = now + 3
            self.retried = not asked
            self.reveal_at = now + 5
            self.revealed = False
            self.phase = 'wait'
        elif self.phase == 'wait':
            alive = [p for p in self.pids if plat.is_alive(p)]
            if self.window_only:        # nothing to watch but the window itself
                try:
                    still_open = bool(app_windows(self.app, set(), plat.list_windows()))
                except Exception:
                    still_open = True
            else:
                still_open = bool(alive)
            if not still_open:
                self.log.append('  closed after %.1f sec' % (now - self.started))
                self.closed.append(self.name)
                self.last_done = self.name
                self.progress(self.idx + 1, len(self.queue))
                self.say('')
                self.idx += 1
                self.gap_end = now + 2
                self.phase = 'gap'
            elif now > self.deadline and self.window_only:
                self.log.append('  window still open at the time limit (no process to stop)')
                self.left_open.append(self.name)
                self.idx += 1
                self.gap_end = time.time() + 2
                self.phase = 'gap'
            elif now > self.deadline:
                self.log.append('  still open at the time limit')
                force = self.ask_force(self.name)
                if force:
                    plat.force_kill(list(family(alive, plat.list_processes())))
                    self.closed.append(self.name + ' (forced)')
                else:
                    self.left_open.append(self.name)
                self.idx += 1
                self.gap_end = time.time() + 2
                self.phase = 'gap'
            else:
                if not self.retried and now > self.retry_at:
                    self.retried = True       # second try, the same way the window's X button does it
                    self.ask_windows('syscommand')
                if not self.revealed and now > self.reveal_at and plat.windows_supported():
                    self.revealed = True
                    try:
                        fam = family(alive, plat.list_processes())
                        plat.reveal_windows(app_windows(self.app, fam, plat.list_windows()))
                    except Exception:
                        pass
                left = int(self.deadline - now)
                try:
                    fam = family(alive, plat.list_processes())
                    has_window = bool(app_windows(self.app, fam, plat.list_windows())) if plat.windows_supported() else True
                except Exception:
                    has_window = True
                if has_window:
                    self.gone_at = None
                    self.say('Waiting for %s to close... If it asks a question, answer it in its window. (%d sec)'
                             % (self.name, left))
                else:
                    # Window gone but the program keeps running: many apps (LocalSend, chat programs...)
                    # only hide in the system tray when their window is closed. Give it a moment to
                    # finish on its own, then ask it to stop the normal way.
                    owners_left = [p for p in self.win_owners if plat.is_alive(p)]
                    if self.gone_at is None:
                        self.gone_at = now
                    elif self.win_owners and not owners_left and now - self.gone_at > HELPER_GRACE:
                        # The program that had the window has ended; what is left never had a window (a helper
                        # it started, or a launcher stub). Don't hold up the rest of the profile for it.
                        helpers = sorted(family(alive, plat.list_processes()), reverse=True)
                        self.log.append('  program ended after %.1f sec; helper processes %s still finishing - '
                                        'not waiting for them' % (now - self.started, helpers))
                        plat.terminate(helpers)          # Linux: polite stop; Windows: they end on their own
                        self.closed.append(self.name)
                        self.last_done = self.name
                        self.progress(self.idx + 1, len(self.queue))
                        self.say('')
                        self.idx += 1
                        self.gap_end = now + 2
                        self.phase = 'gap'
                        self.job = self.root.after(500, self.tick)
                        return
                    elif not self.stopped_tray and now - self.gone_at > TRAY_WAIT and alive:
                        self.stopped_tray = True
                        pids = sorted(family(alive, plat.list_processes()), reverse=True)
                        self.log.append('  window closed but still running (system tray?) - asking %s to stop' % pids)
                        plat.terminate(pids)
                    self.say('%s window closed - letting it finish shutting down...' % self.name)
        elif self.phase == 'gap':
            if now >= self.gap_end:
                self.phase = 'next'
        self.job = self.root.after(500, self.tick)

    def say(self, text):
        """Status: the app that just finished, then what is happening now."""
        lines = []
        if self.last_done:
            lines.append(CHECK + ' ' + self.last_done + ' closed')
        if text:
            lines.append(text)
        self.status('\n'.join(lines))

    def write_log(self):
        """Keeps a short record of the last few closes (close-log.txt next to the settings), for troubleshooting."""
        try:
            path = os.path.join(plat.config_dir(), 'close-log.txt')
            old = []
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    old = f.read().splitlines()[-300:]
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(old + self.log) + '\n')
            self.log = []
        except Exception:
            pass

    def finish(self):
        self.running = False
        self.write_log()
        self.progress(1, 1)
        msg = 'Done. Closed %d app(s).' % len(self.closed)
        if self.not_running:
            msg += ' Not running: ' + ', '.join(self.not_running) + '.'
        if self.left_open:
            msg += ' Left open: ' + ', '.join(self.left_open) + '.'
        self.status(msg)
        self.done(self)


def show_errors(parent, errors):
    if errors:
        messagebox.showwarning('Some apps did not open',
                               "These apps couldn't be opened:\n\n" + '\n'.join(errors) +
                               "\n\nOpen 'Edit apps and profiles' and check the red rows.", parent=parent)


# ======================================================================== quick launch / close window
def quick_window(store, mode, profile_name):
    if mode == 'close':
        name = profile_name if store.get(profile_name or '') else store.last_launched
    else:
        name = profile_name if store.get(profile_name or '') else store.default
        if name != store.last_launched:
            store.last_launched = name
            store.save()
            store.refresh_menu()
    prof = store.get(name)

    root = new_root()
    F = Fonts(root)
    root.title('%s - %s%s' % (APP_TITLE, 'closing ' if mode == 'close' else '', name))
    root.configure(bg=C['Bg'])
    root.resizable(False, False)
    set_icon(root)
    plat.style_window(root, launch_cmd() + ['--run'], res_path(ICON_ICO), dark=store.theme == 'Dark')

    verb, vcolor = ('CLOSING', C['OrangeText']) if mode == 'close' else ('LAUNCHING', C['GreenText'])
    head = tk.Frame(root, bg=C['Header'])
    head.pack(fill='x')
    tk.Label(head, text=verb, font=F.mono, fg=vcolor, bg=C['Header']).pack(side='left', padx=(16, 8), pady=12)
    tk.Label(head, text=name, font=(F.title[0], 15, 'bold'), fg=C['Text'], bg=C['Header']).pack(side='left', pady=8)

    body = tk.Frame(root, bg=C['Bg'])
    body.pack(fill='both', expand=True, padx=16, pady=(10, 12))
    status = tk.Label(body, text='', font=F.status, fg=C['GreenText'], bg=C['Bg'], anchor='w',
                      justify='left', wraplength=440, width=52, height=4)
    status.pack(fill='x')
    bar_back = tk.Frame(body, bg=C['Line'], height=8, width=440)
    bar_back.pack(fill='x', pady=(4, 12))
    bar_back.pack_propagate(False)
    bar = tk.Frame(bar_back, bg=vcolor, height=8, width=0)
    bar.place(x=0, y=0, relheight=1, width=0)
    btns = tk.Frame(body, bg=C['Bg'])
    btns.pack(fill='x')

    state = {'job': None, 'closing': False}

    def set_status(t):
        status.configure(text=t)
        root.update_idletasks()

    def set_progress(v, m):
        bar_back.update_idletasks()
        bar.place_configure(width=int(bar_back.winfo_width() * min(1.0, float(v) / max(1, m))))

    watcher = MinimizeWatcher(root)

    def auto_close():
        if watcher.active():
            root.after(1000, auto_close)
        else:
            root.destroy()

    def on_done(job):
        btn_stop.configure(text='Close')
        errs = getattr(job, 'errors', [])
        if errs:
            show_errors(root, errs)
        elif not getattr(job, 'left_open', []):
            status.configure(text=status.cget('text') + '  Closing...')
            root.after(3000, auto_close)

    def ask_force(app_name):
        return messagebox.askyesno('App still open',
                                   "%s is still open. It may be showing a question, so check its window first.\n\n"
                                   "Yes = force it closed (it won't get to save)\nNo = leave it open and carry on"
                                   % app_name, icon='warning', parent=root)

    def stop():
        job = state['job']
        if job and job.running:
            job.stop()
            what = 'Closed %d' % len(job.closed) if mode == 'close' else 'Opened %d' % len(job.launched)
            set_status('Stopped. %s app(s) before stopping.' % what)
            btn_stop.configure(text='Close')
        else:
            root.destroy()

    def edit():
        if state['job']:
            state['job'].stop()
        plat.run_detached(launch_cmd())
        root.destroy()

    btn_edit = make_button(btns, 'Edit Apps...', edit, font=F.bold)
    btn_edit.pack(side='right')
    btn_stop = make_button(btns, 'STOP', stop, C['Halt'], C['White'], F.bold)
    btn_stop.pack(side='right', padx=(0, 8))

    def begin():
        apps = [a for a in (prof['Apps'] if prof else []) if a.get('Enabled')]
        if not apps:
            set_status('This profile has no apps checked. Click Edit Apps to set it up.')
            btn_stop.configure(text='Close')
            return
        if mode == 'close':
            job = CloseJob(root, apps, set_status, set_progress, ask_force, on_done,
                           lambda t, m: messagebox.showwarning(t, m, parent=root))
        else:
            job = LaunchJob(root, apps, store.skip_running, watcher, set_status, set_progress, on_done)
        state['job'] = job
        job.start()

    root.update_idletasks()
    w, h = root.winfo_reqwidth(), root.winfo_reqheight()
    root.geometry('+%d+%d' % ((root.winfo_screenwidth() - w) // 2, (root.winfo_screenheight() - h) // 3))
    root.after(150, begin)
    root.mainloop()


# ======================================================================== editor
class AppRow(object):
    COLS = 6

    def __init__(self, editor, data):
        self.ed = editor
        p = editor.inner
        F = editor.F
        self.enabled = tk.BooleanVar(value=bool(data['Enabled']))
        self.minimize = tk.BooleanVar(value=bool(data['Minimize']))
        self.name = tk.StringVar(value=data['Name'])
        self.path = tk.StringVar(value=data['Path'])
        self.args = tk.StringVar(value=data['Args'])
        self.delay = tk.StringVar(value=str(data['Delay']))
        self.c_open = tk.Frame(p)
        self.cb_open = CheckBox(self.c_open, self.enabled, C['Green'], C['Field'], editor.changed)
        self.cb_open.place(relx=0.5, rely=0.5, anchor='center')
        ent = dict(relief='flat', bd=0, highlightthickness=0, insertbackground=C['Text'])
        self.e_name = tk.Entry(p, textvariable=self.name, font=F.row_bold, **ent)
        self.e_path = tk.Entry(p, textvariable=self.path, font=F.mono_small, **ent)
        self.e_args = tk.Entry(p, textvariable=self.args, font=F.mono_small, width=12, **ent)
        self.e_delay = tk.Entry(p, textvariable=self.delay, font=F.row_bold, width=5, justify='center', **ent)
        self.c_min = tk.Frame(p)
        self.cb_min = CheckBox(self.c_min, self.minimize, C['Blue'], C['Field'], editor.changed, tick=C['BlueTick'])
        self.cb_min.place(relx=0.5, rely=0.5, anchor='center')
        self.cells = [self.c_open, self.e_name, self.e_path, self.e_args, self.e_delay, self.c_min]
        for v in (self.name, self.path, self.args, self.delay):
            trace_var(v, editor.changed)
        for w in self.cells + [self.cb_open, self.cb_min]:
            w.bind('<Button-1>', self.select, add='+')
        self.e_path.bind('<Double-Button-1>', self.browse)
        self.e_path.bind('<FocusOut>', lambda e: editor.color_rows())
        self.selected = False

    def grid(self, r):
        for c, w in enumerate(self.cells):
            w.grid(row=r, column=c, sticky='nsew', padx=(0 if c == 0 else 1, 0), pady=(1, 0),
                   ipady=7 if isinstance(w, tk.Entry) else 0, ipadx=6 if isinstance(w, tk.Entry) else 0)
        self.c_open.configure(height=36)
        self.c_min.configure(height=36)
        self.e_path.after_idle(lambda: self.e_path.xview_moveto(1.0))

    def destroy(self):
        for w in self.cells:
            w.destroy()

    def data(self):
        try:
            d = max(0, int(self.delay.get().strip() or 0))
        except ValueError:
            d = DEFAULT_WAIT
        return {'Enabled': bool(self.enabled.get()), 'Name': self.name.get().strip(),
                'Path': self.path.get().strip().strip('"'), 'Args': self.args.get().strip(),
                'Delay': d, 'Minimize': bool(self.minimize.get())}

    def select(self, _e=None):
        self.ed.select_row(self)

    def browse(self, _e=None):
        if self.ed.busy():
            return 'break'
        cur = self.path.get().strip()
        start = os.path.dirname(plat.resolve(cur)) if cur else None
        f = plat.pick_file(self.ed.root, start)
        if f:
            name, prog, args = plat.read_dropped(f)
            self.path.set(prog)
            if args:
                self.args.set(args)
            self.ed.color_rows()
        return 'break'

    def paint(self, bg, fg, path_fg):
        for w in (self.c_open, self.c_min):
            w.configure(bg=bg)
        self.cb_open.set_bg(bg)
        self.cb_min.set_bg(bg)
        self.e_name.configure(bg=bg, fg=fg, readonlybackground=bg, disabledbackground=bg)
        self.e_path.configure(bg=bg, fg=path_fg, readonlybackground=bg, disabledbackground=bg)
        self.e_args.configure(bg=bg, fg=path_fg, readonlybackground=bg, disabledbackground=bg)
        self.e_delay.configure(bg=bg, fg=C['GreenText'] if fg != C['MissText'] else fg,
                               readonlybackground=bg, disabledbackground=bg)


class Editor(object):
    def __init__(self, store):
        self.store = store
        self.root = root = new_root()
        self.F = F = Fonts(root)
        self.rows = []
        self.current = None
        self.selected = None
        self.save_job = None
        self.loading = False
        self.job = None
        self.watcher = MinimizeWatcher(root)

        root.title('%s V%s - build %s' % (APP_TITLE, VERSION, BUILD_DATE))
        root.configure(bg=C['Bg'])
        root.minsize(1060, 600)
        set_icon(root)
        style = ttk.Style(root)
        try:
            style.theme_use('clam')
        except Exception:
            pass
        style.configure('Profile.TCombobox', fieldbackground=C['Light'], background=C['Light'],
                        foreground=C['Black'], arrowcolor=C['Black'], bordercolor=C['Grid'],
                        selectbackground=C['Light'], selectforeground=C['Black'], padding=4)
        style.map('Profile.TCombobox', fieldbackground=[('readonly', C['Light'])],
                  foreground=[('readonly', C['Black'])], selectbackground=[('readonly', C['Light'])],
                  selectforeground=[('readonly', C['Black'])])
        style.configure('Vertical.TScrollbar', background=C['Head'], troughcolor=C['Field'],
                        bordercolor=C['Field'], lightcolor=C['Head'], darkcolor=C['Head'],
                        arrowcolor=C['Text'], gripcount=0)
        style.map('Vertical.TScrollbar', background=[('active', shade(C['Head'], 0.2))])
        root.option_add('*TCombobox*Listbox.font', F.profile)
        root.option_add('*TCombobox*Listbox.background', C['Light'])
        root.option_add('*TCombobox*Listbox.foreground', C['Black'])
        root.option_add('*TCombobox*Listbox.selectBackground', C['Yellow'])
        root.option_add('*TCombobox*Listbox.selectForeground', C['Black'])

        self.build_header()
        self.build_toolbar()
        self.build_list()
        self.build_bottom()

        self.combo_names = []
        self.fill_combo()
        self.show_profile(store.default)
        root.protocol('WM_DELETE_WINDOW', self.on_close)
        root.bind_all('<Delete>', self.on_delete_key)
        self.tick_clock()
        w, h = 1100, 700
        root.geometry('%dx%d+%d+%d' % (w, h, max(0, (root.winfo_screenwidth() - w) // 2),
                                       max(0, (root.winfo_screenheight() - h) // 3)))
        root.after(50, lambda: plat.style_window(root, launch_cmd() + ['--run'], res_path(ICON_ICO),
                                                  dark=self.store.theme == 'Dark'))
        root.after(300, self.on_shown)

    # ------------------------------------------------------------ layout
    def build_header(self):
        F = self.F
        h = tk.Frame(self.root, bg=C['Header'])
        h.pack(fill='x')
        tk.Label(h, text=APP_TITLE, font=F.title, fg=C['Text'], bg=C['Header']).pack(side='left', padx=(16, 10), pady=12)
        tk.Label(h, text='V' + VERSION, font=F.mono, fg=C['Text'], bg=C['Header']).pack(side='left', padx=(0, 34))
        tk.Label(h, text='Default:', font=F.mono, fg=C['Text'], bg=C['Header']).pack(side='left')
        self.lbl_default = tk.Label(h, text='', font=F.mono, fg=C['GreenText'], bg=C['Header'])
        self.lbl_default.pack(side='left', padx=(6, 0))
        self.lbl_utc = tk.Label(h, text='', font=F.mono, fg=C['GreenText'], bg=C['Header'])
        self.lbl_utc.pack(side='right', padx=16)

    def switch_theme(self):
        """Dark <-> Light: save, then reopen the editor in the other look (about a second)."""
        if self.busy():
            return
        if self.save_job:
            self.root.after_cancel(self.save_job)
        self.save()
        self.store.theme = 'Light' if self.store.theme == 'Dark' else 'Dark'
        self.store.save()
        plat.run_detached(launch_cmd())
        self.root.destroy()

    def build_toolbar(self):
        F = self.F
        t = tk.Frame(self.root, bg=C['Bg'])
        t.pack(fill='x', padx=14, pady=(12, 10))
        tk.Label(t, text='Profile:', font=F.bold, fg=C['Text'], bg=C['Bg']).pack(side='left', padx=(0, 8))
        self.combo = ttk.Combobox(t, state='readonly', style='Profile.TCombobox', font=F.profile, width=22)
        self.combo.pack(side='left', ipady=2)
        self.combo.bind('<<ComboboxSelected>>', self.on_combo)
        self.b_new = make_button(t, 'New Profile', self.new_profile, font=F.bold)
        self.b_clone = make_button(t, 'Clone', self.clone_profile, font=F.bold)
        self.b_rename = make_button(t, 'Rename', self.rename_profile, font=F.bold)
        self.b_delete = make_button(t, 'Delete Profile', self.delete_profile, fg=C['MissText'], font=F.bold)
        self.b_default = make_button(t, STAR + ' Set as Default', self.set_default, C['Green'], C['Black'], F.bold)
        for b in (self.b_new, self.b_clone, self.b_rename, self.b_delete, self.b_default):
            b.configure(padx=9)
            b.pack(side='left', padx=(6, 0))
        self.b_icon = make_button(t, 'Desktop Icon', self.make_icon, C['Yellow'], C['Black'], F.bold, padx=9)
        self.b_icon.pack(side='left', padx=(16, 0))

    def build_list(self):
        F = self.F
        outer = tk.Frame(self.root, bg=C['Grid'], bd=0)
        outer.pack(fill='both', expand=True, padx=14)
        self.canvas = tk.Canvas(outer, bg=C['Field'], highlightthickness=0, bd=0)
        sb = ttk.Scrollbar(outer, orient='vertical', command=self.canvas.yview, style='Vertical.TScrollbar')
        self.canvas.configure(yscrollcommand=sb.set)
        sb.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True, padx=(1, 0), pady=1)
        self.inner = tk.Frame(self.canvas, bg=C['Grid'])
        self.win_id = self.canvas.create_window(0, 0, window=self.inner, anchor='nw')
        self.inner.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfigure(self.win_id, width=e.width))
        for c, (title, minsize, weight) in enumerate([('Open', 64, 0), ('App', 190, 0),
                                                       ('Program location  (double-click to browse)', 300, 1),
                                                       ('Options', 120, 0), ('Wait (sec)', 96, 0),
                                                       ('Minimize', 96, 0)]):
            self.inner.columnconfigure(c, minsize=minsize, weight=weight)
            tk.Label(self.inner, text=title, font=F.bold, fg=C['Text'], bg=C['Head'], pady=8).grid(
                row=0, column=c, sticky='nsew', padx=(0 if c == 0 else 1, 0))
        self.empty_note = tk.Label(self.canvas, text='No apps yet.  Click  + Add App  below to add your first program.',
                                   font=F.tip, fg=C['Dim'], bg=C['Field'])

        def wheel(e):
            if e.num == 4 or getattr(e, 'delta', 0) > 0:
                self.canvas.yview_scroll(-2, 'units')
            else:
                self.canvas.yview_scroll(2, 'units')
        self.canvas.bind('<Enter>', lambda e: (self.canvas.bind_all('<MouseWheel>', wheel),
                                               self.canvas.bind_all('<Button-4>', wheel),
                                               self.canvas.bind_all('<Button-5>', wheel)))
        self.canvas.bind('<Leave>', lambda e: (self.canvas.unbind_all('<MouseWheel>'),
                                               self.canvas.unbind_all('<Button-4>'),
                                               self.canvas.unbind_all('<Button-5>')))
        if getattr(self.root, 'dnd_ok', False):
            for w in (self.canvas, self.inner):
                try:
                    w.drop_target_register(DND_FILES)
                    w.dnd_bind('<<Drop>>', self.on_drop)
                except Exception:
                    pass

    def build_bottom(self):
        F = self.F
        bar = tk.Frame(self.root, bg=C['Bg'])
        bar.pack(fill='x', padx=14, pady=(12, 0))
        self.b_add = make_button(bar, '+ Add App', self.add_menu, C['Head'], C['GreenText'], F.bold)
        self.b_remove = make_button(bar, 'Remove App', self.remove_app, font=F.bold)
        self.b_up = make_button(bar, 'Move Up', lambda: self.move(-1), font=F.bold)
        self.b_down = make_button(bar, 'Move Down', lambda: self.move(1), font=F.bold)
        self.b_all = make_button(bar, 'Check All', lambda: self.check_all(True), font=F.bold)
        self.b_none = make_button(bar, 'Uncheck All', lambda: self.check_all(False), font=F.bold)
        self.b_find = make_button(bar, 'Find Missing Apps', self.find_missing, font=F.bold)
        for i, b in enumerate((self.b_add, self.b_remove, self.b_up, self.b_down, self.b_all, self.b_none, self.b_find)):
            b.pack(side='left', padx=(0 if i == 0 else 6, 0))
        other = 'Light' if self.store.theme == 'Dark' else 'Dark'
        self.b_theme = make_button(bar, (SUN if other == 'Light' else MOON) + ' ' + other + ' Theme',
                                   self.switch_theme, font=F.bold)
        self.b_theme.pack(side='right')

        row2 = tk.Frame(self.root, bg=C['Bg'])
        row2.pack(fill='x', padx=14, pady=(12, 0))
        self.skip_var = tk.BooleanVar(value=self.store.skip_running)
        self.cb_skip = CheckBox(row2, self.skip_var, C['Green'], C['Bg'], self.on_skip, size=16)
        self.cb_skip.pack(side='left')
        lbl = tk.Label(row2, text='Skip apps that are already open', font=F.bold, fg=C['Text'], bg=C['Bg'], cursor='hand2')
        lbl.pack(side='left', padx=(6, 40))
        lbl.bind('<Button-1>', self.cb_skip._toggle)
        tip = ('Tip: drag program icons onto the list to add apps.' if getattr(self.root, 'dnd_ok', False)
               else 'Tip: + Add App > "Pick from installed apps" lists your menu programs.')
        tk.Label(row2, text=tip, font=F.tip, fg=C['YellowText'], bg=C['Bg']).pack(side='left')

        act = tk.Frame(self.root, bg=C['Bg'])
        act.pack(fill='x', padx=14, pady=(12, 14))
        big = (F.big[0], 13, 'bold')
        self.b_launch = make_button(act, 'LAUNCH', self.launch, C['Green'], C['Black'], big, padx=34, pady=12)
        self.b_stop = make_button(act, 'STOP', self.stop, C['Halt'], C['White'], big, padx=24, pady=12)
        self.b_close = make_button(act, 'CLOSE APPS', self.close_apps, C['Orange'], C['Black'], big, padx=22, pady=12)
        self.b_launch.pack(side='left')
        self.b_stop.pack(side='left', padx=(8, 0))
        self.b_close.pack(side='left', padx=(8, 0))
        self.lbl_status = tk.Label(act, text='', font=F.status, fg=C['GreenText'], bg=C['Bg'], anchor='w',
                                   justify='left', wraplength=440)
        self.lbl_status.pack(side='left', fill='x', expand=True, padx=(16, 0))

    # ------------------------------------------------------------ helpers
    def set_status(self, text):
        self.lbl_status.configure(text=text)
        self.root.update_idletasks()

    def tick_clock(self):
        self.lbl_utc.configure(text='UTC: ' + time.strftime('%H:%M:%S', time.gmtime()))
        self.root.after(1000, self.tick_clock)

    def busy(self):
        return bool(self.job and self.job.running)

    def display_name(self, name):
        return (STAR + ' ' + name + '  (default)') if name == self.store.default else name

    def fill_combo(self):
        self.combo_names = [p['Name'] for p in self.store.profiles]
        self.combo['values'] = [self.display_name(n) for n in self.combo_names]
        if self.current in self.combo_names:
            self.combo.current(self.combo_names.index(self.current))

    def update_default_display(self):
        self.lbl_default.configure(text=self.store.default)
        if self.current == self.store.default:
            self.b_default.configure(text=STAR + ' Default')
            restyle_button(self.b_default, C['Head'], C['GreenText'])
        else:
            self.b_default.configure(text=STAR + ' Set as Default')
            restyle_button(self.b_default, C['Green'], C['Black'])
        self.fill_combo()

    def update_icon_button(self):
        if plat.icon_installed():
            self.b_icon.configure(text=CHECK + ' Icon Up to Date')
            restyle_button(self.b_icon, C['Head'], C['YellowText'])
        else:
            self.b_icon.configure(text='Desktop Icon')
            restyle_button(self.b_icon, C['Yellow'], C['Black'])

    # ------------------------------------------------------------ rows
    def show_profile(self, name):
        self.loading = True
        for r in self.rows:
            r.destroy()
        self.rows = []
        self.selected = None
        prof = self.store.get(name)
        for a in (prof['Apps'] if prof else []):
            self.rows.append(AppRow(self, a))
        self.current = name
        self.regrid()
        self.loading = False
        self.update_default_display()
        self.canvas.yview_moveto(0)

    def regrid(self):
        for i, r in enumerate(self.rows):
            r.grid(i + 1)
        self.color_rows()
        if self.rows:
            self.empty_note.place_forget()
        else:
            self.empty_note.place(relx=0.5, rely=0.45, anchor='center')

    def color_rows(self):
        for i, r in enumerate(self.rows):
            missing = not plat.path_exists(r.path.get())
            if r is self.selected:
                r.paint(C['Select'], C['White'], C['White'])
            elif missing:
                r.paint(C['Missing'], C['MissText'], C['MissText'])
            else:
                bg = C['RowAlt'] if i % 2 else C['Field']
                r.paint(bg, C['Text'], C['PathText'])

    def select_row(self, row):
        self.selected = row
        self.color_rows()

    def changed(self):
        if self.loading:
            return
        if self.save_job:
            self.root.after_cancel(self.save_job)
        self.save_job = self.root.after(500, self.save)

    def collect(self):
        prof = self.store.get(self.current)
        if prof is not None:
            prof['Apps'] = [r.data() for r in self.rows]

    def save(self):
        self.save_job = None
        self.collect()
        self.store.skip_running = bool(self.skip_var.get())
        if not self.store.save():
            self.set_status("Couldn't save settings to " + self.store.path)
        self.store.refresh_menu()
        self.update_icon_button()

    def add_row(self, name, path, args=''):
        row = AppRow(self, {'Enabled': True, 'Name': name, 'Path': path, 'Args': args,
                            'Delay': DEFAULT_WAIT, 'Minimize': False})
        self.rows.append(row)
        self.selected = row
        self.regrid()
        self.save()
        self.root.after(50, lambda: self.canvas.yview_moveto(1.0))
        self.set_status('Added %s. Use Move Up/Down to set the order.' % name)

    # ------------------------------------------------------------ list actions
    def add_menu(self):
        if self.busy():
            return
        m = tk.Menu(self.root, tearoff=0, bg=C['Head'], fg=C['Text'], activebackground=C['Select'],
                    activeforeground=C['White'], font=self.F.bold, bd=0)
        m.add_command(label='Browse for a program...', command=self.add_browse)
        m.add_command(label='Pick from installed apps...', command=self.add_installed)
        x = self.b_add.winfo_rootx()
        y = self.b_add.winfo_rooty() + self.b_add.winfo_height()
        try:
            m.tk_popup(x, y)
        finally:
            m.grab_release()

    def add_browse(self):
        f = plat.pick_file(self.root, None)
        if f:
            name, prog, args = plat.read_dropped(f)
            self.add_row(name, prog, args)

    def add_installed(self):
        self.set_status('Reading installed apps...')
        apps = plat.installed_apps()
        self.set_status('')
        dlg = tk.Toplevel(self.root)
        dlg.title('Pick from installed apps')
        dlg.configure(bg=C['Bg'])
        dlg.transient(self.root)
        dlg.geometry('460x520+%d+%d' % (self.root.winfo_rootx() + 120, self.root.winfo_rooty() + 80))
        F = self.F
        tk.Label(dlg, text='Type to search:', font=F.bold, fg=C['Text'], bg=C['Bg']).pack(anchor='w', padx=14, pady=(14, 4))
        q = tk.StringVar()
        e = tk.Entry(dlg, textvariable=q, font=F.profile, bg=C['Light'], fg=C['Black'], relief='flat',
                     insertbackground=C['Black'])
        e.pack(fill='x', padx=14, ipady=5)
        lb = tk.Listbox(dlg, font=F.row_bold, bg=C['Field'], fg=C['Text'], selectbackground=C['Select'],
                        selectforeground=C['White'], relief='flat', highlightthickness=1,
                        highlightbackground=C['Grid'], activestyle='none')
        lb.pack(fill='both', expand=True, padx=14, pady=10)
        shown = []

        def refill(*_):
            lb.delete(0, 'end')
            del shown[:]
            needle = q.get().lower().strip()
            for a in apps:
                if needle in a[0].lower() or needle in a[1].lower():
                    shown.append(a)
                    lb.insert('end', '  ' + a[0])
            if shown:
                lb.selection_set(0)
        trace_var(q, refill)
        refill()

        def choose(*_):
            sel = lb.curselection()
            if not sel:
                return
            name, prog, args = shown[sel[0]]
            dlg.destroy()
            self.add_row(name, prog, args)
        lb.bind('<Double-Button-1>', choose)
        e.bind('<Return>', choose)
        btns = tk.Frame(dlg, bg=C['Bg'])
        btns.pack(fill='x', padx=14, pady=(0, 14))
        make_button(btns, 'Cancel', dlg.destroy, font=F.bold).pack(side='right')
        make_button(btns, '+ Add', choose, C['Green'], C['Black'], F.bold).pack(side='right', padx=(0, 8))
        if not apps:
            lb.insert('end', '  (no installed apps found - use Browse instead)')
        e.focus_set()
        dlg.grab_set()

    def on_drop(self, event):
        if self.busy():
            return
        for f in self.root.tk.splitlist(event.data):
            name, prog, args = plat.read_dropped(f)
            self.add_row(name, prog, args)

    def on_delete_key(self, event):
        if isinstance(event.widget, (tk.Entry, ttk.Entry)) or isinstance(event.widget, tk.Listbox):
            return
        self.remove_app()

    def remove_app(self):
        if self.busy() or not self.selected:
            if not self.selected:
                self.set_status('Click an app in the list first, then Remove App.')
            return
        n = self.selected.name.get()
        if messagebox.askyesno('Remove App', "Remove %s from the '%s' profile?\n\n(The program itself is not deleted.)"
                               % (n, self.current), parent=self.root):
            self.selected.destroy()
            self.rows.remove(self.selected)
            self.selected = None
            self.regrid()
            self.save()
            self.set_status('Removed %s.' % n)

    def move(self, d):
        if self.busy() or not self.selected:
            return
        i = self.rows.index(self.selected)
        j = i + d
        if 0 <= j < len(self.rows):
            self.rows[i], self.rows[j] = self.rows[j], self.rows[i]
            self.regrid()
            self.save()

    def check_all(self, on):
        if self.busy():
            return
        for r in self.rows:
            r.enabled.set(on)
            r.cb_open.draw()
        self.save()

    def find_missing(self):
        if self.busy():
            return
        self.collect()
        self.root.configure(cursor='watch')
        cache, found, missing = {}, 0, []
        for p in self.store.profiles:
            for a in p['Apps']:
                if plat.path_exists(a['Path']):
                    cache.setdefault(a['Name'], a['Path'])
        for p in self.store.profiles:
            for a in p['Apps']:
                if plat.path_exists(a['Path']):
                    continue
                if a['Name'] not in cache:
                    self.set_status('Looking for %s...' % a['Name'])
                    cache[a['Name']] = plat.find_program(a['Name'])
                if cache[a['Name']]:
                    a['Path'] = cache[a['Name']]
                    found += 1
                elif a['Name'] not in missing:
                    missing.append(a['Name'])
        self.root.configure(cursor='')
        self.show_profile(self.current)
        self.save()
        if missing:
            self.set_status("Couldn't find: %s. Double-click the red rows to pick them." % ', '.join(missing))
        else:
            self.set_status('All apps located. Ready to launch.' if found or self.rows else 'Nothing to look for yet.')

    def on_skip(self):
        self.save()

    # ------------------------------------------------------------ profiles
    def on_combo(self, _e=None):
        i = self.combo.current()
        if i < 0:
            return
        new = self.combo_names[i]
        if new == self.current:
            return
        self.collect()
        self.store.save()
        self.show_profile(new)
        if new == self.store.default:
            self.set_status('Showing %s (the default).' % new)
        else:
            self.set_status('Showing %s. Click Set as Default to make the icon launch it.' % new)

    def ask_name(self, title, prompt, initial=''):
        name = simpledialog.askstring(title, prompt, initialvalue=initial, parent=self.root)
        name = (name or '').strip()
        if not name:
            return None
        if '"' in name:
            messagebox.showinfo(title, 'Profile names cannot contain quote marks.', parent=self.root)
            return None
        if self.store.get(name):
            messagebox.showinfo(title, "There's already a profile called %s." % name, parent=self.root)
            return None
        return name

    def add_profile(self, name, apps):
        self.collect()
        self.store.profiles.append({'Name': name, 'Apps': apps})
        self.show_profile(name)
        self.save()

    def new_profile(self):
        if self.busy():
            return
        name = self.ask_name('New Profile', 'Name for the new, empty profile.\n\n'
                                            '(To start from an existing profile instead, use Clone.)')
        if name:
            self.add_profile(name, [])
            self.set_status('Created %s. Click + Add App to add programs.' % name)

    def clone_profile(self):
        if self.busy():
            return
        src = self.current
        suggest, n = src + ' copy', 2
        while self.store.get(suggest):
            suggest = '%s copy %d' % (src, n)
            n += 1
        name = self.ask_name('Clone Profile', "Name for the copy of '%s'.\n\nIt gets the same apps, order and "
                                              "wait times; then change whatever you like." % src, suggest)
        if name:
            self.collect()
            self.add_profile(name, [dict(a) for a in self.store.get(src)['Apps']])
            self.set_status('Cloned %s as %s. Make your changes; they save automatically.' % (src, name))

    def rename_profile(self):
        if self.busy():
            return
        old = self.current
        name = self.ask_name('Rename Profile', 'New name for this profile:', old)
        if not name or name == old:
            return
        self.store.get(old)['Name'] = name
        if self.store.default == old:
            self.store.default = name
        if self.store.last_launched == old:
            self.store.last_launched = name
        self.current = name
        self.update_default_display()
        self.save()

    def delete_profile(self):
        if self.busy():
            return
        if len(self.store.profiles) <= 1:
            messagebox.showinfo('Delete Profile', 'You need at least one profile.', parent=self.root)
            return
        name = self.current
        if not messagebox.askyesno('Delete Profile',
                                   "Delete the WHOLE profile '%s' and its app list?\n\n(To take just one app out "
                                   "of this profile, click No, then use Remove App.)" % name,
                                   icon='warning', default='no', parent=self.root):
            return
        self.store.profiles.remove(self.store.get(name))
        if self.store.default == name:
            self.store.default = self.store.profiles[0]['Name']
        if self.store.last_launched == name:
            self.store.last_launched = self.store.default
        self.current = None
        self.show_profile(self.store.profiles[0]['Name'])
        self.save()
        self.set_status('Deleted %s. The default is %s.' % (name, self.store.default))

    def set_default(self):
        if self.busy() or self.current == self.store.default:
            return
        self.store.default = self.current
        self.save()
        self.update_default_display()
        self.set_status('%s is now the default. Clicking the icon launches it.' % self.store.default)

    def make_icon(self):
        first = not plat.icon_installed()
        self.collect()
        self.store.save()
        if not self.store.refresh_menu(write_icons=True):
            messagebox.showwarning('Problem', "Couldn't create the icon.", parent=self.root)
            return
        self.update_icon_button()
        if first:
            try:
                plat.pin_to_panel(True)
            except Exception:
                pass
            messagebox.showinfo('Desktop icon created', plat.FIRST_ICON_HELP, parent=self.root)
        else:
            self.set_status('Desktop icon and right-click menu refreshed.')

    # ------------------------------------------------------------ launch / stop / close
    def set_editing(self, on):
        st = 'normal' if on else 'disabled'
        for b in (self.b_new, self.b_clone, self.b_rename, self.b_delete, self.b_default, self.b_icon,
                  self.b_add, self.b_remove, self.b_up, self.b_down, self.b_all, self.b_none, self.b_find,
                  self.b_launch, self.b_close):
            b.configure(state=st)
        self.combo.configure(state='readonly' if on else 'disabled')
        for r in self.rows:
            for e in (r.e_name, r.e_path, r.e_args, r.e_delay):
                e.configure(state='normal' if on else 'readonly')
            r.cb_open.configure(state=st)
            r.cb_min.configure(state=st)

    def launch(self):
        if self.busy():
            return
        self.collect()
        apps = [a for a in self.store.get(self.current)['Apps'] if a['Enabled']]
        if not apps:
            messagebox.showinfo('Nothing to launch', 'Check at least one app to open.', parent=self.root)
            return
        self.store.last_launched = self.current
        self.save()
        self.set_editing(False)

        def done(job):
            self.set_editing(True)
            show_errors(self.root, job.errors)
        self.job = LaunchJob(self.root, apps, self.store.skip_running, self.watcher, self.set_status,
                             lambda v, m: None, done)
        self.job.start()

    def stop(self):
        if self.busy():
            self.job.stop()
            self.set_editing(True)
            self.set_status('Stopped. Opened %d app(s) before stopping.' % len(self.job.launched))

    def close_apps(self):
        if self.busy():
            return
        self.collect()
        self.store.save()
        plat.run_detached(launch_cmd() + ['--close', '--profile', self.current])
        self.set_status('Closing the %s apps, last one first...' % self.current)

    # ------------------------------------------------------------ window
    def on_shown(self):
        if plat.icon_installed():
            self.store.refresh_menu(write_icons=True)     # keeps the taskbar/dock icon working after updates
        self.update_icon_button()
        note = plat.window_tool_note()
        if self.store.bad_copy:
            messagebox.showwarning('Settings could not be read',
                                   'Your settings file could not be read, so a new one was started.\n\n'
                                   'The old file was kept as:\n%s\n\nIt may be fixable by hand '
                                   '(it is a plain JSON text file).' % self.store.bad_copy, parent=self.root)
            self.store.bad_copy = ''
            self.store.welcomed = True
            self.store.save()
        if not self.store.welcomed:
            self.set_status('Welcome! Click + Add App to add your first program.')
            messagebox.showinfo('Getting started',
                                'Welcome to %s!\n\n'
                                '1. Add your programs: click "+ Add App".\n'
                                '2. Put them in order with Move Up / Move Down, and set each app\'s wait time.\n'
                                '3. Click "Desktop Icon", then add that icon to your %s.\n\n'
                                'Click the icon to launch your default profile; right-click it for other '
                                'profiles and Close apps.' % (APP_TITLE, 'taskbar' if IS_WINDOWS else 'dock'),
                                parent=self.root)
            self.store.welcomed = True
            self.store.save()
        elif note:
            self.set_status(note)
        else:
            self.set_status('Ready. Pick a profile and press Launch.')

    def on_close(self):
        if self.save_job:
            self.root.after_cancel(self.save_job)
        self.save()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ======================================================================== main
def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    mode, profile = 'edit', None
    if '--run' in argv:
        mode = 'run'
    if '--close' in argv:
        mode = 'close'
    if '--profile' in argv:
        i = argv.index('--profile')
        if i + 1 < len(argv):
            profile = argv[i + 1]
    store = Store()
    set_theme(store.theme)
    if '--install-icon' in argv:
        plat.prepare_process()
        ok = store.refresh_menu(write_icons=True)
        if sys.stdout:                      # the Windows .exe has no console
            print('Icon created.' if ok else 'Could not create the icon.')
        return 0 if ok else 1
    if '--pin' in argv or '--unpin' in argv:
        msg = plat.pin_to_panel('--pin' in argv)
        if msg and sys.stdout:
            print(msg)
        return 0
    if mode in ('run', 'close'):
        quick_window(store, mode, profile)
    else:
        Editor(store).run()
    return 0


if __name__ == '__main__':      # normally started through run_digiapp.py
    sys.exit(main())
