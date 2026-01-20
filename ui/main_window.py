"""
Main application window with sidebar navigation.
"""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame,
    QButtonGroup, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QIcon, QFont

from .styles import STYLES
from .pages.queue_page import QueuePage
from .pages.history_page import HistoryPage
from .pages.plugins_page import PluginsPage
from .pages.settings_page import SettingsPage
from core import PluginManager, TaskManager, EventBus


class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(self, plugin_manager: PluginManager, task_manager: TaskManager, settings: dict):
        super().__init__()
        
        self.plugin_manager = plugin_manager
        self.task_manager = task_manager
        self.settings = settings
        self.event_bus = EventBus()
        
        self.setWindowTitle("MangaDL")
        self.setMinimumSize(1200, 800)
        self.resize(1400, 900)
        
        # Apply styles
        self.setStyleSheet(STYLES)
        
        # Setup UI
        self._setup_ui()
        
        # Start event processing timer
        self._event_timer = QTimer(self)
        self._event_timer.timeout.connect(self._process_events)
        self._event_timer.start(50)  # 20 fps
    
    def _setup_ui(self):
        """Setup the main UI layout."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)
        
        # Content area
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("content_area")
        main_layout.addWidget(self.content_stack)
        
        # Create pages
        self.queue_page = QueuePage(self.task_manager, self.plugin_manager, self.settings)
        self.history_page = HistoryPage(self.task_manager)
        self.plugins_page = PluginsPage(self.plugin_manager)
        self.settings_page = SettingsPage(self.settings)
        
        self.content_stack.addWidget(self.queue_page)
        self.content_stack.addWidget(self.history_page)
        self.content_stack.addWidget(self.plugins_page)
        self.content_stack.addWidget(self.settings_page)
        
        # Default to queue page
        self.content_stack.setCurrentIndex(0)
        self.nav_buttons[0].setChecked(True)
    
    def _create_sidebar(self) -> QWidget:
        """Create the sidebar navigation."""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(200)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # App title
        title = QLabel("🔥 MangaDL")
        title.setObjectName("sidebar_title")
        layout.addWidget(title)
        
        # Navigation buttons
        nav_items = [
            ("📥  Queue", 0),
            ("📚  History", 1),
            ("🔌  Plugins", 2),
            ("⚙️  Settings", 3),
        ]
        
        self.nav_buttons = []
        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        
        layout.addSpacing(20)
        
        for label, index in nav_items:
            btn = QPushButton(label)
            btn.setObjectName("nav_button")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=index: self._navigate_to(idx))
            
            self.nav_buttons.append(btn)
            self.nav_group.addButton(btn, index)
            layout.addWidget(btn)
        
        # Spacer
        layout.addStretch()
        
        # Version info
        version_label = QLabel("v1.0.0")
        version_label.setObjectName("section_label")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        layout.addSpacing(15)
        
        return sidebar
    
    def _navigate_to(self, index: int):
        """Navigate to a page by index."""
        self.content_stack.setCurrentIndex(index)
        self.nav_buttons[index].setChecked(True)
    
    def _process_events(self):
        """Process queued events from the event bus."""
        self.event_bus.process_queue(50)
    
    def closeEvent(self, event):
        """Handle window close."""
        # Stop task manager
        self.task_manager.stop()
        
        # Stop event timer
        self._event_timer.stop()
        
        event.accept()
