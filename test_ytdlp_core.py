import os
import tempfile
import unittest

from ytdlp_core import (
    PLAYLIST_TEMPLATE,
    build_format_selector,
    build_ytdlp_command,
    ffmpeg_available,
    first_url_in_text,
    is_valid_url,
    parse_progress_line,
    popen_kwargs,
    resolve_ytdlp_path,
    ytdlp_exe_name,
    ytdlp_release_url,
)


class UrlValidationTests(unittest.TestCase):
    def test_accepts_http_and_https(self):
        self.assertTrue(is_valid_url("https://youtu.be/dQw4w9WgXcQ"))
        self.assertTrue(is_valid_url("http://example.com/watch?v=1"))
        self.assertTrue(is_valid_url("  https://example.com/a  "))

    def test_rejects_invalid(self):
        self.assertFalse(is_valid_url(""))
        self.assertFalse(is_valid_url("not a url"))
        self.assertFalse(is_valid_url("ftp://example.com/file"))
        self.assertFalse(is_valid_url("javascript:alert(1)"))
        self.assertFalse(is_valid_url(None))  # type: ignore[arg-type]

    def test_first_url_in_text(self):
        self.assertEqual(
            first_url_in_text("see https://youtu.be/abc extra"),
            "https://youtu.be/abc",
        )
        self.assertEqual(first_url_in_text("<https://example.com/x>"), "https://example.com/x")
        self.assertIsNone(first_url_in_text("no links here"))


class FormatSelectorTests(unittest.TestCase):
    def test_audio_only(self):
        self.assertEqual(build_format_selector("Best Quality", True), "bestaudio/best")
        self.assertEqual(build_format_selector("Audio Only", False), "bestaudio/best")

    def test_height_caps_have_fallback(self):
        spec = build_format_selector("1080p", False)
        self.assertIn("height<=1080", spec)
        self.assertTrue(spec.endswith("/best"))

    def test_best_quality_lets_ytdlp_choose(self):
        self.assertIsNone(build_format_selector("Best Quality", False))


class CommandBuilderTests(unittest.TestCase):
    def test_basic_video_command(self):
        cmd = build_ytdlp_command(
            "/usr/bin/yt-dlp",
            "https://example.com/v",
            {"quality": "Best Quality"},
            "/tmp/out",
            system="Linux",
        )
        self.assertEqual(cmd[0], "/usr/bin/yt-dlp")
        self.assertIn("--no-playlist", cmd)
        self.assertIn("--no-update", cmd)
        self.assertNotIn("-f", cmd)
        self.assertNotIn("--recode-video", cmd)
        joined = " ".join(cmd)
        self.assertIn("%(title)s [%(id)s].%(ext)s", joined)
        self.assertEqual(cmd[-1], "https://example.com/v")

    def test_container_remuxes_without_recode_by_default(self):
        cmd = build_ytdlp_command(
            "yt-dlp",
            "https://example.com/v",
            {"quality": "720p", "video_format": "MP4"},
            "/tmp/out",
            system="Linux",
        )
        self.assertIn("--merge-output-format", cmd)
        self.assertIn("mp4", cmd)
        self.assertNotIn("--recode-video", cmd)
        self.assertIn("bestvideo[height<=720]+bestaudio/best[height<=720]/best", cmd)

    def test_recode_opt_in(self):
        cmd = build_ytdlp_command(
            "yt-dlp",
            "https://example.com/v",
            {"quality": "Best Quality", "video_format": "MKV", "recode": True},
            None,
            system="Linux",
        )
        self.assertIn("--recode-video", cmd)
        self.assertIn("mkv", cmd)

    def test_extract_audio(self):
        cmd = build_ytdlp_command(
            "yt-dlp",
            "https://example.com/v",
            {"extract_audio": True, "audio_format": "flac", "video_format": "MP4"},
            "/tmp/out",
            system="Linux",
        )
        self.assertIn("-x", cmd)
        self.assertIn("flac", cmd)
        self.assertIn("bestaudio/best", cmd)
        self.assertNotIn("--merge-output-format", cmd)

    def test_playlist_range_and_folder_template(self):
        cmd = build_ytdlp_command(
            "yt-dlp",
            "https://example.com/playlist",
            {"playlist": True, "playlist_start": 2, "playlist_end": 5},
            "/data",
            system="Linux",
        )
        self.assertIn("--yes-playlist", cmd)
        self.assertIn("--ignore-errors", cmd)
        self.assertNotIn("--no-playlist", cmd)
        self.assertEqual(cmd[cmd.index("--playlist-start") + 1], "2")
        self.assertEqual(cmd[cmd.index("--playlist-end") + 1], "5")
        self.assertTrue(any(PLAYLIST_TEMPLATE in part for part in cmd))

    def test_zero_playlist_range_omitted(self):
        cmd = build_ytdlp_command(
            "yt-dlp",
            "https://example.com/playlist",
            {"playlist": True, "playlist_start": 0, "playlist_end": 0},
            None,
            system="Linux",
        )
        self.assertNotIn("--playlist-start", cmd)
        self.assertNotIn("--playlist-end", cmd)

    def test_speed_cookies_subs_windows_names(self):
        cmd = build_ytdlp_command(
            "yt-dlp.exe",
            "https://example.com/v",
            {
                "speed_limit": 512,
                "cookies_browser": "Firefox",
                "subtitle": True,
                "auto_sub": True,
                "thumbnail": True,
                "description": True,
            },
            "C:\\Videos",
            system="Windows",
        )
        self.assertIn("-r", cmd)
        self.assertIn("512K", cmd)
        self.assertIn("--cookies-from-browser", cmd)
        self.assertIn("firefox", cmd)
        self.assertIn("--write-subs", cmd)
        self.assertIn("--write-auto-subs", cmd)
        self.assertIn("--write-thumbnail", cmd)
        self.assertIn("--write-description", cmd)
        self.assertIn("--windows-filenames", cmd)

    def test_auto_subs_without_manual_subs(self):
        cmd = build_ytdlp_command(
            "yt-dlp",
            "https://example.com/v",
            {"auto_sub": True},
            None,
            system="Linux",
        )
        self.assertIn("--write-auto-subs", cmd)
        self.assertNotIn("--write-subs", cmd)


