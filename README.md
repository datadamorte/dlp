# yt-dlp GUI

A desktop app for [yt-dlp](https://github.com/yt-dlp/yt-dlp) — download video and audio from YouTube and many other sites without using the command line.

Built with **Python** and **PyQt5**, with a dark Catppuccin Mocha–inspired theme.

## Features

| Area | What you get |
|------|----------------|
| **Downloads** | Quality presets (best, 1080p, 720p, 480p, 360p, audio-only), container choice (MP4 / MKV / WEBM), playlists |
| **Audio** | Extract audio only as mp3, m4a, wav, or flac |
| **Extras** | Subtitles, auto-generated captions, thumbnails, video descriptions |
| **Control** | Custom save folder, speed limit (KB/s), cancel in progress |
| **Auth** | Optional browser cookies (Chrome, Firefox, Safari, Edge, Brave, Opera) for 403 / restricted videos |
| **UX** | Live progress bar and log, clipboard URL detection, keyboard shortcuts |
| **Updates** | Auto-updates yt-dlp on launch; manual **Update yt-dlp** button anytime |

Works on **Windows**, **macOS**, and **Linux**.

## Requirements

- **Python 3.10+** (yt-dlp has deprecated 3.9)
- Dependencies from `requirements.txt` (PyQt5, yt-dlp, requests)
- **ffmpeg** (recommended) — needed to merge separate video/audio streams into one file

The app will download a `yt-dlp` binary if none is found, and checks for yt-dlp updates every time it starts.

## Quick start

### 1. Clone and enter the project

```bash
cd dlp   # or your clone path
```

### 2. Create a virtual environment

**macOS / Linux:**

```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (Command Prompt):**

```cmd
python -m venv venv
venv\Scripts\activate
```

Or run `setup.bat` on Windows to create the venv and install dependencies in one step.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run

```bash
python yt_dlp_gui.py
```

On first launch (or if `yt-dlp` is missing), the app installs it automatically. On later launches it runs a background update check so you stay current.

## Usage

1. Activate the virtual environment (if it isn’t already).
2. Start the app: `python yt_dlp_gui.py`
3. Paste a URL (or copy one — clipboard detection may fill the field for you).
4. Pick quality, container, and any extras.
5. Choose the save location if needed.
6. Click **START DOWNLOAD**. Use **CANCEL** to stop a run in progress.

## Options

| Control | Description |
|---------|-------------|
| **Quality Profile** | Cap resolution or pick audio-only (`Best Quality`, `1080p`, `720p`, `480p`, `360p`, `Audio Only`) |
| **Container** | Output container when downloading video: `Auto (Best)`, `MP4`, `MKV`, `WEBM` |
| **Audio Format** | Used with **Extract Audio**: `mp3`, `m4a`, `wav`, `flac` |
| **Speed Limit** | Max download speed in KB/s (`Unlimited` when set to 0) |
| **Use Cookies** | Browser whose cookies yt-dlp should use (helps with 403 / login walls) |
| **Extract Audio** | Download only the audio track |
| **Download Subtitles** | Save available subtitles |
| **Auto-Subs** | Include auto-generated captions |
| **Thumbnail** | Save the video thumbnail |
| **Description** | Save the description as a text file |
| **Process Playlist** | If the URL is a playlist, download all entries instead of a single video |

Settings such as the last output directory are remembered between sessions.

## Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl+V** | Paste URL from clipboard |
| **Enter** | Start download (when the URL field is focused) |
| **Ctrl+L** | Clear the log |

## Project layout

```
dlp/
├── yt_dlp_gui.py      # Main application
├── requirements.txt   # Python dependencies
├── setup.bat          # Windows one-shot setup
├── yt-dlp / yt-dlp.exe  # Optional local binary (auto-managed)
└── README.md
```

## Troubleshooting

### HTTP 403 Forbidden

YouTube (and some other sites) may block anonymous or bot-like clients.

1. Set **Use Cookies** to a browser where you are logged in (e.g. Safari, Chrome, Firefox).
2. Keep that browser closed or unlocked as needed for cookie access on your OS.
3. Retry the download — yt-dlp will use that browser’s cookies.

### “ffmpeg is not installed” / formats won’t merge

Install ffmpeg and ensure it is on your `PATH`:

**macOS:**

```bash
brew install ffmpeg
```

**Linux (Debian/Ubuntu):**

```bash
sudo apt install ffmpeg
```

**Linux (Fedora):**

```bash
sudo dnf install ffmpeg
```

**Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add the `bin` folder to your system `PATH`.

### Startup update failed

If the log says the startup update was skipped, downloads still work. Fix network access or click **Update yt-dlp** later. You can also install or upgrade manually:

```bash
pip install -U yt-dlp
```

### Python version warning

Use **Python 3.10 or newer**. Older versions may work poorly or fail with current yt-dlp releases.

### yt-dlp missing entirely

Place a binary named `yt-dlp` (or `yt-dlp.exe` on Windows) next to `yt_dlp_gui.py`, install via pip, or let the app download it from the [yt-dlp releases](https://github.com/yt-dlp/yt-dlp/releases) page on first run.

## License

This project is a thin GUI around [yt-dlp](https://github.com/yt-dlp/yt-dlp). Respect the terms of service of sites you download from, and local copyright law.
