#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  FluxKey - Build Linux Binary + Package
#  Run this on any Linux machine or WSL2
#
#  Usage:
#    chmod +x build_linux.sh
#    ./build_linux.sh
#
#  Output:
#    dist/FluxKey_Linux/          - binary folder
#    dist/FluxKey_Linux.tar.gz    - distributable archive
#    dist/install_linux.sh        - one-command installer for users
# ─────────────────────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

echo ""
echo "  ====================================================="
echo "   FluxKey  |  Build Linux Binary + Package"
echo "  ====================================================="
echo ""

# ── Find Python ──────────────────────────────────────────────────────────────
PYTHON=""

for cmd in python3.13 python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        ver=$("$cmd" --version 2>&1)
        echo "  Found: $cmd  ($ver)"
        PYTHON="$cmd"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "  ERROR: Python not found."
    echo "  Install with:  sudo apt install python3 python3-pip"
    exit 1
fi

echo "  Using: $PYTHON"
echo ""

# ── Check we're on Linux ──────────────────────────────────────────────────────
OS="$($PYTHON -c "import platform; print(platform.system())")"
if [ "$OS" = "Windows" ]; then
    echo "  ERROR: This script must run on Linux or WSL."
    echo "  On Windows use:  build_exe.bat"
    exit 1
fi

# ── Install dependencies ──────────────────────────────────────────────────────
echo "  [1/2] Installing dependencies..."
$PYTHON -m pip install -r requirements.txt --quiet --disable-pip-version-check
echo "  Done."
echo ""

# ── Build ─────────────────────────────────────────────────────────────────────
echo "  [2/2] Building Linux binary..."
echo "  (Takes 2-5 minutes on first run)"
echo ""
$PYTHON main.py --linux

# ── Result ───────────────────────────────────────────────────────────────────
echo ""
if [ -f "dist/FluxKey_Linux.tar.gz" ]; then
    echo "  ====================================================="
    echo "   Build Complete!"
    echo "  ====================================================="
    echo ""
    echo "   Archive:    dist/FluxKey_Linux.tar.gz"
    echo "   Installer:  dist/install_linux.sh"
    echo "   Binary:     dist/FluxKey_Linux/FluxKey"
    echo ""
    echo "   To test right now:"
    echo "     ./dist/FluxKey_Linux/FluxKey"
    echo ""
    echo "   To install system-wide:"
    echo "     bash dist/install_linux.sh"
    echo ""
else
    echo "  Build may have failed — check output above."
fi
