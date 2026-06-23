from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON_APP = ROOT / "python_app"
ENTRYPOINT = PYTHON_APP / "mix_files_pyqt.py"
BUILD_ROOT = ROOT / "build" / "pyinstaller"
DIST_ROOT = ROOT / "dist" / "python"
APP_NAME = "MixFiles"


def run(command: list[str], cwd: Path = ROOT) -> None:
    print("$ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def ensure_entrypoint() -> None:
    if not ENTRYPOINT.exists():
        raise SystemExit(f"Missing entrypoint: {ENTRYPOINT}")


def clean() -> None:
    shutil.rmtree(BUILD_ROOT, ignore_errors=True)
    DIST_ROOT.mkdir(parents=True, exist_ok=True)


def build() -> Path:
    ensure_entrypoint()
    clean()

    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name",
        APP_NAME,
        "--distpath",
        str(DIST_ROOT),
        "--workpath",
        str(BUILD_ROOT / "work"),
        "--specpath",
        str(BUILD_ROOT),
        str(ENTRYPOINT),
    ]

    run(command)

    candidates = []
    if platform.system() == "Darwin":
        candidates.extend([
            DIST_ROOT / f"{APP_NAME}.app",
            DIST_ROOT / APP_NAME / APP_NAME,
        ])
    elif platform.system() == "Windows":
        candidates.extend([
            DIST_ROOT / APP_NAME / f"{APP_NAME}.exe",
            DIST_ROOT / f"{APP_NAME}.exe",
        ])
    else:
        candidates.append(DIST_ROOT / APP_NAME / APP_NAME)

    artifact = next((candidate for candidate in candidates if candidate.exists()), candidates[0])

    if not artifact.exists():
        expected = ", ".join(str(candidate) for candidate in candidates)
        raise SystemExit(f"Build finished but artifact was not found. Expected one of: {expected}")

    print(f"Built artifact: {artifact}")
    return artifact


def package_artifact(artifact: Path) -> Path:
    system = platform.system().lower()
    machine = platform.machine().lower() or "unknown"
    archive_base = DIST_ROOT / f"{APP_NAME}-{system}-{machine}"

    if artifact.suffix == ".app":
        source = artifact
    elif artifact.is_file():
        source = artifact.parent
    else:
        source = artifact

    archive = shutil.make_archive(str(archive_base), "zip", root_dir=source.parent, base_dir=source.name)
    print(f"Packaged archive: {archive}")
    return Path(archive)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Python/PyQt Mix Files desktop app.")
    parser.add_argument("--no-package", action="store_true", help="Skip zip packaging after PyInstaller build.")
    args = parser.parse_args()

    artifact = build()

    if not args.no_package:
        package_artifact(artifact)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
