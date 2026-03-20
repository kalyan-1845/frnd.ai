"""
J.A.R.V.I.S. Messaging Module
Send messages via WhatsApp Web, open mail clients, and draft emails.
"""
import webbrowser
import urllib.parse
import time
import subprocess
import os
from core.logger import log_event, log_error


def send_whatsapp_message(target: str) -> tuple:
    """
    Opens WhatsApp Web with a pre-filled message.
    Format: target = "contact_name|message" OR just "message" (to open blank).
    
    Note: Full automation requires pyautogui; this opens WhatsApp Web
    with the message pre-filled in the URL for the user to send.
    """
    try:
        # Parse target: "contact|message" or just "message"
        if "|" in target:
            parts = target.split("|", 1)
            contact = parts[0].strip()
            message = parts[1].strip()
        else:
            contact = ""
            message = target.strip()

        if not message:
            # Just open WhatsApp Web
            webbrowser.open("https://web.whatsapp.com")
            return True, "Opened WhatsApp Web, Sir."

        encoded_msg = urllib.parse.quote(message)

        if contact:
            # Try to open WhatsApp with a phone number (if contact is a number)
            digits = "".join(filter(str.isdigit, contact))
            if digits:
                url = f"https://wa.me/{digits}?text={encoded_msg}"
                webbrowser.open(url)
                return True, f"Opened WhatsApp with message to {contact}. Please confirm and send, Sir."
            else:
                # Open WhatsApp Web and let user navigate
                webbrowser.open(f"https://web.whatsapp.com")
                return True, f"Opened WhatsApp Web. Search for '{contact}' and the message is ready to paste: {message}"
        else:
            # Open WhatsApp Web new chat with message
            url = f"https://web.whatsapp.com/send?text={encoded_msg}"
            webbrowser.open(url)
            return True, f"Opened WhatsApp Web with message pre-filled. Please select a contact and send, Sir."

    except Exception as e:
        log_error("Messaging.whatsapp", e)
        return False, f"Failed to open WhatsApp: {e}"


def open_whatsapp(target: str = "") -> tuple:
    """Opens WhatsApp Web or the desktop app."""
    try:
        # Try desktop app first
        try:
            subprocess.Popen("WhatsApp.exe", shell=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "Opened WhatsApp desktop application, Sir."
        except Exception:
            pass
        # Fallback to web
        webbrowser.open("https://web.whatsapp.com")
        return True, "Opened WhatsApp Web, Sir."
    except Exception as e:
        return False, f"Could not open WhatsApp: {e}"


def open_gmail(target: str = "") -> tuple:
    """Opens Gmail in the default browser."""
    try:
        webbrowser.open("https://mail.google.com/mail/u/0/#inbox")
        return True, "Opened Gmail, Sir."
    except Exception as e:
        return False, f"Could not open Gmail: {e}"


def compose_email(target: str) -> tuple:
    """
    Opens the default mail client or Gmail compose window.
    target format: "to@email.com|Subject|Body" OR just subject/body text.
    """
    try:
        parts = target.split("|")
        to = urllib.parse.quote(parts[0].strip()) if len(parts) > 0 else ""
        subject = urllib.parse.quote(parts[1].strip()) if len(parts) > 1 else "Message from J.A.R.V.I.S."
        body = urllib.parse.quote(parts[2].strip()) if len(parts) > 2 else ""

        # Try mailto: first (opens default mail client)
        mailto = f"mailto:{to}?subject={subject}&body={body}"
        os.startfile(mailto)
        return True, f"Opened email composer, Sir. Please review and send."
    except Exception:
        # Fallback: Gmail compose
        try:
            to_raw = target.split("|")[0].strip() if "|" in target else ""
            subj = target.split("|")[1].strip() if "|" in target and len(target.split("|")) > 1 else "Message"
            url = f"https://mail.google.com/mail/?view=cm&to={urllib.parse.quote(to_raw)}&su={urllib.parse.quote(subj)}"
            webbrowser.open(url)
            return True, "Opened Gmail compose window, Sir."
        except Exception as e:
            return False, f"Could not open email client: {e}"


def open_telegram(target: str = "") -> tuple:
    """Opens Telegram desktop or web."""
    try:
        subprocess.Popen("Telegram.exe", shell=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "Opened Telegram, Sir."
    except Exception:
        webbrowser.open("https://web.telegram.org/")
        return True, "Opened Telegram Web, Sir."
