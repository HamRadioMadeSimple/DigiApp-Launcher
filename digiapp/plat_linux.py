# DigiApp Launcher - Linux (Ubuntu 16.04 and newer) system layer.
# Uses only the Python standard library plus the optional "wmctrl" and "xdotool" tools.
# Written for Python 3.5+ (no f-strings) so it runs on older Ubuntu releases.

import os
import re
import shlex
import shutil
import signal
import subprocess

NAME = 'linux'
APP_FILE_ID = 'digiapp-launcher'
EDIT_FILE_ID = APP_FILE_ID + '-edit'        # second icon that opens only the editor

INTERPRETERS = ('python', 'python2', 'python3', 'bash', 'sh', 'dash', 'env', 'java', 'mono',
                'wine', 'wine64', 'perl', 'ruby', 'node', 'nohup')


def _which(cmd):
    try:
        return shutil.which(cmd)
    except Exception:
        return None


def _run(argv, timeout=5):
    try:
        p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             universal_newlines=True)
        out, _ = p.communicate(timeout=timeout)
        return p.returncode, out
    except Exception:
        return 1, ''


# ---------------------------------------------------------------- folders
def config_dir():
    base = os.environ.get('XDG_CONFIG_HOME') or os.path.join(os.path.expanduser('~'), '.config')
    return os.path.join(base, 'digiapp-launcher')


def _apps_dir():
    base = os.environ.get('XDG_DATA_HOME') or os.path.join(os.path.expanduser('~'), '.local', 'share')
    return os.path.join(base, 'applications')


def _desktop_dir():
    code, out = _run(['xdg-user-dir', 'DESKTOP'])
    d = out.strip() if code == 0 else ''
    if not d or not os.path.isdir(d):
        d = os.path.join(os.path.expanduser('~'), 'Desktop')
    return d if os.path.isdir(d) else None


def prepare_process():
    pass


def clean_child_env():
    pass


def style_window(root, relaunch=None, icon=None, dark=True):
    pass


# ---------------------------------------------------------------- processes
class Proc(object):
    __slots__ = ('pid', 'ppid', 'exe', 'cmdline', 'state')

    def __init__(self, pid, ppid, exe, cmdline, state):
        self.pid, self.ppid, self.exe, self.cmdline, self.state = pid, ppid, exe, cmdline, state


def list_processes():
    procs = []
    me = os.getpid()
    for entry in os.listdir('/proc'):
        if not entry.isdigit():
            continue
        pid = int(entry)
        if pid == me:
            continue
        try:
            with open('/proc/%d/stat' % pid, 'r') as f:
                stat = f.read()
            rest = stat[stat.rfind(')') + 2:].split()
            state, ppid = rest[0], int(rest[1])
            with open('/proc/%d/cmdline' % pid, 'rb') as f:
                raw = f.read()
            cmd = [a.decode('utf-8', 'replace') for a in raw.split(b'\0') if a]
        except Exception:
            continue
        try:
            exe = os.readlink('/proc/%d/exe' % pid)
            if exe.endswith(' (deleted)'):
                exe = exe[:-10]
        except Exception:
            exe = None
        procs.append(Proc(pid, ppid, exe, cmd, state))
    return procs


def is_alive(pid):
    try:
        with open('/proc/%d/stat' % pid, 'r') as f:
            stat = f.read()
        return stat[stat.rfind(')') + 2:].split()[0] not in ('Z', 'X')
    except Exception:
        return False


def start_time(pid):
    """When the process started (clock ticks since boot), so a remembered process id can't be
    mistaken for a different program that got the same id later. None if it isn't running."""
    try:
        with open('/proc/%d/stat' % pid, 'r') as f:
            stat = f.read()
        return int(stat[stat.rfind(')') + 2:].split()[19])
    except Exception:
        return None


