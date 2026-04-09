# 🤖 Frnd.AI: Leo Assistant (BKR 2.0)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Security: Local-First](https://img.shields.io/badge/Security-Local--First-brightgreen.svg)](SECURITY.md)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Platform: Windows](https://img.shields.io/badge/Platform-Windows-0078D6.svg)](https://www.microsoft.com/windows)

**Frnd.AI (Leo)** is a premium, multilingual AI assistant designed for Windows. It provides a seamless, local-first experience with a futuristic visual interface, advanced voice control, and deep system integration.

> [!TIP]
> **Total Privacy**: All core processing (Speech-to-Text, LLM, and Text-to-Speech) runs locally on your machine by default.

---

## ✨ Key Features

### 🎙️ Advanced Multilingual Voice
- **Local STT/TTS**: Powered by Vosk and Piper for high-speed, offline speech processing.
- **Deepgram Integration**: Optional cloud-backed speech processing for enterprise-grade accuracy.
- **Auto-Language Detection**: Supports English, Hindi, Telugu, and more.

### 🧠 Intelligent Core
- **Ollama Powered**: Uses LLaMA 3 (and other models) for grounded reasoning.
- **Long-Term Memory**: Persistent memory across sessions using ChromaDB vector storage.
- **Web Grounding**: Real-time factual retrieval via DuckDuckGo and Wikipedia.

### 🖥️ Deep System Control
- **Application Logic**: Open any app, manage processes, and take screenshots.
- **Power Management**: Lock, sleep, shutdown, and restart with voice commands.
- **Environment Control**: Adjust brightness, volume, and Night Light settings.

### 📱 Communication & Productivity
- **WhatsApp & Gmail**: Send messages and compose emails via voice.
- **File Management**: Organize, create, zip, and find files effortlessly.
- **Adaptive Teaching**: Built-in tutors for coding, language learning, and general study.

### 🎭 Vision & Emotion
- **Emotion Tracking**: Analyzes facial expressions via webcam to adapt tone and response.
- **Infinity Core UI**: A gorgeous, reactive visual interface with high-end animations.

---

## 🚀 Quick Start

### 📋 Prerequisites
- **OS**: Windows 10/11
- **Python**: 3.10 or higher
- **Ollama**: [Download Ollama](https://ollama.com/) and run `ollama pull llama3`.

### 🛠️ Installation

1. **Clone & Setup Environment**:
   ```powershell
   git clone https://github.com/kalyan-1845/frnd.ai.git
   cd frnd.ai
   python -m venv .venv
   .\.venv\Scripts\activate
   ```

2. **Install Dependencies**:
   ```powershell
   pip install -r requirements.txt
   pip install chromadb opencv-python mediapipe pygame
   ```

3. **Bootstrap Local Models**:
   ```powershell
   python scripts\bootstrap_local_models.py --languages en hi te --clean-archives
   ```

### 🏃 Running Leo

- **One-Click Start**: Run `run_agent.bat`.
- **Manual Start**: 
  ```powershell
  python main.py
  ```

---

## 🎤 Command Highlights

| Category | Commands |
| :--- | :--- |
| **Messaging** | `"Hey Leo, send WhatsApp to Ravi saying See you at 5"` |
| **System** | `"Hey Leo, set brightness to 50"`, `"Hey Leo, system status"` |
| **Files** | `"Hey Leo, create folder 'Projects' on Desktop"` |
| **Learning** | `"Hey Leo, teach me about Quantum Computing"`, `"Quiz me"` |
| **Research** | `"Hey Leo, who is Albert Einstein?"` |

---

## 🏗️ Architecture

- **`main.py`**: Entry point and central orchestration loop.
- **`core/`**: High-level logic handlers for memory, tools, and LLM communication.
- **`backend/`**: Low-level system integrations and automation scripts.
- **`frontend/`**: Visual assets and the Infinity Core UI implementation.
- **`layers/`**: Abstracted logic layers for better modularity.

---

## 🛡️ Security & Privacy

Privacy is not an option; it's a feature. Leo is designed to work entirely offline if desired.
- **No Telemetry**: We don't track your usage or collect your data.
- **Local Vectors**: Your long-term memory is stored locally in `nova_memory.db`.
- **Camera Privacy**: Webcam emotion tracking runs locally and never uploads images.

See [SECURITY.md](SECURITY.md) for more details.

---

## 📜 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

*Developed with ❤️ by **Kalyan** — Aiming to build the most helpful local assistant.*
