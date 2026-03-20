"""
Bootstrap Phase 2 file writer

Run this script from the repository root to create/update the Phase 2 files:
    python scripts/bootstrap_phase2.py

It will write the following files (overwriting existing ones):
- backend/app.py
- backend/services/tts_piper_wrapper.py
- backend/services/speech_service.py
- backend/services/tools_registry.py
- scripts/test_end_to_end.py

This keeps the repository edits grouped into a single file write for the assistant.
"""
import os

FILES = {
    "backend/app.py": r"""from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import tempfile

# Import repository components
from core.brain import BrainController
from core import llm_api

# Services we'll implement
from backend.services.llm_adapter import LLMAdapter
from backend.services.speech_service import SpeechService
from backend.services.tools_registry import ToolsRegistry

# Try to import existing memory and personality engines
try:
    from advanced.memory import MemorySystem
except Exception:
    MemorySystem = None

try:
    from core.personality import PersonalityEngine
except Exception:
    PersonalityEngine = None

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
llm = LLMAdapter()
speech = SpeechService()

memory = MemorySystem() if MemorySystem else None
personality = PersonalityEngine() if PersonalityEngine else None

brain = BrainController(memory=memory, personality_engine=personality)

# Register LLM and speak
brain.register_llm(llm.generate, llm.plan, getattr(llm, 'stream_generate', None))
brain.register_speak(speech.speak)

# Register tools
tools = ToolsRegistry()
brain.register_tools(tools.get_tools())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/chat")
def api_chat(user_id: str = Form(default="user"), text: str = Form(...), mode: str = Form(default="chat")):
    """Accepts form data for simplicity from small frontend or curl."""
    result = brain.execute(text, source="text")
    return JSONResponse(result)


@app.post("/api/voice")
def api_voice(file: UploadFile = File(...), user_id: str = Form(default="user")):
    # Save uploaded file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1] or ".wav")
    content = file.file.read()
    tmp.write(content)
    tmp.flush()
    tmp.close()

    # Transcribe
    text = speech.transcribe(tmp.name)
    # Pass to brain
    result = brain.execute(text, source="voice")

    return JSONResponse({"transcript": text, **result})


@app.post("/api/tts")
def api_tts(text: str = Form(...)):
    audio_path = speech.synthesize(text)
    if not audio_path or not os.path.exists(audio_path):
        return JSONResponse({"error": "TTS failed"}, status_code=500)
    return FileResponse(audio_path, media_type="audio/mpeg")


@app.post("/api/confirm")
def api_confirm(answer: str = Form(...)):
    """Frontend confirmation route - passes yes/no text to the BrainController confirmation handler."""
    # BrainController._handle_confirmation expects the raw user input string
    result = brain._handle_confirmation(answer)
    return JSONResponse(result)


@app.get("/api/tools/list")
def api_tools_list():
    return JSONResponse({"tools": list(tools.get_tools().keys())})


@app.get("/api/llm/status")
def api_llm_status():
    return JSONResponse(llm_api.get_llm_status())


@app.get("/")
def index():
    static_index = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'static', 'index.html')
    if os.path.exists(static_index):
        with open(static_index, 'r', encoding='utf-8') as f:
            return HTMLResponse(f.read())
    return HTMLResponse('<html><body><h1>BKR Backend</h1></body></html>')


if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
""",

    "backend/services/tts_piper_wrapper.py": r"""""Piper TTS wrapper (basic). Attempts to use Piper ONNX models in assets/models/piper.
Falls back to edge-tts if Piper not available.
This wrapper exposes `synthesize_to_file(text, out_path)`.
"""
import os

PIPER_MODELS_DIR = os.path.join(os.getcwd(), 'assets', 'models', 'piper')


def synthesize_to_file(text: str, out_path: str) -> bool:
    """Try to use a local Piper ONNX model to synthesize audio.
    This is a placeholder: if proper Piper tooling is not available, return False.
    """
    # Check model files
    if os.path.isdir(PIPER_MODELS_DIR):
        # If you have a Piper synthesis CLI or python API installed, integrate here.
        # For now, we do not implement ONNX runtime-based piper synthesis.
        return False

    return False
""",

    "backend/services/speech_service.py": r"""""Speech service wrapper: provides transcribe and synthesize functions.

This file will attempt to use advanced.voice if present, otherwise fall back to whisper and edge-tts.
"""
import os
import subprocess
import tempfile
from typing import Optional

# Try to reuse existing advanced voice module
try:
    from advanced import voice as advanced_voice
except Exception:
    advanced_voice = None

# Try to import Piper wrapper
try:
    from backend.services import tts_piper_wrapper
except Exception:
    tts_piper_wrapper = None

# Fallback TTS using edge-tts if available
try:
    import edge_tts
except Exception:
    edge_tts = None

# Minimal whisper transcription fallback using openai-whisper if installed
try:
    import whisper
except Exception:
    whisper = None


class SpeechService:
    def __init__(self):
        self.tts_dir = os.path.join(os.getcwd(), "backend", "_tts")
        os.makedirs(self.tts_dir, exist_ok=True)

    def transcribe(self, audio_path: str) -> str:
        # Prefer advanced_voice transcribe
        if advanced_voice and hasattr(advanced_voice, 'transcribe_file'):
            try:
                return advanced_voice.transcribe_file(audio_path)
            except Exception:
                pass

        # Fallback to whisper (if installed)
        if whisper:
            try:
                model = whisper.load_model("small")
                result = model.transcribe(audio_path)
                return result.get('text', '')
            except Exception:
                pass

        # As last resort return empty string
        return ""

    def synthesize(self, text: str, mood: str = 'neutral') -> Optional[str]:
        # Prefer advanced voice speak that returns audio path
        if advanced_voice and hasattr(advanced_voice, 'speak_to_file'):
            try:
                out = advanced_voice.speak_to_file(text)
                if out and os.path.exists(out):
                    return out
            except Exception:
                pass

        # Next try Piper wrapper if available
        out_path = os.path.join(self.tts_dir, f"tts_{abs(hash(text)) % (10**8)}.mp3")
        if tts_piper_wrapper and hasattr(tts_piper_wrapper, 'synthesize_to_file'):
            try:
                ok = tts_piper_wrapper.synthesize_to_file(text, out_path)
                if ok and os.path.exists(out_path):
                    return out_path
            except Exception:
                pass

        # Fallback edge-tts
        if edge_tts:
            # Simple default voice
            voice = "en-US-JennyNeural"
            communicate = edge_tts.Communicate(text, voice)
            try:
                import asyncio

                async def _synthesize():
                    await communicate.save(out_path)

                loop = asyncio.new_event_loop()
                loop.run_until_complete(_synthesize())
                loop.close()
                if os.path.exists(out_path):
                    return out_path
            except Exception:
                pass

        # Last resort: use OS 'say' (mac) or return None
        return None

    def speak(self, text: str, mood: str = 'neutral'):
        """Used by BrainController to speak immediately. We'll synthesize to a file and play it if possible."""
        audio = self.synthesize(text, mood)
        if audio and os.path.exists(audio):
            # Try to play using playsound if available
            try:
                from playsound import playsound
                playsound(audio)
            except Exception:
                # Otherwise, spawn default OS player
                try:
                    if os.name == 'nt':
                        os.startfile(audio)
                    else:
                        subprocess.Popen(["xdg-open", audio])
                except Exception:
                    pass
""",

    "backend/services/tools_registry.py": r"""Tools registry — maps simple actions to local functions using automation modules."""
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
            # Use start to launch registered application names
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


def _open_folder(target: str):
    if not target:
        return False, "No folder specified"
    try:
        if os.path.exists(target) and os.path.isdir(target):
            if os.name == 'nt':
                os.startfile(target)
            else:
                subprocess.Popen(['xdg-open', target])
            return True, f"Opened folder {target}"
        else:
            return False, f"Folder not found: {target}"
    except Exception as e:
        return False, str(e)


def _find_file(target: str):
    """Search user's home for the filename (simple, non-recursive limit)."""
    if not target:
        return False, "No filename provided"
    home = os.path.expanduser('~')
    matches = []
    for root, dirs, files in os.walk(home):
        for f in files:
            if target.lower() in f.lower():
                matches.append(os.path.join(root, f))
        if len(matches) >= 20:
            break
    if matches:
        return True, '; '.join(matches[:10])
    return False, "No files found"


def _write_to_file(target: str):
    """Write to file action requires confirmation in most cases — here we don't perform writes but indicate intent."""
    return False, "write_to_file requires explicit confirmation and will be performed only after user confirmation via the UI."


class ToolsRegistry:
    def __init__(self):
        self.tools: Dict[str, callable] = {
            'open_url': _open_url,
            'launch_app': _open_app,
            'search_google': _search_google,
            'tell_time': _tell_time,
            'open_folder': _open_folder,
            'find_file': _find_file,
            'write_to_file': _write_to_file,
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
""",

    "scripts/test_end_to_end.py": r"""""Simple end-to-end test script for BKR backend.
Usage (after starting backend):
    python scripts/test_end_to_end.py
It will perform a chat request, request TTS for the response, and attempt a voice upload if test audio exists.
"""
import requests
import os

BASE = 'http://localhost:8000'

def test_chat():
    print('Testing chat...')
    resp = requests.post(f'{BASE}/api/chat', files={'text': (None, 'Hello BKR, give me a 3 step plan to learn binary search')}, data={'user_id': 'tester'})
    print('Status:', resp.status_code)
    try:
        j = resp.json()
        print('Response:', j.get('response'))
        return j
    except Exception as e:
        print('Failed to parse JSON:', e)
        print(resp.text)
        return None


def test_tts(text):
    print('Testing TTS...')
    resp = requests.post(f'{BASE}/api/tts', files={'text': (None, text)})
    print('Status:', resp.status_code)
    if resp.status_code == 200:
        out = 'out_tts.mp3'
        with open(out, 'wb') as f:
            f.write(resp.content)
        print('Saved TTS to', out)
    else:
        print('TTS failed:', resp.text)


def test_voice_upload():
    print('Testing voice upload...')
    sample = os.path.join(os.path.dirname(__file__), '..', 'test_audio.wav')
    if not os.path.exists(sample):
        print('No test audio found at', sample)
        return
    resp = requests.post(f'{BASE}/api/voice', files={'file': open(sample, 'rb')}, data={'user_id': 'tester'})
    print('Status:', resp.status_code)
    try:
        print('Result:', resp.json())
    except Exception as e:
        print('Non-JSON resp')


if __name__ == '__main__':
    j = test_chat()
    if j and 'response' in j:
        test_tts(j['response'])
    test_voice_upload()
""",
}


def ensure_dir(path):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for rel, content in FILES.items():
        path = os.path.join(root, rel)
        ensure_dir(path)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print('Wrote', path)


if __name__ == '__main__':
    main()
