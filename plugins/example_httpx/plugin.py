"""
Example plugin demonstrating the plugin interface.
Handles example.com URLs and simulates manga downloads.

This is a reference implementation showing:
- URL matching and normalization
- Async metadata fetching with httpx
- Options schema for UI generation
- Download with progress callbacks
"""
import asyncio
import random
import re
from pathlib import Path
from urllib.parse import urlparse

import httpx

from core.plugin_interface import PluginInterface, PLUGIN_API_VERSION
from core.models import (
    MangaInfo, Chapter, TranslationTeam,
    UserSelection, DownloadPlan, OptionsSchema,
    OptionField, FieldType, CancelToken
)


class ExamplePlugin(PluginInterface):
    """
    Example plugin for demonstration purposes.
    Simulates downloading from example.com.
    """
    
    # Required metadata
    PLUGIN_API_VERSION = PLUGIN_API_VERSION
    name = "Example Plugin"
    version = "1.0.0"
    author = "MangaDL Team"
    description = "Demo plugin that simulates manga downloads from example.com"
    supported_domains = ["example.com", "manga.example.com", "www.example.com"]
    
    # Plugin settings
    rate_limit = 0.5
    max_retries = 3
    timeout = 30
    
    def __init__(self):
        super().__init__()
        self._client: httpx.AsyncClient | None = None
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "MangaDL/1.0 (Example Plugin)"
                }
            )
        return self._client
    
    def can_handle(self, url: str) -> bool:
        """Check if this plugin can handle the URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix for matching
            if domain.startswith("www."):
                domain = domain[4:]
            
            return any(
                domain == d or domain.endswith("." + d)
                for d in self.supported_domains
            )
        except Exception:
            return False
    
    def normalize_url(self, url: str) -> str:
        """Normalize the URL to a canonical form."""
        parsed = urlparse(url)
        
        # Ensure https
        scheme = "https"
        
        # Normalize domain
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        
        # Clean path
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"
        
        return f"{scheme}://{netloc}{path}"
    
    async def fetch_manga_info(self, url: str) -> MangaInfo:
        """
        Fetch metadata about a manga.
        
        In a real plugin, this would:
        1. Make HTTP requests to the manga page
        2. Parse the HTML/JSON response
        3. Extract title, chapters, etc.
        
        This demo simulates the response.
        """
        # Simulate network delay
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
        # Extract manga "slug" from URL for demo purposes
        parsed = urlparse(url)
        path_parts = [p for p in parsed.path.split("/") if p]
        manga_slug = path_parts[-1] if path_parts else "sample-manga"
        
        # Convert slug to title
        title = manga_slug.replace("-", " ").title()
        
        # Generate demo chapters (1-50)
        chapters = []
        for i in range(1, 51):
            # Randomly assign to translation teams
            team_id = random.choice(["team_a", "team_b", "team_c"])
            chapters.append(Chapter(
                id=f"ch_{i}",
                number=float(i),
                title=f"Chapter {i}: The Adventure Continues",
                url=f"{url}/chapter/{i}",
                translation_team_id=team_id,
                language="en",
                page_count=random.randint(15, 40)
            ))
        
        # Add some .5 chapters
        for base in [10, 25, 40]:
            chapters.append(Chapter(
                id=f"ch_{base}_5",
                number=base + 0.5,
                title=f"Chapter {base}.5: Side Story",
                url=f"{url}/chapter/{base}.5",
                translation_team_id="team_a",
                language="en",
                page_count=random.randint(10, 20)
            ))
        
        chapters.sort(key=lambda c: c.number)
        
        # Demo translation teams
        teams = [
            TranslationTeam(id="team_a", name="Speed Scans", language="en"),
            TranslationTeam(id="team_b", name="Quality Translations", language="en"),
            TranslationTeam(id="team_c", name="Fan TL Group", language="en"),
        ]
        
        return MangaInfo(
            title=title,
            url=url,
            cover_url=f"https://via.placeholder.com/300x450?text={manga_slug}",
            description=f"This is a demo manga '{title}' for testing the plugin system.",
            author="Demo Author",
            artist="Demo Artist",
            status="ongoing",
            chapters=chapters,
            translation_teams=teams,
        )
    
    def get_options_schema(self, manga_info: MangaInfo) -> OptionsSchema:
        """
        Define plugin-specific options.
        
        These generate UI fields in the details panel.
        """
        return OptionsSchema(fields=[
            OptionField(
                key="image_quality",
                label="Image Quality",
                field_type=FieldType.DROPDOWN,
                choices=["Original", "High", "Medium", "Low"],
                default="Original",
                description="Quality of downloaded images"
            ),
            OptionField(
                key="image_format",
                label="Image Format",
                field_type=FieldType.DROPDOWN,
                choices=["Keep Original", "PNG", "JPEG", "WebP"],
                default="Keep Original",
                description="Convert images to this format"
            ),
            OptionField(
                key="create_cbz",
                label="Create CBZ",
                field_type=FieldType.CHECKBOX,
                default=False,
                description="Package chapters as CBZ archives"
            ),
            OptionField(
                key="download_covers",
                label="Download Covers",
                field_type=FieldType.CHECKBOX,
                default=True,
                description="Download chapter cover images"
            ),
            OptionField(
                key="rate_limit_override",
                label="Rate Limit (seconds)",
                field_type=FieldType.NUMBER,
                default=0.5,
                min_value=0.1,
                max_value=5.0,
                step=0.1,
                description="Delay between requests (0 = use global setting)"
            ),
        ])
    
    async def build_download_plan(
        self,
        url: str,
        manga_info: MangaInfo,
        selection: UserSelection,
        options: dict
    ) -> DownloadPlan:
        """Build a plan for downloading selected chapters."""
        
        # Filter chapters based on selection
        selected_chapters = selection.chapters_in_range(manga_info.chapters)
        
        return DownloadPlan(
            manga_title=manga_info.title,
            chapters=selected_chapters,
            options=options,
            extra={
                "manga_url": url,
                "cover_url": manga_info.cover_url,
            }
        )
    
    async def download(
        self,
        plan: DownloadPlan,
        progress_callback: callable,
        cancel_token: CancelToken
    ) -> None:
        """
        Execute the download plan.
        
        In a real plugin, this would:
        1. Iterate through chapters
        2. Fetch page URLs for each chapter
        3. Download each image
        4. Save to disk
        
        This demo simulates the process.
        """
        output_dir = Path(plan.output_dir) / self._sanitize_filename(plan.manga_title)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        rate_limit = plan.options.get("rate_limit_override", self.rate_limit)
        
        for chapter_idx, chapter in enumerate(plan.chapters):
            # Check cancellation
            cancel_token.check()
            
            chapter_dir = output_dir / f"Chapter_{chapter.number:05.1f}"
            chapter_dir.mkdir(parents=True, exist_ok=True)
            
            # Simulate fetching page list
            page_count = chapter.page_count or random.randint(15, 30)
            
            # Simulate downloading each page
            for page in range(1, page_count + 1):
                cancel_token.check()
                
                # Simulate download time and speed
                download_time = random.uniform(0.05, 0.2)
                await asyncio.sleep(download_time)
                
                # Simulate file size and speed
                file_size = random.randint(100_000, 500_000)  # 100KB - 500KB
                speed = file_size / download_time
                speed_str = self._format_speed(speed)
                
                # Report progress
                progress_callback(
                    chapter.number,
                    page,
                    page_count,
                    file_size,
                    speed_str
                )
                
                # Rate limiting
                if rate_limit > 0:
                    await asyncio.sleep(rate_limit)
                
                # Create a dummy file (in real plugin, save actual image)
                page_file = chapter_dir / f"{page:03d}.jpg"
                page_file.write_text(f"[Simulated image: Chapter {chapter.number}, Page {page}]")
    
    def _sanitize_filename(self, name: str) -> str:
        """Remove invalid characters from filename."""
        # Remove invalid characters
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        # Limit length
        return name[:100].strip()
    
    def _format_speed(self, bytes_per_sec: float) -> str:
        """Format download speed for display."""
        if bytes_per_sec >= 1_000_000:
            return f"{bytes_per_sec / 1_000_000:.1f} MB/s"
        elif bytes_per_sec >= 1_000:
            return f"{bytes_per_sec / 1_000:.1f} KB/s"
        else:
            return f"{bytes_per_sec:.0f} B/s"
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self._client:
            # Note: In async context, would use await client.aclose()
            pass
