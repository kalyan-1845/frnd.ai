"""
AI Brain Controller — Central intelligence hub for the AI assistant.

Every user input flows through BrainController.execute() which:
1. Classifies the input (chat/task/automation/system/media)
2. Routes to the correct handler
3. Applies safety/confirmation checks
4. Executes with fault tolerance
5. Logs every decision
"""
import time
import re
from typing import Optional, Dict, List, Any
import config
from core.logger import log_decision, log_error, log_event
from core.intent_parser import parse_command
from core.llm_api import get_last_response_meta, is_telugu_input
from core.companion_style import format_companion_response, extract_emotion_tag, tag_to_voice_mood
from core.english_coach import EnglishCoach
from core.tutor_engine import SubjectTutor
from core.input_processor import process_user_input, is_teaching_request, get_response_guidance
from core.safety_system import analyze_command_safety, enforce_safe_mode, get_safety_status
from core.teaching_engine import analyze_learning_request, create_lesson_plan, deliver_lesson

# --- Input Classification ---

# Keywords that indicate actionable intents (not chat)
_TASK_KEYWORDS = frozenset([
    "open", "launch", "start", "run", "create", "make", "search", "find",
    "play", "listen", "turn", "write", "type", "close", "delete", "press",
    "take", "screenshot", "volume", "brightness", "lock", "kill", "terminate",
    "list", "show", "check", "status", "battery", "cpu", "ram", "disk",
    "network", "uptime", "processes", "recycle", "wallpaper", "organize",
    "clean", "empty", "move", "copy", "transfer", "duplicate", "remove", "delete", "translate",
])

_SYSTEM_KEYWORDS = frozenset([
    "wifi", "bluetooth", "shutdown", "restart", "sleep", "phone link",
    "system", "settings", "control panel", "task manager", "registry",
    "device manager", "airplane", "night light", "brightness", "lock",
    "display off", "recycle bin", "wallpaper", "battery", "cpu", "ram",
    "disk", "network", "uptime", "processes",
])

_MEDIA_KEYWORDS = frozenset([
    "play", "song", "music", "video", "youtube", "spotify", "listen",
    "watch", "movie", "podcast",
])

# Learning keywords - for teaching the assistant
_LEARNING_KEYWORDS = frozenset([
    "learn", "remember", "note", "remember that", "don't forget",
    "keep in mind", "memorize", "teach me", "i want you to know",
    "important", "this is", "understand that", "know that",
    "remember this", "never forget", "always", "never",
    "english coach", "start english", "next lesson", "daily session",
    "practice english", "quiz me", "english plan", "study plan",
    "progress report", "start course", "teach english",
    "start lesson", "next step", "repeat step", "lesson status",
    "stop lesson", "help me learn", "learn about", "course on",
    "train", "train that", "training",
])

# Actions that are considered dangerous and require confirmation
_DANGEROUS_ACTIONS = frozenset([
    "wifi_control", "bluetooth_control", "phone_link", "press_key",
    "write_to_file", "create_file", "kill_process",
    "system_shutdown", "system_restart", "empty_recycle_bin",
])

# Actions that are pure system operations
_SYSTEM_ACTIONS = frozenset([
    "wifi_control", "bluetooth_control", "phone_link",
    "system_shutdown", "system_restart", "cancel_shutdown",
    "system_sleep", "lock_screen",
])

# Actions that should trigger tool execution (not chat)
_EXECUTABLE_ACTIONS = frozenset([
    "open_folder", "find_file", "create_file", "write_to_file",
    "search_google", "search_youtube", "open_url", "weather", "news",
    "wifi_control", "bluetooth_control", "phone_link",
    "launch_app", "type_text", "press_key", "screenshot",
    "volume_control", "tell_time", "tell_date", "stop",
    "run_command", "run_script", "organize_folder", "clean_temp",
    # J.A.R.V.I.S. System Monitoring
    "system_status", "battery_status", "cpu_usage", "ram_usage",
    "disk_usage", "network_info", "uptime",
    # Process Management
    "list_apps", "kill_process", "active_window", "count_processes",
    # Advanced System Settings
    "lock_screen", "set_brightness", "night_light", "airplane_mode",
    "display_off", "empty_recycle_bin", "set_wallpaper",
    "system_sleep", "system_shutdown", "system_restart", "cancel_shutdown",
    "open_settings",
    # Web Research & Scraping
    "scrape_url", "wikipedia", "define", "joke", "quote",
    # Messaging
    "whatsapp", "send_whatsapp", "gmail", "compose_email", "telegram",
    # Text & NLP Tools
    "summarize", "grammar", "word_count", "convert_case",
    "calculate", "password", "note", "read_notes",
    "move_file", "copy_file", "delete_item", "translate",
])


