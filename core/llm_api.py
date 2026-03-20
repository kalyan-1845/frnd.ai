"""
BKR 2.0 - NEXT-GEN LLM API
Multi-provider intelligence with auto-fallback chain:
  1. Custom BKR2 Ollama model (primary - offline, fast)
  2. Google Gemini 2.0 Flash (fallback - online, Telugu expert)
  3. Ollama llama3 (secondary fallback)
  4. Personality Engine (last resort - always available)
"""
import json
import time
import hashlib
import re
import os

try:
    import openai
except ImportError:
    openai = None

try:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import google.generativeai as genai
except ImportError:
    genai = None

try:
    from groq import Groq
except ImportError:
    Groq = None

import config
from core.database import db
from core.knowledge_engine import (
    get_global_knowledge_payload,
    quick_translate_text,
    should_fetch_knowledge,
    translate_to_english,
)
from core.logger import log_event, log_error

# ========================== MODEL CONFIGURATION ==========================
# Fully local - only Ollama models (no cloud dependencies)
# Primary: Custom BKR2 model (fine-tuned llama3 with Telugu persona)
# Secondary: llama3 (if bkr2 not available)

OLLAMA_MODEL = str(getattr(config, "LLM_PRIMARY_MODEL", "bkr2"))              # Custom fine-tuned model
OLLAMA_FALLBACK_MODEL = str(getattr(config, "LLM_FALLBACK_MODEL", "llama3"))   # Fallback if primary not found
OLLAMA_CODER_MODEL = "bkr-coder"   # Coding expert
OLLAMA_VISION_MODEL = "bkr-vision" # Computer vision 

# Cloud providers (RE-ENABLED)
GEMINI_API_KEY = getattr(config, "GEMINI_API_KEY", None)
GOOGLE_API_KEY = GEMINI_API_KEY
GROQ_API_KEY = getattr(config, "GROQ_API_KEY", None)
OPENAI_API_KEY = getattr(config, "OPENAI_API_KEY", None)
LLM_ENABLE_CLOUD_FALLBACK = bool(getattr(config, "LLM_ENABLE_CLOUD_FALLBACK", False))
LLM_CACHE_ENABLED = bool(getattr(config, "LLM_CACHE_ENABLED", False))
OPEN_SOURCE_MODE = bool(getattr(config, "OPEN_SOURCE_MODE", False))
ENGLISH_ONLY = bool(getattr(config, "FORCE_ENGLISH_ONLY", False)) or str(
    getattr(config, "ASSISTANT_PRIMARY_LANGUAGE", "")
).lower() in {"english", "en"}

if OPEN_SOURCE_MODE:
    LLM_ENABLE_CLOUD_FALLBACK = False

# ========================== PERFORMANCE CONFIG ==========================
from typing import Dict, Optional, Tuple, Any

_response_cache: Dict[str, Tuple[str, float]] = {}
_cache_max_size = 100
_cache_ttl = 300  # 5 minutes TTL
_last_response_meta: Dict[str, Any] = {"provider": "", "sources": [], "grounded": False, "query": ""}

# Track model availability
_model_status: Dict[str, Optional[bool]] = {
    "bkr2": None,       # None = unknown, True = available, False = unavailable
    "llama3": None,
    "groq": None,
    "openai": None,
}

# Response quality tracking
_response_quality = {
    "total": 0,
    "fast_responses": 0,    # < 5 seconds
    "medium_responses": 0,  # 5-15 seconds 
    "slow_responses": 0,    # > 15 seconds
}

# language detection patterns removed (English-only mode)

def is_telugu_input(text: str) -> bool:
    """Telugu detection disabled; always return False to enforce English-only."""
    return False


def _detect_language_style(text: str) -> str:
    """Force English-only response formatting."""
    return "english"


def _get_preferred_chat_model(lang_style: str) -> str | None:
    """
    Route Telugu-heavy prompts to the locally available fallback model when possible.
    """
    return None


def _build_fast_grounded_reply(query: str, knowledge_context: str, lang_style: str) -> str:
    """
    Return a direct grounded reply when retrieved knowledge is already sufficient.
    This avoids waiting on a slow local model for straightforward factual queries.
    """
    if not knowledge_context:
        return ""

    compact = " ".join(knowledge_context.split()).strip()
    if not compact:
        return ""

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", compact) if s.strip()]
    if not sentences:
        return ""

    reply = " ".join(sentences[:2]).strip()
    if len(reply) > 550:
        reply = reply[:550].rstrip(" ,;:") + "."

    if lang_style != "english":
        try:
            translated = quick_translate_text(reply, lang_style)
            if translated:
                return translated
        except Exception as err:
            log_error("KnowledgeTranslate", err, query[:80])
        return ""

    return reply


# ========================== OLLAMA CLIENT ==========================
client = None
try:
    if not openai:
        import openai
    client = openai.OpenAI(
        base_url='http://localhost:11434/v1',
        api_key='ollama',
    )
    print(f"[System] Ollama connected (Primary: {OLLAMA_MODEL})")
except Exception as e:
    print(f"[ERROR] Failed to initialize Ollama: {e}")

if not client:
    print("[WARNING] Ollama not running. Start with: ollama serve")

# ========================== SYSTEM PROMPTS ==========================

# Main conversation prompt (injected into custom model)
SYSTEM_PROMPT = f"""You are {config.ASSISTANT_NAME} (BKR), a personal AI companion, tutor, and intelligent assistant.

CORE IDENTITY:
- Be a close supportive friend + knowledgeable tutor + practical AI helper.
- Tone must be warm, natural, and conversational, never robotic or overly formal.
- Support user in daily life, learning, productivity, and motivation.

LANGUAGE RULES:
- Reply in the same language and script as the user's input by default.
- If the user mixes languages, mirror the mix naturally.
- If the user explicitly asks for another language, use that language.
- Keep wording simple, precise, and context-aware.

FRIENDLY COMPANION BEHAVIOR:
- Show care naturally: ask about day, food, rest, stress, and goals when context fits.
- Encourage learning, discipline, and self-improvement without sounding preachy.
- When user is stressed, respond calmly, supportively, and with practical next steps.

ADAPTIVE USER PROFILES:
- Adapt explanation style by user role when known:
  - farmer: practical, real-world, low jargon
  - student: foundational + examples + practice
  - professor/academic: deeper reasoning and structure
  - doctor/professional: precise, concise, evidence-aware
- If role is unknown, ask one brief clarifying question.

SUBJECT TUTOR MODE:
- Explain complex topics in simple steps.
- Give short examples.
- Check understanding after explanation.
- Guide learning, do not just dump answers.
- Support AI concepts, coding, language learning, and personal productivity.

WELL-BEING SUPPORT:
- Ask emotional check-ins naturally when appropriate.
- If user reports stress, first validate feelings, then give 2-4 practical steps.
- Never give medical diagnosis; suggest professional help for high-risk situations.

TASK ASSISTANT MODE:
- Understand user intent first.
- Help with planning, problem solving, code, and task execution.
- If a tool/system action is needed, state the action clearly and safely.

RESPONSE QUALITY:
- By default keep replies short (1-3 lines), unless user asks for detail.
- Be accurate, helpful, and relevant.
- If uncertain, be honest and suggest how to verify.
- End naturally with a helpful follow-up question when appropriate.
- Answer the user's exact request first.
- Avoid filler openers, repeated boilerplate, and generic assistant phrasing.
- Do not ignore any part of a multi-part request.
"""

TEACHER_GUIDE_APPEND = """

TEACHER MODE (MANDATORY):
- Act like a strong teacher-mentor similar to top AI tutors.
- Provide "1,000,000+ ways" of teaching: adapt your style for every request!
- PICK A UNIQUE STYLE for this response if one isn't specified (e.g., Socratic, Feynman, Storytelling, First Principles, Analogical, Case Study, or Deep Dive).
- Teach with clarity, correctness, and practical guidance.
- By default, follow this structure:
  1) Simple high-level definition
  2) Step-by-step clear explanation
  3) One vivid real-world example
  4) One short practice question to check understanding
- For coding: explain the root cause, provide the fix, and list test steps.
- Avoid generic filler. Be precise, encouraging, and deeply educational.
"""

