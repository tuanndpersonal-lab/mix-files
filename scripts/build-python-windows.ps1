$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
py -m venv python_app\.venv-build
python_app\.venv-build\Scripts\python.exe -m pip install --upgrade pip
python_app\.venv-build\Scripts\python.exe -m pip install -r python_app\requirements-build.txt
python_app\.venv-build\Scripts\python.exe scripts\build_python_app.py