def flatpak_pids(app_id, proc_root='/proc'):
    """Processes of a running Flatpak app. Flatpak puts each app in its own group named
    app-flatpak-<app id>-<number>.scope; the program itself shows up only as "bwrap ...".
    (Shared helper processes of the Flatpak system have no app group, so they are never included.)"""
    if not app_id:
        return []
    mark = 'app-flatpak-' + app_id + '-'
    pids = []
    try:
        entries = os.listdir(proc_root)
    except Exception:
        return pids
    for entry in entries:
        if not entry.isdigit():
            continue
        try:
            with open(os.path.join(proc_root, entry, 'cgroup'), 'r') as f:
                if mark in f.read():
                    pids.append(int(entry))
        except Exception:
            continue
    return sorted(pids)


def terminate(pids):
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass


def force_kill(pids):
    for pid in pids:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass


def norm(path):
    try:
        return os.path.realpath(path)
    except Exception:
        return path


def base(path):
    return os.path.basename((path or '').replace('\\', '/')).lower()


# ---------------------------------------------------------------- launching
def resolve(path):
    """Full path for a program location or a bare command name (e.g. 'fldigi')."""
    path = (path or '').strip().strip('"')
    if not path:
        return ''
    path = os.path.expanduser(path)
    if '/' in path:
        return path
    return _which(path) or ''


def path_exists(path):
    p = resolve(path)
    return bool(p) and os.path.exists(p)


def parse_desktop_file(path):
    """Returns (name, command, options) from a .desktop menu entry, or None."""
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
    except Exception:
        return None
    info = {}
    section = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('['):
            section = line
            continue
        if section != '[Desktop Entry]' or '=' not in line:
            continue
        k, v = line.split('=', 1)
        info.setdefault(k.strip(), v.strip())
    if info.get('Type', 'Application') != 'Application' or not info.get('Exec'):
        return None
    if info.get('NoDisplay', '').lower() == 'true' or info.get('Hidden', '').lower() == 'true':
        return None
    try:
        parts = shlex.split(info['Exec'])
    except Exception:
        parts = info['Exec'].split()
    parts = [p for p in parts if not re.match(r'^%[a-zA-Z]$', p)]
    parts = [p for p in parts if p not in ('@@', '@@u')]       # Flatpak's file-forwarding markers
    parts = [p.replace('%%', '%') for p in parts]
    if not parts:
        return None
    cmd = parts[0]
    full = _which(cmd) if '/' not in cmd else cmd
    return info.get('Name', os.path.basename(path)), (full or cmd), ' '.join(shlex.quote(p) for p in parts[1:])


def build_argv(path, args):
    full = resolve(path)
    try:
        extra = shlex.split(args or '')
    except Exception:
        extra = (args or '').split()
    low = full.lower()
    if low.endswith('.desktop'):
        d = parse_desktop_file(full)
        if not d:
            raise RuntimeError('cannot read menu entry')
        full = resolve(d[1])
        extra = shlex.split(d[2]) + extra
        low = full.lower()
    if low.endswith('.py') or low.endswith('.pyw'):
        return ['python3', full] + extra, os.path.dirname(full)
    if low.endswith('.sh'):
        return ['bash', full] + extra, os.path.dirname(full)
    if low.endswith('.jar'):
        return ['java', '-jar', full] + extra, os.path.dirname(full)
    if low.endswith('.exe') or low.endswith('.bat'):
        return ['wine', full] + extra, os.path.dirname(full)
    if os.path.isfile(full) and not os.access(full, os.X_OK):
        raise RuntimeError('the file is not marked as a program (chmod +x "%s")' % full)
    cwd = os.path.dirname(full) if full.startswith(os.path.expanduser('~')) or '/opt/' in full else os.path.expanduser('~')
    return [full] + extra, cwd


def launch(path, args, minimize):
    argv, cwd = build_argv(path, args)
    if not cwd or not os.path.isdir(cwd):
        cwd = os.path.expanduser('~')
    p = subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    return p.pid


def run_detached(argv):
    subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


# ---------------------------------------------------------------- windows (X11 via wmctrl/xdotool)
def windows_supported():
    return bool(_which('wmctrl'))