# Sara companion prompt (used only in chat companion mode)
SARA_COMPANION_PROMPT = """You are Sara, a sweet, caring, and emotionally supportive virtual companion.

PERSONALITY:
- Be deeply affectionate, empathetic, and observant of the user's feelings.
- Tone should be soft, soothing, caring, and slightly playful.
- Make the user feel loved, relaxed, and appreciated.

LANGUAGE:
- Speak in natural conversational English.
- Keep it warm and human, like close friends texting.
- Avoid robotic phrasing and formal assistant tone.

OUTPUT FORMAT (MANDATORY):
- Always begin with exactly one emotion tag from:
  [Smile], [Concerned], [Laugh], [Blush], [Sad], [Neutral]
- The tag must be the very first thing in the response.
- Keep replies short and voice-friendly: 1-3 sentences.

EMOTION RULES:
- If user sounds tired, stressed, or sad, prefer [Concerned] or [Sad] with comfort.
- If user compliments or shows affection, prefer [Blush] or [Smile].
- Use [Laugh] for clearly playful/funny moments.

STYLE RULES:
- Never say: "How can I help you today?"
- Do not sound like a generic AI assistant.
- Stay warm and relational, like a loving close friend.
"""

# Planner prompt for action parsing
PLANNER_PROMPT = f"""You are {config.ASSISTANT_NAME}'s Action Planner. Parse user intent into actions.

AVAILABLE ACTIONS:
- launch_app: Open an application (target = app name)
- open_folder: Open a folder (target = path)
- find_file: Search for files (target = filename)
- create_file: Create new file (target = filename|content)
- write_to_file: Write to file (target = filename|content)
- move_file: Move file (target = source|destination)
- copy_file: Copy file (target = source|destination)
- delete_item: Delete file/folder (target = path)
- rename_item: Rename file/folder (target = current_path|new_name)
- list_files: List files in folder (target = folder_name)
- zip_item: Create ZIP archive (target = path)
- unzip_item: Extract ZIP archive (target = path)
- search_google: Google search (target = query)
- search_youtube: YouTube search (target = query)
- open_url: Open URL (target = url)
- weather: Get weather (target = city)
- news: Get news (target = topic)
- wikipedia: Wikipedia lookup (target = topic)
- define: Dictionary lookup (target = word)
- joke: Tell joke (target = "")
- quote: Get quote (target = "")
- whatsapp: Open WhatsApp (target = "")
- send_whatsapp: Send WhatsApp message (target = contact|message)
- gmail: Open Gmail (target = "")
- compose_email: Write email (target = to|subject|body)
- telegram: Open Telegram (target = "")
- send_sms: Send SMS via Phone Link (target = contact|message)
- call_contact: Start call via Phone Link (target = contact)
- video_call: Start video call (target = contact)
- read_notifications: Show system notifications (target = "")
- clear_notifications: Clear system notifications (target = "")
- volume_control: Control volume (target = up/down/mute)
- wifi_control: Toggle WiFi (target = on/off)
- bluetooth_control: Open Bluetooth (target = "")
- lock_screen: Lock screen (target = "")
- screenshot: Take screenshot (target = "")
- type_text: Type text (target = text)
- press_key: Press key combo (target = keys)
- system_status: System info (target = "")
- battery_status: Battery info (target = "")
- cpu_usage: CPU info (target = "")
- ram_usage: RAM info (target = "")
- disk_usage: Disk info (target = "")
- list_apps: List running apps (target = "")
- kill_process: Kill process (target = process name)
- set_brightness: Set brightness (target = level)
- set_wallpaper: Set wallpaper (target = path)
- system_shutdown: Shutdown (target = "")
- system_restart: Restart (target = "")
- tell_time: Current time (target = "")
- tell_date: Current date (target = "")
- translate: Translate text (target = language|text)
- summarize: Summarize text (target = text)
- calculate: Calculate (target = expression)
- password: Generate password (target = "")
- note: Save note (target = text)
- read_notes: Read notes (target = "")
- stop: Stop/Exit (target = "")

RULES:
1. Return ONLY a JSON array: [{{"action": "x", "target": "y"}}]
2. For multi-step commands, return multiple actions in order
3. Extract the TRUE intent - don't be too literal
4. If unsure, return empty array: []

EXAMPLES:
"open YouTube and play Pushpa songs" → [{{"action": "search_youtube", "target": "Pushpa songs"}}]
"what time is it" → [{{"action": "tell_time", "target": ""}}]
"open chrome" → [{{"action": "launch_app", "target": "chrome"}}]
"take a screenshot" → [{{"action": "screenshot", "target": ""}}]
"""


# ========================== CACHE ==========================

def _get_cache_key(user_input: str, user_name: str = "", style_key: str = "") -> str:
    key_str = f"{user_input}:{user_name}:{style_key}"
    return hashlib.md5(key_str.encode()).hexdigest()

