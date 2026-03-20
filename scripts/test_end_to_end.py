"""Simple end-to-end test script for BKR backend.
Usage (after starting backend):
    python scripts/test_end_to_end.py
It will perform a chat request, request TTS for the response, and attempt a voice upload if test audio exists.
"""
import requests
import os

BASE = 'http://localhost:8000'


def test_chat():
    print('Testing chat...')
    resp = requests.post(f'{BASE}/api/chat', files={'text': (None, 'Hello BKR, give me a 3 step plan to learn binary search')}, data={'user_id': 'tester'})
    print('Status:', resp.status_code)
    try:
        j = resp.json()
        print('Response:', j.get('response'))
        return j
    except Exception as e:
        print('Failed to parse JSON:', e)
        print(resp.text)
        return None


def test_tts(text):
    print('Testing TTS...')
    resp = requests.post(f'{BASE}/api/tts', files={'text': (None, text)})
    print('Status:', resp.status_code)
    if resp.status_code == 200:
        out = 'out_tts.mp3'
        with open(out, 'wb') as f:
            f.write(resp.content)
        print('Saved TTS to', out)
    else:
        print('TTS failed:', resp.text)


def test_voice_upload():
    print('Testing voice upload...')
    sample = os.path.join(os.path.dirname(__file__), '..', 'test_audio.wav')
    if not os.path.exists(sample):
        print('No test audio found at', sample)
        return
    resp = requests.post(f'{BASE}/api/voice', files={'file': open(sample, 'rb')}, data={'user_id': 'tester'})
    print('Status:', resp.status_code)
    try:
        print('Result:', resp.json())
    except Exception as e:
        print('Non-JSON resp')


if __name__ == '__main__':
    j = test_chat()
    if j and 'response' in j:
        test_tts(j['response'])
    test_voice_upload()
