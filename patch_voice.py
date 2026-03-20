import sys

with open("advanced/voice.py", "r", encoding="utf-8") as f:
    text = f.read()

target1 = '''print(f"[{config.ASSISTANT_TAG}] ({mood}) {_safe_console_text(text)}", flush=True)'''
repl1 = '''try:
        print(f"[{config.ASSISTANT_TAG}] ({mood}) {_safe_console_text(text)}", flush=True)
    except OSError:
        pass'''

target2 = '''    proc = subprocess.run([sys.executable, "-c", speak_script], capture_output=True, text=True)
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0 or "FAIL:" in out:
        print(f"[Voice] pyttsx3 fallback failed: rc={proc.returncode} out={out} err={err}")
    IS_SPEAKING = False'''
repl2 = '''    try:
        proc = subprocess.run([sys.executable, "-c", speak_script], capture_output=True, text=True)
        out = (proc.stdout or "").strip()
        err = (proc.stderr or "").strip()
        if proc.returncode != 0 or "FAIL:" in out:
            pass # ignore
            # print(f"[Voice] pyttsx3 fallback failed: rc={proc.returncode} out={out} err={err}")
    except OSError:
        pass
    IS_SPEAKING = False'''

if target1 in text and target2 in text:
    text = text.replace(target1, repl1).replace(target2, repl2)
    with open("advanced/voice.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("advanced/voice.py patched!")
else:
    print("Could not find targets in advanced/voice.py")

with open("main.py", "r", encoding="utf-8") as f:
    text = f.read()

target3 = '''try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass'''

repl3 = '''class SafeStream:
    def __init__(self, stream):
        self.stream = stream
    def write(self, data):
        try:
            if self.stream: self.stream.write(data)
        except OSError: pass
    def flush(self):
        try:
            if self.stream: self.stream.flush()
        except OSError: pass
    def isatty(self):
        return getattr(self.stream, 'isatty', lambda: False)()

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.stdout = SafeStream(sys.stdout)
sys.stderr = SafeStream(sys.stderr)'''

if target3 in text:
    text = text.replace(target3, repl3)
    with open("main.py", "w", encoding="utf-8") as f:
        f.write(text)
    print("main.py patched!")
else:
    print("Could not find targets in main.py")
