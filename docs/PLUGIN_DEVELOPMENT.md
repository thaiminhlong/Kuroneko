# Plugin Development Guide

This guide explains how to create plugins for MangaDL.

## Overview

Plugins extend MangaDL to support different manga websites. Each plugin is responsible for:

1. **URL Matching**: Determining if a URL belongs to the plugin's supported site(s)
2. **Metadata Fetching**: Retrieving manga info (title, chapters, translation teams)
3. **Options**: Defining UI fields for user configuration
4. **Downloading**: Fetching and saving manga pages

## Plugin Structure

Plugins can be either:
- **Package**: A directory with `plugin.py` inside
- **Single file**: A `.py` file directly in the `plugins/` folder

### Package Structure (Recommended)

```
plugins/
└── my_plugin/
    ├── __init__.py      # Optional, can export plugin class
    ├── plugin.py        # Required, contains the plugin class
    └── utils.py         # Optional, helper modules
```

### Single File Structure

```
plugins/
└── my_plugin.py         # Contains the plugin class
```

## Plugin Interface

All plugins must subclass `PluginInterface` and implement required methods.

### Required Metadata

```python
from core.plugin_interface import PluginInterface, PLUGIN_API_VERSION

class MyPlugin(PluginInterface):
    # Must match the app's API version
    PLUGIN_API_VERSION = PLUGIN_API_VERSION  # Currently 1
    
    # Plugin info
    name = "My Plugin"
    version = "1.0.0"
    author = "Your Name"
    description = "Downloads manga from mysite.com"
    
    # Domains this plugin handles
    supported_domains = ["mysite.com", "www.mysite.com"]
    
    # Optional settings
    rate_limit = 1.0  # Seconds between requests
    max_retries = 3
    timeout = 30
```

### Required Methods

#### `can_handle(url: str) -> bool`

Check if the plugin can handle a URL.

```python
def can_handle(self, url: str) -> bool:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc.lower().replace("www.", "")
    return domain in ["mysite.com"]
```

#### `normalize_url(url: str) -> str`

Convert URL to a canonical form.

```python
def normalize_url(self, url: str) -> str:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    # Ensure https, remove trailing slash, etc.
    return f"https://{parsed.netloc}{parsed.path.rstrip('/')}"
```

#### `fetch_manga_info(url: str) -> MangaInfo`

Fetch manga metadata. This is an **async** method.

```python
async def fetch_manga_info(self, url: str) -> MangaInfo:
    import httpx
    from core.models import MangaInfo, Chapter, TranslationTeam
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        
        # Parse HTML/JSON and extract data
        # ...
        
        return MangaInfo(
            title="Manga Title",
            url=url,
            cover_url="https://...",
            description="...",
            author="Author Name",
            chapters=[
                Chapter(
                    id="ch1",
                    number=1.0,
                    title="Chapter 1",
                    url="https://.../chapter/1",
                    translation_team_id="team_a",
                    page_count=20
                ),
                # ... more chapters
            ],
            translation_teams=[
                TranslationTeam(id="team_a", name="Scanlation Group", language="en"),
                # ... more teams
            ]
        )
```

#### `get_options_schema(manga_info: MangaInfo) -> OptionsSchema`

Define UI options for this plugin.

```python
def get_options_schema(self, manga_info: MangaInfo) -> OptionsSchema:
    from core.models import OptionsSchema, OptionField, FieldType
    
    return OptionsSchema(fields=[
        OptionField(
            key="quality",
            label="Image Quality",
            field_type=FieldType.DROPDOWN,
            choices=["High", "Medium", "Low"],
            default="High"
        ),
        OptionField(
            key="create_cbz",
            label="Create CBZ Archive",
            field_type=FieldType.CHECKBOX,
            default=False
        ),
        OptionField(
            key="concurrent_pages",
            label="Concurrent Page Downloads",
            field_type=FieldType.NUMBER,
            default=3,
            min_value=1,
            max_value=10
        ),
    ])
```

#### `build_download_plan(url, manga_info, selection, options) -> DownloadPlan`

Create a download plan based on user selection.

```python
async def build_download_plan(
    self,
    url: str,
    manga_info: MangaInfo,
    selection: UserSelection,
    options: dict
) -> DownloadPlan:
    # Filter chapters based on selection
    chapters = selection.chapters_in_range(manga_info.chapters)
    
    return DownloadPlan(
        manga_title=manga_info.title,
        chapters=chapters,
        options=options
    )
```