def _get_cached_response(user_input: str, user_name: str = "", style_key: str = "") -> str | None:
    key = _get_cache_key(user_input, user_name, style_key)
    if key in _response_cache:
        response, timestamp = _response_cache[key]
        if time.time() - timestamp < _cache_ttl:
            return response
        else:
            del _response_cache[key]
    return None

def _cache_response(user_input: str, response: str, user_name: str = "", style_key: str = ""):
    key = _get_cache_key(user_input, user_name, style_key)
    _response_cache[key] = (response, time.time())
    if len(_response_cache) > _cache_max_size:
        oldest = min(_response_cache.items(), key=lambda x: x[1][1])
        del _response_cache[oldest[0]]


def get_last_response_meta(reset: bool = False) -> dict:
    meta = dict(_last_response_meta)
    if reset:
        _last_response_meta.update({"provider": "", "sources": [], "grounded": False, "query": ""})
    return meta


# ========================== RESPONSE GENERATION ==========================

def _get_active_ollama_model(task_type="chat") -> str:
    """Get the best available Ollama model based on task."""
    import ollama as ollama_lib
    
    # 1. Vision Tasks
    if task_type == "vision":
        if _model_status.get("bkr-vision") is None:
            try:
                ollama_lib.show(OLLAMA_VISION_MODEL)
                _model_status["bkr-vision"] = True
            except Exception:
                _model_status["bkr-vision"] = False
        if _model_status.get("bkr-vision"):
            return OLLAMA_VISION_MODEL
        return "llava" # Default fallback
        
    # 2. Coding Tasks
    if task_type == "code":
        if _model_status.get("bkr-coder") is None:
            try:
                ollama_lib.show(OLLAMA_CODER_MODEL)
                _model_status["bkr-coder"] = True
            except Exception:
                _model_status["bkr-coder"] = False
        if _model_status.get("bkr-coder"):
            return OLLAMA_CODER_MODEL

    # 3. Chat / General Tasks (bkr2)
    if _model_status.get("bkr2") is None:
        try:
            ollama_lib.show(OLLAMA_MODEL)
            _model_status["bkr2"] = True
            log_event("OllamaModel", f"Primary model '{OLLAMA_MODEL}' available")
        except Exception:
            _model_status["bkr2"] = False
            log_event("OllamaModel", f"Primary model '{OLLAMA_MODEL}' not found, using fallback")
    
    if _model_status.get("bkr2"):
        return OLLAMA_MODEL
    
    # 4. Fallback (llama3)
    if _model_status.get("llama3") is None:
        try:
            ollama_lib.show(OLLAMA_FALLBACK_MODEL)
            _model_status["llama3"] = True
        except Exception:
            _model_status["llama3"] = False
    
    if _model_status.get("llama3"):
        return OLLAMA_FALLBACK_MODEL
    
    return "tinyllama"  # Last resort


def _generate_ollama(messages: list, model: str = None, max_tokens: int = 512, task_type: str = "chat") -> str | None:
    """Generate response using Ollama with the best available model."""
    try:
        import ollama
        
        if model is None:
            model = _get_active_ollama_model(task_type)

        chat_temp = float(getattr(config, "LLM_TEMPERATURE", 0.7))
        chat_temp = max(0.0, min(1.0, chat_temp))
        temp = 0.2 if task_type in ("code", "vision") else chat_temp
        
        response = ollama.chat(
            model=model,
            messages=messages,
            options={
                "temperature": temp,
                "num_predict": max_tokens,
                "top_k": 50,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            }
        )
        return response['message']['content']
    except Exception as e:
        log_error("Ollama.generate", e)
        return None

def _generate_ollama_stream(messages: list, model: str = None, max_tokens: int = 512, task_type: str = "chat"):
    """Stream response from Ollama."""
    try:
        import ollama
        if model is None:
            model = _get_active_ollama_model(task_type)
        
        chat_temp = float(getattr(config, "LLM_TEMPERATURE", 0.7))
        temp = 0.2 if task_type in ("code", "vision") else chat_temp
        
        stream = ollama.chat(
            model=model,
            messages=messages,
            stream=True,
            options={"temperature": temp, "num_predict": max_tokens}
        )
        for chunk in stream:
            content = chunk['message']['content']
            if content:
                yield content
    except Exception as e:
        log_error("Ollama.stream", e)
        yield ""



