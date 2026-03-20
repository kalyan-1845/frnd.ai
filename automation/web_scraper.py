"""
J.A.R.V.I.S. Web Scraper & Research Module
Real-time web data extraction, summarization, and analysis.
"""
import os
import time
import urllib.request
import urllib.parse
import re
import webbrowser
import json
import random
from core.logger import log_event, log_error


def _fetch_page(url: str, timeout: int = 8) -> str:
    """Fetch raw HTML from a URL."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="ignore")
    except Exception as e:
        raise RuntimeError(f"Fetch failed for {url}: {e}")


def _strip_html(html: str) -> str:
    """Strip HTML tags and condense whitespace."""
    # Remove script/style blocks
    html = re.sub(r"<(script|style)[^>]*>.*?</(script|style)>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    # Remove all tags
    html = re.sub(r"<[^>]+>", " ", html)
    # Decode common HTML entities
    for entity, char in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                          ("&quot;", '"'), ("&nbsp;", " "), ("&#39;", "'")]:
        html = html.replace(entity, char)
    # Collapse whitespace
    html = re.sub(r"\s+", " ", html).strip()
    return html


def scrape_url(target: str) -> tuple:
    """
    Scrape and summarize text content from a URL.
    Returns (success, summary_text).
    """
    try:
        raw_target = (target or "").strip()
        if not raw_target:
            return False, "Please provide a URL to scrape."

        # Detect "full source" mode
        full_mode = False
        lowered = raw_target.lower()
        if any(lowered.endswith(flag) for flag in (" full", " source", " raw", " full source", " fullsource")) or " full source" in lowered:
            full_mode = True
            raw_target = re.sub(r"\b(full\s*source|fullsource|full|source|raw)\b", "", raw_target, flags=re.IGNORECASE).strip()

        url = raw_target
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        log_event("WebScraper", f"Scraping: {url} (full={full_mode})")
        html = _fetch_page(url)
        text = _strip_html(html)

        if full_mode:
            os.makedirs("logs", exist_ok=True)
            safe_name = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:40] or "page"
            filename = os.path.join("logs", f"scrape_{safe_name}_{int(time.time())}.txt")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html)
            preview = text[:1200] + ("..." if len(text) > 1200 else "")
            return True, f"Saved full page source to {filename}.\nPreview:\n{preview}"

        # Limit to first 1500 chars for voice readability
        if len(text) > 1500:
            text = text[:1500] + "... [content truncated]"

        return True, f"Content from {url}:\n{text}"

    except Exception as e:
        log_error("WebScraper.scrape_url", e)
        return False, f"Could not scrape {target}: {e}"


def get_wikipedia_summary(target: str) -> tuple:
    """Fetch a Wikipedia article summary for a given topic."""
    try:
        query = urllib.parse.quote_plus(target.strip())
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}"
        log_event("WebScraper.wikipedia", f"Fetching: {target}")

        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-AI/2.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            extract = data.get("extract", "")
            title = data.get("title", target)

            if not extract:
                return False, f"No Wikipedia article found for '{target}'."

            if len(extract) > 800:
                extract = extract[:800] + "..."

            return True, f"{title}: {extract}"

    except Exception as e:
        log_error("WebScraper.wikipedia", e)
        error_msg = str(e)
        if "404" in error_msg:
            return False, f"I couldn't find a Wikipedia article for '{target}'."
        return False, "Wikipedia lookup failed."


def get_definition(target: str) -> tuple:
    """Defines a word using the Free Dictionary API."""
    try:
        word = target.strip().lower().split()[0]
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}"
        log_event("WebScraper.define", f"Defining: {word}")

        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-AI/2.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))

            if not isinstance(data, list) or not data:
                return False, f"No definition found for '{word}'."

            entry = data[0]
            meanings = entry.get("meanings", [])
            if not meanings:
                return False, f"No definition found for '{word}'."

            result_parts = [f"Definition of '{word}':"]
            for meaning in meanings[:2]:
                pos = meaning.get("partOfSpeech", "")
                defs = meaning.get("definitions", [])
                if defs:
                    result_parts.append(f"  [{pos}] {defs[0].get('definition', '')}")
            
            return True, "\n".join(result_parts)

    except Exception as e:
        log_error("WebScraper.define", e)
        return False, f"Dictionary lookup failed for {target}."


def get_joke(target: str = "") -> tuple:
    """Fetches a random joke with local fallbacks."""
    try:
        url = "https://v2.jokeapi.dev/joke/Any?blacklistFlags=nsfw,explicit&type=twopart"
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-AI/2.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("type") == "twopart":
                return True, f"{data['setup']} ... {data['delivery']}"
            elif data.get("type") == "single":
                return True, data["joke"]
    except Exception:
        pass
    
    # Local fallback
    fallbacks = [
        "Why did the programmer quit his job? Because he didn't get arrays.",
        "A SQL query walks into a bar, walks up to two tables, and asks, 'Can I join you?'",
        "Why do programmers always mix up Halloween and Christmas? Because Oct 31 equals Dec 25.",
        "There are 10 types of people in the world: those who understand binary, and those who don't."
    ]
    return True, f"{random.choice(fallbacks)} (Enjoy this classic while the joke service is resting!)"


def get_quote(target: str = "") -> tuple:
    """Fetches an inspirational quote with local fallbacks."""
    try:
        url = "https://api.quotable.io/random"
        req = urllib.request.Request(url, headers={"User-Agent": "JARVIS-AI/2.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return True, f'"{data["content"]}" — {data["author"]}'
    except Exception:
        pass
    
    # Local fallback
    fallbacks = [
        '"The only way to do great work is to love what you do." — Steve Jobs',
        '"Innovation distinguishes between a leader and a follower." — Steve Jobs',
        '"Your time is limited, so don\'t waste it living someone else\'s life." — Steve Jobs',
        '"Stay hungry, stay foolish." — Whole Earth Catalog',
        '"Success is not final, failure is not fatal: it is the courage to continue that counts." — Winston Churchill'
    ]
    return True, f"{random.choice(fallbacks)} (I picked one of my personal favorites for you!)"
