"""
BKR 2.0 — Main Entry Point
Thin orchestrator: initializes systems, wires the BrainController, and runs I/O loops.
"""
import json
import config
from advanced.voice import speak as _raw_speak, listen
from advanced.avatar_generator import ensure_avatar_frames
from automation.file_manager import (
    open_folder, find_file, create_file, create_folder, write_to_file,
    move_file, copy_file, delete_item, rename_item, list_files,
    zip_item, unzip_item
)
from system_control.system_settings import (
    toggle_wifi, open_bluetooth, open_phone_link, system_sleep,
    lock_screen, set_brightness, toggle_night_light, toggle_airplane_mode,
    display_off, empty_recycle_bin, set_wallpaper, system_shutdown,
    system_restart, cancel_shutdown, open_settings
)
from system_control.system_monitor import (
    get_system_status, get_battery_status, get_cpu_usage,
    get_ram_usage, get_disk_usage, get_network_info, get_uptime
)
from system_control.process_manager import (
    list_running_apps, kill_process, get_active_window, count_running_processes
)
from automation.browser import search_google, search_youtube, open_url, search_weather, search_news
from system_control.app_launcher import launch_application
from system_control.mouse_keyboard import (
    type_text, press_key, take_screenshot, volume_control
)
from automation.executor import run_command, run_script
from automation.web_scraper import (
    scrape_url, get_wikipedia_summary, get_definition, get_joke, get_quote
)
from automation.messaging import (
    send_whatsapp_message, open_whatsapp, open_gmail, compose_email, open_telegram
)
from automation.text_tools import (
    summarize_text, correct_grammar, count_words, convert_case,
    calculate, generate_password, reminder_note, read_notes, translate_text
)
import webbrowser
import sys
import subprocess
import os
import psutil
import shutil
from automation.workspace import organize_folder, clean_temp_files
from automation.startup_manager import ensure_windows_startup, disable_windows_startup
from advanced.memory import MemorySystem
from core.personality import PersonalityEngine
from core.brain import BrainController
from core.input_processor import process_user_input, is_teaching_request, get_response_guidance
from core.safety_system import analyze_command_safety, enforce_safe_mode, get_safety_status
import core.teaching_engine as teaching_module
from core.teaching_engine import analyze_learning_request, create_lesson_plan, deliver_lesson
import core.logger as logger
from core.logger import log_event, log_error
import time
import random
import threading
import queue
from datetime import datetime

class SafeStream:
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
sys.stderr = SafeStream(sys.stderr)

def _safe_console_text(text: str) -> str:
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        return str(text).encode(encoding, errors="replace").decode(encoding, errors="replace")
    except Exception:
        return str(text).encode("ascii", errors="replace").decode("ascii", errors="replace")

# Global Command Queue
command_queue = queue.Queue()

# Thread-safe pause flag
_pause_lock = threading.Lock()
_pause_listener = False

def ensure_singleton():
    """Ensure only one instance of the assistant is running."""
    lock_file = os.path.join(os.path.expanduser("~"), ".bkr_assistant.lock")
    try:
        if os.path.exists(lock_file):
            try:
                with open(lock_file, "r") as f:
                    pid = int(f.read().strip())
                if psutil.pid_exists(pid):
                    proc = psutil.Process(pid)
                    if "python" in proc.name().lower():
                        print(f"\n[System] Another instance is already running (PID {pid}).")
                        print("[System] Please close the other instance before starting a new one.\n")
                        os._exit(1)
            except Exception:
                pass
        
        with open(lock_file, "w") as f:
            f.write(str(os.getpid()))
        
        # Clean up on exit
        import atexit
        def cleanup():
            try:
                if os.path.exists(lock_file):
                    os.remove(lock_file)
            except Exception:
                pass
        atexit.register(cleanup)
    except Exception as e:
        log_error("SingletonCheck", e)

def set_pause_listener(value: bool):
    global _pause_listener
    with _pause_lock:
        _pause_listener = value

def get_pause_listener() -> bool:
    with _pause_lock:
        return _pause_listener

