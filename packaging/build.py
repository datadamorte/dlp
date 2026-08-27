#!/usr/bin/env python3
"""Build a portable yt-dlp-gui bundle with PyInstaller."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "yt-dlp-gui"


def _platform_bundle_name() -> str:
    if sys.platform.startswith("win"):
        return f"{NAME}-windows.zip"
    if sys.platform == "darwin":
        return f"{NAME}-macos.zip"
    return f"{NAME}-linux.tar.gz"


def run_pyinstaller() -> Path:
    os.chdir(ROOT)
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--name",
        NAME,
        "--hidden-import",
        "ytdlp_core",
        str(ROOT / "yt_dlp_gui.py"),
    ]
    print(" ".join(cmd))
    subprocess.check_call(cmd)

    app = ROOT / "dist" / f"{NAME}.app"
    folder = ROOT / "dist" / NAME
    if app.exists():
        return app
    if folder.exists():
        return folder
    raise SystemExit(f"PyInstaller output not found under {ROOT / 'dist'}")


def pack(source: Path, archive_name: str) -> Path:
    dest = ROOT / archive_name
    if dest.exists():
        dest.unlink()
    if archive_name.endswith(".tar.gz"):
        # make_archive adds the suffix itself when format is gztar
        base = str(dest).removesuffix(".tar.gz")
        result = Path(shutil.make_archive(base, "gztar", root_dir=source.parent, base_dir=source.name))
        if result != dest and result.exists():
            result.rename(dest)
        return dest
    base = str(dest).removesuffix(".zip")
    result = Path(shutil.make_archive(base, "zip", root_dir=source.parent, base_dir=source.name))
    if result != dest and result.exists():
        result.rename(dest)
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundle",
        action="store_true",
        help="Also zip/tar the dist folder for GitHub Releases",
    )
    parser.add_argument("--name", default=None, help="Override archive file name")
    args = parser.parse_args()

    output = run_pyinstaller()
    print("Built", output)
    if args.bundle:
        archive = pack(output, args.name or _platform_bundle_name())
        print("Packed", archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
