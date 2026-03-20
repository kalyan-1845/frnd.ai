"""
J.A.R.V.I.S. System Settings Module
Advanced system control: Wi-Fi, Bluetooth, Brightness, Lock, Night Light,
Airplane Mode, Display Off, Recycle Bin, Wallpaper, Sleep, Shutdown, Restart.
"""
import os
import subprocess
import ctypes
from core.logger import log_event, log_error


def toggle_wifi(enable=True):
    """Enables/Disables Wi-Fi on Windows."""
    try:
        if not enable:
            os.system("netsh wlan disconnect")
            return True, "Wi-Fi disconnected, Sir."
        else:
            os.system("start ms-settings:network-wifi")
            return True, "Wi-Fi settings panel opened, Sir."
    except Exception as e:
        return False, f"Failed to control Wi-Fi: {e}"


def open_bluetooth():
    """Opens Bluetooth settings panel."""
    os.system("start ms-settings:bluetooth")
    return True, "Bluetooth settings opened, Sir."


def open_phone_link():
    """Opens the Phone Link app for calls/messages."""
    try:
        os.system("start ms-phone:")
        return True, "Phone Link opened, Sir."
    except Exception as e:
        return False, f"Could not open Phone Link: {e}"


def system_sleep(target=""):
    """Puts the system to sleep."""
    os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
    return True, "Initiating system sleep, Sir."


def lock_screen(target=""):
    """Locks the workstation immediately."""
    try:
        ctypes.windll.user32.LockWorkStation()
        return True, "Workstation locked, Sir."
    except Exception as e:
        return False, f"Failed to lock screen: {e}"


def set_brightness(target=""):
    """
    Sets screen brightness (0-100).
    Uses PowerShell WMI on supported laptops.
    """
    try:
        level = int(target) if target and target.strip().isdigit() else 50
        level = max(0, min(100, level))
        cmd = (
            f'powershell -Command "'
            f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
            f'.WmiSetBrightness(1,{level})"'
        )
        subprocess.run(cmd, shell=True, capture_output=True)
        return True, f"Brightness set to {level}%, Sir."
    except Exception as e:
        return False, f"Failed to set brightness: {e}"


def toggle_night_light(target=""):
    """Opens Night Light settings (toggle must be done manually)."""
    try:
        os.system("start ms-settings:nightlight")
        return True, "Night Light settings opened, Sir."
    except Exception as e:
        return False, f"Failed to open Night Light settings: {e}"


def toggle_airplane_mode(target=""):
    """Opens Airplane Mode settings."""
    try:
        os.system("start ms-settings:network-airplanemode")
        return True, "Airplane Mode settings opened, Sir."
    except Exception as e:
        return False, f"Failed to open Airplane Mode settings: {e}"


def display_off(target=""):
    """Turns off the display (press any key to wake)."""
    try:
        # SendMessage(HWND_BROADCAST, WM_SYSCOMMAND, SC_MONITORPOWER, 2)
        ctypes.windll.user32.SendMessageW(0xFFFF, 0x0112, 0xF170, 2)
        return True, "Display turned off, Sir. Press any key to wake."
    except Exception as e:
        return False, f"Failed to turn off display: {e}"


def empty_recycle_bin(target=""):
    """Empties the Windows Recycle Bin."""
    try:
        # SHEmptyRecycleBin(None, None, flags)
        # Flags: 0x07 = SHERB_NOCONFIRMATION | SHERB_NOPROGRESSUI | SHERB_NOSOUND
        ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, 0x07)
        return True, "Recycle Bin emptied, Sir."
    except Exception as e:
        return False, f"Failed to empty Recycle Bin: {e}"


def set_wallpaper(target=""):
    """
    Sets the desktop wallpaper.
    target: absolute path to an image file.
    """
    try:
        if not target or not os.path.exists(target):
            return False, "Please provide a valid image path for the wallpaper, Sir."
        # SPI_SETDESKWALLPAPER = 0x0014
        ctypes.windll.user32.SystemParametersInfoW(0x0014, 0, target, 3)
        return True, f"Wallpaper updated to {os.path.basename(target)}, Sir."
    except Exception as e:
        return False, f"Failed to set wallpaper: {e}"


def system_shutdown(target=""):
    """Shuts down the system after a 10-second delay (can be cancelled)."""
    try:
        os.system("shutdown /s /t 10")
        return True, "System will shut down in 10 seconds, Sir. Use 'shutdown /a' to cancel."
    except Exception as e:
        return False, f"Failed to initiate shutdown: {e}"


def system_restart(target=""):
    """Restarts the system after a 10-second delay."""
    try:
        os.system("shutdown /r /t 10")
        return True, "System will restart in 10 seconds, Sir."
    except Exception as e:
        return False, f"Failed to initiate restart: {e}"


def cancel_shutdown(target=""):
    """Cancels a pending shutdown or restart."""
    try:
        os.system("shutdown /a")
        return True, "Pending shutdown cancelled, Sir."
    except Exception as e:
        return False, f"Failed to cancel shutdown: {e}"


def open_settings(target=""):
    """Opens Windows Settings to a specific page if specified."""
    try:
        if target:
            target_lower = target.lower().strip()
            settings_map = {
                "display": "ms-settings:display",
                "sound": "ms-settings:sound",
                "notifications": "ms-settings:notifications",
                "power": "ms-settings:powersleep",
                "battery": "ms-settings:batterysaver",
                "storage": "ms-settings:storagesense",
                "apps": "ms-settings:appsfeatures",
                "privacy": "ms-settings:privacy",
                "update": "ms-settings:windowsupdate",
                "personalization": "ms-settings:personalization",
                "accounts": "ms-settings:yourinfo",
                "mouse": "ms-settings:mousetouchpad",
                "keyboard": "ms-settings:typing",
                "time": "ms-settings:dateandtime",
                "language": "ms-settings:regionlanguage",
                "about": "ms-settings:about",
            }
            uri = settings_map.get(target_lower, f"ms-settings:{target_lower}")
            os.system(f"start {uri}")
            return True, f"Opened {target} settings, Sir."
        else:
            os.system("start ms-settings:")
            return True, "Windows Settings opened, Sir."
    except Exception as e:
        return False, f"Failed to open settings: {e}"
