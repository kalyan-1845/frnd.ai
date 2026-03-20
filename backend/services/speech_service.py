"""Speech service wrapper: provides transcribe and synthesize functions.

This file will attempt to use advanced.voice if present, otherwise fall back to edge-tts and a simple whisper wrapper.
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

        # Fallback edge-tts
        if edge_tts:
            out_path = os.path.join(self.tts_dir, f"tts_{abs(hash(text)) % (10**8)}.mp3")
            # Simple default voice
            voice = "en-US-JennyNeural"
            communicate = edge_tts.Communicate(text, voice)
            try:
                # Use async writer via subprocess
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
