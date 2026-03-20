from playsound import playsound
import os

def test_playback():
    print("Testing playsound...")
    if os.path.exists("test_tts.mp3"):
        try:
            playsound("test_tts.mp3", block=True)
            print("Success! Played test_tts.mp3")
        except Exception as e:
            print(f"Error: {e}")
    else:
        print("test_tts.mp3 not found. Run test_edge_tts.py first.")

if __name__ == "__main__":
    test_playback()
