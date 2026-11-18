#!/bin/bash
# DigiApp Launcher - make the Linux download.
#   bash build_linux.sh            -> output/DigiApp-Launcher-<version>-Linux.tar.gz
#   bash build_linux.sh --no-tests    (skip the self-tests)
# Linux users run the Python files directly (Python 3 comes with every Linux), so nothing is compiled.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
VERSION="$(sed -n "s/^__version__ = '\(.*\)'/\1/p" digiapp/__init__.py)"
NAME="DigiApp-Launcher-${VERSION}-Linux"
echo "=== Building ${NAME} ==="

if [ "$1" != "--no-tests" ]; then
    echo "Running tests..."
    python3 -m unittest discover -s tests -q || { echo "Tests failed - fix them, or use --no-tests."; exit 1; }
fi

STAGE="build/linux/${NAME}"
rm -rf "build/linux"
mkdir -p "$STAGE/digiapp" output
cp digiapp/*.py "$STAGE/digiapp/"
cp run_digiapp.py icon.png linux_install.sh update_linux.sh install_linux_launcher.sh \
   linux_uninstall.sh digiapp.sh CHANGELOG.md "$STAGE/"
cp docs/README-Linux.txt "$STAGE/README.txt"
[ -f docs/DigiApp-Launcher-Guide.pdf ] && cp docs/DigiApp-Launcher-Guide.pdf "$STAGE/"
[ -f docs/Installing_DigiApp_Launcher_on_Linux.pdf ] && cp docs/Installing_DigiApp_Launcher_on_Linux.pdf "$STAGE/"
# .sh files must have Linux (LF) line endings - a Windows (CRLF) save gives confusing errors on Linux.
# The copies in the download are always fixed; the project files are only reported, so you can fix them too.
for f in "$STAGE"/*.sh; do
    if grep -q $'\r' "$f"; then
        echo "WARNING: $(basename "$f") had Windows line endings - fixed in the download (fix the project copy too)."
        sed -i 's/\r$//' "$f"
    fi
done
chmod +x "$STAGE"/*.sh "$STAGE/run_digiapp.py"
find "$STAGE" -name '__pycache__' -prune -exec rm -rf {} +

tar -C build/linux -czf "output/${NAME}.tar.gz" "$NAME"
echo ""
echo "Done:  output/${NAME}.tar.gz"
echo "Users install it with:   tar xzf ${NAME}.tar.gz && cd ${NAME} && bash linux_install.sh"
