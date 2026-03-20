"""
J.A.R.V.I.S. System Monitor Module
Real-time system diagnostics and health reporting.
"""
import psutil
import platform
import shutil
import os
import socket
import time
from datetime import datetime, timedelta
from core.logger import log_event, log_error


def get_system_status(target=""):
    """
    Returns a comprehensive system status report.
    Like Tony Stark's HUD — CPU, RAM, Disk, Battery, Network, Uptime.
    """
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count(logical=True)
        cpu_freq = psutil.cpu_freq()
        cpu_freq_str = f"{cpu_freq.current:.0f} MHz" if cpu_freq else "N/A"

        # RAM
        mem = psutil.virtual_memory()
        ram_total = mem.total / (1024 ** 3)
        ram_used = mem.used / (1024 ** 3)
        ram_percent = mem.percent

        # Disk
        disk = shutil.disk_usage("/")
        disk_total = disk.total / (1024 ** 3)
        disk_used = disk.used / (1024 ** 3)
        disk_free = disk.free / (1024 ** 3)
        disk_percent = (disk.used / disk.total) * 100

        # Battery
        battery = psutil.sensors_battery()
        if battery:
            bat_percent = battery.percent
            bat_plugged = "Charging" if battery.power_plugged else "On Battery"
            if battery.secsleft > 0 and not battery.power_plugged:
                bat_time = str(timedelta(seconds=battery.secsleft))
            else:
                bat_time = "Calculating" if not battery.power_plugged else "N/A"
            battery_str = f"{bat_percent}% ({bat_plugged}, Time Left: {bat_time})"
        else:
            battery_str = "No battery detected (Desktop)"

        # Network
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
        except Exception:
            hostname = "Unknown"
            local_ip = "Unknown"

        net_io = psutil.net_io_counters()
        net_sent = net_io.bytes_sent / (1024 ** 2)
        net_recv = net_io.bytes_recv / (1024 ** 2)

        # Uptime
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{hours}h {minutes}m {seconds}s"

        # OS Info
        os_info = f"{platform.system()} {platform.release()} (Build {platform.version()})"

        report = (
            f"System Status Report:\n"
            f"  OS: {os_info}\n"
            f"  Hostname: {hostname}\n"
            f"  CPU: {cpu_percent}% usage across {cpu_count} cores at {cpu_freq_str}\n"
            f"  RAM: {ram_used:.1f} GB / {ram_total:.1f} GB ({ram_percent}%)\n"
            f"  Disk: {disk_used:.1f} GB / {disk_total:.1f} GB ({disk_percent:.1f}% used, {disk_free:.1f} GB free)\n"
            f"  Battery: {battery_str}\n"
            f"  Network: Sent {net_sent:.1f} MB, Received {net_recv:.1f} MB\n"
            f"  Local IP: {local_ip}\n"
            f"  Uptime: {uptime_str}"
        )

        return True, report

    except Exception as e:
        log_error("SystemMonitor.status", e)
        return False, f"Failed to retrieve system status: {e}"


def get_battery_status(target=""):
    """Returns battery level and charging status."""
    try:
        battery = psutil.sensors_battery()
        if battery:
            status = "charging" if battery.power_plugged else "discharging"
            msg = f"Battery is at {battery.percent}%, currently {status}."
            if not battery.power_plugged and battery.secsleft > 0:
                time_left = str(timedelta(seconds=battery.secsleft))
                msg += f" Estimated time remaining: {time_left}."
            return True, msg
        return True, "No battery detected. This appears to be a desktop system, Sir."
    except Exception as e:
        return False, f"Battery check failed: {e}"


def get_cpu_usage(target=""):
    """Returns current CPU usage percentage."""
    try:
        usage = psutil.cpu_percent(interval=1)
        cores = psutil.cpu_count(logical=True)
        freq = psutil.cpu_freq()
        freq_str = f" at {freq.current:.0f} MHz" if freq else ""
        return True, f"CPU usage is at {usage}% across {cores} logical cores{freq_str}."
    except Exception as e:
        return False, f"CPU check failed: {e}"


def get_ram_usage(target=""):
    """Returns current RAM usage."""
    try:
        mem = psutil.virtual_memory()
        used = mem.used / (1024 ** 3)
        total = mem.total / (1024 ** 3)
        return True, f"RAM usage: {used:.1f} GB out of {total:.1f} GB ({mem.percent}% utilized)."
    except Exception as e:
        return False, f"RAM check failed: {e}"


def get_disk_usage(target=""):
    """Returns disk usage for primary drive."""
    try:
        disk = shutil.disk_usage("/")
        total = disk.total / (1024 ** 3)
        used = disk.used / (1024 ** 3)
        free = disk.free / (1024 ** 3)
        percent = (disk.used / disk.total) * 100
        return True, f"Disk usage: {used:.1f} GB / {total:.1f} GB ({percent:.1f}% used). {free:.1f} GB free."
    except Exception as e:
        return False, f"Disk check failed: {e}"


def get_network_info(target=""):
    """Returns network interface information."""
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        net_io = psutil.net_io_counters()
        sent = net_io.bytes_sent / (1024 ** 2)
        recv = net_io.bytes_recv / (1024 ** 2)

        # Check internet connectivity
        import urllib.request
        try:
            urllib.request.urlopen("https://www.google.com", timeout=3)
            internet = "Connected"
        except Exception:
            internet = "Disconnected"

        return True, (
            f"Network Status:\n"
            f"  Hostname: {hostname}\n"
            f"  Local IP: {local_ip}\n"
            f"  Internet: {internet}\n"
            f"  Data Sent: {sent:.1f} MB\n"
            f"  Data Received: {recv:.1f} MB"
        )
    except Exception as e:
        return False, f"Network check failed: {e}"


def get_uptime(target=""):
    """Returns system uptime since last boot."""
    try:
        boot_time = datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.now() - boot_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        boot_str = boot_time.strftime("%I:%M %p on %B %d, %Y")
        return True, f"System has been online for {hours} hours and {minutes} minutes. Last boot: {boot_str}."
    except Exception as e:
        return False, f"Uptime check failed: {e}"
