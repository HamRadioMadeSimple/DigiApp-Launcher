"""Zip the Windows portable folder (called by build_windows.bat).

    python tools/make_portable_zip.py output\\DigiApp-Launcher-<ver>-Windows-Portable

Windows Defender often locks a freshly built .exe for a few seconds while it scans it, which made
PowerShell's Compress-Archive fail with "being used by another process". This waits and retries,
and returns an error code if the zip still can't be made, so the build doesn't claim success.
"""
import os
import sys
import time
import zipfile


def make(folder):
    out = folder.rstrip('\\/') + '.zip'
    top = os.path.basename(folder.rstrip('\\/'))
    tmp = out + '.part'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(os.listdir(folder)):
            z.write(os.path.join(folder, name), top + '/' + name)
    if os.path.exists(out):
        os.remove(out)
    os.rename(tmp, out)
    return out


def main():
    folder = sys.argv[1]
    for attempt in range(1, 11):
        try:
            print(' Portable zip: ' + make(folder))
            return 0
        except (IOError, OSError) as e:
            print(' Portable zip: file busy (%s) - retrying in 3 s (%d/10)' % (e, attempt))
            time.sleep(3)
    print(' Portable zip FAILED - close anything using the output folder (or the program) and run again.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
