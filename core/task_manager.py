"""
Task manager for managing the download queue and executing downloads.
"""
import asyncio
from pathlib import Path
from typing import Optional, Callable
import threading
import time

from .models import Task, TaskStatus, UserSelection, CancelToken, CancelledException
from .plugin_manager import PluginManager
from .event_bus import EventBus, Event, EventType


class TaskManager:
    """
    Manages the download task queue and executes downloads.
    Runs downloads in background threads/async tasks.
    """
    
    def __init__(self, plugin_manager: PluginManager, settings: dict):
        """
        Initialize the task manager.
        
        Args:
            plugin_manager: The plugin manager instance
            settings: App settings dict
        """
        self.plugin_manager = plugin_manager
        self.settings = settings
        self.event_bus = EventBus()
        
        self.tasks: dict[str, Task] = {}
        self.task_order: list[str] = []  # Maintain insertion order
        
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._active_downloads = 0
        self._download_semaphore: Optional[asyncio.Semaphore] = None
    
    def start(self) -> None:
        """Start the background worker thread."""
        if self._running:
            return
        
        self._running = True
        self._worker_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._worker_thread.start()
    
    def stop(self) -> None:
        """Stop the background worker thread."""
        self._running = False
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
    
    def _run_event_loop(self) -> None:
        """Run the asyncio event loop in a background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        max_parallel = self.settings.get("max_parallel_downloads", 3)
        self._download_semaphore = asyncio.Semaphore(max_parallel)
        
        try:
            self._loop.run_forever()
        finally:
            self._loop.close()
    
    def add_task(self, url: str) -> Task:
        """
        Add a new task to the queue.
        
        Args:
            url: The URL to download
            
        Returns:
            The created Task
        """
        task = Task(url=url.strip())
        
        # Try to find a matching plugin
        plugin = self.plugin_manager.get_plugin_for_url(task.url)
        if plugin:
            task.plugin_id = plugin.id
            task.url = plugin.normalize_url(task.url)
        
        self.tasks[task.id] = task
        self.task_order.append(task.id)
        
        self.event_bus.publish_to_queue(Event(
            type=EventType.TASK_ADDED,
            payload={"task_id": task.id, "url": task.url}
        ))
        
        return task
    
    def add_tasks_from_text(self, text: str) -> list[Task]:
        """
        Add multiple tasks from newline-separated URLs.
        
        Args:
            text: Text containing URLs (one per line)
            
        Returns:
            List of created Tasks
        """
        tasks = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("#"):
                tasks.append(self.add_task(line))
        return tasks
    
    def remove_task(self, task_id: str) -> bool:
        """Remove a task from the queue."""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        # Cancel if running
        if task.status in (TaskStatus.DOWNLOADING, TaskStatus.VALIDATING):
            task.cancel_token.cancel()
        
        del self.tasks[task_id]
        self.task_order.remove(task_id)
        
        self.event_bus.publish_to_queue(Event(
            type=EventType.TASK_REMOVED,
            payload={"task_id": task_id}
        ))
        
        return True
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID."""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> list[Task]:
        """Get all tasks in order."""
        return [self.tasks[tid] for tid in self.task_order if tid in self.tasks]
    
    def clear_completed(self) -> int:
        """Remove all completed/failed/canceled tasks. Returns count removed."""
        to_remove = [
            tid for tid, task in self.tasks.items()
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED)
        ]
        for tid in to_remove:
            self.remove_task(tid)
        return len(to_remove)
    
    def validate_task(self, task_id: str) -> None:
        """
        Start validation for a task (fetch manga info).
        Runs asynchronously in the background.
        """
        task = self.tasks.get(task_id)
        if not task:
            return
        
        if not self._loop:
            self.event_bus.emit_log("error", "Worker thread not running")
            return
        
        asyncio.run_coroutine_threadsafe(
            self._validate_task_async(task),
            self._loop
        )
    
    async def _validate_task_async(self, task: Task) -> None:
        """Async task validation (fetch manga info)."""
        try:
            task.status = TaskStatus.VALIDATING
            self._emit_task_update(task)
            
            plugin = self.plugin_manager.get_plugin(task.plugin_id)
            if not plugin:
                raise ValueError(f"No plugin found for task")
            
            # Fetch manga info
            manga_info = await plugin.fetch_manga_info(task.url)
            task.manga_info = manga_info
            task.title = manga_info.title
            
            # Set default selection
            ch_min, ch_max = manga_info.chapter_range
            task.selection.chapter_start = ch_min
            task.selection.chapter_end = ch_max
            if manga_info.translation_teams:
                task.selection.translation_team_id = manga_info.translation_teams[0].id
            
            # Get default options
            options_schema = plugin.get_options_schema(manga_info)
            task.options = options_schema.get_defaults()
            
            task.status = TaskStatus.READY
            task.total_chapters = len(manga_info.chapters)
            self._emit_task_update(task)
            
            self.event_bus.emit_log("info", f"Fetched info: {manga_info.title} ({len(manga_info.chapters)} chapters)")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.errors.append(str(e))
            self._emit_task_update(task)
            self.event_bus.emit_log("error", f"Validation failed: {e}")
    
    def start_download(self, task_id: str) -> None:
        """
        Start downloading a task.
        Runs asynchronously in the background.
        """
        task = self.tasks.get(task_id)
        if not task:
            return
        
        if task.status not in (TaskStatus.READY, TaskStatus.PAUSED, TaskStatus.QUEUED):
            return
        
        if not self._loop:
            self.event_bus.emit_log("error", "Worker thread not running")
            return
        
        task.cancel_token = CancelToken()  # Fresh token
        
        asyncio.run_coroutine_threadsafe(
            self._download_task_async(task),
            self._loop
        )
    
    async def _download_task_async(self, task: Task) -> None:
        """Async task download."""
        async with self._download_semaphore:
            try:
                task.status = TaskStatus.DOWNLOADING
                task.progress = 0.0
                self._emit_task_update(task)
                
                plugin = self.plugin_manager.get_plugin(task.plugin_id)
                if not plugin:
                    raise ValueError("No plugin found for task")
                
                if not task.manga_info:
                    # Need to fetch info first
                    task.manga_info = await plugin.fetch_manga_info(task.url)
                    task.title = task.manga_info.title
                
                # Build download plan
                download_plan = await plugin.build_download_plan(
                    task.url,
                    task.manga_info,
                    task.selection,
                    task.options
                )
                download_plan.output_dir = self.settings.get("download_folder", "./downloads")
                
                task.total_chapters = download_plan.total_chapters
                self._emit_task_update(task)
                
                self.event_bus.publish_to_queue(Event(
                    type=EventType.DOWNLOAD_STARTED,
                    payload={"task_id": task.id, "title": task.title}
                ))
                
                # Track last chapter to detect chapter completion
                last_chapter_num = [None]  # Use list to allow modification in nested function
                
                # Create progress callback
                def progress_callback(
                    chapter_num: float,
                    page_num: int,
                    total_pages: int,
                    bytes_downloaded: int,
                    speed_str: str
                ):
                    # Detect chapter change (new chapter started = previous chapter completed)
                    if last_chapter_num[0] is not None and chapter_num != last_chapter_num[0]:
                        task.completed_chapters += 1
                    last_chapter_num[0] = chapter_num
                    
                    # Also mark complete when we finish the last page of a chapter
                    if page_num == total_pages and chapter_num == last_chapter_num[0]:
                        # This is the last page of the current chapter
                        pass  # Will be counted when next chapter starts or download ends
                    
                    task.current_chapter = str(chapter_num)
                    task.speed = speed_str
                    
                    # Calculate overall progress
                    chapter_progress = page_num / max(total_pages, 1)
                    overall = (task.completed_chapters + chapter_progress) / max(task.total_chapters, 1)
                    task.progress = min(overall, 1.0)
                    
                    self._emit_task_update(task)
                    
                    self.event_bus.publish_to_queue(Event(
                        type=EventType.DOWNLOAD_PROGRESS,
                        payload={
                            "task_id": task.id,
                            "chapter": chapter_num,
                            "page": page_num,
                            "total_pages": total_pages,
                            "speed": speed_str,
                            "progress": task.progress
                        }
                    ))
                
                # Execute download
                await plugin.download(
                    download_plan,
                    progress_callback,
                    task.cancel_token
                )
                
                # Count the last chapter as completed
                if last_chapter_num[0] is not None:
                    task.completed_chapters += 1
                
                task.status = TaskStatus.COMPLETED
                task.progress = 1.0
                task.completed_chapters = task.total_chapters  # Ensure it shows complete
                self._emit_task_update(task)
                
                self.event_bus.publish_to_queue(Event(
                    type=EventType.DOWNLOAD_COMPLETE,
                    payload={"task_id": task.id, "title": task.title}
                ))
                self.event_bus.emit_log("info", f"Download complete: {task.title}")
                
            except CancelledException:
                task.status = TaskStatus.CANCELED
                self._emit_task_update(task)
                self.event_bus.emit_log("info", f"Download cancelled: {task.title}")
                
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.errors.append(str(e))
                self._emit_task_update(task)
                
                self.event_bus.publish_to_queue(Event(
                    type=EventType.DOWNLOAD_ERROR,
                    payload={"task_id": task.id, "error": str(e)}
                ))
                self.event_bus.emit_log("error", f"Download failed: {e}")
    
    def pause_task(self, task_id: str) -> None:
        """Pause a downloading task."""
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.DOWNLOADING:
            task.cancel_token.pause()
            task.status = TaskStatus.PAUSED
            self._emit_task_update(task)
    
    def resume_task(self, task_id: str) -> None:
        """Resume a paused task."""
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.PAUSED:
            task.cancel_token.resume()
            self.start_download(task_id)
    
    def cancel_task(self, task_id: str) -> None:
        """Cancel a downloading task."""
        task = self.tasks.get(task_id)
        if task and task.status in (TaskStatus.DOWNLOADING, TaskStatus.PAUSED, TaskStatus.VALIDATING):
            task.cancel_token.cancel()
            task.status = TaskStatus.CANCELED
            self._emit_task_update(task)
    
    def _emit_task_update(self, task: Task) -> None:
        """Emit a task update event."""
        self.event_bus.publish_to_queue(Event(
            type=EventType.TASK_UPDATED,
            payload={
                "task_id": task.id,
                "status": task.status.name,
                "progress": task.progress,
                "title": task.title,
            }
        ))
    
    def download_all_ready(self) -> int:
        """Start downloading all ready tasks. Returns count started."""
        started = 0
        for task in self.get_all_tasks():
            if task.status == TaskStatus.READY:
                self.start_download(task.id)
                started += 1
        return started
    
    def validate_all_queued(self) -> int:
        """Validate all queued tasks. Returns count started."""
        started = 0
        for task in self.get_all_tasks():
            if task.status == TaskStatus.QUEUED and task.plugin_id:
                self.validate_task(task.id)
                started += 1
        return started
