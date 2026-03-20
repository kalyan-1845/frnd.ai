import re

# Compile all patterns once at module load for efficiency
_STOP_WORDS = frozenset([
    "stop", "exit", "quit", "goodbye", "bye", "shut down",
    "stop jarvis", "exit jarvis", "bye jarvis", "goodbye jarvis",
    "stop bujji", "stop buddy", "exit bujji", "exit buddy",
    "bye bujji", "bye buddy", "goodbye bujji", "goodbye buddy",
    "close buddy", "close bujji", "turn off", "shut up",
    "go away", "sleep", "go to sleep"
])

# Pre-compiled regex patterns for speed
_YOUTUBE_PATTERN = re.compile(
    r'(?:play|youtube|listen onto?|hear|watch)\s+(?:the\s+)?(?:song\s+|video\s+)?(?:on\s+youtube\s+|in\s+youtube\s+)?(.+?)(?:\s+(?:on|in)\s+youtube)?$',
    re.IGNORECASE
)
_GOOGLE_PATTERN = re.compile(
    r'(?:search|google|search for|look up|search google for|google search)\s*(.*)',
    re.IGNORECASE
)
_OPEN_FOLDER_PATTERN = re.compile(
    r'(?:open|show|go to)\s+(?:my\s+)?(?:the\s+)?(\w+)\s+folder|'
    r'open\s+(?:my\s+)?(?:the\s+)?(downloads|documents|desktop|pictures|videos|music)\b',
    re.IGNORECASE
)
_FIND_FILE_PATTERN = re.compile(
    r'(?:find|locate|search for|where is|look for)\s+(?:a\s+)?(?:file\s+)?(?:called\s+|named\s+)?(.+?)(?:\s+file)?$',
    re.IGNORECASE
)
_OPEN_URL_PATTERN = re.compile(
    r'(?:go to|visit|navigate to|open)\s+((?:https?://|www\.|[\w-]+\.(?:com|org|net|io|dev|co|in|edu|gov)\b)[\S]*)',
    re.IGNORECASE
)
_TYPE_PATTERN = re.compile(
    r'^(?:type|write)\s+(.*)',
    re.IGNORECASE
)
_PRESS_KEY_PATTERN = re.compile(
    r'^(?:press|hit|tap)\s+(.*)',
    re.IGNORECASE
)
_LAUNCH_APP_PATTERN = re.compile(
    r'^(?:open|launch|start|run)\s+(?:the\s+)?(?:app\s+)?(.+)',
    re.IGNORECASE
)
_VOLUME_PATTERN = re.compile(
    r'(?:volume|sound)\s+(up|down|mute|unmute|max|min)|'
    r'(mute|unmute)\s+(?:the\s+)?(?:volume|sound)|'
    r'(increase|decrease|raise|lower)\s+(?:the\s+)?volume',
    re.IGNORECASE
)
_SCREENSHOT_PATTERN = re.compile(
    r'(?:take\s+(?:a\s+)?)?screenshot|screen\s*shot|screen\s*capture|capture\s+screen',
    re.IGNORECASE
)
_TIME_DATE_PATTERN = re.compile(
    r"what(?:'s| is) the (?:time|date)|tell me the (?:time|date)|current (?:time|date)|what time is it|what day is it|what date is it",
    re.IGNORECASE
)
_WEATHER_PATTERN = re.compile(
    r'(?:what(?:\'s| is) the )?weather|how(?:\'s| is) the weather|temperature',
    re.IGNORECASE
)
_NEWS_PATTERN = re.compile(
    r'(?:what(?:\'s| is) the )?(?:latest )?news|headlines|updates|what is happening',
    re.IGNORECASE
)

# System control patterns
_WIFI_PATTERN = re.compile(
    r'(?:turn|switch|toggle)\s+(?:on|off|enable|disable)\s+(?:the\s+)?wi-?fi|'
    r'wi-?fi\s+(?:on|off|enable|disable)|'
    r'(?:connect|disconnect)\s+(?:the\s+)?wi-?fi',
    re.IGNORECASE
)
_BLUETOOTH_PATTERN = re.compile(
    r'bluetooth|blue tooth',
    re.IGNORECASE
)
_PHONE_PATTERN = re.compile(
    r'phone\s*link|call\s+(?:a\s+)?friend|make\s+a\s+call',
    re.IGNORECASE
)
_CREATE_FILE_PATTERN = re.compile(
    r'(?:create|make|new)\s+(?:a\s+)?(?:file|script)\s+(?:called\s+|named\s+)?([\w.]+)',
    re.IGNORECASE
)

