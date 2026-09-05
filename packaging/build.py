#!/usr/bin/env python3
"""Build a portable dropdlp (yt-dlp-gui) bundle with PyInstaller.

The v1.2.0 macOS zip was created with shutil.make_archive(), which drops
Unix symlinks. PyInstaller .app bundles rely on those links (python3.12 ->
python3__dot__12, Python.framework/Versions/Current, …), so Finder-unzipped
apps crashed on launch. This script preserves symlinks and then smoke-tests
the frozen binary.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "yt-dlp-gui"
BUNDLE_ID = "com.dropdlp.app"
sys.path.insert(0, str(ROOT))
from ytdlp_core import APP_VERSION  # noqa: E402


def _platform_bundle_name() -> str:
    machine = platform.machine().lower()
    if sys.platform.startswith("win"):
        return f"{NAME}-windows.zip"
    if sys.platform == "darwin":
        arch = "arm64" if machine in {"arm64", "aarch64"} else "x64"
        return f"{NAME}-macos-{arch}.zip"
    return f"{NAME}-linux.tar.gz"


def is_zip_symlink(info: zipfile.ZipInfo) -> bool:
    return stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF)


def _safe_join(root: Path, name: str) -> Path:
    if not name or name.startswith("/") or name.startswith("\\") or ":" in Path(name).parts[0]:
        raise ValueError(f"unsafe zip path: {name}")
    dest = root.joinpath(*Path(name).parts)
    resolved_root = root.resolve()
    try:
        dest.resolve().relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"unsafe zip path: {name}") from exc
    return dest


def _add_zip_symlink(zf: zipfile.ZipFile, parent: Path, path: Path) -> None:
    arcname = path.relative_to(parent).as_posix()
    target = os.readlink(path)
    info = zipfile.ZipInfo(arcname)
    info.create_system = 3
    mode = path.lstat().st_mode
    info.external_attr = (stat.S_IFLNK | (mode & 0o777)) << 16
    payload = target.encode("utf-8") if isinstance(target, str) else target
    zf.writestr(info, payload)


def _add_zip_file(zf: zipfile.ZipFile, parent: Path, path: Path) -> None:
    arcname = path.relative_to(parent).as_posix()
    st = path.stat()
    info = zipfile.ZipInfo(arcname, time.localtime(st.st_mtime)[:6])
    info.create_system = 3
    info.external_attr = (st.st_mode & 0xFFFF) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    with path.open("rb") as handle:
        zf.writestr(info, handle.read())


def create_zip_preserving_links(source: Path, dest: Path) -> None:
    """Zip a tree while storing Unix symlinks and executable bits."""
    source = source.resolve()
    parent = source.parent
    if dest.exists():
        dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
        for dirpath, dirnames, filenames in os.walk(source, followlinks=False):
            dirpath_p = Path(dirpath)
            rel_dir = dirpath_p.relative_to(parent).as_posix()
            dir_info = zipfile.ZipInfo(rel_dir + "/")
            dir_info.create_system = 3
            dir_mode = dirpath_p.stat().st_mode
            dir_info.external_attr = (stat.S_IFDIR | (dir_mode & 0o777)) << 16
            zf.writestr(dir_info, b"")

            for name in list(dirnames):
                child = dirpath_p / name
                if child.is_symlink():
                    dirnames.remove(name)
                    _add_zip_symlink(zf, parent, child)

            for name in filenames:
                child = dirpath_p / name
                if child.is_symlink():
                    _add_zip_symlink(zf, parent, child)
                elif child.is_file():
                    _add_zip_file(zf, parent, child)


def extract_zip_preserving_links(archive: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as zf:
        regular = [info for info in zf.infolist() if not is_zip_symlink(info)]
        links = [info for info in zf.infolist() if is_zip_symlink(info)]
        for info in regular:
            target = _safe_join(dest, info.filename)
            if info.is_dir() or info.filename.endswith("/"):
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(target, "wb") as out:
                shutil.copyfileobj(src, out)
            mode = (info.external_attr >> 16) & 0xFFFF
            if mode:
                os.chmod(target, stat.S_IMODE(mode) or 0o644)
        for info in links:
            target = _safe_join(dest, info.filename)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists() or target.is_symlink():
                target.unlink()
            os.symlink(zf.read(info).decode("utf-8"), target)


def pack(source: Path, archive_name: str) -> Path:
    dest = ROOT / archive_name
    if dest.exists():
        dest.unlink()
    if archive_name.endswith(".tar.gz"):
        base = str(dest).removesuffix(".tar.gz")
        result = Path(shutil.make_archive(base, "gztar", root_dir=source.parent, base_dir=source.name))
        if result != dest and result.exists():
            result.rename(dest)
        return dest

    if sys.platform == "darwin" and shutil.which("ditto"):
        subprocess.check_call(
            ["ditto", "-c", "-k", "--keepParent", str(source), str(dest)],
            cwd=source.parent,
        )
        return dest
    if shutil.which("zip") and sys.platform != "win32":
        subprocess.check_call(
            ["zip", "-ry", str(dest), source.name],
            cwd=source.parent,
        )
        return dest
    create_zip_preserving_links(source, dest)
    return dest


def extract_archive(archive: Path, dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    name = archive.name.lower()
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        shutil.unpack_archive(archive, dest)
    elif sys.platform == "darwin" and shutil.which("ditto"):
        subprocess.check_call(["ditto", "-x", "-k", str(archive), str(dest)])
    else:
        extract_zip_preserving_links(archive, dest)
    entries = [path for path in dest.iterdir() if path.name != "__MACOSX"]
    if len(entries) == 1:
        return entries[0]
    return dest


def _find_gui_executable(root: Path) -> Path:
    apps = list(root.glob("*.app")) if root.is_dir() else []
    if root.suffix == ".app":
        apps = [root]
    if apps:
        macos = apps[0] / "Contents" / "MacOS"
        for path in macos.iterdir() if macos.is_dir() else []:
            if path.is_file() and not path.name.startswith("."):
                return path
        raise SystemExit(f"No executable in {macos}")

    windows = list(root.rglob("yt-dlp-gui.exe")) if root.is_dir() else []
    if windows:
        return windows[0]
    if root.is_file() and root.name.endswith(".exe"):
        return root

    linux = [
        path
        for path in root.rglob("yt-dlp-gui")
        if path.is_file() and not path.name.endswith(".exe")
    ]
    if linux:
        return linux[0]
    raise SystemExit(f"Could not find yt-dlp-gui inside {root}")


def _looks_like_pe(path: Path) -> bool:
    return path.read_bytes()[:2] == b"MZ"


def _looks_like_elf(path: Path) -> bool:
    return path.read_bytes()[:4] == b"\x7fELF"


def _looks_like_macho(path: Path) -> bool:
    magic = path.read_bytes()[:4]
    return magic in {
        b"\xcf\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
        b"\xfe\xed\xfa\xce",
        b"\xce\xfa\xed\xfe",
    }


def verify_extracted_bundle(root: Path) -> Path:
    """Fail the build if a packed app would not launch (missing links/bits)."""
    exe = _find_gui_executable(root)
    data = exe.read_bytes()[:4]
    if exe.suffix.lower() == ".exe":
        if not _looks_like_pe(exe):
            raise SystemExit(f"{exe} is not a Windows PE executable")
    elif data[:4] == b"\x7fELF":
        if not os.access(exe, os.X_OK):
            raise SystemExit(f"{exe} is not executable")
    elif _looks_like_macho(exe):
        if not os.access(exe, os.X_OK):
            raise SystemExit(f"{exe} is not executable")
    else:
        raise SystemExit(f"{exe} is not a recognized executable (magic={data!r})")

    apps = [root] if root.suffix == ".app" else list(root.glob("*.app"))
    for app in apps:
        for fw in (app / "Contents" / "Frameworks", app / "Contents" / "Resources"):
            dotted = fw / "python3__dot__12"
            alias = fw / "python3.12"
            if dotted.exists() and not alias.is_symlink():
                raise SystemExit(
                    f"{alias} must be a symlink to python3__dot__12; "
                    "the zip dropped macOS framework links and the app will not launch"
                )
            versions = fw / "Python.framework" / "Versions"
            current = versions / "Current"
            if versions.is_dir():
                numbered = [path for path in versions.iterdir() if path.name != "Current"]
                if numbered and not current.is_symlink():
                    raise SystemExit(
                        f"{current} must be a symlink; shutil.make_archive-style zips break this app"
                    )
        plist = app / "Contents" / "Info.plist"
        if not plist.is_file():
            raise SystemExit(f"Missing Info.plist in {app}")
    return exe


def verify_archive(archive: Path) -> Path:
    with tempfile.TemporaryDirectory(prefix="dropdlp-verify-") as tmp:
        extracted = extract_archive(archive, Path(tmp) / "out")
        return verify_extracted_bundle(extracted)


def extra_binaries() -> list[tuple[str, str]]:
    """Collect Linux X11 libs PyInstaller often misses so the xcb plugin can load."""
    if not sys.platform.startswith("linux"):
        return []
    names = (
        "libxcb-icccm.so.4",
        "libxcb-image.so.0",
        "libxcb-keysyms.so.1",
        "libxcb-render-util.so.0",
        "libxcb-shape.so.0",
        "libxcb-xinerama.so.0",
        "libxcb-xkb.so.1",
        "libxkbcommon-x11.so.0",
    )
    dirs = (
        Path("/usr/lib/x86_64-linux-gnu"),
        Path("/usr/lib64"),
        Path("/lib/x86_64-linux-gnu"),
        Path("/usr/lib"),
    )
    found: list[tuple[str, str]] = []
    for name in names:
        for folder in dirs:
            path = folder / name
            if path.is_file():
                found.append((str(path), "."))
                break
    return found


def _write_spec(windowed: bool) -> Path:
    spec_path = ROOT / f"{NAME}.spec"
    script = (ROOT / "yt_dlp_gui.py").as_posix()
    console = not windowed
    argv_emulation = sys.platform == "darwin"
    bundle_block = ""
    if sys.platform == "darwin":
        bundle_block = f"""