def window_tool_note():
    if not _which('wmctrl'):
        return 'Minimize and window-close need the "wmctrl" tool: sudo apt install wmctrl xdotool'
    if os.environ.get('XDG_SESSION_TYPE', '').lower() == 'wayland':
        return 'Wayland session: minimize may not work for every app. Choose "Ubuntu on Xorg" at login for full support.'
    return ''


def list_windows():
    """[(window_id, pid, window_class)] for normal top-level windows.
    pid is 0 when the app doesn't publish it (Tk and some FLTK apps); the class is then used instead."""
    code, out = _run(['wmctrl', '-lpx'])
    wins = []
    if code != 0:
        return wins
    for line in out.splitlines():
        parts = line.split(None, 5)
        if len(parts) < 4:
            continue
        try:
            wid, desk, pid = parts[0], int(parts[1]), int(parts[2])
            cls = (parts[3] + ' ' + (parts[5] if len(parts) > 5 else '')).lower()   # class + title
        except ValueError:
            continue
        if desk < 0:            # sticky panels, docks, desktop
            continue
        wins.append((wid, pid, cls))
    return wins


def minimize_window(wid):
    if _which('xdotool'):
        _run(['xdotool', 'windowminimize', str(int(wid, 16))])
    else:
        _run(['wmctrl', '-ir', wid, '-b', 'add,hidden'])


def close_window(wid, method='close'):
    code, _ = _run(['wmctrl', '-ic', wid])
    return 'ok' if code == 0 else 'failed'


def window_busy(wid):
    return False


def window_info(wid):
    return wid


def reveal_windows(wids):
    for wid in wids:
        _run(['wmctrl', '-ia', wid])


# ---------------------------------------------------------------- choosing programs
def pick_file(parent, initialdir):
    if _which('zenity'):
        argv = ['zenity', '--file-selection', '--title=Choose the program to open']
        if initialdir and os.path.isdir(initialdir):
            argv.append('--filename=' + initialdir.rstrip('/') + '/')
        code, out = _run(argv, timeout=3600)
        return out.strip() if code == 0 and out.strip() else None
    from tkinter import filedialog
    p = filedialog.askopenfilename(parent=parent, title='Choose the program to open',
                                   initialdir=initialdir or os.path.expanduser('~'))
    return p or None


def read_dropped(path):
    """(name, program, options) for a dropped or picked file."""
    if path.lower().endswith('.desktop'):
        d = parse_desktop_file(path)
        if d:
            return d
    name = os.path.splitext(os.path.basename(path))[0]
    return name, path, ''


def installed_apps():
    dirs = [_apps_dir(), '/usr/share/applications', '/usr/local/share/applications',
            '/var/lib/snapd/desktop/applications', '/var/lib/flatpak/exports/share/applications',
            os.path.join(os.path.expanduser('~'), '.local/share/flatpak/exports/share/applications')]
    seen, apps = set(), []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.endswith('.desktop') or fn in seen or fn.startswith(APP_FILE_ID):
                continue
            seen.add(fn)
            info = parse_desktop_file(os.path.join(d, fn))
            if info:
                apps.append(info)
    apps.sort(key=lambda a: a[0].lower())
    return apps


def find_program(name):
    """Best guess at a program's location from its name (used by Find Missing Apps)."""
    key = re.sub(r'[^a-z0-9]', '', name.lower())
    for cand in (name.lower(), key, name.lower().replace(' ', '-'), name.lower().split(' ')[0]):
        hit = _which(cand)
        if hit:
            return hit
    home = os.path.expanduser('~')
    roots = [os.path.join(home, 'Applications'), os.path.join(home, 'Downloads'),
             os.path.join(home, 'bin'), os.path.join(home, '.local', 'bin'), '/opt', home]
    for r in roots:
        if not os.path.isdir(r):
            continue
        base_depth = r.rstrip('/').count('/')
        for dirpath, dirnames, filenames in os.walk(r):
            if dirpath.count('/') - base_depth >= 3:
                dirnames[:] = []
            dirnames[:] = [d for d in dirnames if not d.startswith('.')]
            for fn in filenames:
                flat = re.sub(r'[^a-z0-9]', '', fn.lower())
                if flat.startswith(key) and (fn.lower().endswith('.appimage') or
                                             os.access(os.path.join(dirpath, fn), os.X_OK)):
                    if fn.lower().endswith(('.so', '.txt', '.desktop', '.png')):
                        continue
                    return os.path.join(dirpath, fn)
    return None


