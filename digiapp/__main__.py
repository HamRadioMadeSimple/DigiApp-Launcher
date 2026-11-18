"""Allows:  python3 -m digiapp  [--run | --close | --profile NAME | --install-icon]"""
import sys

from digiapp.app import main

sys.exit(main())