def speak(text: str, mood: str = "neutral"):
    """
    Wrap raw TTS so the mic/listener is paused while speaking.
    This prevents echo transcripts and "double agent" behavior.
    """
    if not text: return
    prev_paused = get_pause_listener()
    try:
        set_pause_listener(True)
        return _raw_speak(text, mood)
    finally:
        if not prev_paused:
            time.sleep(float(getattr(config, "VOICE_ECHO_GUARD_SECONDS", 0.4)))
        set_pause_listener(prev_paused)

# Assistant State Management
IS_FOCUS_MODE = False
PLANNING_MODE = False
PLANNING_STEP = 0
USER_GOALS = []
LAST_INTERACTION_TIME = time.time()
CALL_MODE = False
CALL_MODE_TIMEOUT = 30  # Seconds of silence before exiting call mode
last_call_interaction = 0

# --- Time-aware greetings ---

def get_time_based_greeting():
    """Generate a time-appropriate greeting for BKR 2.0."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        greetings = [
            f"Good morning. {config.ASSISTANT_NAME} is online.",
            "Good morning. I am ready for your first task.",
            "Good morning. Daily protocols are initialized.",
        ]
    elif 12 <= hour < 17:
        greetings = [
            "Good afternoon. How can I assist you?",
            "Good afternoon. Systems are running optimally.",
            "Good afternoon. Network is stable and I am on standby.",
        ]
    elif 17 <= hour < 21:
        greetings = [
            "Good evening. All systems are running smoothly.",
            "Good evening. Today's tasks are cataloged.",
            "Good evening. I am ready for your requests.",
        ]
    else:
        greetings = [
            "It is late. Consider taking a short rest.",
            "Night mode active. I am still available if needed.",
            "Operating in night mode and ready for your command.",
        ]
    return random.choice(greetings)

def get_wellbeing_reminder():
    """Return occasional wellbeing reminders — professional tone."""
    if not bool(getattr(config, "WELLBEING_REMINDERS_ENABLED", False)):
        return ""
    reminders = [
        "\n\nQuick reminder: hydrate for better cognitive performance.",
        "\n\nA brief stretch can help after long sitting.",
        "\n\nA short break now can preserve your focus.",
        "\n\nA quick walk might improve clarity.",
    ]
    probability = float(getattr(config, "WELLBEING_REMINDER_PROBABILITY", 0.08))
    if random.random() < max(0.0, min(1.0, probability)):
        return random.choice(reminders)
    return ""

def get_task_followup():
    """Optional short follow-up prompt after successful task actions."""
    if not bool(getattr(config, "VOICE_TASK_FOLLOWUP_ENABLED", False)):
        return ""
    prompts = [
        "Done. Need anything else?",
        "Completed. What next?",
        "Task finished. Next command?",
    ]
    return random.choice(prompts)

# --- Background Threads ---

def proactive_agent_thread():
    """Background thread for proactive intelligence and system health monitoring."""
    global LAST_INTERACTION_TIME, CALL_MODE
    last_health_check = 0
    HEALTH_CHECK_INTERVAL = 1800  # 30 minutes
    log_event("Proactive Intelligence Thread started")
    while True:
        try:
            current_time = time.time()
            if current_time - last_health_check > HEALTH_CHECK_INTERVAL:
                try:
                    cpu_usage = psutil.cpu_percent(interval=1)
                    try:
                        system_drive = os.path.splitdrive(os.environ.get("SystemRoot", "C:\\Windows"))[0] + "\\"
                    except Exception:
                        system_drive = "C:\\"
                    disk = psutil.disk_usage(system_drive)
                    disk_percent = disk.percent
                    if cpu_usage > 90:
                        msg = "System is under heavy load. Minimizing background tasks."
                        print(f"[{config.ASSISTANT_TAG}] {msg}")
                    elif disk_percent > 95:
                        msg = "Primary disk is nearly full. Review storage."
                        print(f"[{config.ASSISTANT_TAG}] {msg}")
                except Exception as e:
                    log_error("HealthCheck", e)
                last_health_check = current_time
            if getattr(config, "WELLBEING_REMINDERS_ENABLED", False) and not get_pause_listener() and not CALL_MODE:
                elapsed_silence = current_time - LAST_INTERACTION_TIME
                if 7200 <= elapsed_silence < 7230:
                    msg = "It has been quite a while. Would you like a brief break?"
                    print(f"[{config.ASSISTANT_TAG}] {msg}")
                    speak(msg, "happy")
                    LAST_INTERACTION_TIME = time.time() - 7230
            time.sleep(30)
        except Exception as e:
            log_error("ProactiveAgent", e)
            time.sleep(10)

def goal_check_in_thread(memory):
    """Background thread to occasionally check on user goals."""
    log_event("Goal Check-in Thread started")
    while True:
        try:
            if not getattr(config, "GOAL_CHECKIN_ENABLED", False):
                time.sleep(3600)
                continue
            if not get_pause_listener():
                time.sleep(14400) 
                goals = memory.get_goals()
                if goals:
                    goal = random.choice(goals)
                    msg = f"Regarding your objective '{goal}', do you have any updates where I can assist?"
                    print(f"[{config.ASSISTANT_TAG}] {msg}")
                    speak(msg)
        except Exception as e:
            log_error("GoalCheckIn", e)
            time.sleep(60)

def focus_timer_thread(minutes):
    """Background timer for focus mode."""
    global IS_FOCUS_MODE, LAST_INTERACTION_TIME
    start_time = time.time()
    end_time = start_time + (minutes * 60)
    check_in_interval = 10 * 60
    next_check_in = start_time + check_in_interval
    while time.time() < end_time:
        if not IS_FOCUS_MODE:
            return
        distracting_apps = ["chrome.exe", "msedge.exe", "steam.exe", "discord.exe", "vlc.exe", "netflix.exe"]
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info['name'].lower() in distracting_apps:
                    msg = f"Focus Shield: I see '{proc.info['name']}' is active. Don't forget your goals!"
                    print(f"[{config.ASSISTANT_TAG}] {msg}")
                    break
        except Exception:
            pass
        if time.time() >= next_check_in and (end_time - time.time()) > 300:
            msg = "Keep it up. You are making excellent progress."
            print(f"[{config.ASSISTANT_TAG}] {msg}")
            speak(msg)
            next_check_in += check_in_interval
        time.sleep(30)
    IS_FOCUS_MODE = False
    msg = f"Time is up. Your {minutes} minute focus session is complete."
    print(f"[{config.ASSISTANT_TAG}] {msg}")
    speak(msg, "happy")
    LAST_INTERACTION_TIME = time.time()

def handle_cli_command(user_input, brain):
    """Handle /slash commands. Returns True if handled, False otherwise."""
    global PLANNING_MODE, PLANNING_STEP, USER_GOALS, IS_FOCUS_MODE
    if not user_input.startswith("/"):
        return False
    command = user_input.split()[0].lower()
    args = " ".join(user_input.split()[1:])
    if command == "/plan":
        PLANNING_MODE = True
        PLANNING_STEP = 1
        USER_GOALS = []
        response = "Let's plan your day. What is your first major objective?"
        print(f"[{config.ASSISTANT_TAG}] {response}")
        speak(response)
        return True
    elif command == "/focus":
        minutes = 25
        if args.isdigit():
            minutes = int(args)
        IS_FOCUS_MODE = True
        response = f"Focus mode initiated for {minutes} minutes. Minimal distractions will be filtered."
        print(f"[{config.ASSISTANT_TAG}] {response}")
        speak(response)
        timer_t = threading.Thread(target=focus_timer_thread, args=(minutes,), daemon=True)
        timer_t.start()
        return True
    elif command == "/motivate":
        response = brain.personality.get_response("motivated")
        print(f"[{config.ASSISTANT_TAG}] {response}")
        speak(response)
        return True
    elif command == "/analyze":
        goals = brain.memory.get_goals()
        if not goals:
            response = "You have not set any long-term goals yet. Use '/addgoal <goal>' to begin."
        else:
            response = f"Current Goals: {', '.join(goals)}. Standing by to assist with these."
        print(f"[{config.ASSISTANT_TAG}] {response}")
        speak(response)
        return True
    elif command == "/addgoal":
        if args:
            brain.memory.add_goal(args)
            response = f"Goal recorded: {args}"
        else:
            response = "Please specify a goal for me to track."
        print(f"[{config.ASSISTANT_TAG}] {response}")
        speak(response)
        return True
    elif command == "/verify":
        try:
            from core.vision import verify_user
            success, msg = verify_user()
        except Exception as e:
            msg = f"Vision module unavailable: {e}"
        print(f"[{config.ASSISTANT_TAG}] {msg}")
        speak(msg)
        return True
    elif command == "/register":
        try:
            from core.vision import capture_user_face
            success, msg = capture_user_face()
        except Exception as e:
            msg = f"Vision module unavailable: {e}"
        print(f"[{config.ASSISTANT_TAG}] {msg}")
        speak(msg)
        return True
    elif command == "/resetmemory":
        brain.memory.reset_all_memory()
        response = "Memory reset complete. All stored data has been expunged."
        print(f"[{config.ASSISTANT_TAG}] {response}")
        speak(response)
        return True
    elif command == "/forget":
        if args:
            brain.memory.forget(args)
            response = f"Understood. I have cleared the '{args}' memory bank."
        else:
            response = "Please specify what to forget."
        print(f"[{config.ASSISTANT_TAG}] {response}")
        speak(response)
        return True
    elif command == "/memory":
        summary = brain.memory.get_memory_summary()
        print(f"[{config.ASSISTANT_TAG}] {summary}")
        speak("Here is your memory summary.")
        return True
    elif command == "/coachstart":
        result = brain.execute("start english coach", source="text")
        if result.get("response"):
            print(f"[{config.ASSISTANT_TAG}] {result['response']}")
        return True
    elif command == "/coachnext":
        result = brain.execute("next lesson", source="text")
        if result.get("response"):
            print(f"[{config.ASSISTANT_TAG}] {result['response']}")
        return True
    elif command == "/coachstatus":
        result = brain.execute("coach status", source="text")
        if result.get("response"):
            print(f"[{config.ASSISTANT_TAG}] {result['response']}")
        return True
    elif command == "/learn":
        if not args:
            print(f"[{config.ASSISTANT_TAG}] Usage: /learn <topic>")
            return True
        result = brain.execute(f"teach me {args}", source="text")
        if result.get("response"):
            print(f"[{config.ASSISTANT_TAG}] {result['response']}")
        return True
    elif command == "/nextstep":
        result = brain.execute("next step", source="text")
        if result.get("response"):
            print(f"[{config.ASSISTANT_TAG}] {result['response']}")
        return True
    elif command == "/quiz":
        result = brain.execute("quiz me", source="text")
        if result.get("response"):
            print(f"[{config.ASSISTANT_TAG}] {result['response']}")
        return True
    elif command == "/lessonstatus":
        result = brain.execute("lesson status", source="text")
        if result.get("response"):
            print(f"[{config.ASSISTANT_TAG}] {result['response']}")
        return True
    elif command == "/stoplesson":
        result = brain.execute("stop lesson", source="text")
        if result.get("response"):
            print(f"[{config.ASSISTANT_TAG}] {result['response']}")
        return True
    elif command == "/speechlang":
        value = (args or "").strip().lower()
        allowed = {"auto", "en", "en-in"}
        if value not in allowed:
            print(f"[{config.ASSISTANT_TAG}] Usage: /speechlang auto|en|en-in")
            return True
        config.STT_ACTIVE_LANGUAGE = value
        response = f"Local speech recognition language set to {value}."
        print(f"[{config.ASSISTANT_TAG}] {response}")
        speak(response)
        return True
    return False

def _tool_stop(target):
    return True, "__EXIT__"
def _tool_open_folder(target):
    return open_folder(target)
def _tool_find_file(target):
    return find_file(target)
def _tool_create_file(target):
    parts = target.split("|", 1)
    filename = parts[0]
    content = parts[1] if len(parts) > 1 else ""
    success, msg = create_file(filename, content)
    if success:
        try:
            import os
            from automation.file_manager import DESKTOP_PATH
            os.startfile(os.path.join(DESKTOP_PATH, filename))
        except Exception:
            pass
    return success, msg
def _tool_write_to_file(target):
    if not target: return False, "I need a filename and content to write."
    parts = target.split("|", 1)
    if len(parts) < 2: return False, "I need both a filename and content to write."
    filename, content = parts[0], parts[1]
    return write_to_file(filename, content)
def _tool_move_file(target):
    if not target: return False, "Please provide source file and destination folder."
    parts = target.split("|", 1)
    if len(parts) < 2: return False, "I need both a source file and a destination folder."
    return move_file(parts[0], parts[1])
def _tool_copy_file(target):
    if not target: return False, "Please provide source file and destination folder."
    parts = target.split("|", 1)
    if len(parts) < 2: return False, "I need both a source file and a destination folder."
    return copy_file(parts[0], parts[1])
def _tool_delete_item(target):
    return delete_item(target)
def _tool_rename_item(target):
    if not target or "|" not in target: return False, "Please provide the current path and the new name separated by '|'."
    parts = target.split("|", 1)
    return rename_item(parts[0], parts[1])
def _tool_list_files(target):
    return list_files(target)
def _tool_zip_item(target):
    return zip_item(target)
def _tool_unzip_item(target):
    return unzip_item(target)
def _tool_search_google(target):
    return search_google(target)
def _tool_search_youtube(target):
    return search_youtube(target)
def _tool_open_url(target):
    return open_url(target)
def _tool_weather(target):
    return search_weather(target)
def _tool_news(target):
    return search_news(target)
def _tool_wifi_control(target):
    enable = "enable" in target or "on" in target
    return toggle_wifi(enable)
def _tool_bluetooth_control(target):
    return open_bluetooth()
def _tool_phone_link(target):
    return open_phone_link()
def _tool_launch_app(target):
    return launch_application(target)
def _tool_type_text(target):
    time.sleep(0.5)
    success = type_text(target)
    return success, "Typed text." if success else "Typing failed."
def _tool_press_key(target):
    success = press_key(target)
    return success, f"Pressed {target}." if success else "Key press failed."
def _tool_send_sms(target):
    return open_phone_link()
def _tool_call_contact(target):
    return open_phone_link()
def _tool_start_video_call(target):
    return open_whatsapp()
def _tool_read_notifications(target):
    return open_settings("notifications")
def _tool_clear_notifications(target):
    return open_settings("notifications")
def _tool_screenshot(target):
    filepath = take_screenshot()
    return bool(filepath), "Screenshot saved." if filepath else "Screenshot failed."
def _tool_volume_control(target):
    volume_control(target)
    return True, f"Volume {target}."
def _tool_translate_text(target):
    parts = target.split("|", 1)
    if len(parts) < 2: return False, "Please use the format: 'to [language]|text to translate'."
    lang, text = parts[0].strip(), parts[1].strip()
    prompt = f"Translate the following text to {lang}. Return ONLY the translated text, nothing else: \"{text}\""
    from core.llm_api import generate_response
    translated = generate_response(prompt, "System", "Neural Translator", "")
    return True, translated
def _tool_tell_time(target):
    now = datetime.now().strftime("%I:%M %p")
    return True, f"It is {now}."
def _tool_tell_date(target):
    today = datetime.now().strftime("%A, %B %d, %Y")
    return True, f"Today is {today}."

def voice_listener_thread():
    WAKE_WORDS = ["leo", "hey leo", "hello leo", "hi leo", "ok leo", "bkr", "hey bkr", "hello bkr", "hi bkr", "ok bkr", "jarvis", "hey jarvis", "hello jarvis", "hi jarvis", "ok jarvis", "buddy", "hey buddy", "ok buddy", "hi buddy", "hello buddy", "bujji", "hey bujji", "ok bujji", "hi bujji", "hello bujji", "ai", "hey ai", "computer", "hey computer"]
    CALL_TRIGGERS = ["call bkr", "hey bkr call", "bkr talk", "call jarvis", "let's talk", "start call", "talk to me", "hey jarvis call", "jarvis talk", "call mode start"]
    import advanced.voice
    WAKE_WORDS.sort(key=len, reverse=True)
    log_event("Voice Listener started")
    last_active_time = 0
    FOLLOW_UP_WINDOW = 15
    last_heard_norm, last_heard_time = "", 0.0
    dedup_window = float(getattr(config, "VOICE_DEDUP_WINDOW_SECONDS", 2.0))
    while True:
        try:
            while get_pause_listener(): time.sleep(0.1)
            text = listen()
            if text and advanced.voice.is_likely_echo(text): continue
            if advanced.voice.IS_SPEAKING: continue
            if text:
                text_lower = text.lower()
                text_norm = " ".join(text_lower.split())
                now_ts = time.time()
                if text_norm and text_norm == last_heard_norm and (now_ts - last_heard_time) < dedup_window: continue
                is_wake = False
                command_text = text
                global CALL_MODE, last_call_interaction
                if any(t in text_lower for t in CALL_TRIGGERS):
                    CALL_MODE = True
                    last_call_interaction = time.time()
                    msg = "Call mode initiated. I am listening continuously now."
                    print(f"[{config.ASSISTANT_TAG}] {msg}")
                    speak(msg, "happy")
                    continue
                if CALL_MODE and any(w in text_lower for w in ["stop call", "end call", "goodbye", "bye"]):
                    CALL_MODE = False
                    msg = "Ending call mode."
                    print(f"[{config.ASSISTANT_TAG}] {msg}")
                    speak(msg, "calm")
                    continue
                if not CALL_MODE and not config.VOICE_REQUIRE_WAKE_WORD: is_wake = True
                elif not CALL_MODE:
                    for w in WAKE_WORDS:
                        if text_lower.startswith(w):
                            is_wake = True
                            command_text = text[len(w):].strip().lstrip(" ,.!:")
                            break
                if CALL_MODE: is_wake = True; last_call_interaction = time.time()
                if not CALL_MODE and not is_wake and not getattr(config, "VOICE_REQUIRE_WAKE_WORD", False):
                    strong_intents = ["play", "open", "launch", "search", "stop", "exit", "close", "turn", "create", "make", "what", "tell", "show", "calculate", "find", "run", "type", "press", "take", "volume", "lock", "set", "send", "compose", "write", "save", "read", "list", "kill", "terminate", "restart", "shutdown", "sleep", "mute", "unmute", "empty", "scrape", "check", "how", "who", "explain", "generate", "note"]
                    if text_lower.split()[0] in strong_intents or any(k in text_lower for k in ["time", "date", "news", "weather", "joke", "quote", "battery", "cpu", "ram", "disk", "network", "uptime", "whatsapp", "gmail", "telegram", "email", "password", "screenshot", "brightness", "wallpaper", "wikipedia", "definition", "meaning", "system status", "recycle bin", "night light", "airplane"]):
                        is_wake = True; command_text = text
                if not CALL_MODE and text_lower in ["stop", "exit", "quit", "shutdown", "wait"]: is_wake = True; command_text = text
                if not CALL_MODE and not is_wake and (time.time() - last_active_time < FOLLOW_UP_WINDOW): is_wake = True; command_text = text
                if is_wake:
                    last_active_time = time.time()
                    last_heard_norm, last_heard_time = text_norm, now_ts
                    command_queue.put(command_text)
            else:
                if CALL_MODE and time.time() - last_call_interaction > CALL_MODE_TIMEOUT:
                    CALL_MODE = False
                    msg = "Call mode timed out."
                    speak(msg, "calm")
                time.sleep(0.1)
        except Exception as e:
            log_error("VoiceListener", e)
            time.sleep(1)

def check_ollama():
    import requests
    try:
        response = requests.get('http://localhost:11434', timeout=2)
        if response.status_code == 200: return True
    except Exception: pass
    print("[WARNING] Ollama is NOT running.")
    return False

def check_internet():
    import socket
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError: return False

def start_assistant():
    ensure_singleton()
    memory = MemorySystem()
    try: teaching_module.teaching_engine.memory = memory
    except Exception: pass
    try:
        current_name = memory.get_user_name()
        if not current_name or current_name == "friend": memory.set_user_name(str(getattr(config, "DEFAULT_USER_NAME", "Kalyan")))
    except Exception: pass
    try:
        current_role = memory.get_user_role()
        if not current_role: memory.set_user_role(str(getattr(config, "DEFAULT_USER_ROLE", "student")))
    except Exception: pass
    personality = PersonalityEngine(memory)
    brain = BrainController(memory, personality, None)
    brain.register_tools({
        "stop": _tool_stop, "open_folder": _tool_open_folder, "find_file": _tool_find_file, "create_file": _tool_create_file, "write_to_file": _tool_write_to_file, "move_file": _tool_move_file, "copy_file": _tool_copy_file, "delete_item": _tool_delete_item, "rename_item": _tool_rename_item, "list_files": _tool_list_files, "zip_item": _tool_zip_item, "unzip_item": _tool_unzip_item, "search_google": _tool_search_google, "search_youtube": _tool_search_youtube, "open_url": _tool_open_url, "weather": _tool_weather, "news": _tool_news, "wifi_control": _tool_wifi_control, "bluetooth_control": _tool_bluetooth_control, "phone_link": _tool_phone_link, "launch_app": _tool_launch_app, "type_text": _tool_type_text, "press_key": _tool_press_key, "screenshot": _tool_screenshot, "volume_control": _tool_volume_control, "tell_time": _tool_tell_time, "tell_date": _tool_tell_date, "organize_folder": lambda path: organize_folder(path), "clean_temp": lambda x: clean_temp_files(), "run_command": lambda cmd: run_command(cmd), "run_script": lambda script: run_script(script), "system_status": get_system_status, "battery_status": get_battery_status, "cpu_usage": get_cpu_usage, "ram_usage": get_ram_usage, "disk_usage": get_disk_usage, "network_info": get_network_info, "uptime": get_uptime, "list_apps": list_running_apps, "kill_process": kill_process, "active_window": get_active_window, "count_processes": count_running_processes, "lock_screen": lock_screen, "set_brightness": set_brightness, "night_light": toggle_night_light, "airplane_mode": toggle_airplane_mode, "display_off": display_off, "empty_recycle_bin": empty_recycle_bin, "set_wallpaper": set_wallpaper, "system_sleep": lambda x: system_sleep(), "system_shutdown": system_shutdown, "system_restart": system_restart, "cancel_shutdown": cancel_shutdown, "open_settings": open_settings, "scrape_url": scrape_url, "wikipedia": get_wikipedia_summary, "define": get_definition, "joke": get_joke, "quote": get_quote, "whatsapp": open_whatsapp, "send_whatsapp": send_whatsapp_message, "gmail": open_gmail, "compose_email": compose_email, "telegram": open_telegram, "summarize": summarize_text, "grammar": correct_grammar, "word_count": count_words, "convert_case": convert_case, "calculate": calculate, "password": generate_password, "note": reminder_note, "read_notes": read_notes, "translate": _tool_translate_text, "send_sms": _tool_send_sms, "call_contact": _tool_call_contact, "video_call": _tool_start_video_call, "read_notifications": _tool_read_notifications, "clear_notifications": _tool_clear_notifications,
    })
    from core.llm_api import generate_response, plan_actions, stream_generate_response
    brain.register_llm(generate_response, plan_actions, stream_generate_response)
    brain.register_speak(speak)
    def avatar_setup_worker():
        if getattr(config, "ASSISTANT_AUTO_GENERATE_AVATAR", True):
            try:
                ok, msg = ensure_avatar_frames(force=bool(getattr(config, "ASSISTANT_FORCE_REGENERATE_AVATAR", False)))
                if ok: log_event("AvatarFrames", msg)
            except Exception as e: log_error("AvatarFrames", e)
    threading.Thread(target=avatar_setup_worker, daemon=True).start()
    try:
        if getattr(config, "AUTO_START_WITH_WINDOWS", False): ensure_windows_startup()
        else: disable_windows_startup()
    except Exception as e: log_error("WindowsStartup", e)
    ollama_ok, internet_ok = check_ollama(), check_internet()
    if not internet_ok: print("[System] No internet."); speak("I am currently offline.")
    try:
        subprocess.run(["powershell", "-Command", "$vol = New-Object -ComObject WScript.Shell; 1..50 | ForEach-Object { $vol.SendKeys([char]175) }"], capture_output=True, timeout=5)
    except Exception: pass
    print("\n" + "=" * 60 + f"\n  {config.ASSISTANT_NAME} — SYSTEM ONLINE\n" + "=" * 60)
    
    # Start zero-latency face emotion tracker
    from core.vision_tracker import start_vision_tracker
    start_vision_tracker()
    
    threading.Thread(target=voice_listener_thread, daemon=True).start()
    threading.Thread(target=proactive_agent_thread, daemon=True).start()
    threading.Thread(target=goal_check_in_thread, args=(memory,), daemon=True).start()
    def terminal_input_thread():
        while True:
            try:
                text = input("> ")
                if text.strip(): command_queue.put(text.strip())
            except EOFError: break
            except Exception: time.sleep(1)
    threading.Thread(target=terminal_input_thread, daemon=True).start()
    app, window = None, None
    if bool(getattr(config, "GUI_ENABLED", True)):
        from visual_window import run_visual_window
        try: app, window = run_visual_window(command_queue)
        except Exception as e: log_error("GUIStartup", e)
    def emit_assistant_message(text: str, sources=None):
        if not text: return
        payload = text
        if sources:
            try: payload = f"{text}\n[[BKR_SOURCES]]{json.dumps(list(sources))}"
            except Exception: pass
        if window and hasattr(window, "msg_signal"):
            try: window.msg_signal.emit("Assistant", payload); return
            except Exception: pass
        print(f"[{config.ASSISTANT_TAG}] {_safe_console_text(text)}")
    def main_loop_worker():
        nonlocal brain
        last_norm, last_at = "", 0.0
        replay_window = float(getattr(config, "VOICE_COMMAND_DEDUP_SECONDS", 3.0))
        while True:
            try:
                user_input = command_queue.get(timeout=1)
                norm = " ".join((user_input or "").lower().split())
                now = time.time()
                if norm and norm == last_norm and (now - last_at) < replay_window: continue
                last_norm, last_at = norm, now
                global PLANNING_MODE, PLANNING_STEP, USER_GOALS
                if PLANNING_MODE:
                    USER_GOALS.append(user_input)
                    PLANNING_STEP += 1
                    if PLANNING_STEP <= 3:
                        res = ["", "And the second objective?", "And the third final objective?"][PLANNING_STEP-1]
                        emit_assistant_message(res); speak(res); continue
                    else:
                        PLANNING_MODE = False
                        for g in USER_GOALS: brain.memory.add_goal(g)
                        res = f"Objectives logged: {', '.join(USER_GOALS)}."
                        emit_assistant_message(res); speak(res); continue
                if handle_cli_command(user_input, brain): continue
                set_pause_listener(True)
                try:
                    result = brain.execute(user_input, source="voice")
                    if result.get("response") == "__EXIT__": os._exit(0)
                    if result.get("response"): emit_assistant_message(result["response"], result.get("sources"))
                except Exception as e: log_error("MainLoop", e)
                finally: set_pause_listener(False)
            except queue.Empty: pass
            except Exception as e: log_error("MainLoopWorker", e); time.sleep(1)
    threading.Thread(target=main_loop_worker, daemon=True).start()
    if app: sys.exit(app.exec_())
    while True: time.sleep(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    if args.headless: config.GUI_ENABLED = False
    start_assistant()
