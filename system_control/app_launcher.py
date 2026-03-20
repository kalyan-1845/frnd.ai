import os
import subprocess
import shutil

# Knowledge Base: Map simple names to commands or paths
APP_PATHS = {
    # Editors
    "notepad": "notepad.exe",
    "code": "code",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "visual studio": "code",
    "sublime": "subl",
    # Browsers
    "chrome": "chrome.exe",
    "google chrome": "chrome.exe",
    "google": "chrome.exe",
    "firefox": "firefox.exe",
    "edge": "msedge.exe",
    "microsoft edge": "msedge.exe",
    "brave": "brave.exe",
    # System Tools
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "cmd": "cmd.exe",
    "command prompt": "cmd.exe",
    "terminal": "wt.exe",
    "windows terminal": "wt.exe",
    "powershell": "powershell.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "files": "explorer.exe",
    "task manager": "taskmgr.exe",
    "settings": "ms-settings:",
    "control panel": "control.exe",
    "device manager": "devmgmt.msc",
    "disk management": "diskmgmt.msc",
    "registry": "regedit.exe",
    "system info": "msinfo32.exe",
    # Media
    "paint": "mspaint.exe",
    "snipping tool": "snippingtool.exe",
    "snip": "snippingtool.exe",
    "camera": "start microsoft.windows.camera:",
    "photos": "start microsoft.windows.photos:",
    "media player": "wmplayer.exe",
    "vlc": "vlc.exe",
    # Office
    "word": "winword.exe",
    "microsoft word": "winword.exe",
    "excel": "excel.exe",
    "microsoft excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "ppt": "powerpnt.exe",
    "outlook": "outlook.exe",
    "onenote": "onenote.exe",
    "teams": "teams.exe",
    "microsoft teams": "teams.exe",
    # Communication
    "discord": "discord",
    "slack": "slack",
    "telegram": "telegram",
    "whatsapp": "start https://web.whatsapp.com",
    # Entertainment
    "spotify": "spotify.exe",
    "steam": "steam.exe",
    # Utilities
    "obs": "obs64.exe",
    "obs studio": "obs64.exe",
    "zoom": "zoom",
    "git bash": "git-bash.exe",
}

# Common misspellings / voice recognition errors
VOICE_CORRECTIONS = {
    "not pad": "notepad",
    "note pad": "notepad",
    "vs cold": "code",
    "v s code": "code",
    "bee us code": "code",
    "bees code": "code",
    "open he has good": "code",
    "open the as good": "code",
    "vs gord": "code",
    "vs gordon": "code",
    "have been vs gordon": "code",
    "file manager": "explorer",
    "my computer": "explorer",
    "this pc": "explorer",
    "calc u later": "calculator",
    "calculater": "calculator",
    "screen shot": "snipping tool",
    "the browser": "chrome",
    "browser": "chrome",
    "internet": "chrome",
    "web browser": "chrome",
    "power point": "powerpoint",
    "one note": "onenote",
    "what's app": "whatsapp",
    "dis cord": "discord",
    "spot ify": "spotify",
}


def launch_application(app_name):
    """
    Launches an application safely.
    Supports exact match, voice correction, partial match, and generic launch.
    Returns (success: bool, message: str)
    """
    original_name = app_name
    app_name = app_name.lower().strip()

    try:
        # 0. Apply voice correction
        if app_name in VOICE_CORRECTIONS:
            corrected = VOICE_CORRECTIONS[app_name]
            print(f"[System] Voice correction: '{app_name}' -> '{corrected}'")
            app_name = corrected

        # 1. Check Known Apps (exact match)
        if app_name in APP_PATHS:
            cmd = APP_PATHS[app_name]
            return _execute_launch(cmd, app_name)

        # 2. Try partial/fuzzy match
        best_match = None
        best_score = 0
        for known_name, cmd in APP_PATHS.items():
            # Check if known name is in spoken text or vice versa
            if known_name in app_name or app_name in known_name:
                score = len(known_name)  # Prefer longer (more specific) matches
                if score > best_score:
                    best_match = (known_name, cmd)
                    best_score = score

        if best_match:
            cmd = best_match[1]
            print(f"[System] Fuzzy matched '{app_name}' -> '{best_match[0]}'")
            return _execute_launch(cmd, best_match[0])

        # 3. Check if the executable exists in PATH
        exe_name = app_name.replace(" ", "") + ".exe"
        if shutil.which(exe_name):
            return _execute_launch(exe_name, app_name)

        # 4. Try Generic Launch (os.startfile for things like 'spotify')
        print(f"[System] Attempting generic launch for: {app_name}")
        try:
            os.startfile(app_name)
            return True, f"Launched {original_name}"
        except OSError:
            # Try with .exe
            try:
                os.startfile(app_name + ".exe")
                return True, f"Launched {original_name}"
            except OSError:
                pass

        print(f"[Error] Could not find application: {app_name}")
        return False, f"Sorry, I couldn't find the application '{original_name}'"

    except FileNotFoundError:
        print(f"[Error] Could not find application: {app_name}")
        return False, f"Sorry, I couldn't find '{original_name}'"
    except Exception as e:
        print(f"[Error] Failed to launch {app_name}: {e}")
        return False, f"Failed to launch '{original_name}': {e}"


def _execute_launch(cmd, name):
    """Internal helper to execute a launch command."""
    print(f"[System] Launching: {cmd}")
    try:
        if cmd.startswith("start "):
            os.system(cmd)
        elif cmd.startswith("ms-settings:") or cmd.endswith(".msc"):
            os.startfile(cmd)
        else:
            subprocess.Popen(cmd, shell=True,
                           stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL)
        return True, f"Launched {name}"
    except Exception as e:
        print(f"[Error] Launch execution failed: {e}")
        return False, f"Failed to launch {name}: {e}"