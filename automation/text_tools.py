"""
J.A.R.V.I.S. Text & NLP Tools Module
Summarize, translate, correct grammar, convert text, count words.
All operations run locally without external API calls.
"""
import re
import os
from core.logger import log_event, log_error


def summarize_text(target: str) -> tuple:
    """
    Extractive summarization — picks the most important sentences.
    Works 100% locally. Useful for long pasted text.
    """
    try:
        text = target.strip()
        if not text:
            return False, "Please provide text to summarize, Sir."

        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)
        if len(sentences) <= 3:
            return True, f"Summary: {text}"

        # Score sentences by keyword frequency
        words = re.findall(r"\b\w+\b", text.lower())
        # Remove stop words
        stop = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                "being", "have", "has", "had", "do", "does", "did", "will",
                "would", "could", "should", "may", "might", "must", "shall",
                "to", "of", "in", "on", "at", "by", "for", "with", "about",
                "as", "into", "through", "during", "before", "after", "above",
                "below", "from", "up", "down", "out", "off", "over", "under",
                "then", "once", "and", "but", "or", "nor", "so", "yet", "both",
                "either", "neither", "not", "only", "own", "same", "than",
                "too", "very", "just", "that", "this", "these", "those", "it",
                "its", "also", "i", "you", "he", "she", "we", "they", "what",
                "which", "who", "whom", "their"}
        freq = {}
        for w in words:
            if w not in stop and len(w) > 2:
                freq[w] = freq.get(w, 0) + 1

        # Score each sentence
        scored = []
        for sent in sentences:
            score = sum(freq.get(w.lower(), 0) for w in re.findall(r"\b\w+\b", sent))
            scored.append((score, sent))

        scored.sort(reverse=True)
        # Pick top 3 sentences, preserve original order
        top_sents = [s for _, s in scored[:3]]
        summary = " ".join(s for s in sentences if s in top_sents)

        return True, f"Summary: {summary}"

    except Exception as e:
        log_error("TextTools.summarize", e)
        return False, f"Summarization failed: {e}"


def correct_grammar(target: str) -> tuple:
    """
    Basic grammar/typo correction using rule-based fixes.
    For deeper correction the LLM is used, but this handles common cases locally.
    """
    try:
        text = target.strip()
        if not text:
            return False, "Please provide text to correct, Sir."

        # Capitalize first letter of sentences
        text = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), text)

        # Capitalize "I" when standalone
        text = re.sub(r"\bi\b", "I", text)

        # Fix double spaces
        text = re.sub(r" {2,}", " ", text)

        # Fix common typos
        typos = {
            r"\bteh\b": "the", r"\bthier\b": "their", r"\breiceve\b": "receive",
            r"\brecieve\b": "receive", r"\bseperate\b": "separate",
            r"\boccured\b": "occurred", r"\buntill\b": "until",
            r"\bdefinately\b": "definitely", r"\bcoudn't\b": "couldn't",
            r"\bwoudn't\b": "wouldn't", r"\bshoudl\b": "should",
            r"\bconvinced\b": "convinced", r"\bexistance\b": "existence",
        }
        for pattern, replacement in typos.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

        # Ensure ends with punctuation
        if text and text[-1] not in ".!?":
            text += "."

        return True, f"Corrected text: {text}"

    except Exception as e:
        log_error("TextTools.grammar", e)
        return False, f"Grammar correction failed: {e}"


def count_words(target: str) -> tuple:
    """Counts words, characters, sentences, and paragraphs in text."""
    try:
        text = target.strip()
        if not text:
            return False, "Please provide text to analyze, Sir."

        words = len(re.findall(r"\b\w+\b", text))
        chars = len(text)
        chars_no_spaces = len(text.replace(" ", ""))
        sentences = len(re.split(r"[.!?]+", text))
        paragraphs = len([p for p in text.split("\n\n") if p.strip()])

        return True, (
            f"Text Analysis:\n"
            f"  Words: {words}\n"
            f"  Characters: {chars} ({chars_no_spaces} without spaces)\n"
            f"  Sentences: {sentences}\n"
            f"  Paragraphs: {paragraphs}"
        )
    except Exception as e:
        return False, f"Word count failed: {e}"


