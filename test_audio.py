
import os
import sys
import time
import importlib.util

# Add project root to path
sys.path.append(os.getcwd())

import config
from advanced.voice import _generate_edge_tts_audio, _play_audio_with_lipsync

def test_audio():
    text = "Hello, this is a test of the audio system."
    print(f"Testing TTS for: '{text}'")
    
    try:
        audio_path = _generate_edge_tts_audio(text)
        print(f"Generated audio at: {audio_path}")
        
        # Set global state expected by _play_audio_with_lipsync
        import advanced.voice
        advanced.voice.IS_SPEAKING = True
        print("Set IS_SPEAKING = True")
        
        print("Attempting playback...")
        playback_ok = _play_audio_with_lipsync(audio_path)
        print(f"Playback status: {playback_ok}")
        
    except Exception as e:
        print(f"Error during audio test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_audio()
