# Modern yt-dlp GUI

A modern, user-friendly graphical interface for yt-dlp with comprehensive download options.

## Features

- **Modern UI**: Clean, intuitive interface with dark theme log output
- **Multiple Quality Options**: Choose from various video qualities or audio-only
- **Audio Extraction**: Download audio in multiple formats (mp3, wav, aac, flac, m4a)
- **Subtitle Support**: Download subtitles and auto-generated captions
- **Thumbnail & Metadata**: Save thumbnails and video descriptions
- **Custom Output Directory**: Choose where to save your downloads
- **Real-time Progress**: Live download progress with percentage tracking
- **Built-in Updater**: Keep yt-dlp up-to-date with one click
- **Clear Log**: Clean log output to keep workspace organized
- **Playlist Support**: Download entire playlists with one click
- **Cancel Downloads**: Stop downloads in progress at any time
- **Speed Limiting**: Throttle download speed to save bandwidth
- **Settings Persistence**: Automatically saves your preferences
- **Keyboard Shortcuts**: Quick actions with comprehensive keyboard shortcuts
- **Clipboard Auto-Detection**: Automatically detects and pastes URLs from clipboard
- **URL Validation**: Validates URLs before attempting download
- **Full Accessibility**: WCAG AA compliant with complete screen reader and keyboard support

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
- **Video Format**: Choose output video container/format (MP4, MKV, WEBM, AVI, FLV, or Auto)
- **Audio Format**: Choose audio format when extracting audio only
- **Extract Audio Only**: Download only the audio track
- **Download Subtitles**: Save available subtitles
- **Auto-generated Subtitles**: Include auto-generated captions
- **Download Thumbnail**: Save video thumbnail image
- **Save Description**: Save video description as text file
- **Download Playlist**: Download entire playlist (if URL is a playlist)
- **Speed Limit**: Set maximum download speed in KB/s (0 = unlimited)

## Keyboard Shortcuts

- **Ctrl+V**: Paste URL from clipboard (when a valid URL is detected)
- **Enter**: Start download (when URL field is focused)
- **Ctrl+L**: Clear log output
- **Alt+D**: Start download
- **Alt+C**: Cancel download (when download is in progress)
- **Alt+U**: Update yt-dlp
- **Alt+B**: Browse for output directory
- **Alt+Q**: Select video quality
- **Alt+F**: Select video format
- **Alt+A**: Select audio format
- **Alt+E**: Toggle extract audio only
- **Alt+S**: Toggle download subtitles
- **Alt+G**: Toggle auto-generated subtitles
- **Alt+T**: Toggle download thumbnail
- **Alt+D**: Toggle save description
- **Alt+P**: Toggle download playlist
- **Alt+L**: Set speed limit
- **Tab**: Navigate between controls in logical order

## Accessibility Features

This application is designed with comprehensive accessibility support to ensure all users can effectively use the software:

### Screen Reader Support
- **Accessible Names**: All interactive controls have descriptive accessible names for screen readers
- **Accessible Descriptions**: Detailed descriptions explain the purpose of each control
- **Status Announcements**: Important status changes (downloads starting, errors, completion) are announced to screen readers
- **Semantic Labels**: Text labels are properly associated with their controls using buddy relationships

### Keyboard Navigation
- **Full Keyboard Access**: All functions can be accessed without a mouse
- **Keyboard Shortcuts**: Comprehensive set of Alt+key mnemonics for all buttons and controls
- **Logical Tab Order**: Tab navigation follows a natural top-to-bottom, left-to-right flow
- **Focus Management**: Focus automatically moves to relevant fields on errors for quick correction
- **Visual Focus Indicators**: Clear, high-contrast focus outlines on all interactive elements

### Visual Accessibility
- **WCAG AA Compliant Colors**: All text and UI elements meet WCAG 2.1 AA contrast requirements (4.5:1 ratio)
- **Enhanced Focus Indicators**: Thick, visible outlines with offset for clear focus visibility
- **No Emoji Dependency**: Status messages use text-based indicators ([INFO], [ERROR], [SUCCESS]) instead of emoji
- **Readable Fonts**: Clear, legible fonts with appropriate sizing
- **High DPI Support**: Proper scaling on high-resolution displays

### User Control
- **Tooltips**: Helpful tooltips on all controls explaining their function
- **Clear Error Messages**: Descriptive error messages with recovery guidance
- **Minimum Window Size**: Ensures UI remains usable and doesn't become too small
- **Settings Persistence**: All preferences saved between sessions

### Error Handling
- **Focus on Error**: When validation fails, focus automatically returns to the problematic field
- **Text Selection**: Invalid input is automatically selected for easy correction
- **Clear Feedback**: Error messages clearly explain what went wrong and how to fix it

This application follows accessibility best practices and aims to be usable by everyone, including:
- Screen reader users (NVDA, JAWS, Narrator)
- Keyboard-only users
- Users with low vision
- Users with motor impairments
- Users who need high contrast

## New Features Details

### Cancel Downloads
Click the "Cancel" button that appears during download to stop the current operation. The download will be terminated gracefully.

### Playlist Support
Enable "Download Playlist" checkbox to download all videos from a playlist URL. The app automatically detects playlists.

### Speed Limiting
Set a download speed limit to avoid saturating your bandwidth. Useful when you need to use the internet for other tasks while downloading.

### Settings Persistence
All your preferences (quality, audio format, checkboxes, output directory, etc.) are automatically saved and restored when you reopen the application.

### Clipboard Auto-Detection
The app monitors your clipboard and automatically detects valid video URLs. If the URL field is empty, it will auto-paste the detected URL for convenience.

### Video Format Selection
Choose your preferred video container format (MP4, MKV, WEBM, AVI, or FLV). The app will automatically merge and re-encode the video to your selected format. Use "Auto (Best)" to let yt-dlp choose the best available format without conversion.