class BrainController:
    """
    Central AI Brain — classifies, routes, executes, and logs all user input.
    """

    def __init__(self, memory, personality_engine, server_module=None):
        """
        Args:
            memory: MemorySystem instance
            personality_engine: PersonalityEngine instance
            server_module: The server module for UI updates (optional)
        """
        self.memory = memory
        self.personality = personality_engine
        self.server = server_module
        self._confirmation_pending = None  # Stores action awaiting confirmation
        self._tools = {}  # Registered tool functions
        self._llm_generate = None  # LLM chat function
        self._llm_plan = None  # LLM planner function
        self._speak_fn = None  # Voice output function
        self.coach = EnglishCoach(memory)
        self.tutor = SubjectTutor(memory)
        log_event("BrainController initialized")

    # --- Registration ---

    def register_tools(self, tools_dict: dict):
        """
        Register tool functions the brain can dispatch to.
        tools_dict maps action names to callables.
        """
        self._tools.update(tools_dict)
        log_event("Tools registered", f"count={len(self._tools)}")

    def register_llm(self, generate_fn, plan_fn, stream_generate_fn=None):
        """Register the LLM generate_response, plan_actions, and optional stream_generate_response functions."""
        self._llm_generate = generate_fn
        self._llm_plan = plan_fn
        self._llm_stream = stream_generate_fn
        try:
            self.tutor.bind_llm(generate_fn)
        except Exception:
            pass
        log_event("LLM registered")

    def register_speak(self, speak_fn):
        """Register the speak/TTS function."""
        self._speak_fn = speak_fn

    # --- Core Processing Pipeline ---

    def execute(self, user_input: str, source: str = "text") -> dict:
        """
        Main entry point. Process user input through the full pipeline.

        Args:
            user_input: Raw text from user (voice-transcribed or typed)
            source: Input source ('voice', 'text', 'web')

        Returns:
            dict with keys: response, action, intent_type, success
        """
        if not user_input or not user_input.strip():
            return {"response": None, "action": None, "intent_type": None, "success": False}

        user_input = user_input.strip()
        start_time = time.time()

        # 0. Check if we're waiting for confirmation
        if self._confirmation_pending:
            return self._handle_confirmation(user_input)

        # 1. FAST PATH: Handle simple commands without LLM
        fast_response = self._fast_path(user_input)
        if fast_response:
            return fast_response

        # 2. Classify the input
        intent_type = self.classify_input(user_input)

        # 2. Route based on classification
        try:
            if intent_type == "system":
                result = self._handle_system(user_input, intent_type)
            elif intent_type == "learning":
                result = self._handle_learning(user_input, intent_type)
            elif intent_type in ("task", "automation", "media"):
                result = self._handle_action(user_input, intent_type)
            else:  # chat
                result = self._handle_chat(user_input, intent_type)
        except Exception as e:
            log_error("BrainController.execute", e, f"input='{user_input[:50]}'")
            result = {
                "response": "I ran into an issue processing that. Let me try a simpler approach.",
                "action": "error_fallback",
                "intent_type": intent_type,
                "success": False,
            }
            # Fallback to chat
            try:
                result = self._handle_chat(user_input, "chat")
            except Exception:
                pass  # Use the error response

        elapsed = time.time() - start_time
        log_event("Execute complete", f"elapsed={elapsed:.2f}s type={intent_type}")
        return result

    # --- Fast Path for Simple Commands ---
    def _fast_path(self, user_input: str) -> Optional[dict]:
        """
        Handle simple commands without LLM for <2s response time.
        Returns dict response if handled, None if needs full processing.
        """
        text_lower_full = user_input.lower().strip()

        # Let the regex parser catch common, non-LLM tasks even when the user prefixes a greeting
        # (e.g. "hello what is the time now").
        try:
            intent = parse_command(user_input)
        except Exception:
            intent = {"action": "unknown"}

        action = intent.get("action", "unknown")
        if action == "tell_time":
            if action in self._tools:
                return self._execute_single(action, "", user_input, "task")
            from datetime import datetime
            now = datetime.now().strftime("%I:%M %p")
            resp = f"It is {now}."
            self._safe_speak(resp, "neutral")
            return {"response": resp, "action": "tell_time", "intent_type": "task", "success": True}
        if action == "tell_date":
            if action in self._tools:
                return self._execute_single(action, "", user_input, "task")
            from datetime import datetime
            today = datetime.now().strftime("%A, %B %d, %Y")
            resp = f"Today is {today}."
            self._safe_speak(resp, "neutral")
            return {"response": resp, "action": "tell_date", "intent_type": "task", "success": True}

        # Greeting responses (simple, no LLM needed). If a greeting is followed by a real request,
        # strip the greeting and let the rest of this fast-path (or the full pipeline) handle it.
        greetings = {
            "hello": "Hello! How can I help you today?",
            "hi": "Hi there! What can I do for you?",
            "hey": "Hey! How's it going?",
            "good morning": "Good morning! Ready to start your day?",
            "good afternoon": "Good afternoon! How can I assist?",
            "good evening": "Good evening! What can I help with?",
        }

        text_lower = text_lower_full
        for kw, resp in greetings.items():
            if text_lower == kw or text_lower.strip(" ,.!:;?") == kw:
                self._safe_speak(resp, "neutral")
                return {"response": resp, "action": "greeting", "intent_type": "chat", "success": True}
            if text_lower.startswith(kw):
                remainder = text_lower[len(kw):].lstrip(" ,.!:;?")
                if remainder:
                    text_lower = remainder
                break
        
        # How are you responses
        if any(kw in text_lower for kw in ["how are you", "how r you", "how do you do"]):
            resp = "I'm doing great, thanks for asking! How can I help you today?"
            self._safe_speak(resp, "neutral")
            return {"response": resp, "action": "greeting", "intent_type": "chat", "success": True}
        
        # Thank you responses
        if any(kw in text_lower for kw in ["thank you", "thanks", "thank u", "thx"]):
            resp = "You're welcome! Let me know if there's anything else."
            self._safe_speak(resp, "neutral")
            return {"response": resp, "action": "thanks", "intent_type": "chat", "success": True}
        
        # Exit/stop commands
        if any(kw in text_lower for kw in ["stop", "exit", "quit", "goodbye", "bye"]):
            resp = "Goodbye! Have a great day!"
            self._safe_speak(resp, "neutral")
            return {"response": resp, "action": "stop", "intent_type": "task", "success": True}
        
        return None  # No fast path - use full LLM processing

    # --- Input Classification ---

    def classify_input(self, user_input: str) -> str:
        """
        OPTIMIZED: Fast input classification with early returns.
        """
        raw_text = user_input.strip()
        # Handle numbered lists like "1. teach me ai"
        text_normalized = re.sub(r"^\d+[\.\)\s]+", "", raw_text).strip()
        text_lower = text_normalized.lower()
        
        # CLI commands are always tasks - FAST PATH
        if text_lower.startswith("/"):
            return "task"

        # Explicit learning keywords should route to learning before tool parsing.
        if any(kw in text_lower for kw in _LEARNING_KEYWORDS):
            # Check for specific learning commands
            if "list lessons" in text_lower or "show lessons" in text_lower or "what did you learn" in text_lower:
                return "learning"
            return "learning"

        # Try the regex parser first (fast path)
        intent = parse_command(user_input)
        action = intent.get("action", "unknown")

        # If regex matched a known action, classify quickly
        if action != "unknown":
            if action in _SYSTEM_ACTIONS:
                return "system"
            if action in _EXECUTABLE_ACTIONS:
                if action in ("search_youtube",) or any(kw in text_lower for kw in ["play", "music", "song", "video"]):
                    return "media"
                return "task"

        # If no tool intent matched, let the tutor/coach take over (e.g. "what is recursion").
        if self.tutor and self.tutor.should_handle(text_normalized):
            return "learning"

        if self.coach and self.coach.should_handle(user_input):
            return "learning"

        # Quick keyword checks using sets for O(1) lookup
        words = set(text_lower.split())

        # System keywords
        if words & _SYSTEM_KEYWORDS or any(kw in text_lower for kw in _SYSTEM_KEYWORDS):
            return "system"

        # Media keywords
        if words & _MEDIA_KEYWORDS and words & {"play", "open", "search", "listen", "watch"}:
            return "media"

        # Task keywords - only for short commands
        if words & _TASK_KEYWORDS and len(user_input.split()) <= 8:
            return "task"

        # Default: chat
        return "chat"

    # --- Handlers ---

    def _handle_action(self, user_input: str, intent_type: str) -> dict:
        """Handle task/automation/media inputs — execute tools."""

        # Step 1: Try regex parser (fast path)
        intent = parse_command(user_input)
        action = intent.get("action", "unknown")
        target = intent.get("target", "")

        # Step 2: If regex didn't match, try LLM planner
        if action == "unknown" and self._llm_plan:
            plan = self._safe_plan(user_input)
            if plan and len(plan) > 0:
                return self._execute_plan(plan, user_input, intent_type)

        # Step 3: Check if action is dangerous
        if action in _DANGEROUS_ACTIONS and self._is_dangerous_context(action, target):
            return self._request_confirmation(action, target, user_input, intent_type)

        # Step 4: Execute the action
        if action != "unknown" and action in self._tools:
            return self._execute_single(action, target, user_input, intent_type)

        # Step 5: Fallback to LLM planner if regex matched 'unknown'
        if self._llm_plan:
            plan = self._safe_plan(user_input)
            if plan and len(plan) > 0:
                return self._execute_plan(plan, user_input, intent_type)

        # Step 6: Nothing worked — fall back to chat
        log_decision(user_input, intent_type, "fallback_to_chat", "", "fallback",
                      "No tool matched, routing to chat")
        return self._handle_chat(user_input, "chat")

    def _handle_system(self, user_input: str, intent_type: str) -> dict:
        """Handle system-level inputs — always require confirmation."""
        intent = parse_command(user_input)
        action = intent.get("action", "unknown")
        target = intent.get("target", "")

        if action != "unknown" and action in self._tools:
            # System commands always require confirmation
            return self._request_confirmation(action, target, user_input, intent_type)

        # If we can't parse it, treat as chat
        return self._handle_chat(user_input, "chat")

    def _handle_chat(self, user_input: str, intent_type: str) -> dict:
        """Handle conversational inputs — route to LLM."""
        response = None
        llm_meta = {}
        user_style = str(getattr(config, "ASSISTANT_USER_STYLE", "friendly_assistant")).lower()
        companion_mode = user_style in {"companion", "romantic_companion", "sara_companion"}

        # If a structured tutor session is active, keep the learning flow coherent.
        if self.tutor and self.tutor.should_handle(user_input):
            tutor_reply = self.tutor.handle_input(user_input)
            if tutor_reply:
                tutor_meta = self.tutor.get_last_meta() if self.tutor else {}
                log_decision(user_input, "learning", "subject_tutor", "", "success")
                self._safe_speak(tutor_reply, "calm")
                return {
                    "response": tutor_reply,
                    "action": "subject_tutor",
                    "intent_type": "learning",
                    "success": True,
                    "sources": tutor_meta.get("sources", []),
                }

        # If English coach is waiting for an answer, route to learning first.
        if self.coach and self.coach.should_handle(user_input):
            coach_reply = self.coach.handle_input(user_input)
            if coach_reply:
                log_decision(user_input, "learning", "english_coach", "", "success")
                self._safe_speak(coach_reply, "calm")
                return {
                    "response": coach_reply,
                    "action": "english_coach",
                    "intent_type": "learning",
                    "success": True,
                }

        # Auto-detect user name ("my name is X" / "call me X")
        self._try_extract_user_info(user_input)

        # Check if user input is in Telugu - if so, prioritize LLM for full Telugu response
        # This ensures the LLM gets the Telugu-only instruction
        english_only = bool(getattr(config, "FORCE_ENGLISH_ONLY", False)) or str(
            getattr(config, "ASSISTANT_PRIMARY_LANGUAGE", "")
        ).lower() in {"english", "en"}
        user_is_telugu = False if english_only else is_telugu_input(user_input)
        
        # For Telugu input, go directly to LLM (which has Telugu-only instruction)
        # For colloquial Telugu, we can still use personality as fallback
        use_personality_first = (
            self._is_colloquial_telugu_input(user_input)
            and not user_is_telugu
            and not english_only
        )
        
        if use_personality_first:
            try:
                response = self.personality.get_response(user_input)
            except Exception as e:
                log_error("PersonalityEngine.get_response", e, f"input='{user_input[:40]}'")
                response = None

        # Streaming generation can easily cause "double voice" (many short TTS calls).
        # Buffer the stream and speak once to keep voice output stable.
        if self._llm_stream and not companion_mode:
            full_response = ""
            mood = "neutral"
            try:
                user_name = self.memory.get_user_name()
                memory_context = self.memory.get_relevant_context(user_input)

                for chunk in self._llm_stream(user_input, user_name, memory_context):
                    if chunk:
                        full_response += chunk + " "

                full_response = full_response.strip()
                if full_response:
                    self._safe_speak(full_response, mood)

                return {
                    "response": full_response,
                    "action": "chat",
                    "intent_type": "chat",
                    "success": True,
                }
            except Exception as e:
                log_error("LLM.stream_generate", e)
                # Fall back to normal generate if stream fails

        # Try LLM first for normal chat or Telugu input
        if not response and self._llm_generate:
            try:
                user_name = self.memory.get_user_name()
                memory_context = self.memory.get_relevant_context(user_input)
                # Companion mode has its own strict style prompt, so avoid adding
                # legacy Telugu persona hints that can conflict with Sara formatting.
                persona_context = ""
                try:
                    response = self._llm_generate(
                        user_input,
                        user_name,
                        memory_context,
                        persona_context,
                        companion_mode=companion_mode,
                    )
                except TypeError:
                    response = self._llm_generate(user_input, user_name, memory_context, persona_context)
                llm_meta = get_last_response_meta(reset=True)
            except Exception as e:
                log_error("LLM.generate_response", e, f"input='{user_input[:40]}'")
                response = None
                llm_meta = {}

        # Fallback to personality engine
        if not response or not response.strip():
            if english_only:
                response = "I am here. Tell me what you want to learn, and I will guide you step by step."
            else:
                try:
                    response = self.personality.get_response(user_input)
                except Exception as e:
                    log_error("PersonalityEngine.get_response", e)
                    response = "I am here. How may I assist you?"

        response = (response or "").strip()
        if companion_mode:
            response = format_companion_response(response, user_text=user_input)

        # Store in short-term memory
        self.memory.set_short_term("last_chat_input", user_input)
        self.memory.set_short_term("last_chat_response", response)

        # Auto-guided English learning nudges in teacher mode.
        try:
            if self.coach:
                self.coach.register_chat_turn()
                passive_prompt = self.coach.get_passive_prompt()
                if passive_prompt and passive_prompt not in response:
                    response = f"{response}\n\n{passive_prompt}"
        except Exception as e:
            log_error("EnglishCoach.passive_prompt", e)

        # Periodic emotional check-in to adapt teaching and support quality.
        try:
            chat_count = int(self.memory.get_short_term("chat_count", 0)) + 1
            self.memory.set_short_term("chat_count", chat_count)
            emotional_words = ("stress", "anxious", "sad", "tired", "overwhelmed", "upset", "worried")
            last_checkin_turn = int(self.memory.get_short_term("last_wellbeing_checkin_turn", 0))
            needs_checkin = (chat_count - last_checkin_turn) >= 8
            if (
                needs_checkin
                and not any(w in user_input.lower() for w in emotional_words)
                and len(user_input.split()) >= 3
            ):
                response = (
                    f"{response}\n\n"
                    "Quick check-in: How are you feeling today? "
                    "If you feel stressed or overloaded, tell me why and I will adapt my response."
                )
                self.memory.set_short_term("last_wellbeing_checkin_turn", chat_count)
        except Exception as e:
            log_error("Brain.checkin", e)

        log_decision(user_input, intent_type, "chat", "", "success")

        # Speak the response
        self._safe_speak(response, "neutral")

        return {
            "response": response,
            "action": "chat",
            "intent_type": intent_type,
            "success": True,
            "sources": llm_meta.get("sources", []),
        }

    def _is_colloquial_telugu_input(self, text: str) -> bool:
        return False

    # --- Learning Handler ---

    def _handle_learning(self, user_input: str, intent_type: str) -> dict:
        """Handle learning/teaching inputs - store or retrieve lessons."""
        # Normalize input
        text_normalized = re.sub(r"^\d+[\.\)\s]+", "", user_input.strip()).strip()
        text_lower = text_normalized.lower()
        
        # Only handle learning if there's an active session OR explicit learning command
        coach = self.coach
        tutor = self.tutor
        
        # Check for active English coach session
        if coach and coach.state.get("active"):
            coach_reply = coach.process(text_normalized)
            if coach_reply:
                log_decision(user_input, "learning", "english_coach", "", "success")
                self._safe_speak(coach_reply, "calm")
                return {
                    "response": coach_reply,
                    "action": "english_coach",
                    "intent_type": "learning",
                    "success": True,
                }
        
        # Check for explicit learning commands (not general chat)
        explicit_learning = any(kw in text_lower for kw in [
            "english", "lesson", "tutor", "teach me", "quiz", "course",
            "practice", "grammar", "vocabulary", "pronunciation", "train", "learn"
        ])
        
        # If no active session and not explicit learning, treat as chat
        if not explicit_learning and (not coach or not coach.state.get("active")):
            return self._handle_chat(user_input, "chat")
        
        # 1. Subject Tutor (Assisting the user with a topic)
        if tutor and tutor.should_handle(text_normalized):
            try:
                tutor_response = tutor.handle_input(text_normalized)
                if tutor_response:
                    tutor_meta = tutor.get_last_meta() if tutor else {}
                    log_decision(user_input, intent_type, "subject_tutor", "", "success")
                    self._safe_speak(tutor_response, "calm")
                    return {
                        "response": tutor_response,
                        "action": "subject_tutor",
                        "intent_type": intent_type,
                        "success": True,
                        "sources": tutor_meta.get("sources", []),
                    }
            except Exception as e:
                log_error("SubjectTutor.handle", e)

        # 2. English Coach (Assisting the user with English)
        if coach and coach.should_handle(text_normalized):
            try:
                coach_response = coach.handle_input(text_normalized)
                if coach_response:
                    log_decision(user_input, intent_type, "english_coach", "", "success")
                    self._safe_speak(coach_response, "calm")
                    return {
                        "response": coach_response,
                        "action": "english_coach",
                        "intent_type": intent_type,
                        "success": True,
                    }
            except Exception as e:
                log_error("EnglishCoach.handle", e)
        
        # 3. Learning Fallback - Use SubjectTutor for all educational requests (ChatGPT Buddy Style)
        learning_for_user = (
            any(phrase in text_lower for phrase in [
                "teach me", "help me learn", "lesson", "course", "explain", "study", "learn"
            ])
            and not any(phrase in text_lower for phrase in [
                "remember", "keep in mind", "learn that", "remember that", "note that"
            ])
        )
        if learning_for_user and tutor:
            try:
                # If it doesn't match an explicit start pattern, use it as a follow-up or a simple topic start
                tutor_response = tutor.handle_input(text_normalized)
                if tutor_response:
                    tutor_meta = tutor.get_last_meta()
                    log_decision(user_input, intent_type, "subject_tutor_auto", "", "success")
                    self._safe_speak(tutor_response, "calm")
                    return {
                        "response": tutor_response,
                        "action": "subject_tutor",
                        "intent_type": intent_type,
                        "success": True,
                        "sources": tutor_meta.get("sources", []),
                    }
            except Exception as e:
                log_error("Brain.buddy_tutor_fallback", e)

        # Check if user wants to list/see what they've taught
        if "list lessons" in text_lower or "show lessons" in text_lower or "what did you learn" in text_lower:
            lessons = self.memory.get_lessons()
            if not lessons:
                response = "You haven't taught me anything yet. Say 'remember that...' to teach me something!"
            else:
                lines = ["Here's what you've taught me:"]
                for i, (lesson, category) in enumerate(lessons, 1):
                    lines.append(f"{i}. [{category}] {lesson}")
                response = "\n".join(lines)
            
            log_decision(user_input, intent_type, "list_lessons", "", "success")
            self._safe_speak(response)
            return {
                "response": response,
                "action": "list_lessons",
                "intent_type": intent_type,
                "success": True,
            }
        
        # Check for clear/remove lessons command
        if "forget lessons" in text_lower or "clear lessons" in text_lower or "remove lessons" in text_lower:
            self.memory.clear_lessons()
            response = "I've forgotten all the lessons you taught me."
            log_decision(user_input, intent_type, "clear_lessons", "", "success")
            self._safe_speak(response)
            return {
                "response": response,
                "action": "clear_lessons",
                "intent_type": intent_type,
                "success": True,
            }
        
        # Extract the lesson content from the input
        # Common patterns: "remember that X", "learn that X", "don't forget X", etc.
        lesson_text = ""
        category = "general"
        
        # Try to extract the lesson from common patterns
        patterns_to_try = [
            "remember that ",
            "remember ",
            "learn that ",
            "learn ",
            "don't forget that ",
            "don't forget ",
            "keep in mind that ",
            "keep in mind ",
            "memorize that ",
            "memorize ",
            "i want you to know that ",
            "i want you to know ",
            "note that ",
            "note: ",
            "important: ",
            "this is important: ",
            "understand that ",
            "know that ",
            "train that ",
            "train ",
        ]
        
        for pattern in patterns_to_try:
            if pattern in text_lower:
                idx = text_lower.index(pattern)
                lesson_text = user_input[idx + len(pattern):].strip()
                if lesson_text:
                    break
        
        # If no pattern matched, use the whole input as the lesson
        if not lesson_text:
            lesson_text = user_input.strip()
        
        # Detect category from the lesson
        if any(w in text_lower for w in ["important", "critical", "must", "never", "always"]):
            category = "important"
        elif any(w in text_lower for w in ["prefer", "like", "don't like", "hate", "love"]):
            category = "preference"
        elif any(w in text_lower for w in ["every day", "daily", "routine", "habit"]):
            category = "habit"
        elif any(w in text_lower for w in ["fact", "true", "actually"]):
            category = "fact"
        
        # Store the lesson
        if lesson_text:
            success = self.memory.add_lesson(lesson_text, category)
            if success:
                response = f"Got it! I've learned: '{lesson_text}'. I'll keep this in mind."
                log_decision(user_input, intent_type, "learn", lesson_text[:30], "success")
            else:
                response = "I couldn't save that lesson. There might be sensitive data in it."
                log_decision(user_input, intent_type, "learn", lesson_text[:30], "failure")
        else:
            response = "I'm not sure what you'd like me to learn. Try saying 'remember that...' followed by what you want me to know."
            log_decision(user_input, intent_type, "learn", "", "failure")
        
        self._safe_speak(response)
        
        return {
            "response": response,
            "action": "learn",
            "intent_type": intent_type,
            "success": bool(lesson_text),
        }

    # --- Execution Engine ---

    def _execute_single(self, action: str, target: str, user_input: str,
                        intent_type: str) -> dict:
        """Execute a single tool action with fault tolerance."""
        tool_fn = self._tools.get(action)
        if not tool_fn:
            log_decision(user_input, intent_type, action, target, "failure",
                          "Tool not registered")
            return self._handle_chat(user_input, "chat")

        try:
            # Execute the tool
            result = tool_fn(target)

            # Interpret result
            if isinstance(result, tuple):
                success, message = result[0], result[1] if len(result) > 1 else ""
            elif result is None:
                success, message = True, ""
            elif isinstance(result, bool):
                success, message = result, ""
            else:
                success, message = True, str(result)

            # Track command frequency for learning
            if success:
                self.memory.track_command(action)

            log_decision(user_input, intent_type, action, target,
                          "success" if success else "failure", message)

            # Speak tool result (brain owns voice output)
            if message and message != "__EXIT__":
                self._safe_speak(message)

            # UI updates removed (server deleted)

            return {
                "response": message,
                "action": action,
                "intent_type": intent_type,
                "success": success,
            }

        except Exception as e:
            log_error(f"Tool.{action}", e, f"target='{target}'")
            log_decision(user_input, intent_type, action, target, "failure", str(e))
            error_msg = f"I attempted to {action.replace('_', ' ')} but encountered an issue. Shall I try again?"
            self._safe_speak(error_msg)
            return {
                "response": error_msg,
                "action": action,
                "intent_type": intent_type,
                "success": False,
            }

    def _execute_plan(self, plan: list, user_input: str, intent_type: str) -> dict:
        """Execute a multi-step plan from the LLM planner."""
        results = []
        all_success = True

        for i, step in enumerate(plan):
            action = step.get("action", "unknown")
            target = step.get("target", "")

            if action in self._tools:
                # Check if step is dangerous
                if action in _DANGEROUS_ACTIONS and self._is_dangerous_context(action, target):
                    log_decision(user_input, intent_type, action, target, "blocked",
                                  "Dangerous action in plan requires confirmation")
                    continue

                step_result = self._execute_single(action, target, user_input, intent_type)
                results.append(step_result)
                if not step_result.get("success"):
                    all_success = False

                # Small delay between steps for system to catch up
                if i < len(plan) - 1:
                    time.sleep(0.3)
            else:
                log_decision(user_input, intent_type, action, target, "skipped",
                              "Action not in registered tools")

        combined_response = "; ".join(
            r.get("response", "") for r in results if r.get("response")
        )

        return {
            "response": combined_response or "Done.",
            "action": "plan_execution",
            "intent_type": intent_type,
            "success": all_success,
        }

    # --- Confirmation Layer ---

    def _request_confirmation(self, action: str, target: str, user_input: str,
                               intent_type: str) -> dict:
        """Store pending action and ask user for confirmation."""
        self._confirmation_pending = {
            "action": action,
            "target": target,
            "user_input": user_input,
            "intent_type": intent_type,
            "timestamp": time.time(),
        }

        action_desc = action.replace("_", " ").title()
        confirm_msg = f"I am about to {action_desc}: '{target}'. Shall I proceed? (yes/no)"

        log_decision(user_input, intent_type, action, target, "awaiting_confirmation")

        # UI updates removed (server deleted)

        self._safe_speak(confirm_msg)

        return {
            "response": confirm_msg,
            "action": "confirmation_request",
            "intent_type": intent_type,
            "success": True,
        }

    def _handle_confirmation(self, user_input: str) -> dict:
        """Process user's yes/no response to a pending confirmation."""
        pending = self._confirmation_pending
        self._confirmation_pending = None  # Clear regardless

        # Check for timeout (60 seconds)
        if time.time() - pending["timestamp"] > 60:
            msg = "Confirmation timed out. Please give the command again."
            self._safe_speak(msg)
            log_decision(pending["user_input"], pending["intent_type"],
                          pending["action"], pending["target"], "timeout")
            return {"response": msg, "action": "timeout", "intent_type": "system", "success": False}

        # More precise affirmative/negative detection using word boundaries
        text_lower = user_input.lower().strip()
        words = set(text_lower.split())
        
        # Exact matches and word-boundary matches
        affirmatives = {"yes", "yeah", "yep", "sure", "okay", "ok", "do it", "go ahead",
                        "proceed", "confirm", "y", "affirmative", "please", "yes please"}
        negatives = {"no", "nah", "nope", "cancel", "stop", "don't", "abort", "n", "negative", 
                    "not now", "maybe", "later"}

        # Check exact match first
        if text_lower in affirmatives:
            self._safe_speak("Understood. Proceeding.")
            return self._execute_single(
                pending["action"], pending["target"],
                pending["user_input"], pending["intent_type"]
            )
        elif text_lower in negatives:
            msg = "Cancelled. The action was not performed."
            self._safe_speak(msg)
            log_decision(pending["user_input"], pending["intent_type"],
                          pending["action"], pending["target"], "cancelled")
            return {"response": msg, "action": "cancelled", "intent_type": "system", "success": True}
        
        # Check if any word in the input is an affirmative/negative
        # But be more careful - require standalone word matches
        has_affirmative = any(w in affirmatives for w in words)
        has_negative = any(w in negatives for w in words)
        
        if has_affirmative and not has_negative:
            self._safe_speak("Understood. Proceeding.")
            return self._execute_single(
                pending["action"], pending["target"],
                pending["user_input"], pending["intent_type"]
            )
        elif has_negative:
            msg = "Cancelled. The action was not performed."
            self._safe_speak(msg)
            log_decision(pending["user_input"], pending["intent_type"],
                          pending["action"], pending["target"], "cancelled")
            return {"response": msg, "action": "cancelled", "intent_type": "system", "success": True}
        else:
            # Ambiguous response — cancel to be safe
            msg = "I didn't get a clear yes or no, so I've cancelled the action to be safe."
            self._safe_speak(msg)
            log_decision(pending["user_input"], pending["intent_type"],
                          pending["action"], pending["target"], "cancelled",
                          "Ambiguous confirmation response")
            return {"response": msg, "action": "cancelled", "intent_type": "system", "success": True}

    # --- Safety & Decision Tree ---

    def _is_dangerous_context(self, action: str, target: str) -> bool:
        """
        Decision tree: determine if an action+target combination is dangerous.
        Returns True if confirmation should be required.
        """
        # System actions are always dangerous
        if action in _SYSTEM_ACTIONS:
            return True

        # File write operations
        if action in ("write_to_file", "create_file"):
            # Writing to system directories is dangerous
            if target and any(d in target.lower() for d in ["system32", "windows", "program files"]):
                return True
            return True  # All file writes require confirmation

        # Key presses that could be destructive
        if action == "press_key":
            dangerous_keys = {"alt+f4", "ctrl+w", "delete", "ctrl+shift+delete",
                              "win+l", "ctrl+alt+delete"}
            if target and target.lower().strip() in dangerous_keys:
                return True

        return False

    # --- Helpers ---

    def _safe_plan(self, user_input: str) -> list:
        """Safely call the LLM planner with validation."""
        if not self._llm_plan:
            return []
        try:
            plan = self._llm_plan(user_input)
            if not isinstance(plan, list):
                return []
            # Validate plan structure
            validated = []
            for step in plan:
                if isinstance(step, dict) and "action" in step:
                    validated.append({
                        "action": str(step.get("action", "")),
                        "target": str(step.get("target", "")),
                    })
            return validated
        except Exception as e:
            log_error("LLM.plan_actions", e, f"input='{user_input[:40]}'")
            return []

    def _safe_speak(self, text: str, mood: str = "neutral"):
        """Safely call the voice engine with the given mood."""
        if not (self._speak_fn and text):
            return

        try:
            tts_text = str(text)
            # Remove GUI/source markers from spoken output.
            if "[[BKR_SOURCES]]" in tts_text:
                tts_text = tts_text.split("[[BKR_SOURCES]]", 1)[0]

            # Strip outlines/lists from TTS ("Plan: 1. ... | 2. ...") while keeping the
            # full text for display.
            cleaned_lines: list[str] = []
            removed_list_lines = False
            for raw_line in tts_text.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                if line.lower().startswith("plan:"):
                    removed_list_lines = True
                    continue
                if re.match(r"^\d+\.\s+", line):
                    removed_list_lines = True
                    continue
                if line.startswith(("- ", "* ")):
                    removed_list_lines = True
                    continue
                cleaned_lines.append(line)

            tts_text = " ".join(cleaned_lines)
            tts_text = re.sub(r"\s+", " ", tts_text).strip()

            # If we stripped everything (e.g. response was only a list), speak a short cue
            # instead of going silent.
            if not tts_text and removed_list_lines:
                tts_text = "I displayed the details on screen."

            if tts_text:
                # Speak once per response to avoid overlapping/fragmented audio.
                self._speak_fn(tts_text, mood)
        except Exception as e:
            log_error("Voice.speak", e)

    def _detect_mood(self, user_input: str) -> str:
        """Quick mood detection from input text."""
        text_lower = user_input.lower()
        if any(w in text_lower for w in ["sad", "depressed", "down", "lonely", "hurt"]):
            return "concerned"
        if any(w in text_lower for w in ["angry", "frustrated", "annoying", "terrible"]):
            return "concerned"
        if any(w in text_lower for w in ["excited", "amazing", "awesome", "great", "wonderful"]):
            return "happy"
        if any(w in text_lower for w in ["proud", "achieved", "succeeded", "won"]):
            return "proud"
        if any(w in text_lower for w in ["worried", "anxious", "nervous", "stress"]):
            return "concerned"
        return "calm"

    # --- Auto-Detect User Info ---

    def _try_extract_user_info(self, text: str):
        """Detect and store user name and preferences from conversation."""
        text_lower = text.lower().strip()

        # Detect name: "my name is X", "call me X", "I'm X", "I am X"
        name_patterns = [
            r"(?:my name is|i'm|i am|call me)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                if len(name) > 1 and len(name) < 30:
                    self.memory.set_user_name(name)
                    log_event("Auto-detected user name", f"name={name}")
                break

        # Detect user role for adaptive teaching depth.
        role_patterns = [
            r"\bi am (?:a|an)\s+(farmer|student|professor|doctor|researcher|academic|teacher|engineer)\b",
            r"\bmy role is\s+(farmer|student|professor|doctor|researcher|academic|teacher|engineer)\b",
            r"\bi work as (?:a|an)\s+(farmer|teacher|doctor|professor|engineer)\b",
        ]
        for pattern in role_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                role = match.group(1).strip().lower()
                self.memory.set_user_role(role)
                log_event("Auto-detected user role", f"role={role}")
                break

        # Detect voice preference
        if "male voice" in text_lower or "deep voice" in text_lower:
            self.memory.set_voice_preference("gender", "male")
            log_event("Auto-detected voice preference", "male")
        elif "female voice" in text_lower:
            self.memory.set_voice_preference("gender", "female")
            log_event("Auto-detected voice preference", "female")

    # --- Status ---

    @property
    def has_pending_confirmation(self):
        return self._confirmation_pending is not None