# ---------------------------------------------------------------- menu / dock icon
def _desktop_quote(arg):
    if re.search(r'[\s"\'\\><~|&;$*?#()`]', arg):
        arg = '"' + arg.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$') + '"'
    return arg


def _exec_line(argv):
    line = ' '.join(_desktop_quote(a) for a in argv)
    return line.replace('\\', '\\\\').replace('%', '%%')


def _desktop_text(launch_cmd, icon, entries):
    lines = ['[Desktop Entry]', 'Version=1.0', 'Type=Application',
             'Name=DigiApp Launcher',
             'Comment=Open your radio apps in order (right-click for profiles)',
             'Exec=' + _exec_line(launch_cmd + ['--run']),
             'Icon=' + icon, 'Terminal=false', 'Categories=Utility;HamRadio;',
             'StartupWMClass=Digiapplauncher', 'StartupNotify=false']
    actions = []
    body = []
    n = 0
    for title, extra in entries:
        if title == '-':
            continue
        aid = 'item%d' % n
        n += 1
        actions.append(aid)
        body += ['', '[Desktop Action %s]' % aid, 'Name=' + title,
                 'Exec=' + _exec_line(launch_cmd + extra)]
    lines.append('Actions=' + ';'.join(actions) + ';')
    return '\n'.join(lines + body) + '\n'


def _edit_desktop_text(launch_cmd, icon):
    """The 'DigiApp Launcher - Edit' icon: opens the editor only, never launches apps."""
    lines = ['[Desktop Entry]', 'Version=1.0', 'Type=Application',
             'Name=DigiApp Launcher - Edit',
             'Comment=Edit your apps and profiles (does not open any apps)',
             'Exec=' + _exec_line(launch_cmd),
             'Icon=' + icon, 'Terminal=false', 'Categories=Utility;HamRadio;',
             'StartupNotify=false']
    return '\n'.join(lines) + '\n'


def icon_path():
    return os.path.join(_apps_dir(), APP_FILE_ID + '.desktop')


def edit_icon_path():
    return os.path.join(_apps_dir(), EDIT_FILE_ID + '.desktop')


def icon_installed():
    return os.path.exists(icon_path())


def _write_entry(path, text, also_desktop):
    """Writes one menu entry (and its desktop copy, if wanted or already there). Returns True if changed."""
    changed = True
    try:
        with open(path, 'r') as f:
            changed = f.read() != text
    except Exception:
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    targets = [path]
    desk = _desktop_dir()
    name = os.path.basename(path)
    if desk and (also_desktop or os.path.exists(os.path.join(desk, name))):
        targets.append(os.path.join(desk, name))
    for t in targets:
        if t != path or changed:
            with open(t, 'w') as f:
                f.write(text)
            os.chmod(t, 0o755)
        if t != path and _which('gio'):
            _run(['gio', 'set', t, 'metadata::trusted', 'true'])
    return changed


def refresh_menu(launch_cmd, icon, entries, also_desktop=False):
    """Writes/updates the menu entry (its right-click list shows the profiles) and the
    separate Edit icon. Returns True if anything changed."""
    changed = _write_entry(icon_path(), _desktop_text(launch_cmd, icon, entries), also_desktop)
    changed = _write_entry(edit_icon_path(), _edit_desktop_text(launch_cmd, icon), also_desktop) or changed
    if changed and _which('update-desktop-database'):
        _run(['update-desktop-database', _apps_dir()])
    return changed