#### `download(plan, progress_callback, cancel_token) -> None`

Execute the download. This is an **async** method.

```python
async def download(
    self,
    plan: DownloadPlan,
    progress_callback: callable,
    cancel_token: CancelToken
) -> None:
    import httpx
    from pathlib import Path
    
    output_dir = Path(plan.output_dir) / self._sanitize(plan.manga_title)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    async with httpx.AsyncClient() as client:
        for chapter in plan.chapters:
            # Check for cancellation
            cancel_token.check()  # Raises CancelledException if cancelled
            
            chapter_dir = output_dir / f"Chapter_{chapter.number}"
            chapter_dir.mkdir(exist_ok=True)
            
            # Fetch page URLs for this chapter
            page_urls = await self._get_page_urls(client, chapter.url)
            
            for page_num, page_url in enumerate(page_urls, 1):
                cancel_token.check()
                
                # Download page
                response = await client.get(page_url)
                page_path = chapter_dir / f"{page_num:03d}.jpg"
                page_path.write_bytes(response.content)
                
                # Report progress
                progress_callback(
                    chapter.number,      # Current chapter
                    page_num,            # Current page
                    len(page_urls),      # Total pages in chapter
                    len(response.content),  # Bytes downloaded
                    "1.2 MB/s"           # Speed string
                )
                
                # Rate limiting
                await asyncio.sleep(self.rate_limit)
```

## Data Models

### MangaInfo

```python
@dataclass
class MangaInfo:
    title: str
    url: str
    cover_url: Optional[str] = None
    description: str = ""
    author: str = ""
    artist: str = ""
    status: str = ""  # "ongoing", "completed", "hiatus"
    chapters: list[Chapter] = field(default_factory=list)
    translation_teams: list[TranslationTeam] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
```

### Chapter

```python
@dataclass
class Chapter:
    id: str                              # Unique identifier
    number: float                        # Chapter number (can be 1.5)
    title: str = ""                      # Chapter title
    url: str = ""                        # Chapter page URL
    translation_team_id: Optional[str] = None
    language: str = "en"
    page_count: Optional[int] = None
```

### TranslationTeam

```python
@dataclass
class TranslationTeam:
    id: str              # Unique identifier
    name: str            # Display name
    language: str = "en"
```

### OptionField Types

| Type | Widget | Properties |
|------|--------|------------|
| `TEXT` | QLineEdit | `default` |
| `NUMBER` | QSpinBox | `default`, `min_value`, `max_value`, `step` |
| `DROPDOWN` | QComboBox | `choices`, `default` |
| `CHECKBOX` | QCheckBox | `default` (bool) |
| `RANGE` | QSlider | `min_value`, `max_value`, `step` |

### CancelToken

Used for cooperative cancellation:

```python
def download(self, ..., cancel_token: CancelToken):
    for item in items:
        # Raises CancelledException if user clicked Cancel
        cancel_token.check()
        
        # Or check manually
        if cancel_token.is_cancelled:
            return
        
        # Blocks if user clicked Pause (unblocks on Resume)
        cancel_token.check()
```

## Best Practices

### 1. Use Async Networking

Prefer `httpx` or `aiohttp` for non-blocking requests:

```python
import httpx

async def fetch_manga_info(self, url: str) -> MangaInfo:
    async with httpx.AsyncClient(timeout=self.timeout) as client:
        response = await client.get(url)
        # ...
```

### 2. Handle Errors Gracefully

```python
async def fetch_manga_info(self, url: str) -> MangaInfo:
    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        raise ValueError(f"Server returned {e.response.status_code}")
    except httpx.RequestError as e:
        raise ConnectionError(f"Failed to connect: {e}")
```

### 3. Respect Rate Limits

```python
async def download(self, ...):
    for page in pages:
        await self._download_page(page)
        await asyncio.sleep(self.rate_limit)  # Be nice to servers
```

### 4. Use Retries

```python
async def _download_with_retry(self, client, url, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
        except httpx.HTTPError:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### 5. Sanitize Filenames

```python
import re

def _sanitize_filename(self, name: str) -> str:
    # Remove invalid characters
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    # Replace multiple spaces
    name = re.sub(r'\s+', ' ', name)
    # Limit length
    return name[:100].strip()
```

### 6. Support User-Agent Customization

```python
async def _get_client(self) -> httpx.AsyncClient:
    user_agent = self.settings.get("user_agent") or "MangaDL/1.0"
    return httpx.AsyncClient(
        headers={"User-Agent": user_agent},
        timeout=self.timeout
    )
