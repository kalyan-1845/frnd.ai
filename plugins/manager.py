"""
Plugin System — Plugin Manager
===============================
Manages plugin discovery, loading, lifecycle, and execution.
"""

import os
import sys
import importlib
import inspect
import json
from typing import Dict, List, Optional, Any, Callable, Type
from pathlib import Path

from plugins.base import (
    PluginBase, PluginMetadata, PluginType, PluginState,
    ToolPlugin, TriggerPlugin, IPluginManager
)

class PluginManager(IPluginManager):
    """
    Central plugin management system.
    Handles discovery, loading, lifecycle, and tool registration.
    """
    
    def __init__(self, plugin_dir: str = "plugins"):
        self.plugin_dir = plugin_dir
        self._plugins: Dict[str, PluginBase] = {}
        self._tools: Dict[str, Callable] = {}
        self._triggers: Dict[str, List[str]] = {}  # pattern -> [plugin_names]
        self._hooks: Dict[str, List[Callable]] = {}
        self._plugin_classes: Dict[str, Type[PluginBase]] = {}
        
        # Auto-discover plugins
        self._discover_plugins()
    
    def _discover_plugins(self):
        """Auto-discover plugin classes in the plugins directory."""
        if not os.path.exists(self.plugin_dir):
            return
        
        # Look for plugin files
        for filename in os.listdir(self.plugin_dir):
            if filename.endswith(".py") and not filename.startswith("_"):
                module_name = filename[:-3]
                self._load_plugin_class(module_name)
    
    def _load_plugin_class(self, module_name: str):
        """Load a plugin class from a module."""
        try:
            # Import the module
            if module_name == "base":
                return  # Skip base module
                
            module = importlib.import_module(f"plugins.{module_name}")
            
            # Find plugin classes in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, PluginBase) and obj is not PluginBase:
                    self._plugin_classes[name.lower()] = obj
                    
        except Exception as e:
            print(f"[PluginManager] Failed to load {module_name}: {e}")
    
    def load_plugin(self, plugin_path: str) -> bool:
        """
        Load and initialize a plugin.
        
        Args:
            plugin_path: Path to plugin file or plugin name
            
        Returns:
            True if successful
        """
        # Handle both path and name
        plugin_name = os.path.splitext(os.path.basename(plugin_path))[0]
        
        if plugin_name in self._plugins:
            print(f"[PluginManager] Plugin '{plugin_name}' already loaded")
            return True
        
        # Try to get the plugin class
        plugin_class = self._plugin_classes.get(plugin_name.lower())
        
        if not plugin_class:
            print(f"[PluginManager] Plugin class not found: {plugin_name}")
            return False
        
        try:
            # Instantiate
            plugin = plugin_class()
            
            # Get metadata
            if not hasattr(plugin, '_metadata') or not plugin._metadata:
                # Try to get from class
                plugin._metadata = getattr(plugin_class, 'METADATA', None)
            
            # Initialize
            config = self._load_plugin_config(plugin_name)
            if not plugin.initialize(config):
                print(f"[PluginManager] Failed to initialize: {plugin_name}")
                plugin._set_state(PluginState.ERROR)
                return False
            
            plugin._set_state(PluginState.LOADED)
            
            # Activate
            if not plugin.activate():
                print(f"[PluginManager] Failed to activate: {plugin_name}")
                plugin._set_state(PluginState.ERROR)
                return False
            
            plugin._set_state(PluginState.ACTIVE)
            
            # Register tools
            tools = plugin.get_tools()
            for tool_name, tool_func in tools.items():
                full_name = f"{plugin_name}.{tool_name}"
                self._tools[full_name] = tool_func
            
            # Register triggers
            for trigger in plugin.get_commands():
                if trigger not in self._triggers:
                    self._triggers[trigger] = []
                self._triggers[trigger].append(plugin_name)
            
            # Store plugin
            self._plugins[plugin_name] = plugin
            
            print(f"[PluginManager] Loaded: {plugin_name}")
            return True
            
        except Exception as e:
            print(f"[PluginManager] Error loading {plugin_name}: {e}")
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin.
        
        Args:
            plugin_name: Name of plugin to unload
            
        Returns:
            True if successful
        """
        if plugin_name not in self._plugins:
            return False
        
        plugin = self._plugins[plugin_name]
        
        try:
            # Deactivate
            plugin.deactivate()
            plugin._set_state(PluginState.UNLOADED)
            
            # Cleanup
            plugin.cleanup()
            
            # Unregister tools
            tools_to_remove = [
                name for name in self._tools 
                if name.startswith(f"{plugin_name}.")
            ]
            for tool_name in tools_to_remove:
                del self._tools[tool_name]
            
            # Unregister triggers
            for trigger in list(self._triggers.keys()):
                if plugin_name in self._triggers[trigger]:
                    self._triggers[trigger].remove(plugin_name)
                if not self._triggers[trigger]:
                    del self._triggers[trigger]
            
            # Remove from registry
            del self._plugins[plugin_name]
            
            print(f"[PluginManager] Unloaded: {plugin_name}")
            return True
            
        except Exception as e:
            print(f"[PluginManager] Error unloading {plugin_name}: {e}")
            return False
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginBase]:
        """Get a loaded plugin by name."""
        return self._plugins.get(plugin_name)
    
    def get_all_plugins(self) -> List[PluginBase]:
        """Get all loaded plugins."""
        return list(self._plugins.values())
    
    def get_plugins_by_type(self, plugin_type: PluginType) -> List[PluginBase]:
        """Get all plugins of a specific type."""
        return [
            p for p in self._plugins.values()
            if p.metadata and p.metadata.plugin_type == plugin_type
        ]
    
    def register_tool(self, name: str, func: Callable):
        """Register a tool function."""
        self._tools[name] = func
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a registered tool."""
        return self._tools.get(name)
    
    def get_all_tools(self) -> Dict[str, Callable]:
        """Get all registered tools."""
        return self._tools.copy()
    
    def register_hook(self, event: str, callback: Callable):
        """Register a global hook."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)
    
    def trigger_hook(self, event: str, *args, **kwargs) -> List[Any]:
        """Trigger all hooks for an event."""
        results = []
        if event in self._hooks:
            for callback in self._hooks[event]:
                try:
                    result = callback(*args, **kwargs)
                    results.append(result)
                except Exception as e:
                    results.append({"error": str(e)})
        return results
    
    def find_matching_plugins(self, command: str) -> List[str]:
        """Find plugins that handle a given command."""
        matches = []
        command_lower = command.lower()
        
        for trigger, plugin_names in self._triggers.items():
            trigger_lower = trigger.lower()
            if trigger_lower in command_lower:
                matches.extend(plugin_names)
        
        return list(set(matches))
    
    def _load_plugin_config(self, plugin_name: str) -> Dict[str, Any]:
        """Load plugin configuration from file."""
        config_path = os.path.join(self.plugin_dir, f"{plugin_name}.json")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return {}
    
    def save_plugin_config(self, plugin_name: str, config: Dict[str, Any]):
        """Save plugin configuration to file."""
        config_path = os.path.join(self.plugin_dir, f"{plugin_name}.json")
        
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"[PluginManager] Failed to save config for {plugin_name}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all plugins."""
        return {
            "total_loaded": len(self._plugins),
            "total_tools": len(self._tools),
            "total_triggers": len(self._triggers),
            "plugins": {
                name: {
                    "state": plugin.state.value,
                    "type": plugin.metadata.plugin_type.value if plugin.metadata else "unknown",
                    "version": plugin.metadata.version if plugin.metadata else "unknown"
                }
                for name, plugin in self._plugins.items()
            }
        }


# Global instance
_plugin_manager: Optional[PluginManager] = None

def get_plugin_manager() -> PluginManager:
    """Get global plugin manager instance."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager
