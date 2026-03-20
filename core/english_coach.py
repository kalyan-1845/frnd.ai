"""
English coaching engine for step-by-step guided learning.

This module keeps a persistent curriculum state, asks practice questions,
grades quick answers, and auto-advances lessons when configured.
"""
from __future__ import annotations

import re
from datetime import datetime

import config
from core.logger import log_error, log_event


class EnglishCoach:
    """Persistent English learning workflow manager."""

    PROFILE_KEY = "english_coach_state_v1"

    LESSONS = [
        {
            "id": "intro",
            "title": "Clear Introductions",
            "concept": "Use a simple structure: name + role + goal.",
            "steps": [
                "Start with your name: 'My name is ...'",
                "Add your role: 'I am a ...'",
                "Add your goal: 'I want to improve ...'",
            ],
            "example": "My name is Rahul. I am a software student. I want to improve my spoken English.",
            "question": "Write 2-3 sentences to introduce yourself clearly.",
            "expected": ["my name is", "i am", "i want to"],
            "hint": "Include all 3 parts: name, role, goal.",
            "homework": "Record your introduction voice note 3 times.",
        },
        {
            "id": "present_simple",
            "title": "Present Simple for Daily Routine",
            "concept": "Use present simple for habits and repeated actions.",
            "steps": [
                "Use subject + base verb: I study, you practice, we learn.",
                "For he/she/it, add s/es: she studies, he works.",
                "Use time words: every day, usually, often.",
            ],
            "example": "I practice English every day. She reads one article every morning.",
            "question": "Write 2 sentences about your daily routine using present simple.",
            "expected": ["every day", "i", "usually"],
            "hint": "Mention routine words like every day, usually, often.",
            "homework": "Write your routine in 5 simple present sentences.",
        },
        {
            "id": "past_simple",
            "title": "Past Simple for Yesterday",
            "concept": "Use past simple to describe completed past actions.",
            "steps": [
                "Use past verb form: worked, studied, watched.",
                "Use did for negatives/questions: I did not go, did you read?",
                "Use clear time: yesterday, last night, last week.",
            ],
            "example": "Yesterday I studied grammar and watched one interview video.",
            "question": "Write 2 sentences about what you did yesterday.",
            "expected": ["yesterday", "i", "ed"],
            "hint": "Include 'yesterday' and a past action.",
            "homework": "Write a short 4-line diary entry about yesterday.",
        },
        {
            "id": "questions",
            "title": "Asking Better Questions",
            "concept": "Use WH words to ask clear and useful questions.",
            "steps": [
                "Choose the right starter: what, why, when, where, how.",
                "Keep one clear intent per question.",
                "Add context: 'for interview', 'for grammar', 'for speaking'.",
            ],
            "example": "How can I improve fluency for job interviews in 30 days?",
            "question": "Write one clear question about improving your English.",
            "expected": ["how", "improve", "english"],
            "hint": "Start with How/What and include your goal.",
            "homework": "Prepare 5 questions to ask your AI teacher this week.",
        },
        {
            "id": "sentence_building",
            "title": "Sentence Building with Connectors",
            "concept": "Use connectors to make sentences natural and complete.",
            "steps": [
                "Use because for reason.",
                "Use but for contrast.",
                "Use so for result.",
            ],
            "example": "I practice every morning because I want to speak confidently.",
            "question": "Write one sentence using 'because' and one sentence using 'but'.",
            "expected": ["because", "but"],
            "hint": "Two sentences: one with because, one with but.",
            "homework": "Write 6 connected sentences about your study plan.",
        },
        {
            "id": "speaking_clarity",
            "title": "Speak Clearly and Confidently",
            "concept": "Clarity improves when you use short, complete sentences.",
            "steps": [
                "Use one idea per sentence.",
                "Pause after each sentence.",
                "Avoid filler words like 'uh', 'like', 'you know'.",
            ],
            "example": "Today I practiced for twenty minutes. I focused on pronunciation and pace.",
            "question": "Write 2 short sentences about what you will practice today.",
            "expected": ["today", "i will", "practice"],
            "hint": "Use short complete sentences with one idea each.",
            "homework": "Read one paragraph aloud slowly for 5 minutes.",
        },
        {
            "id": "email_writing",
            "title": "Professional Email Basics",
            "concept": "Professional writing needs a greeting, purpose, and clear close.",
            "steps": [
                "Start politely: Dear..., Hello...",
                "State purpose in one sentence.",
                "Close with action + thanks.",
            ],
            "example": "Hello Sir, I am writing to request an interview slot for Friday. Thank you for your time.",
            "question": "Write a 3-line email requesting a meeting.",
            "expected": ["hello", "request", "thank"],
            "hint": "Include greeting, request, and thanks.",
            "homework": "Draft 2 short professional emails and review grammar.",
        },
        {
            "id": "interview",
            "title": "Interview Answers",
            "concept": "Use concise structure for interview responses.",
            "steps": [
                "Start with direct answer.",
                "Add one specific example.",
                "End with what you learned.",
            ],
            "example": "I solved a deployment issue by debugging logs and fixing environment variables. I learned to verify configuration first.",
            "question": "Answer this: 'Tell me about a challenge you solved.'",
            "expected": ["i", "challenge", "learned"],
            "hint": "Use answer + example + learning.",
            "homework": "Prepare 3 interview answers and practice aloud.",
        },
        {
            "id": "review",
            "title": "Weekly Review and Reinforcement",
            "concept": "Review fixes weak spots and builds consistency.",
            "steps": [
                "Check one grammar topic from the week.",
                "Speak for 2 minutes about your week.",
                "Write 5 sentences with no grammar mistakes.",
            ],
            "example": "This week I improved sentence clarity and reduced grammar mistakes.",
            "question": "Write 3 lines reviewing your English progress this week.",
            "expected": ["this week", "improved", "i"],
            "hint": "Mention progress and one area to improve.",
            "homework": "Create a simple weekly score: grammar, speaking, confidence.",
        },
    ]

    START_KEYWORDS = (
        "start english",
        "begin english",
        "start english course",
        "start english coach",
        "english coach",
        "teach me english",
    )
    NEXT_KEYWORDS = ("next lesson", "continue english lesson", "continue course", "start english lesson")
    STATUS_KEYWORDS = ("english progress", "english status", "coach status", "course status")
    DAILY_KEYWORDS = ("english daily session", "today english plan", "english study plan", "daily english plan", "today english lesson")
    QUIZ_KEYWORDS = ("english quiz", "test my english", "english practice question", "practice english")
    RESET_KEYWORDS = ("reset english", "start over", "restart course", "reset coach", "stop english", "exit coach", "stop coach")

    ANSWER_PREFIXES = (
        "answer:",
        "my answer is",
        "i answer",
        "the answer is",
    )

    def __init__(self, memory_system):
        self.memory = memory_system
        self.state = self._load_state()

    def _default_state(self) -> dict:
        return {
            "enabled": bool(getattr(config, "ENGLISH_COACH_ENABLED", True)),
            "started": False,
            "current_lesson_index": 0,
            "awaiting_answer": False,
            "current_question": "",
            "expected": [],
            "hint": "",
            "sessions_completed": 0,
            "lessons_completed": 0,
            "answers_total": 0,
            "answers_correct": 0,
            "daily_target_minutes": int(getattr(config, "ENGLISH_COACH_DAILY_TARGET_MINUTES", 30)),
            "last_session_date": "",
            "chat_turn_count": 0,
            "last_nudge_turn": 0,
        }

    def _load_state(self) -> dict:
        state = self._default_state()
        try:
            raw = self.memory.get_preference(self.PROFILE_KEY)
            if raw:
                import json

                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    state.update(loaded)
        except Exception as err:
            log_error("EnglishCoach.load_state", err)
        return state

    def _save_state(self) -> None:
        try:
            import json

            self.memory.store_preference(self.PROFILE_KEY, json.dumps(self.state))
        except Exception as err:
            log_error("EnglishCoach.save_state", err)

    def _norm(self, text: str) -> str:
        return " ".join((text or "").lower().strip().split())

    def _contains_any(self, text: str, keywords: tuple[str, ...]) -> bool:
        return any(k in text for k in keywords)

    def is_active(self) -> bool:
        return bool(self.state.get("enabled", True))

    def should_handle(self, user_input: str) -> bool:
        text = self._norm(user_input)
        if self._contains_any(text, self.RESET_KEYWORDS + self.START_KEYWORDS + self.NEXT_KEYWORDS + self.STATUS_KEYWORDS + self.DAILY_KEYWORDS + self.QUIZ_KEYWORDS):
            return True
            
        # Only handle if there's an active lesson session
        if not self.state.get("started"):
            return False
        if not self.state.get("awaiting_answer"):
            return False
            
        # Require explicit answer prefix to prevent taking over normal chat
        for prefix in self.ANSWER_PREFIXES:
            if text.startswith(prefix):
                return True
                
        return False

    def handle_input(self, user_input: str) -> str | None:
        text = self._norm(user_input)
        if not text:
            return None

        if self._contains_any(text, self.RESET_KEYWORDS):
            if "stop" in text or "exit" in text:
                self.state["started"] = False
                self.state["awaiting_answer"] = False
                self._save_state()
                return "English Coach session stopped. You are back in standard chat mode."
            return self.start_course(reset=True)

        if self._contains_any(text, self.START_KEYWORDS):
            return self.start_course(reset=False)

        if "set daily target" in text:
            return self._set_daily_target(text)

        if self._contains_any(text, self.STATUS_KEYWORDS):
            return self.get_progress_report()

        if self._contains_any(text, self.DAILY_KEYWORDS):
            return self.get_daily_session_plan()

        if self._contains_any(text, self.NEXT_KEYWORDS):
            return self.next_lesson(auto_requested=True)

        if "repeat lesson" in text or "repeat this lesson" in text:
            return self.repeat_lesson()

        if self._contains_any(text, self.QUIZ_KEYWORDS):
            return self.ask_practice_question()

        if self.state.get("awaiting_answer"):
            answer = self._extract_answer(user_input)
            return self.grade_answer(answer)

        return None

    def start_course(self, reset: bool = False) -> str:
        if reset:
            self.state = self._default_state()
            self.state["enabled"] = True
            self.state["started"] = True
            self._save_state()
            log_event("EnglishCoach", "Course reset")
            intro = "English Coach has been reset and restarted."
        else:
            self.state["enabled"] = True
            self.state["started"] = True
            self._save_state()
            log_event("EnglishCoach", "Course started")
            intro = "English Coach is now active."

        lesson_block = self._render_lesson(self.state["current_lesson_index"], include_practice=True)
        return (
            f"{intro}\n\n"
            "I will teach you step by step automatically: concept, example, and practice.\n\n"
            f"{lesson_block}\n\n"
            "Reply with your answer, and I will grade it instantly."
        )

    def next_lesson(self, auto_requested: bool = False) -> str:
        if not self.state.get("started"):
            return self.start_course(reset=False)

        idx = int(self.state.get("current_lesson_index", 0))
        next_idx = idx + 1
        if next_idx >= len(self.LESSONS):
            next_idx = 0
            self.state["sessions_completed"] = int(self.state.get("sessions_completed", 0)) + 1

        self.state["current_lesson_index"] = next_idx
        self.state["awaiting_answer"] = False
        self._save_state()

        prefix = "Next lesson loaded." if auto_requested else "Auto-advancing to the next lesson."
        lesson_block = self._render_lesson(next_idx, include_practice=True)
        return f"{prefix}\n\n{lesson_block}"

    def repeat_lesson(self) -> str:
        idx = int(self.state.get("current_lesson_index", 0))
        lesson_block = self._render_lesson(idx, include_practice=True)
        return f"Repeating your current lesson.\n\n{lesson_block}"

    def ask_practice_question(self) -> str:
        idx = int(self.state.get("current_lesson_index", 0))
        lesson = self.LESSONS[idx]
        self.state["awaiting_answer"] = True
        self.state["current_question"] = lesson["question"]
        self.state["expected"] = list(lesson["expected"])
        self.state["hint"] = lesson["hint"]
        self._save_state()
        return (
            f"Practice question:\n{lesson['question']}\n\n"
            "Reply with `answer: ...` and I will evaluate it."
        )

    def _extract_answer(self, raw_text: str) -> str:
        text = (raw_text or "").strip()
        lower = text.lower()
        for prefix in self.ANSWER_PREFIXES:
            if lower.startswith(prefix):
                return text[len(prefix) :].strip()
        return text

    def _match_score(self, answer: str, expected: list[str]) -> float:
        if not expected:
            return 0.0
        answer_l = (answer or "").lower()
        hits = 0
        for marker in expected:
            marker_l = marker.lower().strip()
            if not marker_l:
                continue
            if marker_l in answer_l:
                hits += 1
        return hits / max(1, len(expected))

    def grade_answer(self, answer: str) -> str:
        answer = (answer or "").strip()
        expected = list(self.state.get("expected") or [])
        question = str(self.state.get("current_question") or "the practice question")
        hint = str(self.state.get("hint") or "Use the lesson structure and retry.")

        if not answer:
            return f"I did not receive an answer. Please answer this:\n{question}"

        self.state["answers_total"] = int(self.state.get("answers_total", 0)) + 1
        score = self._match_score(answer, expected)
        enough_length = len(answer.split()) >= 5
        is_correct = score >= 0.5 and enough_length

        if is_correct:
            self.state["answers_correct"] = int(self.state.get("answers_correct", 0)) + 1
            self.state["awaiting_answer"] = False
            self.state["lessons_completed"] = int(self.state.get("lessons_completed", 0)) + 1
            self._save_state()

            auto_advance = bool(getattr(config, "ENGLISH_COACH_AUTO_ADVANCE", True))
            praise = (
                "Great answer. Structure is clear and useful."
                if score >= 0.75
                else "Good answer. You are on the right track."
            )
            if auto_advance:
                next_block = self.next_lesson(auto_requested=False)
                return f"{praise}\n\n{next_block}"
            return f"{praise}\nSay `next lesson` to continue."

        self.state["awaiting_answer"] = True
        self._save_state()
        return (
            "Not fully correct yet. Let's refine it.\n\n"
            f"Hint: {hint}\n\n"
            f"Question: {question}\n"
            "Reply again with `answer: ...`."
        )

    def get_daily_session_plan(self) -> str:
        if not self.state.get("started"):
            self.state["started"] = True

        today = datetime.now().strftime("%Y-%m-%d")
        target = int(self.state.get("daily_target_minutes", 30))
        self.state["last_session_date"] = today
        self.state["sessions_completed"] = int(self.state.get("sessions_completed", 0)) + 1
        self._save_state()

        idx = int(self.state.get("current_lesson_index", 0))
        lesson = self.LESSONS[idx]
        return (
            f"Daily English Session ({target} minutes)\n"
            "1. Warm-up (5m): Speak yesterday's summary in English.\n"
            f"2. Core Lesson (10m): {lesson['title']}\n"
            f"3. Practice (10m): {lesson['question']}\n"
            "4. Review (5m): Rewrite one answer with better grammar.\n\n"
            "Reply with `answer: ...` to start the practice now."
        )

    def get_progress_report(self) -> str:
        total = int(self.state.get("answers_total", 0))
        correct = int(self.state.get("answers_correct", 0))
        accuracy = (correct / total * 100.0) if total else 0.0
        lesson_idx = int(self.state.get("current_lesson_index", 0))
        lesson = self.LESSONS[lesson_idx]

        return (
            "English Coach Progress\n"
            f"- Current lesson: {lesson['title']} ({lesson_idx + 1}/{len(self.LESSONS)})\n"
            f"- Lessons completed: {int(self.state.get('lessons_completed', 0))}\n"
            f"- Answer accuracy: {accuracy:.0f}% ({correct}/{total})\n"
            f"- Daily target: {int(self.state.get('daily_target_minutes', 30))} minutes\n"
            f"- Sessions completed: {int(self.state.get('sessions_completed', 0))}\n"
            "Use `next lesson`, `daily session`, or `quiz me`."
        )

    def _set_daily_target(self, text: str) -> str:
        match = re.search(r"set daily target(?: to)? (\d+)", text)
        if not match:
            return "Use: `set daily target 30` (minutes)."
        value = int(match.group(1))
        value = max(10, min(180, value))
        self.state["daily_target_minutes"] = value
        self._save_state()
        return f"Daily target updated to {value} minutes."

    def register_chat_turn(self) -> None:
        self.state["chat_turn_count"] = int(self.state.get("chat_turn_count", 0)) + 1
        self._save_state()

    def get_passive_prompt(self) -> str:
        if not bool(getattr(config, "ENGLISH_COACH_AUTO_MODE", True)):
            return ""
        if not self.is_active():
            return ""

        if self.state.get("awaiting_answer"):
            q = str(self.state.get("current_question") or "").strip()
            if q:
                return f"English Coach Step: {q}"
            return ""

        turns = int(self.state.get("chat_turn_count", 0))
        last_nudge = int(self.state.get("last_nudge_turn", 0))
        if turns - last_nudge < 3:
            return ""

        self.state["last_nudge_turn"] = turns
        self._save_state()
        idx = int(self.state.get("current_lesson_index", 0))
        lesson = self.LESSONS[idx]
        return f"English Coach Step: say `next lesson` to continue `{lesson['title']}`, or `daily session` for today's full plan."

    def _render_lesson(self, index: int, include_practice: bool = True) -> str:
        lesson = self.LESSONS[max(0, min(index, len(self.LESSONS) - 1))]
        lines = [
            f"Lesson {index + 1}/{len(self.LESSONS)}: {lesson['title']}",
            f"Definition: {lesson['concept']}",
            "Steps:",
        ]
        for step_num, step in enumerate(lesson["steps"], 1):
            lines.append(f"{step_num}. {step}")
        lines.append(f"Example: {lesson['example']}")
        lines.append(f"Practice: {lesson['question']}")
        lines.append(f"Homework: {lesson['homework']}")

        if include_practice:
            self.state["awaiting_answer"] = True
            self.state["current_question"] = lesson["question"]
            self.state["expected"] = list(lesson["expected"])
            self.state["hint"] = lesson["hint"]
            self._save_state()

        return "\n".join(lines)