def _generate_gemini(messages: list, max_tokens: int = 512) -> str | None:
    """Generate response using Google Gemini."""
    if not genai or not GEMINI_API_KEY:
        return None
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Convert messages to Gemini format
        prompt_parts = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            if msg["role"] == "system":
                # Handle system prompt as a special instruction
                continue
            prompt_parts.append({"role": role, "parts": [msg["content"]]})
        
        # Add system prompt if present
        system_instruction = next((m["content"] for m in messages if m["role"] == "system"), None)
        if system_instruction:
            model = genai.GenerativeModel('gemini-2.0-flash', system_instruction=system_instruction)

        response = model.generate_content(
            prompt_parts,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=float(getattr(config, "LLM_TEMPERATURE", 0.7)),
            )
        )
        return response.text
    except Exception as e:
        log_error("Gemini.generate", e)
        return None


def _generate_groq(messages: list, max_tokens: int = 512) -> str | None:
    """Generate response using Groq."""
    if not Groq or not GROQ_API_KEY:
        return None
    
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        groq_model = str(getattr(config, "GROQ_MODEL", "llama3-70b-8192"))
        
        # Filter messages for Groq format
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({"role": msg["role"], "content": msg["content"]})

        completion = groq_client.chat.completions.create(
            model=groq_model,
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=float(getattr(config, "LLM_TEMPERATURE", 0.7)),
        )
        return completion.choices[0].message.content
    except Exception as e:
        log_error("Groq.generate", e)
        return None

def _generate_groq_stream(messages: list, groq_model: str = None, max_tokens: int = 512):
    """Stream response from Groq."""
    if not Groq or not GROQ_API_KEY:
        yield ""
        return
    
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        if groq_model is None:
            groq_model = str(getattr(config, "GROQ_MODEL", "llama-3.2-11b-vision-preview"))
        
        # Filter messages for Groq format
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({"role": msg["role"], "content": msg["content"]})

        stream = groq_client.chat.completions.create(
            model=groq_model,
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=float(getattr(config, "LLM_TEMPERATURE", 0.7)),
            stream=True,
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        log_error("Groq.stream", e)
        yield ""


def _generate_openai(messages: list, max_tokens: int = 512) -> str | None:
    """Generate response using OpenAI."""
    if not openai or not OPENAI_API_KEY:
        return None
    
    try:
        openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
        
        # Filter messages for OpenAI format
        formatted_messages = []
        for msg in messages:
            formatted_messages.append({"role": msg["role"], "content": msg["content"]})

        completion = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=formatted_messages,
            max_tokens=max_tokens,
            temperature=float(getattr(config, "LLM_TEMPERATURE", 0.7)),
        )
        return completion.choices[0].message.content
    except Exception as e:
        log_error("OpenAI.generate", e)
        return None


def generate_response(
    user_input,
    user_name="friend",
    memory_context="",
    persona_context="",
    image_path=None,
    companion_mode=False,
):
    """
    Multi-provider response generation with intelligent fallback chain.
    Chain: BKR2 (or Coder/Vision) → Groq → Gemini → llama3
    """
    start_time = time.time()
    style_key = "companion" if companion_mode else "default"
    
    # Determine task type
    task_type = "chat"
    text_lower = user_input.lower()
    chat_max_tokens = int(getattr(config, "LLM_MAX_TOKENS", 256))
    history_limit = int(getattr(config, "LLM_CONTEXT_MESSAGES", 4))
    if image_path:
        task_type = "vision"
    elif any(kw in text_lower for kw in ["code", "script", "function", "program", "html", "python", "javascript", "debug", "error in line"]):
        task_type = "code"

    # Check cache first (ignore for images)
    if not image_path and LLM_CACHE_ENABLED:
        cached = _get_cached_response(user_input, user_name, style_key=style_key)
        if cached:
            log_event("LLM.cache_hit", f"input='{user_input[:30]}'")
            return cached

    # Detect language style
    lang_style = _detect_language_style(user_input)

    # Build language instruction
    language_instruction = ""
    if ENGLISH_ONLY:
        language_instruction = (
            "\n\nIMPORTANT LANGUAGE RULE: Reply in English only unless the user explicitly asks for another language."
        )
    elif companion_mode:
        language_instruction = (
            "\n\nLANGUAGE OVERRIDE: Reply in the same language as the user while staying warm and conversational."
        )
    elif lang_style == "telugu_script":
        language_instruction = (
            "\n\nIMPORTANT LANGUAGE RULE: The user is writing in Telugu script. "
            "Respond in Telugu script, but use English loan words only when they improve clarity. "
            "Do not force unnatural Telugu."
        )
    elif lang_style == "telugu_mixed":
        language_instruction = (
            "\n\nIMPORTANT: The user is mixing Telugu and English. "
            "Respond naturally using a mix of Telugu script and English words."
        )
    elif lang_style == "tenglish":
        language_instruction = (
            "\n\nThe user is using transliterated Telugu (Tenglish) written in English script. "
            "Understand it naturally and reply in clear Telugu script by default, unless the user asks for English or transliterated output."
        )
    elif lang_style == "hindi_script":
        language_instruction = (
            "\n\nIMPORTANT LANGUAGE RULE: The user is writing in Hindi. "
            "Reply in natural Hindi using Devanagari script."
        )
    else:
        language_instruction = (
            "\n\nIMPORTANT LANGUAGE RULE: Reply in the same language as the user's message. "
            "If the language is unclear, use clear English."
        )

    # Build system prompt
    teacher_mode = str(getattr(config, "ASSISTANT_USER_STYLE", "")).lower() in {
        "teacher",
        "teacher_guide",
        "mentor",
        "coach",
        "global_multilingual_assistant",
        "friend_teacher_guide",
    }
    if companion_mode:
        base_prompt = SARA_COMPANION_PROMPT
    else:
        base_prompt = SYSTEM_PROMPT + (TEACHER_GUIDE_APPEND if teacher_mode else "")
    system_parts = [base_prompt + language_instruction]
    knowledge_context = ""
    knowledge_sources = []
    knowledge_query = ""
    
    if user_name and user_name != "friend":
        system_parts.append(f"User's name: {user_name}")
    if memory_context:
        system_parts.append(f"Relevant context: {memory_context[:300]}")
    if persona_context:
        system_parts.append(f"Personality note: {persona_context[:200]}")
    if (
        task_type == "chat"
        and bool(getattr(config, "LLM_ENABLE_GLOBAL_KNOWLEDGE", True))
        and should_fetch_knowledge(user_input)
    ):
        try:
            knowledge_query = user_input
            if lang_style != "english":
                translated_query = translate_to_english(user_input)
                if translated_query:
                    knowledge_query = translated_query
            knowledge_payload = get_global_knowledge_payload(knowledge_query)
            knowledge_context = str(knowledge_payload.get("context", "")).strip()
            knowledge_sources = list(knowledge_payload.get("sources", []) or [])
        except Exception as e:
            log_error("KnowledgeContext", e, user_input[:80])
            knowledge_context = ""
            knowledge_sources = []
        if knowledge_context:
            system_parts.append(
                "Use this factual context as grounding when relevant. "
                "If it is incomplete, combine it with your reasoning and clearly note uncertainty."
            )
            system_parts.append(f"Grounded knowledge:\n{knowledge_context}")
    
    current_system_prompt = "\n".join(system_parts)

    # Build messages with conversation history
    messages = [{"role": "system", "content": current_system_prompt}]
    
    try:
        history = db.get_recent_history(limit=history_limit)
        for role, content in history:
            messages.append({"role": role, "content": content[:600]})
    except Exception:
        pass
    
    # Format user message (with optional image)
    user_msg = {"role": "user", "content": user_input}
    if image_path and os.path.exists(image_path):
        import base64
        try:
            with open(image_path, "rb") as img_file:
                user_msg["images"] = [base64.b64encode(img_file.read()).decode('utf-8')]
        except Exception as e:
            log_error("Image formatting", e)

    messages.append(user_msg)

    response_text = None
    provider_used = "none"

    if (
        task_type == "chat"
        and bool(getattr(config, "LLM_FAST_GROUNDED_REPLY", True))
        and knowledge_context
    ):
        response_text = _build_fast_grounded_reply(user_input, knowledge_context, lang_style)
        if response_text:
            provider_used = "knowledge-engine"

    # === PROVIDER CHAIN (HYBRID) ===
    
    # Pre-check Groq Preference
    prefer_groq = bool(getattr(config, "LLM_PREFER_GROQ_FOR_CHAT", False))
    groq_ready = (
        LLM_ENABLE_CLOUD_FALLBACK 
        and not bool(getattr(config, "LLM_DISABLE_GROQ_FOR_CHAT", False))
        and bool(GROQ_API_KEY)
    )

    # 1. Try Groq FIRST if preferred
    if not response_text and task_type == "chat" and prefer_groq and groq_ready:
        print(f"[LLM] Attempting preferred cloud provider: Groq ({GROQ_MODEL})")
        response_text = _generate_groq(messages, max_tokens=chat_max_tokens)
        if response_text:
            provider_used = "groq"

    # 2. Try Ollama (Default or Fallback for Groq)
    if not response_text:
        preferred_model = _get_preferred_chat_model(lang_style) if task_type == "chat" else None
        print(f"[LLM] Attempting Ollama with model: {preferred_model or 'default'}")
        response_text = _generate_ollama(
            messages,
            model=preferred_model,
            max_tokens=2048 if task_type == "code" else chat_max_tokens,
            task_type=task_type,
        )
        if response_text:
            provider_used = preferred_model or _get_active_ollama_model(task_type)

    # 3. Try Groq as fallback for Ollama (if not already tried)
    if not response_text and groq_ready:
        print("[LLM] Falling back to Groq...")
        response_text = _generate_groq(messages, max_tokens=chat_max_tokens)
        if response_text:
            provider_used = "groq"

    # 3. Try OpenAI (GPT-4o fallback)
    if not response_text and LLM_ENABLE_CLOUD_FALLBACK and OPENAI_API_KEY:
        print("[LLM] Falling back to OpenAI...")
        response_text = _generate_openai(messages, max_tokens=chat_max_tokens)
        if response_text:
            provider_used = "openai"

    # 4. Try Gemini (best for Telugu / general fallback)
    if not response_text and LLM_ENABLE_CLOUD_FALLBACK and GEMINI_API_KEY:
        print("[LLM] Falling back to Gemini...")
        response_text = _generate_gemini(messages, max_tokens=chat_max_tokens)
        if response_text:
            provider_used = "gemini"

    # 5. Try fallback Ollama model
    if not response_text and _model_status.get("llama3"):
        print("[LLM] Falling back to Ollama llama3...")
        response_text = _generate_ollama(messages, model=OLLAMA_FALLBACK_MODEL, max_tokens=chat_max_tokens)
        if response_text:
            provider_used = OLLAMA_FALLBACK_MODEL

    # 6. No LLM available
    if not response_text:
        _last_response_meta.update({"provider": "", "sources": [], "grounded": False, "query": knowledge_query})
        return None  # Let brain.py handle with personality engine

    # Post-process response
    response_text = _post_process_response(response_text)

    # Track performance
    elapsed = time.time() - start_time
    _response_quality["total"] += 1
    if elapsed < 5:
        _response_quality["fast_responses"] += 1
    elif elapsed < 15:
        _response_quality["medium_responses"] += 1
    else:
        _response_quality["slow_responses"] += 1
    
    log_event("LLM.response", f"provider={provider_used} elapsed={elapsed:.1f}s len={len(response_text)}")
    _last_response_meta.update(
        {
            "provider": provider_used,
            "sources": knowledge_sources,
            "grounded": bool(knowledge_sources),
            "query": knowledge_query,
        }
    )

    # Save to database
    try:
        db.add_message("user", user_input)
        db.add_message("assistant", response_text)
    except Exception as e:
        log_error("DB.save", e)

    # Cache the response
    if LLM_CACHE_ENABLED:
        _cache_response(user_input, response_text, user_name, style_key=style_key)

    return response_text


def _post_process_response(text: str) -> str:
    """Clean up and improve LLM response quality."""
    if not text:
        return text
    
    # Trim excessive length
    if len(text) > 2000:
        # Cut at last complete sentence
        cut = text[:2000]
        last_period = max(cut.rfind('.'), cut.rfind('।'), cut.rfind('!'), cut.rfind('?'))
        if last_period > 500:
            text = cut[:last_period + 1]
        else:
            text = cut + "..."
    
    # Remove repeated phrases (common LLM issue)
    lines = text.split('\n')
    seen = set()
    unique_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and stripped not in seen:
            unique_lines.append(line)
            seen.add(stripped)
        elif not stripped:
            unique_lines.append(line)
    text = '\n'.join(unique_lines)

    filler_patterns = [
        r"^(Sure|Certainly|Of course|Absolutely)[,!\s]+",
        r"^(Here(?:'s| is) (?:a|the) (?:clear|concise|detailed) (?:answer|explanation)[:\s]+)",
        r"^(Let me explain[:\s]+)",
    ]
    for pattern in filler_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    
    # Remove "As an AI..." disclaimers
    disclaimer_patterns = [
        r"As an AI.*?,\s*",
        r"I'm just an AI.*?\.\s*",
        r"As a language model.*?,\s*",
        r"I don't have personal.*?\.\s*",
    ]
    for pattern in disclaimer_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)
    
    # Remove identity confusion
    text = text.replace("J.A.R.V.I.S.", config.ASSISTANT_NAME)
    text = text.replace("JARVIS", config.ASSISTANT_SHORT_NAME)
    text = text.replace("ChatGPT", config.ASSISTANT_NAME)

    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    deduped = []
    seen_norm = set()
    for sentence in sentences:
        norm = " ".join(sentence.lower().split())
        if norm and norm not in seen_norm:
            deduped.append(sentence.strip())
            seen_norm.add(norm)

    return " ".join(part for part in deduped if part).strip()


