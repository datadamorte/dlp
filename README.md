# yt-dlp GUI

A desktop app for [yt-dlp](https://github.com/yt-dlp/yt-dlp) — download video and audio from YouTube and many other sites without using the command line.

Built with **Python** and **PyQt5**. Dark, compact desktop UI with a native menu bar, live progress, and an activity log.

## Features

| Area | What you get |
|------|----------------|
| **Downloads** | Quality presets (best, 1080p, 720p, 480p, 360p, audio-only), container remux (MP4 / MKV / WEBM), optional re-encode |
| **Audio** | Extract audio only as mp3, m4a, wav, or flac |
| **Extras** | Subtitles, auto-generated captions, thumbnails, video descriptions |
| **Playlists** | Optional full-playlist download, start/end range, one folder per playlist |
| **Control** | Custom save folder, speed limit (KB/s), cancel in progress (Esc) |
| **Auth** | Optional browser cookies (Chrome, Firefox, Safari, Edge, Brave, Opera) for 403 / restricted videos |
| **UX** | Live progress (percent, speed, ETA), activity log, clipboard URL detection, drag-and-drop URLs, Reveal folder |
| **Updates** | Auto-updates yt-dlp on launch; **Check for updates** in the header or Help menu anytime |

Works on **Windows**, **macOS**, and **Linux**.

## Requirements

- **Python 3.10+** (yt-dlp has deprecated 3.9)
- Dependencies from `requirements.txt` (PyQt5, yt-dlp)
- **ffmpeg** (recommended) — needed to merge separate video/audio streams into one file

The app will download a `yt-dlp` binary if none is found, and checks for yt-dlp updates every time it starts. A warning is shown if ffmpeg is missing.

## Quick start

### 1. Clone and enter the project

```bash
cd dlp   # or your clone path
```

### 2. Create a virtual environment

**macOS / Linux:**

```bash
chmod +x setup.sh
./setup.sh
```

Or manually:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Windows (Command Prompt):**

```cmd
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Or run `setup.bat` on Windows to create the venv and install dependencies in one step.

### 3. Run

```bash
python yt_dlp_gui.py
```

On first launch (or if `yt-dlp` is missing), the app installs it automatically in the background. On later launches it runs a background update check so you stay current.

### Tests

```bash
python -m unittest discover -s . -p 'test_*.py'
```

## Usage

1. Activate the virtual environment (if it isn’t already).
2. Start the app: `python yt_dlp_gui.py`
3. Paste a URL, drop one onto the window, or copy one — clipboard detection may fill the field if it is empty.
4. Pick quality, container, and any extras.
5. Choose the save location if needed.
6. Click **Download**. Use **Cancel** or **Esc** to stop a run in progress.

## Options

| Control | Description |
|---------|-------------|
| **Quality** | Cap resolution or pick audio-only (`Best Quality`, `1080p`, `720p`, `480p`, `360p`, `Audio Only`) |
| **Container** | Remux output when downloading video: `Auto (Best)`, `MP4`, `MKV`, `WEBM` (no re-encode unless you opt in) |
| **Re-encode container** | Force ffmpeg re-encode into the chosen container. Slower; only needed if remux fails |
| **Audio** | Used with **Extract audio** or **Audio Only**: `mp3`, `m4a`, `wav`, `flac` |
| **Rate limit** | Max download speed in KB/s (`No limit` when set to 0) |
| **Cookies** | Browser whose cookies yt-dlp should use (helps with 403 / login walls) |
| **Extract audio** | Download only the audio track |
| **Subtitles** | Save available subtitles |
| **Auto-captions** | Include auto-generated captions (works even if official subs are off) |
| **Thumbnail** | Save the video thumbnail |
| **Description** | Save the description as a text file |
| **Download playlist** | If the URL is a playlist, download all entries instead of a single video |
| **From / to** | 1-based index range when a playlist is enabled (`Start` / `End` = unbounded) |

Video files are saved as `Title [id].ext` to avoid overwriting same-named videos. Playlists go into a subfolder named after the playlist.

Settings such as the last output directory are remembered between sessions.

## Keyboard shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl+V** | Paste into the focused field (URL field accepts a copied link) |
| **Ctrl+Shift+V** | Paste a URL from the clipboard into the URL field |
| **Enter** | Start download (when the URL field is focused) |
| **Ctrl+Enter** | Start download from anywhere in the window |
| **Esc** | Cancel the download in progress |
| **Ctrl+L** | Clear the activity log |
| **Ctrl+O** | Reveal the save folder |
| **Ctrl+Shift+O** | Choose a save folder |

## Project layout

```
dlp/
├── yt_dlp_gui.py      # Desktop GUI
├── ytdlp_core.py      # Command building, path lookup, progress parsing
├── test_ytdlp_core.py # Unit tests (no network)
├── requirements.txt   # Python dependencies
├── setup.sh           # macOS / Linux one-shot setup
├── setup.bat          # Windows one-shot setup
├── yt-dlp / yt-dlp.exe  # Optional local binary (auto-managed)
└── README.md
```

## Troubleshooting

### HTTP 403 Forbidden

YouTube (and some other sites) may block anonymous or bot-like clients.

1. Set **Cookies** to a browser where you are logged in (e.g. Safari, Chrome, Firefox).
2. Keep that browser closed or unlocked as needed for cookie access on your OS.
3. Retry the download — yt-dlp will use that browser’s cookies.

### “ffmpeg is not installed” / formats won’t merge

The app warns on startup if ffmpeg is missing. Install it and ensure it is on your `PATH`:

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

If a chosen container fails to remux, enable **Re-encode container** (slower, re-encodes video).

### Startup update failed

If the log says the startup update was skipped, downloads still work. Fix network access or click **Check for updates** later. You can also install or upgrade manually:

```bash
pip install -U yt-dlp
```

### Python version warning

Use **Python 3.10 or newer**. Older versions may work poorly or fail with current yt-dlp releases.

### yt-dlp missing entirely

Place a binary named `yt-dlp` (or `yt-dlp.exe` on Windows) next to `yt_dlp_gui.py`, install via pip, or let the app download it from the [yt-dlp releases](https://github.com/yt-dlp/yt-dlp/releases) page on first run.

## License

This project is a thin GUI around [yt-dlp](https://github.com/yt-dlp/yt-dlp). Respect the terms of service of sites you download from, and local copyright law.
