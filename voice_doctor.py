
import os
import sys
import time
import asyncio
import tempfile
import subprocess

# Add project root to path
sys.path.append(os.getcwd())

import config
from advanced.voice import speak, _play_audio_with_lipsync, _generate_edge_tts_audio

async def diagnostic():
    print("--- BKR Voice System Diagnostics ---")
    
    # 1. Check Internet
    print("\n[1/5] Checking Internet...")
    import socket
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        print("OK: Internet connected.")
    except Exception as e:
        print(f"FAIL: Internet may be down: {e}")

    # 2. Test Edge-TTS Generation
    print("\n[2/5] Testing Edge-TTS Generation...")
    try:
        test_text = "Checking text to speech generation."
        audio_path = _generate_edge_tts_audio(test_text)
        if audio_path and os.path.exists(audio_path):
            print(f"OK: Audio generated at {audio_path}")
            size = os.path.getsize(audio_path)
            print(f"    File size: {size} bytes")
        else:
            print("FAIL: Audio generation failed.")
    except Exception as e:
        print(f"FAIL: Edge-TTS error: {e}")

    # 3. Test Playback Backend
    print("\n[3/5] Testing Playback Backend (playsound/pygame)...")
    try:
        from playsound import playsound
        import importlib.util
        pygame_available = importlib.util.find_spec("pygame") is not None
        print(f"    Pygame available: {pygame_available}")
        
        # Use the file we just generated
        if audio_path and os.path.exists(audio_path):
            print("    Attempting playback...")
            success = _play_audio_with_lipsync(audio_path)
            if success:
                print("OK: Playback reported success.")
            else:
                print("FAIL: Playback reported failure.")
    except Exception as e:
        print(f"FAIL: Playback error: {e}")

    # 4. Test pyttsx3 Fallback
    print("\n[4/5] Testing pyttsx3 Fallback...")
    try:
        from advanced.voice import _speak_pyttsx3
        print("    Attempting pyttsx3...")
        _speak_pyttsx3("Testing local fallback.")
        print("OK: pyttsx3 triggered.")
    except Exception as e:
        print(f"FAIL: pyttsx3 error: {e}")

    # 5. Check System Volume
    print("\n[5/5] Checking System Volume (via PowerShell)...")
    try:
        res = subprocess.run(["powershell", "-Command", "Get-AudioDevice -Playback"], capture_output=True, text=True)
        # Even if Get-AudioDevice fails, we try to get SOMETHING
        print("    Audio Devices Found:")
        print(res.stdout or "None found via Get-AudioDevice")
    except Exception as e:
        print(f"INFO: Volume check failed (expected on some systems): {e}")

    print("\n--- Diagnostics Finished ---")

if __name__ == "__main__":
    asyncio.run(diagnostic())
