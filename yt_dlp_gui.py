import sys
import os
import subprocess
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QLabel, QLineEdit, QPushButton, QTextEdit, 
                            QCheckBox, QComboBox, QGroupBox, QProgressBar, QFileDialog,
                            QGridLayout, QSpacerItem, QSizePolicy, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPalette, QColor


class DownloadThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url, options, output_path):
        super().__init__()
        self.url = url
        self.options = options
        self.output_path = output_path

    def run(self):
        try:
            # Build yt-dlp command
            cmd = ['yt-dlp.exe']
            
            # Add options based on selections
            if self.options.get('format'):
                cmd.extend(['-f', self.options['format']])
            
            if self.options.get('extract_audio'):
                cmd.extend(['-x', '--audio-format', self.options.get('audio_format', 'mp3')])
            
            if self.options.get('subtitle'):
                cmd.append('--write-subs')
                if self.options.get('auto_sub'):
                    cmd.append('--write-auto-subs')
            
            if self.options.get('thumbnail'):
                cmd.append('--write-thumbnail')
            
            if self.options.get('description'):
                cmd.append('--write-description')
            
            # Output directory
            if self.output_path:
                cmd.extend(['-o', f'{self.output_path}/%(title)s.%(ext)s'])
            
            # Add URL
            cmd.append(self.url)
            
            # Run command
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
                self.finished.emit("Download completed successfully!")
            else:
                self.error.emit(f"Download failed with return code: {process.returncode}")
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
    def __init__(self):
        super().__init__()
        self.download_thread = None
        self.update_thread = None
        self.init_ui()
        self.apply_modern_style()

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
        title_label = QLabel("🎬 yt-dlp Downloader")
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
        main_layout.addWidget(title_label)
        
        # URL Input Section
        url_group = QGroupBox("Video URL")
        url_layout = QVBoxLayout(url_group)
        
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("Paste your video URL here...")
        self.url_input.setMinimumHeight(40)
        url_layout.addWidget(self.url_input)
        
        main_layout.addWidget(url_group)
        
        # Options Section
        options_group = QGroupBox("Download Options")
        options_layout = QGridLayout(options_group)
        
        # Format selection
        format_label = QLabel("Video Quality:")
        self.format_combo = QComboBox()
        self.format_combo.addItems([
            "Best Quality", "1080p", "720p", "480p", "360p", "240p", "Audio Only"
        ])
        options_layout.addWidget(format_label, 0, 0)
        options_layout.addWidget(self.format_combo, 0, 1)
        
        # Audio format for audio-only downloads
        audio_label = QLabel("Audio Format:")
        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(["mp3", "wav", "aac", "flac", "m4a"])
        options_layout.addWidget(audio_label, 0, 2)
        options_layout.addWidget(self.audio_format_combo, 0, 3)
        
        # Checkboxes for additional options
        self.extract_audio_cb = QCheckBox("Extract Audio Only")
        self.subtitle_cb = QCheckBox("Download Subtitles")
        self.auto_sub_cb = QCheckBox("Auto-generated Subtitles")
        self.thumbnail_cb = QCheckBox("Download Thumbnail")
        self.description_cb = QCheckBox("Save Description")
        
        options_layout.addWidget(self.extract_audio_cb, 1, 0)
        options_layout.addWidget(self.subtitle_cb, 1, 1)
        options_layout.addWidget(self.auto_sub_cb, 1, 2)
        options_layout.addWidget(self.thumbnail_cb, 2, 0)
        options_layout.addWidget(self.description_cb, 2, 1)
        
        main_layout.addWidget(options_group)
        
        # Output Directory Section
        output_group = QGroupBox("Output Directory")
        output_layout = QHBoxLayout(output_group)
        
        self.output_path = QLineEdit()
        self.output_path.setPlaceholderText("Select output directory (default: current directory)")
        self.output_path.setText(os.getcwd())
        
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_output_dir)
        browse_btn.setMaximumWidth(100)
        
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(browse_btn)
        
        main_layout.addWidget(output_group)
        
        # Control Buttons
        button_layout = QHBoxLayout()
        
        self.download_btn = QPushButton("Download")
        self.download_btn.setMinimumHeight(50)
        self.download_btn.clicked.connect(self.start_download)
        
        self.update_btn = QPushButton("Update yt-dlp")
        self.update_btn.setObjectName("update_btn")
        self.update_btn.setMinimumHeight(50)
        self.update_btn.clicked.connect(self.start_update)

        self.clear_btn = QPushButton("Clear Log")
        self.clear_btn.setObjectName("clear_btn")
        self.clear_btn.setMinimumHeight(50)
        self.clear_btn.clicked.connect(self.clear_log)
        
        button_layout.addWidget(self.download_btn)
        button_layout.addWidget(self.update_btn)
        button_layout.addWidget(self.clear_btn)
        
        main_layout.addLayout(button_layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        
        # Log Output
        log_group = QGroupBox("Download Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(200)
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
                outline: 2px solid rgba(9, 105, 218, 0.15);
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
                background: #94a3b8;
                border-color: #cbd5e1;
                color: #f1f5f9;
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
                outline: 2px solid rgba(9, 105, 218, 0.15);
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

    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if directory:
            self.output_path.setText(directory)

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            self.log_output.append("❌ Please enter a URL")
            return
        
        if self.download_thread and self.download_thread.isRunning():
            self.log_output.append("❌ Download already in progress")
            return
        
        # Block downloads while an update is running
        if self.update_thread and self.update_thread.isRunning():
            self.log_output.append("❌ Please wait for yt-dlp update to finish before starting a download")
            return
        
        # Get options
        options = {
            'extract_audio': self.extract_audio_cb.isChecked(),
            'audio_format': self.audio_format_combo.currentText(),
            'subtitle': self.subtitle_cb.isChecked(),
            'auto_sub': self.auto_sub_cb.isChecked(),
            'thumbnail': self.thumbnail_cb.isChecked(),
            'description': self.description_cb.isChecked()
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
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.error.connect(self.download_error)
        
        self.download_btn.setText("Downloading...")
        self.download_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        self.download_thread.start()

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
        self.download_btn.setText("Download")
        self.download_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def start_update(self):
        # Prevent update during an active download
        if self.download_thread and self.download_thread.isRunning():
            self.log_output.append("❌ Please wait for the current download to finish before updating yt-dlp")
            return
        # Prevent multiple updates
        if self.update_thread and self.update_thread.isRunning():
            self.log_output.append("❌ Update already in progress")
            return

        exe_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yt-dlp.exe')
        if not os.path.exists(exe_path):
            self.log_output.append("❌ yt-dlp.exe not found next to the application. Place yt-dlp.exe in the same folder and try again.")
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
