"""Self-tests for DigiApp Launcher.   Run:  python3 -m unittest discover -s tests

These cover the parts that decide WHICH running program belongs to which app, how settings
are saved, and how menu/panel entries are written - the things that have caused real bugs.
They don't open any windows.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from digiapp import app
    from digiapp import plat_linux
except SystemExit:          # Tk missing on this machine
    app = None

LINUX = sys.platform.startswith('linux')


class Proc(object):
    def __init__(self, pid, ppid, exe, cmdline, state='S'):
        self.pid, self.ppid, self.exe, self.cmdline, self.state = pid, ppid, exe, cmdline, state


@unittest.skipIf(app is None, 'Tk for Python is not installed')
class TargetTests(unittest.TestCase):
    """app_target(): the file that identifies a running copy of an app."""

    @unittest.skipUnless(LINUX, 'Linux paths')
    def test_plain_program(self):
        self.assertEqual(app.app_target({'Path': '/usr/bin/env', 'Args': ''}), '/usr/bin/env')

    @unittest.skipUnless(LINUX, 'Linux paths')
    def test_python_script(self):
        self.assertEqual(app.app_target({'Path': '/usr/bin/python3', 'Args': '-u /opt/x/run.py'}), '/opt/x/run.py')

    @unittest.skipUnless(LINUX, 'Linux paths')
    def test_bash_dash_c_with_cd(self):
        t = app.app_target({'Path': '/usr/bin/bash',
                            'Args': "-c 'cd /home/u/Radio/JS8Spotter && python3 js8spotter.py'"})
        self.assertEqual(t, '/home/u/Radio/JS8Spotter/js8spotter.py')

    @unittest.skipUnless(LINUX, 'Linux paths')
    def test_sh_running_a_script(self):
        t = app.app_target({'Path': '/usr/bin/sh', 'Args': "'/home/u/JS8Map/start.sh'"})
        self.assertEqual(t, '/home/u/JS8Map/start.sh')

    def test_versioned_python_is_an_interpreter(self):
        self.assertTrue(app.is_interpreter('python3.12'))
        self.assertTrue(app.is_interpreter('python3'))
        self.assertFalse(app.is_interpreter('fldigi'))

    def test_command_string_parsing(self):
        t = app.target_from_command('cd /a/b; exec python3 ./tool.py --x')
        self.assertEqual(t.replace('\\', '/'), '/a/b/tool.py')
        self.assertEqual(app.target_from_command('VAR=1 nohup flrig'), 'flrig')


@unittest.skipIf(app is None, 'Tk for Python is not installed')
@unittest.skipUnless(LINUX, 'uses Linux process paths')
class MatchingTests(unittest.TestCase):
    """find_app_pids(), family() and app_windows(): which processes and windows belong to an app."""

    def setUp(self):
        self.procs = [
            Proc(10, 1, '/usr/bin/flrig', ['/usr/bin/flrig']),
            Proc(20, 1, '/usr/bin/bash', ['bash', '-c', 'cd /r/JS8Spotter && python3 js8spotter.py']),
            Proc(21, 20, '/usr/bin/python3.12', ['python3', 'js8spotter.py']),
            Proc(30, 1, '/usr/bin/dash', ['/usr/bin/sh', '/r/JS8Map/start.sh']),
            Proc(31, 30, '/usr/bin/python3.12', ['python3', 'main.py']),
            Proc(40, 1, '/usr/bin/python3.12', ['python3', '/other/js8spotter_notes.py']),
        ]

    def test_same_script_different_options_are_different_apps(self):
        procs = self.procs + [
            Proc(50, 1, '/usr/bin/python3.12', ['python3', '/t/mock.py', '--title', 'Fake Rig']),
            Proc(51, 1, '/usr/bin/python3.12', ['python3', '/t/mock.py', '--title', 'Fake Fldigi', '--ask'])]
        rig = {'Path': '/usr/bin/python3', 'Args': '/t/mock.py --title "Fake Rig"'}
        fl = {'Path': '/usr/bin/python3', 'Args': '/t/mock.py --title "Fake Fldigi" --ask'}
        other = {'Path': '/usr/bin/python3', 'Args': '/t/mock.py --title "Fake Map"'}
        self.assertEqual(app.find_app_pids(rig, procs), [50])
        self.assertEqual(app.find_app_pids(fl, procs), [51])
        self.assertEqual(app.find_app_pids(other, procs), [])

    def test_program_by_path(self):
        self.assertEqual(app.find_app_pids({'Path': '/usr/bin/flrig', 'Args': ''}, self.procs), [10])

    def test_script_through_bash(self):
        a = {'Path': '/usr/bin/bash', 'Args': "-c 'cd /r/JS8Spotter && python3 js8spotter.py'"}
        self.assertIn(21, app.find_app_pids(a, self.procs))
        self.assertNotIn(40, app.find_app_pids(a, self.procs))

    def test_family_includes_children(self):
        a = {'Path': '/usr/bin/sh', 'Args': "'/r/JS8Map/start.sh'"}
        pids = app.find_app_pids(a, self.procs)
        self.assertEqual(pids, [30])
        self.assertEqual(app.family(pids, self.procs), {30, 31})

    def test_window_by_app_name_when_no_pid(self):
        a = {'Name': 'JS8Map Spotter', 'Path': '/usr/bin/sh', 'Args': "'/r/JS8Map/start.sh'"}
        wins = [('0x1', 0, 'tk.tk js8map spotter ver 1.1'),
                ('0x2', 0, 'digiapplauncher.digiapplauncher digiapp launcher - js8map spotter'),
                ('0x3', 0, 'fldigi.fldigi fldigi ver4.2')]
        self.assertEqual(app.app_windows(a, {30, 31}, wins), ['0x1'])

    def test_window_by_pid(self):
        a = {'Name': 'Flrig', 'Path': '/usr/bin/flrig', 'Args': ''}
        self.assertEqual(app.app_windows(a, {10}, [('0x9', 10, 'x'), ('0x8', 11, 'flrig')]), ['0x9'])


@unittest.skipIf(app is None, 'Tk for Python is not installed')
class StoreTests(unittest.TestCase):
    """Settings: a new user gets one empty profile; old files are read; nothing personal is assumed."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.old = app.plat.config_dir
        app.plat.config_dir = lambda: self.tmp

    def tearDown(self):
        app.plat.config_dir = self.old
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_new_user_gets_one_empty_profile(self):
        s = app.Store()
        self.assertEqual([p['Name'] for p in s.profiles], ['My Profile'])
        self.assertEqual(s.profiles[0]['Apps'], [])
        self.assertFalse(s.welcomed)
        self.assertTrue(os.path.exists(os.path.join(self.tmp, 'settings.json')))

    def test_reads_older_settings_and_cleans_values(self):
        with open(os.path.join(self.tmp, 'settings.json'), 'w') as f:
            json.dump({'LastProfile': 'Net', 'Profiles': [
                {'Name': 'Net', 'Apps': {'Name': 'Flrig', 'Path': 'flrig', 'Delay': '7'}}]}, f)
        s = app.Store()
        self.assertEqual(s.default, 'Net')                     # old "LastProfile" key
        a = s.profiles[0]['Apps'][0]
        self.assertEqual((a['Delay'], a['Enabled'], a['Minimize']), (7, True, False))

    def test_menu_entries(self):
        s = app.Store()
        titles = [t for t, _ in s.menu_entries()]
        self.assertIn('Close Open Apps', titles)
        self.assertIn('Edit apps and profiles...', titles)
        self.assertTrue(titles[0].endswith('(default)'))

    def test_default_wait_is_two_seconds(self):
        self.assertEqual(app.DEFAULT_WAIT, 2)

    def test_themes_have_the_same_colours(self):
        self.assertEqual(set(app.THEMES['Dark']), set(app.THEMES['Light']))

    def test_theme_is_saved_and_old_files_get_dark(self):
        s = app.Store()
        self.assertEqual(s.theme, 'Dark')                  # files from before 1.3 have no Theme key
        s.theme = 'Light'
        s.save()
        self.assertEqual(app.Store().theme, 'Light')
        app.set_theme('Light')
        self.assertEqual(app.C['Bg'], app.THEMES['Light']['Bg'])
        app.set_theme('Dark')

    def test_unreadable_settings_are_kept(self):
        path = os.path.join(self.tmp, 'settings.json')
        with open(path, 'w') as f:
            f.write('{"Profiles": [{"Name": "JS8 Net", "Apps": []}],')      # broken by a hand edit
        s = app.Store()
        self.assertTrue(s.bad_copy)
        with open(s.bad_copy) as f:
            self.assertIn('JS8 Net', f.read())                           # the old profiles are still there
        self.assertEqual([p['Name'] for p in s.profiles], ['My Profile'])


