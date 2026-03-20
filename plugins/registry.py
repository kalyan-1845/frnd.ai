"""
Plugin System — Registry
========================
Built-in plugin registry for core capabilities.
"""

from typing import Dict, Any, Callable, List
from plugins.base import PluginType, PluginMetadata, ToolPlugin, TriggerPlugin

class PluginRegistry:
    """
    Registry of built-in plugins.
    Maps plugin names to their implementations and metadata.
    """
    
    # Registry of available plugins
    _registry: Dict[str, type] = {}
    
    @classmethod
    def register(cls, name: str, plugin_class: type, metadata: PluginMetadata):
        """Register a plugin class with its metadata."""
        cls._registry[name] = {
            "class": plugin_class,
            "metadata": metadata
        }
    
    @classmethod
    def get(cls, name: str) -> type:
        """Get a registered plugin class."""
        return cls._registry.get(name, {}).get("class")
    
    @classmethod
    def get_metadata(cls, name: str) -> PluginMetadata:
        """Get plugin metadata."""
        return cls._registry.get(name, {}).get("metadata")
    
    @classmethod
    def list_all(cls) -> List[str]:
        """List all registered plugin names."""
        return list(cls._registry.keys())
    
    @classmethod
    def list_by_type(cls, plugin_type: PluginType) -> List[str]:
        """List plugins by type."""
        return [
            name for name, info in cls._registry.items()
            if info["metadata"].plugin_type == plugin_type
        ]


# Built-in tool plugins
class OpenFolderPlugin(ToolPlugin):
    """Plugin for folder operations."""
    
    METADATA = PluginMetadata(
        name="open_folder",
        version="1.0.0",
        author="BKR Team",
        description="Open and manage folders",
        plugin_type=PluginType.AUTOMATION
    )
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        return True
    
    def activate(self) -> bool:
        # Import actual implementation
        try:
            from automation.file_manager import open_folder
            self._open_folder = open_folder
            return True
        except ImportError:
            return False
    
    def deactivate(self) -> bool:
        return True
    
    def get_tools(self) -> Dict[str, Callable]:
        return {"open_folder": self._open_folder if hasattr(self, '_open_folder') else None}


class SearchPlugin(ToolPlugin):
    """Plugin for search operations."""
    
    METADATA = PluginMetadata(
        name="search",
        version="1.0.0",
        author="BKR Team",
        description="Google, YouTube, and web search",
        plugin_type=PluginType.AUTOMATION
    )
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        return True
    
    def activate(self) -> bool:
        try:
            from automation.browser import search_google, search_youtube
            self._search_google = search_google
            self._search_youtube = search_youtube
            return True
        except ImportError:
            return False
    
    def deactivate(self) -> bool:
        return True
    
    def get_tools(self) -> Dict[str, Callable]:
        return {
            "search_google": getattr(self, '_search_google', None),
            "search_youtube": getattr(self, '_search_youtube', None)
        }


class SystemControlPlugin(ToolPlugin):
    """Plugin for system control operations."""
    
    METADATA = PluginMetadata(
        name="system_control",
        version="1.0.0",
        author="BKR Team",
        description="System settings and controls",
        plugin_type=PluginType.AUTOMATION
    )
    
    def initialize(self, config: Dict[str, Any]) -> bool:
        return True
    
    def activate(self) -> bool:
        try:
            from system_control.system_settings import (
                lock_screen, system_sleep, set_brightness
            )
            from system_control.system_monitor import get_system_status
            self._tools = {
                "lock_screen": lock_screen,
                "system_sleep": system_sleep,
                "set_brightness": set_brightness,
                "system_status": get_system_status
            }
            return True
        except ImportError:
            return False
    
    def deactivate(self) -> bool:
        return True
    
    def get_tools(self) -> Dict[str, Callable]:
        return self._tools if hasattr(self, '_tools') else {}


# Register built-in plugins
def register_builtin_plugins():
    """Register all built-in plugins."""
    PluginRegistry.register("open_folder", OpenFolderPlugin, OpenFolderPlugin.METADATA)
    PluginRegistry.register("search", SearchPlugin, SearchPlugin.METADATA)
    PluginRegistry.register("system_control", SystemControlPlugin, SystemControlPlugin.METADATA)
