"""
Plugins page - manage and test plugins.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QFrame, QLineEdit, QTextEdit,
    QCheckBox, QAbstractItemView, QGroupBox
)
from PySide6.QtCore import Qt
import subprocess
import sys
from pathlib import Path

from core import PluginManager
from ..styles import Colors


class PluginsPage(QWidget):
    """Page for managing plugins."""
    
    def __init__(self, plugin_manager: PluginManager):
        super().__init__()
        self.plugin_manager = plugin_manager
        self._setup_ui()
        self._refresh_plugins()
    
    def _setup_ui(self):
        """Setup the page UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Page title
        title = QLabel("Plugins")
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
        info_layout = QVBoxLayout(info_card)
        
        info_label = QLabel(
            "🔌 Plugins extend MangaDL to support different manga websites. "
            "Each plugin handles URL matching, metadata fetching, and downloading for specific sites."
        )
        info_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        
        button_row = QHBoxLayout()
        
        self.open_folder_btn = QPushButton("Open Plugins Folder")
        self.open_folder_btn.setCursor(Qt.PointingHandCursor)
        self.open_folder_btn.clicked.connect(self._on_open_folder)
        button_row.addWidget(self.open_folder_btn)
        
        self.reload_btn = QPushButton("Reload Plugins")
        self.reload_btn.setCursor(Qt.PointingHandCursor)
        self.reload_btn.clicked.connect(self._on_reload_plugins)
        button_row.addWidget(self.reload_btn)
        
        button_row.addStretch()
        info_layout.addLayout(button_row)
        
        content_layout.addWidget(info_card)
        
        # Plugins table
        header_layout = QHBoxLayout()
        header_label = QLabel("INSTALLED PLUGINS")
        header_label.setObjectName("section_label")
        header_layout.addWidget(header_label)
        
        self.plugin_count_label = QLabel("0 plugins")
        self.plugin_count_label.setStyleSheet(f"color: {Colors.TEXT_MUTED};")
        header_layout.addWidget(self.plugin_count_label)
        
        header_layout.addStretch()
        content_layout.addLayout(header_layout)
        
        self.plugins_table = QTableWidget()
        self.plugins_table.setColumnCount(6)
        self.plugins_table.setHorizontalHeaderLabels([
            "Enabled", "Name", "Version", "Domains", "Author", "API Version"
        ])
        
        self.plugins_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.plugins_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.plugins_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.plugins_table.setShowGrid(False)
        self.plugins_table.verticalHeader().setVisible(False)
        
        header = self.plugins_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        
        content_layout.addWidget(self.plugins_table)
        
        # Test URL section
        test_group = QGroupBox("Test URL")
        test_layout = QVBoxLayout(test_group)
        
        url_row = QHBoxLayout()
        
        self.test_url_input = QLineEdit()
        self.test_url_input.setPlaceholderText("Enter a URL to test which plugin handles it...")
        url_row.addWidget(self.test_url_input)
        
        self.test_btn = QPushButton("Test")
        self.test_btn.setObjectName("primary_button")
        self.test_btn.setCursor(Qt.PointingHandCursor)
        self.test_btn.clicked.connect(self._on_test_url)
        url_row.addWidget(self.test_btn)
        
        test_layout.addLayout(url_row)
        
        self.test_result = QTextEdit()
        self.test_result.setReadOnly(True)
        self.test_result.setMaximumHeight(100)
        self.test_result.setPlaceholderText("Test results will appear here...")
        test_layout.addWidget(self.test_result)
        
        content_layout.addWidget(test_group)
        
        # Load errors section
        errors_layout = QHBoxLayout()
        errors_label = QLabel("LOAD ERRORS")
        errors_label.setObjectName("section_label")
        errors_layout.addWidget(errors_label)
        errors_layout.addStretch()
        content_layout.addLayout(errors_layout)
        
        self.errors_text = QTextEdit()
        self.errors_text.setReadOnly(True)
        self.errors_text.setMaximumHeight(100)
        self.errors_text.setObjectName("log_console")
        self.errors_text.setPlaceholderText("No load errors")
        content_layout.addWidget(self.errors_text)
        
        layout.addWidget(content)
    
    def _refresh_plugins(self):
        """Refresh the plugins table."""
        plugins_info = self.plugin_manager.get_plugin_info()
        self.plugin_count_label.setText(f"{len(plugins_info)} plugins")
        
        self.plugins_table.setRowCount(len(plugins_info))
        
        for row, info in enumerate(plugins_info):
            # Enabled checkbox
            checkbox = QCheckBox()
            checkbox.setChecked(info["enabled"])
            checkbox.stateChanged.connect(
                lambda state, pid=info["id"]: self._on_toggle_plugin(pid, state)
            )
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.plugins_table.setCellWidget(row, 0, checkbox_widget)
            
            # Name
            self.plugins_table.setItem(row, 1, QTableWidgetItem(info["name"]))
            
            # Version
            self.plugins_table.setItem(row, 2, QTableWidgetItem(info["version"]))
            
            # Domains
            domains_text = ", ".join(info["domains"][:3])
            if len(info["domains"]) > 3:
                domains_text += f" (+{len(info['domains']) - 3} more)"
            self.plugins_table.setItem(row, 3, QTableWidgetItem(domains_text))
            
            # Author
            self.plugins_table.setItem(row, 4, QTableWidgetItem(info["author"]))
            
            # API Version
            self.plugins_table.setItem(row, 5, QTableWidgetItem(str(info["api_version"])))
        
        # Update errors
        errors = self.plugin_manager.load_errors
        if errors:
            error_text = "\n\n".join(
                f"❌ {name}:\n{error}" for name, error in errors.items()
            )
            self.errors_text.setText(error_text)
        else:
            self.errors_text.clear()
    
    def _on_toggle_plugin(self, plugin_id: str, state: int):
        """Toggle a plugin's enabled state."""
        if state == Qt.CheckState.Checked.value:
            self.plugin_manager.enable_plugin(plugin_id)
        else:
            self.plugin_manager.disable_plugin(plugin_id)
    
    def _on_open_folder(self):
        """Open the plugins folder."""
        folder = self.plugin_manager.plugins_dir
        folder.mkdir(parents=True, exist_ok=True)
        
        if sys.platform == "win32":
            subprocess.run(["explorer", str(folder)])
        elif sys.platform == "darwin":
            subprocess.run(["open", str(folder)])
        else:
            subprocess.run(["xdg-open", str(folder)])
    
    def _on_reload_plugins(self):
        """Reload all plugins."""
        count = self.plugin_manager.reload_plugins()
        self._refresh_plugins()
        self.test_result.setText(f"✅ Reloaded {count} plugin(s)")
    
    def _on_test_url(self):
        """Test which plugin handles a URL."""
        url = self.test_url_input.text().strip()
        if not url:
            self.test_result.setText("⚠️ Please enter a URL to test")
            return
        
        plugin = self.plugin_manager.get_plugin_for_url(url)
        
        if plugin:
            self.test_result.setText(
                f"✅ URL matched!\n\n"
                f"Plugin: {plugin.name} v{plugin.version}\n"
                f"Domains: {', '.join(plugin.supported_domains)}\n"
                f"Normalized URL: {plugin.normalize_url(url)}"
            )
        else:
            self.test_result.setText(
                f"❌ No plugin found for this URL\n\n"
                f"Make sure you have a plugin installed that supports this website."
            )
    
    def showEvent(self, event):
        """Refresh when page is shown."""
        super().showEvent(event)
        self._refresh_plugins()
