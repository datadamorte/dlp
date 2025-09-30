# Modern yt-dlp GUI

A modern, user-friendly graphical interface for yt-dlp with comprehensive download options.

## Features

- 🎯 **Modern UI**: Clean, intuitive interface with dark theme log output
- 📺 **Multiple Quality Options**: Choose from various video qualities or audio-only
- 🎵 **Audio Extraction**: Download audio in multiple formats (mp3, wav, aac, flac, m4a)
- 📝 **Subtitle Support**: Download subtitles and auto-generated captions
- 🖼️ **Thumbnail & Metadata**: Save thumbnails and video descriptions
- 📁 **Custom Output Directory**: Choose where to save your downloads
- 📊 **Real-time Progress**: Live download progress and logging
- 🔄 **Built-in Updater**: Keep yt-dlp up-to-date with one click
- 🧹 **Clear Log**: Clean log output to keep workspace organized

## Setup

### Option 1: Automatic Setup (Recommended)
1. Double-click `setup.bat` to automatically create virtual environment and install dependencies
2. Follow the on-screen instructions

### Option 2: Manual Setup
1. Create virtual environment:
   ```
   python -m venv venv
   ```
2. Activate virtual environment:
   ```
   venv\Scripts\activate.bat
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

1. Activate the virtual environment:
   ```
   venv\Scripts\activate.bat
   ```
2. Run the application:
   ```
   python yt_dlp_gui.py
   ```
3. Paste your video URL and select your preferred options
4. Choose output directory (optional)
5. Click "Download" to start
6. Use "Update yt-dlp" button to keep yt-dlp updated
7. Use "Clear Log" button to clear the download log

## Requirements

- Python 3.7+
- yt-dlp.exe (should be placed in the same directory as the script)
- PyQt5 (installed via requirements.txt)
- Internet connection

**Note**: Download the latest yt-dlp.exe from [yt-dlp releases](https://github.com/yt-dlp/yt-dlp/releases) and place it in the same folder as `yt_dlp_gui.py`. You can also use the built-in updater to keep it current.

## Supported Sites

This GUI supports all sites that yt-dlp supports, including:
- YouTube
- Twitch
- Facebook
- Instagram
- TikTok
- And many more!

## Options Explained

- **Video Quality**: Select the maximum quality to download
- **Audio Format**: Choose audio format when extracting audio only
- **Extract Audio Only**: Download only the audio track
- **Download Subtitles**: Save available subtitles
- **Auto-generated Subtitles**: Include auto-generated captions
- **Download Thumbnail**: Save video thumbnail image
- **Save Description**: Save video description as text file
