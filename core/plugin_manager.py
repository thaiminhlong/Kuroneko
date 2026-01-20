"""
Plugin manager for discovering, loading, and managing plugins.
"""
import importlib.util
import sys
from pathlib import Path
from typing import Optional
import traceback

from .plugin_interface import PluginInterface, PLUGIN_API_VERSION
from .event_bus import EventBus, Event, EventType


class PluginManager:
    """
    Manages plugin discovery, loading, and lifecycle.
    """
    
    def __init__(self, plugins_dir: Path):
        """
        Initialize the plugin manager.
        
        Args:
            plugins_dir: Directory to scan for plugins
        """
        self.plugins_dir = plugins_dir
        self.plugins: dict[str, PluginInterface] = {}
        self.load_errors: dict[str, str] = {}
        self.event_bus = EventBus()
        
        # Create plugins directory if it doesn't exist
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
    
    def discover_and_load(self) -> int:
        """
        Discover and load all plugins from the plugins directory.
        
        Returns:
            Number of successfully loaded plugins
        """
        self.plugins.clear()
        self.load_errors.clear()
        
        if not self.plugins_dir.exists():
            self.event_bus.emit_log("warning", f"Plugins directory not found: {self.plugins_dir}")
            return 0
        
        loaded = 0
        
        # Look for plugin directories (each plugin is a package)
        for item in self.plugins_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                plugin_file = item / "plugin.py"
                if plugin_file.exists():
                    if self._load_plugin(plugin_file, item.name):
                        loaded += 1
            # Also support single-file plugins
            elif item.is_file() and item.suffix == ".py" and not item.name.startswith("_"):
                if self._load_plugin(item, item.stem):
                    loaded += 1
        
        self.event_bus.emit_log("info", f"Loaded {loaded} plugin(s)")
        return loaded
    
    def _load_plugin(self, plugin_path: Path, plugin_name: str) -> bool:
        """
        Load a single plugin from a file.
        
        Args:
            plugin_path: Path to the plugin file
            plugin_name: Name for the plugin module
            
        Returns:
            True if successfully loaded
        """
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(
                f"plugins.{plugin_name}",
                plugin_path
            )
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load spec for {plugin_path}")
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            # Find the plugin class
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type) and 
                    issubclass(attr, PluginInterface) and 
                    attr is not PluginInterface):
                    plugin_class = attr
                    break
            
            if plugin_class is None:
                raise ImportError(f"No PluginInterface subclass found in {plugin_path}")
            
            # Check API version
            if not hasattr(plugin_class, "PLUGIN_API_VERSION"):
                raise ImportError(f"Plugin missing PLUGIN_API_VERSION")
            
            if plugin_class.PLUGIN_API_VERSION != PLUGIN_API_VERSION:
                raise ImportError(
                    f"Plugin API version mismatch: "
                    f"plugin={plugin_class.PLUGIN_API_VERSION}, "
                    f"required={PLUGIN_API_VERSION}"
                )
            
            # Instantiate the plugin
            plugin = plugin_class()
            plugin_id = plugin.id
            
            self.plugins[plugin_id] = plugin
            self.event_bus.publish_to_queue(Event(
                type=EventType.PLUGIN_LOADED,
                payload={"plugin_id": plugin_id, "name": plugin.name}
            ))
            self.event_bus.emit_log("info", f"Loaded plugin: {plugin.name} v{plugin.version}")
            return True
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
            self.load_errors[plugin_name] = error_msg
            self.event_bus.publish_to_queue(Event(
                type=EventType.PLUGIN_ERROR,
                payload={"plugin_name": plugin_name, "error": str(e)}
            ))
            self.event_bus.emit_log("error", f"Failed to load plugin {plugin_name}: {e}")
            return False
    
    def get_plugin(self, plugin_id: str) -> Optional[PluginInterface]:
        """Get a plugin by its ID."""
        return self.plugins.get(plugin_id)
    
    def get_plugin_for_url(self, url: str) -> Optional[PluginInterface]:
        """
        Find a plugin that can handle the given URL.
        
        Args:
            url: The URL to match
            
        Returns:
            The first matching enabled plugin, or None
        """
        for plugin in self.plugins.values():
            if plugin.enabled and plugin.can_handle(url):
                return plugin
        return None
    
    def get_all_plugins(self) -> list[PluginInterface]:
        """Get all loaded plugins."""
        return list(self.plugins.values())
    
    def get_enabled_plugins(self) -> list[PluginInterface]:
        """Get all enabled plugins."""
        return [p for p in self.plugins.values() if p.enabled]
    
    def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a plugin."""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].enabled = True
            self.event_bus.publish_to_queue(Event(
                type=EventType.PLUGIN_ENABLED,
                payload={"plugin_id": plugin_id}
            ))
            return True
        return False
    
    def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin."""
        if plugin_id in self.plugins:
            self.plugins[plugin_id].enabled = False
            self.event_bus.publish_to_queue(Event(
                type=EventType.PLUGIN_DISABLED,
                payload={"plugin_id": plugin_id}
            ))
            return True
        return False
    
    def reload_plugins(self) -> int:
        """Reload all plugins."""
        # Cleanup existing plugins
        for plugin in self.plugins.values():
            try:
                plugin.cleanup()
            except Exception as e:
                self.event_bus.emit_log("warning", f"Error cleaning up plugin: {e}")
        
        return self.discover_and_load()
    
    def get_plugin_info(self) -> list[dict]:
        """Get info about all plugins for display."""
        info = []
        for plugin_id, plugin in self.plugins.items():
            info.append({
                "id": plugin_id,
                "name": plugin.name,
                "version": plugin.version,
                "author": plugin.author,
                "description": plugin.description,
                "domains": plugin.supported_domains,
                "enabled": plugin.enabled,
                "api_version": plugin.PLUGIN_API_VERSION,
            })
        return info
