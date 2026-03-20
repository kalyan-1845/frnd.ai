
import os
import sys
import time

# Add project root to path
sys.path.append(os.getcwd())

import config
from advanced.voice import speak

def test_speak():
    text = "Testing the speak function. Can you hear me?"
    print(f"Calling speak('{text}')")
    try:
        speak(text)
        print("speak() call finished.")
    except Exception as e:
        print(f"Error in speak(): {e}")

if __name__ == "__main__":
    test_speak()