@unittest.skipIf(app is None, 'Tk for Python is not installed')
class LinuxMenuTests(unittest.TestCase):
    """The .desktop entry (menu icon + right-click profile list) and panel pinning."""

    def test_exec_quoting(self):
        line = plat_linux._exec_line(['/usr/bin/python3', '/home/u/My Radio/run_digiapp.py', '--profile', '50% Net'])
        self.assertIn('"/home/u/My Radio/run_digiapp.py"', line)
        self.assertIn('50%%', line)

    def test_desktop_file_has_actions(self):
        text = plat_linux._desktop_text(['/usr/bin/python3', '/x/run_digiapp.py'], '/x/icon.png',
                                        [('A', ['--run', '--profile', 'A']), ('-', None), ('Close Open Apps', ['--close'])])
        self.assertIn('Actions=item0;item1;', text)
        self.assertIn('Name=Close Open Apps', text)
        self.assertIn('Exec=/usr/bin/python3 /x/run_digiapp.py --run\n', text)

    def test_edit_icon_opens_editor_only(self):
        text = plat_linux._edit_desktop_text(['/usr/bin/python3', '/x/run_digiapp.py'], '/x/icon.png')
        self.assertIn('Name=DigiApp Launcher - Edit\n', text)
        self.assertIn('Exec=/usr/bin/python3 /x/run_digiapp.py\n', text)      # no --run: nothing is launched
        self.assertNotIn('Actions=', text)

    @unittest.skipUnless(LINUX, 'Linux desktop files')
    def test_refresh_menu_writes_main_and_edit_icons(self):
        home = tempfile.mkdtemp()
        saved = dict((k, os.environ.get(k)) for k in ('HOME', 'XDG_DATA_HOME'))
        try:
            os.makedirs(os.path.join(home, 'Desktop'))
            os.environ['HOME'] = home
            os.environ.pop('XDG_DATA_HOME', None)
            cmd = ['/usr/bin/python3', '/x/run_digiapp.py']
            entries = [('A', ['--run', '--profile', 'A']), ('Edit apps and profiles...', [])]
            self.assertTrue(plat_linux.refresh_menu(cmd, '/x/icon.png', entries, also_desktop=True))
            apps = os.path.join(home, '.local', 'share', 'applications')
            for d in (apps, os.path.join(home, 'Desktop')):
                self.assertTrue(os.path.exists(os.path.join(d, 'digiapp-launcher.desktop')))
                self.assertTrue(os.path.exists(os.path.join(d, 'digiapp-launcher-edit.desktop')))
            self.assertFalse(plat_linux.refresh_menu(cmd, '/x/icon.png', entries))     # nothing changed
            os.environ['XDG_DATA_HOME'] = os.path.join(home, '.local', 'share')
            names = [a[0] for a in plat_linux.installed_apps()]
            self.assertNotIn('DigiApp Launcher - Edit', names)                      # not offered as an app
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
            shutil.rmtree(home, ignore_errors=True)

    @unittest.skipUnless(LINUX, 'Linux desktop settings')
    def test_cinnamon_pin_and_unpin_keep_other_settings(self):
        home = tempfile.mkdtemp()
        old_home, old_desk = os.environ.get('HOME'), os.environ.get('XDG_CURRENT_DESKTOP')
        try:
            d = os.path.join(home, '.config', 'cinnamon', 'spices', 'grouped-window-list@cinnamon.org')
            os.makedirs(d)
            f = os.path.join(d, '2.json')
            with open(f, 'w') as fh:
                json.dump({'pinned-apps': {'type': 'generic', 'default': [], 'value': ['nemo.desktop']},
                           'other': {'value': 5}}, fh)
            os.environ['HOME'] = home
            os.environ['XDG_CURRENT_DESKTOP'] = 'X-Cinnamon'
            self.assertIn('panel', plat_linux.pin_to_panel(True))
            plat_linux.pin_to_panel(True)                       # twice: no duplicate
            with open(f) as fh:
                data = json.load(fh)
            self.assertEqual(data['pinned-apps']['value'], ['nemo.desktop', 'digiapp-launcher.desktop'])
            plat_linux.pin_to_panel(False)
            with open(f) as fh:
                data = json.load(fh)
            self.assertEqual(data['pinned-apps']['value'], ['nemo.desktop'])
            self.assertEqual(data['other'], {'value': 5})
        finally:
            if old_home is not None:
                os.environ['HOME'] = old_home
            if old_desk is None:
                os.environ.pop('XDG_CURRENT_DESKTOP', None)
            else:
                os.environ['XDG_CURRENT_DESKTOP'] = old_desk
            shutil.rmtree(home, ignore_errors=True)



