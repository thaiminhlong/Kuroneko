#!/usr/bin/env python3
"""
MangaDL - Manga Downloader Application

A modern desktop application for downloading manga with a plugin-based
architecture for supporting multiple websites.

Usage:
    python main.py
"""
import sys
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontDatabase

from core import PluginManager, TaskManager, EventBus
from ui import MainWindow


def setup_high_dpi():
    """Configure high DPI scaling."""
    # Qt6 handles this automatically, but we can set attributes if needed
    pass


def load_fonts():
    """Load custom fonts if available."""
    fonts_dir = PROJECT_ROOT / "assets" / "fonts"
    if fonts_dir.exists():
        for font_file in fonts_dir.glob("*.ttf"):
            QFontDatabase.addApplicationFont(str(font_file))


def main():
    """Main entry point."""
    # Setup
    setup_high_dpi()
    
    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("MangaDL")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("MangaDL")
    
    # Set default font
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Load custom fonts
    load_fonts()
    
    # Initialize settings
    settings = {
        "download_folder": str(Path.home() / "Downloads" / "MangaDL"),
        "max_parallel_downloads": 3,
        "retry_count": 3,
        "timeout": 30,
        "rate_limit": 0.5,
    }
    
    # Initialize plugin manager
    plugins_dir = PROJECT_ROOT / "plugins"
    plugin_manager = PluginManager(plugins_dir)
    plugin_manager.discover_and_load()
    
    # Initialize task manager
    task_manager = TaskManager(plugin_manager, settings)
    task_manager.start()
    
    # Create main window
    window = MainWindow(plugin_manager, task_manager, settings)
    window.show()
    
    # Run application
    exit_code = app.exec()
    
    # Cleanup
    task_manager.stop()
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
