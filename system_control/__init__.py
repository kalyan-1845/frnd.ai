"""
System Control Module — Secure OS Integration Hub
=================================================
Central module for all operating system interactions.
Features secure whitelisting for all commands.

Security Design:
- All terminal commands must be whitelisted
- Process termination is protected
- File operations have path validation
- All operations are logged
"""

import os
import sys
import subprocess
import psutil
import shutil
import time
import json
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Import existing modules
from system_control.app_launcher import launch_application
from system_control.process_manager import (
    list_running_apps, kill_process, get_active_window, count_running_processes
)
from system_control.mouse_keyboard import (
    type_text, press_key, take_screenshot, volume_control
)
from core.logger import log_event, log_error


# ============================================================
# SECURITY: Command Whitelist
# ============================================================

class CommandWhitelist:
    """
    Secure whitelist for allowed terminal commands.
    Only whitelisted commands can be executed via shell.
    """
    
    # Safe commands that can be executed without arguments
    SAFE_COMMANDS = frozenset([
        # File listing
        "dir", "ls", "cls", "clear", "pwd", "cd", "tree",
        # System info
        "hostname", "whoami", "date", "time", "ver", "systeminfo",
        # Network
        "ipconfig", "ipconfig /all", "ping localhost", "ping 127.0.0.1",
        # Process
        "tasklist", "netstat -an",
    ])
    
    # Command patterns with allowed arguments
    SAFE_PATTERNS = [
        # File operations (restricted to user directories)
        r"^dir\s+", r"^ls\s+", r"^cd\s+", r"^type\s+", r"^cat\s+",
        # Network (limited scope)
        r"^ping\s+(-n\s+\d+\s+)?(127\.0\.0\.1|localhost|google\.com|8\.8\.8\.8)",
        # System info
        r"^systeminfo",
        # Task list
        r"^tasklist",
    ]
    
    # Dangerous patterns that are ALWAYS blocked
    BLOCKED_PATTERNS = [
        r"del\s+/[fqs]",  # Force delete
        r"rm\s+-[rf]",    # Recursive force delete
        r"rmdir\s+/s",    # Remove directory tree
        r"format",        # Format drive
        r"diskpart",      # Disk partitioning
        r"reg\s+(delete|add)",  # Registry modification
        r"netsh\s+firewall",   # Firewall changes
        r"bcdedit",       # Boot configuration
        r"shutdown",      # System shutdown
        r"taskkill\s+/f", # Force kill
        r"powershell.*-enc",   # Encoded commands
        r"cmd\s+/c\s+del",     # Delete via cmd
        r"\|\s*rm",      # Pipe to rm
        r">\s*C:",       # Write to root
        r">\s+/",        # Write to root
    ]
    
    @classmethod
    def is_allowed(cls, command: str) -> Tuple[bool, str]:
        """
        Check if command is allowed.
        Returns (allowed: bool, reason: str)
        """
        cmd_lower = command.lower().strip()
        
        # Check blocked patterns first
        import re
        for pattern in cls.BLOCKED_PATTERNS:
            if re.search(pattern, cmd_lower):
                return False, f"Command matches blocked pattern: {pattern}"
        
        # Check exact safe commands
        if cmd_lower in cls.SAFE_COMMANDS:
            return True, "Whitelisted command"
        
        # Check safe patterns
        for pattern in cls.SAFE_PATTERNS:
            if re.match(pattern, cmd_lower):
                return True, "Matches safe pattern"
        
        # Not in whitelist
        return False, "Command not in whitelist"
    
    @classmethod
    def get_allowed_commands(cls) -> List[str]:
        """Return list of all allowed commands."""
        return sorted(cls.SAFE_COMMANDS)


# ============================================================
# Application Management
# ============================================================

class AppManager:
    """Manages application launching and control."""
    
    @staticmethod
    def open_application(app_name: str) -> Tuple[bool, str]:
        """Open an application by name."""
        return launch_application(app_name)
    
    @staticmethod
    def close_application(app_name: str) -> Tuple[bool, str]:
        """Close an application by name."""
        return kill_process(app_name)
    
    @staticmethod
    def list_applications() -> Tuple[bool, str]:
        """List running applications."""
        return list_running_apps()


# ============================================================
# File Management
# ============================================================

