"""
Lightweight global knowledge retrieval for chat grounding.

This module fetches short factual context from public sources and caches it
so chat responses can be grounded without opening a browser.
"""
from __future__ import annotations

import time
import urllib.parse

import requests

import config
from core.logger import log_error, log_event

_CACHE: dict[str, tuple[dict, float]] = {}
_CACHE_TTL_SECONDS = 900

_SMALL_TALK_MARKERS = (
    "hello",
    "hi",
    "hey",
    "how are you",
    "what are you doing",
    "good morning",
    "good evening",
    "thank you",
    "thanks",
)

_KNOWLEDGE_MARKERS = (
    "what is",
    "who is",
    "who was",
    "when did",
    "where is",
    "why is",
    "how does",
    "explain",
    "tell me about",
    "meaning of",
    "define",
    "history of",
    "difference between",
    "compare",
)

_TRANSLATE_CODES = {}


def _get_cache(query: str) -> dict | None:
    item = _CACHE.get(query)
    if not item:
        return None
    value, ts = item
    if (time.time() - ts) > _CACHE_TTL_SECONDS:
        _CACHE.pop(query, None)
        return None
    return value


def _set_cache(query: str, value: str) -> None:
    _CACHE[query] = (value, time.time())


def should_fetch_knowledge(query: str) -> bool:
    text = " ".join((query or "").lower().split())
    if not text or len(text) < 6:
        return False
    if any(marker in text for marker in _SMALL_TALK_MARKERS):
        return False
    if any(marker in text for marker in _KNOWLEDGE_MARKERS):
        return True
    if text.endswith("?") and len(text.split()) >= 3:
        return True
    return False


def _duckduckgo_payload(query: str) -> dict:
    response = requests.get(
        "https://api.duckduckgo.com/",
        params={
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        },
        headers={"User-Agent": f"{config.ASSISTANT_SHORT_NAME}/1.0"},
        timeout=6,
    )
    response.raise_for_status()
    payload = response.json() if response.content else {}

    parts: list[str] = []
    answer = str(payload.get("Answer", "")).strip()
    abstract = str(payload.get("AbstractText", "")).strip()
    definition = str(payload.get("Definition", "")).strip()
    heading = str(payload.get("Heading", "")).strip()

    if heading and abstract:
        parts.append(f"{heading}: {abstract}")
    elif abstract:
        parts.append(abstract)
    if answer and answer not in " ".join(parts):
        parts.append(answer)
    if definition and definition not in " ".join(parts):
        parts.append(definition)

    related = payload.get("RelatedTopics", []) or []
    for item in related[:3]:
        if isinstance(item, dict):
            text = str(item.get("Text", "")).strip()
            if text and text not in " ".join(parts):
                parts.append(text)
        if len(" ".join(parts)) > 700:
            break

    context = "\n".join(part for part in parts if part).strip()
    sources = []
    if context:
        sources.append(
            {
                "label": "DuckDuckGo Instant Answer",
                "url": f"https://duckduckgo.com/?q={urllib.parse.quote_plus(query)}",
            }
        )
    return {"context": context, "sources": sources}


def _wikipedia_payload(query: str) -> dict:
    search_response = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 1,
        },
        headers={"User-Agent": f"{config.ASSISTANT_SHORT_NAME}/1.0"},
        timeout=6,
    )
    search_response.raise_for_status()
    payload = search_response.json() if search_response.content else {}
    results = payload.get("query", {}).get("search", []) or []
    if not results:
        return ""

    title = str(results[0].get("title", "")).strip()
    if not title:
        return ""

    summary_response = requests.get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title)}",
        headers={"User-Agent": f"{config.ASSISTANT_SHORT_NAME}/1.0"},
        timeout=6,
    )
    summary_response.raise_for_status()
    summary_payload = summary_response.json() if summary_response.content else {}
    extract = str(summary_payload.get("extract", "")).strip()
    final_title = str(summary_payload.get("title", title)).strip()
    if not extract:
        return {"context": "", "sources": []}

    wiki_url = (
        summary_payload.get("content_urls", {})
        .get("desktop", {})
        .get("page", "")
    )
    if not wiki_url:
        wiki_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(final_title.replace(' ', '_'))}"

    return {
        "context": f"{final_title}: {extract}",
        "sources": [{"label": final_title or "Wikipedia", "url": wiki_url}],
    }


