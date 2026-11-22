#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m pip install -r requirements-dev.txt
python -m ruff format --check .
python -m ruff check .
python -m unittest discover -s tests -v
python -m compileall -q portal
python -m portal --help >/dev/null
echo "Contrôles réussis"
