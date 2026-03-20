"""
Plugin System — Base Classes
==============================
Defines the interface contract for all plugins.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

class PluginType(Enum):
    """Categories of plugins."""
    INTERFACE = "interface"      # UI, voice, avatar
    INTELLIGENCE = "intelligence" # AI, reasoning
    AUTOMATION = "automation"    # Task execution
    INTEGRATION = "integration"  # External APIs
    SECURITY = "security"        # Auth, monitoring
    CUSTOM = "custom"            # User-defined

class PluginState(Enum):
    """Plugin lifecycle states."""
    UNLOADED = "unloaded"
    LOADED = "loaded"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"

@dataclass
class PluginMetadata:
    """Plugin information and configuration."""
    name: str
    version: str
    author: str
    description: str
    plugin_type: PluginType
    dependencies: List[str] = None
    config_schema: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.config_schema is None:
            self.config_schema = {}

class PluginBase(ABC):
    """
    Abstract base class for all plugins.
    
    All plugins must inherit from this class and implement
    the required methods.
    """
    
    def __init__(self):
        self._state = PluginState.UNLOADED
        self._metadata: Optional[PluginMetadata] = None
        self._config: Dict[str, Any] = {}
        self._hooks: Dict[str, List[Callable]] = {}
        self._resources: List[Any] = []  # Track resources for cleanup
    
    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata."""
        return self._metadata
    
    @property
    def state(self) -> PluginState:
        """Get current plugin state."""
        return self._state
    
    @property
    def name(self) -> str:
        """Get plugin name."""
        return self._metadata.name if self._metadata else "Unknown"
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the plugin with configuration.
        
        Args:
            config: Plugin-specific configuration dictionary
            
        Returns:
            True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    def activate(self) -> bool:
        """
        Activate the plugin (start operations).
        
        Returns:
            True if activation successful
        """
        pass
    
    @abstractmethod
    def deactivate(self) -> bool:
        """
        Deactivate the plugin (stop operations).
        
        Returns:
            True if deactivation successful
        """
        pass
    
    def cleanup(self):
        """
        Clean up plugin resources.
        Called when plugin is unloaded.
        """
        for resource in self._resources:
            try:
                if hasattr(resource, 'close'):
                    resource.close()
                elif hasattr(resource, 'cleanup'):
                    resource.cleanup()
            except Exception:
                pass
        self._resources.clear()
    
    def register_hook(self, event: str, callback: Callable):
        """
        Register a callback for a specific event.
        
        Args:
            event: Event name (e.g., "on_command", "on_startup")
            callback: Function to call when event occurs
        """
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)
    
    def trigger_hook(self, event: str, *args, **kwargs) -> List[Any]:
        """
        Trigger all callbacks for an event.
        
        Args:
            event: Event name
            *args, **kwargs: Arguments to pass to callbacks
            
        Returns:
            List of results from callbacks
        """
        results = []
        if event in self._hooks:
            for callback in self._hooks[event]:
                try:
                    result = callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    # Log error but continue
                    results.append({"error": str(e)})
        return results
    
    def get_tools(self) -> Dict[str, Callable]:
        """
        Get tools/functions provided by this plugin.
        
        Returns:
            Dictionary mapping tool names to callables
        """
        return {}
    
    def get_commands(self) -> List[str]:
        """
        Get voice/text commands this plugin handles.
        
        Returns:
            List of command patterns
        """
        return []
    
    def _set_state(self, state: PluginState):
        """Internal method to update state."""
        self._state = state


class ToolPlugin(PluginBase):
    """Plugin that provides callable tools/functions."""
    
    def get_tools(self) -> Dict[str, Callable]:
        """Override to return plugin's tools."""
        return {}


class TriggerPlugin(PluginBase):
    """Plugin that responds to specific command patterns."""
    
    def get_commands(self) -> List[str]:
        """Override to return trigger patterns."""
        return []


# Plugin interface for the manager
class IPluginManager(ABC):
    """Interface for plugin management."""
    
    @abstractmethod
    def load_plugin(self, plugin_path: str) -> bool:
        pass
    
    @abstractmethod
    def unload_plugin(self, plugin_name: str) -> bool:
        pass
    
    @abstractmethod
    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        pass
    
    @abstractmethod
    def get_all_plugins(self) -> List[PluginBase]:
        pass
    
    @abstractmethod
    def register_tool(self, name: str, func: Callable):
        pass
