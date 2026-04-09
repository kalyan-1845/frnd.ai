import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Assistant Identity
ASSISTANT_NAME = "Leo"
CURRENT_ASSISTANT = ASSISTANT_NAME
ASSISTANT_TAG = "Frnd.AI (BKR 2.0)"
ASSISTANT_SHORT_NAME = "Leo"

# Startup Greetings (randomly selected on boot)
ASSISTANT_GREETINGS = [
    "Hello! I'm here and ready to help.",
    "Hi there! BKR 2.0 at your service.",
    "Hey! System online and ready.",
    "Good to see you! What can I do for you?",
    "I'm back! Let's get things done.",
    "Welcome back! How can I assist you today?",
    "Ready when you are! What's on your mind?",
    "Hello! Your AI assistant is online.",
    "Hey there! Let's make today productive.",
    "Hi! Ready to help you with anything.",
]

DEFAULT_USER_NAME = "Kalyan"
DEFAULT_USER_ROLE = "student"
ASSISTANT_VOICE_EN = "en-IN-NeerjaNeural"
ASSISTANT_PRIMARY_LANGUAGE = "english"
FORCE_ENGLISH_ONLY = True
ASSISTANT_RELATION_STYLE = "teacher"
ASSISTANT_USER_STYLE = "global_english_tutor"
OPEN_SOURCE_MODE = False
LOCAL_SPEECH_ONLY = False
# User's photo for avatar - put your photo (bkr2.0.jpeg) in assets folder
ASSISTANT_SOURCE_PHOTO = os.path.join(os.path.dirname(__file__), "assets", "bkr2.0.jpeg")
# Fallback to other common names if bkr2.0.jpeg doesn't exist
_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")
for _photo_name in [
    "bkr2.0.png", "bkr2.0.jpeg", "bkr2.0.jpg",
    "user_photo.png", "user_photo.jpg", "user_photo.jpeg", "user_photo.webp",
    "my_photo.png", "my_photo.jpg", "my_photo.jpeg", "my_photo.webp",
]:
    _photo_path = os.path.join(_ASSETS_DIR, _photo_name)
    if os.path.exists(_photo_path):
        ASSISTANT_SOURCE_PHOTO = _photo_path
        break
ASSISTANT_AVATAR_PATH = os.path.join(os.path.dirname(__file__), "assets", "idle.png")
ASSISTANT_IDLE_SHIFT = os.path.join(os.path.dirname(__file__), "assets", "idle_shift.png")
ASSISTANT_BLINK = os.path.join(os.path.dirname(__file__), "assets", "blink.png")
ASSISTANT_SPEAK_1 = os.path.join(os.path.dirname(__file__), "assets", "speak_1.png")
ASSISTANT_SPEAK_2 = os.path.join(os.path.dirname(__file__), "assets", "speak_2.png")

# Voice behavior
VOICE_REQUIRE_WAKE_WORD = False  # Only listen when wake word is spoken
VOICE_ECHO_GUARD_SECONDS = 0.9
VOICE_ECHO_MATCH_WINDOW_SECONDS = 6.0
VOICE_DEDUP_WINDOW_SECONDS = 2.0
VOICE_COMMAND_DEDUP_SECONDS = 3.0

# Desktop companion UI
GUI_ENABLED = True
GUI_WINDOW_ONLY = True
DESKTOP_COMPANION_MODE = False
DESKTOP_COMPANION_CORNER = "bottom_right"
DESKTOP_COMPANION_MARGIN = 16
DESKTOP_SHOW_CHAT = True
AVATAR_3D_MODE = True
AVATAR_3D_INTENSITY = 1.8

# Runtime features
ASSISTANT_AUTO_GENERATE_AVATAR = True
ASSISTANT_FORCE_REGENERATE_AVATAR = False
AUTO_START_WITH_WINDOWS = False

# LLM Configuration
LLM_PRIMARY_MODEL = "llama3"          # English-first local model
LLM_FALLBACK_MODEL = "bkr2"           # Fallback model (local)
LLM_MAX_TOKENS = 64                   # Max response tokens restricted for extreme speed
LLM_TEMPERATURE = 0.3                 # Lower temp for faster, highly predictable, smart replies
LLM_CONTEXT_MESSAGES = 2              # Fewer history messages for lower processing latency
LLM_CACHE_ENABLED = True             # Enable caching for faster responses

