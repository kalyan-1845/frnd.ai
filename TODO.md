# TODO - Remove Window and Make Fully Local

## Task: Remove GUI window and make assistant fully local (no cloud dependencies)

### Steps:
- [x] 1. Understand the codebase and plan changes
- [x] 2. Modify main.py - Make headless mode default (with optional --gui flag)
- [x] 3. Modify core/llm_api.py - Remove cloud fallbacks (Gemini, Groq), keep only local Ollama
- [x] 4. Test the changes

## Changes Summary:
1. **main.py**: Headless mode by default; --gui flag to show window
2. **core/llm_api.py**: Remove cloud providers, keep only local Ollama + personality engine fallback
