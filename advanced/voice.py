"""
Advanced Voice Module for BKR 2.0 - Lip-Sync Edition.

Features:
- Local-first STT/TTS provider routing
- Real-time amplitude and viseme state for avatar lip-sync
- Fallback-safe playback and recognition pipeline
"""
import os
import threading
import subprocess
import shutil
import sys
import importlib.util
import glob
import json
import config
import asyncio
import edge_tts
from playsound import playsound
import tempfile
import re
import numpy as np
import io
import wave
import time
import requests

from core.companion_style import extract_emotion_tag

# --- TEXT TO SPEECH ENGINE ---
# NOTE: pyttsx3 is run in a SUBPROCESS because eventlet (used by Flask-SocketIO)
# monkey-patches Python's threading/IO which completely breaks pyttsx3's 
# Windows COM (SAPI5) calls. A subprocess has clean COM initialization.

# Lock to prevent concurrent speak() calls
_speak_lock = threading.Lock()

# ==================== LIP-SYNC GLOBAL STATE ====================
# These are shared between voice.py and visual_window.py
IS_SPEAKING = False
LIP_SYNC_ENABLED = True
CURRENT_AMPLITUDE = 0.0  # 0.0 to 1.0 - real-time audio level
CURRENT_VISEME = "neutral"  # Current mouth shape
TARGET_VISEME = "neutral"  # Target mouth shape for smooth transition
VISEME_TRANSITION_PROGRESS = 1.0  # 0.0 to 1.0 - how close we are to target
TEXT_BEING_SPOKEN = ""  # Current text being spoken
SYLLABLE_TIMING = []  # Timing for each syllable/viseme
CURRENT_SYLLABLE_INDEX = 0

# Last speech timestamp for timing
_last_speech_end = 0.0
_last_spoken_text = ""

# Lip-sync configuration
LIP_SYNC_UPDATE_INTERVAL = 0.05  # 50ms between updates
LIP_SYNC_SMOOTHING = 0.3  # How fast amplitude changes (0.1-0.9)

# Event for lip-sync animation to subscribe to
lip_sync_signal = None  # Will be set by visual_window

# Track if ffmpeg warning has been shown
_ffmpeg_warned = False
_pygame_warned = False


def _find_ffmpeg_tool(tool_name: str) -> str | None:
    """
    Resolve ffmpeg/ffprobe binary path.
    Handles PATH-based discovery and common winget install locations.
    """
    found = shutil.which(tool_name)
    if found:
        return found

    exe = f"{tool_name}.exe" if os.name == "nt" else tool_name
    localapp = os.environ.get("LOCALAPPDATA", "")
    if localapp:
        winget_base = os.path.join(localapp, "Microsoft", "WinGet", "Packages")
        patterns = [
            os.path.join(winget_base, "Gyan.FFmpeg_*", "*", "bin", exe),
            os.path.join(winget_base, "*FFmpeg*", "*", "bin", exe),
        ]
        for pattern in patterns:
            matches = glob.glob(pattern)
            if matches:
                return matches[0]
    return None


def _has_ffmpeg_tools() -> bool:
    """Return True only when both ffmpeg and ffprobe are available."""
    return bool(_find_ffmpeg_tool("ffmpeg")) and bool(_find_ffmpeg_tool("ffprobe"))


def _in_echo_guard_window() -> bool:
    """
    Block microphone capture while TTS is speaking and briefly right after.
    Prevents the assistant from hearing its own voice as user input.
    """
    if IS_SPEAKING:
        return True
    guard_seconds = float(getattr(config, "VOICE_ECHO_GUARD_SECONDS", 0.9))
    if guard_seconds <= 0:
        return False
    return (time.time() - _last_speech_end) < guard_seconds


