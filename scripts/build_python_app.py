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


def normalize_machine_name() -> str:
    machine = platform.machine().lower() or "unknown"

    if machine in {"x86_64", "amd64"}:
        return "amd64"

    if machine in {"arm64", "aarch64"}:
        return "arm64"

    return machine


def sign_macos_app(artifact: Path) -> None:
    if platform.system() != "Darwin" or artifact.suffix != ".app":
        return

    run(["xattr", "-cr", str(artifact)])
    run(["codesign", "--force", "--deep", "--sign", "-", str(artifact)])


def package_artifact(artifact: Path) -> Path:
    sign_macos_app(artifact)

    system = platform.system().lower()
    machine = normalize_machine_name()
    archive_base = DIST_ROOT / f"{APP_NAME}-{system}-{machine}"

    if artifact.suffix == ".app" and platform.system() == "Darwin":
        archive = archive_base.with_suffix(".zip")
        archive.unlink(missing_ok=True)
        run([
            "ditto",
            "-c",
            "-k",
            "--sequesterRsrc",
            "--keepParent",
            str(artifact),
            str(archive),
        ])
        print(f"Packaged archive: {archive}")
        return archive

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
