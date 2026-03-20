import pyautogui
import time
import os
import subprocess
from datetime import datetime

# SAFETY: Fail-safe mode.
# If you slam the mouse to any corner of the screen, the program will crash/stop.
pyautogui.FAILSAFE = True


def type_text(text):
    """
    Types text with a small delay to look natural and ensure apps catch up.
    Uses hotkey-based paste for speed when text is long.
    """
    try:
        print(f"[Keyboard] Typing: '{text}'")
        if len(text) > 50:
            # For long text, use clipboard paste (much faster)
            import subprocess
            process = subprocess.Popen(
                ['clip'], stdin=subprocess.PIPE, shell=True
            )
            process.communicate(text.encode('utf-16-le'))
            time.sleep(0.2)
            pyautogui.hotkey('ctrl', 'v')
        else:
            pyautogui.write(text, interval=0.05)
        return True
    except Exception as e:
        print(f"[Error] Typing failed: {e}")
        return False


def press_key(key_name):
    """
    Presses a single key or key combination.
    Supports: 'enter', 'tab', 'esc', 'space', 'backspace', 'delete',
              'ctrl+c', 'ctrl+v', 'alt+tab', 'alt+f4', etc.
    """
    try:
        key_name = key_name.lower().strip()
        print(f"[Keyboard] Pressing: {key_name}")

        # Handle key combinations like ctrl+c, alt+tab
        if '+' in key_name:
            keys = [k.strip() for k in key_name.split('+')]
            pyautogui.hotkey(*keys)
        else:
            # Map common spoken names to pyautogui key names
            key_map = {
                "enter": "enter", "return": "enter",
                "tab": "tab",
                "escape": "esc", "esc": "esc",
                "space": "space", "spacebar": "space",
                "backspace": "backspace", "back space": "backspace",
                "delete": "delete", "del": "delete",
                "up": "up", "down": "down", "left": "left", "right": "right",
                "home": "home", "end": "end",
                "page up": "pageup", "page down": "pagedown",
                "caps lock": "capslock", "caps": "capslock",
                "print screen": "printscreen",
                "f1": "f1", "f2": "f2", "f3": "f3", "f4": "f4",
                "f5": "f5", "f6": "f6", "f7": "f7", "f8": "f8",
                "f9": "f9", "f10": "f10", "f11": "f11", "f12": "f12",
                "windows": "win", "win": "win",
            }
            actual_key = key_map.get(key_name, key_name)
            pyautogui.press(actual_key)
        return True
    except Exception as e:
        print(f"[Error] Key press failed: {e}")
        return False


def take_screenshot():
    """
    Takes a screenshot and saves it to Desktop with a timestamp filename.
    Returns the file path on success, None on failure.
    """
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(desktop, f"screenshot_{timestamp}.png")
        
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        print(f"[Screenshot] Saved to: {filepath}")
        return filepath
    except Exception as e:
        print(f"[Error] Screenshot failed: {e}")
        return None


def volume_control(direction):
    """
    Controls system volume: up, down, mute, unmute, max, min.
    Uses Windows nircmd or keyboard media keys.
    """
    try:
        direction = direction.lower().strip() if direction else "mute"
        print(f"[Volume] Action: {direction}")

        if direction == "up":
            for _ in range(5):  # 5 steps up
                pyautogui.press("volumeup")
        elif direction == "down":
            for _ in range(5):  # 5 steps down
                pyautogui.press("volumedown")
        elif direction in ("mute", "unmute"):
            pyautogui.press("volumemute")
        elif direction == "max":
            for _ in range(50):
                pyautogui.press("volumeup")
        elif direction == "min":
            for _ in range(50):
                pyautogui.press("volumedown")
        else:
            print(f"[Volume] Unknown direction: {direction}")
            return False
        return True
    except Exception as e:
        print(f"[Error] Volume control failed: {e}")
        return False