def get_global_knowledge_payload(query: str) -> dict:
    """
    Return factual context plus source metadata for a knowledge-seeking query.
    """
    normalized = " ".join((query or "").strip().split())
    if not normalized:
        return {"context": "", "sources": []}

    cached = _get_cache(normalized)
    if cached is not None:
        return cached

    max_chars = int(getattr(config, "LLM_GLOBAL_KNOWLEDGE_MAX_CHARS", 1400))
    fragments: list[str] = []
    sources: list[dict] = []

    try:
        ddg_payload = _duckduckgo_payload(normalized)
        ddg_context = str(ddg_payload.get("context", "")).strip()
        if ddg_context:
            fragments.append(ddg_context)
        for item in ddg_payload.get("sources", []) or []:
            if isinstance(item, dict) and item.get("url"):
                sources.append({"label": str(item.get("label", "Source")), "url": str(item["url"])})
    except Exception as err:
        log_error("Knowledge.DDG", err, normalized[:80])

    try:
        wiki_payload = _wikipedia_payload(normalized)
        wiki_context = str(wiki_payload.get("context", "")).strip()
        if wiki_context and wiki_context not in "\n".join(fragments):
            fragments.append(wiki_context)
        for item in wiki_payload.get("sources", []) or []:
            if isinstance(item, dict) and item.get("url"):
                url = str(item["url"])
                if all(existing.get("url") != url for existing in sources):
                    sources.append({"label": str(item.get("label", "Source")), "url": url})
    except Exception as err:
        log_error("Knowledge.Wikipedia", err, normalized[:80])

    context = "\n\n".join(fragment for fragment in fragments if fragment).strip()
    if len(context) > max_chars:
        context = context[:max_chars].rstrip() + "..."

    payload = {"context": context, "sources": sources}
    if context:
        log_event("KnowledgeContext", f"query='{normalized[:60]}' len={len(context)}")
    _set_cache(normalized, payload)
    return payload


def get_global_knowledge_context(query: str) -> str:
    """
    Return short factual context for a knowledge-seeking query.
    """
    return str(get_global_knowledge_payload(query).get("context", "")).strip()


def quick_translate_text(text: str, lang_style: str) -> str:
    """
    Translate a short answer into the target language when a known fast path exists.
    """
    target_lang = _TRANSLATE_CODES.get(lang_style)
    if not target_lang or not text.strip():
        return ""

    response = requests.get(
        "https://translate.googleapis.com/translate_a/single",
        params={
            "client": "gtx",
            "sl": "auto",
            "tl": target_lang,
            "dt": "t",
            "q": text,
        },
        headers={"User-Agent": f"{config.ASSISTANT_SHORT_NAME}/1.0"},
        timeout=6,
    )
    response.raise_for_status()
    payload = response.json() if response.content else []

    parts = []
    if isinstance(payload, list) and payload:
        for item in payload[0]:
            if isinstance(item, list) and item:
                parts.append(str(item[0]))
    return "".join(parts).strip()


def translate_to_english(text: str) -> str:
    """
    Translate a short query to English for retrieval.
    """
    if not text.strip():
        return ""

    response = requests.get(
        "https://translate.googleapis.com/translate_a/single",
        params={
            "client": "gtx",
            "sl": "auto",
            "tl": "en",
            "dt": "t",
            "q": text,
        },
        headers={"User-Agent": f"{config.ASSISTANT_SHORT_NAME}/1.0"},
        timeout=6,
    )
    response.raise_for_status()
    payload = response.json() if response.content else []

    parts = []
    if isinstance(payload, list) and payload:
        for item in payload[0]:
            if isinstance(item, list) and item:
                parts.append(str(item[0]))
    return "".join(parts).strip()
