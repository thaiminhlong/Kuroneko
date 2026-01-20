"""
History page - view completed downloads.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QFrame, QAbstractItemView
)
from PySide6.QtCore import Qt

from core import TaskManager, TaskStatus
from ..styles import Colors


class HistoryPage(QWidget):
    """Page showing download history."""
    
    def __init__(self, task_manager: TaskManager):
        super().__init__()
        self.task_manager = task_manager
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Page title
        title = QLabel("Download History")
        title.setObjectName("page_title")
        layout.addWidget(title)
        
        # Content
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(25, 10, 25, 25)
        content_layout.setSpacing(15)
        
        # Info card
        info_card = QFrame()
        info_card.setObjectName("card")
        info_layout = QHBoxLayout(info_card)
        
        info_label = QLabel(
            "📚 Download history shows completed, failed, and canceled downloads. "
            "Clear the history to remove old entries."
        )
        info_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        
        content_layout.addWidget(info_card)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("HISTORY")
        header_label.setObjectName("section_label")
        header_layout.addWidget(header_label)
        
        header_layout.addStretch()
        
        self.clear_btn = QPushButton("Clear History")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self._on_clear_history)
        header_layout.addWidget(self.clear_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self._refresh_history)
        header_layout.addWidget(self.refresh_btn)
        
        content_layout.addLayout(header_layout)
        
        # History table
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "Title", "Chapters", "Status", "Date", "Errors"
        ])
        
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setShowGrid(False)
        self.history_table.verticalHeader().setVisible(False)
        
        header = self.history_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        
        content_layout.addWidget(self.history_table)
        
        layout.addWidget(content)
        
        # Initial refresh
        self._refresh_history()
    
    def _refresh_history(self):
        """Refresh the history table."""
        # Get completed/failed/canceled tasks
        tasks = [
            t for t in self.task_manager.get_all_tasks()
            if t.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED)
        ]
        
        self.history_table.setRowCount(len(tasks))
        
        for row, task in enumerate(tasks):
            # Title
            self.history_table.setItem(row, 0, QTableWidgetItem(task.display_title))
            
            # Chapters
            chapters_text = f"{task.completed_chapters}/{task.total_chapters}"
            self.history_table.setItem(row, 1, QTableWidgetItem(chapters_text))
            
            # Status
            status_item = QTableWidgetItem(task.status.name.capitalize())
            if task.status == TaskStatus.COMPLETED:
                status_item.setForeground(Qt.GlobalColor.green)
            elif task.status == TaskStatus.FAILED:
                status_item.setForeground(Qt.GlobalColor.red)
            self.history_table.setItem(row, 2, status_item)
            
            # Date (placeholder)
            self.history_table.setItem(row, 3, QTableWidgetItem("-"))
            
            # Errors
            errors_text = "; ".join(task.errors) if task.errors else "-"
            self.history_table.setItem(row, 4, QTableWidgetItem(errors_text))
    
    def _on_clear_history(self):
        """Clear download history."""
        self.task_manager.clear_completed()
        self._refresh_history()
    
    def showEvent(self, event):
        """Refresh when page is shown."""
        super().showEvent(event)
        self._refresh_history()
