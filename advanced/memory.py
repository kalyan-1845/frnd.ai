"""
Memory System — Short-term + Long-term memory with safety filtering.

Short-term: in-memory dict, resets every session.
Long-term: SQLite-persisted via core.database (user profile, preferences, commands, projects).
"""
import re
import config
from core.database import db
from datetime import datetime


# Patterns that indicate sensitive data — never store these
_SENSITIVE_PATTERNS = [
    re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'),  # Credit card
    re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),                         # SSN
    re.compile(r'(?i)\b(?:password|passwd|pwd)\s*[:=]\s*\S+'),     # password=xxx
    re.compile(r'(?i)\b(?:api[_\s]?key|secret[_\s]?key|token)\s*[:=]\s*\S+'),  # API keys
    re.compile(r'(?i)\b(?:bearer)\s+\S{20,}'),                    # Bearer tokens
]


def _is_sensitive(value: str) -> bool:
    """Return True if the value looks like sensitive data."""
    if not isinstance(value, str):
        return False
    for pattern in _SENSITIVE_PATTERNS:
        if pattern.search(value):
            return True
    return False


class MemorySystem:
    """
    Dual-layer memory: short-term (session) + long-term (persistent).
    """

    def __init__(self):
        # Short-term memory — resets when this instance is created (i.e. per session)
        self._short_term = {}
        self._session_start = datetime.now().isoformat()

    # ------------------------------------------------------------------ #
    #  Short-Term Memory (in-memory, session-scoped)
    # ------------------------------------------------------------------ #

    def set_short_term(self, key: str, value):
        """Store a value in short-term (session) memory."""
        self._short_term[key] = value

    def get_short_term(self, key: str, default=None):
        """Retrieve a value from short-term memory."""
        return self._short_term.get(key, default)

    def clear_short_term(self):
        """Reset all short-term memory."""
        self._short_term.clear()

    def get_short_term_summary(self) -> dict:
        """Return a copy of all short-term entries."""
        return dict(self._short_term)

    # ------------------------------------------------------------------ #
    #  Long-Term Memory — User Profile
    # ------------------------------------------------------------------ #

    def get_user_name(self) -> str:
        try:
            name = db.get_profile("user_name")
            return name if name else "friend"
        except Exception as e:
            print(f"[Memory Error] get_user_name: {e}")
            return "friend"

    def set_user_name(self, name: str) -> bool:
        if _is_sensitive(name):
            print("[Memory] Blocked: name looks like sensitive data.")
            return False
        try:
            return db.set_profile("user_name", name)
        except Exception as e:
            print(f"[Memory Error] set_user_name: {e}")
            return False

    def get_user_role(self) -> str:
        try:
            role = db.get_profile("user_role")
            if role:
                return str(role)
            return str(getattr(config, "DEFAULT_USER_ROLE", "student"))
        except Exception:
            return "student"

    def set_user_role(self, role: str) -> bool:
        if _is_sensitive(role):
            return False
        role_norm = (role or "").strip().lower()
        if not role_norm:
            return False
        try:
            return db.set_profile("user_role", role_norm)
        except Exception as e:
            print(f"[Memory Error] set_user_role: {e}")
            return False

    # ------------------------------------------------------------------ #
    #  Long-Term Memory — Voice Preferences
    # ------------------------------------------------------------------ #

    def set_voice_preference(self, key: str, value: str) -> bool:
        """Store a voice preference (gender, speed, wake_word, etc.)."""
        if _is_sensitive(value):
            return False
        try:
            return db.set_profile(f"voice_{key}", value)
        except Exception as e:
            print(f"[Memory Error] set_voice_preference: {e}")
            return False

    def get_voice_preference(self, key: str, default=None):
        """Retrieve a voice preference."""
        try:
            val = db.get_profile(f"voice_{key}")
            return val if val is not None else default
        except Exception as e:
            print(f"[Memory Error] get_voice_preference: {e}")
            return default

    # ------------------------------------------------------------------ #
    #  Long-Term Memory — Preferences (generic key-value)
    # ------------------------------------------------------------------ #

    def store_preference(self, key: str, value: str) -> bool:
        """Store any user preference in long-term memory."""
        if _is_sensitive(value):
            print(f"[Memory] Blocked sensitive data for key '{key}'.")
            return False
        try:
            return db.set_profile(key, value)
        except Exception as e:
            print(f"[Memory Error] store_preference: {e}")
            return False

    def get_preference(self, key: str, default=None):
        """Retrieve a user preference."""
        try:
            val = db.get_profile(key)
            return val if val is not None else default
        except Exception as e:
            print(f"[Memory Error] get_preference: {e}")
            return default

    # ------------------------------------------------------------------ #
    #  Long-Term Memory — Command Frequency
    # ------------------------------------------------------------------ #

    def track_command(self, command: str):
        """Increment the usage counter for a command."""
        try:
            db.increment_command(command)
        except Exception as e:
            print(f"[Memory Error] track_command: {e}")

    def get_frequent_commands(self, limit: int = 5) -> list:
        """Return top N most-used commands as [(command, count), ...]."""
        try:
            return db.get_top_commands(limit)
        except Exception as e:
            print(f"[Memory Error] get_frequent_commands: {e}")
            return []

    # ------------------------------------------------------------------ #
    #  Long-Term Memory — Project Context
    # ------------------------------------------------------------------ #

    def store_project_context(self, key: str, value: str) -> bool:
        if _is_sensitive(value):
            return False
        try:
            return db.set_project_context(key, value)
        except Exception as e:
            print(f"[Memory Error] store_project_context: {e}")
            return False

    def get_project_context(self, key: str, default=None):
        try:
            val = db.get_project_context(key)
            return val if val is not None else default
        except Exception as e:
            print(f"[Memory Error] get_project_context: {e}")
            return default

    def get_all_project_context(self) -> dict:
        try:
            return db.get_all_project_context()
        except Exception as e:
            print(f"[Memory Error] get_all_project_context: {e}")
            return {}

    # ------------------------------------------------------------------ #
    #  Long-Term Memory — Goals & Facts (category-based)
    # ------------------------------------------------------------------ #

    def add_goal(self, goal: str) -> bool:
        if _is_sensitive(goal):
            return False
        try:
            db.add_memory("goal", goal)
            return True
        except Exception as e:
            print(f"[Memory Error] add_goal: {e}")
            return False

    def get_goals(self) -> list:
        try:
            return db.get_memories("goal")
        except Exception as e:
            print(f"[Memory Error] get_goals: {e}")
            return []

    # ------------------------------------------------------------------ #
    #  Learning System — Lessons & Facts (NEW)
    # ------------------------------------------------------------------ #

    def add_lesson(self, lesson: str, category: str = "general") -> bool:
        """
        Add a lesson/fact that the user wants the assistant to remember.
        Categories: general, fact, preference, habit, important
        """
        if _is_sensitive(lesson):
            print("[Memory] Blocked: lesson looks like sensitive data.")
            return False
        try:
            # Store with timestamp for context
            import json
            lesson_data = json.dumps({"lesson": lesson, "category": category})
            db.add_memory("lesson", lesson_data)
            return True
        except Exception as e:
            print(f"[Memory Error] add_lesson: {e}")
            return False

    def get_lessons(self, category: str = None) -> list:
        """
        Get all lessons, optionally filtered by category.
        Returns list of tuples: [(lesson_text, category), ...]
        """
        try:
            import json
            all_lessons = db.get_memories("lesson")
            result = []
            for lesson_data in all_lessons:
                try:
                    data = json.loads(lesson_data)
                    if category is None or data.get("category") == category:
                        result.append((data.get("lesson", ""), data.get("category", "general")))
                except (json.JSONDecodeError, AttributeError):
                    # Handle legacy format (plain text lessons)
                    if category is None or category == "general":
                        result.append((lesson_data, "general"))
            return result
        except Exception as e:
            print(f"[Memory Error] get_lessons: {e}")
            return []

    def get_all_lessons_text(self) -> str:
        """Get all lessons as a formatted text string for LLM context."""
        lessons = self.get_lessons()
        if not lessons:
            return ""
        
        lines = ["LESSONS I'VE LEARNED:"]
        for i, (lesson, category) in enumerate(lessons, 1):
            lines.append(f"{i}. [{category}] {lesson}")
        
        return "\n".join(lines)

    def delete_lesson(self, lesson_text: str) -> bool:
        """Delete a specific lesson by its text."""
        try:
            db.delete_memory("lesson", lesson_text)
            return True
        except Exception as e:
            print(f"[Memory Error] delete_lesson: {e}")
            return False

    def clear_lessons(self) -> bool:
        """Clear all learned lessons."""
        try:
            db.delete_memory("lesson")
            return True
        except Exception as e:
            print(f"[Memory Error] clear_lessons: {e}")
            return False

    def update_mood(self, mood: str, trigger_text: str = ""):
        try:
            db.add_memory("mood_log", f"Mood: {mood}, Trigger: {trigger_text}")
        except Exception as e:
            print(f"[Memory Error] update_mood: {e}")

    # ------------------------------------------------------------------ #
    #  Check-in Status
    # ------------------------------------------------------------------ #

    def set_check_in_status(self, has_checked_in: bool):
        try:
            if has_checked_in:
                today = datetime.now().strftime("%Y-%m-%d")
                db.set_profile("last_check_in_date", today)
        except Exception as e:
            print(f"[Memory Error] set_check_in_status: {e}")

    def get_check_in_status(self) -> bool:
        try:
            last_date = db.get_profile("last_check_in_date")
            if not last_date:
                return False
            today = datetime.now().strftime("%Y-%m-%d")
            return last_date == today
        except Exception as e:
            print(f"[Memory Error] get_check_in_status: {e}")
            return False

    # ------------------------------------------------------------------ #
    #  Memory Control — Reset & Selective Deletion
    # ------------------------------------------------------------------ #

    def reset_all_memory(self):
        """Wipe everything: short-term + all long-term tables."""
        self._short_term.clear()
        try:
            db.clear_all_memories()
            print("[Memory] Full memory reset complete.")
            return True
        except Exception as e:
            print(f"[Memory Error] reset_all_memory: {e}")
            return False

    def forget(self, category: str, key: str = None):
        """
        Selective deletion.
        - forget("goals") → deletes all goals
        - forget("profile", "user_name") → deletes a specific profile key
        - forget("project") → clears all project context
        - forget("commands") → clears command frequency
        - forget("short_term") → clears session memory
        """
        try:
            cat = category.lower().strip()
            if cat in ("goal", "goals"):
                if key:
                    db.delete_memory("goal", key)
                else:
                    db.delete_memory("goal")
                return True
            elif cat == "profile":
                if key:
                    db.delete_profile(key)
                return True
            elif cat in ("project", "projects"):
                db.clear_project_context()
                return True
            elif cat in ("command", "commands"):
                db.clear_all_memories()  # This is a bit heavy; ideally clear only commands
                return True
            elif cat == "short_term":
                self._short_term.clear()
                return True
            elif cat == "conversations":
                db.clear_conversations()
                return True
            else:
                # Try as a memory category
                db.delete_memory(cat)
                return True
        except Exception as e:
            print(f"[Memory Error] forget: {e}")
            return False

    # ------------------------------------------------------------------ #
    #  Memory Summary (for display / debugging)
    # ------------------------------------------------------------------ #

    def get_memory_summary(self) -> str:
        """Return a human-readable summary of all stored memory."""
        lines = ["--- Memory Summary ---"]

        # User profile
        try:
            profile = db.get_all_profile()
            if profile:
                lines.append("Profile:")
                for k, v in profile.items():
                    lines.append(f"  {k}: {v}")
        except Exception:
            pass

        # Goals
        try:
            goals = self.get_goals()
            if goals:
                lines.append(f"Goals: {', '.join(goals[:5])}")
        except Exception:
            pass

        # Top commands
        try:
            cmds = self.get_frequent_commands(5)
            if cmds:
                lines.append("Frequent commands:")
                for cmd, count in cmds:
                    lines.append(f"  {cmd}: {count}x")
        except Exception:
            pass

        # Project context
        try:
            ctx = self.get_all_project_context()
            if ctx:
                lines.append("Project context:")
                for k, v in ctx.items():
                    lines.append(f"  {k}: {v[:60]}")
        except Exception:
            pass

        # Short-term
        if self._short_term:
            lines.append(f"Session memory: {len(self._short_term)} entries")

        if len(lines) == 1:
            lines.append("  (empty)")

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  Context Builder (for LLM injection)
    # ------------------------------------------------------------------ #

    def get_relevant_context(self, user_input: str = "") -> str:
        """
        Build a concise context string for the LLM, containing only
        relevant long-term memory. Avoids overloading the prompt.
        """
        parts = []

        # User name
        name = self.get_user_name()
        if name and name != "friend":
            parts.append(f"User's name: {name}")

        role = self.get_user_role()
        if role:
            parts.append(f"User profile role: {role}")

        # Goals (max 3)
        goals = self.get_goals()
        if goals:
            parts.append(f"User goals: {', '.join(goals[:3])}")

        # Learned lessons (max 5 most recent)
        lessons = self.get_lessons()
        if lessons:
            lesson_texts = [f"[{cat}] {text}" for text, cat in lessons[:5]]
            parts.append(f"Learned lessons: {'; '.join(lesson_texts)}")

        # Project context (if any)
        ctx = self.get_all_project_context()
        if ctx:
            ctx_str = "; ".join(f"{k}: {v[:40]}" for k, v in list(ctx.items())[:3])
            parts.append(f"Project context: {ctx_str}")

        # Frequent commands (so LLM can anticipate)
        cmds = self.get_frequent_commands(3)
        if cmds:
            cmd_str = ", ".join(f"{c}" for c, _ in cmds)
            parts.append(f"Frequently used: {cmd_str}")

        # Voice preference
        voice_gender = self.get_voice_preference("gender")
        if voice_gender:
            parts.append(f"Voice preference: {voice_gender}")

        if not parts:
            return ""

        return "USER CONTEXT:\n" + "\n".join(parts)
