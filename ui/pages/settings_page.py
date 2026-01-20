"""
Settings page - configure application settings.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QLineEdit, QSpinBox,
    QDoubleSpinBox, QFileDialog, QGroupBox,
    QFormLayout, QCheckBox, QScrollArea
)
from PySide6.QtCore import Qt
from pathlib import Path
import json

from ..styles import Colors


class SettingsPage(QWidget):
    """Page for application settings."""
    
    SETTINGS_FILE = "settings.json"
    
    def __init__(self, settings: dict):
        super().__init__()
        self.settings = settings
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        """Setup the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Page title
        title = QLabel("Settings")
        title.setObjectName("page_title")
        layout.addWidget(title)
        
        # Scroll area for settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(25, 10, 25, 25)
        content_layout.setSpacing(20)
        
        # Download settings
        download_group = QGroupBox("Download Settings")
        download_layout = QFormLayout(download_group)
        download_layout.setSpacing(15)
        
        # Download folder
        folder_row = QHBoxLayout()
        self.download_folder = QLineEdit()
        self.download_folder.setPlaceholderText("Select download folder...")
        folder_row.addWidget(self.download_folder)
        
        browse_btn = QPushButton("Browse")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._on_browse_folder)
        folder_row.addWidget(browse_btn)
        
        download_layout.addRow("Download Folder:", folder_row)
        
        # Max parallel downloads
        self.max_parallel = QSpinBox()
        self.max_parallel.setRange(1, 10)
        self.max_parallel.setValue(3)
        download_layout.addRow("Max Parallel Downloads:", self.max_parallel)
        
        # Create chapter folders
        self.chapter_folders = QCheckBox("Create folder for each chapter")
        self.chapter_folders.setChecked(True)
        download_layout.addRow("", self.chapter_folders)
        
        # Overwrite existing
        self.overwrite_existing = QCheckBox("Overwrite existing files")
        self.overwrite_existing.setChecked(False)
        download_layout.addRow("", self.overwrite_existing)
        
        content_layout.addWidget(download_group)
        
        # Network settings
        network_group = QGroupBox("Network Settings")
        network_layout = QFormLayout(network_group)
        network_layout.setSpacing(15)
        
        # Retry count
        self.retry_count = QSpinBox()
        self.retry_count.setRange(0, 10)
        self.retry_count.setValue(3)
        network_layout.addRow("Retry Count:", self.retry_count)
        
        # Timeout
        self.timeout = QSpinBox()
        self.timeout.setRange(5, 120)
        self.timeout.setValue(30)
        self.timeout.setSuffix(" seconds")
        network_layout.addRow("Request Timeout:", self.timeout)
        
        # Global rate limit
        self.rate_limit = QDoubleSpinBox()
        self.rate_limit.setRange(0.0, 10.0)
        self.rate_limit.setValue(0.5)
        self.rate_limit.setSuffix(" seconds")
        self.rate_limit.setDecimals(1)
        self.rate_limit.setSingleStep(0.1)
        network_layout.addRow("Rate Limit (delay between requests):", self.rate_limit)
        
        # User agent
        self.user_agent = QLineEdit()
        self.user_agent.setPlaceholderText("Leave empty for default")
        network_layout.addRow("User Agent:", self.user_agent)
        
        content_layout.addWidget(network_group)
        
        # File naming settings
        naming_group = QGroupBox("File Naming")
        naming_layout = QFormLayout(naming_group)
        naming_layout.setSpacing(15)
        
        # Chapter format
        self.chapter_format = QLineEdit()
        self.chapter_format.setText("{manga_title}/Chapter {chapter_number}")
        self.chapter_format.setPlaceholderText("{manga_title}/Chapter {chapter_number}")
        naming_layout.addRow("Chapter Folder Format:", self.chapter_format)
        
        # Page format
        self.page_format = QLineEdit()
        self.page_format.setText("{page_number:03d}")
        self.page_format.setPlaceholderText("{page_number:03d}")
        naming_layout.addRow("Page File Format:", self.page_format)
        
        format_help = QLabel(
            "Available variables: {manga_title}, {chapter_number}, {chapter_title}, "
            "{page_number}, {translation_team}"
        )
        format_help.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px;")
        format_help.setWordWrap(True)
        naming_layout.addRow("", format_help)
        
        content_layout.addWidget(naming_group)
        
        # Appearance settings
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout(appearance_group)
        appearance_layout.setSpacing(15)
        
        # Show notifications
        self.show_notifications = QCheckBox("Show desktop notifications on completion")
        self.show_notifications.setChecked(True)
        appearance_layout.addRow("", self.show_notifications)
        
        # Minimize to tray
        self.minimize_to_tray = QCheckBox("Minimize to system tray")
        self.minimize_to_tray.setChecked(False)
        appearance_layout.addRow("", self.minimize_to_tray)
        
        content_layout.addWidget(appearance_group)
        
        # Spacer
        content_layout.addStretch()
        
        # Save button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.clicked.connect(self._on_reset)
        button_layout.addWidget(self.reset_btn)
        
        self.save_btn = QPushButton("Save Settings")
        self.save_btn.setObjectName("primary_button")
        self.save_btn.setCursor(Qt.PointingHandCursor)
        self.save_btn.clicked.connect(self._on_save)
        button_layout.addWidget(self.save_btn)
        
        content_layout.addLayout(button_layout)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
    
    def _on_browse_folder(self):
        """Browse for download folder."""
        folder = QFileDialog.getExistingDirectory(
            self, "Select Download Folder",
            self.download_folder.text() or str(Path.home())
        )
        if folder:
            self.download_folder.setText(folder)
    
    def _on_save(self):
        """Save settings."""
        self.settings["download_folder"] = self.download_folder.text()
        self.settings["max_parallel_downloads"] = self.max_parallel.value()
        self.settings["chapter_folders"] = self.chapter_folders.isChecked()
        self.settings["overwrite_existing"] = self.overwrite_existing.isChecked()
        self.settings["retry_count"] = self.retry_count.value()
        self.settings["timeout"] = self.timeout.value()
        self.settings["rate_limit"] = self.rate_limit.value()
        self.settings["user_agent"] = self.user_agent.text()
        self.settings["chapter_format"] = self.chapter_format.text()
        self.settings["page_format"] = self.page_format.text()
        self.settings["show_notifications"] = self.show_notifications.isChecked()
        self.settings["minimize_to_tray"] = self.minimize_to_tray.isChecked()
        
        # Save to file
        try:
            with open(self.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def _on_reset(self):
        """Reset to default settings."""
        defaults = self._get_defaults()
        self._apply_settings(defaults)
    
    def _load_settings(self):
        """Load settings from file."""
        defaults = self._get_defaults()
        
        try:
            if Path(self.SETTINGS_FILE).exists():
                with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                defaults.update(saved)
        except Exception as e:
            print(f"Error loading settings: {e}")
        
        self.settings.update(defaults)
        self._apply_settings(defaults)
    
    def _apply_settings(self, settings: dict):
        """Apply settings to UI widgets."""
        self.download_folder.setText(settings.get("download_folder", ""))
        self.max_parallel.setValue(settings.get("max_parallel_downloads", 3))
        self.chapter_folders.setChecked(settings.get("chapter_folders", True))
        self.overwrite_existing.setChecked(settings.get("overwrite_existing", False))
        self.retry_count.setValue(settings.get("retry_count", 3))
        self.timeout.setValue(settings.get("timeout", 30))
        self.rate_limit.setValue(settings.get("rate_limit", 0.5))
        self.user_agent.setText(settings.get("user_agent", ""))
        self.chapter_format.setText(settings.get("chapter_format", "{manga_title}/Chapter {chapter_number}"))
        self.page_format.setText(settings.get("page_format", "{page_number:03d}"))
        self.show_notifications.setChecked(settings.get("show_notifications", True))
        self.minimize_to_tray.setChecked(settings.get("minimize_to_tray", False))
    
    def _get_defaults(self) -> dict:
        """Get default settings."""
        return {
            "download_folder": str(Path.home() / "Downloads" / "MangaDL"),
            "max_parallel_downloads": 3,
            "chapter_folders": True,
            "overwrite_existing": False,
            "retry_count": 3,
            "timeout": 30,
            "rate_limit": 0.5,
            "user_agent": "",
            "chapter_format": "{manga_title}/Chapter {chapter_number}",
            "page_format": "{page_number:03d}",
            "show_notifications": True,
            "minimize_to_tray": False,
        }