# --- J.A.R.V.I.S. Advanced Patterns ---
_SYSTEM_STATUS_PATTERN = re.compile(
    r'(?:system\s+)?(?:status|diagnostics|health|report)|how(?:\'s| is) (?:the )?system|run diagnostics',
    re.IGNORECASE
)
_BATTERY_PATTERN = re.compile(
    r'battery|charge|charging|power level|how much (?:battery|charge|power)',
    re.IGNORECASE
)
_CPU_PATTERN = re.compile(
    r'cpu|processor|how(?:\'s| is) (?:the )?(?:cpu|processor)|cpu usage',
    re.IGNORECASE
)
_RAM_PATTERN = re.compile(
    r'\bram\b|memory usage|how much (?:ram|memory)',
    re.IGNORECASE
)
_DISK_PATTERN = re.compile(
    r'disk|storage|how much (?:disk|storage|space)',
    re.IGNORECASE
)
_NETWORK_PATTERN = re.compile(
    r'network\s+(?:status|info)|ip\s+address|internet\s+(?:status|speed|connectivity)',
    re.IGNORECASE
)
_UPTIME_PATTERN = re.compile(
    r'uptime|how long (?:has|have) (?:the )?(?:system|computer|pc) been (?:on|running|up)',
    re.IGNORECASE
)
_LOCK_PATTERN = re.compile(
    r'lock\s+(?:the\s+)?(?:screen|computer|pc|system|workstation)',
    re.IGNORECASE
)
_BRIGHTNESS_PATTERN = re.compile(
    r'(?:set\s+)?brightness\s+(?:to\s+)?(\d+)|'
    r'(?:increase|decrease|lower|raise|dim|brighten)\s+(?:the\s+)?(?:screen|brightness|display)',
    re.IGNORECASE
)
_KILL_PATTERN = re.compile(
    r'(?:kill|terminate|end|close|stop)\s+(?:the\s+)?(?:process\s+|app\s+|application\s+)?(.+)',
    re.IGNORECASE
)
_LIST_APPS_PATTERN = re.compile(
    r'(?:list|show|what)(?:\'s|\s+are)?\s+(?:the\s+)?(?:running|active|open)\s+(?:apps|applications|programs|processes)',
    re.IGNORECASE
)
_SHUTDOWN_PATTERN = re.compile(
    r'(?:shut\s*down|power\s+off)\s+(?:the\s+)?(?:system|computer|pc)',
    re.IGNORECASE
)
_RESTART_PATTERN = re.compile(
    r'restart\s+(?:the\s+)?(?:system|computer|pc)|reboot',
    re.IGNORECASE
)
_DISPLAY_OFF_PATTERN = re.compile(
    r'(?:turn\s+off|switch\s+off)\s+(?:the\s+)?(?:display|screen|monitor)',
    re.IGNORECASE
)
_RECYCLE_BIN_PATTERN = re.compile(
    r'(?:empty|clean|clear)\s+(?:the\s+)?recycle\s*bin|'
    r'recycle\s*bin\s+(?:empty|clean|clear)',
    re.IGNORECASE
)
_WALLPAPER_PATTERN = re.compile(
    r'(?:set|change)\s+(?:the\s+)?(?:wallpaper|desktop\s+background)\s+(?:to\s+)?(.+)',
    re.IGNORECASE
)
_NIGHT_LIGHT_PATTERN = re.compile(
    r'night\s*light|blue\s*light|eye\s*(?:care|comfort)',
    re.IGNORECASE
)
_AIRPLANE_PATTERN = re.compile(
    r'airplane\s*mode|flight\s*mode',
    re.IGNORECASE
)
_SETTINGS_PATTERN = re.compile(
    r'open\s+(?:the\s+)?(?:windows\s+)?settings?\s*(\w*)',
    re.IGNORECASE
)

