"""
Avatar backend bridge for external expression control.

Current supported backends:
- local_ui: no-op (handled inside visual_window.py)
- vtube_studio: trigger hotkeys via VTube Studio Public API websocket
"""
from __future__ import annotations

import json
import uuid

import config

try:
    import websocket  # websocket-client
except Exception:
    websocket = None


_DEFAULT_VTS_HOTKEYS = {
    "Smile": "Smile",
    "Concerned": "Concerned",
    "Laugh": "Laugh",
    "Blush": "Blush",
    "Sad": "Sad",
    "Neutral": "Neutral",
}

_session_auth_token = None


def _normalize_tag(tag: str | None) -> str:
    if not tag:
        return "Neutral"
    clean = str(tag).strip().lower()
    mapping = {
        "smile": "Smile",
        "concerned": "Concerned",
        "laugh": "Laugh",
        "blush": "Blush",
        "sad": "Sad",
        "neutral": "Neutral",
    }
    return mapping.get(clean, "Neutral")


def _resolve_hotkey(tag: str) -> str:
    hotkey_map = getattr(config, "VTS_HOTKEY_MAP", None)
    if isinstance(hotkey_map, dict):
        candidate = hotkey_map.get(tag)
        if candidate:
            return str(candidate)
    return _DEFAULT_VTS_HOTKEYS.get(tag, _DEFAULT_VTS_HOTKEYS["Neutral"])


def _vts_request(ws, message_type: str, data: dict | None = None) -> dict:
    payload = {
        "apiName": "VTubeStudioPublicAPI",
        "apiVersion": "1.0",
        "requestID": str(uuid.uuid4()),
        "messageType": message_type,
        "data": data or {},
    }
    ws.send(json.dumps(payload))
    
    # Wait for response with timeout handling
    try:
        raw = ws.recv()
        return json.loads(raw)
    except Exception as e:
        log_error("VTS.recv", e)
        return {"data": {"error": f"Receive timeout or error: {e}"}}


def _get_auth_token(ws) -> str | None:
    global _session_auth_token

    cfg_token = getattr(config, "VTS_AUTH_TOKEN", None)
    if cfg_token:
        _session_auth_token = str(cfg_token)
        return _session_auth_token
    if _session_auth_token:
        return _session_auth_token

    resp = _vts_request(
        ws,
        "AuthenticationTokenRequest",
        {
            "pluginName": str(getattr(config, "VTS_PLUGIN_NAME", "Sara Companion Bridge")),
            "pluginDeveloper": str(getattr(config, "VTS_PLUGIN_DEVELOPER", "BKR2")),
        },
    )
    token = (
        resp.get("data", {}).get("authenticationToken")
        if isinstance(resp, dict)
        else None
    )
    if token:
        _session_auth_token = str(token)
    return _session_auth_token


def _authenticate_vts(ws) -> bool:
    token = _get_auth_token(ws)
    if not token:
        return False

    resp = _vts_request(
        ws,
        "AuthenticationRequest",
        {
            "pluginName": str(getattr(config, "VTS_PLUGIN_NAME", "Sara Companion Bridge")),
            "pluginDeveloper": str(getattr(config, "VTS_PLUGIN_DEVELOPER", "BKR2")),
            "authenticationToken": token,
        },
    )
    return bool(resp.get("data", {}).get("authenticated"))


def _trigger_vts_hotkey(tag: str) -> tuple[bool, str]:
    if websocket is None:
        return False, "websocket-client package is not installed."

    ws_url = str(getattr(config, "VTS_WS_URL", "ws://127.0.0.1:8001"))
    hotkey_id = _resolve_hotkey(tag)
    if not hotkey_id:
        return False, f"No hotkey mapping found for tag '{tag}'."

    try:
        ws = websocket.create_connection(ws_url, timeout=2)
    except Exception as e:
        return False, f"Unable to connect to VTube Studio at {ws_url}: {e}"

    try:
        if not _authenticate_vts(ws):
            return False, "VTube Studio authentication failed. Approve the plugin in VTube Studio."
        _vts_request(ws, "HotkeyTriggerRequest", {"hotkeyID": hotkey_id})
        return True, f"Triggered VTube hotkey '{hotkey_id}'."
    except Exception as e:
        return False, f"VTube Studio hotkey trigger failed: {e}"
    finally:
        try:
            ws.close()
        except Exception:
            pass


def apply_expression_from_tag(tag: str | None) -> tuple[bool, str]:
    """
    Trigger avatar expression from Sara emotion tag.
    """
    provider = str(getattr(config, "AVATAR_PROVIDER", "local_ui")).strip().lower()
    normalized_tag = _normalize_tag(tag)

    if provider in {"local_ui", "local", "none"}:
        return False, "Local UI handles expressions internally."
    if provider in {"vtube_studio", "vtubestudio", "vts"}:
        return _trigger_vts_hotkey(normalized_tag)
    return False, f"Unsupported AVATAR_PROVIDER='{provider}'."
