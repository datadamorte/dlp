import os
import platform
import subprocess
import sys

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings, QUrl
from PyQt5.QtGui import QKeySequence, QDesktopServices
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QProgressBar,
    QFileDialog,
    QGridLayout,
    QSpinBox,
    QShortcut,
)

from ytdlp_core import (
    build_ytdlp_command,
    download_file,
    ffmpeg_available,
    first_url_in_text,
    is_valid_url,
    make_executable,
    parse_progress_line,
    popen_kwargs,
    resolve_ytdlp_path,
    terminate_process,
    ytdlp_exe_name,
    ytdlp_release_url,
)

APP_VERSION = "1.1.0"


class DownloadThread(QThread):
    progress = pyqtSignal(str)
    progress_percent = pyqtSignal(int)
    progress_status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, exe_path, url, options, output_path):
        super().__init__()
        self.exe_path = exe_path
        self.url = url
        self.options = options
        self.output_path = output_path
        self.process = None
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        terminate_process(self.process)

    def run(self):
        try:
            cmd = build_ytdlp_command(self.exe_path, self.url, self.options, self.output_path)
            self.process = subprocess.Popen(cmd, **popen_kwargs())

            for line in self.process.stdout:
                if self._is_cancelled:
                    break
                line = line.strip()
                if not line:
                    continue
                self.progress.emit(line)
                info = parse_progress_line(line)
                if not info:
                    continue
                if info.percent is not None:
                    self.progress_percent.emit(info.percent)
                parts = []
                if info.percent is not None:
                    parts.append(f"{info.percent}%")
                if info.speed:
                    parts.append(info.speed)
                if info.eta:
                    parts.append(f"ETA {info.eta}")
                if info.postprocessing:
                    parts.append("Processing…")
                if info.destination:
                    parts.append(os.path.basename(info.destination))
                if parts:
                    self.progress_status.emit("  •  ".join(parts))

            try:
                self.process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                terminate_process(self.process)
                self.error.emit("Download did not exit cleanly")
                return

            if self._is_cancelled:
                self.error.emit("Download cancelled by user")
            elif self.process.returncode == 0:
                self.finished.emit("Download completed successfully!")
            else:
                self.error.emit(f"Download failed with return code: {self.process.returncode}")
        except Exception as e:
            self.error.emit(f"Error: {e}")


class UpdateThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, exe_path):
        super().__init__()
        self.exe_path = exe_path
        self.process = None
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        terminate_process(self.process)

    def run(self):
        try:
            cmd = [self.exe_path, "-U"]
            self.process = subprocess.Popen(cmd, **popen_kwargs())
            output_lines = []
            for line in self.process.stdout:
                if self._is_cancelled:
                    terminate_process(self.process)
                    self.error.emit("Update cancelled")
                    return
                stripped = line.strip()
                output_lines.append(stripped)
                self.progress.emit(stripped)
            self.process.wait(timeout=30)

            if self._is_cancelled:
                self.error.emit("Update cancelled")
                return

            if self.process.returncode == 0:
                self.finished.emit("yt-dlp update completed.")
                return

            output_text = "\n".join(output_lines)
            if self.process.returncode == 100 or "installed yt-dlp with pip" in output_text:
                self.progress.emit("Detected pip installation, updating via pip...")
                self._update_via_pip()
            else:
                self.error.emit(f"Update failed with return code: {self.process.returncode}")
        except Exception as e:
            self.error.emit(f"Error: {e}")

    def _update_via_pip(self):
        try:
            cmd = [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"]
            self.process = subprocess.Popen(cmd, **popen_kwargs())
            for line in self.process.stdout:
                if self._is_cancelled:
                    terminate_process(self.process)
                    self.error.emit("Update cancelled")
                    return
                self.progress.emit(line.strip())
            self.process.wait(timeout=30)
            if self.process.returncode == 0:
                self.finished.emit("yt-dlp updated via pip.")
            else:
                self.error.emit(f"pip update failed with return code: {self.process.returncode}")
        except Exception as e:
            self.error.emit(f"pip update error: {e}")


class InstallThread(QThread):
    progress_percent = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, dest_path, system_name):
        super().__init__()
        self.dest_path = dest_path
        self.system_name = system_name

    def run(self):
        tmp_path = self.dest_path + ".download"
        try:
            url = ytdlp_release_url(self.system_name)
            download_file(url, tmp_path, progress_cb=self.progress_percent.emit)
            make_executable(tmp_path, self.system_name)
            os.replace(tmp_path, self.dest_path)
            self.finished.emit(self.dest_path)
        except Exception as e:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            self.error.emit(str(e))


