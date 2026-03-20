import os
import re
import subprocess
import urllib.parse
import webbrowser
from typing import Optional, Tuple


_DOMAIN_RE = re.compile(
    r"^(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?::\d{1,5})?(?:/.*)?$"
)


def _looks_like_domain(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return False
    if t.startswith(("http://", "https://", "www.")):
        return True
    if t.startswith("localhost") or t.startswith("127.0.0.1"):
        return True
    return bool(_DOMAIN_RE.match(t))


def _launch_url(url: str) -> bool:
    """
    Open URL with multiple fallbacks for Windows reliability.
    """
    try:
        if webbrowser.open(url, new=2):
            return True
    except Exception:
        pass

    # Windows-native fallbacks
    if os.name == "nt":
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            return True
        except Exception:
            pass
        try:
            subprocess.Popen(["cmd", "/c", "start", "", url], shell=False)
            return True
        except Exception:
            pass

    return False


def _normalize_open_target(raw_target: str) -> tuple[str | None, str]:
    """
    Convert user target into a valid URL.
    - domain/url -> open directly
    - plain token like 'youtube' -> https://www.youtube.com
    - phrase -> Google search
    """
    original = (raw_target or "").strip()
    if not original:
        return None, ""

    target = original
    lower = target.lower()
    if lower.startswith(("http://", "https://")):
        return target, original
    if lower.startswith("www."):
        return f"https://{target}", original

    if _looks_like_domain(target):
        return f"https://{target}", original

    # Single app-like token (e.g., youtube, facebook, github)
    if " " not in target and re.fullmatch(r"[a-zA-Z0-9-]+", target):
        return f"https://www.{target}.com", original

    # Fallback: treat as search text
    encoded = urllib.parse.quote_plus(target)
    return f"https://www.google.com/search?q={encoded}", original


def open_url(url):
    """
    Opens a specific website in the default browser.
    Automatically adds https:// if no protocol is specified.
    Returns (success: bool, message: str)
    """
    try:
        normalized, original = _normalize_open_target(url)
        if not normalized:
            return False, "No URL provided."

        print(f"[Browser] Opening: {normalized}")
        if _launch_url(normalized):
            return True, f"Opened {original or normalized}"
        return False, "Failed to launch browser."
    except Exception as e:
        print(f"[Error] Failed to open URL: {e}")
        return False, f"Failed to open {url}"


def search_google(query):
    """
    Searches Google for the given query.
    Returns (success: bool, message: str)
    """
    try:
        query = (query or "").strip() or "latest updates"
        print(f"[Browser] Searching Google for: {query}")
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={encoded}"
        if _launch_url(url):
            return True, f"Searching Google for {query}"
        return False, "Failed to launch browser for Google search."
    except Exception as e:
        print(f"[Error] Google search failed: {e}")
        return False, f"Failed to search Google"


def search_youtube(query):
    """
    Searches or plays a video on YouTube.
    If query contains 'play', it attempts to launch it more directly.
    Returns (success: bool, message: str)
    """
    def _youtube_first_result(q: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Use yt_dlp to resolve the first matching YouTube video.
        Returns (url, title) or (None, None) on failure.
        """
        try:
            import yt_dlp  # type: ignore
        except Exception:
            return None, None

        ydl_opts = {
            "quiet": True,
            "skip_download": True,
            "extract_flat": "in_playlist",
            "default_search": "ytsearch1",
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(q, download=False)
                entries = info.get("entries") or []
                if not entries:
                    return None, None
                first = entries[0]
                url = first.get("webpage_url") or first.get("url")
                title = first.get("title")
                if url and not url.startswith("http"):
                    url = f"https://www.youtube.com/watch?v={url}"
                return url, title
        except Exception:
            return None, None

    try:
        query = (query or "").strip()
        print(f"[Browser] YouTube Action: {query}")

        if not query or query.lower() in ["youtube", "open youtube"]:
            return open_url("https://www.youtube.com")

        if query.startswith(("http://", "https://")):
            return open_url(query)

        # If it's a 'play' request, we can append 'play' to the query for better results
        search_query = query
        if "play" not in query.lower():
            search_query = f"play {query}"

        # Try resolving the first video and play it directly
        direct_url, title = _youtube_first_result(search_query)
        if direct_url:
            if _launch_url(direct_url):
                name = title or query
                return True, f"Playing {name} on YouTube"

        # Fallback: open search results page
        encoded = urllib.parse.quote_plus(search_query)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        if _launch_url(url):
            return True, f"Searching YouTube for {query}"
        return False, "Failed to launch browser for YouTube."
    except Exception as e:
        print(f"[Error] YouTube action failed: {e}")
        return False, f"Failed to play on YouTube"


def search_weather(query="weather"):
    """
    Opens a weather search in the browser.
    Returns (success: bool, message: str)
    """
    try:
        query = (query or "").strip() or "weather near me"
        encoded = urllib.parse.quote_plus(query)
        url = f"https://www.google.com/search?q={encoded}"
        if _launch_url(url):
            return True, "Showing weather"
        return False, "Failed to launch browser for weather."
    except Exception as e:
        print(f"[Error] Weather search failed: {e}")
        return False, "Failed to check weather"


def search_news(query="latest news"):
    """
    Opens Google News in the browser.
    Returns (success: bool, message: str)
    """
    try:
        query = (query or "").strip() or "latest news"
        encoded = urllib.parse.quote_plus(query)
        url = f"https://news.google.com/search?q={encoded}"
        if _launch_url(url):
            return True, "Showing latest news"
        return False, "Failed to launch browser for news."
    except Exception as e:
        print(f"[Error] News search failed: {e}")
        return False, "Failed to search news"
