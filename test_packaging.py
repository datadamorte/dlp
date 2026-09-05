import importlib.util
import os
import shutil
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

MACHO = b"\xcf\xfa\xed\xfe" + b"\x00" * 32


def load_build():
    path = Path(__file__).resolve().parent / "packaging" / "build.py"
    spec = importlib.util.spec_from_file_location("dropdlp_bundle_build", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_fake_app(root: Path, *, with_symlinks: bool) -> Path:
    app = root / "yt-dlp-gui.app"
    macos = app / "Contents" / "MacOS"
    fw = app / "Contents" / "Frameworks"
    macos.mkdir(parents=True)
    (app / "Contents" / "Info.plist").write_text(
        "<?xml version='1.0'?><plist><dict></dict></plist>\n",
        encoding="utf-8",
    )
    exe = macos / "yt-dlp-gui"
    exe.write_bytes(MACHO)
    exe.chmod(0o755)
    dotted = fw / "python3__dot__12" / "lib-dynload"
    dotted.mkdir(parents=True)
    (dotted / "math.so").write_bytes(b"so")
    versions = fw / "Python.framework" / "Versions" / "3.12"
    versions.mkdir(parents=True)
    (versions / "Python").write_bytes(MACHO)
    if with_symlinks:
        os.symlink("python3__dot__12", fw / "python3.12")
        os.symlink("3.12", fw / "Python.framework" / "Versions" / "Current")
    else:
        (fw / "python3.12").mkdir()
        (fw / "Python.framework" / "Versions" / "Current").mkdir()
    return app


class ArchivePackingTests(unittest.TestCase):
    def test_zip_roundtrip_keeps_framework_symlinks(self):
        build = load_build()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            app = make_fake_app(tmp_path / "src", with_symlinks=True)
            archive = tmp_path / "app.zip"
            build.create_zip_preserving_links(app, archive)
            with zipfile.ZipFile(archive) as zf:
                links = {info.filename.rstrip("/") for info in zf.infolist() if build.is_zip_symlink(info)}
            self.assertTrue(any(name.endswith("python3.12") for name in links))
            self.assertTrue(any(name.endswith("Versions/Current") for name in links))

            extracted = tmp_path / "out"
            build.extract_zip_preserving_links(archive, extracted)
            restored = extracted / "yt-dlp-gui.app"
            self.assertTrue((restored / "Contents" / "Frameworks" / "python3.12").is_symlink())
            self.assertTrue(
                (restored / "Contents" / "Frameworks" / "Python.framework" / "Versions" / "Current").is_symlink()
            )
            exe = build.verify_extracted_bundle(restored)
            self.assertEqual(exe.name, "yt-dlp-gui")
            self.assertTrue(os.access(exe, os.X_OK))

    def test_missing_symlinks_fail_verification(self):
        build = load_build()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            app = make_fake_app(tmp_path / "src", with_symlinks=False)
            with self.assertRaises(SystemExit):
                build.verify_extracted_bundle(app)

    def test_shutil_make_archive_zip_breaks_app_symlinks(self):
        """This is the v1.2.0 macOS release bug: Python's zip drops Unix links."""
        build = load_build()
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            app = make_fake_app(tmp_path / "src", with_symlinks=True)
            archive_base = tmp_path / "broken"
            shutil.make_archive(str(archive_base), "zip", root_dir=app.parent, base_dir=app.name)
            archive = tmp_path / "broken.zip"
            with zipfile.ZipFile(archive) as zf:
                link_count = sum(1 for info in zf.infolist() if stat.S_ISLNK((info.external_attr >> 16) & 0xFFFF))
            self.assertEqual(link_count, 0)
            with self.assertRaises(SystemExit):
                build.verify_archive(archive)


class InstallPathTests(unittest.TestCase):
    def test_macos_install_dir_is_not_inside_app_bundle(self):
        from ytdlp_core import portable_root, ytdlp_install_dir

        with tempfile.TemporaryDirectory() as tmp:
            macos = Path(tmp) / "yt-dlp-gui.app" / "Contents" / "MacOS"
            macos.mkdir(parents=True)
            exe = macos / "yt-dlp-gui"
            exe.write_text("x", encoding="utf-8")
            from unittest.mock import patch

            with patch("ytdlp_core.is_frozen", return_value=True), patch.object(sys, "executable", str(exe)):
                self.assertEqual(portable_root(), tmp)
            install = ytdlp_install_dir(system="Darwin", home=tmp)
            self.assertEqual(
                install,
                os.path.join(tmp, "Library", "Application Support", "dropdlp"),
            )
            self.assertNotIn(".app", install)

    def test_resolve_checks_extra_dirs(self):
        from ytdlp_core import resolve_ytdlp_path

        with tempfile.TemporaryDirectory() as install, tempfile.TemporaryDirectory() as extra:
            local = os.path.join(extra, "yt-dlp")
            with open(local, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\n")
            found = resolve_ytdlp_path(
                install,
                extra_dirs=[extra],
                which=lambda _name: None,
                system="Linux",
                is_runnable=lambda _path: True,
            )
            self.assertEqual(found, local)


if __name__ == "__main__":
    unittest.main()
