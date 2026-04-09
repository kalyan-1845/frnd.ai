# Security Policy

## Supported Versions

The following versions of Frnd.AI (Leo Assistant) are currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| < 2.0   | :x:                |

## Reporting a Vulnerability

Privacy and security are core principles of Frnd.AI. If you discover a security vulnerability, please follow these steps:

1. **Do Not Open a Public Issue**: To prevent exploitation, please report vulnerabilities privately.
2. **Report via Email**: Send a detailed report to the maintainer (Kalyan).
3. **Wait for Triage**: We will acknowledge your report and provide an estimated timeline for a fix.

## Local-First Philosophy

Frnd.AI is designed to be **local-first**. Most processing (LLM, STT, TTS) happens on your machine.
- **Data Privacy**: Your voice and chat data stay on your device unless you explicitly configure cloud providers (like Deepgram or OpenAI).
- **Network Security**: Ensure your local LLM server (Ollama) is not exposed to the public internet unless you intend it to be.
- **Dependencies**: We regularly review dependencies for known vulnerabilities. Please keep your environment updated.

---

*Thank you for helping keep Frnd.AI secure!*
