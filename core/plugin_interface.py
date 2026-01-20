"""
Plugin interface definition.
All plugins must implement this interface.
"""
from abc import ABC, abstractmethod
from typing import Union
import asyncio

from .models import (
    MangaInfo,
    UserSelection,
    DownloadPlan,
    OptionsSchema,
    CancelToken,
)

# Current plugin API version - plugins must match this
PLUGIN_API_VERSION = 1


class PluginInterface(ABC):
    """
    Abstract base class for manga downloader plugins.
    
    Plugins must implement all abstract methods and define
    class-level metadata attributes.
    """
    
    # Required metadata (override in subclass)
    PLUGIN_API_VERSION: int = PLUGIN_API_VERSION
    name: str = "Unnamed Plugin"
    version: str = "0.0.0"
    author: str = "Unknown"
    description: str = ""
    supported_domains: list[str] = []
    
    # Optional settings
    rate_limit: float = 0.5  # Seconds between requests (default)
    max_retries: int = 3
    timeout: int = 30
    
    def __init__(self):
        """Initialize the plugin."""
        self._enabled = True
    
    @property
    def id(self) -> str:
        """Unique identifier for this plugin."""
        return f"{self.name.lower().replace(' ', '_')}_{self.version}"
    
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    @enabled.setter
    def enabled(self, value: bool):
        self._enabled = value
    
    # ==================== Required Methods ====================
    
    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """
        Check if this plugin can handle the given URL.
        
        Args:
            url: The URL to check
            
        Returns:
            True if this plugin can handle the URL
        """
        pass
    
    @abstractmethod
    def normalize_url(self, url: str) -> str:
        """
        Normalize/clean a URL to a canonical form.
        
        Args:
            url: The URL to normalize
            
        Returns:
            The normalized URL
        """
        pass
    
    @abstractmethod
    async def fetch_manga_info(self, url: str) -> MangaInfo:
        """
        Fetch metadata about a manga from the given URL.
        
        This should retrieve:
        - Title, description, author, artist
        - Cover image URL
        - List of available chapters
        - List of translation teams/groups
        
        Args:
            url: The manga URL
            
        Returns:
            MangaInfo with all available metadata
            
        Raises:
            Exception on network or parsing errors
        """
        pass
    
    @abstractmethod
    def get_options_schema(self, manga_info: MangaInfo) -> OptionsSchema:
        """
        Get the schema for plugin-specific options.
        
        This defines what UI fields should be shown to the user
        for configuring the download (e.g., image quality, format).
        
        Args:
            manga_info: The fetched manga info (may influence available options)
            
        Returns:
            OptionsSchema describing available options
        """
        pass
    
    @abstractmethod
    async def build_download_plan(
        self,
        url: str,
        manga_info: MangaInfo,
        selection: UserSelection,
        options: dict
    ) -> DownloadPlan:
        """
        Build a plan for downloading chapters.
        
        Args:
            url: The manga URL
            manga_info: Previously fetched manga info
            selection: User's chapter/team selection
            options: User's selected options
            
        Returns:
            DownloadPlan with chapters to download
        """
        pass
    
    @abstractmethod
    async def download(
        self,
        plan: DownloadPlan,
        progress_callback: callable,
        cancel_token: CancelToken
    ) -> None:
        """
        Execute the download plan.
        
        Args:
            plan: The download plan to execute
            progress_callback: Callback for progress updates
                Signature: callback(chapter_num, page_num, total_pages, bytes_downloaded, speed_str)
            cancel_token: Token to check for cancellation/pause
            
        Raises:
            CancelledException if cancelled
            Exception on download errors
        """
        pass
    
    # ==================== Optional Methods ====================
    
    def validate_url(self, url: str) -> tuple[bool, str]:
        """
        Validate a URL more thoroughly than can_handle().
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if self.can_handle(url):
            return (True, "")
        return (False, "URL not supported by this plugin")
    
    async def test_connection(self) -> tuple[bool, str]:
        """
        Test if the plugin can connect to its target site.
        
        Returns:
            Tuple of (success, message)
        """
        return (True, "Connection test not implemented")
    
    def get_rate_limit(self) -> float:
        """Get the rate limit in seconds between requests."""
        return self.rate_limit
    
    def cleanup(self) -> None:
        """Called when plugin is unloaded. Clean up resources."""
        pass


class SyncPluginWrapper:
    """
    Wrapper to run sync plugin methods in an executor.
    Use this if your plugin uses synchronous networking (requests).
    """
    
    def __init__(self, sync_method: callable):
        self.sync_method = sync_method
    
    async def __call__(self, *args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: self.sync_method(*args, **kwargs))
