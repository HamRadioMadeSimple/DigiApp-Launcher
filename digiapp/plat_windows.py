# DigiApp Launcher - Windows system layer.
# Built into DigiAppLauncher.exe by build.bat (needs: psutil, comtypes; tkinterdnd2 optional).

import os
import sys
import re
import ctypes
from ctypes import wintypes, byref, POINTER, Structure, c_ushort, c_ulong, c_uint, c_void_p, c_int

import psutil

NAME = 'windows'
APP_ID = 'DigiApp.Launcher'
APP_TITLE = 'DigiApp Launcher'

INTERPRETERS = ('python.exe', 'pythonw.exe', 'py.exe', 'pyw.exe', 'cmd.exe', 'java.exe', 'javaw.exe',
                'powershell.exe', 'pwsh.exe', 'wscript.exe', 'cscript.exe')

user32 = ctypes.WinDLL('user32', use_last_error=True)
shell32 = ctypes.WinDLL('shell32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)


# ---------------------------------------------------------------- folders
def config_dir():
    base = os.environ.get('APPDATA') or os.path.expanduser('~')
    return os.path.join(base, 'DigiApp Launcher')


def clean_child_env():
    """The one-file DigiAppLauncher.exe unpacks itself to a temporary _MEI folder and points Tcl/Tk (and PATH)
    there. Programs we start would inherit that - a Tk program such as CommStat then uses, and locks, our temporary
    folder, and Windows can't delete it when we exit ("Failed to remove temporary directory"). Called once Tk is
    running, so everything started from now on gets a clean environment."""
    mei = getattr(sys, '_MEIPASS', None)
    if not mei:
        return
    meil = os.path.normcase(os.path.abspath(mei))
    for k in list(os.environ):
        v = os.environ.get(k, '')
        if k in ('_MEIPASS2',) or k.startswith('_PYI_') or \
                (k in ('TCL_LIBRARY', 'TK_LIBRARY', 'TIX_LIBRARY') and os.path.normcase(v).startswith(meil)):
            del os.environ[k]
    parts = [p for p in os.environ.get('PATH', '').split(os.pathsep)
             if p and not os.path.normcase(os.path.abspath(p)).startswith(meil)]
    os.environ['PATH'] = os.pathsep.join(parts)
    os.environ['PYINSTALLER_RESET_ENVIRONMENT'] = '1'     # our own restarts unpack fresh (PyInstaller 6.9+)


def _desktop_dir():
    buf = ctypes.create_unicode_buffer(260)
    if shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf) == 0:      # CSIDL_DESKTOPDIRECTORY
        return buf.value
    return os.path.join(os.path.expanduser('~'), 'Desktop')


def _programs_dir():
    buf = ctypes.create_unicode_buffer(260)
    if shell32.SHGetFolderPathW(None, 0x0002, None, 0, buf) == 0:      # CSIDL_PROGRAMS
        return buf.value
    return None


def prepare_process():
    try:
        shell32.SetCurrentProcessExplicitAppUserModelID(ctypes.c_wchar_p(APP_ID))
    except Exception:
        pass
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


def _hwnd(root):
    root.update_idletasks()
    return user32.GetParent(root.winfo_id()) or root.winfo_id()


def style_window(root, relaunch=None, icon=None, dark=True):
    """Dark (or light) title bar, gold taskbar icon, and grouping with the pinned taskbar icon."""
    try:
        hwnd = _hwnd(root)
        on = c_int(1 if dark else 0)
        dwm = ctypes.windll.dwmapi
        if dwm.DwmSetWindowAttribute(hwnd, 20, byref(on), 4) != 0:
            dwm.DwmSetWindowAttribute(hwnd, 19, byref(on), 4)
    except Exception:
        pass
    if icon:
        _set_window_icons(root, icon)
    if relaunch:
        try:
            _tag_window(root, relaunch, icon)
        except Exception:
            pass