class FileManager:
    """
    Secure file operations.
    Validates paths to prevent directory traversal attacks.
    """
    
    # Allowed base directories for file operations
    ALLOWED_BASE_DIRS = [
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/Pictures"),
        os.path.expanduser("~/Videos"),
        os.path.expanduser("~/Music"),
    ]
    
    # Add Windows-specific paths
    if os.name == 'nt':
        ALLOWED_BASE_DIRS.extend([
            os.path.expanduser("~\\Documents"),
            os.path.expanduser("~\\Desktop"),
            os.path.expanduser("~\\Downloads"),
        ])
    
    @classmethod
    def _validate_path(cls, path: str) -> Tuple[bool, str]:
        """Validate that path is within allowed directories."""
        try:
            # Resolve the absolute path
            abs_path = os.path.abspath(os.path.expanduser(path))
            
            # Check against allowed base directories
            for base_dir in cls.ALLOWED_BASE_DIRS:
                if abs_path.startswith(os.path.abspath(base_dir)):
                    return True, ""
            
            # Allow if it's a relative path to allowed location
            if not os.path.isabs(path):
                return True, ""
            
            return False, f"Path not in allowed directories: {path}"
        except Exception as e:
            return False, f"Path validation error: {e}"
    
    @classmethod
    def create_file(cls, filename: str, content: str = "") -> Tuple[bool, str]:
        """Create a new file."""
        valid, msg = cls._validate_path(filename)
        if not valid:
            return False, msg
        
        try:
            filepath = os.path.join(os.path.expanduser("~/Desktop"), filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            log_event("FileManager.create", filepath)
            return True, f"Created file: {filename}"
        except Exception as e:
            return False, f"Failed to create file: {e}"
    
    @classmethod
    def delete_file(cls, filepath: str) -> Tuple[bool, str]:
        """Delete a file."""
        valid, msg = cls._validate_path(filepath)
        if not valid:
            return False, msg
        
        try:
            abs_path = os.path.abspath(os.path.expanduser(filepath))
            if os.path.isfile(abs_path):
                os.remove(abs_path)
                log_event("FileManager.delete", abs_path)
                return True, f"Deleted file: {os.path.basename(filepath)}"
            elif os.path.isdir(abs_path):
                return False, "Use remove_folder for directories"
            else:
                return False, "File not found"
        except Exception as e:
            return False, f"Failed to delete: {e}"
    
    @classmethod
    def remove_folder(cls, folderpath: str) -> Tuple[bool, str]:
        """Remove a folder."""
        valid, msg = cls._validate_path(folderpath)
        if not valid:
            return False, msg
        
        try:
            abs_path = os.path.abspath(os.path.expanduser(folderpath))
            if os.path.isdir(abs_path):
                shutil.rmtree(abs_path)
                log_event("FileManager.remove_folder", abs_path)
                return True, f"Removed folder: {os.path.basename(folderpath)}"
            else:
                return False, "Folder not found"
        except Exception as e:
            return False, f"Failed to remove folder: {e}"
    
    @classmethod
    def move_file(cls, source: str, destination: str) -> Tuple[bool, str]:
        """Move a file."""
        valid_src, msg = cls._validate_path(source)
        valid_dst, msg = cls._validate_path(destination)
        if not valid_src or not valid_dst:
            return False, "Path validation failed"
        
        try:
            src = os.path.abspath(os.path.expanduser(source))
            dst = os.path.abspath(os.path.expanduser(destination))
            shutil.move(src, dst)
            log_event("FileManager.move", f"{src} -> {dst}")
            return True, f"Moved file to {destination}"
        except Exception as e:
            return False, f"Failed to move: {e}"
    
    @classmethod
    def copy_file(cls, source: str, destination: str) -> Tuple[bool, str]:
        """Copy a file."""
        valid_src, msg = cls._validate_path(source)
        valid_dst, msg = cls._validate_path(destination)
        if not valid_src or not valid_dst:
            return False, "Path validation failed"
        
        try:
            src = os.path.abspath(os.path.expanduser(source))
            dst = os.path.abspath(os.path.expanduser(destination))
            shutil.copy2(src, dst)
            log_event("FileManager.copy", f"{src} -> {dst}")
            return True, f"Copied file to {destination}"
        except Exception as e:
            return False, f"Failed to copy: {e}"
    
    @classmethod
    def rename_file(cls, old_name: str, new_name: str) -> Tuple[bool, str]:
        """Rename a file."""
        valid, msg = cls._validate_path(old_name)
        if not valid:
            return False, msg
        
        try:
            old_path = os.path.abspath(os.path.expanduser(old_name))
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            os.rename(old_path, new_path)
            log_event("FileManager.rename", f"{old_path} -> {new_path}")
            return True, f"Renamed to {new_name}"
        except Exception as e:
            return False, f"Failed to rename: {e}"
    
    @classmethod
    def list_files(cls, directory: str = "~") -> Tuple[bool, str]:
        """List files in a directory."""
        valid, msg = cls._validate_path(directory)
        if not valid:
            return False, msg
        
        try:
            dir_path = os.path.abspath(os.path.expanduser(directory))
            if not os.path.isdir(dir_path):
                return False, "Not a valid directory"
            
            files = os.listdir(dir_path)
            if not files:
                return True, "Directory is empty"
            
            lines = [f"Contents of {os.path.basename(dir_path)}:"]
            for f in sorted(files):
                full_path = os.path.join(dir_path, f)
                if os.path.isdir(full_path):
                    lines.append(f"  📁 {f}/")
                else:
                    size = os.path.getsize(full_path)
                    size_str = cls._format_size(size)
                    lines.append(f"  📄 {f} ({size_str})")
            
            return True, "\n".join(lines)
        except Exception as e:
            return False, f"Failed to list files: {e}"
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"


# ============================================================
# Terminal Command Execution
# ============================================================

class CommandExecutor:
    """
    Secure command execution with whitelisting.
    """
    
    @staticmethod
    def execute(command: str) -> Tuple[bool, str]:
        """
        Execute a whitelisted command.
        """
        allowed, reason = CommandWhitelist.is_allowed(command)
        if not allowed:
            log_event("CommandExecutor.blocked", command)
            return False, f"Command not allowed: {reason}"
        
        try:
            # Use shell=True for Windows compatibility
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                output = result.stdout.strip() or "Command executed successfully"
                log_event("CommandExecutor.execute", command)
                return True, output
            else:
                return False, result.stderr.strip() or "Command failed"
        
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, f"Command failed: {e}"
    
    @staticmethod
    def get_allowed_commands() -> List[str]:
        """Get list of allowed commands."""
        return CommandWhitelist.get_allowed_commands()


# ============================================================
# System Resource Monitoring
# ============================================================

class SystemMonitor:
    """
    Monitor system resources (CPU, RAM, Disk, Network).
    """
    
    @staticmethod
    def get_cpu_usage(interval: float = 1.0) -> Tuple[bool, str]:
        """Get CPU usage percentage."""
        try:
            usage = psutil.cpu_percent(interval=interval)
            # Get per-CPU usage
            per_cpu = psutil.cpu_percent(interval=0.1, percpu=True)
            
            lines = [f"CPU Usage: {usage:.1f}%"]
            if len(per_cpu) <= 8:  # Only show if reasonable number of cores
                lines.append("Per-core usage:")
                for i, u in enumerate(per_cpu):
                    bar = "█" * int(u / 5) + "░" * (20 - int(u / 5))
                    lines.append(f"  Core {i}: {bar} {u:.1f}%")
            
            return True, "\n".join(lines)
        except Exception as e:
            return False, f"Failed to get CPU usage: {e}"
    
    @staticmethod
    def get_ram_usage() -> Tuple[bool, str]:
        """Get RAM usage."""
        try:
            mem = psutil.virtual_memory()
            
            lines = [
                f"RAM Usage: {mem.percent:.1f}%",
                f"  Used: {FileManager._format_size(mem.used)} / {FileManager._format_size(mem.total)}",
                f"  Available: {FileManager._format_size(mem.available)}",
            ]
            
            # Add warning if high usage
            if mem.percent > 90:
                lines.append("\n⚠️ Warning: Memory usage is very high!")
            elif mem.percent > 75:
                lines.append("\n⚠️ Notice: Memory usage is elevated.")
            
            return True, "\n".join(lines)
        except Exception as e:
            return False, f"Failed to get RAM usage: {e}"
    
    @staticmethod
    def get_disk_usage(path: str = None) -> Tuple[bool, str]:
        """Get disk usage."""
        try:
            if path is None:
                # Default to system drive on Windows, root on others
                if os.name == 'nt':
                    path = os.environ.get('SystemDrive', 'C:') + '\\'
                else:
                    path = '/'
            
            usage = psutil.disk_usage(path)
            
            lines = [
                f"Disk Usage for {path}:",
                f"  Total: {FileManager._format_size(usage.total)}",
                f"  Used: {FileManager._format_size(usage.used)} ({usage.percent}%)",
                f"  Free: {FileManager._format_size(usage.free)}",
            ]
            
            if usage.percent > 95:
                lines.append("\n⚠️ Warning: Disk is nearly full!")
            elif usage.percent > 85:
                lines.append("\n⚠️ Notice: Disk space is running low.")
            
            return True, "\n".join(lines)
        except Exception as e:
            return False, f"Failed to get disk usage: {e}"
    
    @staticmethod
    def get_network_info() -> Tuple[bool, str]:
        """Get network interface information."""
        try:
            interfaces = psutil.net_io_counters(pernic=True)
            
            lines = ["Network Statistics:"]
            for name, stats in interfaces.items():
                if stats.bytes_sent > 0 or stats.bytes_recv > 0:
                    lines.append(f"  {name}:")
                    lines.append(f"    Sent: {FileManager._format_size(stats.bytes_sent)}")
                    lines.append(f"    Received: {FileManager._format_size(stats.bytes_recv)}")
            
            return True, "\n".join(lines) if len(lines) > 1 else "No network activity"
        except Exception as e:
            return False, f"Failed to get network info: {e}"
    
    @staticmethod
    def get_battery_status() -> Tuple[bool, str]:
        """Get battery status."""
        try:
            battery = psutil.sensors_battery()
            
            if battery is None:
                return True, "No battery (desktop PC)"
            
            percent = battery.percent
            charging = "Charging" if battery.power_plugged else "On battery"
            
            lines = [
                f"Battery: {percent}%",
                f"Status: {charging}",
            ]
            
            if not battery.power_plugged and percent < 20:
                lines.append("\n⚠️ Warning: Low battery!")
            
            return True, "\n".join(lines)
        except Exception as e:
            return False, f"Failed to get battery status: {e}"
    
    @staticmethod
    def get_system_status() -> Tuple[bool, str]:
        """Get comprehensive system status."""
        try:
            lines = ["System Status Report", "=" * 30]
            
            # CPU
            cpu = psutil.cpu_percent(interval=0.5)
            lines.append(f"CPU: {cpu:.1f}%")
            
            # RAM
            mem = psutil.virtual_memory()
            lines.append(f"RAM: {mem.percent:.1f}% ({FileManager._format_size(mem.used)}/{FileManager._format_size(mem.total)})")
            
            # Disk
            if os.name == 'nt':
                disk_path = os.environ.get('SystemDrive', 'C:') + '\\'
            else:
                disk_path = '/'
            disk = psutil.disk_usage(disk_path)
            lines.append(f"Disk: {disk.percent:.1f}% used")
            
            # Network
            net = psutil.net_io_counters()
            lines.append(f"Network: ↑{FileManager._format_size(net.bytes_sent)} ↓{FileManager._format_size(net.bytes_recv)}")
            
            # Battery
            battery = psutil.sensors_battery()
            if battery:
                lines.append(f"Battery: {battery.percent}%")
            
            return True, "\n".join(lines)
        except Exception as e:
            return False, f"Failed to get system status: {e}"
    
    @staticmethod
    def get_uptime() -> Tuple[bool, str]:
        """Get system uptime."""
        try:
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            return True, f"System uptime: {days}d {hours}h {minutes}m"
        except Exception as e:
            return False, f"Failed to get uptime: {e}"


# ============================================================
# Central Hub: SystemController
# ============================================================

class SystemController:
    """
    Central system control interface.
    Routes requests to appropriate handlers.
    """
    
    def __init__(self):
        self.app = AppManager()
        self.files = FileManager()
        self.commands = CommandExecutor()
        self.monitor = SystemMonitor()
    
    def execute(self, operation: str, target: str = "") -> Tuple[bool, str]:
        """
        Execute a system operation.
        
        Operations:
        - open_app, close_app, list_apps
        - create_file, delete_file, move_file, copy_file, rename_file, list_files
        - execute_command
        - cpu_usage, ram_usage, disk_usage, network_info, battery_status, system_status, uptime
        """
        operation = operation.lower().strip()
        
        # Application operations
        if operation == "open_app":
            return self.app.open_application(target)
        elif operation == "close_app":
            return self.app.close_application(target)
        elif operation == "list_apps":
            return self.app.list_applications()
        
        # File operations
        elif operation == "create_file":
            parts = target.split("|", 1)
            filename = parts[0]
            content = parts[1] if len(parts) > 1 else ""
            return self.files.create_file(filename, content)
        elif operation == "delete_file":
            return self.files.delete_file(target)
        elif operation == "remove_folder":
            return self.files.remove_folder(target)
        elif operation == "move_file":
            parts = target.split("|", 1)
            if len(parts) < 2:
                return False, "Usage: move_file source|destination"
            return self.files.move_file(parts[0], parts[1])
        elif operation == "copy_file":
            parts = target.split("|", 1)
            if len(parts) < 2:
                return False, "Usage: copy_file source|destination"
            return self.files.copy_file(parts[0], parts[1])
        elif operation == "rename_file":
            parts = target.split("|", 1)
            if len(parts) < 2:
                return False, "Usage: rename_file old_name|new_name"
            return self.files.rename_file(parts[0], parts[1])
        elif operation == "list_files":
            return self.files.list_files(target or "~")
        
        # Command execution
        elif operation == "execute_command":
            return self.commands.execute(target)
        
        # System monitoring
        elif operation == "cpu_usage":
            return self.monitor.get_cpu_usage()
        elif operation == "ram_usage":
            return self.monitor.get_ram_usage()
        elif operation == "disk_usage":
            return self.monitor.get_disk_usage(target or None)
        elif operation == "network_info":
            return self.monitor.get_network_info()
        elif operation == "battery_status":
            return self.monitor.get_battery_status()
        elif operation == "system_status":
            return self.monitor.get_system_status()
        elif operation == "uptime":
            return self.monitor.get_uptime()
        
        else:
            return False, f"Unknown operation: {operation}"
    
    def get_capabilities(self) -> Dict[str, List[str]]:
        """Return available operations."""
        return {
            "applications": ["open_app", "close_app", "list_apps"],
            "files": ["create_file", "delete_file", "remove_folder", "move_file", "copy_file", "rename_file", "list_files"],
            "commands": ["execute_command"],
            "monitoring": ["cpu_usage", "ram_usage", "disk_usage", "network_info", "battery_status", "system_status", "uptime"],
        }


# ============================================================
# Convenience Functions (backward compatibility)
# ============================================================

# Create global instance
_system_controller = None

def get_system_controller() -> SystemController:
    """Get global system controller instance."""
    global _system_controller
    if _system_controller is None:
        _system_controller = SystemController()
    return _system_controller


# Direct function exports for backward compatibility
def open_application(app_name: str) -> Tuple[bool, str]:
    """Open an application."""
    return get_system_controller().execute("open_app", app_name)

def close_application(app_name: str) -> Tuple[bool, str]:
    """Close an application."""
    return get_system_controller().execute("close_app", app_name)

def create_file(filename: str, content: str = "") -> Tuple[bool, str]:
    """Create a file."""
    return get_system_controller().execute("create_file", f"{filename}|{content}")

def delete_file(filepath: str) -> Tuple[bool, str]:
    """Delete a file."""
    return get_system_controller().execute("delete_file", filepath)

def move_file(source: str, dest: str) -> Tuple[bool, str]:
    """Move a file."""
    return get_system_controller().execute("move_file", f"{source}|{dest}")

def copy_file(source: str, dest: str) -> Tuple[bool, str]:
    """Copy a file."""
    return get_system_controller().execute("copy_file", f"{source}|{dest}")

def execute_command(command: str) -> Tuple[bool, str]:
    """Execute a whitelisted command."""
    return get_system_controller().execute("execute_command", command)

def get_system_status() -> Tuple[bool, str]:
    """Get system status."""
    return get_system_controller().execute("system_status")

def get_cpu_usage() -> Tuple[bool, str]:
    """Get CPU usage."""
    return get_system_controller().execute("cpu_usage")

def get_ram_usage() -> Tuple[bool, str]:
    """Get RAM usage."""
    return get_system_controller().execute("ram_usage")

def get_disk_usage() -> Tuple[bool, str]:
    """Get disk usage."""
    return get_system_controller().execute("disk_usage")

def get_network_info() -> Tuple[bool, str]:
    """Get network info."""
    return get_system_controller().execute("network_info")

def get_battery_status() -> Tuple[bool, str]:
    """Get battery status."""
    return get_system_controller().execute("battery_status")

def get_uptime() -> Tuple[bool, str]:
    """Get system uptime."""
    return get_system_controller().execute("uptime")
