#!/usr/bin/env python3
"""A stand-in "radio program" for testing DigiApp Launcher without real radio software.

It opens a small window and can imitate the awkward behaviours real programs have:

    python3 tools/mock_radio_app.py --title "Fake Fldigi" --ask        asks "Save changes?" when closed
    python3 tools/mock_radio_app.py --title "Fake Map" --slow 5        window closes, program takes 5 s to exit
    python3 tools/mock_radio_app.py --title "Fake Rig" --popup         restores itself after being minimized once
    python3 tools/mock_radio_app.py --title "Fake JS8" --class Tk      generic window class (like many Tk apps)

Add it to a profile with  Path = python3  and  Options = /full/path/tools/mock_radio_app.py --title "..." ...
"""
import argparse
import time
import tkinter as tk
from tkinter import messagebox


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--title', default='Mock Radio App')
    ap.add_argument('--class', dest='cls', default='mockradio', help='window class name')
    ap.add_argument('--ask', action='store_true', help='ask "Save changes?" before closing')
    ap.add_argument('--slow', type=float, default=0, help='seconds to keep running after the window closes')
    ap.add_argument('--popup', action='store_true', help='un-minimize itself once, shortly after starting')
    a = ap.parse_args()

    root = tk.Tk(className=a.cls)
    root.title(a.title)
    root.geometry('340x150')
    root.configure(bg='#0D1626')
    tk.Label(root, text=a.title, fg='#3DF58A', bg='#0D1626', font=('DejaVu Sans', 14, 'bold')).pack(expand=True)
    info = []
    if a.ask:
        info.append('asks before closing')
    if a.slow:
        info.append('slow exit %gs' % a.slow)
    if a.popup:
        info.append('pops back up')
    tk.Label(root, text=', '.join(info) or 'plain', fg='#8E9AB0', bg='#0D1626').pack(pady=(0, 14))

    def close():
        if a.ask and not messagebox.askyesno(a.title, 'Save changes to configuration?', parent=root):
            return                                  # "No" keeps it open, like many real programs' Cancel
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', close)
    if a.popup:
        root.after(2500, root.deiconify)
    root.mainloop()
    if a.slow:
        time.sleep(a.slow)


if __name__ == '__main__':
    main()
