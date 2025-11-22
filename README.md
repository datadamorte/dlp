# Modern yt-dlp GUI

A modern, user-friendly graphical interface for [yt-dlp](https://github.com/yt-dlp/yt-dlp) with a professional dark theme and comprehensive download options.

## Features

- 🎨 **Modern Dark UI**: Professional dark theme (Catppuccin Mocha inspired) for reduced eye strain.
- 🖥️ **Cross-Platform**: Works seamlessly on Windows, macOS, and Linux.
- 📺 **Multiple Quality Options**: Choose from various video qualities (1080p, 720p, etc.) or audio-only.
- 🎵 **Audio Extraction**: Download audio in multiple formats (mp3, wav, aac, flac, m4a).
- 📝 **Subtitle Support**: Download subtitles and auto-generated captions.
- 🖼️ **Thumbnail & Metadata**: Save thumbnails and video descriptions.
- 📁 **Custom Output Directory**: Choose where to save your downloads.
- 📊 **Real-time Progress**: Live download progress with percentage tracking.
- 🔄 **Built-in Updater**: Keep `yt-dlp` up-to-date with one click.
- 🎬 **Playlist Support**: Download entire playlists with one click.
- ⚡ **Speed Limiting**: Throttle download speed to save bandwidth.
- 📋 **Clipboard Auto-Detection**: Automatically detects and pastes URLs from clipboard.

## Requirements

- Python 3.7+
- `PyQt5` (installed via requirements.txt)
- `yt-dlp` executable (automatically downloaded by the app if missing)

## Setup

### 1. Create Virtual Environment

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the Application

The application will automatically check for `yt-dlp` and download it if necessary.

```bash
python yt_dlp_gui.py
```

## Usage

1.  Activate the virtual environment (if not already active).
2.  Run the application:
    ```bash
    python yt_dlp_gui.py
    ```
3.  Paste a video URL (or let the clipboard auto-detect do it).
4.  Select your preferred options (Quality, Format, etc.).
5.  Click **START DOWNLOAD**.

## Options Explained

-   **Quality Profile**: Select the maximum quality to download (e.g., "Best Quality", "1080p").
-   **Container**: Choose output video container (MP4, MKV, WEBM). "Auto (Best)" is recommended.
-   **Audio Format**: Choose audio format when extracting audio only.
-   **Speed Limit**: Set maximum download speed in KB/s (0 = unlimited).
-   **Checkboxes**:
    -   **Extract Audio**: Download only the audio track.
    -   **Download Subtitles**: Save available subtitles.
    -   **Auto-Subs**: Include auto-generated captions.
    -   **Thumbnail**: Save video thumbnail image.
    -   **Description**: Save video description as text file.
    -   **Process Playlist**: Download all videos if the URL is a playlist.

## Keyboard Shortcuts

-   **Ctrl+V**: Paste URL from clipboard.
-   **Enter**: Start download (when URL field is focused).
-   **Ctrl+L**: Clear log output.