def _set_window_icons(root, ico_file):
    """Give the window real large + small icons, so the taskbar button shows the gold icon."""
    try:
        if not (ico_file and ico_file.lower().endswith('.ico') and os.path.exists(ico_file)):
            return
        hwnd = _hwnd(root)
        user32.LoadImageW.restype = wintypes.HANDLE
        user32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        big = user32.LoadImageW(None, ico_file, 1, user32.GetSystemMetrics(11), user32.GetSystemMetrics(12), 0x10)
        small = user32.LoadImageW(None, ico_file, 1, user32.GetSystemMetrics(49), user32.GetSystemMetrics(50), 0x10)
        if big:
            user32.SendMessageW(hwnd, 0x0080, 1, big)        # WM_SETICON, ICON_BIG
        if small:
            user32.SendMessageW(hwnd, 0x0080, 0, small)      # WM_SETICON, ICON_SMALL
        root._win_icons = (big, small)                       # keep them alive
    except Exception:
        pass


def _tag_window(root, relaunch, icon):
    """Stamp the window with the app's ID, icon and relaunch command (what a pinned button uses)."""
    c = _com()
    hwnd = _hwnd(root)
    store = ctypes.POINTER(c['IPropertyStore'])()
    shell32.SHGetPropertyStoreForWindow(wintypes.HWND(hwnd), byref(c['IPropertyStore']._iid_), byref(store))
    if not store:
        return
    exe = relaunch[0]
    _set_string(c, store, c['FMT_APPMODEL'], 5, APP_ID)                                   # AppUserModel.ID
    _set_string(c, store, c['FMT_APPMODEL'], 2, ' '.join(_quote(a) for a in relaunch))    # RelaunchCommand
    _set_string(c, store, c['FMT_APPMODEL'], 4, APP_TITLE)                                # RelaunchDisplayName
    _set_string(c, store, c['FMT_APPMODEL'], 3, (exe if exe.lower().endswith('.exe') and
                                                 'python' not in os.path.basename(exe).lower()
                                                 else (icon or exe)) + ',0')              # RelaunchIconResource
    store.Commit()


# ---------------------------------------------------------------- processes
class Proc(object):
    __slots__ = ('pid', 'ppid', 'exe', 'cmdline', 'state')

    def __init__(self, pid, ppid, exe, cmdline):
        self.pid, self.ppid, self.exe, self.cmdline, self.state = pid, ppid, exe, cmdline, 'R'


def list_processes():
    me = os.getpid()
    out = []
    for p in psutil.process_iter(['pid', 'ppid', 'exe', 'cmdline']):
        info = p.info
        if info['pid'] == me:
            continue
        out.append(Proc(info['pid'], info.get('ppid') or 0, info.get('exe'), info.get('cmdline') or []))
    return out


def is_alive(pid):
    try:
        return psutil.pid_exists(pid) and psutil.Process(pid).status() != psutil.STATUS_ZOMBIE
    except Exception:
        return False


def start_time(pid):
    """When the process started, so a remembered process id isn't confused with a later program."""
    try:
        return psutil.Process(pid).create_time()
    except Exception:
        return None


def terminate(pids):
    pass        # Windows has no gentle "terminate" for GUI apps; closing is done through their windows


def force_kill(pids):
    for pid in pids:
        try:
            psutil.Process(pid).kill()
        except Exception:
            pass


def norm(path):
    try:
        return os.path.normcase(os.path.realpath(path))
    except Exception:
        return (path or '').lower()


def base(path):
    return os.path.basename((path or '').replace('/', '\\')).lower()


# ---------------------------------------------------------------- launching
def resolve(path):
    path = os.path.expandvars((path or '').strip().strip('"'))
    if not path:
        return ''
    if os.path.dirname(path):
        return path
    import shutil
    return shutil.which(path) or ''


def path_exists(path):
    p = resolve(path)
    return bool(p) and os.path.exists(p)


class SHELLEXECUTEINFO(Structure):
    _fields_ = [('cbSize', wintypes.DWORD), ('fMask', c_ulong), ('hwnd', wintypes.HWND),
                ('lpVerb', wintypes.LPCWSTR), ('lpFile', wintypes.LPCWSTR),
                ('lpParameters', wintypes.LPCWSTR), ('lpDirectory', wintypes.LPCWSTR),
                ('nShow', c_int), ('hInstApp', wintypes.HINSTANCE), ('lpIDList', c_void_p),
                ('lpClass', wintypes.LPCWSTR), ('hkeyClass', wintypes.HKEY), ('dwHotKey', wintypes.DWORD),
                ('hIconOrMonitor', wintypes.HANDLE), ('hProcess', wintypes.HANDLE)]