app = BUNDLE(
    coll,
    name='{NAME}.app',
    icon=None,
    bundle_identifier='{BUNDLE_ID}',
    info_plist={{
        'CFBundleName': 'dropdlp',
        'CFBundleDisplayName': 'dropdlp',
        'CFBundleShortVersionString': '{APP_VERSION}',
        'CFBundleVersion': '{APP_VERSION}',
        'CFBundleIdentifier': '{BUNDLE_ID}',
        'LSMinimumSystemVersion': '11.0',
        'NSHighResolutionCapable': True,
        'NSAppleEventsUsageDescription': (
            'dropdlp reads browser cookies through yt-dlp when you choose a browser in Cookies.'
        ),
    }},
)
"""
    extras = extra_binaries()
    extras_repr = repr(extras)
    spec_path.write_text(
        f"""# -*- mode: python ; coding: utf-8 -*-
# Generated by packaging/build.py — do not edit by hand.

a = Analysis(
    [{script!r}],
    pathex=[{str(ROOT)!r}],
    binaries={extras_repr},
    datas=[],
    hiddenimports=['ytdlp_core', 'PyQt5.sip'],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{NAME}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console={console},
    disable_windowed_traceback=False,
    argv_emulation={argv_emulation},
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='{NAME}',
)
{bundle_block}
""",
        encoding="utf-8",
    )
    return spec_path


def run_pyinstaller() -> Path:
    os.chdir(ROOT)
    windowed = sys.platform.startswith("win") or sys.platform == "darwin"
    spec = _write_spec(windowed=windowed)
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        str(spec),
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


def smoke_test(exe: Path, timeout: int = 60) -> None:
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    with tempfile.TemporaryDirectory(prefix="dropdlp-smoke-") as tmp:
        marker = Path(tmp) / "smoke.txt"
        env["DROP_DLP_SMOKE_MARKER"] = str(marker)
        print("Smoke-testing", exe)
        result = subprocess.run(
            [str(exe), "--smoke-test"],
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout or "") + "\n" + (result.stderr or "")
        if result.returncode != 0:
            raise SystemExit(
                f"smoke-test failed with code {result.returncode}\n{output}"
            )
        if marker.is_file():
            print("Smoke marker:", marker.read_text(encoding="utf-8").strip())
            return
        if "smoke-test ok" in output:
            print(output.strip())
            return
        raise SystemExit(
            "smoke-test exited 0 but did not write a marker or print smoke-test ok\n"
            f"{output}"
        )


def smoke_test_archive(archive: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="dropdlp-smoke-archive-") as tmp:
        extracted = extract_archive(archive, Path(tmp) / "out")
        exe = verify_extracted_bundle(extracted)
        same_platform = True
        if exe.suffix.lower() == ".exe" and not sys.platform.startswith("win"):
            same_platform = False
        elif _looks_like_macho(exe) and sys.platform != "darwin":
            same_platform = False
        elif _looks_like_elf(exe) and sys.platform.startswith("win"):
            same_platform = False
        elif _looks_like_elf(exe) and sys.platform == "darwin":
            same_platform = False
        if not same_platform:
            print("Archive structure OK; skipping native smoke-test on this OS")
            return
        smoke_test(exe)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bundle",
        action="store_true",
        help="Also zip/tar the dist folder for GitHub Releases",
    )
    parser.add_argument("--name", default=None, help="Override archive file name")
    parser.add_argument(
        "--skip-smoke",
        action="store_true",
        help="Do not launch the frozen binary after packing",
    )
    parser.add_argument(
        "--smoke-archive",
        default=None,
        help="Extract and smoke-test an existing archive, then exit",
    )
    args = parser.parse_args()

    if args.smoke_archive:
        smoke_test_archive(Path(args.smoke_archive).resolve())
        return 0

    output = run_pyinstaller()
    print("Built", output)
    archive = None
    if args.bundle:
        archive = pack(output, args.name or _platform_bundle_name())
        print("Packed", archive)
        verify_archive(archive)
        print("Archive verified", archive)
        if not args.skip_smoke:
            smoke_test_archive(archive)
    elif not args.skip_smoke:
        exe = verify_extracted_bundle(output)
        smoke_test(exe)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
