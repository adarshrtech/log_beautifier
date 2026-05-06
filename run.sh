#!/bin/bash
BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$BASE_DIR"

VENV_PYTHON="$BASE_DIR/venv/bin/python3"

if [ ! -d "venv" ]; then
    echo " Creating local virtual environment..."
    python3 -m venv venv
fi
if ! "$VENV_PYTHON" -c "import textual, rich" &>/dev/null; then
    echo "🔧 Installing/Fixing dependencies inside venv..."
    "$VENV_PYTHON" -m pip install --upgrade pip
    "$VENV_PYTHON" -m pip install textual rich
fi

export PYTHONPATH="$BASE_DIR"

if [ -f "src/main.py" ]; then
    "$VENV_PYTHON" src/main.py "$@"
else
    "$VENV_PYTHON" main.py "$@"
fi
