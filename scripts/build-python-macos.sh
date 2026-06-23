#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv python_app/.venv-build
source python_app/.venv-build/bin/activate
python -m pip install --upgrade pip
python -m pip install -r python_app/requirements-build.txt
python scripts/build_python_app.py