class ModernYTDLPGUI(QMainWindow):
    def __init__(self, skip_startup=False, settings=None):
        super().__init__()
        self.download_thread = None
        self.update_thread = None
        self.install_thread = None
        self._auto_updating = False
        self.settings = settings or QSettings("YTDLPGui", "ModernYTDLP")
        self.last_clipboard = ""
        self._warned_ffmpeg = False

        self.init_ui()
        self.apply_modern_style()
        self.load_settings()
        self.setup_shortcuts()
        self.sync_dependent_controls()

        self.check_clipboard_timer = QTimer(self)
        self.check_clipboard_timer.timeout.connect(self.check_clipboard)

        if not skip_startup:
            self.check_clipboard_timer.start(1000)
            QTimer.singleShot(100, self.check_and_install_ytdlp)
            QTimer.singleShot(200, self.warn_if_ffmpeg_missing)

    def _app_dir(self):
        return os.path.dirname(os.path.abspath(__file__))

    def _ytdlp_exe_name(self):
        return ytdlp_exe_name()

    def resolve_ytdlp_path(self):
        return resolve_ytdlp_path(self._app_dir(), os.getcwd())

    def warn_if_ffmpeg_missing(self):
        if self._warned_ffmpeg or ffmpeg_available():
            return
        self._warned_ffmpeg = True
        self.log_output.append(
            "⚠️ ffmpeg was not found on PATH. Some formats need it to merge video and audio. "
            "Install ffmpeg for the best results."
        )

    def check_and_install_ytdlp(self):
        exe_name = self._ytdlp_exe_name()
        exe_path = self.resolve_ytdlp_path()
        if exe_path:
            self.start_update(auto=True)
            return

        local_path = os.path.join(self._app_dir(), exe_name)
        self.log_output.append(f"⚠️ {exe_name} not found. Downloading automatically...")
        self.download_btn.setEnabled(False)
        self.update_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Downloading yt-dlp: %p%")

        self.install_thread = InstallThread(local_path, platform.system())
        self.install_thread.progress_percent.connect(self._install_progress)
        self.install_thread.finished.connect(self._install_finished)
        self.install_thread.error.connect(self._install_error)
        self.install_thread.start()

    def _install_progress(self, percent):
        self.progress_bar.setValue(percent)
        self.progress_bar.setFormat(f"Downloading yt-dlp: {percent}%")

    def _install_finished(self, path):
        self.log_output.append(f"✅ {os.path.basename(path)} downloaded and installed successfully!")
        self.progress_bar.setVisible(False)
        self.download_btn.setEnabled(True)
        self.update_btn.setEnabled(True)
        self.start_update(auto=True)

    def _install_error(self, message):
        self.log_output.append(f"❌ Failed to download yt-dlp: {message}")
        self.log_output.append("Please download it manually from https://github.com/yt-dlp/yt-dlp/releases")
        self.progress_bar.setVisible(False)
        self.download_btn.setEnabled(True)
        self.update_btn.setEnabled(True)

    def init_ui(self):
        self.setWindowTitle("yt-dlp Downloader")
        self.setGeometry(100, 100, 1000, 800)
        self.setMinimumSize(800, 650)
        self.setAcceptDrops(True)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)

        header_layout = QVBoxLayout()
        title_label = QLabel("yt-dlp GUI")
        title_label.setObjectName("title_label")
        title_label.setAlignment(Qt.AlignCenter)

        subtitle_label = QLabel("Advanced Video Downloader")
        subtitle_label.setObjectName("subtitle_label")
        subtitle_label.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        main_layout.addLayout(header_layout)

        url_group = QGroupBox("Target URL")
        url_layout = QVBoxLayout(url_group)
        url_layout.setContentsMargins(15, 25, 15, 15)

        input_container = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste or drop a video URL (YouTube, Twitch, Twitter, …)")
        self.url_input.setMinimumHeight(45)
        self.url_input.setClearButtonEnabled(True)
        self.url_input.setToolTip("Video or playlist URL. Drag-and-drop also works.")

        paste_btn = QPushButton("Paste")
        paste_btn.setObjectName("secondary_btn")
        paste_btn.setFixedWidth(80)
        paste_btn.setMinimumHeight(45)
        paste_btn.setToolTip("Paste clipboard text into the URL field")
        paste_btn.clicked.connect(self.paste_from_clipboard)

        input_container.addWidget(self.url_input)
        input_container.addWidget(paste_btn)
        url_layout.addLayout(input_container)
        main_layout.addWidget(url_group)

        options_group = QGroupBox("Configuration")
        options_layout = QGridLayout(options_group)
        options_layout.setContentsMargins(15, 25, 15, 15)
        options_layout.setHorizontalSpacing(20)
        options_layout.setVerticalSpacing(15)

        options_layout.addWidget(QLabel("Quality Profile:"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["Best Quality", "1080p", "720p", "480p", "360p", "Audio Only"])
        self.format_combo.setToolTip("Cap video height, or extract audio only")
        self.format_combo.currentTextChanged.connect(self.sync_dependent_controls)
        options_layout.addWidget(self.format_combo, 0, 1)

        options_layout.addWidget(QLabel("Container:"), 0, 2)
        self.video_format_combo = QComboBox()
        self.video_format_combo.addItems(["Auto (Best)", "MP4", "MKV", "WEBM"])
        self.video_format_combo.setToolTip(
            "Remux into this container without re-encoding. Re-encode only if you turn that option on."
        )
        self.video_format_combo.currentTextChanged.connect(self.sync_dependent_controls)
        options_layout.addWidget(self.video_format_combo, 0, 3)

        options_layout.addWidget(QLabel("Audio Format:"), 0, 4)
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(["mp3", "m4a", "wav", "flac"])
        self.audio_format_combo.setToolTip("Used when extracting audio or when quality is Audio Only")
        options_layout.addWidget(self.audio_format_combo, 0, 5)

        options_layout.addWidget(QLabel("Speed Limit:"), 1, 0)
        self.speed_limit_spin = QSpinBox()
        self.speed_limit_spin.setRange(0, 100000)
        self.speed_limit_spin.setSpecialValueText("Unlimited")
        self.speed_limit_spin.setSuffix(" KB/s")
        self.speed_limit_spin.setToolTip("0 means unlimited")
        options_layout.addWidget(self.speed_limit_spin, 1, 1)

        options_layout.addWidget(QLabel("Use Cookies:"), 1, 2)
        self.cookies_combo = QComboBox()
        self.cookies_combo.addItems(["None", "Chrome", "Firefox", "Safari", "Edge", "Brave", "Opera"])
        self.cookies_combo.setToolTip("Use browser cookies to bypass 403 errors and age-gates")
        options_layout.addWidget(self.cookies_combo, 1, 3)

        self.recode_cb = QCheckBox("Re-encode container")
        self.recode_cb.setToolTip("Slower. Only needed if remuxing into the chosen container fails.")
        options_layout.addWidget(self.recode_cb, 1, 4, 1, 2)

        checkbox_layout = QGridLayout()
        self.extract_audio_cb = QCheckBox("Extract Audio")
        self.subtitle_cb = QCheckBox("Download Subtitles")
        self.auto_sub_cb = QCheckBox("Auto-Subs")
        self.thumbnail_cb = QCheckBox("Thumbnail")
        self.description_cb = QCheckBox("Description")
        self.playlist_cb = QCheckBox("Process Playlist")
        self.extract_audio_cb.setToolTip("Download audio only in the selected audio format")
        self.playlist_cb.setToolTip("Download every video in a playlist instead of a single item")
        self.auto_sub_cb.setToolTip("Include auto-generated captions even if official subs are missing")
        self.extract_audio_cb.toggled.connect(self.sync_dependent_controls)
        self.playlist_cb.toggled.connect(self.sync_dependent_controls)

        checkbox_layout.addWidget(self.extract_audio_cb, 0, 0)
        checkbox_layout.addWidget(self.subtitle_cb, 0, 1)
        checkbox_layout.addWidget(self.auto_sub_cb, 0, 2)
        checkbox_layout.addWidget(self.thumbnail_cb, 1, 0)
        checkbox_layout.addWidget(self.description_cb, 1, 1)
        checkbox_layout.addWidget(self.playlist_cb, 1, 2)

        playlist_range = QHBoxLayout()
        playlist_range.addWidget(QLabel("Playlist from:"))
        self.playlist_start_spin = QSpinBox()
        self.playlist_start_spin.setRange(0, 9999)
        self.playlist_start_spin.setSpecialValueText("Start")
        self.playlist_start_spin.setToolTip("1-based start index. Start means the first item.")
        playlist_range.addWidget(self.playlist_start_spin)
        playlist_range.addWidget(QLabel("to:"))
        self.playlist_end_spin = QSpinBox()
        self.playlist_end_spin.setRange(0, 9999)
        self.playlist_end_spin.setSpecialValueText("End")
        self.playlist_end_spin.setToolTip("1-based end index. End means the last item.")
        playlist_range.addWidget(self.playlist_end_spin)
        playlist_range.addStretch()
        checkbox_layout.addLayout(playlist_range, 2, 0, 1, 3)

        options_layout.addLayout(checkbox_layout, 2, 0, 1, 6)
        main_layout.addWidget(options_group)

        output_group = QGroupBox("Save Location")
        output_layout = QHBoxLayout(output_group)
        output_layout.setContentsMargins(15, 25, 15, 15)

        self.output_path = QLineEdit()
        self.output_path.setText(os.getcwd())
        self.output_path.setReadOnly(True)
        self.output_path.setToolTip("Folder where files are saved")

        browse_btn = QPushButton("Browse...")
        browse_btn.setObjectName("secondary_btn")
        browse_btn.clicked.connect(self.browse_output_dir)

        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.setObjectName("secondary_btn")
        self.open_folder_btn.setToolTip("Open the save location in your file manager")
        self.open_folder_btn.clicked.connect(self.open_output_dir)

        output_layout.addWidget(self.output_path)
        output_layout.addWidget(browse_btn)
        output_layout.addWidget(self.open_folder_btn)
        main_layout.addWidget(output_group)

        action_layout = QHBoxLayout()
        action_layout.setSpacing(15)

        self.download_btn = QPushButton("START DOWNLOAD")
        self.download_btn.setObjectName("download_btn")
        self.download_btn.setMinimumHeight(55)
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setDefault(True)
        self.download_btn.clicked.connect(self.start_download)

        self.cancel_btn = QPushButton("CANCEL")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setMinimumHeight(55)
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setVisible(False)

        self.update_btn = QPushButton("Update yt-dlp")
        self.update_btn.setObjectName("secondary_btn")
        self.update_btn.clicked.connect(self.start_update)

        self.clear_btn = QPushButton("Clear Log")
        self.clear_btn.setObjectName("secondary_btn")
        self.clear_btn.clicked.connect(self.clear_log)

        action_layout.addWidget(self.download_btn, 2)
        action_layout.addWidget(self.cancel_btn, 2)
        action_layout.addWidget(self.update_btn, 1)
        action_layout.addWidget(self.clear_btn, 1)
        main_layout.addLayout(action_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.progress_bar)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Download logs will appear here...")
        self.log_output.setToolTip("yt-dlp output")
        main_layout.addWidget(self.log_output)

    def apply_modern_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e2e;
            }

            QWidget {
                color: #cdd6f4;
                font-family: 'Segoe UI', 'Roboto', sans-serif;
                font-size: 13px;
            }

            QLabel#title_label {
                font-size: 28px;
                font-weight: bold;
                color: #89b4fa;
                margin-bottom: 5px;
            }

            QLabel#subtitle_label {
                font-size: 14px;
                color: #a6adc8;
                margin-bottom: 15px;
            }

            QGroupBox {
                background-color: #252535;
                border: 1px solid #313244;
                border-radius: 10px;
                margin-top: 12px;
                font-weight: bold;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #89b4fa;
                background-color: #252535;
            }

            QLineEdit {
                background-color: #181825;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 8px 12px;
                color: #cdd6f4;
                selection-background-color: #45475a;
            }

            QLineEdit:focus {
                border: 1px solid #89b4fa;
                background-color: #1e1e2e;
            }

            QComboBox {
                background-color: #181825;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px 10px;
                min-width: 100px;
            }

            QComboBox:on, QComboBox:focus {
                border: 1px solid #89b4fa;
            }

            QComboBox:disabled, QSpinBox:disabled {
                color: #6c7086;
            }

            QComboBox::drop-down {
                border: none;
                width: 20px;
            }

            QComboBox QAbstractItemView {
                background-color: #181825;
                border: 1px solid #45475a;
                selection-background-color: #313244;
                color: #cdd6f4;
            }

            QSpinBox {
                background-color: #181825;
                border: 1px solid #45475a;
                border-radius: 6px;
                padding: 6px;
            }

            QSpinBox:focus {
                border: 1px solid #89b4fa;
            }

            QCheckBox {
                spacing: 8px;
            }

            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #45475a;
                border-radius: 4px;
                background-color: #181825;
            }

            QCheckBox::indicator:checked {
                background-color: #89b4fa;
                border-color: #89b4fa;
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjMWUxZTJlIiBzdHJva2Utd2lkdGg9IjMiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
            }

            QPushButton {
                background-color: #313244;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
                color: #cdd6f4;
            }

            QPushButton:hover {
                background-color: #45475a;
            }

            QPushButton:pressed {
                background-color: #585b70;
            }

            QPushButton:disabled {
                background-color: #313244;
                color: #6c7086;
            }

            QPushButton#download_btn {
                background-color: #89b4fa;
                color: #1e1e2e;
                font-size: 16px;
                font-weight: 800;
                border-radius: 8px;
            }

            QPushButton#download_btn:hover {
                background-color: #b4befe;
            }

            QPushButton#download_btn:disabled {
                background-color: #45475a;
                color: #a6adc8;
            }

            QPushButton#cancel_btn {
                background-color: #f38ba8;
                color: #1e1e2e;
                font-size: 16px;
                font-weight: 800;
                border-radius: 8px;
            }

            QPushButton#cancel_btn:hover {
                background-color: #eba0ac;
            }

            QPushButton#secondary_btn {
                background-color: #313244;
                border: 1px solid #45475a;
            }

            QPushButton#secondary_btn:hover {
                background-color: #45475a;
                border-color: #585b70;
            }

            QProgressBar {
                border: none;
                background-color: #313244;
                border-radius: 6px;
                text-align: center;
                color: #cdd6f4;
            }

            QProgressBar::chunk {
                background-color: #a6e3a1;
                border-radius: 6px;
            }

            QTextEdit {
                background-color: #11111b;
                border: 1px solid #313244;
                border-radius: 8px;
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 12px;
                padding: 10px;
                color: #a6adc8;
            }

            QScrollBar:vertical {
                border: none;
                background: #1e1e2e;
                width: 10px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background: #45475a;
                min-height: 20px;
                border-radius: 5px;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

    def setup_shortcuts(self):
        download_shortcut = QShortcut(QKeySequence("Return"), self.url_input)
        download_shortcut.activated.connect(self.start_download)

        clear_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_shortcut.activated.connect(self.clear_log)

        cancel_shortcut = QShortcut(QKeySequence("Escape"), self)
        cancel_shortcut.activated.connect(self.cancel_download)

        open_folder_shortcut = QShortcut(QKeySequence("Ctrl+O"), self)
        open_folder_shortcut.activated.connect(self.open_output_dir)

    def sync_dependent_controls(self, *_args):
        audio_mode = self.extract_audio_cb.isChecked() or self.format_combo.currentText() == "Audio Only"
        self.video_format_combo.setEnabled(not audio_mode)
        container_chosen = (not audio_mode) and self.video_format_combo.currentText() != "Auto (Best)"
        self.recode_cb.setEnabled(container_chosen)
        self.audio_format_combo.setEnabled(audio_mode)
        playlist_on = self.playlist_cb.isChecked()
        self.playlist_start_spin.setEnabled(playlist_on)
        self.playlist_end_spin.setEnabled(playlist_on)

    def collect_options(self):
        quality = self.format_combo.currentText()
        extract_audio = self.extract_audio_cb.isChecked() or quality == "Audio Only"
        start = self.playlist_start_spin.value()
        end = self.playlist_end_spin.value()
        return {
            "quality": quality,
            "extract_audio": extract_audio,
            "video_format": self.video_format_combo.currentText(),
            "audio_format": self.audio_format_combo.currentText(),
            "subtitle": self.subtitle_cb.isChecked(),
            "auto_sub": self.auto_sub_cb.isChecked(),
            "thumbnail": self.thumbnail_cb.isChecked(),
            "description": self.description_cb.isChecked(),
            "playlist": self.playlist_cb.isChecked(),
            "playlist_start": start,
            "playlist_end": end,
            "speed_limit": self.speed_limit_spin.value(),
            "cookies_browser": self.cookies_combo.currentText(),
            "recode": self.recode_cb.isChecked(),
        }

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = (clipboard.text() or "").strip()
        if not text:
            return
        url = first_url_in_text(text)
        self.url_input.setText(url or text)
        self.url_input.setFocus()

    def check_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text() or ""
        if text == self.last_clipboard:
            return
        self.last_clipboard = text
        if self.url_input.text().strip():
            return
        url = first_url_in_text(text)
        if url:
            self.url_input.setText(url)

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls() or mime.hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        mime = event.mimeData()
        candidates = []
        if mime.hasUrls():
            candidates.extend(url.toString() for url in mime.urls())
        if mime.hasText():
            candidates.append(mime.text())
        for item in candidates:
            url = first_url_in_text(item)
            if url:
                self.url_input.setText(url)
                event.acceptProposedAction()
                return
        event.ignore()

    def load_settings(self):
        last_dir = self.settings.value("output_dir", os.getcwd())
        self.output_path.setText(last_dir)
        self.format_combo.setCurrentIndex(self.settings.value("format_index", 0, type=int))
        self.video_format_combo.setCurrentIndex(self.settings.value("video_format_index", 0, type=int))
        self.audio_format_combo.setCurrentIndex(self.settings.value("audio_format_index", 0, type=int))
        self.extract_audio_cb.setChecked(self.settings.value("extract_audio", False, type=bool))
        self.subtitle_cb.setChecked(self.settings.value("subtitle", False, type=bool))
        self.auto_sub_cb.setChecked(self.settings.value("auto_sub", False, type=bool))
        self.thumbnail_cb.setChecked(self.settings.value("thumbnail", False, type=bool))
        self.description_cb.setChecked(self.settings.value("description", False, type=bool))
        self.playlist_cb.setChecked(self.settings.value("playlist", False, type=bool))
        self.playlist_start_spin.setValue(self.settings.value("playlist_start", 0, type=int))
        self.playlist_end_spin.setValue(self.settings.value("playlist_end", 0, type=int))
        self.speed_limit_spin.setValue(self.settings.value("speed_limit", 0, type=int))
        self.cookies_combo.setCurrentIndex(self.settings.value("cookies_index", 0, type=int))
        self.recode_cb.setChecked(self.settings.value("recode", False, type=bool))

    def save_settings(self):
        self.settings.setValue("output_dir", self.output_path.text())
        self.settings.setValue("format_index", self.format_combo.currentIndex())
        self.settings.setValue("video_format_index", self.video_format_combo.currentIndex())
        self.settings.setValue("audio_format_index", self.audio_format_combo.currentIndex())
        self.settings.setValue("extract_audio", self.extract_audio_cb.isChecked())
        self.settings.setValue("subtitle", self.subtitle_cb.isChecked())
        self.settings.setValue("auto_sub", self.auto_sub_cb.isChecked())
        self.settings.setValue("thumbnail", self.thumbnail_cb.isChecked())
        self.settings.setValue("description", self.description_cb.isChecked())
        self.settings.setValue("playlist", self.playlist_cb.isChecked())
        self.settings.setValue("playlist_start", self.playlist_start_spin.value())
        self.settings.setValue("playlist_end", self.playlist_end_spin.value())
        self.settings.setValue("speed_limit", self.speed_limit_spin.value())
        self.settings.setValue("cookies_index", self.cookies_combo.currentIndex())
        self.settings.setValue("recode", self.recode_cb.isChecked())

    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.output_path.text())
        if directory:
            self.output_path.setText(directory)
            self.settings.setValue("output_dir", directory)

    def open_output_dir(self):
        directory = self.output_path.text().strip() or os.getcwd()
        if not os.path.isdir(directory):
            self.log_output.append(f"❌ Folder does not exist: {directory}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(directory)))

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            self.log_output.append("❌ Please enter a URL")
            self.url_input.setFocus()
            return

        if not is_valid_url(url):
            self.log_output.append("❌ Invalid URL. Please enter a valid http:// or https:// URL")
            self.url_input.setFocus()
            self.url_input.selectAll()
            return

        if self.download_thread and self.download_thread.isRunning():
            self.log_output.append("❌ Download already in progress")
            return

        if self.update_thread and self.update_thread.isRunning():
            self.log_output.append("❌ Please wait for yt-dlp update to finish before starting a download")
            return

        if self.install_thread and self.install_thread.isRunning():
            self.log_output.append("❌ Please wait for yt-dlp to finish installing")
            return

        options = self.collect_options()
        if options["playlist"] and options["playlist_end"] and options["playlist_start"]:
            if options["playlist_end"] < options["playlist_start"]:
                self.log_output.append("❌ Playlist end must be greater than or equal to start")
                return

        exe_path = self.resolve_ytdlp_path()
        if not exe_path:
            self.log_output.append(
                f"❌ {self._ytdlp_exe_name()} not found. "
                "Please install it or place it in the app directory."
            )
            return

        output_dir = self.output_path.text().strip() or os.getcwd()
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                self.log_output.append(f"❌ Cannot create output folder: {e}")
                return

        self.save_settings()

        self.log_output.append(f"🚀 Starting download from: {url}")
        self.log_output.append(f"📁 Output directory: {output_dir}")
        self.log_output.append(f"🛠 Using yt-dlp: {exe_path}")

        self.download_thread = DownloadThread(exe_path, url, options, output_dir)
        self.download_thread.progress.connect(self.update_log)
        self.download_thread.progress_percent.connect(self.update_progress)
        self.download_thread.progress_status.connect(self.update_progress_status)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.error.connect(self.download_error)

        self.download_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Starting…")
        self.setWindowTitle("yt-dlp Downloader — downloading")

        self.download_thread.start()

    def cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.log_output.append("🛑 Cancelling download...")
            self.download_thread.cancel()
            self.cancel_btn.setEnabled(False)

    def update_progress(self, percent):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(percent)

    def update_progress_status(self, status):
        self.progress_bar.setFormat(status)
        self.setWindowTitle(f"yt-dlp Downloader — {status}")

    def update_log(self, message):
        if message:
            self.log_output.append(message)
            self.log_output.verticalScrollBar().setValue(
                self.log_output.verticalScrollBar().maximum()
            )

    def download_finished(self, message):
        self.log_output.append(f"✅ {message}")
        self.reset_download_ui()

    def download_error(self, message):
        self.log_output.append(f"❌ {message}")
        self.reset_download_ui()

    def reset_download_ui(self):
        self.download_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.setWindowTitle("yt-dlp Downloader")

    def start_update(self, auto=False):
        if self.download_thread and self.download_thread.isRunning():
            if not auto:
                self.log_output.append("❌ Please wait for the current download to finish before updating yt-dlp")
            return
        if self.update_thread and self.update_thread.isRunning():
            if not auto:
                self.log_output.append("❌ Update already in progress")
            return

        exe_path = self.resolve_ytdlp_path()
        if not exe_path:
            if not auto:
                self.log_output.append(
                    f"❌ {self._ytdlp_exe_name()} not found. "
                    "Please install it or place it in the app directory."
                )
            return

        self._auto_updating = auto
        if auto:
            self.log_output.append("🔄 Checking for yt-dlp updates on startup...")
        else:
            self.log_output.append("🔄 Checking for yt-dlp updates...")

        self.update_thread = UpdateThread(exe_path)
        self.update_thread.progress.connect(self.update_log)
        self.update_thread.finished.connect(self.update_finished)
        self.update_thread.error.connect(self.update_error)

        self.update_btn.setText("Updating...")
        self.update_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.update_thread.start()

    def update_finished(self, message):
        prefix = "Startup update: " if self._auto_updating else ""
        self.log_output.append(f"✅ {prefix}{message}")
        self._auto_updating = False
        self.update_btn.setText("Update yt-dlp")
        self.update_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def update_error(self, message):
        if self._auto_updating:
            self.log_output.append(f"⚠️ Startup update skipped: {message}")
            self.log_output.append('You can still download videos, or click "Update yt-dlp" later.')
        else:
            self.log_output.append(f"❌ {message}")
        self._auto_updating = False
        self.update_btn.setText("Update yt-dlp")
        self.update_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def clear_log(self):
        self.log_output.clear()

    def closeEvent(self, event):
        self.save_settings()
        for thread in (self.download_thread, self.update_thread, self.install_thread):
            if thread and thread.isRunning():
                if hasattr(thread, "cancel"):
                    thread.cancel()
                thread.wait(4000)
        event.accept()


def main():
    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("yt-dlp GUI")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("YTDLPGui")

    window = ModernYTDLPGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
