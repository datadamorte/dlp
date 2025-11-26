import sys
import os
import subprocess
import threading
import json
import re
import platform
import urllib.request
import stat
from urllib.parse import urlparse
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QLabel, QLineEdit, QPushButton, QTextEdit, 
                            QCheckBox, QComboBox, QGroupBox, QProgressBar, QFileDialog,
                            QGridLayout, QSpacerItem, QSizePolicy, QFrame, QSpinBox,
                            QShortcut)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings
from PyQt5.QtGui import QFont, QPalette, QColor, QKeySequence, QIcon


class DownloadThread(QThread):
    progress = pyqtSignal(str)
    progress_percent = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url, options, output_path):
        super().__init__()
        self.url = url
        self.options = options
        self.output_path = output_path
        self.process = None
        self._is_cancelled = False

    def cancel(self):
        """Cancel the download process."""
        self._is_cancelled = True
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except:
                try:
                    self.process.kill()
                except:
                    pass

    def run(self):
        try:
            # Build yt-dlp command
            exe_name = 'yt-dlp.exe' if platform.system() == 'Windows' else 'yt-dlp'
            # Check if local exists, else assume in path
            local_exe = os.path.join(os.getcwd(), exe_name)
            if os.path.exists(local_exe):
                cmd = [local_exe]
            else:
                cmd = [exe_name]
            
            # Add progress template for better parsing
            cmd.extend(['--newline', '--no-colors'])
            
            # Add options based on selections
            if self.options.get('format'):
                cmd.extend(['-f', self.options['format']])
            
            if self.options.get('extract_audio'):
                cmd.extend(['-x', '--audio-format', self.options.get('audio_format', 'mp3')])
            else:
                # Add video format/container preference
                video_format = self.options.get('video_format')
                if video_format and video_format != 'Auto (Best)':
                    cmd.extend(['--merge-output-format', video_format.lower()])
                    # Also add --recode-video to ensure the format is correct
                    cmd.extend(['--recode-video', video_format.lower()])
            
            if self.options.get('subtitle'):
                cmd.append('--write-subs')
                if self.options.get('auto_sub'):
                    cmd.append('--write-auto-subs')
            
            if self.options.get('thumbnail'):
                cmd.append('--write-thumbnail')
            
            if self.options.get('description'):
                cmd.append('--write-description')
            
            # Playlist options
            if self.options.get('playlist'):
                if self.options.get('playlist_start'):
                    cmd.extend(['--playlist-start', str(self.options['playlist_start'])])
                if self.options.get('playlist_end'):
                    cmd.extend(['--playlist-end', str(self.options['playlist_end'])])
            else:
                cmd.append('--no-playlist')
            
            # Speed limit
            if self.options.get('speed_limit') and self.options['speed_limit'] > 0:
                cmd.extend(['-r', f"{self.options['speed_limit']}K"])
            
            # Output directory
            if self.output_path:
                cmd.extend(['-o', f'{self.output_path}/%(title)s.%(ext)s'])
            
            # Add URL
            cmd.append(self.url)
            
            # Run command
            self.process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                bufsize=1,
                universal_newlines=True
            )
            
            for line in self.process.stdout:
                if self._is_cancelled:
                    break
                    
                line = line.strip()
                if line:
                    self.progress.emit(line)
                    
                    # Parse progress percentage
                    progress_match = re.search(r'(\d+\.\d+)%', line)
                    if progress_match:
                        try:
                            percent = float(progress_match.group(1))
                            self.progress_percent.emit(int(percent))
                        except:
                            pass
            
            self.process.wait()
            
            if self._is_cancelled:
                self.error.emit("Download cancelled by user")
            elif self.process.returncode == 0:
                self.finished.emit("Download completed successfully!")
            else:
                self.error.emit(f"Download failed with return code: {self.process.returncode}")
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")

class UpdateThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, exe_path):
        super().__init__()
        self.exe_path = exe_path

    def run(self):
        try:
            # First try native yt-dlp update
            cmd = [self.exe_path, '-U']
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            output_lines = []
            for line in process.stdout:
                output_lines.append(line.strip())
                self.progress.emit(line.strip())
            process.wait()
            
            if process.returncode == 0:
                self.finished.emit("yt-dlp update completed.")
                return
            
            # Check if it's a pip installation (return code 100)
            output_text = '\n'.join(output_lines)
            if process.returncode == 100 or 'installed yt-dlp with pip' in output_text:
                self.progress.emit("Detected pip installation, updating via pip...")
                self._update_via_pip()
            else:
                self.error.emit(f"Update failed with return code: {process.returncode}")
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")

    def _update_via_pip(self):
        try:
            cmd = [sys.executable, '-m', 'pip', 'install', '-U', 'yt-dlp']
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            for line in process.stdout:
                self.progress.emit(line.strip())
            process.wait()
            if process.returncode == 0:
                self.finished.emit("yt-dlp updated via pip.")
            else:
                self.error.emit(f"pip update failed with return code: {process.returncode}")
        except Exception as e:
            self.error.emit(f"pip update error: {str(e)}")

class ModernYTDLPGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.download_thread = None
        self.update_thread = None
        self.settings = QSettings('YTDLPGui', 'ModernYTDLP')
        self.init_ui()
        self.apply_modern_style()
        self.load_settings()
        self.setup_shortcuts()
        self.check_clipboard_timer = QTimer()
        self.check_clipboard_timer.timeout.connect(self.check_clipboard)
        self.check_clipboard_timer.start(1000)  # Check every second
        self.last_clipboard = ""
        
        # Check for yt-dlp and install if missing
        QTimer.singleShot(100, self.check_and_install_ytdlp)

    def check_and_install_ytdlp(self):
        """Check if yt-dlp is present, if not download it."""
        exe_name = 'yt-dlp.exe' if platform.system() == 'Windows' else 'yt-dlp'
        
        # Check local directory
        local_path = os.path.join(os.getcwd(), exe_name)
        if os.path.exists(local_path):
            return

        # Check PATH
        import shutil
        if shutil.which(exe_name):
            return

        # Not found, download it
        self.log_output.append(f"⚠️ {exe_name} not found. Downloading automatically...")
        self.download_btn.setEnabled(False)
        self.update_btn.setEnabled(False)
        
        try:
            system = platform.system()
            if system == 'Windows':
                url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
            elif system == 'Darwin': # macOS
                url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos"
            else: # Linux
                url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"
            
            # Download with progress
            def progress_hook(count, block_size, total_size):
                percent = int(count * block_size * 100 / total_size)
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(percent)
                self.progress_bar.setFormat(f"Downloading yt-dlp: {percent}%")
                QApplication.processEvents()

            urllib.request.urlretrieve(url, local_path, progress_hook)
            
            # Make executable on Unix
            if system != 'Windows':
                st = os.stat(local_path)
                os.chmod(local_path, st.st_mode | stat.S_IEXEC)
            
            self.log_output.append(f"✅ {exe_name} downloaded and installed successfully!")
            self.progress_bar.setVisible(False)
            self.download_btn.setEnabled(True)
            self.update_btn.setEnabled(True)
            
        except Exception as e:
            self.log_output.append(f"❌ Failed to download yt-dlp: {str(e)}")
            self.log_output.append("Please download it manually from https://github.com/yt-dlp/yt-dlp/releases")

    def init_ui(self):
        self.setWindowTitle("yt-dlp Downloader")
        self.setGeometry(100, 100, 1000, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
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
        
        # URL Input Section
        url_group = QGroupBox("Target URL")
        url_layout = QVBoxLayout(url_group)
        url_layout.setContentsMargins(15, 25, 15, 15)
        
        input_container = QHBoxLayout()
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste video URL here (e.g., YouTube, Twitch, Twitter)...")
        self.url_input.setMinimumHeight(45)
        
        paste_btn = QPushButton("Paste")
        paste_btn.setObjectName("secondary_btn")
        paste_btn.setFixedWidth(80)
        paste_btn.setMinimumHeight(45)
        paste_btn.clicked.connect(self.paste_from_clipboard)
        
        input_container.addWidget(self.url_input)
        input_container.addWidget(paste_btn)
        url_layout.addLayout(input_container)
        
        main_layout.addWidget(url_group)
        
        # Options Grid
        options_group = QGroupBox("Configuration")
        options_layout = QGridLayout(options_group)
        options_layout.setContentsMargins(15, 25, 15, 15)
        options_layout.setHorizontalSpacing(20)
        options_layout.setVerticalSpacing(15)
        
        # Row 1: Formats
        options_layout.addWidget(QLabel("Quality Profile:"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "Best Quality", "1080p", "720p", "480p", "360p", "Audio Only"
        ])
        options_layout.addWidget(self.format_combo, 0, 1)
        
        options_layout.addWidget(QLabel("Container:"), 0, 2)
        self.video_format_combo = QComboBox()
        self.video_format_combo.addItems(["Auto (Best)", "MP4", "MKV", "WEBM"])
        options_layout.addWidget(self.video_format_combo, 0, 3)
        
        options_layout.addWidget(QLabel("Audio Format:"), 0, 4)
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(["mp3", "m4a", "wav", "flac"])
        options_layout.addWidget(self.audio_format_combo, 0, 5)

        # Row 2: Speed Limit
        options_layout.addWidget(QLabel("Speed Limit:"), 1, 0)
        self.speed_limit_spin = QSpinBox()
        self.speed_limit_spin.setRange(0, 100000)
        self.speed_limit_spin.setSpecialValueText("Unlimited")
        self.speed_limit_spin.setSuffix(" KB/s")
        options_layout.addWidget(self.speed_limit_spin, 1, 1)

        # Row 3: Checkboxes
        checkbox_layout = QGridLayout()
        self.extract_audio_cb = QCheckBox("Extract Audio")
        self.subtitle_cb = QCheckBox("Download Subtitles")
        self.auto_sub_cb = QCheckBox("Auto-Subs")
        self.thumbnail_cb = QCheckBox("Thumbnail")
        self.description_cb = QCheckBox("Description")
        self.playlist_cb = QCheckBox("Process Playlist")
        
        checkbox_layout.addWidget(self.extract_audio_cb, 0, 0)
        checkbox_layout.addWidget(self.subtitle_cb, 0, 1)
        checkbox_layout.addWidget(self.auto_sub_cb, 0, 2)
        checkbox_layout.addWidget(self.thumbnail_cb, 1, 0)
        checkbox_layout.addWidget(self.description_cb, 1, 1)
        checkbox_layout.addWidget(self.playlist_cb, 1, 2)
        
        options_layout.addLayout(checkbox_layout, 2, 0, 1, 6)
        
        main_layout.addWidget(options_group)
        
        # Output Directory
        output_group = QGroupBox("Save Location")
        output_layout = QHBoxLayout(output_group)
        output_layout.setContentsMargins(15, 25, 15, 15)
        
        self.output_path = QLineEdit()
        self.output_path.setText(os.getcwd())
        self.output_path.setReadOnly(True)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.setObjectName("secondary_btn")
        browse_btn.clicked.connect(self.browse_output_dir)
        
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(browse_btn)
        
        main_layout.addWidget(output_group)
        
        # Action Buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(15)
        
        self.download_btn = QPushButton("START DOWNLOAD")
        self.download_btn.setObjectName("download_btn")
        self.download_btn.setMinimumHeight(55)
        self.download_btn.setCursor(Qt.PointingHandCursor)
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
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.progress_bar)
        
        # Log Area
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Download logs will appear here...")
        main_layout.addWidget(self.log_output)

    def apply_modern_style(self):
        # Catppuccin Mocha inspired palette
        # Base: #1e1e2e
        # Mantle: #181825
        # Surface0: #313244
        # Text: #cdd6f4
        # Blue: #89b4fa
        # Red: #f38ba8
        # Green: #a6e3a1
        
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
                background-color: #252535; /* Surface0 slightly lighter */
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
                background-color: #252535; /* Match groupbox bg */
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
            
            QComboBox:on {
                border: 1px solid #89b4fa;
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
                background-color: #11111b; /* Crust */
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
        """Setup keyboard shortcuts."""
        # Ctrl+V to paste URL
        paste_shortcut = QShortcut(QKeySequence("Ctrl+V"), self)
        paste_shortcut.activated.connect(self.paste_from_clipboard)
        
        # Enter to start download
        download_shortcut = QShortcut(QKeySequence("Return"), self.url_input)
        download_shortcut.activated.connect(self.start_download)
        
        # Ctrl+L to clear log
        clear_shortcut = QShortcut(QKeySequence("Ctrl+L"), self)
        clear_shortcut.activated.connect(self.clear_log)

    def paste_from_clipboard(self):
        """Paste URL from clipboard."""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text and self.is_valid_url(text):
            self.url_input.setText(text)
            self.url_input.setFocus()

    def check_clipboard(self):
        """Auto-detect URLs from clipboard."""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        
        if text != self.last_clipboard and self.is_valid_url(text):
            self.last_clipboard = text
            # Only auto-paste if URL field is empty
            if not self.url_input.text().strip():
                self.url_input.setText(text)

    def is_valid_url(self, url):
        """Validate if string is a valid URL."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        except:
            return False

    def load_settings(self):
        """Load saved settings."""
        # Load last output directory
        last_dir = self.settings.value('output_dir', os.getcwd())
        self.output_path.setText(last_dir)
        
        # Load last selected options
        self.format_combo.setCurrentIndex(self.settings.value('format_index', 0, type=int))
        self.video_format_combo.setCurrentIndex(self.settings.value('video_format_index', 0, type=int))
        self.audio_format_combo.setCurrentIndex(self.settings.value('audio_format_index', 0, type=int))
        self.extract_audio_cb.setChecked(self.settings.value('extract_audio', False, type=bool))
        self.subtitle_cb.setChecked(self.settings.value('subtitle', False, type=bool))
        self.auto_sub_cb.setChecked(self.settings.value('auto_sub', False, type=bool))
        self.thumbnail_cb.setChecked(self.settings.value('thumbnail', False, type=bool))
        self.description_cb.setChecked(self.settings.value('description', False, type=bool))
        self.playlist_cb.setChecked(self.settings.value('playlist', False, type=bool))
        self.speed_limit_spin.setValue(self.settings.value('speed_limit', 0, type=int))

    def save_settings(self):
        """Save current settings."""
        self.settings.setValue('output_dir', self.output_path.text())
        self.settings.setValue('format_index', self.format_combo.currentIndex())
        self.settings.setValue('video_format_index', self.video_format_combo.currentIndex())
        self.settings.setValue('audio_format_index', self.audio_format_combo.currentIndex())
        self.settings.setValue('extract_audio', self.extract_audio_cb.isChecked())
        self.settings.setValue('subtitle', self.subtitle_cb.isChecked())
        self.settings.setValue('auto_sub', self.auto_sub_cb.isChecked())
        self.settings.setValue('thumbnail', self.thumbnail_cb.isChecked())
        self.settings.setValue('description', self.description_cb.isChecked())
        self.settings.setValue('playlist', self.playlist_cb.isChecked())
        self.settings.setValue('speed_limit', self.speed_limit_spin.value())

    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory", self.output_path.text())
        if directory:
            self.output_path.setText(directory)
            self.settings.setValue('output_dir', directory)

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            self.log_output.append("❌ Please enter a URL")
            return
        
        # Validate URL
        if not self.is_valid_url(url):
            self.log_output.append("❌ Invalid URL. Please enter a valid http:// or https:// URL")
            return
        
        if self.download_thread and self.download_thread.isRunning():
            self.log_output.append("❌ Download already in progress")
            return
        
        # Block downloads while an update is running
        if self.update_thread and self.update_thread.isRunning():
            self.log_output.append("❌ Please wait for yt-dlp update to finish before starting a download")
            return
        
        # Save settings
        self.save_settings()
        
        # Get options
        options = {
            'extract_audio': self.extract_audio_cb.isChecked(),
            'video_format': self.video_format_combo.currentText(),
            'audio_format': self.audio_format_combo.currentText(),
            'subtitle': self.subtitle_cb.isChecked(),
            'auto_sub': self.auto_sub_cb.isChecked(),
            'thumbnail': self.thumbnail_cb.isChecked(),
            'description': self.description_cb.isChecked(),
            'playlist': self.playlist_cb.isChecked(),
            'speed_limit': self.speed_limit_spin.value()
        }
        
        # Format selection
        format_text = self.format_combo.currentText()
        if format_text == "Best Quality":
            # Let yt-dlp auto-select and merge the best formats (no -f)
            pass
        elif format_text == "Audio Only":
            options['extract_audio'] = True
            # Prefer bestaudio with a safe fallback
            options['format'] = "bestaudio/best"
        elif format_text.endswith('p'):
            height = format_text[:-1]
            # Select best video up to the chosen height + best audio, with fallback to a single file up to that height
            options['format'] = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]"
        
        output_dir = self.output_path.text().strip() or os.getcwd()
        
        self.log_output.append(f"🚀 Starting download from: {url}")
        self.log_output.append(f"📁 Output directory: {output_dir}")
        
        # Start download thread
        self.download_thread = DownloadThread(url, options, output_dir)
        self.download_thread.progress.connect(self.update_log)
        self.download_thread.progress_percent.connect(self.update_progress)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.error.connect(self.download_error)
        
        self.download_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        self.download_thread.start()

    def cancel_download(self):
        """Cancel the current download."""
        if self.download_thread and self.download_thread.isRunning():
            self.log_output.append("🛑 Cancelling download...")
            self.download_thread.cancel()
            self.cancel_btn.setEnabled(False)

    def update_progress(self, percent):
        """Update progress bar with percentage."""
        self.progress_bar.setValue(percent)
        self.progress_bar.setFormat(f"{percent}%")

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

    def start_update(self):
        # Prevent update during an active download
        if self.download_thread and self.download_thread.isRunning():
            self.log_output.append("❌ Please wait for the current download to finish before updating yt-dlp")
            return
        # Prevent multiple updates
        if self.update_thread and self.update_thread.isRunning():
            self.log_output.append("❌ Update already in progress")
            return

        exe_name = 'yt-dlp.exe' if platform.system() == 'Windows' else 'yt-dlp'
        exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), exe_name)
        
        if not os.path.exists(exe_path):
            # Check if it's in the path
            import shutil
            if shutil.which(exe_name):
                exe_path = exe_name
            else:
                self.log_output.append(f"❌ {exe_name} not found. Please install it or place it in the app directory.")
                return

        self.log_output.append("🔄 Checking for yt-dlp updates...")
        self.update_thread = UpdateThread(exe_path)
        self.update_thread.progress.connect(self.update_log)
        self.update_thread.finished.connect(self.update_finished)
        self.update_thread.error.connect(self.update_error)

        self.update_btn.setText("Updating...")
        self.update_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self.update_thread.start()

    def update_finished(self, message):
        self.log_output.append(f"✅ {message}")
        self.update_btn.setText("Update yt-dlp")
        self.update_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def update_error(self, message):
        self.log_output.append(f"❌ {message}")
        self.update_btn.setText("Update yt-dlp")
        self.update_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def clear_log(self):
        self.log_output.clear()

    def closeEvent(self, event):
        """Save settings on close."""
        self.save_settings()
        
        # Cancel any running downloads
        if self.download_thread and self.download_thread.isRunning():
            self.download_thread.cancel()
            self.download_thread.wait()
        
        event.accept()


def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("Modern yt-dlp GUI")
    app.setApplicationVersion("1.0")
    
    window = ModernYTDLPGUI()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
