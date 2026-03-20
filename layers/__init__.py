"""
BKR 2.0 — Layered Architecture
===============================
A modular, pluggable AI assistant system with clear layer separation.

Layers:
- interface: UI/UX (voice, avatar, gui, gestures)
- intelligence: AI/Brain (brain, intent_parser, personality, llm)
- automation: Task execution (files, browser, messaging, tools)
- system_control: OS control (processes, settings, devices)
- data: Storage (memory, database, cache)
- integration: External APIs (ollama, tts, stt)
- security: Auth, monitoring, breach detection

Plugin System:
- Extensible capabilities via plugins/
"""

__version__ = "2.0.0"
__all__ = [
    "interface",
    "intelligence", 
    "automation",
    "system_control",
    "data",
    "integration",
    "security",
]