FIRST_ICON_HELP = ("DigiApp Launcher is now in your Applications menu, on your desktop,\n"
                   "and on your panel or dock (where your desktop allows it).\n\n"
                   "Click the dock icon to launch your default profile.\n"
                   "Right-click it to pick a different profile, Close apps, or edit.\n\n"
                   "To change your apps without launching anything, use the\n"
                   "'DigiApp Launcher - Edit' icon on your desktop or in the menu.\n\n"
                   "If a desktop icon says 'Untrusted', right-click it > Allow Launching.")


# ---------------------------------------------------------------- pin to the panel / dock
def _desktop_name():
    return (os.environ.get('XDG_CURRENT_DESKTOP', '') + ':' + os.environ.get('DESKTOP_SESSION', '')).lower()


def _cinnamon_files():
    import glob
    files = []
    for base in (os.path.join(os.path.expanduser('~'), '.config', 'cinnamon', 'spices'),
                 os.path.join(os.path.expanduser('~'), '.cinnamon', 'configs')):
        files += glob.glob(os.path.join(base, 'grouped-window-list@cinnamon.org', '*.json'))
    return files


def _edit_cinnamon(add):
    import json
    fid = APP_FILE_ID + '.desktop'
    changed = False
    found = False
    for f in _cinnamon_files():
        try:
            with open(f, 'r') as fh:
                data = json.load(fh)
            entry = data.get('pinned-apps')
            if not isinstance(entry, dict):
                continue
            apps = list(entry.get('value', entry.get('default', [])) or [])
            found = True
            if add and fid not in apps:
                apps.append(fid)
            elif not add and fid in apps:
                apps.remove(fid)
            else:
                continue
            entry['value'] = apps
            with open(f, 'w') as fh:
                json.dump(data, fh, indent=4)
            changed = True
        except Exception:
            continue
    if changed and _which('dbus-send'):        # make the panel pick up the change right away
        _run(['dbus-send', '--session', '--dest=org.Cinnamon.LookingGlass', '--type=method_call',
              '/org/Cinnamon/LookingGlass', 'org.Cinnamon.LookingGlass.ReloadExtension',
              'string:grouped-window-list@cinnamon.org', 'string:APPLET'])
    return found        # True when a panel was found (pinned now, or already pinned)


def _edit_gsettings_list(schema, key, item, add):
    import ast
    if not _which('gsettings'):
        return False
    code, out = _run(['gsettings', 'get', schema, key])
    if code != 0:
        return False
    text = out.strip()
    if text.startswith('@as '):
        text = text[4:]
    try:
        items = list(ast.literal_eval(text))
    except Exception:
        return False
    if add and item not in items:
        items.append(item)
    elif not add and item in items:
        items.remove(item)
    else:
        return True
    code, _ = _run(['gsettings', 'set', schema, key, str(items)])
    return code == 0


def pin_to_panel(add=True):
    """Adds (or removes) the launcher on the panel/dock. Returns a short message for the user."""
    fid = APP_FILE_ID + '.desktop'
    d = _desktop_name()
    if 'cinnamon' in d:
        if _edit_cinnamon(add) or not add:
            return 'Added to the bottom panel.' if add else ''
        return 'Right-click DigiApp Launcher in the Menu > "Add to panel".'
    if 'unity' in d:
        if _edit_gsettings_list('com.canonical.Unity.Launcher', 'favorites', 'application://' + fid, add):
            return 'Added to the launcher.' if add else ''
    if 'gnome' in d or 'ubuntu' in d or 'pop' in d or 'zorin' in d:
        if _edit_gsettings_list('org.gnome.shell', 'favorite-apps', fid, add):
            return 'Added to the dock.' if add else ''
    if not add:
        return ''
    if 'kde' in d or 'plasma' in d:
        return 'Open the application menu, right-click DigiApp Launcher > "Pin to Task Manager".'
    if 'xfce' in d:
        return 'Right-click the panel > Panel > Add New Items > Launcher, then add DigiApp Launcher.'
    if 'mate' in d:
        return 'Open the menu, right-click DigiApp Launcher > "Add this launcher to panel".'
    return 'Add DigiApp Launcher to your panel or dock from your applications menu.'