def _normalize_for_match(text: str) -> str:
    """Normalize transcript/text for robust echo comparisons."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\u0c00-\u0c7fa-z0-9\s]+", " ", text)
    return " ".join(text.split()).strip()


def _tokenize_for_match(text: str) -> set[str]:
    if not text:
        return set()
    return set(re.findall(r"[\u0c00-\u0c7fa-z0-9]+", text))


def is_likely_echo(transcript: str) -> bool:
    """
    Heuristic echo detection: ignore transcripts that closely match
    assistant speech within a short post-speech window.
    """
    global _last_spoken_text, _last_speech_end

    candidate = _normalize_for_match(transcript or "")
    if not candidate:
        return False

    window = float(getattr(config, "VOICE_ECHO_MATCH_WINDOW_SECONDS", 6.0))
    if window <= 0 or (time.time() - _last_speech_end) > window:
        return False

    spoken = _normalize_for_match(_last_spoken_text)
    if not spoken:
        return False

    # Direct containment catches most simple repeats.
    if candidate in spoken or spoken in candidate:
        return True

    c_tokens = _tokenize_for_match(candidate)
    s_tokens = _tokenize_for_match(spoken)
    if not c_tokens or not s_tokens:
        return False

    overlap = len(c_tokens & s_tokens) / max(1, len(c_tokens))
    return overlap >= 0.7

# Simple phoneme to viseme mapping
PHONEME_TO_VISEME = {
    # Vowels
    'a': 'A', 'e': 'E', 'i': 'I', 'o': 'O', 'u': 'U',
    'aa': 'A', 'ee': 'E', 'ii': 'I', 'oo': 'O', 'uu': 'U',
    'ai': 'E', 'au': 'O', 'ou': 'O',
    # Consonants that affect mouth shape
    'b': 'MBP', 'm': 'MBP', 'p': 'MBP',
    'f': 'STH', 'v': 'STH', 'th': 'STH', 's': 'STH', 'z': 'STH',
    't': 'STH', 'd': 'STH', 'n': 'STH', 'l': 'E',
    'r': 'E', 'j': 'E', 'k': 'A', 'g': 'A', 'h': 'A',
    'w': 'U', 'y': 'E',
}


def _allow_cloud_fallback() -> bool:
    if bool(getattr(config, "LOCAL_SPEECH_ONLY", False)) or bool(getattr(config, "OPEN_SOURCE_MODE", False)):
        return False
    return bool(getattr(config, "STT_ALLOW_CLOUD_FALLBACK", False))


_TELUGU_RE = re.compile(r"")
_DEVANAGARI_RE = re.compile(r"")
_TAMIL_RE = re.compile(r"[\u0B80-\u0BFF]")
_KANNADA_RE = re.compile(r"[\u0C80-\u0CFF]")
_MALAYALAM_RE = re.compile(r"[\u0D00-\u0D7F]")
_PIPER_VOICE_CACHE = {}
_VOSK_MODEL_CACHE = {}


def _detect_text_language(text: str) -> str:
    return "en"


def _resolve_piper_model_path(text: str = "") -> str:
    lang = _detect_text_language(text)
    configured = getattr(config, "PIPER_MODEL_PATHS", {}) or {}
    candidates = []
    if isinstance(configured, dict):
        candidates.extend(
            [
                str(configured.get(lang, "")).strip(),
                str(configured.get("en", "")).strip(),
            ]
        )
    candidates.append(str(getattr(config, "PIPER_MODEL_PATH", "")).strip())

    model_dir = str(getattr(config, "PIPER_MODEL_DIR", "")).strip()
    if model_dir and os.path.isdir(model_dir):
        for pattern in ("*.onnx", "*/*.onnx"):
            for path in glob.glob(os.path.join(model_dir, pattern)):
                candidates.append(path)

    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return ""


def _resolve_piper_config_path(model_path: str) -> str | None:
    if not model_path:
        return None
    for candidate in (f"{model_path}.json", os.path.splitext(model_path)[0] + ".onnx.json"):
        if candidate and os.path.exists(candidate):
            return candidate
    return None


def _resolve_vosk_model_paths() -> list[str]:
    candidates = []
    configured = getattr(config, "VOSK_MODEL_PATHS", {}) or {}
    active_language = str(getattr(config, "STT_ACTIVE_LANGUAGE", "en")).strip().lower()
    if isinstance(configured, dict):
        ordered_keys = ["en", "en-in", "hi", "te"]
        if active_language and active_language != "auto":
            ordered_keys = [active_language] + [key for key in ordered_keys if key != active_language]
        for key in ordered_keys:
            path = str(configured.get(key, "")).strip()
            if path:
                candidates.append(path)

    fallback_path = str(getattr(config, "VOSK_MODEL_PATH", "")).strip()
    if fallback_path:
        candidates.append(fallback_path)

    model_dir = str(getattr(config, "VOSK_MODEL_DIR", "")).strip()
    if model_dir and os.path.isdir(model_dir):
        for path in glob.glob(os.path.join(model_dir, "*")):
            if os.path.isdir(path):
                candidates.append(path)

    resolved = []
    seen = set()
    for path in candidates:
        normalized = os.path.abspath(path)
        if normalized in seen or not os.path.isdir(normalized):
            continue
        seen.add(normalized)
        resolved.append(normalized)
    return resolved

def _safe_console_text(text: str) -> str:
    """Avoid Windows cp1252 encode crashes when printing Telugu text."""
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        return text.encode(encoding, errors="replace").decode(encoding, errors="replace")
    except Exception:
        return text.encode("ascii", errors="replace").decode("ascii", errors="replace")


def _normalize_assistant_text(text: str) -> str:
    """
    Normalize legacy identity terms so spoken output stays in BKR 2.0 persona.
    """
    if not text:
        return text
    normalized = text
    normalized = normalized.replace("J.A.R.V.I.S.", config.ASSISTANT_NAME)
    normalized = normalized.replace("JARVIS", config.ASSISTANT_SHORT_NAME)
    normalized = normalized.replace("Sir", "").replace(" ,", ",")
    return " ".join(normalized.split())


def _sanitize_for_speech(raw_text: str) -> str:
    """Strip leading Sara emotion tags and URLs so TTS never reads them aloud."""
    tag, body = extract_emotion_tag(raw_text or "")
    clean = body if tag and body else (raw_text or "")
    
    # Strip URLs
    clean = re.sub(r'https?://\S+|www\.\S+', '', clean)
    
    return _normalize_assistant_text(clean)


def _elevenlabs_voice_settings(mood: str) -> dict:
    """Mood-aware ElevenLabs voice tuning for softer companion speech."""
    stability = float(getattr(config, "ELEVENLABS_STABILITY", 0.35))
    similarity = float(getattr(config, "ELEVENLABS_SIMILARITY_BOOST", 0.78))
    style = float(getattr(config, "ELEVENLABS_STYLE", 0.45))

    mood_l = (mood or "").lower()
    if mood_l in {"happy", "proud"}:
        style = min(1.0, style + 0.15)
    elif mood_l in {"concerned", "sad"}:
        stability = min(1.0, stability + 0.15)
        style = max(0.0, style - 0.1)

    return {
        "stability": stability,
        "similarity_boost": similarity,
        "style": style,
        "use_speaker_boost": bool(getattr(config, "ELEVENLABS_USE_SPEAKER_BOOST", True)),
    }


def _generate_edge_tts_audio(text: str) -> str:
    """Generate MP3 audio with Edge TTS and return temp file path."""
    voice = _select_edge_voice(text)

    async def generate_speech():
        communicate = edge_tts.Communicate(
            text,
            voice,
            volume="+80%",
            rate="+0%",
        )
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_path = tmp_file.name
        await communicate.save(tmp_path)
        return tmp_path

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(generate_speech())
    finally:
        try:
            loop.close()
        except Exception:
            pass


def _select_edge_voice(text: str) -> str:
    """
    Pick an Edge TTS voice based on script detection.
    """
    return str(getattr(config, "ASSISTANT_VOICE_EN", "en-US-AriaNeural"))


def _generate_elevenlabs_audio(text: str, mood: str = "neutral") -> str | None:
    """Generate MP3 audio using ElevenLabs API and return temp file path."""
    api_key = (
        getattr(config, "ELEVENLABS_API_KEY", None)
        or os.getenv("ELEVENLABS_API_KEY")
    )
    if not api_key:
        return None

    voice_id = str(getattr(config, "ELEVENLABS_VOICE_ID", "")).strip()
    if not voice_id:
        return None

    model_id = str(getattr(config, "ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")).strip()
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": _elevenlabs_voice_settings(mood),
    }
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    response = requests.post(
        url,
        params={"output_format": "mp3_44100_128"},
        headers=headers,
        json=payload,
        timeout=60,
        stream=True,
    )
    if not response.ok:
        raise RuntimeError(f"ElevenLabs API error: {response.status_code} {response.text[:180]}")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                tmp_file.write(chunk)
        return tmp_file.name


def _generate_piper_audio(text: str) -> str | None:
    """
    Generate WAV audio with local Piper TTS.
    """
    model_path = _resolve_piper_model_path(text)
    if not model_path:
        raise RuntimeError("Piper model not found. Run the local model bootstrap or set config.PIPER_MODEL_PATHS.")

    try:
        from piper.voice import PiperVoice
    except Exception as err:
        raise RuntimeError(f"Piper import failed: {err}") from err

    cache_key = os.path.abspath(model_path)
    voice = _PIPER_VOICE_CACHE.get(cache_key)
    if voice is None:
        config_path = _resolve_piper_config_path(model_path)
        voice = PiperVoice.load(model_path, config_path=config_path)
        _PIPER_VOICE_CACHE[cache_key] = voice

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        out_path = tmp_file.name

    with wave.open(out_path, "wb") as wav_file:
        voice.synthesize_wav(text or "", wav_file)
    return out_path


def _play_audio_with_lipsync(audio_path: str) -> bool:
    """
    Play audio file and drive lip-sync amplitude monitoring.
    Returns True when playback succeeded using at least one backend.
    """
    safe_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", ".tts_cache")
    os.makedirs(safe_dir, exist_ok=True)
    safe_path = os.path.join(safe_dir, "tts_output.mp3")
    playback_ok = False

    audio_path_str = str(audio_path)
    try:
        if os.path.exists(safe_path):
            os.remove(safe_path)
        shutil.copy2(audio_path_str, safe_path)
        play_path = safe_path
    except Exception:
        play_path = audio_path_str

    try:
        if LIP_SYNC_ENABLED:
            amp_thread = threading.Thread(
                target=_amplitude_monitor_thread,
                args=(play_path,),
                daemon=True,
            )
            amp_thread.start()

        try:
            import pygame
            pygame_available = True
        except ImportError:
            pygame_available = False
        if pygame_available:
            import pygame
            try:
                pygame.mixer.init()
                pygame.mixer.music.load(play_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy() and IS_SPEAKING:
                    time.sleep(0.1)
                pygame.mixer.music.stop()
                pygame.mixer.quit()
                playback_ok = True
            except Exception as e:
                print(f"[Voice] Pygame playback error: {e}")
                pygame_available = False # Fallback to playsound
        
        if not pygame_available:
            global _pygame_warned
            if not _pygame_warned:
                print("[Voice] pygame not installed; using fallback playback backend.")
                _pygame_warned = True
            
            print(f"[Voice] Attempting playsound with path: {play_path}")
            try:
                playsound(play_path, block=True)
                playback_ok = True
                print("[Voice] playsound finished successfully.")
            except Exception as ps_err:
                print(f"[Voice] playsound error: {ps_err}")
                playback_ok = False
                
    except Exception as play_err:
        print(f"[Voice] Audio playback failed: {play_err}")
        # Last fallback: native TTS pipeline (pyttsx3) handled by caller.
        playback_ok = False
    finally:
        for path_to_clean in [audio_path_str, safe_path]:
            if path_to_clean and os.path.exists(path_to_clean):
                try:
                    os.remove(path_to_clean)
                except Exception:
                    pass
    return playback_ok


def is_telugu(text):
    """Telugu detection disabled (English-only)."""
    return False

def _should_use_telugu_voice(text: str) -> bool:
    return False


def _analyze_text_for_visemes(text: str) -> list:
    """
    Analyze text and generate a sequence of visemes with timing.
    Returns list of (viseme, start_time, duration) tuples.
    """
    global SYLLABLE_TIMING, CURRENT_SYLLABLE_INDEX
    SYLLABLE_TIMING = []
    
    # Simple word-by-word analysis
    words = text.lower().split()
    current_time: float = 0.0
    
    for word in words:
        # Estimate duration based on word length (rough approximation)
        base_duration = float(0.15 + len(word) * 0.05)
        
        # Analyze first character for viseme
        first_char = word[0] if word else 'a'
        
        # Determine viseme from phoneme mapping
        viseme = 'neutral'
        for phoneme, v in sorted(PHONEME_TO_VISEME.items(), key=lambda x: -len(x[0])):
            if phoneme in word:
                viseme = v
                break
        
        # Add small pause between words
        v_start: float = float(current_time)
        SYLLABLE_TIMING.append({
            'viseme': str(viseme),
            'start': v_start,
            'duration': float(base_duration),
            'word': str(word)
        })
        current_time = float(v_start + base_duration + 0.08)
    
    CURRENT_SYLLABLE_INDEX = 0
    return SYLLABLE_TIMING


def _get_current_viseme_at_time(elapsed_time: float) -> tuple:
    """
    Get the appropriate viseme at the given elapsed time.
    Returns (viseme, amplitude_factor)
    """
    global SYLLABLE_TIMING, CURRENT_SYLLABLE_INDEX
    
    if not SYLLABLE_TIMING:
        return "neutral", 0.0
    
    for i, syllable in enumerate(SYLLABLE_TIMING):
        start = syllable['start']
        duration = syllable['duration']
        
        if start <= elapsed_time < start + duration:
            CURRENT_SYLLABLE_INDEX = i
            # Amplitude peaks in middle of syllable
            mid = start + duration / 2
            if elapsed_time < mid:
                # Rising
                amplitude = (elapsed_time - start) / (duration / 2)
            else:
                # Falling
                amplitude = 1.0 - (elapsed_time - mid) / (duration / 2)
            
            return syllable['viseme'], max(0.3, min(1.0, amplitude))
    
    # Past all syllables
    if SYLLABLE_TIMING:
        last = SYLLABLE_TIMING[-1]
        if elapsed_time > last['start'] + last['duration'] + 0.2:
            return "neutral", 0.0
    
    return "neutral", 0.0


def _amplitude_monitor_thread(audio_path: str):
    """
    Monitor audio playback amplitude in real-time for lip-sync.
    Uses simple amplitude detection from audio file.
    """
    global CURRENT_AMPLITUDE, CURRENT_VISEME, TARGET_VISEME, VISEME_TRANSITION_PROGRESS
    global IS_SPEAKING, TEXT_BEING_SPOKEN
    
    if not os.path.exists(audio_path):
        return
    
    try:
        # Try to use pydub for amplitude analysis
        try:
            ffmpeg_path = _find_ffmpeg_tool("ffmpeg")
            ffprobe_path = _find_ffmpeg_tool("ffprobe")
            if not (ffmpeg_path and ffprobe_path):
                raise RuntimeError("ffmpeg_missing")

            # Ensure pydub can find binaries even if PATH is stale in this shell.
            ffmpeg_dir = os.path.dirname(ffmpeg_path)
            if ffmpeg_dir and ffmpeg_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

            from pydub import AudioSegment
            AudioSegment.converter = ffmpeg_path
            AudioSegment.ffprobe = ffprobe_path
            audio = AudioSegment.from_file(audio_path)
            
            # Get samples as numpy array
            samples = np.array(audio.get_array_of_samples())
            if audio.channels > 1:
                samples = samples[::audio.channels]  # Take one channel
            
            # Calculate frame-wise amplitude
            frame_duration_ms = int(LIP_SYNC_UPDATE_INTERVAL * 1000)
            n_frames = len(samples) // (audio.frame_rate * LIP_SYNC_UPDATE_INTERVAL)
            
            if n_frames > 0:
                frame_size = len(samples) // n_frames
                
                for i in range(min(n_frames, 500)):  # Limit processing
                    if not IS_SPEAKING:
                        break
                    
                    start_idx = i * frame_size
                    end_idx = min((i + 1) * frame_size, len(samples))
                    
                    if start_idx >= len(samples):
                        break
                    
                    frame_samples = samples[start_idx:end_idx]
                    
                    # Calculate RMS amplitude
                    if len(frame_samples) > 0:
                        rms = np.sqrt(np.mean(frame_samples.astype(float)**2))
                        # Normalize to 0-1 range (with some headroom)
                        amplitude = min(1.0, rms / 8000.0)
                        
                        # Smooth the amplitude
                        CURRENT_AMPLITUDE = CURRENT_AMPLITUDE * (1 - LIP_SYNC_SMOOTHING) + amplitude * LIP_SYNC_SMOOTHING
                        
                        # Get corresponding viseme based on timing
                        elapsed = i * LIP_SYNC_UPDATE_INTERVAL
                        target_viseme, amp_factor = _get_current_viseme_at_time(elapsed)
                        
                        if target_viseme != TARGET_VISEME:
                            TARGET_VISEME = target_viseme
                            VISEME_TRANSITION_PROGRESS = 0.0
                        
                        # Update current viseme based on transition
                        if VISEME_TRANSITION_PROGRESS < 1.0:
                            VISEME_TRANSITION_PROGRESS = min(1.0, VISEME_TRANSITION_PROGRESS + 0.3)
                            if VISEME_TRANSITION_PROGRESS >= 1.0:
                                CURRENT_VISEME = TARGET_VISEME
                        
                        # Adjust amplitude based on viseme type
                        if CURRENT_VISEME in ["A", "O"]:
                            CURRENT_AMPLITUDE *= 1.2
                        elif CURRENT_VISEME in ["E", "I"]:
                            CURRENT_AMPLITUDE *= 0.9
                        elif CURRENT_VISEME in ["MBP", "U"]:
                            CURRENT_AMPLITUDE *= 0.5
                        
                        CURRENT_AMPLITUDE = min(1.0, CURRENT_AMPLITUDE)
                    
                    time.sleep(LIP_SYNC_UPDATE_INTERVAL)
                    
        except Exception as e:
            # pydub fails if ffmpeg/ffprobe are missing or import fails.
            global _ffmpeg_warned
            if not _ffmpeg_warned:
                if str(e) == "ffmpeg_missing":
                    print("[LipSync] ffmpeg/ffprobe not found for audio analysis, using text-based fallback.")
                elif isinstance(e, ImportError):
                    print("[LipSync] pydub not available, using text-based fallback.")
                else:
                    print(f"[LipSync] Audio analysis unavailable ({e}); using text-based fallback.")
                _ffmpeg_warned = True

            # Fallback: simulate amplitude based on text visemes
            if TEXT_BEING_SPOKEN:
                _analyze_text_for_visemes(TEXT_BEING_SPOKEN)
                start_time = time.time()
                
                while IS_SPEAKING and TEXT_BEING_SPOKEN:
                    elapsed = time.time() - start_time
                    viseme, amplitude = _get_current_viseme_at_time(elapsed)
                    
                    CURRENT_VISEME = viseme
                    TARGET_VISEME = viseme
                    CURRENT_AMPLITUDE = amplitude
                    VISEME_TRANSITION_PROGRESS = 1.0
                    
                    time.sleep(LIP_SYNC_UPDATE_INTERVAL)
                    
    except Exception as e:
        print(f"[LipSync] Amplitude monitor error: {e}")
    
    finally:
        # Reset when done
        CURRENT_AMPLITUDE = 0.0
        CURRENT_VISEME = "neutral"
        TARGET_VISEME = "neutral"


def _simulate_text_lipsync(text: str):
    """
    Fallback lip-sync driver when no analyzable audio stream is available.
    Works well for pyttsx3 path.
    """
    global CURRENT_AMPLITUDE, CURRENT_VISEME, TARGET_VISEME, VISEME_TRANSITION_PROGRESS
    if not text:
        return
    _analyze_text_for_visemes(text)
    start_time = time.time()
    while IS_SPEAKING:
        elapsed = time.time() - start_time
        viseme, amplitude = _get_current_viseme_at_time(elapsed)
        CURRENT_VISEME = viseme
        TARGET_VISEME = viseme
        CURRENT_AMPLITUDE = amplitude
        VISEME_TRANSITION_PROGRESS = 1.0
        if viseme == "neutral" and elapsed > max(1.0, len(text) * 0.04):
            break
        time.sleep(LIP_SYNC_UPDATE_INTERVAL)
    CURRENT_AMPLITUDE = 0.0
    CURRENT_VISEME = "neutral"
    TARGET_VISEME = "neutral"


def speak(text, mood="neutral"):
    """
    Speak text aloud with real-time lip-sync.
    Uses configurable providers (Edge-TTS / ElevenLabs).
    Includes amplitude tracking for visual lip-sync animation.
    """
    global IS_SPEAKING, TEXT_BEING_SPOKEN, _last_spoken_text
    text = _sanitize_for_speech(text)
    _last_spoken_text = text
    try:
        print(f"[{config.ASSISTANT_TAG}] ({mood}) {_safe_console_text(text)}", flush=True)
    except OSError:
        pass
    
    print(f"[Voice] Requesting speak lock for: {text[:20]}...")
    with _speak_lock:
        print(f"[Voice] Speak lock acquired for: {text[:20]}...")
        IS_SPEAKING = True
        TEXT_BEING_SPOKEN = text
        
        # Pre-analyze text for visemes
        _analyze_text_for_visemes(text)
        
        try:
            provider = str(getattr(config, "TTS_PROVIDER", "edge_tts")).strip().lower()
            if bool(getattr(config, "LOCAL_SPEECH_ONLY", False)) or bool(getattr(config, "OPEN_SOURCE_MODE", False)):
                provider = "piper_local"
            # When SINGLE_TTS_ONLY is True we will strictly use only the configured provider
            # and will not try to fall back to other cloud/edge providers. If it fails, we
            # only fall back to the safe local pyttsx3 path to avoid multiple voices playing.
            strict_single_voice = bool(getattr(config, "SINGLE_TTS_ONLY", False))
            audio_path = None

            if provider in {"pyttsx3", "local_pyttsx3"}:
                sim_thread = threading.Thread(target=_simulate_text_lipsync, args=(text,), daemon=True)
                sim_thread.start()
                _speak_pyttsx3(text, mood)
                return

            # Try only the configured provider first
            if provider in {"piper_local", "piper"}:
                try:
                    audio_path = _generate_piper_audio(text)
                except Exception as e:
                    print(f"[Voice] Piper TTS failed: {e}")
                    audio_path = None

            elif provider in {"elevenlabs", "11labs"}:
                try:
                    audio_path = _generate_elevenlabs_audio(text, mood=mood)
                    if not audio_path:
                        print("[Voice] ElevenLabs is not configured or returned no audio.")
                except Exception as e:
                    print(f"[Voice] ElevenLabs failed: {e}")
                    audio_path = None

            elif provider in {"edge_tts", "edge"}:
                try:
                    audio_path = _generate_edge_tts_audio(text)
                except Exception as e:
                    print(f"[Voice] Edge TTS failed: {e}")
                    audio_path = None

            # If not strict mode, allow existing fallback behavior (edge/e11 -> edge)
            if not strict_single_voice and not audio_path and provider in {"elevenlabs", "11labs"}:
                # previous behavior: if elevenlabs requested and allowed fallback, try edge
                if bool(getattr(config, "TTS_ALLOW_CLOUD_FALLBACK", False)):
                    try:
                        audio_path = _generate_elevenlabs_audio(text, mood=mood)
                        if not audio_path:
                            audio_path = None
                    except Exception:
                        audio_path = None

            if not strict_single_voice and not audio_path and provider in {"edge_tts", "edge", "elevenlabs", "11labs"}:
                try:
                    audio_path = _generate_edge_tts_audio(text)
                except Exception:
                    audio_path = None

            # If we still don't have audio, only fall back to safe local pyttsx3
            if not audio_path:
                sim_thread = threading.Thread(target=_simulate_text_lipsync, args=(text,), daemon=True)
                sim_thread.start()
                _speak_pyttsx3(text, mood)
                return

            playback_ok = _play_audio_with_lipsync(audio_path)
            if not playback_ok:
                raise RuntimeError("Audio playback failed for configured backend.")
        except Exception as e:
            # Import core.logger inside to avoid circular dependency
            try:
                from core.logger import log_error
                log_error("Voice.speak", e, f"text='{text[:30]}...'")
            except ImportError:
                pass
            print(f"[Voice] TTS failed: {e}. Falling back to pyttsx3.")
            sim_thread = threading.Thread(target=_simulate_text_lipsync, args=(text,), daemon=True)
            sim_thread.start()
            _speak_pyttsx3(text, mood)
        finally:
            IS_SPEAKING = False
            TEXT_BEING_SPOKEN = ""
            global _last_speech_end
            _last_speech_end = time.time()
            print(f"[Voice] Speak lock released for: {text[:20]}...")


def _speak_pyttsx3(text, mood="neutral"):
    """Native pyttsx3 fallback using COM threading."""
    global IS_SPEAKING
    IS_SPEAKING = True
    try:
        import pyttsx3
        if os.name == 'nt' or sys.platform == 'win32':
            import pythoncom
            pythoncom.CoInitialize()
            
        rate = 180  # Faster speech rate
        volume = 1.0
        
        engine = pyttsx3.init()
        engine.setProperty('rate', rate)
        engine.setProperty('volume', volume)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"[Voice] pyttsx3 fallback failed: {e}")
    finally:
        IS_SPEAKING = False


def _wav_to_sr_audio(wav_buffer):
    """Helper to convert a WAV buffer to speech_recognition.AudioData."""
    import speech_recognition as sr
    wav_buffer.seek(0)
    with sr.AudioFile(wav_buffer) as source:
        recognizer = sr.Recognizer()
        audio = recognizer.record(source)
    return audio

def _record_with_silence_detection():
    """
    Records audio from the microphone using sounddevice with REAL-TIME
    silence detection. Stops recording as soon as the user stops speaking.
    """
    frames = []
    import numpy as np
    
    # State tracking object to fix mutability check
    state = {
        'speech_started': False,
        'silence_chunks': 0,
        'speech_chunks': 0,
        'total_chunks': 0
    }
    
    max_silence_chunks = int(SILENCE_DURATION * SAMPLE_RATE / CHUNK_SIZE)
    min_speech_chunks = int(MIN_SPEECH_SECONDS * SAMPLE_RATE / CHUNK_SIZE)
    max_total_chunks = int(MAX_RECORD_SECONDS * SAMPLE_RATE / CHUNK_SIZE)

    # Calibrate noise level (quick 0.3s sample)
    import sounddevice as sd
    calibration = sd.rec(int(0.1 * SAMPLE_RATE), samplerate=SAMPLE_RATE,
                         channels=CHANNELS, dtype=DTYPE)
    sd.wait()
    noise_level = np.abs(calibration).mean()
    threshold = max(int(noise_level * 1.5), 150)
    
    print("\rListening...", end="", flush=True)

    # Record in a streaming fashion using callback
    recording_done = threading.Event()
    
    def audio_callback(indata, frame_count, time_info, status):
        if status:
            pass
        
        chunk = indata.copy().flatten()
        amplitude = np.abs(chunk).mean()
        frames.append(chunk)
        state['total_chunks'] += 1
        
        if amplitude > threshold:
            state['speech_started'] = True
            print(".", end="", flush=True)
            state['speech_chunks'] += 1
            state['silence_chunks'] = 0
        elif state['speech_started']:
            state['silence_chunks'] += 1
        
        # Stop conditions
        has_enough_speech = state['speech_started'] and state['speech_chunks'] >= min_speech_chunks
        is_silent_after_speech = has_enough_speech and state['silence_chunks'] >= max_silence_chunks
        
        if is_silent_after_speech or state['total_chunks'] >= max_total_chunks:
            recording_done.set()
            raise sd.CallbackAbort()

    try:
        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=CHUNK_SIZE,
            callback=audio_callback
        )
        
        with stream:
            recording_done.wait(timeout=MAX_RECORD_SECONDS + 2)

    except sd.CallbackAbort:
        pass
    except (sd.PortAudioError, OSError):
        raise

    if not frames or not state['speech_started']:
        return None
    
    # Combine all frames into one numpy array
    audio_data = np.concatenate(frames)
    
    # Convert to WAV in memory
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(audio_data.tobytes())
    
    return _wav_to_sr_audio(wav_buffer)

# --- AUDIO INPUT CONFIG ---
SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = 'int16'
CHUNK_SIZE = 1024
SILENCE_THRESHOLD = 200
SILENCE_DURATION = 0.5
MIN_SPEECH_SECONDS = 0.1
MAX_RECORD_SECONDS = 10
_USE_TEXT_FALLBACK = False

# Import sr here to avoid conflicts
import speech_recognition as sr
import sounddevice as sd

# Track consecutive audio errors
_audio_error_count = 0
_MAX_AUDIO_ERRORS = 3


def _recognize_google_free(recognizer: sr.Recognizer, audio: sr.AudioData) -> str:
    configured = getattr(config, "STT_GOOGLE_LANGUAGE_CANDIDATES", None)
    if configured:
        languages = [str(lang).strip() for lang in configured if str(lang).strip()]
    else:
        english_only = bool(getattr(config, "FORCE_ENGLISH_ONLY", False)) or str(
            getattr(config, "ASSISTANT_PRIMARY_LANGUAGE", "")
        ).lower() in {"english", "en"}
        if english_only:
            languages = ["en-IN", "en-US"]
        else:
            languages = ["en-IN", "te-IN", "hi-IN", "en-US"]

    command = ""
    for lang in languages:
        try:
            if lang == "te-IN":
                print("Checking for Telugu...")
            elif lang == "hi-IN":
                print("Checking for Hindi...")
            raw_command = recognizer.recognize_google(audio, language=lang)
            if raw_command:
                command = str(raw_command)
                break
        except sr.UnknownValueError:
            continue
    return command


def _recognize_sphinx_local(recognizer: sr.Recognizer, audio: sr.AudioData) -> str:
    """
    Offline open-source STT using PocketSphinx via SpeechRecognition.
    """
    try:
        return str(recognizer.recognize_sphinx(audio)).strip()
    except sr.UnknownValueError:
        return ""


def _transcribe_vosk(audio: sr.AudioData) -> str:
    """
    Offline open-source STT using Vosk model.
    """
    try:
        import json as json_lib
        from vosk import KaldiRecognizer, Model
    except Exception as err:
        raise RuntimeError(f"Vosk import failed: {err}") from err

    model_paths = _resolve_vosk_model_paths()
    if not model_paths:
        raise RuntimeError("Vosk model not found. Run the local model bootstrap or set config.VOSK_MODEL_PATHS.")
    active_language = str(getattr(config, "STT_ACTIVE_LANGUAGE", "en")).strip().lower()
    if active_language and active_language != "auto":
        model_paths = model_paths[:1]

    wav_bytes = audio.get_wav_data(convert_rate=16000, convert_width=2)
    best_text = ""
    best_score = -1

    for model_path in model_paths:
        cache_key = os.path.abspath(model_path)
        model = _VOSK_MODEL_CACHE.get(cache_key)
        if model is None:
            model = Model(model_path)
            _VOSK_MODEL_CACHE[cache_key] = model

        recognizer = KaldiRecognizer(model, 16000)
        recognizer.AcceptWaveform(wav_bytes)
        result = recognizer.FinalResult() or "{}"
        payload = json_lib.loads(result)
        transcript = str(payload.get("text", "")).strip()
        if not transcript:
            continue

        score = len(transcript.split())
        model_name = os.path.basename(model_path).lower()
        if "hi" in model_name and _DEVANAGARI_RE.search(transcript):
            score += 100
        elif "te" in model_name and _TELUGU_RE.search(transcript):
            score += 100
        elif ("en" in model_name or "us" in model_name or "in" in model_name) and re.fullmatch(r"[a-z0-9 '\-]+", transcript.lower()):
            score += 20

        if score > best_score:
            best_score = score
            best_text = transcript

    return best_text


def _transcribe_openai_whisper(audio: sr.AudioData) -> str:
    api_key = os.getenv("OPENAI_API_KEY") or getattr(config, "OPENAI_API_KEY", None)
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    wav_bytes = audio.get_wav_data()
    model = str(getattr(config, "OPENAI_STT_MODEL", "whisper-1"))

    data = {
        "model": model,
        "temperature": "0",
    }
    language = str(getattr(config, "OPENAI_STT_LANGUAGE", "")).strip()
    prompt = str(getattr(config, "OPENAI_STT_PROMPT", "")).strip()
    if language:
        data["language"] = language
    if prompt:
        data["prompt"] = prompt

    files = {
        "file": ("speech.wav", wav_bytes, "audio/wav"),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    response = requests.post(
        "https://api.openai.com/v1/audio/transcriptions",
        headers=headers,
        data=data,
        files=files,
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(f"OpenAI STT failed: {response.status_code} {response.text[:180]}")

    payload = response.json() if response.content else {}
    return str(payload.get("text", "")).strip()


def _transcribe_deepgram(audio: sr.AudioData) -> str:
    api_key = os.getenv("DEEPGRAM_API_KEY") or getattr(config, "DEEPGRAM_API_KEY", None)
    if not api_key:
        raise RuntimeError("DEEPGRAM_API_KEY is not configured.")

    wav_bytes = audio.get_wav_data()
    model = str(getattr(config, "DEEPGRAM_MODEL", "nova-2")).strip() or "nova-2"
    language = str(getattr(config, "DEEPGRAM_LANGUAGE", "")).strip()

    params = {
        "model": model,
        "smart_format": "true",
        "punctuate": "true",
    }
    if not language:
        params["detect_language"] = "true"
    else:
        params["language"] = language

    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "audio/wav",
    }

    response = requests.post(
        "https://api.deepgram.com/v1/listen",
        params=params,
        data=wav_bytes,
        headers=headers,
        timeout=60,
    )
    if not response.ok:
        raise RuntimeError(f"Deepgram STT failed: {response.status_code} {response.text[:180]}")

    payload = response.json() if response.content else {}
    channels = payload.get("results", {}).get("channels", [])
    if not channels:
        return ""
    alternatives = channels[0].get("alternatives", [])
    if not alternatives:
        return ""
    return str(alternatives[0].get("transcript", "")).strip()


def _transcribe_with_provider(recognizer: sr.Recognizer, audio: sr.AudioData) -> str:
    provider = str(getattr(config, "STT_PROVIDER", "google_free")).strip().lower()
    if bool(getattr(config, "LOCAL_SPEECH_ONLY", False)) or bool(getattr(config, "OPEN_SOURCE_MODE", False)):
        provider = "vosk_local"
    cloud_fallback = _allow_cloud_fallback()

    if provider in {"sphinx_local", "sphinx", "pocketsphinx"}:
        try:
            print("Recognizing with PocketSphinx (local)...")
            transcript = _recognize_sphinx_local(recognizer, audio)
            if transcript:
                return transcript
            if not cloud_fallback:
                return ""
            print("[STT] PocketSphinx returned empty transcript; using cloud fallback.")
        except Exception as e:
            if not cloud_fallback:
                print(f"[STT] PocketSphinx failed: {e}. Cloud fallback disabled.")
                return ""
            print(f"[STT] PocketSphinx failed: {e}. Falling back to cloud STT.")

    if provider in {"vosk_local", "vosk"}:
        try:
            print("Recognizing with Vosk (local)...")
            transcript = _transcribe_vosk(audio)
            if transcript:
                return transcript
            if not cloud_fallback:
                return ""
            print("[STT] Vosk returned empty transcript; using cloud fallback.")
        except Exception as e:
            if not cloud_fallback:
                print(f"[STT] Vosk failed: {e}. Cloud fallback disabled.")
                return ""
            print(f"[STT] Vosk failed: {e}. Falling back to cloud STT.")

    if provider in {"openai_whisper", "openai", "whisper"}:
        if not cloud_fallback:
            print("[STT] Cloud fallback disabled; OpenAI Whisper provider skipped.")
            return ""
        try:
            print("Recognizing with OpenAI Whisper...")
            transcript = _transcribe_openai_whisper(audio)
            if transcript:
                return transcript
        except Exception as e:
            print(f"[STT] OpenAI Whisper failed: {e}. Falling back to Google.")

    elif provider in {"deepgram", "dg"}:
        if not cloud_fallback:
            print("[STT] Cloud fallback disabled; Deepgram provider skipped.")
            return ""
        try:
            print("Recognizing with Deepgram...")
            transcript = _transcribe_deepgram(audio)
            if transcript:
                return transcript
        except Exception as e:
            print(f"[STT] Deepgram failed: {e}. Falling back to Google.")

    # Default fallback path
    if provider in {"google_free", "google"} or cloud_fallback:
        try:
            return _recognize_google_free(recognizer, audio)
        except Exception as e:
            print(f"[STT] Google recognition failed: {e}. Trying local fallback.")
            try:
                return _recognize_sphinx_local(recognizer, audio)
            except Exception:
                return ""
    return ""


def listen():
    """
    Listens to the microphone with real-time silence detection.
    Stops recording as soon as you stop speaking (fast & responsive).
    Falls back to text input if audio device is unavailable.
    """
    global _USE_TEXT_FALLBACK, _audio_error_count
    
    # Text fallback mode
    if _USE_TEXT_FALLBACK:
        try:
            user_input = input("You (type): ").strip()
            return user_input
        except (EOFError, KeyboardInterrupt, OSError):
            time.sleep(2)
            return ""

    # Skip mic capture during and shortly after assistant speech (echo suppression).
    if _in_echo_guard_window():
        return ""
    
    recognizer = sr.Recognizer()
    
    try:
        audio = _record_with_silence_detection()
        
        if audio is None:
            return ""
            
        print("Recognizing...")
        command = _transcribe_with_provider(recognizer, audio)

        if not command:
            return None

        if is_likely_echo(command):
            print(f"[Voice] Ignored probable echo transcript: {command}")
            return ""
        
        # Reset error count on success
        _audio_error_count = 0
            
        print(f"You said: {command}")
        return command.strip()

    except sd.PortAudioError:
        print("[Warning] No microphone detected. Switching to text input mode.")
        _USE_TEXT_FALLBACK = True
        return ""
    except OSError as e:
        _audio_error_count = _audio_error_count + 1
        if _audio_error_count >= _MAX_AUDIO_ERRORS:
            print(f"[Warning] {_audio_error_count} consecutive audio errors (OSError: {e}). Switching to text input mode.")
            _USE_TEXT_FALLBACK = True
            return ""
        else:
            print(f"[Audio] OSError ({_audio_error_count}/{_MAX_AUDIO_ERRORS}): {e}. Retrying...")
            time.sleep(2)  # Wait longer before retry
            return ""
    except Exception as e:
        print(f"[Audio Error] {e}")
        _audio_error_count = _audio_error_count + 1
        is_audio_error = "device" in str(e).lower() or "portaudio" in str(e).lower()

        if is_audio_error or _audio_error_count >= _MAX_AUDIO_ERRORS:
            print("[Warning] Audio device error. Switching to text input mode.")
            _USE_TEXT_FALLBACK = True
            return ""
        return ""


# --- LIP-SYNC HELPER FUNCTIONS ---

def get_lip_sync_state():
    """Get current lip-sync state for visual animation."""
    return {
        'is_speaking': IS_SPEAKING,
        'amplitude': CURRENT_AMPLITUDE,
        'current_viseme': CURRENT_VISEME,
        'target_viseme': TARGET_VISEME,
        'transition_progress': VISEME_TRANSITION_PROGRESS,
        'text': TEXT_BEING_SPOKEN
    }


def set_lip_sync_enabled(enabled: bool):
    """Enable or disable lip-sync features."""
    global LIP_SYNC_ENABLED
    LIP_SYNC_ENABLED = enabled

