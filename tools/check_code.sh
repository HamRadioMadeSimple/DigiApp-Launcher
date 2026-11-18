#!/bin/bash
# Quick code checks before a release:  bash tools/check_code.sh
#   - pyflakes: mistakes such as unused or undefined names
#   - vermin:   confirms the code still runs on Python 3.5 (older Ubuntu releases)
#   - line endings: .sh files must be LF (Linux), .bat files CRLF (Windows)
#   - the self-tests
# Needs:  pip install pyflakes vermin
cd "$(dirname "$0")/.." || exit 1
python3 -m pyflakes run_digiapp.py digiapp/ tests/ tools/ && echo "pyflakes: clean"
vermin -q --no-tips -t=3.5- --violations run_digiapp.py digiapp/ && echo "vermin: OK for Python 3.5+"
bad=""
for f in *.sh tools/*.sh; do grep -q $'\r' "$f" && bad="$bad $f"; done
for f in *.bat; do grep -qv $'\r$' "$f" && bad="$bad $f"; done
if [ -n "$bad" ]; then
    echo "line endings: WRONG in:$bad  (.sh must be LF, .bat CRLF - see .gitattributes)"
else
    echo "line endings: OK"
fi
python3 -m unittest discover -s tests -q