```

## Translation Teams

The UI shows a dropdown for selecting translation teams. Populate this by:

```python
async def fetch_manga_info(self, url: str) -> MangaInfo:
    # Fetch chapters with team info
    chapters = []
    teams_seen = {}
    
    for ch_data in chapter_list:
        team_id = ch_data["group_id"]
        team_name = ch_data["group_name"]
        
        if team_id not in teams_seen:
            teams_seen[team_id] = TranslationTeam(
                id=team_id,
                name=team_name,
                language=ch_data.get("language", "en")
            )
        
        chapters.append(Chapter(
            id=ch_data["id"],
            number=ch_data["chapter"],
            translation_team_id=team_id,
            # ...
        ))
    
    return MangaInfo(
        # ...
        chapters=chapters,
        translation_teams=list(teams_seen.values())
    )
```

## Plugin Template

Copy this template to get started:

```python
"""
MyManga Plugin - Downloads from mymanga.com
"""
import asyncio
from urllib.parse import urlparse

import httpx

from core.plugin_interface import PluginInterface, PLUGIN_API_VERSION
from core.models import (
    MangaInfo, Chapter, TranslationTeam,
    UserSelection, DownloadPlan, OptionsSchema,
    OptionField, FieldType, CancelToken
)


class MyMangaPlugin(PluginInterface):
    """Plugin for mymanga.com"""
    
    PLUGIN_API_VERSION = PLUGIN_API_VERSION
    name = "MyManga"
    version = "1.0.0"
    author = "Your Name"
    description = "Downloads manga from mymanga.com"
    supported_domains = ["mymanga.com", "www.mymanga.com"]
    
    rate_limit = 1.0
    max_retries = 3
    timeout = 30
    
    def can_handle(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace("www.", "")
            return domain == "mymanga.com"
        except Exception:
            return False
    
    def normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"https://mymanga.com{parsed.path.rstrip('/')}"
    
    async def fetch_manga_info(self, url: str) -> MangaInfo:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            # TODO: Parse response and extract manga info
            # data = response.json()  # or parse HTML
            
            return MangaInfo(
                title="TODO",
                url=url,
                chapters=[],
                translation_teams=[]
            )
    
    def get_options_schema(self, manga_info: MangaInfo) -> OptionsSchema:
        return OptionsSchema(fields=[
            OptionField(
                key="quality",
                label="Quality",
                field_type=FieldType.DROPDOWN,
                choices=["Original", "Compressed"],
                default="Original"
            )
        ])
    
    async def build_download_plan(
        self,
        url: str,
        manga_info: MangaInfo,
        selection: UserSelection,
        options: dict
    ) -> DownloadPlan:
        chapters = selection.chapters_in_range(manga_info.chapters)
        return DownloadPlan(
            manga_title=manga_info.title,
            chapters=chapters,
            options=options
        )
    
    async def download(
        self,
        plan: DownloadPlan,
        progress_callback: callable,
        cancel_token: CancelToken
    ) -> None:
        from pathlib import Path
        
        output_dir = Path(plan.output_dir) / plan.manga_title
        output_dir.mkdir(parents=True, exist_ok=True)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for chapter in plan.chapters:
                cancel_token.check()
                
                # TODO: Implement actual download logic
                # 1. Fetch page URLs
                # 2. Download each page
                # 3. Save to disk
                # 4. Report progress
                
                pass
```

## Testing Your Plugin

1. Place your plugin in the `plugins/` directory
2. Run MangaDL
3. Go to the Plugins page
4. Check for load errors
5. Use the "Test URL" box to verify URL matching
6. Try a full download

## Debugging

Enable debug logging in your plugin:

```python
from core.event_bus import EventBus

class MyPlugin(PluginInterface):
    def __init__(self):
        super().__init__()
        self.event_bus = EventBus()
    
    def _log(self, message: str, level: str = "info"):
        self.event_bus.emit_log(level, f"[{self.name}] {message}")
    
    async def download(self, ...):
        self._log("Starting download...")
        # ...
        self._log(f"Downloaded {count} pages")
```

## Publishing

To share your plugin:

1. Create a GitHub repository
2. Include:
   - `plugin.py` (main plugin code)
   - `README.md` (installation and usage)
   - `requirements.txt` (if extra dependencies needed)
3. Tag releases with version numbers
4. Share the repository URL
