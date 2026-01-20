"""
MangaDex plugin for downloading manga from mangadex.org.

Uses the official MangaDex API v5:
- https://api.mangadex.org/docs/

Features:
- Fetch manga metadata, chapters, and scanlation groups
- Language filtering
- Data saver mode for smaller image sizes
- Proper rate limiting to respect API guidelines
- CBZ archive creation option
"""
import asyncio
import re
import zipfile
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional
from datetime import datetime

import httpx

from core.plugin_interface import PluginInterface, PLUGIN_API_VERSION
from core.models import (
    MangaInfo, Chapter, TranslationTeam,
    UserSelection, DownloadPlan, OptionsSchema,
    OptionField, FieldType, CancelToken
)


class MangaDexPlugin(PluginInterface):
    """
    Plugin for downloading manga from MangaDex.
    Uses the official MangaDex API v5.
    """
    
    # Required metadata
    PLUGIN_API_VERSION = PLUGIN_API_VERSION
    name = "MangaDex"
    version = "1.0.0"
    author = "MangaDL Team"
    description = "Download manga from MangaDex using the official API"
    supported_domains = ["mangadex.org", "www.mangadex.org"]
    
    # API configuration
    API_BASE = "https://api.mangadex.org"
    
    # Plugin settings - MangaDex recommends 5 requests/second max
    rate_limit = 0.25  # 250ms between requests
    max_retries = 3
    timeout = 30
    
    # UUID regex pattern
    UUID_PATTERN = re.compile(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
        re.IGNORECASE
    )
    
    def __init__(self):
        super().__init__()
        self._client: Optional[httpx.AsyncClient] = None
        self._groups_cache: dict[str, TranslationTeam] = {}
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
                headers={
                    "User-Agent": "MangaDL/1.0 (MangaDex Plugin)",
                    "Accept": "application/json",
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
            
            # Check domain
            if domain != "mangadex.org":
                return False
            
            # Must be a title URL with UUID
            if "/title/" not in parsed.path:
                return False
            
            # Extract and validate UUID
            uuid = self._extract_manga_id(url)
            return uuid is not None
            
        except Exception:
            return False
    
    def _extract_manga_id(self, url: str) -> Optional[str]:
        """Extract manga UUID from URL."""
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        
        # URL format: /title/{uuid} or /title/{uuid}/slug-name
        if len(path_parts) >= 2 and path_parts[0] == "title":
            potential_uuid = path_parts[1]
            if self.UUID_PATTERN.match(potential_uuid):
                return potential_uuid.lower()
        
        return None
    
    def normalize_url(self, url: str) -> str:
        """Normalize the URL to a canonical form."""
        manga_id = self._extract_manga_id(url)
        if manga_id:
            return f"https://mangadex.org/title/{manga_id}"
        return url
    
    async def fetch_manga_info(self, url: str) -> MangaInfo:
        """
        Fetch metadata about a manga from MangaDex.
        
        Makes API calls to:
        - /manga/{id} for manga metadata
        - /manga/{id}/feed for chapter list
        """
        manga_id = self._extract_manga_id(url)
        if not manga_id:
            raise ValueError(f"Could not extract manga ID from URL: {url}")
        
        client = await self._get_client()
        
        # Fetch manga metadata
        manga_data = await self._fetch_manga_metadata(client, manga_id)
        
        # Fetch all chapters
        chapters, groups = await self._fetch_all_chapters(client, manga_id)
        
        return MangaInfo(
            title=manga_data["title"],
            url=url,
            cover_url=manga_data.get("cover_url"),
            description=manga_data.get("description", ""),
            author=manga_data.get("author", ""),
            artist=manga_data.get("artist", ""),
            status=manga_data.get("status", ""),
            chapters=chapters,
            translation_teams=list(groups.values()),
            extra={
                "manga_id": manga_id,
                "content_rating": manga_data.get("content_rating"),
                "original_language": manga_data.get("original_language"),
            }
        )
    
    async def _fetch_manga_metadata(self, client: httpx.AsyncClient, manga_id: str) -> dict:
        """Fetch manga metadata from the API."""
        url = f"{self.API_BASE}/manga/{manga_id}"
        params = {"includes[]": ["cover_art", "author", "artist"]}
        
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data.get("result") != "ok":
            raise ValueError(f"API error: {data.get('errors', 'Unknown error')}")
        
        manga = data["data"]
        attributes = manga["attributes"]
        
        # Get title (prefer English, fallback to other languages)
        titles = attributes.get("title", {})
        title = (
            titles.get("en") or
            titles.get("ja-ro") or
            titles.get("ja") or
            list(titles.values())[0] if titles else "Unknown"
        )
        
        # Get description
        descriptions = attributes.get("description", {})
        description = descriptions.get("en", "") or list(descriptions.values())[0] if descriptions else ""
        
        # Get author and artist from relationships
        author = ""
        artist = ""
        cover_url = None
        
        for rel in manga.get("relationships", []):
            if rel["type"] == "author" and "attributes" in rel:
                author = rel["attributes"].get("name", "")
            elif rel["type"] == "artist" and "attributes" in rel:
                artist = rel["attributes"].get("name", "")
            elif rel["type"] == "cover_art" and "attributes" in rel:
                filename = rel["attributes"].get("fileName")
                if filename:
                    cover_url = f"https://uploads.mangadex.org/covers/{manga_id}/{filename}"
        
        return {
            "title": title,
            "description": description,
            "author": author,
            "artist": artist,
            "status": attributes.get("status", ""),
            "content_rating": attributes.get("contentRating", ""),
            "original_language": attributes.get("originalLanguage", ""),
            "cover_url": cover_url,
        }
    
    async def _fetch_all_chapters(
        self, 
        client: httpx.AsyncClient, 
        manga_id: str
    ) -> tuple[list[Chapter], dict[str, TranslationTeam]]:
        """Fetch all chapters for a manga with pagination."""
        chapters = []
        groups: dict[str, TranslationTeam] = {}
        offset = 0
        limit = 100
        
        while True:
            url = f"{self.API_BASE}/manga/{manga_id}/feed"
            params = {
                "limit": limit,
                "offset": offset,
                "order[chapter]": "asc",
                "includes[]": ["scanlation_group"],
                "contentRating[]": ["safe", "suggestive", "erotica", "pornographic"],
            }
            
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("result") != "ok":
                break
            
            chapter_list = data.get("data", [])
            if not chapter_list:
                break
            
            for ch_data in chapter_list:
                chapter, group = self._parse_chapter(ch_data)
                if chapter:
                    chapters.append(chapter)
                if group:
                    groups[group.id] = group
            
            # Check if we have more pages
            total = data.get("total", 0)
            offset += limit
            if offset >= total:
                break
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit)
        
        return chapters, groups
    
    def _parse_chapter(self, ch_data: dict) -> tuple[Optional[Chapter], Optional[TranslationTeam]]:
        """Parse a chapter from API response."""
        attributes = ch_data.get("attributes", {})
        
        # Skip external chapters (no pages on MangaDex)
        if attributes.get("externalUrl"):
            return None, None
        
        # Get chapter number
        chapter_num_str = attributes.get("chapter")
        if chapter_num_str is None:
            # Oneshot or unnumbered chapter
            chapter_num = 0.0
        else:
            try:
                chapter_num = float(chapter_num_str)
            except ValueError:
                chapter_num = 0.0
        
        # Get scanlation group
        group = None
        group_id = None
        for rel in ch_data.get("relationships", []):
            if rel["type"] == "scanlation_group":
                group_id = rel["id"]
                if "attributes" in rel:
                    group = TranslationTeam(
                        id=rel["id"],
                        name=rel["attributes"].get("name", "Unknown Group"),
                        language=attributes.get("translatedLanguage", "en")
                    )
                else:
                    group = TranslationTeam(
                        id=rel["id"],
                        name="Unknown Group",
                        language=attributes.get("translatedLanguage", "en")
                    )
                break
        
        # If no group, create a "No Group" placeholder
        if not group:
            group_id = "no_group"
            group = TranslationTeam(
                id="no_group",
                name="No Group",
                language=attributes.get("translatedLanguage", "en")
            )
        
        chapter = Chapter(
            id=ch_data["id"],
            number=chapter_num,
            title=attributes.get("title") or f"Chapter {chapter_num}",
            url=f"https://mangadex.org/chapter/{ch_data['id']}",
            translation_team_id=group_id,
            language=attributes.get("translatedLanguage", "en"),
            page_count=attributes.get("pages", 0),
        )
        
        return chapter, group
    
    def get_options_schema(self, manga_info: MangaInfo) -> OptionsSchema:
        """
        Define plugin-specific options.
        
        MangaDex-specific options:
        - Data saver mode
        - Output format
        - Concurrent downloads
        """
        return OptionsSchema(fields=[
            OptionField(
                key="data_saver",
                label="Data Saver",
                field_type=FieldType.CHECKBOX,
                default=False,
                description="Use compressed images (smaller file size, lower quality)"
            ),
            OptionField(
                key="format",
                label="Format",
                field_type=FieldType.DROPDOWN,
                choices=["CBZ", "CBR", "ZIP", "Folder"],
                default="CBZ",
                description="Output format for downloaded chapters"
            ),
            OptionField(
                key="concurrent_pages",
                label="Concurrent Page Downloads",
                field_type=FieldType.NUMBER,
                default=3,
                min_value=1,
                max_value=5,
                step=1,
                description="Number of pages to download simultaneously"
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
        
        # Filter chapters based on selection (chapter range + translation team)
        selected_chapters = selection.chapters_in_range(manga_info.chapters)
        
        return DownloadPlan(
            manga_title=manga_info.title,
            chapters=selected_chapters,
            options=options,
            extra={
                "manga_id": manga_info.extra.get("manga_id"),
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
        
        For each chapter:
        1. Get the at-home server URL
        2. Download all pages
        3. Optionally create CBZ archive
        """
        output_dir = Path(plan.output_dir) / self._sanitize_filename(plan.manga_title)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        client = await self._get_client()
        
        data_saver = plan.options.get("data_saver", False)
        output_format = plan.options.get("format", "CBZ")
        concurrent_pages = plan.options.get("concurrent_pages", 3)
        
        for chapter_idx, chapter in enumerate(plan.chapters):
            cancel_token.check()
            
            # Create chapter directory
            chapter_num_str = f"{chapter.number:g}" if chapter.number != int(chapter.number) else str(int(chapter.number))
            chapter_dir = output_dir / f"Chapter {chapter_num_str.zfill(4)}"
            chapter_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                # Get at-home server info
                server_info = await self._get_at_home_server(client, chapter.id)
                
                if not server_info:
                    raise ValueError(f"Could not get server info for chapter {chapter.number}")
                
                base_url = server_info["base_url"]
                chapter_hash = server_info["hash"]
                
                # Choose data or data-saver
                if data_saver and server_info.get("data_saver"):
                    page_files = server_info["data_saver"]
                    quality_path = "data-saver"
                else:
                    page_files = server_info["data"]
                    quality_path = "data"
                
                total_pages = len(page_files)
                
                # Download pages with concurrency limit
                semaphore = asyncio.Semaphore(concurrent_pages)
                downloaded_files = []
                total_bytes = 0
                start_time = asyncio.get_event_loop().time()
                
                async def download_page(page_idx: int, filename: str):
                    nonlocal total_bytes
                    async with semaphore:
                        cancel_token.check()
                        
                        page_url = f"{base_url}/{quality_path}/{chapter_hash}/{filename}"
                        
                        for retry in range(self.max_retries):
                            try:
                                response = await client.get(page_url)
                                response.raise_for_status()
                                
                                # Determine file extension
                                ext = Path(filename).suffix or ".jpg"
                                page_file = chapter_dir / f"{(page_idx + 1):03d}{ext}"
                                page_file.write_bytes(response.content)
                                
                                file_size = len(response.content)
                                total_bytes += file_size
                                
                                # Calculate speed
                                elapsed = asyncio.get_event_loop().time() - start_time
                                speed = total_bytes / elapsed if elapsed > 0 else 0
                                speed_str = self._format_speed(speed)
                                
                                # Report progress
                                progress_callback(
                                    chapter.number,
                                    page_idx + 1,
                                    total_pages,
                                    file_size,
                                    speed_str
                                )
                                
                                downloaded_files.append(page_file)
                                break
                                
                            except httpx.HTTPStatusError as e:
                                if retry < self.max_retries - 1:
                                    await asyncio.sleep(1 * (retry + 1))
                                else:
                                    raise
                        
                        # Rate limiting between pages
                        await asyncio.sleep(self.rate_limit)
                
                # Download all pages
                tasks = [
                    download_page(idx, filename) 
                    for idx, filename in enumerate(page_files)
                ]
                await asyncio.gather(*tasks)
                
                # Create archive based on format
                if output_format != "Folder" and downloaded_files:
                    chapter_name = f"Chapter {chapter_num_str.zfill(4)}"
                    
                    if output_format == "CBZ":
                        archive_path = output_dir / f"{chapter_name}.cbz"
                        self._create_archive(chapter_dir, archive_path, downloaded_files, "zip")
                    elif output_format == "CBR":
                        # CBR is RAR format, but we create as ZIP since Python lacks RAR write support
                        # Most comic readers can still open it
                        archive_path = output_dir / f"{chapter_name}.cbr"
                        self._create_archive(chapter_dir, archive_path, downloaded_files, "zip")
                    elif output_format == "ZIP":
                        archive_path = output_dir / f"{chapter_name}.zip"
                        self._create_archive(chapter_dir, archive_path, downloaded_files, "zip")
                    
                    # Remove images after creating archive
                    for img_file in downloaded_files:
                        try:
                            img_file.unlink()
                        except Exception:
                            pass
                    try:
                        chapter_dir.rmdir()
                    except Exception:
                        pass
                
            except Exception as e:
                # Log error but continue with next chapter
                progress_callback(
                    chapter.number,
                    0,
                    1,
                    0,
                    f"Error: {e}"
                )
            
            # Rate limit between chapters
            await asyncio.sleep(self.rate_limit * 2)
    
    async def _get_at_home_server(self, client: httpx.AsyncClient, chapter_id: str) -> Optional[dict]:
        """Get the at-home server URL for a chapter."""
        url = f"{self.API_BASE}/at-home/server/{chapter_id}"
        
        for retry in range(self.max_retries):
            try:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                if data.get("result") != "ok":
                    return None
                
                chapter_data = data.get("chapter", {})
                return {
                    "base_url": data.get("baseUrl"),
                    "hash": chapter_data.get("hash"),
                    "data": chapter_data.get("data", []),
                    "data_saver": chapter_data.get("dataSaver", []),
                }
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    # Rate limited, wait and retry
                    await asyncio.sleep(5 * (retry + 1))
                elif retry < self.max_retries - 1:
                    await asyncio.sleep(1 * (retry + 1))
                else:
                    raise
        
        return None
    
    def _create_archive(self, source_dir: Path, archive_path: Path, files: list[Path], format_type: str = "zip") -> None:
        """Create an archive from downloaded images.
        
        Args:
            source_dir: Directory containing the images
            archive_path: Path for the output archive
            files: List of image files to include
            format_type: Archive format ("zip" for CBZ/CBR/ZIP)
        """
        if format_type == "zip":
            with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for img_file in sorted(files):
                    if img_file.exists():
                        zf.write(img_file, img_file.name)
    
    def _sanitize_filename(self, name: str) -> str:
        """Remove invalid characters from filename."""
        # Remove invalid characters
        name = re.sub(r'[<>:"/\\|?*]', '', name)
        # Replace multiple spaces
        name = re.sub(r'\s+', ' ', name)
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
    
    async def test_connection(self) -> tuple[bool, str]:
        """Test if we can connect to MangaDex API."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.API_BASE}/ping")
            
            if response.status_code == 200:
                return (True, "Connected to MangaDex API successfully")
            else:
                return (False, f"API returned status {response.status_code}")
                
        except Exception as e:
            return (False, f"Connection failed: {e}")
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self._client and not self._client.is_closed:
            # Note: proper cleanup would use await client.aclose()
            # but we're in a sync context here
            pass
