import sys
import os
import subprocess
import threading
import json
import re
from urllib.parse import urlparse
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
                            QWidget, QLabel, QLineEdit, QPushButton, QTextEdit,
                            QCheckBox, QComboBox, QGroupBox, QProgressBar, QFileDialog,
                            QGridLayout, QSpacerItem, QSizePolicy, QFrame, QSpinBox,
                            QShortcut, QWhatsThis)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSettings, QEvent
from PyQt5.QtGui import QFont, QPalette, QColor, QKeySequence, QAccessible


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
            cmd = ['yt-dlp.exe']
            
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
            cmd = [self.exe_path, '-U']
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
                self.finished.emit("yt-dlp update completed.")
            else:
                self.error.emit(f"Update failed with return code: {process.returncode}")
        except Exception as e:
            self.error.emit(f"Error: {str(e)}")

class ModernYTDLPGUI(QMainWindow):
    # Signal for announcing status changes to screen readers
    status_changed = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.download_thread = None
        self.update_thread = None
        self.settings = QSettings('YTDLPGui', 'ModernYTDLP')
        self.init_ui()
        self.apply_modern_style()
        self.load_settings()
        self.setup_shortcuts()
        self.setup_accessibility()
        self.check_clipboard_timer = QTimer()
        self.check_clipboard_timer.timeout.connect(self.check_clipboard)
        self.check_clipboard_timer.start(1000)  # Check every second
        self.last_clipboard = ""

    def init_ui(self):
        self.setWindowTitle("yt-dlp Downloader")
        self.setGeometry(100, 100, 900, 750)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(25)
        main_layout.setContentsMargins(40, 35, 40, 35)
        
        # Title
        title_label = QLabel("yt-dlp Downloader")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: 700;
                color: #1a1a1a;
                margin-bottom: 15px;
                letter-spacing: -0.5px;
            }
        """)
        title_label.setAccessibleName("yt-dlp Downloader Application")
        title_label.setAccessibleDescription("Main application for downloading videos and audio using yt-dlp")
        main_layout.addWidget(title_label)
        
        # URL Input Section
        url_group = QGroupBox("Video URL")
        url_group.setAccessibleName("Video URL Input Section")
        url_group.setAccessibleDescription("Enter the URL of the video you want to download")
        url_layout = QVBoxLayout(url_group)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste your video URL here...")
        self.url_input.setMinimumHeight(40)
        self.url_input.setAccessibleName("Video URL")
        self.url_input.setAccessibleDescription("Enter or paste the URL of the video you want to download. Press Enter to start download.")
        self.url_input.setToolTip("Enter the URL of the video to download\nShortcut: Ctrl+V to paste\nPress Enter to start download")
        url_layout.addWidget(self.url_input)

        main_layout.addWidget(url_group)
        
        # Options Section
        options_group = QGroupBox("Download Options")
        options_group.setAccessibleName("Download Options Section")
        options_group.setAccessibleDescription("Configure video quality, format, and additional download options")
        options_layout = QGridLayout(options_group)

        # Format selection
        format_label = QLabel("&Quality:")
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "Best Quality", "1080p", "720p", "480p", "360p", "240p", "Audio Only"
        ])
        self.format_combo.setAccessibleName("Video Quality")
        self.format_combo.setAccessibleDescription("Select the desired video quality or choose audio only")
        self.format_combo.setToolTip("Choose video quality (resolution) or select Audio Only to download just the audio track")
        format_label.setBuddy(self.format_combo)
        options_layout.addWidget(format_label, 0, 0)
        options_layout.addWidget(self.format_combo, 0, 1)

        # Video format/container selection
        video_format_label = QLabel("Video &Format:")
        self.video_format_combo = QComboBox()
        self.video_format_combo.addItems(["Auto (Best)", "MP4", "MKV", "WEBM", "AVI", "FLV"])
        self.video_format_combo.setAccessibleName("Video Container Format")
        self.video_format_combo.setAccessibleDescription("Select the video file container format")
        self.video_format_combo.setToolTip("Choose the video container format\nMP4: Best compatibility\nMKV: High quality, supports multiple tracks\nWEBM: Web-optimized format")
        video_format_label.setBuddy(self.video_format_combo)
        options_layout.addWidget(video_format_label, 0, 2)
        options_layout.addWidget(self.video_format_combo, 0, 3)

        # Audio format for audio-only downloads
        audio_label = QLabel("&Audio Format:")
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(["mp3", "wav", "aac", "flac", "m4a"])
        self.audio_format_combo.setAccessibleName("Audio Format")
        self.audio_format_combo.setAccessibleDescription("Select the audio file format for audio-only downloads")
        self.audio_format_combo.setToolTip("Choose audio format for audio-only downloads\nMP3: Universal compatibility\nFLAC: Lossless quality\nAAC: Good quality, small size")
        audio_label.setBuddy(self.audio_format_combo)
        options_layout.addWidget(audio_label, 0, 4)
        options_layout.addWidget(self.audio_format_combo, 0, 5)
        
        # Checkboxes for additional options
        self.extract_audio_cb = QCheckBox("&Extract Audio Only")
        self.extract_audio_cb.setAccessibleName("Extract Audio Only")
        self.extract_audio_cb.setAccessibleDescription("Extract only the audio track from the video")
        self.extract_audio_cb.setToolTip("Extract only audio from the video (ignores video streams)")

        self.subtitle_cb = QCheckBox("Download &Subtitles")
        self.subtitle_cb.setAccessibleName("Download Subtitles")
        self.subtitle_cb.setAccessibleDescription("Download available subtitles with the video")
        self.subtitle_cb.setToolTip("Download subtitle files if available")

        self.auto_sub_cb = QCheckBox("Auto-&generated Subs")
        self.auto_sub_cb.setAccessibleName("Auto-generated Subtitles")
        self.auto_sub_cb.setAccessibleDescription("Include automatically generated subtitles")
        self.auto_sub_cb.setToolTip("Download auto-generated subtitles (requires Download Subtitles to be checked)")

        self.thumbnail_cb = QCheckBox("Download &Thumbnail")
        self.thumbnail_cb.setAccessibleName("Download Thumbnail")
        self.thumbnail_cb.setAccessibleDescription("Download the video thumbnail image")
        self.thumbnail_cb.setToolTip("Download the video thumbnail as a separate image file")

        self.description_cb = QCheckBox("Save &Description")
        self.description_cb.setAccessibleName("Save Description")
        self.description_cb.setAccessibleDescription("Save the video description to a text file")
        self.description_cb.setToolTip("Save video description and metadata to a text file")

        self.playlist_cb = QCheckBox("Download &Playlist")
        self.playlist_cb.setAccessibleName("Download Playlist")
        self.playlist_cb.setAccessibleDescription("Download all videos in the playlist")
        self.playlist_cb.setToolTip("Download entire playlist (if URL is a playlist)")

        options_layout.addWidget(self.extract_audio_cb, 1, 0)
        options_layout.addWidget(self.subtitle_cb, 1, 1)
        options_layout.addWidget(self.auto_sub_cb, 1, 2)
        options_layout.addWidget(self.thumbnail_cb, 2, 0)
        options_layout.addWidget(self.description_cb, 2, 1)
        options_layout.addWidget(self.playlist_cb, 2, 2)

        # Speed limit option
        speed_label = QLabel("Speed &Limit:")
        self.speed_limit_spin = QSpinBox()
        self.speed_limit_spin.setMinimum(0)
        self.speed_limit_spin.setMaximum(100000)
        self.speed_limit_spin.setValue(0)
        self.speed_limit_spin.setSpecialValueText("No Limit")
        self.speed_limit_spin.setSuffix(" KB/s")
        self.speed_limit_spin.setAccessibleName("Download Speed Limit")
        self.speed_limit_spin.setAccessibleDescription("Set maximum download speed in kilobytes per second, 0 for unlimited")
        self.speed_limit_spin.setToolTip("Limit download speed (0 = no limit)\nUseful for preventing bandwidth saturation")
        speed_label.setBuddy(self.speed_limit_spin)
        options_layout.addWidget(speed_label, 3, 0)
        options_layout.addWidget(self.speed_limit_spin, 3, 1)
        
        main_layout.addWidget(options_group)
        
        # Output Directory Section
        output_group = QGroupBox("Output Directory")
        output_group.setAccessibleName("Output Directory Section")
        output_group.setAccessibleDescription("Choose where to save downloaded files")
        output_layout = QHBoxLayout(output_group)

        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Select output directory (default: current directory)")
        self.output_path.setText(os.getcwd())
        self.output_path.setAccessibleName("Output Directory Path")
        self.output_path.setAccessibleDescription("Path where downloaded files will be saved")
        self.output_path.setToolTip("Directory path where downloaded videos will be saved\nClick Browse to select a different folder")

        browse_btn = QPushButton("&Browse...")
        browse_btn.clicked.connect(self.browse_output_dir)
        browse_btn.setMaximumWidth(120)
        browse_btn.setAccessibleName("Browse for Output Directory")
        browse_btn.setAccessibleDescription("Open folder browser to select output directory")
        browse_btn.setToolTip("Browse and select output folder (Alt+B)")

        output_layout.addWidget(self.output_path)
        output_layout.addWidget(browse_btn)

        main_layout.addWidget(output_group)
        
        # Control Buttons
        button_layout = QHBoxLayout()

        self.download_btn = QPushButton("&Download")
        self.download_btn.setMinimumHeight(50)
        self.download_btn.clicked.connect(self.start_download)
        self.download_btn.setAccessibleName("Download")
        self.download_btn.setAccessibleDescription("Start downloading the video from the entered URL")
        self.download_btn.setToolTip("Start download (Alt+D or press Enter in URL field)")
        self.download_btn.setDefault(True)

        self.cancel_btn = QPushButton("&Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setMinimumHeight(50)
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setAccessibleName("Cancel Download")
        self.cancel_btn.setAccessibleDescription("Stop the current download operation")
        self.cancel_btn.setToolTip("Cancel the current download (Alt+C)")

        self.update_btn = QPushButton("&Update yt-dlp")
        self.update_btn.setObjectName("update_btn")
        self.update_btn.setMinimumHeight(50)
        self.update_btn.clicked.connect(self.start_update)
        self.update_btn.setAccessibleName("Update yt-dlp")
        self.update_btn.setAccessibleDescription("Check for and install yt-dlp updates")
        self.update_btn.setToolTip("Update yt-dlp to the latest version (Alt+U)")

        self.clear_btn = QPushButton("C&lear Log")
        self.clear_btn.setObjectName("clear_btn")
        self.clear_btn.setMinimumHeight(50)
        self.clear_btn.clicked.connect(self.clear_log)
        self.clear_btn.setAccessibleName("Clear Log")
        self.clear_btn.setAccessibleDescription("Clear the download log output")
        self.clear_btn.setToolTip("Clear the log output (Ctrl+L)")

        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.update_btn)
        button_layout.addWidget(self.clear_btn)

        main_layout.addLayout(button_layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setAccessibleName("Download Progress")
        self.progress_bar.setAccessibleDescription("Shows download progress percentage")
        main_layout.addWidget(self.progress_bar)

        # Log Output
        log_group = QGroupBox("Download Log")
        log_group.setAccessibleName("Download Log Section")
        log_group.setAccessibleDescription("Shows download status messages and progress information")
        log_layout = QVBoxLayout(log_group)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(200)
        self.log_output.setAccessibleName("Download Log Output")
        self.log_output.setAccessibleDescription("Read-only log showing download progress and status messages")
        self.log_output.setToolTip("Download progress and status messages appear here")
        log_layout.addWidget(self.log_output)

        main_layout.addWidget(log_group)

    def apply_modern_style(self):
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f5f7fa, stop:1 #e8edf2);
            }
            
            QGroupBox {
                font-weight: 600;
                font-size: 13px;
                color: #1a1a1a;
                border: 1px solid #d0d7de;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 18px;
                background-color: rgba(255, 255, 255, 0.85);
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 3px 8px;
                background-color: white;
                border-radius: 4px;
            }
            
            QLineEdit {
                border: 1.5px solid #d0d7de;
                border-radius: 8px;
                padding: 10px 14px;
                font-size: 13px;
                background-color: white;
                color: #1a1a1a;
                selection-background-color: #0969da;
            }
            
            QLineEdit:focus {
                border-color: #0969da;
                outline: 3px solid rgba(9, 105, 218, 0.4);
                outline-offset: 1px;
            }
            
            QLineEdit:hover {
                border-color: #a8b3c1;
            }
            
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0969da, stop:1 #0550ae);
                color: white;
                border: 1px solid rgba(0, 0, 0, 0.15);
                border-radius: 8px;
                padding: 12px 24px;
                font-weight: 600;
                font-size: 13px;
            }

            QPushButton:focus {
                outline: 3px solid rgba(9, 105, 218, 0.5);
                outline-offset: 2px;
            }

            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #0860ca, stop:1 #044a9e);
                border-color: rgba(0, 0, 0, 0.2);
            }
            
            QPushButton:pressed {
                background: #0550ae;
                padding-top: 13px;
                padding-bottom: 11px;
            }
            
            QPushButton:disabled {
                background: #64748b;
                border-color: #94a3b8;
                color: #f8fafc;
            }
            
            QPushButton#update_btn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7c3aed, stop:1 #6d28d9);
            }
            
            QPushButton#update_btn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #6d28d9, stop:1 #5b21b6);
            }
            
            QPushButton#clear_btn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #64748b, stop:1 #475569);
            }
            
            QPushButton#clear_btn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #475569, stop:1 #334155);
            }
            
            QPushButton#cancel_btn {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #dc2626, stop:1 #b91c1c);
            }
            
            QPushButton#cancel_btn:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #b91c1c, stop:1 #991b1b);
            }
            
            QSpinBox {
                border: 1.5px solid #d0d7de;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: white;
                color: #1a1a1a;
                font-size: 12px;
            }
            
            QSpinBox:focus {
                border-color: #0969da;
                outline: 3px solid rgba(9, 105, 218, 0.4);
                outline-offset: 1px;
            }
            
            QSpinBox:hover {
                border-color: #a8b3c1;
            }
            
            QComboBox {
                border: 1.5px solid #d0d7de;
                border-radius: 8px;
                padding: 8px 12px;
                background-color: white;
                min-width: 110px;
                color: #1a1a1a;
                font-size: 12px;
            }
            
            QComboBox:focus {
                border-color: #0969da;
                outline: 3px solid rgba(9, 105, 218, 0.4);
                outline-offset: 1px;
            }
            
            QComboBox:hover {
                border-color: #a8b3c1;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 25px;
            }
            
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #6e7681;
                margin-right: 5px;
            }
            
            QComboBox QAbstractItemView {
                border: 1px solid #d0d7de;
                border-radius: 6px;
                background-color: white;
                selection-background-color: #0969da;
                selection-color: white;
                padding: 4px;
            }
            
            QCheckBox {
                font-size: 13px;
                color: #1a1a1a;
                spacing: 10px;
            }
            
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
                border: 1.5px solid #d0d7de;
                border-radius: 4px;
                background-color: white;
            }
            
            QCheckBox::indicator:hover {
                border-color: #0969da;
            }

            QCheckBox::indicator:focus {
                outline: 3px solid rgba(9, 105, 218, 0.4);
                outline-offset: 1px;
            }

            QCheckBox::indicator:checked {
                background-color: #0969da;
                border-color: #0969da;
                image: none;
            }
            
            QTextEdit {
                border: 1.5px solid #d0d7de;
                border-radius: 8px;
                background-color: #0d1117;
                color: #e6edf3;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                padding: 8px;
            }
            
            QProgressBar {
                border: none;
                border-radius: 6px;
                text-align: center;
                font-weight: 600;
                background-color: #e5e7eb;
                height: 8px;
                font-size: 11px;
            }
            
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0969da, stop:1 #0550ae);
                border-radius: 6px;
            }
            
            QLabel {
                color: #1a1a1a;
                font-size: 12px;
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

    def setup_accessibility(self):
        """Setup accessibility features including tab order and window properties."""
        # Set minimum window size for proper display
        self.setMinimumSize(800, 650)

        # Enable high DPI scaling
        self.setAttribute(Qt.AA_EnableHighDpiScaling, True)

        # Set explicit tab order for logical keyboard navigation
        self.setTabOrder(self.url_input, self.format_combo)
        self.setTabOrder(self.format_combo, self.video_format_combo)
        self.setTabOrder(self.video_format_combo, self.audio_format_combo)
        self.setTabOrder(self.audio_format_combo, self.extract_audio_cb)
        self.setTabOrder(self.extract_audio_cb, self.subtitle_cb)
        self.setTabOrder(self.subtitle_cb, self.auto_sub_cb)
        self.setTabOrder(self.auto_sub_cb, self.thumbnail_cb)
        self.setTabOrder(self.thumbnail_cb, self.description_cb)
        self.setTabOrder(self.description_cb, self.playlist_cb)
        self.setTabOrder(self.playlist_cb, self.speed_limit_spin)
        self.setTabOrder(self.speed_limit_spin, self.output_path)
        self.setTabOrder(self.output_path, self.download_btn)
        self.setTabOrder(self.download_btn, self.update_btn)
        self.setTabOrder(self.update_btn, self.clear_btn)
        self.setTabOrder(self.clear_btn, self.log_output)

        # Connect status signal for announcements
        self.status_changed.connect(self.announce_status)

    def announce_status(self, message):
        """Announce status changes to screen readers."""
        # This uses Qt's accessibility system to announce changes
        QAccessible.updateAccessibility(self, 0, QAccessible.Alert)

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
            msg = "[ERROR] Please enter a URL"
            self.log_output.append(msg)
            self.status_changed.emit(msg)
            self.url_input.setFocus()
            return

        # Validate URL
        if not self.is_valid_url(url):
            msg = "[ERROR] Invalid URL. Please enter a valid http:// or https:// URL"
            self.log_output.append(msg)
            self.status_changed.emit(msg)
            self.url_input.setFocus()
            self.url_input.selectAll()
            return

        if self.download_thread and self.download_thread.isRunning():
            msg = "[ERROR] Download already in progress"
            self.log_output.append(msg)
            self.status_changed.emit(msg)
            return

        # Block downloads while an update is running
        if self.update_thread and self.update_thread.isRunning():
            msg = "[ERROR] Please wait for yt-dlp update to finish before starting a download"
            self.log_output.append(msg)
            self.status_changed.emit(msg)
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

        start_msg = f"[INFO] Starting download from: {url}"
        dir_msg = f"[INFO] Output directory: {output_dir}"
        self.log_output.append(start_msg)
        self.log_output.append(dir_msg)
        self.status_changed.emit("Download started")
        
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
            msg = "[INFO] Cancelling download..."
            self.log_output.append(msg)
            self.status_changed.emit("Cancelling download")
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
        msg = f"[SUCCESS] {message}"
        self.log_output.append(msg)
        self.status_changed.emit(message)
        self.reset_download_ui()

    def download_error(self, message):
        msg = f"[ERROR] {message}"
        self.log_output.append(msg)
        self.status_changed.emit(f"Error: {message}")
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
            msg = "[ERROR] Please wait for the current download to finish before updating yt-dlp"
            self.log_output.append(msg)
            self.status_changed.emit(msg)
            return
        # Prevent multiple updates
        if self.update_thread and self.update_thread.isRunning():
            msg = "[ERROR] Update already in progress"
            self.log_output.append(msg)
            self.status_changed.emit(msg)
            return

        exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yt-dlp.exe')
        if not os.path.exists(exe_path):
            msg = "[ERROR] yt-dlp.exe not found next to the application. Place yt-dlp.exe in the same folder and try again."
            self.log_output.append(msg)
            self.status_changed.emit(msg)
            return

        msg = "[INFO] Checking for yt-dlp updates..."
        self.log_output.append(msg)
        self.status_changed.emit("Checking for updates")
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
        msg = f"[SUCCESS] {message}"
        self.log_output.append(msg)
        self.status_changed.emit(message)
        self.update_btn.setText("&Update yt-dlp")
        self.update_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def update_error(self, message):
        msg = f"[ERROR] {message}"
        self.log_output.append(msg)
        self.status_changed.emit(f"Update error: {message}")
        self.update_btn.setText("&Update yt-dlp")
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
