"""
Windows startup registration for BKR 2.0.
"""
from __future__ import annotations

import os
import sys


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def ensure_windows_startup() -> tuple[bool, str]:
    if os.name != "nt":
        return False, "Startup registration skipped (non-Windows OS)."

    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return False, "APPDATA not available; cannot configure startup."

    startup_dir = os.path.join(
        appdata, "Microsoft", "Windows", "Start Menu", "Programs", "Startup"
    )
    os.makedirs(startup_dir, exist_ok=True)

    launcher_path = os.path.join(startup_dir, "BKR_2_0_Startup.bat")
    project_root = _project_root()
    venv_python = os.path.join(project_root, ".venv", "Scripts", "python.exe")
    python_exe = venv_python if os.path.exists(venv_python) else sys.executable
    main_script = os.path.join(project_root, "main.py")

    content = (
        "@echo off\n"
        f'cd /d "{project_root}"\n'
        f'start "" "{python_exe}" "{main_script}"\n'
    )

    try:
        if os.path.exists(launcher_path):
            with open(launcher_path, "r", encoding="utf-8", errors="ignore") as f:
                existing = f.read()
            if existing.strip() == content.strip():
                return True, f"Startup already configured: {launcher_path}"

        with open(launcher_path, "w", encoding="utf-8") as f:
            f.write(content)
        return True, f"Startup configured: {launcher_path}"
    except Exception as e:
        return False, f"Startup setup failed: {e}"


def disable_windows_startup() -> tuple[bool, str]:
    """Remove startup launcher if present."""
    if os.name != "nt":
        return False, "Startup removal skipped (non-Windows OS)."

    appdata = os.environ.get("APPDATA", "")
    if not appdata:
        return False, "APPDATA not available; cannot remove startup entry."

    launcher_path = os.path.join(
        appdata,
        "Microsoft",
        "Windows",
        "Start Menu",
        "Programs",
        "Startup",
        "BKR_2_0_Startup.bat",
    )
    try:
        if os.path.exists(launcher_path):
            os.remove(launcher_path)
            return True, f"Startup disabled: {launcher_path}"
        return True, "Startup already disabled."
    except Exception as e:
        return False, f"Failed to disable startup: {e}"