LOCALSEND = {'Enabled': True, 'Name': 'LocalSend', 'Path': '/usr/bin/flatpak', 'Delay': 2, 'Minimize': False,
             'Args': 'run --branch=stable --arch=x86_64 --command=localsend --file-forwarding '
                     'org.localsend.localsend_app @@u @@'}
FCC = {'Enabled': True, 'Name': 'FCC Lookup', 'Path': '/home/u/.local/bin/fcc-lookup', 'Args': '',
       'Delay': 2, 'Minimize': False}


@unittest.skipIf(app is None, 'Tk for Python is not installed')
class FlatpakTests(unittest.TestCase):
    """Flatpak apps are started with  flatpak run APPID  but run as  bwrap ... ."""

    def test_app_id_and_target(self):
        self.assertEqual(app.flatpak_app_id(LOCALSEND), 'org.localsend.localsend_app')
        self.assertEqual(app.app_target(LOCALSEND), 'org.localsend.localsend_app')
        self.assertEqual(app.flatpak_app_id(FCC), '')

    def test_window_found_by_app_id(self):
        wins = [('0x1', 0, 'org.localsend.localsend_app.org.localsend.localsend_app localsend'),
                ('0x2', 0, 'tk.tk fcc lookup ver 1.65 linux')]
        self.assertEqual(app.app_windows(LOCALSEND, set(), wins), ['0x1'])

    @unittest.skipUnless(LINUX, 'Linux process groups')
    def test_processes_found_by_flatpak_group(self):
        root = tempfile.mkdtemp()
        try:
            groups = {'38165': '0::/user.slice/app-flatpak-org.localsend.localsend_app-123.scope\n',
                      '38180': '0::/user.slice/app-flatpak-org.localsend.localsend_app-123.scope\n',
                      '38200': '0::/user.slice/app-flatpak-org.other.app-9.scope\n',
                      '38160': '0::/user.slice/app-gnome-terminal.scope\n'}
            for pid, text in groups.items():
                os.makedirs(os.path.join(root, pid))
                with open(os.path.join(root, pid, 'cgroup'), 'w') as f:
                    f.write(text)
            self.assertEqual(plat_linux.flatpak_pids('org.localsend.localsend_app', root), [38165, 38180])
        finally:
            shutil.rmtree(root, ignore_errors=True)

    @unittest.skipUnless(LINUX, 'Linux menu entries')
    def test_menu_entry_markers_are_dropped(self):
        d = tempfile.mkdtemp()
        try:
            f = os.path.join(d, 'x.desktop')
            with open(f, 'w') as fh:
                fh.write('[Desktop Entry]\nType=Application\nName=LocalSend\n'
                         'Exec=/usr/bin/flatpak run --branch=stable org.localsend.localsend_app @@u %U @@\n')
            name, prog, args = plat_linux.parse_desktop_file(f)
            self.assertEqual(args, 'run --branch=stable org.localsend.localsend_app')
        finally:
            shutil.rmtree(d, ignore_errors=True)


