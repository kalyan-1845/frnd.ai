# 🤖 Leo AI Assistant — Complete User Guide

> **Project**: Frnd.AI (Leo)
> **Version**: BKR 2.0

---

## 📋 Table of Contents

1. [Setup & Installation](#-setup--installation)
2. [Starting the Assistant](#-starting-the-assistant)
3. [Wake Word Activation](#-wake-word-activation)
4. [Voice Commands Reference](#-voice-commands-reference)
5. [Messaging & Communication](#-messaging--communication)
6. [File & Folder Management](#-file--folder-management)
7. [System Control](#-system-control)
8. [Web & Research](#-web--research)
9. [Text & NLP Tools](#-text--nlp-tools)
10. [Entertainment](#-entertainment)
11. [Advanced AI Features](#-advanced-ai-features)
12. [Troubleshooting](#-troubleshooting)

---

## 🔧 Setup & Installation

### Prerequisites
- **Python 3.10+** installed
- **Ollama** installed and running with `llama3` model
- Windows 10/11

### Step 1: Install Dependencies
```bash
cd "ai-assistant - Copy"
pip install -r requirements.txt
```

### Step 2: Install Additional Packages (for advanced features)
```bash
pip install chromadb opencv-python mediapipe pygame
```

### Step 3: Verify Ollama is Running
```bash
ollama list
```
Make sure `llama3` appears in the list. If not:
```bash
ollama pull llama3
```

---

## 🚀 Starting the Assistant

```bash
python main.py
```

**What happens on startup:**
1. Ollama connects to the LLM (`llama3`)
2. Brain Controller initializes with 78 tools
3. Avatar visual window opens (Infinity Core UI)
4. Voice listener starts (microphone activates)
5. Webcam emotion tracker starts (background)
6. Leo says: *"What do you need today, Kalyan?"*

---

## 🎤 Wake Word Activation

Leo uses a **custom wake word** to avoid responding to background noise.

| Action | What to Say |
|--------|-------------|
| **Activate Leo** | `"Hey Leo"` followed by your command |
| **Example** | `"Hey Leo, what time is it?"` |

> **Note**: Leo will ignore everything until you say "Hey Leo" first.
> The wake word is stripped from your command before processing.

---

## 📱 Messaging & Communication

### WhatsApp

| Action | Voice Command |
|--------|---------------|
| **Open WhatsApp** | `"Hey Leo, open WhatsApp"` |
| **Send message by phone number** | `"Hey Leo, send WhatsApp message to 9876543210 saying Happy Birthday"` |
| **Send message by name** | `"Hey Leo, send a message to Ravi saying Hey bro"` |
| **Quick message** | `"Hey Leo, text Ravi on WhatsApp saying see you tomorrow"` |

**How it works:**
- If you give a **phone number**, Leo opens `wa.me` link directly
- If you give a **name**, Leo opens WhatsApp Web for you to search the contact
- The message is pre-filled automatically

### Gmail & Email

| Action | Voice Command |
|--------|---------------|
| **Open Gmail** | `"Hey Leo, open Gmail"` |
| **Check email** | `"Hey Leo, check my email"` |
| **Compose email** | `"Hey Leo, compose an email to john@gmail.com about Meeting Tomorrow"` |

### Telegram

| Action | Voice Command |
|--------|---------------|
| **Open Telegram** | `"Hey Leo, open Telegram"` |

### Phone Link (Call/SMS)

| Action | Voice Command |
|--------|---------------|
| **Open Phone Link** | `"Hey Leo, open Phone Link"` |
| **Call a friend** | `"Hey Leo, call a friend"` |
| **Make a call** | `"Hey Leo, make a call"` |
| **Send SMS** | `"Hey Leo, send SMS to Ravi"` |
| **Video call** | `"Hey Leo, video call Ravi"` |

> **Requirement**: Windows Phone Link app must be set up and connected to your phone.

---

## 📁 File & Folder Management

| Action | Voice Command |
|--------|---------------|
| **Create folder** | `"Hey Leo, create a folder called Projects on Desktop"` |
| **Create file** | `"Hey Leo, create a file called notes.txt"` |
| **Open folder** | `"Hey Leo, open my Documents folder"` |
| **Open Downloads** | `"Hey Leo, open Downloads"` |
| **Open Desktop** | `"Hey Leo, open Desktop"` |
| **Find a file** | `"Hey Leo, find file called report.pdf"` |
| **Move file** | `"Hey Leo, move file notes.txt to Documents"` |
| **Copy file** | `"Hey Leo, copy file data.csv to Desktop"` |
| **Delete file** | `"Hey Leo, delete file old_backup.zip"` |
| **Rename file** | `"Hey Leo, rename file draft.txt to final.txt"` |
| **List files** | `"Hey Leo, list files in Documents"` |
| **Zip files** | `"Hey Leo, zip the Projects folder"` |
| **Unzip files** | `"Hey Leo, unzip archive.zip"` |
| **Organize folder** | `"Hey Leo, organize my Downloads folder"` |
| **Clean temp files** | `"Hey Leo, clean temp files"` |

---

## 💻 System Control

### Power & Display

| Action | Voice Command |
|--------|---------------|
| **Lock screen** | `"Hey Leo, lock the screen"` |
| **Turn off display** | `"Hey Leo, turn off the display"` |
| **Sleep** | `"Hey Leo, go to sleep"` |
| **Shutdown** | `"Hey Leo, shut down the computer"` |
| **Restart** | `"Hey Leo, restart the system"` |
| **Cancel shutdown** | `"Hey Leo, cancel shutdown"` |

### Display Settings

| Action | Voice Command |
|--------|---------------|
| **Set brightness** | `"Hey Leo, set brightness to 80"` |
| **Increase brightness** | `"Hey Leo, increase brightness"` |
| **Dim screen** | `"Hey Leo, dim the screen"` |
| **Night light** | `"Hey Leo, turn on night light"` |
| **Change wallpaper** | `"Hey Leo, set wallpaper to sunset.jpg"` |

### Volume

| Action | Voice Command |
|--------|---------------|
| **Volume up** | `"Hey Leo, volume up"` |
| **Volume down** | `"Hey Leo, volume down"` |
| **Mute** | `"Hey Leo, mute the volume"` |
| **Unmute** | `"Hey Leo, unmute"` |

### Connectivity

| Action | Voice Command |
|--------|---------------|
| **Toggle Wi-Fi** | `"Hey Leo, turn on Wi-Fi"` or `"turn off Wi-Fi"` |
| **Bluetooth** | `"Hey Leo, open Bluetooth settings"` |
| **Airplane mode** | `"Hey Leo, airplane mode"` |

### System Information

| Action | Voice Command |
|--------|---------------|
| **Full system status** | `"Hey Leo, system status"` |
| **Battery level** | `"Hey Leo, how much battery?"` |
| **CPU usage** | `"Hey Leo, CPU usage"` |
| **RAM usage** | `"Hey Leo, how much RAM?"` |
| **Disk space** | `"Hey Leo, how much disk space?"` |
| **Network info** | `"Hey Leo, network status"` or `"IP address"` |
| **Uptime** | `"Hey Leo, how long has the system been running?"` |

### App & Process Management

| Action | Voice Command |
|--------|---------------|
| **Open any app** | `"Hey Leo, open Chrome"` / `"open Calculator"` / `"open Notepad"` |
| **List running apps** | `"Hey Leo, show running apps"` |
| **Kill a process** | `"Hey Leo, kill Chrome"` |
| **Take screenshot** | `"Hey Leo, take a screenshot"` |
| **Open Settings** | `"Hey Leo, open Windows settings"` |
| **Empty Recycle Bin** | `"Hey Leo, empty the recycle bin"` |

---

## 🌐 Web & Research

| Action | Voice Command |
|--------|---------------|
| **Google search** | `"Hey Leo, search for machine learning tutorials"` |
| **Open any website** | `"Hey Leo, go to github.com"` |
| **Wikipedia** | `"Hey Leo, tell me about Albert Einstein"` or `"who is Elon Musk?"` |
| **Define a word** | `"Hey Leo, define quantum computing"` |
| **Scrape a website** | `"Hey Leo, scrape content from example.com"` |
| **Open YouTube** | `"Hey Leo, open YouTube"` |
| **Play on YouTube** | `"Hey Leo, play Interstellar soundtrack on YouTube"` |

---

## ✍️ Text & NLP Tools

| Action | Voice Command |
|--------|---------------|
| **Summarize text** | `"Hey Leo, summarize this text: ..."` |
| **Grammar check** | `"Hey Leo, correct grammar of ..."` |
| **Word count** | `"Hey Leo, count words in ..."` |
| **Calculate** | `"Hey Leo, calculate 125 * 48 + 300"` |
| **Generate password** | `"Hey Leo, generate a strong password"` |
| **Password (custom length)** | `"Hey Leo, generate a password of 24 characters"` |
| **Translate text** | `"Hey Leo, translate hello to Telugu"` |
| **Save a note** | `"Hey Leo, save a note: Buy groceries tomorrow"` |
| **Read notes** | `"Hey Leo, read my notes"` |
| **Convert case** | `"Hey Leo, convert to uppercase: hello world"` |

---

## 🎭 Entertainment

| Action | Voice Command |
|--------|---------------|
| **Tell a joke** | `"Hey Leo, tell me a joke"` |
| **Inspirational quote** | `"Hey Leo, give me a quote"` |
| **Play music** | `"Hey Leo, play Shape of You on YouTube"` |
| **Watch video** | `"Hey Leo, play funny cat videos on YouTube"` |

---

## 🧠 Advanced AI Features

### 1. Long-Term Memory (Vector Database)
Leo remembers **everything** you've ever discussed across sessions using ChromaDB.

- **Automatic**: Every conversation is saved and recalled
- **How to test**: Ask Leo about something you discussed days ago: `"Hey Leo, what did we talk about last time?"`

### 2. Live Emotion Tracking (Webcam)
Leo reads your facial expressions and adapts its tone.

- **Automatic**: Runs silently in background via webcam
- **Detected emotions**: Smiling/Happy, Surprised/Talking, Frowning/Stressed, Neutral
- **How to test**: Smile while talking to Leo — it will respond more cheerfully!

### 3. Infinity Core Visual UI
The glowing energy orb in the center of the window:

- **Idle**: Soft pulsing blue/purple glow with orbital ring
- **Speaking**: Expands with energy sparks and neural mesh lines
- **Sound-reactive**: Responds to voice amplitude in real-time

### 4. Custom Wake Word
- Default: `"Hey Leo"`
- Change in `config.py` → `WAKE_WORD = "your custom phrase"`

---

## 🛠️ Troubleshooting

### Leo doesn't respond to voice
1. Make sure your microphone is connected and set as default
2. Check if wake word is correct: say `"Hey Leo"` clearly
3. Verify Deepgram/Vosk STT is configured in `config.py`

### WhatsApp message doesn't send automatically
- Leo opens WhatsApp Web with the message pre-filled
- You need to **press Enter** to send (for security reasons)
- For phone numbers, use format: `9876543210` (with country code if needed)

### Phone Link not working
1. Open **Phone Link** app on Windows manually first
2. Connect your Android/iPhone to Phone Link
3. Then ask Leo: `"Hey Leo, open Phone Link"`

### Webcam emotion tracking not working
- Install: `pip install opencv-python mediapipe`
- Make sure webcam is not used by another app
- Leo will show `"Camera Offline"` if webcam is unavailable

### Ollama not connecting
```bash
ollama serve                 # Start Ollama server
ollama list                  # Check available models
ollama pull llama3           # Download if missing
```

### General tips
- Speak clearly and naturally
- Wait for Leo to finish speaking before giving next command
- Use `"Hey Leo, stop"` to exit the assistant
- Check `logs/` folder for error details

---

## ⚡ Quick Reference Card

```
╔══════════════════════════════════════════════════════╗
║  LEO AI ASSISTANT — QUICK COMMANDS                  ║
╠══════════════════════════════════════════════════════╣
║  "Hey Leo, what time is it?"                        ║
║  "Hey Leo, open WhatsApp"                           ║
║  "Hey Leo, send message to Ravi saying hi"          ║
║  "Hey Leo, call a friend"                           ║
║  "Hey Leo, create folder Projects on Desktop"       ║
║  "Hey Leo, search for Python tutorials"             ║
║  "Hey Leo, play music on YouTube"                   ║
║  "Hey Leo, take a screenshot"                       ║
║  "Hey Leo, system status"                           ║
║  "Hey Leo, volume up"                               ║
║  "Hey Leo, lock the screen"                         ║
║  "Hey Leo, tell me a joke"                          ║
║  "Hey Leo, stop"                                    ║
╚══════════════════════════════════════════════════════╝
```

---

*Made with ❤️ by Kalyan — Powered by Ollama + LLaMA 3*
