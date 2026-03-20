"""Tools registry — maps simple actions to local functions using automation modules."""
import shutil
import webbrowser
import os
import subprocess
from typing import Dict

# Try to import automation tools from the repo
try:
    from automation import executor as automation_executor
except Exception:
    automation_executor = None


def _open_url(target: str):
    if not target:
        return False, "No URL provided"
    try:
        webbrowser.open(target)
        return True, f"Opened {target}"
    except Exception as e:
        return False, str(e)


def _open_app(target: str):
    if not target:
        return False, "No app specified"
    try:
        # Attempt to open by name (Windows start)
        if os.name == 'nt':
            subprocess.Popen(['start', '', target], shell=True)
        else:
            subprocess.Popen([target])
        return True, f"Launched {target}"
    except Exception as e:
        return False, str(e)


def _search_google(target: str):
    if not target:
        return False, "No query provided"
    url = f"https://www.google.com/search?q={target.replace(' ', '+')}"
    try:
        webbrowser.open(url)
        return True, f"Searched Google for '{target}'"
    except Exception as e:
        return False, str(e)


def _tell_time(_):
    from datetime import datetime
    now = datetime.now().strftime("%I:%M %p")
    return True, f"It is {now}."


class ToolsRegistry:
    def __init__(self):
        self.tools: Dict[str, callable] = {
            'open_url': _open_url,
            'launch_app': _open_app,
            'search_google': _search_google,
            'tell_time': _tell_time,
        }
        # If automation executor is available, map additional tools
        if automation_executor:
            # The executor module may expose helpful functions — try to attach known names
            if hasattr(automation_executor, 'open_url'):
                self.tools['open_url'] = automation_executor.open_url
            if hasattr(automation_executor, 'launch_app'):
                self.tools['launch_app'] = automation_executor.launch_app

    def get_tools(self):
        return self.tools