# Google Gemini API (best fallback for Telugu)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Groq API (super fast Llama-3 70B)
# Get free key from https://console.groq.com/keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_MAX_TOKENS = 512
LLM_PREFER_GROQ_FOR_CHAT = True
LLM_PREFER_GROQ_FOR_CODE = True
LLM_DISABLE_GROQ_FOR_CHAT = False
LLM_ENABLE_CLOUD_FALLBACK = True
LLM_ENABLE_GLOBAL_KNOWLEDGE = False
LLM_GLOBAL_KNOWLEDGE_MAX_CHARS = 900
LLM_FAST_GROUNDED_REPLY = True

# Optional assistant nudges
WELLBEING_REMINDERS_ENABLED = False
WELLBEING_REMINDER_PROBABILITY = 0.08
VOICE_TASK_FOLLOWUP_ENABLED = False

# OpenAI API (for ChatGPT fallback)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# English learning automation
ENGLISH_COACH_ENABLED = True
ENGLISH_COACH_AUTO_MODE = True
ENGLISH_COACH_AUTO_ADVANCE = True
ENGLISH_COACH_DAILY_TARGET_MINUTES = 30

# General tutoring automation
TUTOR_ENABLED = True
TUTOR_DEFAULT_LEVEL = "beginner"
TUTOR_MAX_STEPS = 5

# ========================= SPEECH STACK =========================
# STT providers: "sphinx_local", "google_free", "openai_whisper", "deepgram", "vosk_local"
STT_PROVIDER = "deepgram"
STT_ALLOW_CLOUD_FALLBACK = True
STT_ACTIVE_LANGUAGE = "en-in"  # en-in or en-us
STT_GOOGLE_LANGUAGE_CANDIDATES = [
    "en-IN",
    "en-US",
]
OPENAI_STT_MODEL = "whisper-1"
OPENAI_STT_LANGUAGE = ""
OPENAI_STT_PROMPT = "Multilingual conversational speech for a global AI assistant."
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")
DEEPGRAM_MODEL = "nova-2"
DEEPGRAM_LANGUAGE = "en-IN"
VOSK_MODEL_DIR = os.path.join(os.path.dirname(__file__), "assets", "models", "vosk")
VOSK_MODEL_PATH = os.path.join(VOSK_MODEL_DIR, "vosk-model-small-en-us-0.15")
VOSK_MODEL_PATHS = {
    "en": os.path.join(VOSK_MODEL_DIR, "vosk-model-small-en-us-0.15"),
    "en-in": os.path.join(VOSK_MODEL_DIR, "vosk-model-small-en-in-0.4"),
}

# TTS providers: "pyttsx3", "edge_tts", "elevenlabs", "piper_local"
TTS_PROVIDER = "edge_tts"
TTS_ALLOW_CLOUD_FALLBACK = True
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = "EXAVITQu4vr4xnSDxMaL"
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"
ELEVENLABS_STABILITY = 0.35
ELEVENLABS_SIMILARITY_BOOST = 0.78
ELEVENLABS_STYLE = 0.45
ELEVENLABS_USE_SPEAKER_BOOST = True
PIPER_BINARY = "piper"
PIPER_MODEL_DIR = os.path.join(os.path.dirname(__file__), "assets", "models", "piper")
PIPER_MODEL_PATH = os.path.join(PIPER_MODEL_DIR, "en_US-lessac-medium.onnx")
PIPER_MODEL_PATHS = {
    "en": os.path.join(PIPER_MODEL_DIR, "en_US-lessac-medium.onnx"),
}

# Avatar backend: "local_ui", "vtube_studio"
# local_ui = current PyQt avatar with lip-sync (static images)
# vtube_studio = trigger expression hotkeys over VTube Studio API (RECOMMENDED for animated girl)
AVATAR_PROVIDER = "vtube_studio"
VTS_WS_URL = "ws://127.0.0.1:8001"
VTS_PLUGIN_NAME = "Sara Companion Bridge"
VTS_PLUGIN_DEVELOPER = "BKR2"
VTS_AUTH_TOKEN = None
VTS_HOTKEY_MAP = {
    "Smile": "Smile",
    "Concerned": "Concerned",
    "Laugh": "Laugh",
    "Blush": "Blush",
    "Sad": "Sad",
    "Neutral": "Neutral",
}