def _shell_execute(file, params, directory, show):
    sei = SHELLEXECUTEINFO()
    sei.cbSize = ctypes.sizeof(sei)
    sei.fMask = 0x00000040 | 0x00000400         # SEE_MASK_NOCLOSEPROCESS | SEE_MASK_FLAG_NO_UI
    sei.lpVerb = 'open'
    sei.lpFile = file
    sei.lpParameters = params or None
    sei.lpDirectory = directory or None
    sei.nShow = show
    if not shell32.ShellExecuteExW(byref(sei)):
        raise ctypes.WinError(ctypes.get_last_error())
    pid = None
    if sei.hProcess:
        pid = kernel32.GetProcessId(sei.hProcess)
        kernel32.CloseHandle(sei.hProcess)
    return pid


def launch(path, args, minimize):
    full = resolve(path)
    show = 7 if minimize else 1           # SW_SHOWMINNOACTIVE / SW_SHOWNORMAL
    return _shell_execute(full, args, os.path.dirname(full), show)


def run_detached(argv):
    import subprocess
    subprocess.Popen(argv, creationflags=0x00000008 | 0x00000200, close_fds=True)   # DETACHED | NEW_GROUP


# ---------------------------------------------------------------- windows
EnumWindowsProc = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
user32.GetWindowLongW.restype = ctypes.c_long


def windows_supported():
    return True


def window_tool_note():
    return ''


def list_windows():
    found = []

    def cb(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.GetWindow(hwnd, 4):                         # owned popup
            return True
        if user32.GetWindowLongW(hwnd, -20) & 0x80:           # tool window
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, byref(pid))
        found.append((int(hwnd), pid.value, ''))
        return True
    user32.EnumWindows(EnumWindowsProc(cb), 0)
    return found


def minimize_window(wid):
    if not user32.IsIconic(wid):
        user32.ShowWindowAsync(wid, 7)                        # SW_SHOWMINNOACTIVE


user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]


def close_window(wid, method='close'):
    """Politely asks a window to close. Returns 'ok', 'denied' (blocked by Windows: the app runs
    as administrator) or 'failed'."""
    if method == 'syscommand':
        ok = user32.PostMessageW(wid, 0x0112, 0xF060, 0)      # WM_SYSCOMMAND / SC_CLOSE (same as the X button)
    else:
        ok = user32.PostMessageW(wid, 0x0010, 0, 0)           # WM_CLOSE
    if ok:
        return 'ok'
    return 'denied' if ctypes.get_last_error() == 5 else 'failed'


def window_busy(wid):
    """True while the window is showing a question (a modal dialog disables its main window)."""
    return not user32.IsWindowEnabled(wid)


def window_info(wid):
    title = ctypes.create_unicode_buffer(200)
    cls = ctypes.create_unicode_buffer(100)
    try:
        user32.GetWindowTextW(wid, title, 200)
        user32.GetClassNameW(wid, cls, 100)
    except Exception:
        pass
    return '"%s" [%s]%s' % (title.value, cls.value, ' minimized' if user32.IsIconic(wid) else '')


def reveal_windows(wids):
    for w in wids:
        if user32.IsIconic(w):
            user32.ShowWindowAsync(w, 9)                      # SW_RESTORE
    if wids:
        top = user32.GetLastActivePopup(wids[0]) or wids[0]
        user32.SetForegroundWindow(top)


# ---------------------------------------------------------------- choosing programs
def _wsh():
    import comtypes.client
    return comtypes.client.CreateObject('WScript.Shell', dynamic=True)


def read_shortcut(path):
    try:
        sc = _wsh().CreateShortcut(path)
        if sc.TargetPath:
            return sc.TargetPath, sc.Arguments or ''
    except Exception:
        pass
    return path, ''


def pick_file(parent, initialdir):
    from tkinter import filedialog
    p = filedialog.askopenfilename(parent=parent, title='Choose the program to open',
                                   initialdir=initialdir or None,
                                   filetypes=[('Programs and shortcuts', '*.exe *.lnk *.bat *.cmd *.py *.pyw *.jar'),
                                              ('All files', '*.*')])
    return os.path.normpath(p) if p else None


