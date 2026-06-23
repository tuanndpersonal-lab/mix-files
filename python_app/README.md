# Mix Files Python + PyQt

A simple desktop version of Mix Files built with Python and PyQt6.

## Install

```bash
cd python_app
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

On Windows PowerShell:

```powershell
cd python_app
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run

```bash
python mix_files_pyqt.py
```

## Features

- Choose source and output folders with native folder dialogs.
- Set the number of folders to create.
- Set how many MP3 files each folder should contain, or choose `All files`.
- Optionally add numeric prefixes such as `1_song.mp3`.
- Optionally clean the output folder before generating.
- Optionally use a shuffle seed for repeatable output.
- Open the generated output folder and copy generated paths.

## Build an executable

### macOS

```bash
cd ..
./scripts/build-python-macos.sh
```

The generated `.app` and `.zip` are created in `dist/python/`.

### Windows

Run this on a Windows machine or GitHub Actions Windows runner:

```powershell
cd ..
.\scripts\build-python-windows.ps1
```

The generated `.exe` folder and `.zip` are created in `dist\python\`.

### GitHub Actions

The workflow at `.github/workflows/build-python-app.yml` builds both macOS and Windows artifacts. Run it manually from the Actions tab or push a tag matching `python-v*`.
