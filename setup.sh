#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo
echo "Setup complete."
echo "Activate the environment:  source venv/bin/activate"
echo "Run the app:               python yt_dlp_gui.py"
echo "Run tests:                 python -m unittest discover -s . -p 'test_*.py'"