class FakeRoot(object):
    """Runs a job's  root.after(...)  steps one at a time, with a pretend clock."""

    def __init__(self):
        self.queue = []
        self.now = 1000.0

    def after(self, ms, fn):
        self.queue.append((ms, fn))
        return len(self.queue)

    def after_cancel(self, job):
        pass

    def run(self, limit=2000):
        steps = 0
        while self.queue and steps < limit:
            ms, fn = self.queue.pop(0)
            self.now += ms / 1000.0
            fn()
            steps += 1


@unittest.skipIf(app is None, 'Tk for Python is not installed')
class CloseTests(unittest.TestCase):
    """Close Open Apps for programs that are hard to recognise."""

    def setUp(self):
        self.cfg = tempfile.mkdtemp()
        self.root = FakeRoot()
        self.windows = []          # (id, pid, class+title)
        self.procs = []
        self.stopped = []
        self.closed_windows = []
        self.patches = [
            mock.patch.object(app.plat, 'config_dir', lambda: self.cfg),
            mock.patch.object(app.plat, 'list_processes', lambda: list(self.procs)),
            mock.patch.object(app.plat, 'list_windows', lambda: list(self.windows)),
            mock.patch.object(app.plat, 'windows_supported', lambda: True),
            mock.patch.object(app.plat, 'close_window', self.close_window),
            mock.patch.object(app.plat, 'reveal_windows', lambda w: None),
            mock.patch.object(app.plat, 'window_busy', lambda w: False),
            mock.patch.object(app.plat, 'window_info', lambda w: ''),
            mock.patch.object(app.plat, 'is_alive', lambda pid: any(p.pid == pid for p in self.procs)),
            mock.patch.object(app.plat, 'start_time', lambda pid: 77 if any(p.pid == pid for p in self.procs) else None),
            mock.patch.object(app.plat, 'terminate', self.terminate),
            mock.patch.object(app.time, 'time', lambda: self.root.now),
        ]
        if hasattr(app.plat, 'flatpak_pids'):
            self.patches.append(mock.patch.object(app.plat, 'flatpak_pids', lambda fid: [
                p.pid for p in self.procs if p.cmdline[:1] == ['bwrap']]))
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()
        shutil.rmtree(self.cfg, ignore_errors=True)

    def close_window(self, wid, method='close'):
        self.closed_windows.append(wid)
        self.windows = [w for w in self.windows if w[0] != wid]
        return 'ok'

    def terminate(self, pids):
        self.stopped += list(pids)
        self.procs = [p for p in self.procs if p.pid not in pids]

    def close(self, apps):
        result = {}
        job = app.CloseJob(self.root, apps, lambda t: None, lambda v, m: None,
                           lambda name: False, lambda j: result.setdefault('job', j))
        job.start()
        self.root.run()
        return result['job']

    def test_window_named_like_the_app_is_closed_when_no_process_matches(self):
        # fcc-lookup is a helper script that hands over to python3 FCC_Lookup.py; Tk windows have no pid
        self.procs = [Proc(38160, 1, '/usr/bin/python3.12', ['python3', '/home/u/.local/share/fcc-lookup/FCC_Lookup.py'])]
        self.windows = [('0x0500001f', 0, 'tk.tk fcc lookup ver 1.65 linux')]
        job = self.close([FCC])
        self.assertEqual(self.closed_windows, ['0x0500001f'])
        self.assertEqual(job.closed, ['FCC Lookup'])

    def test_launched_copy_is_remembered(self):
        self.procs = [Proc(38160, 1, '/usr/bin/python3.12', ['python3', '/home/u/.local/share/fcc-lookup/FCC_Lookup.py'])]
        self.assertEqual(app.running_pids(FCC, self.procs), [])
        app.Launched.record(FCC, 38160)
        self.assertEqual(app.running_pids(FCC, self.procs), [38160])
        self.procs = []
        self.assertEqual(app.running_pids(FCC, self.procs), [])          # ended: forgotten

    @unittest.skipUnless(LINUX, 'Flatpak is Linux only')
    def test_flatpak_app_that_hides_in_the_tray_is_asked_to_stop(self):
        self.procs = [Proc(38165, 1, '/usr/bin/bwrap', ['bwrap', '--args', '40', '--', 'localsend']),
                      Proc(38180, 38165, '/app/localsend', ['localsend'])]
        self.windows = [('0x05200003', 0, 'org.localsend.localsend_app.org.localsend.localsend_app localsend')]
        job = self.close([LOCALSEND])
        self.assertEqual(self.closed_windows, ['0x05200003'])
        self.assertEqual(sorted(self.stopped), [38165, 38180])
        self.assertEqual(job.closed, ['LocalSend'])

    def test_leftover_helper_without_a_window_does_not_hold_up_closing(self):
        # Seen with JS8Call on Windows: the program with the window ends at once, a second windowless process
        # of the same program lingers ~25 s - and Windows has no gentle way to stop it.
        js8 = {'Enabled': True, 'Name': 'JS8Call Ver 3.03', 'Path': '/opt/js8call/JS8Call', 'Args': '',
               'Delay': 2, 'Minimize': False}
        self.procs = [Proc(4620, 1, '/opt/js8call/JS8Call', ['/opt/js8call/JS8Call']),
                      Proc(16024, 1, '/opt/js8call/JS8Call', ['/opt/js8call/JS8Call'])]
        self.windows = [(68244, 16024, 'Qt693QWindowIcon JS8Call 3.0.3')]
        real_close = self.close_window

        def close_and_exit(wid, method='close'):
            r = real_close(wid, method)
            self.procs = [p for p in self.procs if p.pid != 16024]     # the window's program exits at once
            return r
        start = self.root.now
        with mock.patch.object(app.plat, 'close_window', close_and_exit), \
                mock.patch.object(app.plat, 'terminate', lambda pids: None):       # like Windows
            job = self.close([js8])
        self.assertEqual(job.closed, ['JS8Call Ver 3.03'])
        self.assertLess(self.root.now - start, 10)            # not the 60-second time limit

    def test_nothing_running_is_reported_not_running(self):
        job = self.close([FCC])
        self.assertEqual(job.not_running, ['FCC Lookup'])
        self.assertEqual(self.closed_windows, [])


if __name__ == '__main__':
    unittest.main()