class ProgressParseTests(unittest.TestCase):
    def test_standard_download_line(self):
        info = parse_progress_line(
            "[download]  45.2% of  10.50MiB at  1.20MiB/s ETA 00:04"
        )
        self.assertIsNotNone(info)
        self.assertEqual(info.percent, 45)
        self.assertEqual(info.speed, "1.20MiB/s")
        self.assertEqual(info.eta, "00:04")

    def test_destination_and_already_downloaded(self):
        dest = parse_progress_line("[download] Destination: /tmp/Video [abc].mp4")
        self.assertEqual(dest.destination, "/tmp/Video [abc].mp4")
        done = parse_progress_line("[download] Video has already been downloaded")
        self.assertTrue(done.already_downloaded)
        self.assertEqual(done.percent, 100)

    def test_postprocessing_and_empty(self):
        merge = parse_progress_line("[Merger] Merging formats into \"out.mp4\"")
        self.assertTrue(merge.postprocessing)
        self.assertIsNone(parse_progress_line(""))
        self.assertIsNone(parse_progress_line("[info] Testing format"))


class PathResolutionTests(unittest.TestCase):
    def test_exe_name_and_release_url(self):
        self.assertEqual(ytdlp_exe_name("Windows"), "yt-dlp.exe")
        self.assertEqual(ytdlp_exe_name("Linux"), "yt-dlp")
        self.assertTrue(ytdlp_release_url("Darwin").endswith("yt-dlp_macos"))

    def test_prefers_app_dir_over_path(self):
        with tempfile.TemporaryDirectory() as app_dir, tempfile.TemporaryDirectory() as cwd:
            local = os.path.join(app_dir, "yt-dlp")
            with open(local, "w", encoding="utf-8") as handle:
                handle.write("#!/bin/sh\n")
            found = resolve_ytdlp_path(
                app_dir,
                cwd,
                which=lambda _name: "/usr/bin/yt-dlp",
                system="Linux",
            )
            self.assertEqual(found, local)

    def test_falls_back_to_which(self):
        with tempfile.TemporaryDirectory() as empty:
            found = resolve_ytdlp_path(
                empty,
                empty,
                which=lambda _name: "/usr/local/bin/yt-dlp",
                system="Linux",
            )
            self.assertEqual(found, "/usr/local/bin/yt-dlp")


class GuiSmokeTests(unittest.TestCase):
    @unittest.skipUnless(
        os.environ.get("YTDLP_GUI_SMOKE", "1") == "1",
        "GUI smoke test disabled",
    )
    def test_window_constructs_offscreen(self):
        try:
            from PyQt5.QtWidgets import QApplication
        except ImportError:
            self.skipTest("PyQt5 is not installed")

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PyQt5.QtCore import QSettings
        from yt_dlp_gui import ModernYTDLPGUI

        app = QApplication.instance() or QApplication(["yt-dlp-gui-test"])
        with tempfile.TemporaryDirectory() as tmp:
            settings = QSettings(os.path.join(tmp, "settings.ini"), QSettings.IniFormat)
            window = ModernYTDLPGUI(skip_startup=True, settings=settings)
            self.assertEqual(window.windowTitle(), "yt-dlp Downloader")
            window.url_input.setText("https://example.com/watch?v=1")
            options = window.collect_options()
            self.assertIn("quality", options)
            self.assertFalse(window.playlist_start_spin.isEnabled())
            window.playlist_cb.setChecked(True)
            self.assertTrue(window.playlist_start_spin.isEnabled())
            window.format_combo.setCurrentText("Audio Only")
            window.sync_dependent_controls()
            self.assertFalse(window.video_format_combo.isEnabled())
            cmd = build_ytdlp_command(
                "/usr/bin/yt-dlp",
                "https://example.com/watch?v=1",
                window.collect_options(),
                "/tmp/out",
                system="Linux",
            )
            self.assertIn("-x", cmd)
            self.assertIn("--yes-playlist", cmd)
            window.close()
        self.assertIsNotNone(app)


class HelperTests(unittest.TestCase):
    def test_popen_kwargs_streams_utf8(self):
        kwargs = popen_kwargs()
        self.assertTrue(kwargs["text"])
        self.assertEqual(kwargs["encoding"], "utf-8")
        self.assertEqual(kwargs["errors"], "replace")

    def test_ffmpeg_available_respects_which(self):
        self.assertTrue(ffmpeg_available(which=lambda _name: "/usr/bin/ffmpeg"))
        self.assertFalse(ffmpeg_available(which=lambda _name: None))


if __name__ == "__main__":
    unittest.main()