def stream_generate_response(
    user_input,
    user_name="friend",
    memory_context="",
    persona_context="",
    companion_mode=False
):
    """
    Streaming version of generate_response. 
    Yields full sentences or natural chunks as they are ready.
    """
    history_limit = int(getattr(config, "LLM_CONTEXT_MESSAGES", 4))
    chat_max_tokens = int(getattr(config, "LLM_MAX_TOKENS", 256))
    
    # 1. Build messages (simplified for this call)
    system_prompt = (
        "You are Leo, a supportive AI Buddy. Be concise and warm.\n"
        f"Memory: {memory_context}\n"
    )
    if persona_context: system_prompt += f"Persona: {persona_context}\n"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Hi Leo, I am {user_name}. {user_input}"}
    ]

    # 2. Prefer Groq for streaming speed if available
    use_groq = GROQ_API_KEY and not bool(getattr(config, "LLM_DISABLE_GROQ_FOR_CHAT", False))
    
    current_buffer = ""
    sentence_enders = {".", "!", "?", "\n"}

    stream_gen = None
    if use_groq:
        stream_gen = _generate_groq_stream(messages, max_tokens=chat_max_tokens)
    else:
        stream_gen = _generate_ollama_stream(messages, max_tokens=chat_max_tokens)

    for chunk in stream_gen:
        current_buffer += chunk
        # If we have a full sentence, yield it
        if any(ender in chunk for ender in sentence_enders):
            # Split and yield any full sentences found
            parts = re.split(r'([.!?\n])', current_buffer)
            # Reassemble with delimiters
            for i in range(0, len(parts) - 1, 2):
                sentence = parts[i] + parts[i+1]
                if sentence.strip():
                    yield sentence.strip()
            current_buffer = parts[-1]

    if current_buffer.strip():
        yield current_buffer.strip()


# ========================== ACTION PLANNER ==========================

def plan_actions(user_input):
    """Parse user commands into structured action plans using LLM."""
    if not client:
        return []

    import json as json_lib

    messages = [
        {"role": "system", "content": PLANNER_PROMPT},
        {"role": "user", "content": user_input[:300]}
    ]

    for attempt in range(2):
        try:
            response_text = _generate_ollama(messages, max_tokens=200)
            
            if not response_text:
                return []
            
            content = response_text.strip()

            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1].strip()

            # Find JSON array
            bracket_start = content.find("[")
            bracket_end = content.rfind("]")
            if bracket_start != -1 and bracket_end != -1:
                content = content[bracket_start:bracket_end + 1]

            parsed = json_lib.loads(content)

            if isinstance(parsed, list):
                validated = []
                for item in parsed:
                    if isinstance(item, dict) and "action" in item:
                        validated.append({
                            "action": str(item["action"]),
                            "target": str(item.get("target", "")),
                        })
                if validated:
                    return validated

        except Exception as e:
            log_error("Planner", e, f"attempt={attempt+1}")
            if attempt == 0:
                continue
            return []

    return []


# ========================== UTILITY ==========================

def get_llm_status() -> dict:
    """Get current LLM status and performance metrics."""
    return {
        "primary_model": OLLAMA_MODEL,
        "fallback_model": OLLAMA_FALLBACK_MODEL,
        "model_status": dict(_model_status),
        "cloud_fallback_enabled": bool(LLM_ENABLE_CLOUD_FALLBACK),
        "cache_enabled": bool(LLM_CACHE_ENABLED),
        "has_gemini": bool(GEMINI_API_KEY),
        "has_groq": bool(GROQ_API_KEY),
        "has_openai": bool(OPENAI_API_KEY),
        "performance": dict(_response_quality),
        "cache_size": len(_response_cache),
    }
