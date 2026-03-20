from fastapi import FastAPI, UploadFile, File, Form
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
personality = PersonalityEngine(memory) if PersonalityEngine else None

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
