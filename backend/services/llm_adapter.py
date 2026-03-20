"""LLM Adapter — thin wrapper over core.llm_api functions so the BrainController can call them.
Provides a simple class LLMAdapter with methods generate, plan, and stream_generate.
"""
from typing import Generator
import core.llm_api as llm_api


class LLMAdapter:
    def generate(self, user_input, user_name='friend', memory_context='', persona_context='', companion_mode=False):
        return llm_api.generate_response(user_input, user_name, memory_context, persona_context, companion_mode=companion_mode)

    def plan(self, user_input):
        try:
            return llm_api.plan_actions(user_input)
        except Exception:
            return []

    def stream_generate(self, user_input, user_name='friend', memory_context='', persona_context='', companion_mode=False):
        try:
            gen = llm_api.stream_generate_response(user_input, user_name, memory_context, persona_context, companion_mode=companion_mode)
            for chunk in gen:
                yield chunk
        except Exception:
            if False:
                yield ""
