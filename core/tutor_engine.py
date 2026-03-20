"""
General subject tutor for step-by-step guided learning on any topic.

The tutor keeps a lightweight persistent session so the assistant can:
- start a learning plan for any subject
- continue step by step across turns
- ask practice questions
- grade short answers with simple keyword matching
- answer follow-up questions within the active lesson
"""
from __future__ import annotations

import json
import re
import random
import time
from typing import Optional, Callable

import config
from core.knowledge_engine import (
    get_global_knowledge_payload,
)
from core.logger import log_error, log_event


_STOPWORDS = {
    "about",
    "after",
    "also",
    "because",
    "before",
    "between",
    "could",
    "does",
    "from",
    "have",
    "into",
    "just",
    "more",
    "should",
    "than",
    "that",
    "their",
    "there",
    "these",
    "they",
    "this",
    "topic",
    "focus",
    "foundation",
    "basics",
    "core",
    "ideas",
    "parts",
    "important",
    "understand",
    "break",
    "building",
    "blocks",
    "workflow",
    "works",
    "usage",
    "example",
    "applied",
    "practice",
    "mastery",
    "goal",
    "goals",
    "very",
    "what",
    "when",
    "where",
    "which",
    "while",
    "with",
    "would",
    "your",
}


class SubjectTutor:
    """Persistent guided tutor for arbitrary subjects."""

    PROFILE_KEY = "subject_tutor_state_v1"

    START_PATTERNS = (
        r"^(?:teach me(?: about)?|help me learn|i want to learn|learn|explain me|explain|i want learn)\s+(?P<subject>.+)$",
        r"^(?:what is|who is|who was|define|tell me about|what is the meaning of|what do you know about|search for|search|search about)\s+(?P<subject>.+)$",
        r"^(?:start|create|build|design|give me|make)\s+(?:a\s+)?(?:lesson|course|study plan|roadmap|syllabus|curriculum|learning path)\s+(?:on|for|about)\s+(?P<subject>.+)$",
        r"^explain\s+(?P<subject>.+?)\s+(?:step by step|like a teacher|in small understanding)$",
        r"^(?:difference between|compare)\s+(?P<subject>.+)$",
        r"^study\s+(?P<subject>.+)$",
    )
    NEXT_KEYWORDS = (
        "next step",
        "next topic",
        "continue",
        "continue lesson",
        "go on",
        "move ahead",
    )
    REPEAT_KEYWORDS = ("repeat", "repeat step", "repeat lesson", "say that again")
    STATUS_KEYWORDS = ("lesson status", "study status", "learning status", "where am i")
    QUIZ_KEYWORDS = ("quiz me", "test me", "ask a question", "practice question", "check my knowledge", "give me exercise", "challenge", "problem")
    STOP_KEYWORDS = ("stop lesson", "end lesson", "stop teaching", "close lesson", "exit lesson", "end teaching", "get out of lesson")
    LEVEL_KEYWORDS = ("beginner", "intermediate", "advanced")

    QUESTION_STARTERS = (
        "what",
        "why",
        "how",
        "when",
        "where",
        "which",
        "who",
        "explain",
        "describe",
        "simplify",
        "tell me",
        "can",
        "could",
        "should",
        "is",
        "are",
        "do",
        "does",
        "did",
        "my answer",
        "answer:",
        "i think",
        "it means",
        "because",
        "hint",
        "solution",
        "how to solve",
        "answer is",
        "correct me",
        "feedback",
    )

    def __init__(self, memory_system):
        self.memory = memory_system
        # Explicitly type the LLM generation function so static checkers know
        # it's optional and callable when present. This reduces 'not-callable'
        # static errors and communicates intent.
        self._llm_generate: Optional[Callable[[str], str | None]] = None
        self._last_meta = {"sources": [], "grounded": False, "subject": ""}
        
        self.learning_styles = {
            "visual": ["show", "visual", "diagram", "chart", "graph", "picture"],
            "auditory": ["explain", "tell", "describe", "read", "listen", "voice"],
            "kinesthetic": ["practice", "do", "try", "exercise", "example", "action"],
            "reading": ["read", "text", "book", "article", "document", "write"],
            "logical": ["reason", "logic", "proof", "derivation", "why"],
            "creative": ["story", "imagine", "metaphor", "analogy", "art"],
            "social": ["discuss", "talk", "chat", "collaborate", "group"]
        }
        
        self.teaching_methods = {
            "step_by_step": ["explain", "how to", "steps", "process"],
            "example_based": ["example", "show me", "demonstrate", "illustrate"],
            "question_answer": ["what is", "why", "how", "when", "where", "who"],
            "practice_oriented": ["practice", "exercise", "quiz", "test", "solve"],
            "feynman": ["simple", "plain english", "like i'm five", "eli5"],
            "socratic": ["question", "ask me", "guide", "inquiry"],
            "storytelling": ["story", "narrative", "tale", "analogy"],
            "first_principles": ["break down", "fundamental", "basics", "from scratch"],
            "deep_dive": ["advanced", "deep", "complex", "everything", "expert"]
        }
        
        self.state = self._load_state()

    def bind_llm(self, generate_fn):
        self._llm_generate = generate_fn

    def get_last_meta(self) -> dict:
        return dict(self._last_meta)

    def _default_state(self) -> dict:
        return {
            "enabled": bool(getattr(config, "TUTOR_ENABLED", True)),
            "active": False,
            "subject": "",
            "level": str(getattr(config, "TUTOR_DEFAULT_LEVEL", "beginner")),
            "curriculum": "general",
            "language_style": "english",
            "current_step_index": 0,
            "outline": [],
            "awaiting_answer": False,
            "current_question": "",
            "expected_terms": [],
            "completed_steps": 0,
            "quiz_count": 0,
            "quiz_pass_count": 0,
            "last_knowledge": "",
            "last_session_summary": "",
            "summary_sentences": 2,
            "teaching_method": "step_by_step",
            "learning_style": "reading",
        }

    def _load_state(self) -> dict:
        state = self._default_state()
        try:
            raw = self.memory.get_preference(self.PROFILE_KEY)
            if raw:
                loaded = json.loads(raw)
                if isinstance(loaded, dict):
                    state.update(loaded)
        except Exception as err:
            log_error("SubjectTutor.load_state", err)
        return state

    def _save_state(self) -> None:
        try:
            self.memory.store_preference(self.PROFILE_KEY, json.dumps(self.state))
        except Exception as err:
            log_error("SubjectTutor.save_state", err)

    def _norm(self, text: str) -> str:
        return " ".join((text or "").strip().lower().split())

    def is_active(self) -> bool:
        return bool(self.state.get("enabled", True) and self.state.get("active") and self.state.get("subject"))

    def _looks_like_new_question(self, text: str) -> bool:
        starters = ("who is", "what is", "when is", "where is", "where was", "who was", "tell me about", "define")
        return text.endswith("?") or any(text.startswith(prefix) for prefix in starters)

    def _looks_related_to_subject(self, text: str) -> bool:
        subject = str(self.state.get("subject", "")).strip().lower()
        context = str(self.state.get("last_knowledge", "")).strip().lower()
        subject_terms = set(self._extract_key_terms(subject, context, limit=10))
        if any(term in text for term in subject_terms):
            return True
        reference_markers = ("this step", "that step", "this topic", "that topic", "this example", "that example", "current step")
        return any(marker in text for marker in reference_markers)

    def should_handle(self, user_input: str) -> bool:
        if not bool(getattr(config, "TUTOR_ENABLED", True)):
            return False

        text = self._norm(user_input)
        if not text or "english coach" in text:
            return False

        if not text.strip() or len(text) < 2: # Handle silence/vague
             return self.is_active()

        if self._extract_start_request(user_input):
            return True

        if not self.is_active():
            return False

        if self.state.get("awaiting_answer"):
            if self._looks_like_new_question(text) and not self._looks_related_to_subject(text):
                return False
            return True

        if any(keyword in text for keyword in self.NEXT_KEYWORDS + self.REPEAT_KEYWORDS + self.STATUS_KEYWORDS + self.QUIZ_KEYWORDS + self.STOP_KEYWORDS):
            return True

        if self._is_feedback_request(text) or any(kw in text for kw in ["hint", "solution", "answer", "correct", "wrong", "mistake", "feedback"]):
            return True

        if text.endswith("?") or any(text.startswith(prefix) for prefix in self.QUESTION_STARTERS):
            return self._looks_related_to_subject(text)
        return False

    def handle_input(self, user_input: str) -> str | None:
        self.state = self._load_state()
        text = self._norm(user_input)
        if not text:
            return None

        start_request = self._extract_start_request(user_input)
        if start_request:
            subject, level = start_request
            return self._start_session(subject, level, user_input)

        if not self.is_active():
            return None

        if any(keyword in text for keyword in self.STOP_KEYWORDS):
            return self._stop_session()

        requested_level = self._extract_level(text)
        if requested_level and ("level" in text or "switch" in text or "make it" in text):
            return self._change_level(requested_level)

        if any(keyword in text for keyword in self.STATUS_KEYWORDS):
            return self._status_report()

        if any(keyword in text for keyword in self.REPEAT_KEYWORDS):
            return self._render_current_step(prefix="Repeating the current lesson.")

        if self._is_feedback_request(text):
            return self._refine_current_step(user_input)

        if any(keyword in text for keyword in self.QUIZ_KEYWORDS):
            return self._quiz_current_step()

        if any(keyword in text for keyword in self.NEXT_KEYWORDS):
            return self._next_step()

        if self.state.get("awaiting_answer") or any(kw in text for kw in ["check", "correct", "evaluate", "rate", "answer is"]):
            return self._grade_answer(user_input)

        if "hint" in text:
            return self._provide_hint()

        if "solution" in text or "solve" in text or "how do I" in text:
            return self._provide_solution(text)

        if any(kw in text for kw in ["recommend", "suggest", "books", "videos", "resources", "projects"]):
            return self._provide_recommendations(user_input)

        if any(kw in text for kw in ["roadmap", "plan", "syllabus", "curriculum", "strategy"]):
            return self._provide_planning_overview(user_input)

        return self._answer_follow_up(user_input)

    def _extract_start_request(self, user_input: str) -> tuple[str, str] | None:
        raw = (user_input or "").strip()
        text = self._norm(raw)
        if not text or "english coach" in text:
            return None

        for pattern in self.START_PATTERNS:
            match = re.match(pattern, text, flags=re.IGNORECASE)
            if not match:
                continue
            subject = (match.group("subject") or "").strip(" .?")
            if not subject:
                continue
            subject = re.sub(r"\b(?:please|for me|step by step|like a teacher)\b", "", subject, flags=re.IGNORECASE)
            subject = " ".join(subject.split()).strip(" .?")
            if not subject:
                continue
            level = self._extract_level(text) or str(getattr(config, "TUTOR_DEFAULT_LEVEL", "beginner"))
            return subject, level
        return None

    def _extract_level(self, text: str) -> str | None:
        for level in self.LEVEL_KEYWORDS:
            if level in text:
                return level
        return None

    def _detect_language_style(self, text: str) -> str:
        return "english"

    def _localize(self, text: str, language_style: str) -> str:
        return text

    def _translate_query_for_lookup(self, text: str, language_style: str) -> str:
        return text

    def _detect_curriculum(self, subject: str) -> str:
        subject_lower = subject.lower()
        if any(word in subject_lower for word in ("english", "grammar", "language", "speaking", "writing", "vocabulary", "ielts", "toefl")):
            return "language"
        if any(word in subject_lower for word in ("interview", "exam", "gate", "gre", "upsc", "neet", "jee", "revision")):
            return "exam_prep"
        if any(word in subject_lower for word in ("python", "java", "javascript", "coding", "programming", "sql", "react", "api", "debug", "git")):
            return "coding"
        if any(word in subject_lower for word in ("ai", "machine learning", "deep learning", "neural network", "llm", "rag", "data science")):
            return "ai_ml"
        if any(word in subject_lower for word in ("stress", "anxiety", "sleep", "focus", "burnout", "wellbeing", "well-being", "habit")):
            return "wellbeing"
        if any(word in subject_lower for word in ("physics", "chemistry", "biology", "math", "mathematics", "photosynthesis", "algebra")):
            return "science"
        if any(word in subject_lower for word in ("business", "startup", "marketing", "finance", "economics", "management", "leadership", "negotiation", "entrepreneurship")):
            return "business"
        if any(word in subject_lower for word in ("productivity", "time management", "thinking", "problem solving", "communication", "public speaking", "writing", "design")):
            return "soft_skills"
        return "general"

    def _identify_teaching_method(self, text: str) -> str:
        text_l = text.lower()
        for method, keywords in self.teaching_methods.items():
            if any(kw in text_l for kw in keywords):
                return method
        return random.choice(list(self.teaching_methods.keys()))

    def _identify_learning_style(self, text: str) -> str:
        text_l = text.lower()
        for style, keywords in self.learning_styles.items():
            if any(kw in text_l for kw in keywords):
                return style
        return random.choice(list(self.learning_styles.keys()))

    def _build_outline(self, subject: str, curriculum: str, max_steps: int = 5) -> list[dict]:
        max_steps = max(3, int(max_steps or getattr(config, "TUTOR_MAX_STEPS", 5)))

        if curriculum == "language":
            outline = [
                {"title": "Goal and Basics", "focus": f"Define the goal, scope, and beginner foundations of {subject}."},
                {"title": "Core Patterns", "focus": f"Learn the key patterns, structures, or vocabulary used in {subject}."},
                {"title": "Usage", "focus": f"Understand how {subject} is used in real conversations or tasks."},
                {"title": "Practice", "focus": f"Apply {subject} through short exercises and corrections."},
                {"title": "Fluency Build", "focus": f"Identify the next drills and habits to improve in {subject}."},
            ]
        elif curriculum == "coding":
            outline = [
                {"title": "Foundation", "focus": f"Define what {subject} is and why it matters."},
                {"title": "Core Building Blocks", "focus": f"Learn the main components, syntax, or concepts in {subject}."},
                {"title": "Workflow", "focus": f"Understand how {subject} works step by step in practice."},
                {"title": "Real Example", "focus": f"Walk through one concrete example of {subject}."},
                {"title": "Practice Project", "focus": f"Plan a small hands-on task to reinforce {subject}."},
            ]
        elif curriculum == "ai_ml":
            outline = [
                {"title": "Problem Framing", "focus": f"Define the core goal, inputs, and outputs in {subject}."},
                {"title": "Core Concepts", "focus": f"Learn the models, terms, and data concepts behind {subject}."},
                {"title": "Training and Inference", "focus": f"Understand how {subject} is built, trained, or executed."},
                {"title": "Evaluation", "focus": f"Measure quality, limitations, and common failure modes in {subject}."},
                {"title": "Practical Use", "focus": f"Design one practical application or experiment for {subject}."},
            ]
        elif curriculum == "exam_prep":
            outline = [
                {"title": "Syllabus Map", "focus": f"Break {subject} into high-yield units and exam priorities."},
                {"title": "Core Concepts", "focus": f"Cover the must-know ideas and formulas for {subject}."},
                {"title": "Question Patterns", "focus": f"Study how {subject} appears in typical exam questions."},
                {"title": "Timed Practice", "focus": f"Use short drills and error review for {subject}."},
                {"title": "Revision Plan", "focus": f"Create a revision and mock-test plan for {subject}."},
            ]
        elif curriculum == "wellbeing":
            outline = [
                {"title": "Situation Check", "focus": f"Understand the current situation, triggers, and goals around {subject}."},
                {"title": "Core Principles", "focus": f"Learn the practical basics that improve {subject}."},
                {"title": "Daily Routine", "focus": f"Build a simple routine that supports better {subject}."},
                {"title": "Tracking", "focus": f"Measure progress and identify warning signs for {subject}."},
                {"title": "Sustainable Plan", "focus": f"Create a realistic weekly plan to improve {subject}."},
            ]
        elif curriculum == "science":
            outline = [
                {"title": "Definition", "focus": f"Define {subject} clearly and identify the core phenomenon."},
                {"title": "Mechanism", "focus": f"Explain the internal process or scientific logic of {subject}."},
                {"title": "Key Terms", "focus": f"Learn the formulas, parts, or terminology linked to {subject}."},
                {"title": "Applied Example", "focus": f"Connect {subject} to one experiment or real-world case."},
                {"title": "Check Understanding", "focus": f"Review {subject} through short recall and application questions."},
            ]
        elif curriculum == "business":
            outline = [
                {"title": "Core Market Definition", "focus": f"Identify the value proposition, market, and customers for {subject}."},
                {"title": "Business Model", "focus": f"Learn how {subject} generates value and sustains itself."},
                {"title": "Growth Strategies", "focus": f"Understand marketing, scaling, and distribution for {subject}."},
                {"title": "Operational Management", "focus": f"Execution, leadership, and day-to-day management in {subject}."},
                {"title": "Vision and Scale", "focus": f"Long-term strategy and innovation in the world of {subject}."},
            ]
        elif curriculum == "soft_skills":
            outline = [
                {"title": "Foundational Mindset", "focus": f"Understand the mental shifts needed for effective {subject}."},
                {"title": "Core Techniques", "focus": f"Learn 2-3 specific techniques to improve your {subject} today."},
                {"title": "Practical Practice", "focus": f"Execute a real-world scenario to apply your {subject} skills."},
                {"title": "Feedback and Review", "focus": f"Analyze common errors and how to refine your {subject}."},
                {"title": "Habit Building", "focus": f"Create a 7-day plan to integrate {subject} into your life."},
            ]
        else:
            outline = [
                {"title": "Foundation", "focus": f"Understand what {subject} is and why it matters."},
                {"title": "Core Ideas", "focus": f"Break {subject} into its most important ideas or parts."},
                {"title": "How It Works", "focus": f"Explain the process, logic, or mechanism behind {subject}."},
                {"title": "Applied Example", "focus": f"Connect {subject} to one practical real-world example."},
                {"title": "Practice and Mastery", "focus": f"Review {subject}, practice it, and identify the next milestone."},
            ]

        # If a higher step count is requested, interleave more detail or advanced steps
        if max_steps > len(outline):
            # Dynamic expansion logic for high-count lessons
            expanded = []
            for i, step in enumerate(outline):
                expanded.append(step)
                if len(expanded) < max_steps:
                    if "Core" in step["title"] or "Concept" in step["title"]:
                        expanded.append({"title": f"Deep Dive into {step['title']}", "focus": f"Exploring advanced details of {step['focus']}"})
                    elif "Foundation" in step["title"]:
                        expanded.append({"title": "Historical Context", "focus": f"Evolution and history of {subject}."})
            outline = expanded

        return outline[:max_steps]

    def _get_step(self) -> dict:
        outline = self.state.get("outline") or []
        if not outline:
            return {"title": "Foundation", "focus": "Build the basics first."}
        index = max(0, min(int(self.state.get("current_step_index", 0)), len(outline) - 1))
        return outline[index]

    def _build_lookup_query(self, subject: str, step: dict) -> str:
        title = str(step.get("title", "")).lower()
        if "foundation" in title or "goal" in title:
            return f"what is {subject}"
        if "core" in title or "building blocks" in title:
            return f"{subject} key concepts"
        if "workflow" in title or "how it works" in title:
            return f"how {subject} works"
        if "example" in title or "usage" in title:
            return f"{subject} example"
        if "practice" in title or "mastery" in title or "project" in title:
            return f"{subject} applications"
        return subject

    def _summarize_context(self, context: str, max_sentences: int = 2, max_chars: int = 420) -> str:
        compact = " ".join((context or "").split()).strip()
        if not compact:
            return ""
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", compact) if part.strip()]
        if not parts:
            return compact[:320].rstrip()
        summary = " ".join(parts[:max_sentences]).strip()
        return summary[:max_chars].rstrip(" ,;:")

    def _extract_key_terms(self, *values: str, limit: int = 6) -> list[str]:
        terms = []
        seen = set()
        for value in values:
            for word in re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{3,}", (value or "").lower()):
                if word in _STOPWORDS or word in seen:
                    continue
                seen.add(word)
                terms.append(word)
                if len(terms) >= limit:
                    return terms
        return terms

    def _build_example(self, subject: str, step: dict, knowledge_summary: str, curriculum: str) -> str:
        sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", knowledge_summary) if part.strip()]
        if len(sentences) >= 2:
            return sentences[1]

        title = step.get("title", "").lower()
        if curriculum == "coding":
            return f"Write one small code snippet or function that demonstrates {subject}."
        if curriculum == "ai_ml":
            return f"Describe one dataset, model, or workflow where {subject} would be used."
        if curriculum == "exam_prep":
            return f"Solve one short exam-style question on {subject} under a time limit."
        if curriculum == "wellbeing":
            return f"Track one daily habit related to {subject} for the next three days."
        if curriculum == "language":
            return f"Use {subject} in one short speaking or writing example from daily life."
        if "example" in title:
            return f"Pick one real situation where {subject} appears and describe how it is used."
        if "practice" in title or "project" in title:
            return f"Create one small task on {subject} and complete it in under 20 minutes."
        return f"Explain {subject} to another person using one simple real-life example."

    def _build_practice_question(self, subject: str, step: dict, curriculum: str) -> str:
        title = step.get("title", "").lower()
        if curriculum == "coding":
            if "project" in title:
                return f"What is the smallest working project you can build to practice {subject} today?"
            return f"Name two important concepts in {subject} and explain where each is used."
        if curriculum == "ai_ml":
            return f"Explain one input, one output, and one limitation of {subject}."
        if curriculum == "exam_prep":
            return f"What are the top three exam points you must revise first in {subject}?"
        if curriculum == "wellbeing":
            return f"What is one trigger and one practical habit that would improve {subject}?"
        if curriculum == "language":
            return f"Write or speak two short lines using {subject} correctly."
        if "foundation" in title or "goal" in title:
            return f"In 2 lines, what is {subject} and why does it matter?"
        if "core" in title or "building blocks" in title:
            return f"Name two important parts or ideas inside {subject}."
        if "workflow" in title or "how it works" in title:
            return f"Explain the process of {subject} in 3 short steps."
        if "example" in title or "usage" in title:
            return f"Give one practical example of {subject} from real life or work."
        return f"What would you practice next to improve your understanding of {subject}?"

    def _render_current_step(self, prefix: str = "") -> str:
        subject = str(self.state.get("subject", "")).strip()
        level = str(self.state.get("level", "beginner"))
        curriculum = str(self.state.get("curriculum", "general"))
        language_style = str(self.state.get("language_style", "english"))
        step = self._get_step()
        step_index = int(self.state.get("current_step_index", 0))
        outline = self.state.get("outline") or []
        summary_sentences = int(self.state.get("summary_sentences", 2))
        max_chars = 720 if summary_sentences >= 3 else 420

        lookup_query = self._translate_query_for_lookup(self._build_lookup_query(subject, step), language_style)
        knowledge_payload = get_global_knowledge_payload(lookup_query)
        if not knowledge_payload.get("context"):
            knowledge_payload = get_global_knowledge_payload(self._translate_query_for_lookup(subject, language_style))
        knowledge = str(knowledge_payload.get("context", "")).strip()
        self._last_meta = {
            "sources": list(knowledge_payload.get("sources", []) or []),
            "grounded": bool(knowledge_payload.get("sources")),
            "subject": subject,
        }
        knowledge_summary = self._summarize_context(knowledge, max_sentences=summary_sentences, max_chars=max_chars)
        
        # Determine if we need to be creative (nonsense/imaginary/no info)
        is_creative_mode = not bool(knowledge.strip()) or any(kw in subject.lower() for kw in ["imaginary", "nonsense", "impossible", "fictional"])

        if not knowledge_summary:
            knowledge_summary = f"I'll use my imagination for this one! {subject} is a fascinating concept that we can explore together through creativity."

        example = self._build_example(subject, step, knowledge_summary, curriculum)
        practice = self._build_practice_question(subject, step, curriculum)
        expected_terms = self._extract_key_terms(subject, step.get("title", ""), step.get("focus", ""), knowledge_summary)

        self.state["current_question"] = practice
        self.state["expected_terms"] = expected_terms
        self.state["awaiting_answer"] = False
        self.state["last_knowledge"] = knowledge_summary
        self.state["last_session_summary"] = knowledge_summary
        self._save_state()

        # Conversational Buddy Synthesis using LLM
        if self._llm_generate:
            method_name = str(self.state.get("teaching_method", "step_by_step")).replace("_", " ").title()
            style_name = str(self.state.get("learning_style", "reading")).title()
            
            prompt = f"""You are a brilliant, friendly AI Tutor Buddy. 
Act like an expert teacher using the {method_name} method and {style_name} learning style.

SUBJECT: {subject}
CURRENT STEP: {step.get('title')} ({step_index + 1}/{len(outline)})
KNOWLEDGE CONTEXT: {knowledge}

TASK:
1. Synthesize a warm, conversational greeting and explanation for this step.
2. If this is a creative/nonsense/imaginary topic (MODE: {'CREATIVE' if is_creative_mode else 'FACTUAL'}), be playful and play along as a Buddy.
3. Provide a vivid, real-world (or imaginary-world) example.
4. Conclude with a clear practice question (use this as a base: {practice}).

IF THE USER SEEMS CONFUSED OR FRUSTRATED:
- Pivot to be extra supportive.
- Simplify further.
- Ask if they want to 'go slower' or 'skip this part'.

FORMATTING RULES:
- If method is 'storytelling', use a short narrative.
- If method is 'example_based', lead with the example.
- If method is 'feynman', use ultra-simple language (ELI5).
- If style is 'visual', use a simple text-based diagram or Mermaid flow.
- If the user specifically asked for a TABLE, use a Markdown table.
- If the user specifically asked for BULLET POINTS, use a list.

Keep it buddy-like, supportive, and prioritize clarity. Avoid robotic headers. Output must be in {language_style}.
"""
            try:
                conversational_response = self._llm_generate(prompt)
                if conversational_response:
                    return self._localize(conversational_response, language_style)
            except Exception as e:
                log_error("SubjectTutor.llm_synthesis", e)

        # Fallback to template-based output
        lines = []
        if prefix:
            lines.append(prefix)
        lines.extend(
            [
                f"Learning session: {subject} ({level})",
                f"Track: {curriculum.replace('_', ' ')}",
                f"Approach: {self.state.get('teaching_method', 'Standard').replace('_', ' ').title()} ({self.state.get('learning_style', 'Reading').title()} style)",
                f"Step {step_index + 1}/{len(outline) or 1}: {step.get('title', 'Foundation')}",
                f"Explanation: {knowledge_summary}",
                f"Example: {example}",
                f"Practice: {practice}",
                "Use `quiz me`, `next step`, or answer the practice question.",
            ]
        )
        return self._localize("\n".join(lines), language_style)

    def _start_session(self, subject: str, level: str, source_text: str) -> str:
        language_style = self._detect_language_style(source_text)
        curriculum_type = self._detect_curriculum(subject)
        
        # Detect custom step count
        max_steps = 5
        step_match = re.search(r"in (\d+) steps", source_text.lower())
        if step_match:
            max_steps = int(step_match.group(1))
        elif "quick" in source_text.lower():
            max_steps = 3
        elif "deep" in source_text.lower() or "detailed" in source_text.lower():
            max_steps = 8

        self.state = self._default_state()
        self.state.update(
            {
                "active": True,
                "subject": subject,
                "level": level,
                "curriculum": curriculum_type,
                "language_style": language_style,
                "outline": self._build_outline(subject, curriculum_type, max_steps),
                "current_step_index": 0,
                "teaching_method": self._identify_teaching_method(source_text),
                "learning_style": self._identify_learning_style(source_text),
            }
        )
        self._save_state()

        outline_lines = [f"{idx + 1}. {step['title']}" for idx, step in enumerate(self.state["outline"])]
        
        plan_type = "lesson"
        if "roadmap" in source_text.lower(): plan_type = "roadmap"
        elif "syllabus" in source_text.lower(): plan_type = "syllabus"
        elif "plan" in source_text.lower(): plan_type = "study plan"

        intro = f"Structured {plan_type} started for {subject}.\n"
        lesson_block = self._render_current_step(prefix=intro.strip())
        log_event("SubjectTutor.start", f"subject={subject} level={level} type={plan_type}")
        return lesson_block

    def _next_step(self) -> str:
        outline = self.state.get("outline") or []
        current_index = int(self.state.get("current_step_index", 0))
        if not outline:
            return self._render_current_step(prefix="The lesson outline was missing, so I rebuilt the current step.")

        if current_index >= len(outline) - 1:
            language_style = str(self.state.get("language_style", "english"))
            summary = (
                f"You completed the current structured path for {self.state.get('subject', 'this topic')}.\n"
                "Use `quiz me` for revision, ask a follow-up question, or start a new lesson on another subject."
            )
            return self._localize(summary, language_style)

        self.state["current_step_index"] = current_index + 1
        self.state["completed_steps"] = max(int(self.state.get("completed_steps", 0)), current_index + 1)
        self._save_state()
        return self._render_current_step(prefix="Moving to the next step.")

    def _quiz_current_step(self) -> str:
        language_style = str(self.state.get("language_style", "english"))
        self._last_meta = {"sources": [], "grounded": False, "subject": str(self.state.get("subject", ""))}
        question = str(
            self.state.get("current_question")
            or self._build_practice_question(
                self.state.get("subject", "this topic"),
                self._get_step(),
                str(self.state.get("curriculum", "general")),
            )
        )
        self.state["current_question"] = question
        self.state["awaiting_answer"] = True
        self.state["quiz_count"] = int(self.state.get("quiz_count", 0)) + 1
        self._save_state()
        return self._localize(
            f"Quiz time.\nQuestion: {question}\nAnswer in 2-4 lines. I will check it and guide you.",
            language_style,
        )

    def _grade_answer(self, answer: str) -> str:
        language_style = str(self.state.get("language_style", "english"))
        answer_norm = self._norm(answer)
        expected_terms = [term for term in self.state.get("expected_terms", []) if term]
        matches = [term for term in expected_terms if term in answer_norm]
        
        # Determine feedback using LLM for "Buddy" quality
        if self._llm_generate:
            prompt = f"""You are a supportive AI Tutor Buddy.
SUBJECT: {self.state.get('subject')}
QUESTION WAS: {self.state.get('current_question')}
USER'S ANSWER: {answer}
EXPECTED CONCEPTS: {', '.join(expected_terms)}
USER EMOTION: (Detect if they are frustrated, confused, or curious from their text)

TASK:
1. Evaluate the answer warmly.
2. If they are FRUSTRATED: Don't correct them strictly—instead, validate them and offer a hint or the solution.
3. If they are CONFUSED: Explain the concept again with a different analogy.
4. If they are CURIOUS: Give them an extra fun fact along with the feedback.
5. Provide a 'Buddy Score' and suggest `next step`.

Keep it concise, encouraging, and in {language_style}.
"""
            try:
                feedback = self._llm_generate(prompt)
                self.state["awaiting_answer"] = False
                self._save_state()
                return self._localize(feedback, language_style)
            except:
                pass

        # Fallback logic
        passed = len(matches) >= 1
        self.state["awaiting_answer"] = False
        if passed:
            self.state["quiz_pass_count"] += 1
            self._save_state()
            return f"Spot on! You nailed the core concepts: {', '.join(matches)}. What's next?"
        return f"Not quite, but you're getting there! Think more about {', '.join(expected_terms[:2])}. Want a hint?"

    def _provide_hint(self) -> str:
        language_style = str(self.state.get("language_style", "english"))
        prompt = f"Give a subtle, helpful hint for the topic {self.state.get('subject')} and question {self.state.get('current_question')}. Don't give the full answer!"
        hint = self._llm_generate(prompt) if self._llm_generate else "Try thinking about the basic objective of the topic."
        return self._localize(f"💡 Hint: {hint}", language_style)

    def _provide_solution(self, text: str) -> str:
        language_style = str(self.state.get("language_style", "english"))
        modifier = ""
        if "simplified" in text or "simple" in text: modifier = "simple and easy"
        elif "alternative" in text: modifier = "alternative/different"
        elif "optimized" in text or "best" in text: modifier = "highly optimized and professional"
        
        prompt = f"Provide a {modifier} solution/explanation for the current challenge in {self.state.get('subject')}. Break it into clear steps."
        solution = self._llm_generate(prompt) if self._llm_generate else "I'll guide you through this. (Manual lookup required)"
        return self._localize(f"✅ Solution Breakdown:\n\n{solution}", language_style)

    def _answer_follow_up(self, user_input: str) -> str:
        language_style = str(self.state.get("language_style", "english"))
        subject = str(self.state.get("subject", "")).strip()
        curriculum = str(self.state.get("curriculum", "general"))
        step = self._get_step()
        lookup_query = self._translate_query_for_lookup(f"{subject} {user_input}", language_style)
        knowledge_payload = get_global_knowledge_payload(lookup_query)
        knowledge = str(knowledge_payload.get("context", "")).strip()
        if knowledge_payload.get("sources"):
            self._last_meta = {
                "sources": list(knowledge_payload.get("sources", []) or []),
                "grounded": True,
                "subject": subject,
            }
        summary = self._summarize_context(knowledge, max_sentences=3) or str(self.state.get("last_knowledge", "")).strip()
        if not summary:
            summary = f"Stay with the current focus: {step.get('focus', 'understand the basics and then apply one example')}."

        example = self._build_example(subject, step, summary, curriculum)
        response = (
            f"Topic: {subject}\n"
            f"Track: {curriculum.replace('_', ' ')}\n"
            f"Current step: {step.get('title', 'Foundation')}\n"
            f"Answer: {summary}\n"
            f"Example: {example}\n"
            "Ask another question, answer the practice, or say `next step`."
        )
        return self._localize(response, language_style)

    def _status_report(self) -> str:
        language_style = str(self.state.get("language_style", "english"))
        self._last_meta = {"sources": [], "grounded": False, "subject": str(self.state.get("subject", ""))}
        outline = self.state.get("outline") or []
        current_index = int(self.state.get("current_step_index", 0))
        response = (
            f"Current subject: {self.state.get('subject', 'none')}\n"
            f"Track: {self.state.get('curriculum', 'general').replace('_', ' ')}\n"
            f"Level: {self.state.get('level', 'beginner')}\n"
            f"Current step: {current_index + 1}/{len(outline) or 1}\n"
            f"Completed steps: {int(self.state.get('completed_steps', 0))}\n"
            f"Quizzes passed: {int(self.state.get('quiz_pass_count', 0))}/{int(self.state.get('quiz_count', 0))}\n"
            "Use `next step`, `quiz me`, `repeat step`, or `stop lesson`."
        )
        return self._localize(response, language_style)

    def _provide_recommendations(self, user_input: str) -> str:
        subject = self.state.get("subject") or self._norm(user_input).replace("recommend", "").replace("resources", "").strip()
        if not subject: return "What subject would you like recommendations for?"
        
        language_style = str(self.state.get("language_style", "english"))
        
        prompt = f"""You are a Learning Resource Buddy.
SUBJECT: {subject}
USER REQUEST: {user_input}

TASK:
1. Recommend top 3 books/articles.
2. Recommend top 2-3 free online courses or videos (YouTube creators, etc.).
3. Suggest a specific hands-on project or exercise.
4. If they asked for 'advanced' or 'beginner' specifically, tailor the list.

Maintain a friendly, 'Buddy' tone. Use Markdown formatting. Output in {language_style}.
"""
        try:
            resp = self._llm_generate(prompt) if self._llm_generate else "I recommend checking Wikipedia and official documentation for starters!"
            return self._localize(f"📚 **Recommended Resources for {subject}:**\n\n{resp}", language_style)
        except:
            return "I run into a small error fetching those. I'd suggest starting with Google Scholar or YouTube for the best curated lists!"

    def _provide_planning_overview(self, user_input: str) -> str:
        subject = self.state.get("subject") or self._norm(user_input).replace("roadmap", "").replace("plan", "").strip()
        if not subject: return "What topic should I create a plan for?"
        
        language_style = str(self.state.get("language_style", "english"))
        prompt = f"""You are an Educational Strategist Buddy.
SUBJECT: {subject}
TYPE: {user_input} (Roadmap/Plan/Strategy)

TASK:
1. Create a high-level visual roadmap (using Markdown/ASCII).
2. Suggest a 4-week study timeline.
3. Identify the 'Checkpoint' goals for each week.
4. Give one 'Learning Tip' for staying focused on this topic.

Friendly, supportive, and extremely clear. Output in {language_style}.
"""
        try:
            resp = self._llm_generate(prompt) if self._llm_generate else "Follow a 5-step journey: Intro -> Theory -> Practice -> Project -> Portfolio."
            return self._localize(f"🗺️ **Learning Roadmap: {subject}**\n\n{resp}", language_style)
        except:
            return "Strategy: Start simple, build a small project, and then scale up. I can give you a better breakdown if you ask again in a moment!"

    def _change_level(self, level: str) -> str:
        self.state["level"] = level
        self._save_state()
        return self._render_current_step(prefix=f"Level changed to {level}.")

    def _stop_session(self) -> str:
        language_style = str(self.state.get("language_style", "english"))
        subject = str(self.state.get("subject", "this lesson"))
        self._last_meta = {"sources": [], "grounded": False, "subject": subject}
        self.state["active"] = False
        self.state["awaiting_answer"] = False
        self._save_state()
        return self._localize(
            f"Stopped the guided lesson for {subject}. Start another one with `teach me ...` whenever you want.",
            language_style,
        )

    def _is_feedback_request(self, text: str) -> bool:
        text_l = text.lower()
        return any(kw in text_l for kw in [
            "better", "improve", "more detail", "more details", "explain more", "expand", "deeper",
            "shorter", "brief", "concise", "two lines", "2 lines", "simpler", "simple words", "easy words",
            "another example", "different example", "change example"
        ])

    def _refine_current_step(self, feedback: str) -> str:
        text_l = feedback.lower()
        
        # 1. Detail Level Adjustments
        if any(kw in text_l for kw in ["shorter", "brief", "concise", "two lines", "2 lines", "simpler", "easy words", "simple words", "quickly", "fast learner", "skip"]):
            self.state["summary_sentences"] = 1
        elif any(kw in text_l for kw in ["more detail", "more details", "expand", "deeper", "better", "improve", "explain more", "thoroughly", "deeply", "fully", "slow learner", "slowly", "confused"]):
            self.state["summary_sentences"] = 4
        
        # 2. Teaching Method Switches
        new_method = self._identify_teaching_method(text_l)
        if new_method != self.state.get("teaching_method"):
            # Only update if a specific keyword was found (don't use random fallback here)
            for m, keywords in self.teaching_methods.items():
                if any(kw in text_l for kw in keywords):
                    self.state["teaching_method"] = m
                    break

        # 3. Learning Style Switches
        new_style = self._identify_learning_style(text_l)
        if new_style != self.state.get("learning_style"):
            for s, keywords in self.learning_styles.items():
                if any(kw in text_l for kw in keywords):
                    self.state["learning_style"] = s
                    break

        # 4. Special format flags (handled by prompt usually, but can influence state)
        if "table" in text_l:
            self.state["teaching_method"] = "example_based" # Tables are great for examples/comparisons
        if "story" in text_l or "metaphor" in text_l or "analogy" in text_l:
            self.state["teaching_method"] = "storytelling"

        self._save_state()

        prefix = f"Done! I've adjusted my approach to be more {self.state.get('teaching_method', '').replace('_', ' ')} for you. "
        return self._render_current_step(prefix=prefix.strip())