def read_dropped(path):
    name = os.path.splitext(os.path.basename(path))[0]
    if path.lower().endswith('.lnk'):
        target, args = read_shortcut(path)
        return name, target, args
    return name, path, ''


def installed_apps():
    roots = [_programs_dir(), os.path.join(os.environ.get('ProgramData', r'C:\ProgramData'),
                                           r'Microsoft\Windows\Start Menu\Programs')]
    apps, seen = [], set()
    for r in roots:
        if not r or not os.path.isdir(r):
            continue
        for dirpath, _, files in os.walk(r):
            for fn in files:
                if not fn.lower().endswith('.lnk'):
                    continue
                name = os.path.splitext(fn)[0]
                if re.search(r'uninstall|readme|help|manual|website', name, re.I) or name.lower() in seen:
                    continue
                target, args = read_shortcut(os.path.join(dirpath, fn))
                if not target.lower().endswith('.exe') or 'digiapp' in target.lower():
                    continue
                seen.add(name.lower())
                apps.append((name, target, args))
    apps.sort(key=lambda a: a[0].lower())
    return apps


def find_program(name):
    key = re.sub(r'[^a-z0-9]', '', name.lower())
    roots = [os.environ.get('ProgramFiles'), os.environ.get('ProgramFiles(x86)'),
             os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs'),
             os.path.join(os.path.expanduser('~'), 'Desktop'), os.path.join(os.path.expanduser('~'), 'Documents'),
             os.path.join(os.path.expanduser('~'), 'Downloads'), 'C:\\']
    for r in roots:
        if not r or not os.path.isdir(r):
            continue
        depth0 = r.rstrip('\\').count('\\')
        limit = 2 if r == 'C:\\' else 4
        for dirpath, dirnames, files in os.walk(r):
            if dirpath.count('\\') - depth0 >= limit:
                dirnames[:] = []
            for fn in files:
                low = fn.lower()
                if low.endswith('.exe') and re.sub(r'[^a-z0-9]', '', low[:-4]).startswith(key) \
                        and not re.search(r'unins|setup|install|update', low):
                    return os.path.join(dirpath, fn)
    return None


# ---------------------------------------------------------------- taskbar icon + right-click list (jump list)
_com_ready = None


