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

- Python 3.10+ (3.9 is deprecated by yt-dlp)
- `PyQt5` (installed via requirements.txt)
- `yt-dlp` (installed via pip or auto-downloaded)
- **ffmpeg** (recommended for merging video+audio formats)

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
-   **Use Cookies**: Use browser cookies to bypass 403 errors (see Troubleshooting).
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

## Troubleshooting

### HTTP Error 403: Forbidden

YouTube may block requests that appear to come from bots. To fix this:

1. Set **Use Cookies** to your browser (e.g., Safari, Chrome, Firefox)
2. Make sure you're logged into YouTube in that browser
3. The app will use your browser's authentication to bypass restrictions

### Formats won't merge

If you see "ffmpeg is not installed" warning, install ffmpeg:

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

**Linux:**
```bash
sudo apt install ffmpeg  # Debian/Ubuntu
sudo dnf install ffmpeg  # Fedora
```

### Python version warning

yt-dlp has deprecated Python 3.9. For best compatibility, use Python 3.10 or newer.
