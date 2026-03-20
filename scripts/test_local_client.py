"""Local Test Client — calls FastAPI app endpoints via TestClient (no server process required).
Run: python scripts/test_local_client.py
"""
from fastapi.testclient import TestClient
import importlib.util
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
spec = importlib.util.spec_from_file_location('backend_app', r'backend/app.py')
backend_app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend_app)

client = TestClient(backend_app.app)

print('Running local TestClient against backend.app...')

# Test health
resp = client.get('/health')
print('/health', resp.status_code, resp.json())

# Test chat
resp = client.post('/api/chat', data={'text': 'Hello BKR, how are you?', 'user_id': 'tester'})
print('/api/chat', resp.status_code)
try:
    print(resp.json())
except Exception as e:
    print('chat response not JSON', e, resp.text)

# Try a tutor request
resp2 = client.post('/api/chat', data={'text': 'Explain binary search in 3 steps', 'user_id': 'tester'})
print('/api/chat tutor', resp2.status_code)
try:
    j = resp2.json()
    print('Tutor response:', j.get('response'))
    # If we have a text response, try TTS
    if j.get('response'):
        tts = client.post('/api/tts', data={'text': j['response']})
        print('/api/tts', tts.status_code)
except Exception as e:
    print('Tutor call failed', e, resp2.text)

print('Local tests complete.')