def _com():
    global _com_ready
    if _com_ready is not None:
        return _com_ready
    import comtypes
    from comtypes import GUID, IUnknown, COMMETHOD, HRESULT
    from comtypes.shelllink import IShellLinkW
    from comtypes.persist import IPersistFile

    class PROPERTYKEY(Structure):
        _fields_ = [('fmtid', GUID), ('pid', c_ulong)]

    class PROPVARIANT(Structure):
        _fields_ = [('vt', c_ushort), ('r1', c_ushort), ('r2', c_ushort), ('r3', c_ushort),
                    ('data', c_void_p), ('data2', c_void_p)]

    class IPropertyStore(IUnknown):
        _iid_ = GUID('{886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99}')
        _methods_ = [
            COMMETHOD([], HRESULT, 'GetCount', (['out'], POINTER(c_ulong), 'c')),
            COMMETHOD([], HRESULT, 'GetAt', (['in'], c_ulong, 'i'), (['out'], POINTER(PROPERTYKEY), 'k')),
            COMMETHOD([], HRESULT, 'GetValue', (['in'], POINTER(PROPERTYKEY), 'k'), (['in'], POINTER(PROPVARIANT), 'v')),
            COMMETHOD([], HRESULT, 'SetValue', (['in'], POINTER(PROPERTYKEY), 'k'), (['in'], POINTER(PROPVARIANT), 'v')),
            COMMETHOD([], HRESULT, 'Commit'),
        ]

    class IObjectArray(IUnknown):
        _iid_ = GUID('{92CA9DCD-5622-4BBA-A805-5E9F541BD8C9}')
        _methods_ = [
            COMMETHOD([], HRESULT, 'GetCount', (['out'], POINTER(c_uint), 'c')),
            COMMETHOD([], HRESULT, 'GetAt', (['in'], c_uint, 'i'), (['in'], POINTER(GUID), 'riid'),
                      (['out'], POINTER(c_void_p), 'ppv')),
        ]

    class IObjectCollection(IObjectArray):
        _iid_ = GUID('{5632B1A4-E38A-400A-928A-D4CD63230295}')
        _methods_ = [
            COMMETHOD([], HRESULT, 'AddObject', (['in'], POINTER(IUnknown), 'o')),
            COMMETHOD([], HRESULT, 'AddFromArray', (['in'], POINTER(IObjectArray), 'a')),
            COMMETHOD([], HRESULT, 'RemoveObjectAt', (['in'], c_uint, 'i')),
            COMMETHOD([], HRESULT, 'Clear'),
        ]

    class ICustomDestinationList(IUnknown):
        _iid_ = GUID('{6332DEBF-87B5-4670-90C0-5E57B408A49E}')
        _methods_ = [
            COMMETHOD([], HRESULT, 'SetAppID', (['in'], wintypes.LPCWSTR, 'id')),
            COMMETHOD([], HRESULT, 'BeginList', (['out'], POINTER(c_uint), 'slots'),
                      (['in'], POINTER(GUID), 'riid'), (['out'], POINTER(c_void_p), 'removed')),
            COMMETHOD([], HRESULT, 'AppendCategory', (['in'], wintypes.LPCWSTR, 'name'),
                      (['in'], POINTER(IObjectArray), 'a')),
            COMMETHOD([], HRESULT, 'AppendKnownCategory', (['in'], c_int, 'cat')),
            COMMETHOD([], HRESULT, 'AddUserTasks', (['in'], POINTER(IObjectArray), 'a')),
            COMMETHOD([], HRESULT, 'CommitList'),
            COMMETHOD([], HRESULT, 'GetRemovedDestinations', (['in'], POINTER(GUID), 'riid'),
                      (['out'], POINTER(c_void_p), 'ppv')),
            COMMETHOD([], HRESULT, 'DeleteList', (['in'], wintypes.LPCWSTR, 'id')),
            COMMETHOD([], HRESULT, 'AbortList'),
        ]

    comtypes.CoInitialize()
    _com_ready = {
        'comtypes': comtypes, 'GUID': GUID, 'IShellLinkW': IShellLinkW, 'IPersistFile': IPersistFile,
        'IPropertyStore': IPropertyStore, 'IObjectArray': IObjectArray, 'IObjectCollection': IObjectCollection,
        'ICustomDestinationList': ICustomDestinationList, 'PROPERTYKEY': PROPERTYKEY, 'PROPVARIANT': PROPVARIANT,
        'CLSID_ShellLink': GUID('{00021401-0000-0000-C000-000000000046}'),
        'CLSID_DestinationList': GUID('{77F10CF0-3DB5-4966-B520-B7C54FD35ED6}'),
        'CLSID_ObjectCollection': GUID('{2D3468C1-36A7-43B6-AC24-D3F02FD9607A}'),
        'FMT_APPMODEL': GUID('{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}'),
        'FMT_TITLE': GUID('{F29F85E0-4FF9-1068-AB91-08002B27B3D9}'),
    }
    return _com_ready


def _set_string(c, store, fmt, pid, value):
    key = c['PROPERTYKEY'](fmt, pid)
    pv = c['PROPVARIANT']()
    buf = ctypes.create_unicode_buffer(value)
    pv.vt = 31                                               # VT_LPWSTR
    pv.data = ctypes.cast(buf, c_void_p)
    store.SetValue(byref(key), byref(pv))


def _set_bool(c, store, fmt, pid, value):
    key = c['PROPERTYKEY'](fmt, pid)
    pv = c['PROPVARIANT']()
    pv.vt = 11                                               # VT_BOOL
    pv.data = 0xFFFF if value else 0
    store.SetValue(byref(key), byref(pv))


def _make_link(c, argv, icon, desc):
    link = c['comtypes'].CoCreateInstance(c['CLSID_ShellLink'], interface=c['IShellLinkW'])
    link.SetPath(argv[0])
    link.SetArguments(' '.join(_quote(a) for a in argv[1:]))
    link.SetWorkingDirectory(os.path.dirname(argv[0]))
    if icon:
        link.SetIconLocation(icon, 0)
    if desc:
        link.SetDescription(desc)
    return link


def _quote(a):
    return '"' + a.replace('"', '') + '"' if (' ' in a or not a) else a


