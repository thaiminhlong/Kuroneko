# MangaDL - Manga Downloader

A modern desktop application for downloading manga with a plugin-based architecture.

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)
![PySide6](https://img.shields.io/badge/GUI-PySide6-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## Features

- **Plugin-based architecture**: Support any manga website through plugins
- **Batch downloads**: Add multiple URLs at once
- **Queue management**: Pause, resume, and cancel downloads
- **Translation team selection**: Choose which scanlation group's version to download
- **Chapter range selection**: Download specific chapter ranges
- **Plugin options**: Each plugin can expose custom options (quality, format, etc.)
- **Dark theme**: Modern UI with orange accents
- **Async downloads**: Non-blocking UI with concurrent downloads

## Screenshots

The application features:
- Left sidebar navigation (Queue, History, Plugins, Settings)
- URL input with batch support
- Task queue with progress tracking
- Details panel for per-task configuration
- Log console for monitoring

## Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Setup

1. Clone or download the application:

```bash
cd manga_downloader
```

2. Create a virtual environment (recommended):

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the application:

```bash
python main.py
```

## Usage

### Adding Downloads

1. **Paste URLs**: Enter manga URLs in the text area (one per line)
2. **Import file**: Click "Import .txt" to load URLs from a text file
3. **Add to Queue**: Click "Add to Queue" to add the URLs

### Managing Downloads

1. **Select a task** from the queue to view details
2. **Fetch Info**: Click to retrieve manga metadata from the website
3. **Configure options**:
   - Set chapter range (start/end)
   - Select translation team
   - Adjust plugin-specific options
4. **Download**: Click "Download" to start

### Keyboard Shortcuts

- `Ctrl+V` in URL input: Paste from clipboard
- Select task + `Delete`: Remove from queue

## Architecture

```
manga_downloader/
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
├── settings.json        # User settings (auto-generated)
│
├── core/                # Core logic (no UI dependencies)
│   ├── __init__.py
│   ├── models.py        # Data models (Task, MangaInfo, etc.)
│   ├── plugin_interface.py  # Plugin base class
│   ├── plugin_manager.py    # Plugin discovery & loading
│   ├── task_manager.py      # Download queue management
│   └── event_bus.py         # Event system for UI updates
│
├── ui/                  # PySide6 UI components
│   ├── __init__.py
│   ├── main_window.py   # Main window with navigation
│   ├── styles.py        # Theme and styling
│   └── pages/
│       ├── queue_page.py    # Main download queue
│       ├── history_page.py  # Completed downloads
│       ├── plugins_page.py  # Plugin management
│       └── settings_page.py # App settings
│
└── plugins/             # Plugin directory
    └── example_httpx/   # Example plugin
        ├── __init__.py
        └── plugin.py
```

### Key Components

| Component | Responsibility |
|-----------|----------------|
| **PluginManager** | Discovers, loads, and manages plugins |
| **TaskManager** | Manages download queue, runs async downloads |
| **EventBus** | Thread-safe communication between workers and UI |
| **PluginInterface** | Abstract base class for all plugins |

### State Machine

Tasks flow through these states:

```
QUEUED → VALIDATING → READY → DOWNLOADING → COMPLETED
                ↓           ↓              ↓
              FAILED      PAUSED ←→ DOWNLOADING
                            ↓
                        CANCELED
```

## Plugin System

Plugins extend MangaDL to support different manga websites. Each plugin:
- Handles URL matching for its supported domains
- Fetches manga metadata (title, chapters, teams)
- Defines custom options for the UI
- Performs the actual download

See [PLUGIN_DEVELOPMENT.md](docs/PLUGIN_DEVELOPMENT.md) for the full plugin development guide.

### Quick Plugin Example

```python
from core.plugin_interface import PluginInterface, PLUGIN_API_VERSION
from core.models import MangaInfo, OptionsSchema

class MyPlugin(PluginInterface):
    PLUGIN_API_VERSION = PLUGIN_API_VERSION
    name = "My Plugin"
    version = "1.0.0"
    supported_domains = ["example.com"]
    
    def can_handle(self, url: str) -> bool:
        return "example.com" in url
    
    async def fetch_manga_info(self, url: str) -> MangaInfo:
        # Fetch and parse manga page
        ...
    
    async def download(self, plan, progress_cb, cancel_token):
        # Download chapters
        ...
```

## Building Standalone Executable

Use PyInstaller to create a standalone executable:

```bash
pip install pyinstaller

# Windows
pyinstaller --name MangaDL --windowed --onedir main.py

# Add plugins folder to dist
xcopy /E /I plugins dist\MangaDL\plugins
```

### PyInstaller Spec File

For more control, create `MangaDL.spec`:

```python
# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('plugins', 'plugins'),
    ],
    hiddenimports=['httpx', 'aiohttp'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MangaDL',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MangaDL',
)
```

Build with: `pyinstaller MangaDL.spec`

## Configuration

Settings are stored in `settings.json`:

| Setting | Description | Default |
|---------|-------------|---------|
| `download_folder` | Where to save downloads | `~/Downloads/MangaDL` |
| `max_parallel_downloads` | Concurrent downloads | `3` |
| `retry_count` | Retries on failure | `3` |
| `timeout` | Request timeout (seconds) | `30` |
| `rate_limit` | Delay between requests | `0.5` |

## Troubleshooting

### Plugin not loading

1. Check the Plugins page for load errors
2. Ensure plugin has `PLUGIN_API_VERSION = 1`
3. Check the plugin's `plugin.py` has a class extending `PluginInterface`

### Downloads failing

1. Check the log console for error messages
2. Verify the URL is correct and accessible
3. Try increasing timeout in Settings
4. Some sites may require specific headers or cookies

### UI freezing

This shouldn't happen with the async architecture. If it does:
1. Check if a plugin is using synchronous networking
2. Reduce `max_parallel_downloads`
3. Report the issue with reproduction steps

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.