# --- Web Scraping & Research Patterns ---
_WIKIPEDIA_PATTERN = re.compile(
    r'(?:search|look up|tell me about|what(?:\'s| is)(?: the)?|who(?:\'s| is)|explain)\s+(?:wikipedia\s+|about\s+)?(.+?)(?:\s+on wikipedia)?$',
    re.IGNORECASE
)
_DEFINE_PATTERN = re.compile(
    r'(?:define|what(?:\'s| does| is the meaning of)|meaning of|definition of)\s+(?:the\s+word\s+)?(.+)',
    re.IGNORECASE
)
_JOKE_PATTERN = re.compile(
    r'(?:tell|say|give)?\s*(?:me\s+)?(?:a\s+)?joke|make\s+me\s+laugh',
    re.IGNORECASE
)
_QUOTE_PATTERN = re.compile(
    r'(?:tell|give|say)?\s*(?:me\s+)?(?:an?\s+)?(?:inspirational\s+|motivational\s+)?quote',
    re.IGNORECASE
)
_SCRAPE_PATTERN = re.compile(
    r'(?:scrape|extract|get content from|read)\s+(?:the\s+)?(?:website\s+|page\s+|url\s+)?(.+)',
    re.IGNORECASE
)

# --- Messaging Patterns ---
_WHATSAPP_PATTERN = re.compile(
    r'(?:open|launch)\s+(?:whatsapp|what\'s app|whats app)',
    re.IGNORECASE
)
_WHATSAPP_SEND_PATTERN = re.compile(
    r'(?:send|text|message)\s+(?:a\s+)?(?:whatsapp\s+)?(?:message\s+)?(?:to\s+)?(.+?)(?:\s+(?:saying|with|that|:)\s+(.+))?$',
    re.IGNORECASE
)
_GMAIL_PATTERN = re.compile(
    r'(?:open|launch|check)\s+(?:my\s+)?(?:gmail|email|mail)',
    re.IGNORECASE
)
_TELEGRAM_PATTERN = re.compile(
    r'(?:open|launch)\s+telegram',
    re.IGNORECASE
)
_EMAIL_COMPOSE_PATTERN = re.compile(
    r'(?:compose|write|send)\s+(?:an?\s+)?email(?:\s+to\s+(.+?))?(?:\s+(?:about|regarding|with subject)\s+(.+))?$',
    re.IGNORECASE
)

# --- Text & NLP Tool Patterns ---
_SUMMARIZE_PATTERN = re.compile(
    r'summarize(?:\s+this)?(?:\s+text)?(?::?\s+(.+))?',
    re.IGNORECASE
)
_GRAMMAR_PATTERN = re.compile(
    r'(?:correct|fix|check)\s+(?:the\s+)?grammar(?:\s+of)?(?:\s+(.+))?',
    re.IGNORECASE
)
_WORD_COUNT_PATTERN = re.compile(
    r'(?:count|how many)\s+words?(?:\s+in)?(?:\s+(.+))?',
    re.IGNORECASE
)
_CALCULATE_PATTERN = re.compile(
    r'(?:calculate|compute|what(?:\'s| is)\s+(?:the\s+)?(?:result\s+of)?)\s+(.+)',
    re.IGNORECASE
)
_PASSWORD_PATTERN = re.compile(
    r'(?:generate|create|make)\s+(?:a\s+)?(?:strong\s+|random\s+|secure\s+)?password(?:\s+of\s+(\d+)(?:\s+characters?)?)?',
    re.IGNORECASE
)
_NOTE_PATTERN = re.compile(
    r'(?:save|take|add|write|make)\s+(?:a\s+)?(?:note|reminder)(?:\s+(?:that|:)\s*)?(.+)',
    re.IGNORECASE
)
_READ_NOTES_PATTERN = re.compile(
    r'(?:read|show|display|what are)\s+(?:my\s+)?(?:notes?|reminders?)',
    re.IGNORECASE
)

# Apps that should open in browser, not as desktop apps
_WEB_APPS = frozenset(["youtube", "gmail", "spotify", "netflix", "twitter", "instagram", "facebook", "reddit"])

# Known folder names for quick matching
_KNOWN_FOLDERS = frozenset([
    "downloads", "documents", "desktop", "pictures", "videos", "music",
    "download", "document", "picture", "video"
])