EDIT_TITLE = APP_TITLE + ' - Edit'       # second shortcut that opens only the editor


def _common_dir(csidl):
    buf = ctypes.create_unicode_buffer(260)
    if shell32.SHGetFolderPathW(None, csidl, None, 0, buf) == 0:
        return buf.value
    return None


def _setup_install():
    """Installed by DigiAppLauncher-<ver>-Setup.exe (its uninstaller sits next to the exe)?"""
    return bool(getattr(sys, 'frozen', False)) and \
        os.path.exists(os.path.join(os.path.dirname(sys.executable), 'unins000.exe'))


def icon_installed():
    dirs = [_desktop_dir(), _programs_dir(), _common_dir(0x0019), _common_dir(0x0017)]   # + all-users desktop/menu
    return any(d and os.path.exists(os.path.join(d, APP_TITLE + '.lnk')) for d in dirs)


def _write_shortcuts(c, launch_cmd, icon):
    if _setup_install():
        # The installer made the icons (all users). Copies the program made earlier in the user's own desktop /
        # Start menu would show up twice, so they are removed; only the taskbar right-click list is refreshed.
        for d in (_desktop_dir(), _programs_dir()):
            for name in (APP_TITLE, EDIT_TITLE):
                p = d and os.path.join(d, name + '.lnk')
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except OSError:
                        pass
        return
    for d in (_desktop_dir(), _programs_dir()):
        if not d or not os.path.isdir(d):
            continue
        link = _make_link(c, launch_cmd + ['--run'], icon,
                          'Launch your default radio apps profile (right-click the taskbar icon for others)')
        store = link.QueryInterface(c['IPropertyStore'])
        _set_string(c, store, c['FMT_APPMODEL'], 5, APP_ID)
        store.Commit()
        link.QueryInterface(c['IPersistFile']).Save(os.path.join(d, APP_TITLE + '.lnk'), True)
        # "DigiApp Launcher - Edit": no --run, so it opens the editor and launches nothing
        edit = _make_link(c, list(launch_cmd), icon, 'Edit your apps and profiles (does not open any apps)')
        edit.QueryInterface(c['IPersistFile']).Save(os.path.join(d, EDIT_TITLE + '.lnk'), True)


def _write_jump_list(c, launch_cmd, icon, entries):
    dest = c['comtypes'].CoCreateInstance(c['CLSID_DestinationList'], interface=c['ICustomDestinationList'])
    dest.SetAppID(APP_ID)
    dest.BeginList(byref(c['IObjectArray']._iid_))
    coll = c['comtypes'].CoCreateInstance(c['CLSID_ObjectCollection'], interface=c['IObjectCollection'])
    for title, extra in entries:
        if title == '-':
            link = c['comtypes'].CoCreateInstance(c['CLSID_ShellLink'], interface=c['IShellLinkW'])
            store = link.QueryInterface(c['IPropertyStore'])
            _set_bool(c, store, c['FMT_APPMODEL'], 6, True)       # separator
            store.Commit()
        else:
            link = _make_link(c, launch_cmd + extra, icon, title)
            store = link.QueryInterface(c['IPropertyStore'])
            _set_string(c, store, c['FMT_TITLE'], 2, title)
            store.Commit()
        coll.AddObject(link)
    dest.AddUserTasks(coll.QueryInterface(c['IObjectArray']))
    dest.CommitList()


def refresh_menu(launch_cmd, icon, entries, also_desktop=False):
    c = _com()
    if also_desktop:
        _write_shortcuts(c, launch_cmd, icon)
    _write_jump_list(c, launch_cmd, icon, entries)
    return True


def pin_to_panel(add=True):
    return ''          # Windows doesn't allow programs to pin themselves; the user pins the desktop icon


FIRST_ICON_HELP = ("A gold 'DigiApp Launcher' icon is now on your desktop.\n\n"
                   "To pin it: right-click the desktop icon > Show more options > Pin to taskbar.\n\n"
                   "Click the taskbar icon to launch your default profile.\n"
                   "Right-click it to pick a different profile, Close apps, or edit your apps.\n\n"
                   "To change your apps without launching anything, double-click the\n"
                   "'DigiApp Launcher - Edit' icon on your desktop.")
