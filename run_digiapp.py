#!/usr/bin/env python3
"""DigiApp Launcher - start here.

    python3 run_digiapp.py                    open the editor
    python3 run_digiapp.py --run              launch the default profile
    python3 run_digiapp.py --run --profile X  launch profile X
    python3 run_digiapp.py --close            close the open apps (last one first)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from digiapp.app import main  # noqa: E402

if __name__ == '__main__':
    sys.exit(main())
