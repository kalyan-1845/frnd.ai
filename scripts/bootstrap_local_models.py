"""
Bootstrap open-source local speech models for BKR 2.0.

Downloads:
- Vosk STT models
- Piper TTS voice models

Usage:
  .\.venv\Scripts\python.exe scripts\bootstrap_local_models.py
  .\.venv\Scripts\python.exe scripts\bootstrap_local_models.py --languages en hi te
  .\.venv\Scripts\python.exe scripts\bootstrap_local_models.py --skip-vosk
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys
import zipfile

import requests


ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "assets" / "models"
VOSK_DIR = MODELS_DIR / "vosk"
PIPER_DIR = MODELS_DIR / "piper"

VOSK_MODELS = {
    "en": {
        "name": "vosk-model-small-en-us-0.15",
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
    },
    "en-in": {
        "name": "vosk-model-small-en-in-0.4",
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-en-in-0.4.zip",
    },
    "hi": {
        "name": "vosk-model-small-hi-0.22",
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-hi-0.22.zip",
    },
    "te": {
        "name": "vosk-model-small-te-0.42",
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-te-0.42.zip",
    },
}

PIPER_MODELS = {
    "en": {
        "files": [
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx",
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json",
        ]
    },
    "hi": {
        "files": [
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/priyamvada/medium/hi_IN-priyamvada-medium.onnx",
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/priyamvada/medium/hi_IN-priyamvada-medium.onnx.json",
        ]
    },
    "te": {
        "files": [
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/te/te_IN/maya/medium/te_IN-maya-medium.onnx",
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/te/te_IN/maya/medium/te_IN-maya-medium.onnx.json",
        ]
    },
}


def _download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"[skip] {dest.name}")
        return

    print(f"[get] {url}")
    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        with open(dest, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 512):
                if chunk:
                    handle.write(chunk)


def _install_vosk(language: str) -> None:
    spec = VOSK_MODELS[language]
    target_dir = VOSK_DIR / spec["name"]
    if target_dir.exists():
        print(f"[ok] Vosk {language}: {target_dir.name}")
        return

    archive_path = VOSK_DIR / f"{spec['name']}.zip"
    _download(spec["url"], archive_path)
    print(f"[unzip] {archive_path.name}")
    with zipfile.ZipFile(archive_path, "r") as zip_file:
        zip_file.extractall(VOSK_DIR)


def _install_piper(language: str) -> None:
    spec = PIPER_MODELS[language]
    for url in spec["files"]:
        filename = url.rstrip("/").split("/")[-1]
        _download(url, PIPER_DIR / filename)
    print(f"[ok] Piper {language}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Download local speech models for BKR 2.0")
    parser.add_argument(
        "--languages",
        nargs="+",
        default=["en", "hi", "te"],
        help="Languages to download. Supported: en, en-in, hi, te",
    )
    parser.add_argument("--skip-vosk", action="store_true", help="Skip Vosk STT model downloads")
    parser.add_argument("--skip-piper", action="store_true", help="Skip Piper TTS model downloads")
    parser.add_argument("--clean-archives", action="store_true", help="Delete downloaded zip files after extraction")
    args = parser.parse_args(argv)

    requested = [lang.strip().lower() for lang in args.languages if lang.strip()]
    VOSK_DIR.mkdir(parents=True, exist_ok=True)
    PIPER_DIR.mkdir(parents=True, exist_ok=True)

    for lang in requested:
        if not args.skip_vosk and lang in VOSK_MODELS:
            _install_vosk(lang)
        if not args.skip_piper and lang in PIPER_MODELS:
            _install_piper(lang)

    if args.clean_archives:
        for archive in VOSK_DIR.glob("*.zip"):
            try:
                archive.unlink()
            except Exception:
                pass

    print("[done] Local model bootstrap complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
