"""
BKR 2.0 runtime doctor.

Usage:
  python doctor.py
  python doctor.py --fix-avatar
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ASSETS_DIR = ROOT / "assets"

GENERATED_ASSET_NAMES = {
    "idle.png",
    "idle_shift.png",
    "idle_breath.png",
    "blink.png",
    "blink_quick.png",
    "eyes_open.png",
    "smile.png",
    "speak_1.png",
    "speak_2.png",
    "viseme_neutral.png",
    "viseme_A.png",
    "viseme_E.png",
    "viseme_I.png",
    "viseme_O.png",
    "viseme_U.png",
    "viseme_MBP.png",
    "viseme_STH.png",
}


def _ok(msg: str) -> None:
    print(f"[OK] {msg}")


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}")


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def _module_exists(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _find_tool(tool_name: str) -> str | None:
    found = shutil.which(tool_name)
    if found:
        return found

    exe = f"{tool_name}.exe" if os.name == "nt" else tool_name
    localapp = os.environ.get("LOCALAPPDATA", "")
    if not localapp:
        return None

    winget_base = Path(localapp) / "Microsoft" / "WinGet" / "Packages"
    if not winget_base.exists():
        return None

    patterns = [
        "Gyan.FFmpeg_*/*/bin/" + exe,
        "*FFmpeg*/*/bin/" + exe,
    ]
    for pattern in patterns:
        matches = list(winget_base.glob(pattern))
        if matches:
            return str(matches[0])
    return None


def _is_generated_asset(path: Path) -> bool:
    return path.name.lower() in {n.lower() for n in GENERATED_ASSET_NAMES}


def _resolve_real_source_photo(config_module) -> Path | None:
    candidates = [
        Path(getattr(config_module, "ASSISTANT_SOURCE_PHOTO", "")),
        ASSETS_DIR / "bkr2.0.png",
        ASSETS_DIR / "bkr2.0.jpg",
        ASSETS_DIR / "bkr2.0.jpeg",
        ASSETS_DIR / "user_photo.png",
        ASSETS_DIR / "user_photo.jpg",
        ASSETS_DIR / "user_photo.jpeg",
        ASSETS_DIR / "user_photo.webp",
        ASSETS_DIR / "my_photo.png",
        ASSETS_DIR / "my_photo.jpg",
        ASSETS_DIR / "my_photo.jpeg",
        ASSETS_DIR / "my_photo.webp",
    ]
    for p in candidates:
        if not p:
            continue
        p = p if p.is_absolute() else (ROOT / p)
        if p.exists() and not _is_generated_asset(p):
            return p.resolve()
    return None


def check_python() -> bool:
    ver = sys.version_info
    exe = sys.executable
    print(f"[INFO] Python: {ver.major}.{ver.minor}.{ver.micro}")
    print(f"[INFO] Executable: {exe}")
    if ver.major == 3 and ver.minor <= 11:
        _ok("Python version is suitable for this project.")
        return True
    _warn("Python 3.12+ can break some audio libs; prefer .venv Python 3.10/3.11.")
    return False


def check_imports() -> bool:
    required = [
        "PyQt5",
        "edge_tts",
        "speech_recognition",
        "sounddevice",
        "numpy",
        "requests",
        "ollama",
        "playsound",
    ]
    optional = ["cv2", "pygame", "pydub", "pocketsphinx", "vosk", "piper"]

    ok_all = True
    for mod in required:
        if _module_exists(mod):
            _ok(f"Module available: {mod}")
        else:
            _fail(f"Missing required module: {mod}")
            ok_all = False

    for mod in optional:
        if _module_exists(mod):
            _ok(f"Optional module available: {mod}")
        else:
            _warn(f"Optional module missing: {mod}")

    return ok_all


def check_runtime_mode(config_module) -> bool:
    ok = True

    english_only = bool(getattr(config_module, "FORCE_ENGLISH_ONLY", False))
    if english_only:
        _ok("English-only mode is enabled.")
    else:
        primary_language = str(getattr(config_module, "ASSISTANT_PRIMARY_LANGUAGE", "english")).lower()
        if primary_language == "multilingual":
            _ok("Multilingual mode is enabled.")
        else:
            _warn("Neither English-only nor multilingual mode is explicitly enabled.")

    window_only = bool(getattr(config_module, "GUI_WINDOW_ONLY", False))
    desktop_mode = bool(getattr(config_module, "DESKTOP_COMPANION_MODE", False))
    if window_only and not desktop_mode:
        _ok("Window-only UI mode is enabled.")
    else:
        _warn("Desktop companion mode is still enabled.")
        ok = False

    tutor_enabled = bool(getattr(config_module, "TUTOR_ENABLED", False))
    if tutor_enabled:
        _ok("General tutor automation is enabled.")
    else:
        _warn("General tutor automation is disabled.")
        ok = False

    coach_enabled = bool(getattr(config_module, "ENGLISH_COACH_ENABLED", False))
    if coach_enabled:
        _ok("English coach automation is enabled.")
    else:
        _warn("English coach automation is disabled.")

    if bool(getattr(config_module, "OPEN_SOURCE_MODE", False)):
        _ok("Open-source mode is enabled (cloud fallback blocked by default).")
    else:
        cloud_fallback = bool(getattr(config_module, "LLM_ENABLE_CLOUD_FALLBACK", False))
        if cloud_fallback:
            _ok("Hybrid mode is enabled (cloud fallback allowed).")
        else:
            _warn("Open-source mode is disabled.")

    if bool(getattr(config_module, "LOCAL_SPEECH_ONLY", False)):
        _ok("Local speech-only mode is enabled.")
    else:
        _warn("Speech stack still allows hosted providers.")

    return ok


def check_audio() -> bool:
    import config as config_module
    import sounddevice as sd

    ffmpeg = _find_tool("ffmpeg")
    ffprobe = _find_tool("ffprobe")
    if ffmpeg and ffprobe:
        _ok(f"ffmpeg + ffprobe found ({Path(ffmpeg).parent}).")
    else:
        _warn("ffmpeg/ffprobe missing; lip-sync audio analysis will use text fallback.")

    vosk_dir = Path(str(getattr(config_module, "VOSK_MODEL_DIR", "")))
    piper_dir = Path(str(getattr(config_module, "PIPER_MODEL_DIR", "")))
    if vosk_dir.exists():
        _ok(f"Vosk model directory present: {vosk_dir}")
    else:
        _warn("Vosk model directory missing.")

    if piper_dir.exists():
        _ok(f"Piper model directory present: {piper_dir}")
    else:
        _warn("Piper model directory missing.")

    try:
        devices = sd.query_devices()
        input_devices = [d for d in devices if d.get("max_input_channels", 0) > 0]
        if input_devices:
            _ok(f"Microphone devices detected: {len(input_devices)}")
            return True
        _warn("No microphone input device found.")
        return False
    except Exception as e:
        _warn(f"Audio device check failed: {e}")
        return False


def check_ollama(config_module) -> bool:
    import requests

    primary = str(getattr(config_module, "LLM_PRIMARY_MODEL", "bkr2"))
    fallback = str(getattr(config_module, "LLM_FALLBACK_MODEL", "llama3"))

    try:
        resp = requests.get("http://localhost:11434", timeout=2)
        if resp.status_code == 200:
            _ok("Ollama server reachable.")
        else:
            _fail(f"Ollama responded with status {resp.status_code}.")
            return False
    except Exception as e:
        _fail(f"Ollama not reachable: {e}")
        return False

    try:
        import ollama

        ok_models = True
        for name in (primary, fallback):
            try:
                ollama.show(name)
                _ok(f"Ollama model available: {name}")
            except Exception:
                _warn(f"Ollama model not found locally: {name}")
                ok_models = False
        return ok_models
    except Exception as e:
        _fail(f"Failed to query Ollama models: {e}")
        return False


def check_avatar(config_module) -> bool:
    required_frames = [
        Path(getattr(config_module, "ASSISTANT_AVATAR_PATH", ASSETS_DIR / "idle.png")),
        Path(getattr(config_module, "ASSISTANT_IDLE_SHIFT", ASSETS_DIR / "idle_shift.png")),
        Path(getattr(config_module, "ASSISTANT_BLINK", ASSETS_DIR / "blink.png")),
        Path(getattr(config_module, "ASSISTANT_SPEAK_1", ASSETS_DIR / "speak_1.png")),
        Path(getattr(config_module, "ASSISTANT_SPEAK_2", ASSETS_DIR / "speak_2.png")),
        ASSETS_DIR / "viseme_neutral.png",
        ASSETS_DIR / "viseme_A.png",
        ASSETS_DIR / "viseme_E.png",
        ASSETS_DIR / "viseme_I.png",
        ASSETS_DIR / "viseme_O.png",
        ASSETS_DIR / "viseme_U.png",
        ASSETS_DIR / "viseme_MBP.png",
        ASSETS_DIR / "viseme_STH.png",
    ]
    missing = [p for p in required_frames if not (p if p.is_absolute() else (ROOT / p)).exists()]
    if missing:
        _warn(f"Missing avatar frames: {len(missing)}")
        for p in missing[:4]:
            print(f"       - {p}")
    else:
        _ok("Avatar frame set is present.")

    source = _resolve_real_source_photo(config_module)
    if source:
        _ok(f"Avatar source photo: {source.name}")
        return True

    _warn("No real source photo found in assets (only generated frames).")
    _warn("Add assets/bkr2.0.png or assets/user_photo.png for personalized avatar.")
    # This is not a hard runtime blocker; default generated frames still work.
    return True


def maybe_fix_avatar(force_fix: bool) -> None:
    if not force_fix:
        return
    try:
        from advanced.avatar_generator import ensure_avatar_frames

        ok, msg = ensure_avatar_frames(force=True)
        if ok:
            _ok(f"Avatar regeneration: {msg}")
        else:
            _warn(f"Avatar regeneration warning: {msg}")
    except Exception as e:
        _warn(f"Avatar regeneration failed: {e}")


def main() -> int:
    parser = argparse.ArgumentParser(description="BKR runtime health checker")
    parser.add_argument("--fix-avatar", action="store_true", help="Force avatar frame regeneration")
    args = parser.parse_args()

    os.chdir(ROOT)
    import config  # local import after cwd set

    print("=== BKR Runtime Doctor ===")
    checks = [
        ("python", check_python()),
        ("imports", check_imports()),
        ("runtime_mode", check_runtime_mode(config)),
        ("audio", check_audio()),
        ("ollama", check_ollama(config)),
        ("avatar", check_avatar(config)),
    ]

    maybe_fix_avatar(args.fix_avatar)

    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)
    print(f"=== Summary: {passed}/{total} checks passed ===")

    critical_ok = dict(checks)["imports"] and dict(checks)["ollama"]
    return 0 if critical_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
