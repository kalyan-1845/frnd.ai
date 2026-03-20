"""
Shared Sara companion response formatting utilities.
"""
import re

EMOTION_TAGS = ("Smile", "Concerned", "Laugh", "Blush", "Sad", "Neutral")

_TAG_LOOKUP = {tag.lower(): tag for tag in EMOTION_TAGS}
_EMOTION_RE = re.compile(
    r"^\s*\[(smile|concerned|laugh|blush|sad|neutral)\]\s*",
    flags=re.IGNORECASE,
)
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def extract_emotion_tag(text: str) -> tuple[str | None, str]:
    """
    Extract a supported leading emotion tag and return (tag, body_without_tag).
    """
    raw = (text or "").strip()
    if not raw:
        return None, ""

    match = _EMOTION_RE.match(raw)
    if not match:
        return None, raw

    tag = _TAG_LOOKUP.get(match.group(1).lower())
    body = raw[match.end():].strip()
    return tag, body


def infer_emotion_tag(user_text: str = "", reply_text: str = "") -> str:
    """
    Infer the best tag when one is not present.
    """
    combined = f"{user_text} {reply_text}".lower()

    if any(w in combined for w in ("sad", "cry", "depressed", "lonely", "hurt", "down")):
        return "Sad"
    if any(w in combined for w in ("tired", "stress", "anxious", "worry", "upset")):
        return "Concerned"
    if any(w in combined for w in ("thank", "sweet", "cute", "love you", "best")):
        return "Blush"
    if any(w in combined for w in ("haha", "lol", "lmao", "funny", "joke")):
        return "Laugh"
    return "Smile"


def ensure_emotion_tag(text: str, user_text: str = "", default_tag: str = "Smile") -> str:
    """
    Ensure output starts with one supported emotion tag.
    """
    raw = (text or "").strip()
    if not raw:
        raw = "I am right here."

    existing_tag, body = extract_emotion_tag(raw)
    if existing_tag:
        final_tag = existing_tag
        final_body = body or "I am right here."
    else:
        final_tag = infer_emotion_tag(user_text, raw) or default_tag
        final_body = raw

    final_body = " ".join(final_body.split()).strip() or "I am right here."
    return f"[{final_tag}] {final_body}"


def _limit_to_short_chat(text: str, max_sentences: int = 3, max_chars: int = 280) -> str:
    compact = " ".join((text or "").split()).strip()
    if not compact:
        return ""

    parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(compact) if p.strip()]
    if len(parts) > max_sentences:
        compact = " ".join(parts[:max_sentences]).strip()
    else:
        compact = " ".join(parts).strip()

    if len(compact) > max_chars:
        compact = compact[:max_chars].rstrip(" ,;:")
        if compact and compact[-1] not in ".!?":
            compact += "."

    return compact


def format_companion_response(text: str, user_text: str = "") -> str:
    """
    Enforce Sara output style:
    - valid emotion tag prefix
    - short, conversational 1-3 sentence body
    """
    tagged = ensure_emotion_tag(text, user_text=user_text)
    tag, body = extract_emotion_tag(tagged)
    short_body = _limit_to_short_chat(body, max_sentences=3, max_chars=280)
    if not short_body:
        short_body = "I am right here."
    return f"[{tag or 'Smile'}] {short_body}"


def tag_to_voice_mood(tag: str | None, fallback: str = "calm") -> str:
    """
    Map Sara emotion tags to available TTS mood labels.
    """
    mapping = {
        "Smile": "happy",
        "Laugh": "happy",
        "Blush": "happy",
        "Concerned": "concerned",
        "Sad": "concerned",
        "Neutral": "calm",
    }
    if not tag:
        return fallback
    return mapping.get(tag, fallback)


def tag_to_avatar_state(tag: str | None) -> str:
    """
    Map Sara emotion tags to existing avatar frame states.
    """
    if tag in {"Smile", "Laugh", "Blush"}:
        return "smile"
    if tag == "Concerned":
        return "eyes_open"
    if tag == "Sad":
        return "idle_shift"
    return "idle"
