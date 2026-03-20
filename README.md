## BKR 2.0 Global Multilingual Assistant

This build is configured as a **window-only multilingual assistant** with:
- same-language replies by default
- grounded world-knowledge retrieval for factual questions
- adaptive teaching for coding, AI, language learning, and general study
- emotional check-ins without repetitive filler
- local Ollama runtime with network-backed speech/retrieval support

## Quick Start

1. Use virtualenv Python:
`.\.venv\Scripts\python.exe --version`

2. Install dependencies:
`.\.venv\Scripts\python.exe -m pip install -r requirements.txt`

3. Start local LLM server:
`ollama serve`

4. Verify runtime health:
`.\.venv\Scripts\python.exe doctor.py --fix-avatar`

5. Launch:
- one-click: `run_agent.bat`
- manual: `.\.venv\Scripts\python.exe main.py`

## Assistant Commands

- `teach me <topic>`
- `start lesson on <topic>`
- `next step`
- `repeat step`
- `quiz me`
- `lesson status`
- `stop lesson`
- `/speechlang en|hi|te|auto`
- `start english coach`
- `next lesson`
- `daily session`
- `quiz me`
- `coach status`
- `set daily target 45`

The default learning mode is the general subject tutor. The English coach remains available on demand for a fixed English curriculum.

## Local Speech Bootstrap

Populate the local open-source speech stack with:
`.\.venv\Scripts\python.exe scripts\bootstrap_local_models.py --languages en hi te --clean-archives`

This downloads Vosk STT models and Piper TTS voices into `assets/models`.

## Runtime Notes

- LLM: local Ollama first (`llama3`, fallback `bkr2`), with optional cloud fallback if keys are configured.
- STT defaults to `vosk_local` with local model auto-discovery.
- TTS defaults to `piper_local` with local voice auto-selection and `pyttsx3` fallback.
- Global knowledge grounding uses DuckDuckGo Instant Answer and Wikipedia summaries.
- Structured tutoring uses a persistent lesson session so `next step`, `quiz me`, and follow-up questions stay on the same topic.
- Grounded answers now show source cards inside the chat window.

## Runtime Stability Settings

- Voice echo suppression is enabled.
- Duplicate command replay suppression is enabled.
- Default UI mode is window-only assistant mode (no desktop companion).
- Windows auto-start is disabled by default.

## Local-Only Profile

If you want a stricter open-source/local-only runtime, switch these settings in [config.py](/c:/Users/prsnl/OneDrive/Desktop/ai-assistant%20-%20Copy/config.py):
- `OPEN_SOURCE_MODE = True`
- `STT_PROVIDER = "sphinx_local"` or `STT_PROVIDER = "vosk_local"` after installing a Vosk model
- `TTS_PROVIDER = "pyttsx3"` or `TTS_PROVIDER = "piper_local"` after adding a Piper voice model

This removes hosted LLM fallback, but multilingual speech quality will depend on the local models you install.