def parse_command(command_text):
    """
    Analyzes the raw command text and determines the Intent.
    Uses pre-compiled regex patterns for maximum efficiency.
    Returns dict with 'action' and 'target' keys.
    """
    if not command_text:
        return {"action": "unknown", "target": ""}
    
    command_text = command_text.lower().strip()

    # Strip wake words if present (important for text/web input)
    wake_words = [
        "bkr 2.0", "hey bkr 2.0",
        "bkr", "hey bkr", "hello bkr", "hi bkr", "ok bkr",
        "jarvis", "hey jarvis", "hello jarvis", "hi jarvis", "ok jarvis",
        "j.a.r.v.i.s.", "hey j.a.r.v.i.s.",
        "nova", "hey nova", "hello nova", "hi nova", "ok nova",
        "bujji", "hey bujji", "hello bujji", "hi bujji", "ok bujji",
        "buddy", "hey buddy", "hello buddy", "hi buddy", "ok buddy",
        "ai", "hey ai", "computer", "hey computer",
    ]
    # Sort by length desc to match longest first ("hey jarvis" before "jarvis")
    wake_words.sort(key=len, reverse=True)
    
    for w in wake_words:
        if command_text.startswith(w):
            # Check for word boundary
            if len(command_text) == len(w) or command_text[len(w)].isspace() or command_text[len(w)] in ",.!:":
                command_text = command_text[len(w):].strip(" ,.!:")
                break

    # --- PRIORITY 0: SYSTEM COMMANDS (Check first!) ---
    if command_text in _STOP_WORDS:
        return {"action": "stop", "target": None}

    # --- PRIORITY 1: TIME/DATE (simple, fast check) ---
    if _TIME_DATE_PATTERN.search(command_text):
        if "date" in command_text:
            return {"action": "tell_date", "target": None}
        return {"action": "tell_time", "target": None}

    # --- PRIORITY 2: SCREENSHOT ---
    if _SCREENSHOT_PATTERN.search(command_text):
        return {"action": "screenshot", "target": None}

    # --- PRIORITY 3: VOLUME CONTROL ---
    m = _VOLUME_PATTERN.search(command_text)
    if m:
        direction = m.group(1) or m.group(2) or m.group(3)
        if direction:
            direction = direction.lower()
            if direction in ("increase", "raise"):
                direction = "up"
            elif direction in ("decrease", "lower"):
                direction = "down"
        return {"action": "volume_control", "target": direction}

    # --- PRIORITY 4: WEATHER ---
    if _WEATHER_PATTERN.search(command_text):
        return {"action": "weather", "target": command_text}

    # --- PRIORITY 5: NEWS ---
    if _NEWS_PATTERN.search(command_text):
        return {"action": "news", "target": command_text}

    # --- PRIORITY 5b: WIFI ---
    if _WIFI_PATTERN.search(command_text):
        return {"action": "wifi_control", "target": command_text}

    # --- PRIORITY 5c: BLUETOOTH ---
    if _BLUETOOTH_PATTERN.search(command_text) and any(kw in command_text for kw in ["open", "turn", "switch", "setting"]):
        return {"action": "bluetooth_control", "target": command_text}

    # --- PRIORITY 5d: PHONE LINK ---
    if _PHONE_PATTERN.search(command_text):
        return {"action": "phone_link", "target": command_text}

    # --- PRIORITY 5e: CREATE FILE ---
    m = _CREATE_FILE_PATTERN.search(command_text)
    if m:
        filename = m.group(1).strip()
        return {"action": "create_file", "target": filename}

    # --- J.A.R.V.I.S. SYSTEM COMMANDS ---

    # System status / diagnostics
    if _SYSTEM_STATUS_PATTERN.search(command_text):
        return {"action": "system_status", "target": ""}

    # Battery
    if _BATTERY_PATTERN.search(command_text):
        return {"action": "battery_status", "target": ""}

    # CPU
    if _CPU_PATTERN.search(command_text):
        return {"action": "cpu_usage", "target": ""}

    # RAM
    if _RAM_PATTERN.search(command_text):
        return {"action": "ram_usage", "target": ""}

    # Disk
    if _DISK_PATTERN.search(command_text) and not any(kw in command_text for kw in ["open", "launch"]):
        return {"action": "disk_usage", "target": ""}

    # Network info
    if _NETWORK_PATTERN.search(command_text):
        return {"action": "network_info", "target": ""}

    # Uptime
    if _UPTIME_PATTERN.search(command_text):
        return {"action": "uptime", "target": ""}

    # Lock screen
    if _LOCK_PATTERN.search(command_text):
        return {"action": "lock_screen", "target": ""}

    # Brightness
    m = _BRIGHTNESS_PATTERN.search(command_text)
    if m:
        level = m.group(1) if m.group(1) else "50"
        if "increase" in command_text or "raise" in command_text or "brighten" in command_text:
            level = "80"
        elif "decrease" in command_text or "lower" in command_text or "dim" in command_text:
            level = "20"
        return {"action": "set_brightness", "target": level}

    # Kill process
    if any(kw in command_text for kw in ["kill", "terminate", "end task"]):
        m = _KILL_PATTERN.search(command_text)
        if m:
            target = m.group(1).strip()
            return {"action": "kill_process", "target": target}

    # List running apps
    if _LIST_APPS_PATTERN.search(command_text):
        return {"action": "list_apps", "target": ""}

    # Shutdown
    if _SHUTDOWN_PATTERN.search(command_text):
        return {"action": "system_shutdown", "target": ""}

    # Restart
    if _RESTART_PATTERN.search(command_text):
        return {"action": "system_restart", "target": ""}

    # Display off
    if _DISPLAY_OFF_PATTERN.search(command_text):
        return {"action": "display_off", "target": ""}

    # Empty Recycle Bin
    if _RECYCLE_BIN_PATTERN.search(command_text):
        return {"action": "empty_recycle_bin", "target": ""}

    # Wallpaper
    m = _WALLPAPER_PATTERN.search(command_text)
    if m:
        return {"action": "set_wallpaper", "target": m.group(1).strip()}

    # Night Light
    if _NIGHT_LIGHT_PATTERN.search(command_text):
        return {"action": "night_light", "target": ""}

    # Airplane Mode
    if _AIRPLANE_PATTERN.search(command_text):
        return {"action": "airplane_mode", "target": ""}

    # Open Settings
    m = _SETTINGS_PATTERN.search(command_text)
    if m:
        page = m.group(1).strip() if m.group(1) else ""
        return {"action": "open_settings", "target": page}

    # --- MESSAGING ---

    # WhatsApp open
    if _WHATSAPP_PATTERN.search(command_text):
        return {"action": "whatsapp", "target": ""}

    # WhatsApp send message (must check before whatsapp open)
    if any(kw in command_text for kw in ["send", "text", "message"]) and \
       any(kw in command_text for kw in ["whatsapp", "whats app"]):
        m = _WHATSAPP_SEND_PATTERN.search(command_text)
        if m:
            contact = m.group(1).strip() if m.group(1) else ""
            msg = m.group(2).strip() if m.group(2) else ""
            target = f"{contact}|{msg}" if contact and msg else msg or contact
            return {"action": "send_whatsapp", "target": target}
        return {"action": "whatsapp", "target": ""}

    # Gmail
    if _GMAIL_PATTERN.search(command_text):
        return {"action": "gmail", "target": ""}

    # Telegram
    if _TELEGRAM_PATTERN.search(command_text):
        return {"action": "telegram", "target": ""}

    # Compose email
    if _EMAIL_COMPOSE_PATTERN.search(command_text):
        m = _EMAIL_COMPOSE_PATTERN.search(command_text)
        to = m.group(1).strip() if m and m.group(1) else ""
        subj = m.group(2).strip() if m and m.group(2) else "Message"
        return {"action": "compose_email", "target": f"{to}|{subj}"}

    # --- TEXT & NLP TOOLS ---

    # Summarize (must come before generic chat catch)
    if "summarize" in command_text:
        m = _SUMMARIZE_PATTERN.search(command_text)
        text = m.group(1).strip() if m and m.group(1) else ""
        return {"action": "summarize", "target": text}

    # Grammar correction
    if any(kw in command_text for kw in ["correct grammar", "fix grammar", "check grammar"]):
        m = _GRAMMAR_PATTERN.search(command_text)
        text = m.group(1).strip() if m and m.group(1) else ""
        return {"action": "grammar", "target": text}

    # Word count
    if _WORD_COUNT_PATTERN.search(command_text):
        m = _WORD_COUNT_PATTERN.search(command_text)
        text = m.group(1).strip() if m and m.group(1) else ""
        return {"action": "word_count", "target": text}

    # Calculator
    if any(kw in command_text for kw in ["calculate", "compute", "what is the result"]):
        m = _CALCULATE_PATTERN.search(command_text)
        if m:
            return {"action": "calculate", "target": m.group(1).strip()}

    # Password generation
    if _PASSWORD_PATTERN.search(command_text):
        m = _PASSWORD_PATTERN.search(command_text)
        length = m.group(1).strip() if m and m.group(1) else "16"
        return {"action": "password", "target": length}

    # Save note
    if any(kw in command_text for kw in ["save a note", "take a note", "add a note", "write a note",
                                           "make a note", "save a reminder", "remind me"]):
        m = _NOTE_PATTERN.search(command_text)
        note = m.group(1).strip() if m and m.group(1) else command_text
        return {"action": "note", "target": note}

    # Read notes
    if _READ_NOTES_PATTERN.search(command_text):
        return {"action": "read_notes", "target": ""}

    # --- WEB RESEARCH (priority before generic URL open) ---

    # Joke
    if _JOKE_PATTERN.search(command_text):
        return {"action": "joke", "target": ""}

    # Quote
    if _QUOTE_PATTERN.search(command_text):
        return {"action": "quote", "target": ""}

    # Define a word (before Wikipedia so "define" takes priority)
    if any(kw in command_text for kw in ["define ", "definition of", "meaning of", "what does"]):
        m = _DEFINE_PATTERN.search(command_text)
        if m:
            return {"action": "define", "target": m.group(1).strip()}

    # Scrape URL
    if any(kw in command_text for kw in ["scrape", "extract content", "get content from"]):
        m = _SCRAPE_PATTERN.search(command_text)
        if m:
            return {"action": "scrape_url", "target": m.group(1).strip()}

    # Wikipedia lookup — "tell me about X" / "who is X" / "what is X" (not weather/time/news)
    if any(kw in command_text for kw in ["tell me about", "who is", "who was", "what is", "explain"]):
        skip_words = {"time", "date", "weather", "news", "cpu", "ram", "battery", "disk", "network"}
        if not any(skip in command_text for skip in skip_words):
            m = _WIKIPEDIA_PATTERN.search(command_text)
            if m:
                topic = m.group(1).strip()
                if topic and len(topic) > 1:
                    return {"action": "wikipedia", "target": topic}

    # --- PRIORITY 6: URL OPENING (before generic open) ---
    m = _OPEN_URL_PATTERN.search(command_text)
    if m:
        target = m.group(1).strip()
        return {"action": "open_url", "target": target}

    # --- PRIORITY 6: FOLDER MANAGEMENT ---
    # Quick check: if "folder" is in the text
    if "folder" in command_text:
        m = _OPEN_FOLDER_PATTERN.search(command_text)
        if m:
            target = (m.group(1) or m.group(2) or "").strip()
            if target:
                return {"action": "open_folder", "target": target}

    # Direct folder name match: "open downloads", "open documents"
    for folder in _KNOWN_FOLDERS:
        if folder in command_text and ("open" in command_text or "show" in command_text):
            return {"action": "open_folder", "target": folder}

    # --- PRIORITY 7: FILE FINDING ---
    if any(kw in command_text for kw in ["find", "locate", "where is", "look for"]):
        m = _FIND_FILE_PATTERN.search(command_text)
        if m:
            target = m.group(1).strip()
            if target:
                return {"action": "find_file", "target": target}

    # --- PRIORITY 8: YOUTUBE (before Google, since "play" is specific) ---
    if any(kw in command_text for kw in ["youtube", "play "]):
        m = _YOUTUBE_PATTERN.search(command_text)
        if m:
            target = m.group(1).strip()
            # Clean up common suffixes
            for suffix in ["on youtube", "youtube", "for me", "please"]:
                target = target.replace(suffix, "").strip()
            if target:
                return {"action": "search_youtube", "target": target}
        # Fallback: If just "open youtube" with no query, open YouTube homepage
        if "youtube" in command_text:
            return {"action": "open_url", "target": "https://www.youtube.com"}
        # Fallback: extract everything after "play"
        target = command_text
        for word in ["play", "on youtube", "youtube", "search"]:
            target = target.replace(word, "").strip()
        if target:
            return {"action": "search_youtube", "target": target}

    # --- PRIORITY 9: GOOGLE SEARCH ---
    if any(kw in command_text for kw in ["search", "google", "look up"]):
        m = _GOOGLE_PATTERN.search(command_text)
        if m:
            target = m.group(1).strip()
            for suffix in ["on google", "google", "for me", "please"]:
                target = target.replace(suffix, "").strip()
            if target:
                return {"action": "search_google", "target": target}

    # --- PRIORITY 10: TYPING/KEYBOARD ---
    m = _TYPE_PATTERN.match(command_text)
    if m:
        return {"action": "type_text", "target": m.group(1).strip()}

    m = _PRESS_KEY_PATTERN.match(command_text)
    if m:
        return {"action": "press_key", "target": m.group(1).strip()}

    # --- PRIORITY 11: APP LAUNCHING (catch-all for 'open') ---
    m = _LAUNCH_APP_PATTERN.match(command_text)
    if m:
        target = m.group(1).strip()
        if target:
            # If it's a web app, open in browser instead
            if target in _WEB_APPS:
                return {"action": "open_url", "target": f"https://www.{target}.com"}
            return {"action": "launch_app", "target": target}

    # --- PRIORITY 12: UNKNOWN → Chat mode ---
    return {"action": "unknown", "target": command_text}
