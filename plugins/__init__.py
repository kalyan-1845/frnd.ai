"""
Plugin System
=============
Modular plugin architecture for extensibility.
"""

from plugins.base import (
    PluginBase,
    PluginType,
    PluginState,
    PluginMetadata,
    ToolPlugin,
    TriggerPlugin
)
from plugins.manager import PluginManager, get_plugin_manager
from plugins.registry import PluginRegistry, register_builtin_plugins

__all__ = [
    "PluginBase",
    "PluginType", 
    "PluginState",
    "PluginMetadata",
    "ToolPlugin",
    "TriggerPlugin",
    "PluginManager",
    "get_plugin_manager",
    "PluginRegistry",
    "register_builtin_plugins",
]