def convert_case(target: str) -> tuple:
    """
    Converts text case.
    Format: "upper|hello world" → "HELLO WORLD"
    Modes: upper, lower, title, sentence, camel, snake
    """
    try:
        if "|" in target:
            parts = target.split("|", 1)
            mode = parts[0].strip().lower()
            text = parts[1].strip()
        else:
            return False, "Please specify mode and text. Example: 'upper|your text here', Sir."

        if mode == "upper":
            result = text.upper()
        elif mode == "lower":
            result = text.lower()
        elif mode == "title":
            result = text.title()
        elif mode == "sentence":
            result = text.capitalize()
        elif mode == "camel":
            words = text.split()
            result = words[0].lower() + "".join(w.title() for w in words[1:]) if words else text
        elif mode == "snake":
            result = "_".join(text.lower().split())
        else:
            return False, f"Unknown case mode '{mode}'. Use: upper, lower, title, sentence, camel, snake."

        return True, f"Converted: {result}"
    except Exception as e:
        return False, f"Case conversion failed: {e}"


def calculate(target: str) -> tuple:
    """
    Evaluates a math expression safely.
    Supports: +, -, *, /, **, %, sqrt, etc.
    """
    import math
    try:
        expr = target.strip().lower()
        if not expr:
            return False, "Please provide a math expression or conversion, Sir."

        # Handle descriptive math and unit conversions
        expr = expr.replace("plus", "+").replace("minus", "-").replace("times", "*").replace("multiplied by", "*").replace("divided by", "/").replace("divided", "/")
        expr = expr.replace("power", "**").replace("square root of", "sqrt").replace("square of", "**2").replace("cube of", "**3")
        expr = expr.replace("percent of", "*0.01*").replace("% of", "*0.01*")

        # Basic conversions
        if "km to meters" in expr or "kilometer to meter" in expr:
            val = re.findall(r"\d+\.?\d*", expr)[0]
            return True, f"{val} km = {float(val) * 1000} meters"
        if "grams to kg" in expr or "g to kg" in expr:
            val = re.findall(r"\d+\.?\d*", expr)[0]
            return True, f"{val} grams = {float(val) / 1000} kg"

        # Allow only safe math characters
        safe_expr = re.sub(r"[^0-9+\-*/().%^ sqrt\spielog\*\*\d]", "", expr)
        safe_expr = safe_expr.replace("^", "**")
        safe_expr = safe_expr.replace("sqrt", "math.sqrt")
        safe_expr = safe_expr.replace("pi", "math.pi")
        safe_expr = safe_expr.replace("log", "math.log")

        result = eval(safe_expr, {"__builtins__": {}, "math": math})
        return True, f"The result is {result}"
    except ZeroDivisionError:
        return False, "Division by zero is undefined, Sir."
    except Exception as e:
        return False, f"Could not evaluate '{target}': {e}"


def generate_password(target: str = "16") -> tuple:
    """Generates a strong random password."""
    import secrets
    import string
    try:
        length = int(target.strip()) if target.strip().isdigit() else 16
        length = max(8, min(64, length))
        alphabet = string.ascii_letters + string.digits + "!@#$%&*"
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        return True, f"Generated password ({length} chars): {password}"
    except Exception as e:
        return False, f"Password generation failed: {e}"


def reminder_note(target: str) -> tuple:
    """
    Saves a quick note/reminder to a text file on the Desktop.
    """
    try:
        if not target.strip():
            return False, "Please provide a note to save, Sir."

        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        note_file = os.path.join(desktop, "jarvis_notes.txt")

        from datetime import datetime
        timestamp = datetime.now().strftime("[%Y-%m-%d %H:%M]")

        with open(note_file, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} {target.strip()}\n")

        return True, f"Note saved to Desktop, Sir: '{target.strip()}'"
    except Exception as e:
        return False, f"Failed to save note: {e}"


def read_notes(target: str = "") -> tuple:
    """Reads all saved notes from the Desktop notes file."""
    try:
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        note_file = os.path.join(desktop, "jarvis_notes.txt")

        if not os.path.exists(note_file):
            return True, "No notes saved yet, Sir."

        with open(note_file, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            return True, "The notes file is empty, Sir."

        lines = content.split("\n")
        recent = lines[-10:]  # Last 10 notes
        return True, "Recent notes:\n" + "\n".join(recent)
    except Exception as e:
        return False, f"Failed to read notes: {e}"
def translate_text(target: str) -> tuple:
    """
    Translates text between languages.
    Format: "to telugu|Hello how are you"
    This is typically handled by the LLM for maximum international accuracy.
    """
    # This is a stub; the BrainController/Main will route this to the LLM
    # if it's not handled here. For now, we report it needs LLM logic.
    return False, "I need to use my neural translation engine for this. One moment..."
