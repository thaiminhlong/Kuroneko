"""
Core data models for the manga downloader application.
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Optional
import uuid
import threading


class TaskStatus(Enum):
    """Task state machine states."""
    QUEUED = auto()
    VALIDATING = auto()
    READY = auto()
    DOWNLOADING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELED = auto()


class FieldType(Enum):
    """Types of UI fields for plugin options."""
    TEXT = "text"
    NUMBER = "number"
    DROPDOWN = "dropdown"
    CHECKBOX = "checkbox"
    RANGE = "range"


@dataclass
class OptionField:
    """Describes a single option field for plugin UI."""
    key: str
    label: str
    field_type: FieldType
    default: Any = None
    choices: list[str] = field(default_factory=list)  # For dropdown
    min_value: Optional[float] = None  # For number/range
    max_value: Optional[float] = None  # For number/range
    step: Optional[float] = None  # For number/range
    required: bool = False
    description: str = ""


@dataclass
class OptionsSchema:
    """Schema for plugin-defined options."""
    fields: list[OptionField] = field(default_factory=list)
    
    def get_defaults(self) -> dict[str, Any]:
        """Return a dict of default values for all fields."""
        return {f.key: f.default for f in self.fields}


@dataclass
class Chapter:
    """Represents a manga chapter."""
    id: str
    number: float  # Can be 1.5 for side chapters
    title: str = ""
    url: str = ""
    translation_team_id: Optional[str] = None
    language: str = "en"
    page_count: Optional[int] = None


@dataclass
class TranslationTeam:
    """Represents a scanlation/translation group."""
    id: str
    name: str
    language: str = "en"
    
    def __str__(self) -> str:
        return f"{self.name} [{self.language}]"


@dataclass
class MangaInfo:
    """Metadata about a manga series fetched by a plugin."""
    title: str
    url: str
    cover_url: Optional[str] = None
    description: str = ""
    author: str = ""
    artist: str = ""
    status: str = ""  # ongoing, completed, hiatus
    chapters: list[Chapter] = field(default_factory=list)
    translation_teams: list[TranslationTeam] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    
    @property
    def chapter_range(self) -> tuple[float, float]:
        """Return (min_chapter, max_chapter) or (0, 0) if no chapters."""
        if not self.chapters:
            return (0.0, 0.0)
        numbers = [c.number for c in self.chapters]
        return (min(numbers), max(numbers))


@dataclass
class UserSelection:
    """User's selection for downloading."""
    chapter_start: Optional[float] = None
    chapter_end: Optional[float] = None
    translation_team_id: Optional[str] = None
    language: Optional[str] = None
    
    def chapters_in_range(self, chapters: list[Chapter]) -> list[Chapter]:
        """Filter chapters to only those in the selected range."""
        result = []
        for ch in chapters:
            if self.chapter_start is not None and ch.number < self.chapter_start:
                continue
            if self.chapter_end is not None and ch.number > self.chapter_end:
                continue
            if self.translation_team_id and ch.translation_team_id != self.translation_team_id:
                continue
            if self.language and ch.language != self.language:
                continue
            result.append(ch)
        return sorted(result, key=lambda c: c.number)


@dataclass
class DownloadPlan:
    """Plan for downloading chapters, built by a plugin."""
    manga_title: str
    chapters: list[Chapter]
    output_dir: str = ""
    options: dict[str, Any] = field(default_factory=dict)
    extra: dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_chapters(self) -> int:
        return len(self.chapters)


class CancelToken:
    """Thread-safe cancellation token for download tasks."""
    
    def __init__(self):
        self._cancelled = threading.Event()
        self._paused = threading.Event()
    
    def cancel(self):
        """Request cancellation."""
        self._cancelled.set()
    
    def pause(self):
        """Request pause."""
        self._paused.set()
    
    def resume(self):
        """Resume from pause."""
        self._paused.clear()
    
    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()
    
    @property
    def is_paused(self) -> bool:
        return self._paused.is_set()
    
    def check(self) -> None:
        """Raise if cancelled, block if paused."""
        if self._cancelled.is_set():
            raise CancelledException("Download was cancelled")
        while self._paused.is_set() and not self._cancelled.is_set():
            self._paused.wait(timeout=0.5)
        if self._cancelled.is_set():
            raise CancelledException("Download was cancelled")


class CancelledException(Exception):
    """Raised when a download is cancelled."""
    pass


@dataclass
class Task:
    """Represents a download task in the queue."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    url: str = ""
    plugin_id: Optional[str] = None
    title: str = ""
    status: TaskStatus = TaskStatus.QUEUED
    progress: float = 0.0  # 0.0 to 1.0
    speed: str = ""  # e.g., "1.2 MB/s"
    eta: str = ""  # e.g., "2m 30s"
    current_chapter: str = ""
    total_chapters: int = 0
    completed_chapters: int = 0
    errors: list[str] = field(default_factory=list)
    manga_info: Optional[MangaInfo] = None
    selection: UserSelection = field(default_factory=UserSelection)
    options: dict[str, Any] = field(default_factory=dict)
    cancel_token: CancelToken = field(default_factory=CancelToken)
    
    @property
    def display_title(self) -> str:
        return self.title if self.title else self.url
    
    @property
    def status_text(self) -> str:
        status_map = {
            TaskStatus.QUEUED: "Queued",
            TaskStatus.VALIDATING: "Validating...",
            TaskStatus.READY: "Ready",
            TaskStatus.DOWNLOADING: f"Downloading ({self.completed_chapters}/{self.total_chapters})",
            TaskStatus.PAUSED: "Paused",
            TaskStatus.COMPLETED: "Completed",
            TaskStatus.FAILED: "Failed",
            TaskStatus.CANCELED: "Canceled",
        }
        return status_map.get(self.status, str(self.status))
    
    @property
    def progress_percent(self) -> int:
        return int(self.progress * 100)
