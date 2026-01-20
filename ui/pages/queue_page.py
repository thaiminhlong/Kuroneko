"""
Queue page - main interface for adding URLs and managing downloads.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QLabel, QTextEdit, QTableWidget,
    QTableWidgetItem, QHeaderView, QFrame, QComboBox,
    QDoubleSpinBox, QProgressBar, QPlainTextEdit,
    QFormLayout, QScrollArea, QFileDialog, QCheckBox,
    QSpinBox, QLineEdit, QGroupBox, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont

from core import (
    TaskManager, PluginManager, Task, TaskStatus,
    EventBus, Event, EventType, FieldType
)
from ..styles import Colors


class QueuePage(QWidget):
    """Main queue management page."""
    
    def __init__(self, task_manager: TaskManager, plugin_manager: PluginManager, settings: dict):
        super().__init__()
        
        self.task_manager = task_manager
        self.plugin_manager = plugin_manager
        self.settings = settings
        self.event_bus = EventBus()
        
        self.current_task_id: str | None = None
        self._option_widgets: dict = {}
        
        self._setup_ui()
        self._connect_events()
        
        # Refresh timer
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_task_list)
        self._refresh_timer.start(500)
    
    def _setup_ui(self):
        """Setup the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Page title
        title = QLabel("Download Queue")
        title.setObjectName("page_title")
        layout.addWidget(title)
        
        # Main container with margins
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(25, 10, 25, 25)
        container_layout.setSpacing(15)
        
        # Top section: URL input (fixed height)
        input_section = self._create_input_section()
        container_layout.addWidget(input_section)
        
        # Vertical splitter for main content and log
        main_splitter = QSplitter(Qt.Vertical)
        
        # Middle section: Task list and details (horizontal splitter)
        middle_splitter = QSplitter(Qt.Horizontal)
        
        # Task table
        task_table_widget = self._create_task_table()
        middle_splitter.addWidget(task_table_widget)
        
        # Details panel
        details_panel = self._create_details_panel()
        middle_splitter.addWidget(details_panel)
        
        middle_splitter.setSizes([600, 400])
        main_splitter.addWidget(middle_splitter)
        
        # Bottom section: Log console (resizable via splitter)
        log_section = self._create_log_section()
        main_splitter.addWidget(log_section)
        
        # Set initial sizes: main content gets more space, log gets less
        main_splitter.setSizes([500, 150])
        
        container_layout.addWidget(main_splitter, stretch=1)
        layout.addWidget(container)
    
    def _create_input_section(self) -> QWidget:
        """Create the URL input section."""
        section = QFrame()
        section.setObjectName("card")
        
        layout = QVBoxLayout(section)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("ADD URLS")
        header_label.setObjectName("section_label")
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # URL input
        self.url_input = QTextEdit()
        self.url_input.setPlaceholderText("Paste manga URLs here (one per line)...\n\nExample:\nhttps://example.com/manga/one-piece\nhttps://example.com/manga/naruto")
        self.url_input.setMinimumHeight(80)
        self.url_input.setMaximumHeight(120)
        layout.addWidget(self.url_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Add to Queue")
        self.add_btn.setObjectName("primary_button")
        self.add_btn.setCursor(Qt.PointingHandCursor)
        self.add_btn.clicked.connect(self._on_add_urls)
        button_layout.addWidget(self.add_btn)
        
        self.import_btn = QPushButton("Import .txt")
        self.import_btn.setCursor(Qt.PointingHandCursor)
        self.import_btn.clicked.connect(self._on_import_file)
        button_layout.addWidget(self.import_btn)
        
        self.validate_all_btn = QPushButton("Validate All")
        self.validate_all_btn.setCursor(Qt.PointingHandCursor)
        self.validate_all_btn.clicked.connect(self._on_validate_all)
        button_layout.addWidget(self.validate_all_btn)
        
        self.download_all_btn = QPushButton("Download All")
        self.download_all_btn.setObjectName("primary_button")
        self.download_all_btn.setCursor(Qt.PointingHandCursor)
        self.download_all_btn.clicked.connect(self._on_download_all)
        button_layout.addWidget(self.download_all_btn)
        
        button_layout.addStretch()
        
        self.clear_btn = QPushButton("Clear Input")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(lambda: self.url_input.clear())
        button_layout.addWidget(self.clear_btn)
        
        layout.addLayout(button_layout)
        
        return section
    
    def _create_task_table(self) -> QWidget:
        """Create the task list table."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("QUEUE")
        header_label.setObjectName("section_label")
        header_layout.addWidget(header_label)
        
        self.queue_count_label = QLabel("0 items")
        self.queue_count_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        header_layout.addWidget(self.queue_count_label)
        
        header_layout.addStretch()
        
        self.clear_completed_btn = QPushButton("Clear Completed")
        self.clear_completed_btn.setCursor(Qt.PointingHandCursor)
        self.clear_completed_btn.clicked.connect(self._on_clear_completed)
        header_layout.addWidget(self.clear_completed_btn)
        
        layout.addLayout(header_layout)
        
        # Table
        self.task_table = QTableWidget()
        self.task_table.setColumnCount(6)
        self.task_table.setHorizontalHeaderLabels([
            "Title", "Plugin", "Chapters", "Status", "Progress", "Speed"
        ])
        
        # Configure table
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.task_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.task_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.task_table.setShowGrid(False)
        self.task_table.setAlternatingRowColors(False)
        self.task_table.verticalHeader().setVisible(False)
        
        # Column sizing
        header = self.task_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.resizeSection(4, 120)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        self.task_table.itemSelectionChanged.connect(self._on_task_selected)
        
        layout.addWidget(self.task_table)
        
        return widget
    
    def _create_details_panel(self) -> QWidget:
        """Create the task details panel."""
        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumWidth(350)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # Header
        header_label = QLabel("DETAILS")
        header_label.setObjectName("section_label")
        layout.addWidget(header_label)
        
        # Scroll area for options
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        self.details_layout = QVBoxLayout(scroll_content)
        self.details_layout.setSpacing(15)
        self.details_layout.setContentsMargins(0, 0, 10, 0)
        
        # Title
        self.detail_title = QLabel("Select a task to view details")
        self.detail_title.setStyleSheet(f"font-size: 16px; font-weight: 600; color: {Colors.TEXT_PRIMARY};")
        self.detail_title.setWordWrap(True)
        self.details_layout.addWidget(self.detail_title)
        
        # URL
        self.detail_url = QLabel("")
        self.detail_url.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        self.detail_url.setWordWrap(True)
        self.details_layout.addWidget(self.detail_url)
        
        # Chapter range group
        chapter_group = QGroupBox("Chapter Range")
        chapter_layout = QHBoxLayout(chapter_group)
        
        self.chapter_start = QDoubleSpinBox()
        self.chapter_start.setDecimals(1)
        self.chapter_start.setRange(0, 99999)
        self.chapter_start.setPrefix("From: ")
        chapter_layout.addWidget(self.chapter_start)
        
        self.chapter_end = QDoubleSpinBox()
        self.chapter_end.setDecimals(1)
        self.chapter_end.setRange(0, 99999)
        self.chapter_end.setPrefix("To: ")
        chapter_layout.addWidget(self.chapter_end)
        
        self.details_layout.addWidget(chapter_group)
        
        # Translation team
        team_group = QGroupBox("Translation Team")
        team_layout = QVBoxLayout(team_group)
        
        self.team_combo = QComboBox()
        self.team_combo.addItem("All Teams", None)
        team_layout.addWidget(self.team_combo)
        
        self.details_layout.addWidget(team_group)
        
        # Plugin options (dynamic)
        self.options_group = QGroupBox("Options")
        self.options_layout = QFormLayout(self.options_group)
        self.details_layout.addWidget(self.options_group)
        
        # Spacer
        self.details_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, stretch=1)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.fetch_btn = QPushButton("Fetch Info")
        self.fetch_btn.setCursor(Qt.PointingHandCursor)
        self.fetch_btn.clicked.connect(self._on_fetch_info)
        button_layout.addWidget(self.fetch_btn)
        
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setCursor(Qt.PointingHandCursor)
        self.apply_btn.clicked.connect(self._on_apply_options)
        button_layout.addWidget(self.apply_btn)
        
        layout.addLayout(button_layout)
        
        button_layout2 = QHBoxLayout()
        
        self.download_btn = QPushButton("Download")
        self.download_btn.setObjectName("primary_button")
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.clicked.connect(self._on_download_task)
        button_layout2.addWidget(self.download_btn)
        
        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setCursor(Qt.PointingHandCursor)
        self.pause_btn.clicked.connect(self._on_pause_task)
        button_layout2.addWidget(self.pause_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("danger_button")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.clicked.connect(self._on_cancel_task)
        button_layout2.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout2)
        
        return panel
    
    def _create_log_section(self) -> QWidget:
        """Create the collapsible log console."""
        section = QFrame()
        section.setObjectName("card")
        section.setMinimumHeight(100)  # Minimum so it's always visible
        
        layout = QVBoxLayout(section)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("LOG")
        header_label.setObjectName("section_label")
        header_layout.addWidget(header_label)
        
        header_layout.addStretch()
        
        self.clear_log_btn = QPushButton("Clear")
        self.clear_log_btn.setFixedSize(60, 24)
        self.clear_log_btn.setCursor(Qt.PointingHandCursor)
        self.clear_log_btn.clicked.connect(self._on_clear_log)
        header_layout.addWidget(self.clear_log_btn)
        
        layout.addLayout(header_layout)
        
        # Log output
        self.log_output = QPlainTextEdit()
        self.log_output.setObjectName("log_console")
        self.log_output.setReadOnly(True)
        self.log_output.setMaximumBlockCount(500)
        layout.addWidget(self.log_output)
        
        return section
    
    def _connect_events(self):
        """Connect to event bus."""
        self.event_bus.subscribe(EventType.TASK_ADDED, self._on_event_task_added)
        self.event_bus.subscribe(EventType.TASK_UPDATED, self._on_event_task_updated)
        self.event_bus.subscribe(EventType.TASK_REMOVED, self._on_event_task_removed)
        self.event_bus.subscribe(EventType.LOG_INFO, self._on_event_log)
        self.event_bus.subscribe(EventType.LOG_WARNING, self._on_event_log)
        self.event_bus.subscribe(EventType.LOG_ERROR, self._on_event_log)
        self.event_bus.subscribe(EventType.DOWNLOAD_PROGRESS, self._on_event_download_progress)
    
    # ==================== Event Handlers ====================
    
    def _on_add_urls(self):
        """Handle add URLs button click."""
        text = self.url_input.toPlainText().strip()
        if not text:
            return
        
        tasks = self.task_manager.add_tasks_from_text(text)
        self.url_input.clear()
        
        self._log(f"Added {len(tasks)} URL(s) to queue")
        self._refresh_task_list()
    
    def _on_import_file(self):
        """Handle import file button click."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import URLs", "", "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                tasks = self.task_manager.add_tasks_from_text(text)
                self._log(f"Imported {len(tasks)} URL(s) from file")
                self._refresh_task_list()
            except Exception as e:
                self._log(f"Error importing file: {e}", "error")
    
    def _on_validate_all(self):
        """Validate all queued tasks."""
        count = self.task_manager.validate_all_queued()
        self._log(f"Started validation for {count} task(s)")
    
    def _on_download_all(self):
        """Start downloading all ready tasks."""
        count = self.task_manager.download_all_ready()
        self._log(f"Started download for {count} task(s)")
    
    def _on_clear_completed(self):
        """Clear completed tasks."""
        count = self.task_manager.clear_completed()
        self._log(f"Cleared {count} completed task(s)")
        self._refresh_task_list()
    
    def _on_task_selected(self):
        """Handle task selection in table."""
        selected = self.task_table.selectedItems()
        if not selected:
            self.current_task_id = None
            self._update_details_panel(None)
            return
        
        row = selected[0].row()
        task_id = self.task_table.item(row, 0).data(Qt.UserRole)
        self.current_task_id = task_id
        
        task = self.task_manager.get_task(task_id)
        self._update_details_panel(task)
    
    def _on_fetch_info(self):
        """Fetch manga info for current task."""
        if self.current_task_id:
            self.task_manager.validate_task(self.current_task_id)
    
    def _on_apply_options(self):
        """Apply current options to task."""
        if not self.current_task_id:
            return
        
        task = self.task_manager.get_task(self.current_task_id)
        if not task:
            return
        
        # Update selection
        task.selection.chapter_start = self.chapter_start.value()
        task.selection.chapter_end = self.chapter_end.value()
        
        team_data = self.team_combo.currentData()
        task.selection.translation_team_id = team_data
        
        # Update plugin options
        for key, widget in self._option_widgets.items():
            if isinstance(widget, QCheckBox):
                task.options[key] = widget.isChecked()
            elif isinstance(widget, QSpinBox):
                task.options[key] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                task.options[key] = widget.value()
            elif isinstance(widget, QComboBox):
                task.options[key] = widget.currentText()
            elif isinstance(widget, QLineEdit):
                task.options[key] = widget.text()
        
        self._log(f"Applied options to: {task.display_title}")
    
    def _on_download_task(self):
        """Start download for current task."""
        if self.current_task_id:
            self._on_apply_options()  # Apply first
            self.task_manager.start_download(self.current_task_id)
    
    def _on_pause_task(self):
        """Pause current task."""
        if self.current_task_id:
            task = self.task_manager.get_task(self.current_task_id)
            if task and task.status == TaskStatus.PAUSED:
                self.task_manager.resume_task(self.current_task_id)
                self.pause_btn.setText("Pause")
            else:
                self.task_manager.pause_task(self.current_task_id)
                self.pause_btn.setText("Resume")
    
    def _on_cancel_task(self):
        """Cancel current task."""
        if self.current_task_id:
            self.task_manager.cancel_task(self.current_task_id)
    
    def _on_clear_log(self):
        """Clear log output."""
        self.log_output.clear()
    
    # ==================== Event Bus Handlers ====================
    
    def _on_event_task_added(self, event: Event):
        self._refresh_task_list()
    
    def _on_event_task_updated(self, event: Event):
        self._refresh_task_list()
        if event.payload.get("task_id") == self.current_task_id:
            task = self.task_manager.get_task(self.current_task_id)
            self._update_details_panel(task)
    
    def _on_event_task_removed(self, event: Event):
        self._refresh_task_list()
    
    def _on_event_log(self, event: Event):
        level = event.payload.get("level", "info")
        message = event.payload.get("message", "")
        self._log(message, level)
    
    def _on_event_download_progress(self, event: Event):
        pass  # Handled by refresh timer
    
    # ==================== UI Updates ====================
    
    def _refresh_task_list(self):
        """Refresh the task table."""
        tasks = self.task_manager.get_all_tasks()
        self.queue_count_label.setText(f"{len(tasks)} items")
        
        # Remember selection
        selected_id = self.current_task_id
        
        # Update table
        self.task_table.setRowCount(len(tasks))
        
        for row, task in enumerate(tasks):
            # Title
            title_item = QTableWidgetItem(task.display_title)
            title_item.setData(Qt.UserRole, task.id)
            self.task_table.setItem(row, 0, title_item)
            
            # Plugin
            plugin = self.plugin_manager.get_plugin(task.plugin_id) if task.plugin_id else None
            plugin_name = plugin.name if plugin else "Unknown"
            self.task_table.setItem(row, 1, QTableWidgetItem(plugin_name))
            
            # Chapters
            if task.manga_info:
                ch_min, ch_max = task.manga_info.chapter_range
                chapters_text = f"{task.selection.chapter_start or ch_min} - {task.selection.chapter_end or ch_max}"
            else:
                chapters_text = "-"
            self.task_table.setItem(row, 2, QTableWidgetItem(chapters_text))
            
            # Status
            status_item = QTableWidgetItem(task.status_text)
            status_color = self._get_status_color(task.status)
            status_item.setForeground(status_color)
            self.task_table.setItem(row, 3, status_item)
            
            # Progress
            progress_item = QTableWidgetItem(f"{task.progress_percent}%")
            self.task_table.setItem(row, 4, progress_item)
            
            # Speed
            self.task_table.setItem(row, 5, QTableWidgetItem(task.speed or "-"))
            
            # Restore selection
            if task.id == selected_id:
                self.task_table.selectRow(row)
    
    def _update_details_panel(self, task: Task | None):
        """Update the details panel for a task."""
        if not task:
            self.detail_title.setText("Select a task to view details")
            self.detail_url.setText("")
            self.chapter_start.setValue(0)
            self.chapter_end.setValue(0)
            self.team_combo.clear()
            self.team_combo.addItem("All Teams", None)
            self._clear_options()
            return
        
        # Update basic info
        self.detail_title.setText(task.display_title)
        self.detail_url.setText(task.url)
        
        # Update chapter range
        if task.manga_info:
            ch_min, ch_max = task.manga_info.chapter_range
            self.chapter_start.setRange(ch_min, ch_max)
            self.chapter_end.setRange(ch_min, ch_max)
            self.chapter_start.setValue(task.selection.chapter_start or ch_min)
            self.chapter_end.setValue(task.selection.chapter_end or ch_max)
            
            # Update teams
            self.team_combo.clear()
            self.team_combo.addItem("All Teams", None)
            self._log(f"Loading {len(task.manga_info.translation_teams)} translation team(s)")
            for team in task.manga_info.translation_teams:
                self.team_combo.addItem(str(team), team.id)
                self._log(f"  Added team: {team.name}")
            
            # Select current team
            if task.selection.translation_team_id:
                for i in range(self.team_combo.count()):
                    if self.team_combo.itemData(i) == task.selection.translation_team_id:
                        self.team_combo.setCurrentIndex(i)
                        break
        else:
            self.chapter_start.setValue(0)
            self.chapter_end.setValue(0)
            self.team_combo.clear()
            self.team_combo.addItem("All Teams", None)
        
        # Update plugin options
        self._update_options(task)
        
        # Update button states
        is_downloading = task.status == TaskStatus.DOWNLOADING
        is_paused = task.status == TaskStatus.PAUSED
        
        self.fetch_btn.setEnabled(task.status in (TaskStatus.QUEUED, TaskStatus.FAILED))
        self.download_btn.setEnabled(task.status in (TaskStatus.READY, TaskStatus.QUEUED))
        self.pause_btn.setEnabled(is_downloading or is_paused)
        self.pause_btn.setText("Resume" if is_paused else "Pause")
        self.cancel_btn.setEnabled(is_downloading or is_paused)
    
    def _update_options(self, task: Task):
        """Update plugin options form."""
        self._clear_options()
        
        if not task.plugin_id or not task.manga_info:
            self._log(f"Options: No plugin_id ({task.plugin_id}) or manga_info ({task.manga_info is not None})")
            return
        
        plugin = self.plugin_manager.get_plugin(task.plugin_id)
        if not plugin:
            self._log(f"Options: Plugin not found for id: {task.plugin_id}")
            return
        
        schema = plugin.get_options_schema(task.manga_info)
        self._log(f"Options: Loaded {len(schema.fields)} option(s) from {plugin.name}")
        
        for field in schema.fields:
            widget = None
            
            if field.field_type == FieldType.CHECKBOX:
                widget = QCheckBox()
                widget.setChecked(task.options.get(field.key, field.default or False))
                
            elif field.field_type == FieldType.NUMBER:
                if field.step and field.step < 1:
                    widget = QDoubleSpinBox()
                    widget.setDecimals(2)
                else:
                    widget = QSpinBox()
                if field.min_value is not None:
                    widget.setMinimum(int(field.min_value))
                if field.max_value is not None:
                    widget.setMaximum(int(field.max_value))
                widget.setValue(task.options.get(field.key, field.default or 0))
                
            elif field.field_type == FieldType.DROPDOWN:
                widget = QComboBox()
                for choice in field.choices:
                    widget.addItem(choice)
                current = task.options.get(field.key, field.default)
                if current in field.choices:
                    widget.setCurrentText(current)
                    
            elif field.field_type == FieldType.TEXT:
                widget = QLineEdit()
                widget.setText(task.options.get(field.key, field.default or ""))
            
            if widget:
                self._option_widgets[field.key] = widget
                self.options_layout.addRow(field.label + ":", widget)
    
    def _clear_options(self):
        """Clear plugin options form."""
        while self.options_layout.count():
            item = self.options_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._option_widgets.clear()
    
    def _get_status_color(self, status: TaskStatus):
        """Get color for task status."""
        from PySide6.QtGui import QColor
        color_map = {
            TaskStatus.QUEUED: Colors.TEXT_MUTED,
            TaskStatus.VALIDATING: Colors.INFO,
            TaskStatus.READY: Colors.TEXT_PRIMARY,
            TaskStatus.DOWNLOADING: Colors.INFO,
            TaskStatus.PAUSED: Colors.WARNING,
            TaskStatus.COMPLETED: Colors.SUCCESS,
            TaskStatus.FAILED: Colors.ERROR,
            TaskStatus.CANCELED: Colors.TEXT_MUTED,
        }
        return QColor(color_map.get(status, Colors.TEXT_PRIMARY))
    
    def _log(self, message: str, level: str = "info"):
        """Add a log message."""
        import datetime
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        color_map = {
            "info": Colors.TEXT_SECONDARY,
            "warning": Colors.WARNING,
            "error": Colors.ERROR,
            "debug": Colors.TEXT_MUTED,
        }
        color = color_map.get(level, Colors.TEXT_SECONDARY)
        
        # Simple text append (HTML for colors would require QTextEdit)
        prefix = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "debug": "🔧"}.get(level, "")
        self.log_output.appendPlainText(f"[{timestamp}] {prefix} {message}")
