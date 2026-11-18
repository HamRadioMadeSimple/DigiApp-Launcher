#!/usr/bin/env python3
"""Zip the whole project folder for sending (to a new session, a helper, a backup).

    python tools/make_project_zip.py          (Windows: py tools\\make_project_zip.py)
        -> DigiApp_Launcher-<version>-Project.zip next to the project folder
    python tools/make_project_zip.py --github
        -> DigiApp-Launcher-<version>.zip (for GitHub): the same, without your own development notes

Use this instead of "Send to > Compressed folder" in Windows Explorer, because it:
  - leaves out build/, dist/ and output/ (big, and stale copies cause "old version starts" problems)
    plus __pycache__ and editor folders,
  - keeps the "executable" mark on .sh files (Explorer zips drop it -> "Permission denied" on Linux),
  - stores .sh files with Linux (LF) line endings and .bat files with Windows (CRLF) line endings,
  - refuses to include anything that looks like a user's own settings or logs.
Runs on Windows and Linux with plain Python 3.
"""
import os
import re
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {'build', 'dist', 'output', '__pycache__', '.git', '.vscode', '.idea', 'node_modules'}
SKIP_FILES = re.compile(r'(\.pyc$|\.spec\.bak$|^settings\.json$|^settings-unreadable-.*\.json$|^launched\.json$'
                        r'|^close-log\.txt$|^DigiAppLauncher\.json$|\.zip$)', re.IGNORECASE)
PRIVATE = {'DigiApp_Session_Handoff.md'}         # own development notes - left out with --github


def version():
    with open(os.path.join(ROOT, 'digiapp', '__init__.py')) as f:
        m = re.search(r"__version__ = '([^']+)'", f.read())
    return m.group(1) if m else 'dev'


def main():
    top = os.path.basename(ROOT)
    github = '--github' in sys.argv
    if github:                               # the public source: DigiApp-Launcher-<ver>.zip, folder DigiApp-Launcher
        top = 'DigiApp-Launcher'
        out = os.path.join(os.path.dirname(ROOT), '%s-%s.zip' % (top, version()))
    else:
        out = os.path.join(os.path.dirname(ROOT), '%s-%s-Project.zip' % (top, version()))
    count = 0
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for name in sorted(filenames):
                if SKIP_FILES.search(name) or (github and name in PRIVATE):
                    continue
                path = os.path.join(dirpath, name)
                rel = os.path.relpath(path, ROOT).replace(os.sep, '/')
                with open(path, 'rb') as f:
                    data = f.read()
                if name.endswith('.sh'):
                    data = data.replace(b'\r\n', b'\n')
                elif name.lower().endswith('.bat'):
                    data = data.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n')
                info = zipfile.ZipInfo(top + '/' + rel, time.localtime(os.path.getmtime(path))[:6])
                info.compress_type = zipfile.ZIP_DEFLATED
                info.create_system = 3                      # "made on Unix" so the marks below are used
                executable = name.endswith('.sh') or rel == 'run_digiapp.py'
                info.external_attr = ((0o100755 if executable else 0o100644) & 0xFFFF) << 16
                z.writestr(info, data)
                count += 1
    print('Done: %s  (%d files; build/, dist/ and output/ left out)' % (out, count))


if __name__ == '__main__':
    sys.exit(main())
