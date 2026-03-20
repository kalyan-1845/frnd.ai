import asyncio
import edge_tts
import os

async def test_speak():
    print("Testing Edge-TTS...")
    text = "Hello, this is a test of the emergency broadcast system."
    voice = "en-US-AriaNeural"
    communicate = edge_tts.Communicate(text, voice)
    try:
        await communicate.save("test_tts.mp3")
        print("Success! test_tts.mp3 created.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_speak())
