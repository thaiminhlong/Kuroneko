"""
Event bus for decoupled communication between components.
Thread-safe and Qt-compatible.
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable
from collections import defaultdict
import threading
import queue


class EventType(Enum):
    """Types of events in the application."""
    # Task events
    TASK_ADDED = auto()
    TASK_UPDATED = auto()
    TASK_REMOVED = auto()
    TASK_STATUS_CHANGED = auto()
    TASK_PROGRESS = auto()
    TASK_COMPLETED = auto()
    TASK_FAILED = auto()
    
    # Plugin events
    PLUGIN_LOADED = auto()
    PLUGIN_ERROR = auto()
    PLUGIN_ENABLED = auto()
    PLUGIN_DISABLED = auto()
    
    # Log events
    LOG_INFO = auto()
    LOG_WARNING = auto()
    LOG_ERROR = auto()
    LOG_DEBUG = auto()
    
    # Download events
    DOWNLOAD_STARTED = auto()
    DOWNLOAD_PROGRESS = auto()
    DOWNLOAD_CHAPTER_COMPLETE = auto()
    DOWNLOAD_COMPLETE = auto()
    DOWNLOAD_ERROR = auto()


@dataclass
class Event:
    """An event with type and payload."""
    type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = ""


class EventBus:
    """
    Thread-safe event bus for publishing and subscribing to events.
    Supports both immediate callbacks and queued events for UI thread safety.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for global event bus."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._subscribers: dict[EventType, list[Callable]] = defaultdict(list)
        self._queue: queue.Queue[Event] = queue.Queue()
        self._lock = threading.Lock()
    
    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Subscribe to an event type."""
        with self._lock:
            if callback not in self._subscribers[event_type]:
                self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        """Unsubscribe from an event type."""
        with self._lock:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
    
    def publish(self, event: Event) -> None:
        """
        Publish an event immediately to all subscribers.
        Note: Callbacks are called in the publishing thread.
        For UI safety, use publish_to_queue() and process in UI thread.
        """
        with self._lock:
            subscribers = list(self._subscribers[event.type])
        
        for callback in subscribers:
            try:
                callback(event)
            except Exception as e:
                print(f"Error in event handler: {e}")
    
    def publish_to_queue(self, event: Event) -> None:
        """
        Add event to queue for later processing (UI thread safe).
        """
        self._queue.put(event)
    
    def process_queue(self, max_events: int = 100) -> int:
        """
        Process queued events. Call this from UI thread.
        Returns number of events processed.
        """
        processed = 0
        while processed < max_events:
            try:
                event = self._queue.get_nowait()
                self.publish(event)
                processed += 1
            except queue.Empty:
                break
        return processed
    
    def clear_queue(self) -> None:
        """Clear all queued events."""
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break
    
    def emit_log(self, level: str, message: str, source: str = "") -> None:
        """Convenience method to emit log events."""
        event_map = {
            "info": EventType.LOG_INFO,
            "warning": EventType.LOG_WARNING,
            "error": EventType.LOG_ERROR,
            "debug": EventType.LOG_DEBUG,
        }
        event_type = event_map.get(level.lower(), EventType.LOG_INFO)
        self.publish_to_queue(Event(
            type=event_type,
            payload={"message": message, "level": level},
            source=source
        ))


# Global event bus instance
event_bus = EventBus()
