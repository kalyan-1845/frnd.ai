"""
J.A.R.V.I.S. Process Manager Module
List, inspect, and terminate running processes on the system.
"""
import psutil
import os
import subprocess
from core.logger import log_event, log_error


def list_running_apps(target=""):
    """
    Lists the top running applications by memory usage.
    Filters out system background processes to show only user-visible apps.
    """
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent', 'status']):
            try:
                info = proc.info
                # Filter: only show processes using > 0.1% memory (user apps)
                if info['memory_percent'] and info['memory_percent'] > 0.1:
                    processes.append(info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Sort by memory usage descending
        processes.sort(key=lambda x: x.get('memory_percent', 0), reverse=True)
        top = processes[:15]

        if not top:
            return True, "No significant user applications are currently running."

        lines = ["Currently running applications (by memory usage):"]
        for i, p in enumerate(top, 1):
            mem = p.get('memory_percent', 0)
            name = p.get('name', 'Unknown')
            pid = p.get('pid', '?')
            lines.append(f"  {i:2d}. {name:<30s} PID: {pid:<8} RAM: {mem:.1f}%")

        return True, "\n".join(lines)

    except Exception as e:
        log_error("ProcessManager.list", e)
        return False, f"Failed to list running apps: {e}"


def kill_process(target):
    """
    Terminates a process by name or PID.
    Safety: Will not kill critical system processes.
    """
    PROTECTED = [
        "explorer.exe", "svchost.exe", "csrss.exe", "winlogon.exe",
        "lsass.exe", "services.exe", "smss.exe", "dwm.exe",
        "system", "registry", "wininit.exe", "taskmgr.exe"
    ]

    try:
        target = target.strip()

        # Check if target is a PID (number)
        if target.isdigit():
            pid = int(target)
            try:
                proc = psutil.Process(pid)
                name = proc.name().lower()
                if name in PROTECTED:
                    return False, f"Cannot terminate protected system process: {name} (PID {pid})."
                proc.terminate()
                proc.wait(timeout=5)
                log_event("ProcessManager.kill", f"Terminated PID {pid} ({name})")
                return True, f"Process {name} (PID {pid}) has been terminated."
            except psutil.NoSuchProcess:
                return False, f"No process found with PID {pid}."
            except psutil.AccessDenied:
                return False, f"Access denied when trying to terminate PID {pid}. May require elevated privileges."
        else:
            # Kill by name
            target_lower = target.lower().strip()
            if not target_lower.endswith(".exe"):
                target_lower += ".exe"

            if target_lower in PROTECTED:
                return False, f"Cannot terminate protected system process: {target_lower}."

            killed = 0
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() == target_lower:
                        proc.terminate()
                        killed += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if killed > 0:
                log_event("ProcessManager.kill", f"Terminated {killed} instance(s) of {target}")
                return True, f"Terminated {killed} instance(s) of {target}."
            else:
                return False, f"No running process found matching '{target}'."

    except Exception as e:
        log_error("ProcessManager.kill", e)
        return False, f"Failed to terminate process: {e}"


def get_active_window(target=""):
    """Returns the title of the currently active/focused window."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd) + 1
        buf = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(hwnd, buf, length)
        title = buf.value
        if title:
            return True, f"Active window: {title}"
        return True, "No active window detected or the window has no title."
    except Exception as e:
        return False, f"Could not determine active window: {e}"


def count_running_processes(target=""):
    """Returns the total number of running processes."""
    try:
        count = len(list(psutil.process_iter()))
        return True, f"There are currently {count} processes running on the system."
    except Exception as e:
        return False, f"Failed to count processes: {e}"
