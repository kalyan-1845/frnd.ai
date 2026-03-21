"""
Advanced Visual Window for BKR 2.0 - Human Clone Lip-Sync Edition.

Features:
- Real-time lip-sync driven animation (8 viseme mouth shapes)
- Natural head movements and micro-expressions
- Smooth transitions between all animation states
- Audio amplitude-driven mouth openness
- Human-like breathing and idle animations
"""
import random
import sys
import threading
import math
import os
import json
import html

import config
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QPixmap, QTransform, QPainter, QColor, QLinearGradient, QRadialGradient
from PyQt5.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

import advanced.voice
from core.companion_style import extract_emotion_tag, tag_to_avatar_state


class AssistantWindow(QMainWindow):
    msg_signal = pyqtSignal(str, str)
    status_signal = pyqtSignal(str)
    mic_state_signal = pyqtSignal(bool)

    def __init__(self, command_queue=None):
        super().__init__()
        self.command_queue = command_queue
        self.msg_signal.connect(self.append_message)
        self.status_signal.connect(self._set_status_text)
        self.mic_state_signal.connect(self._set_mic_enabled)

        window_only = bool(getattr(config, "GUI_WINDOW_ONLY", True))
        self.is_companion = bool(getattr(config, "DESKTOP_COMPANION_MODE", False)) and not window_only
        self.window_only = window_only
        self.show_chat = bool(getattr(config, "DESKTOP_SHOW_CHAT", True))
        self.enable_3d = bool(getattr(config, "AVATAR_3D_MODE", True))
        self.motion_intensity = max(
            0.6,
            min(3.0, float(getattr(config, "AVATAR_3D_INTENSITY", 1.8))),
        )
        self._drag_pos = None
        self._manual_listening = False

        # ==================== LIP-SYNC ANIMATION STATE ====================
        self.is_speaking = False
        self.current_mood = "neutral"
        self.expression_ticks = 0
        self.expression_state = "idle"
        
        # Lip-sync related
        self.lip_sync_enabled = True
        self.current_viseme = "neutral"
        self.target_viseme = "neutral"
        self.viseme_transition = 1.0  # 0-1, how complete the transition is
        self.audio_amplitude = 0.0
        
        # Viseme frame mapping
        self.viseme_frames = {}
        
        # Animation timing
        self.current_speak_frame = 1
        self.idle_frame_toggle = False
        self.idle_tick = 0
        self.blink_ticks = 0
        self.next_blink_tick = random.randint(18, 42)
        
        # Head movement (human-like natural movement)
        self.head_tilt_x = 0.0  # Left-right tilt
        self.head_tilt_y = 0.0  # Up-down tilt
        self.head_pos_x = 0.0   # Horizontal position drift
        self.head_pos_y = 0.0   # Vertical position drift
        self.head_tilt_dir_x = 1
        self.head_tilt_dir_y = 1
        self.head_pos_dir_x = 1
        self.head_pos_dir_y = 1
        
        # Enhanced 3D Animation Variables
        self.avatar_tilt = 0.0  # Horizontal tilt
        self.avatar_depth = 0.0  # Forward/backward depth
        self.avatar_scale = 1.0  # Scale for depth effect
        self.tilt_dir = 1
        self.depth_dir = 1
        self.breathe_phase = 0.0  # For subtle breathing animation
        self.breathe_speed = 0.03
        
        # Eye tracking (slight movement during speech)
        self.eye_offset_x = 0
        self.eye_offset_y = 0
        
        self._apply_window_mode()
        self._build_ui()
        self._load_frames()

        # Animation timer - faster for smooth lip-sync (50ms)
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.animate)
        self.anim_timer.start(50)

        default_name = str(getattr(config, "DEFAULT_USER_NAME", "Kalyan"))
        self.append_message("Assistant", f"What do you need today, {default_name}?")
        self.update_avatar("idle")

    def _apply_window_mode(self):
        self.setWindowTitle(f"{config.ASSISTANT_NAME} - Global Assistant")
        if self.is_companion:
            self.setFixedSize(430, 650)
            self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        else:
            self.resize(980, 900)
            self.setMinimumSize(780, 700)
            self.setWindowFlags(Qt.Window)

    def _build_ui(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.central_widget.setStyleSheet(
            """
            QWidget { background-color: #15171d; color: #e6e6e6; border-radius: 14px; }
            QTextEdit, QTextBrowser { background-color: #1f2230; border: 1px solid #2f3447; border-radius: 10px; padding: 8px; }
            QLineEdit { background-color: #222738; border: 1px solid #323a54; border-radius: 10px; padding: 8px; color: #e8ebff; }
            QPushButton { background-color: #3f70ff; color: white; border-radius: 10px; padding: 8px 12px; font-weight: bold; }
            QPushButton:hover { background-color: #5a86ff; }
            """
        )

        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(8)

        self.header = QLabel(config.ASSISTANT_NAME)
        self.header.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setStyleSheet("color: #76a7ff;")
        self.layout.addWidget(self.header)

        self.status_label = QLabel("Listening...")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #a9b6d6;")
        self.layout.addWidget(self.status_label)

        # Infinity Core Mastered Widget
        self.core_widget = InfinityCoreWidget()
        self.layout.addWidget(self.core_widget, stretch=2)

        self.chat_area = QTextBrowser()
        self.chat_area.setOpenExternalLinks(True)
        self.chat_area.setFont(QFont("Segoe UI", 11))
        if self.show_chat:
            self.layout.addWidget(self.chat_area, stretch=1)
        else:
            self.chat_area.hide()

        self.input_layout = QHBoxLayout()
        self.input_field = QLineEdit()
        self.input_field.setFont(QFont("Segoe UI", 11))
        self.input_field.setPlaceholderText("Type or speak in any language...")
        self.input_field.returnPressed.connect(self.send_message)

        self.mic_btn = QPushButton("Mic")
        self.mic_btn.clicked.connect(self.manual_mic_capture)

        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self.send_message)

        self.input_layout.addWidget(self.mic_btn)
        self.input_layout.addWidget(self.input_field)
        self.input_layout.addWidget(self.send_btn)
        self.layout.addLayout(self.input_layout)

        self.mic_hint = QLabel("Global assistant mode: AI, coding, languages, research, and well-being")
        self.mic_hint.setAlignment(Qt.AlignCenter)
        self.mic_hint.setStyleSheet("color: #8f9fc3; font-size: 10px;")
        self.layout.addWidget(self.mic_hint)

        if self.is_companion:
            self._position_in_corner()

    def _load_frames(self):
        """Load all animation frames including visemes for lip-sync."""
        assets_dir = os.path.dirname(config.ASSISTANT_AVATAR_PATH)
        
        # Basic frames
        self.frames = {
            "idle": QPixmap(config.ASSISTANT_AVATAR_PATH),
            "idle_shift": QPixmap(getattr(config, "ASSISTANT_IDLE_SHIFT", config.ASSISTANT_AVATAR_PATH)),
            "idle_breath": QPixmap(os.path.join(assets_dir, "idle_breath.png")),
            "blink": QPixmap(getattr(config, "ASSISTANT_BLINK", config.ASSISTANT_AVATAR_PATH)),
            "blink_quick": QPixmap(os.path.join(assets_dir, "blink_quick.png")),
            "eyes_open": QPixmap(os.path.join(assets_dir, "eyes_open.png")),
            "smile": QPixmap(os.path.join(assets_dir, "smile.png")),
            "speak_1": QPixmap(config.ASSISTANT_SPEAK_1),
            "speak_2": QPixmap(config.ASSISTANT_SPEAK_2),
        }
        
        # Load viseme frames for lip-sync
        viseme_names = ["neutral", "A", "E", "I", "O", "U", "MBP", "STH"]
        for viseme in viseme_names:
            frame_path = os.path.join(assets_dir, f"viseme_{viseme}.png")
            if os.path.exists(frame_path):
                self.viseme_frames[viseme] = QPixmap(frame_path)
                self.frames[f"viseme_{viseme}"] = QPixmap(frame_path)
        
        # Fallback to basic frames if visemes not available
        for key in self.frames:
            if self.frames[key].isNull():
                self.frames[key] = QPixmap(config.ASSISTANT_SPEAK_1)
        
        # Ensure viseme frames have fallbacks
        for viseme in viseme_names:
            if viseme not in self.viseme_frames or self.viseme_frames[viseme].isNull():
                self.viseme_frames[viseme] = self.frames.get("idle", QPixmap(config.ASSISTANT_AVATAR_PATH))

        try:
            loaded_visemes = sum(1 for v in self.viseme_frames.values() if not v.isNull())
            print(
                f"[Avatar] 3D={'on' if self.enable_3d else 'off'} "
                f"intensity={self.motion_intensity:.2f} visemes={loaded_visemes}"
            )
        except Exception:
            pass

    def _position_in_corner(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        margin = int(getattr(config, "DESKTOP_COMPANION_MARGIN", 16))
        corner = str(getattr(config, "DESKTOP_COMPANION_CORNER", "bottom_right")).lower()

        if corner == "top_left":
            x = geo.left() + margin
            y = geo.top() + margin
        elif corner == "top_right":
            x = geo.right() - self.width() - margin
            y = geo.top() + margin
        elif corner == "bottom_left":
            x = geo.left() + margin
            y = geo.bottom() - self.height() - margin
        else:
            x = geo.right() - self.width() - margin
            y = geo.bottom() - self.height() - margin
        self.move(x, y)

    def closeEvent(self, event):
        print("Closing application...")
        os._exit(0)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.is_companion:
            self._position_in_corner()

    def mousePressEvent(self, event):
        if self.is_companion and event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.is_companion and (event.buttons() & Qt.LeftButton) and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def _get_viseme_frame(self, viseme: str) -> QPixmap:
        """Get the appropriate viseme frame with fallback."""
        if viseme in self.viseme_frames:
            frame = self.viseme_frames[viseme]
            if not frame.isNull():
                return frame
        
        # Fallback to basic speaking frames based on mouth openness
        if viseme in ["A", "O"]:  # Very open
            return self.frames.get("speak_2", self.frames["idle"])
        elif viseme in ["E", "I"]:  # Medium
            return self.frames.get("speak_1", self.frames["idle"])
        elif viseme in ["MBP", "U"]:  # Closed
            return self.frames.get("idle", self.frames["idle"])
        else:
            return self.frames.get("speak_1", self.frames["idle"])

    def update_avatar(self, state: str, mood: str = "neutral", custom_viseme: str = None):
        """Update avatar with the given state (Now replaced by SineWaveWidget)."""
        pass

    def animate(self):
        """Main animation loop - runs every 50ms."""
        lip_state = advanced.voice.get_lip_sync_state()
        self.is_speaking = lip_state['is_speaking']
        self.audio_amplitude = lip_state['amplitude']
        
        if hasattr(self, "core_widget"):
            self.core_widget.update_core()

    def _set_status_text(self, text: str):
        self.status_label.setText(text)

    def _set_mic_enabled(self, enabled: bool):
        self.mic_btn.setEnabled(enabled)

    def manual_mic_capture(self):
        if self._manual_listening:
            return
        self._manual_listening = True
        self._set_mic_enabled(False)
        self.status_signal.emit("Mic active... speak now")
        worker = threading.Thread(target=self._manual_listen_worker, daemon=True)
        worker.start()

    def _manual_listen_worker(self):
        try:
            heard = advanced.voice.listen()
            if heard and heard.strip():
                text = heard.strip()
                self.msg_signal.emit("You", text)
                if self.command_queue:
                    self.command_queue.put(text)
        except Exception:
            pass
        finally:
            self._manual_listening = False
            self.mic_state_signal.emit(True)
            self.status_signal.emit("Listening...")

    def send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return
        self.append_message("You", text)
        self.input_field.clear()
        if self.command_queue:
            self.command_queue.put(text)
        else:
            print(f"[UI_INPUT] {text}")
            sys.stdout.flush()

    def append_message(self, role, text):
        if self.chat_area.isHidden():
            return

        body_text = text or ""
        sources = []
        marker = "\n[[BKR_SOURCES]]"
        if marker in body_text:
            body_text, _, source_blob = body_text.partition(marker)
            try:
                decoded = json.loads(source_blob.strip())
                if isinstance(decoded, list):
                    sources = decoded
            except Exception:
                sources = []

        if role == "Assistant":
            tag, _ = extract_emotion_tag(body_text)
            if tag:
                self.current_mood = tag.lower()
                self.expression_state = tag_to_avatar_state(tag)
                self.expression_ticks = 16

        color = "#76a7ff" if role == "Assistant" else "#f0f2ff"
        safe_text = html.escape(body_text).replace("\n", "<br>")
        source_html = ""
        if sources:
            cards = [
                '<div style="margin-top:8px; padding:8px; background:#1b2030; border:1px solid #2e3752; border-radius:8px;">',
                '<div style="color:#9bb8ff; font-size:10px; font-weight:bold; margin-bottom:4px;">Sources</div>',
            ]
            for item in sources[:3]:
                label = html.escape(str(item.get("label", "Source")))
                url = html.escape(str(item.get("url", "")))
                if url:
                    cards.append(
                        f'<div style="margin-top:3px;"><a href="{url}" style="color:#9ec4ff; text-decoration:none;">{label}</a>'
                        f'<div style="color:#7f8aa8; font-size:10px;">{url}</div></div>'
                    )
            cards.append("</div>")
            source_html = "".join(cards)

        self.chat_area.append(f'<b style="color: {color};">{role}:</b> {safe_text}<br>{source_html}<br>')
        self.chat_area.ensureCursorVisible()


class Particle:
    """Represents a single energy spark radiating from the Infinity Core."""
    def __init__(self, x, y, angle, speed, color):
        self.x = x
        self.y = y
        self.angle = angle
        self.speed = speed
        self.life = 1.0  # 1.0 to 0.0
        self.decay = random.uniform(0.015, 0.035)
        self.color = color

    def update(self):
        self.x += math.cos(self.angle) * self.speed
        self.y += math.sin(self.angle) * self.speed
        self.life -= self.decay
        return self.life > 0

class InfinityCoreWidget(QWidget):
    """
    Infinity Core Mastered UI - A futuristic energy sphere with sound-reactive particles.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(450)
        self.time_step = 0.0
        self.amplitude_multiplier = 0.05
        self.particles = []
        
        # Performance: Pre-calculate colors for gradients
        self.colors = [
            QColor(0, 242, 255, 180),   # Cyan
            QColor(112, 0, 255, 140),   # Purple
            QColor(0, 124, 255, 100),   # Blue
            QColor(255, 255, 255, 200)  # White core
        ]
        
    def update_core(self):
        self.time_step += 0.2
        import advanced.voice
        lip_state = advanced.voice.get_lip_sync_state()
        target_amp = lip_state['amplitude'] if lip_state['is_speaking'] else 0.04
        
        # Smooth physics
        self.amplitude_multiplier += (target_amp - self.amplitude_multiplier) * 0.2
        
        # Spawn particles when amplitude is high
        if target_amp > 0.08 and len(self.particles) < 40:
            for _ in range(int(target_amp * 8)):
                angle = random.uniform(0, 2 * math.pi)
                speed = random.uniform(2, 6)
                color = random.choice(self.colors)
                w, h = self.width(), self.height()
                self.particles.append(Particle(w/2, h/2, angle, speed, color))
        
        # Update existing particles
        self.particles = [p for p in self.particles if p.update()]
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        # 1. Deep space background
        painter.fillRect(0, 0, w, h, QColor(10, 12, 18))

        # Reset to standard blending for all core drawing
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        # 2. Always-visible ambient glow (even when idle)
        ambient_r = min(w, h) * 0.35
        ambient_grad = QRadialGradient(cx, cy, ambient_r)
        ambient_grad.setColorAt(0.0, QColor(0, 80, 180, 50))
        ambient_grad.setColorAt(0.5, QColor(50, 0, 120, 25))
        ambient_grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setPen(Qt.NoPen)
        painter.setBrush(ambient_grad)
        painter.drawEllipse(int(cx - ambient_r), int(cy - ambient_r), int(ambient_r * 2), int(ambient_r * 2))

        # 3. Infinity Core: Multi-layered radial gradient orb
        # Base radius is always clearly visible (minimum ~80px), and grows with amplitude
        base_radius = max(60, (min(w, h) * 0.12) + (min(w, h) * 0.25 * self.amplitude_multiplier))
        
        # Layer definitions: outermost to innermost
        core_layers = [
            {"scale": 2.5, "r": 0,   "g": 60,  "b": 200, "a": 30,  "rot_speed": 0.5},
            {"scale": 1.8, "r": 40,  "g": 0,   "b": 160, "a": 55,  "rot_speed": -0.7},
            {"scale": 1.3, "r": 0,   "g": 180, "b": 255, "a": 80,  "rot_speed": 1.1},
            {"scale": 0.8, "r": 80,  "g": 140, "b": 255, "a": 120, "rot_speed": 0.3},
            {"scale": 0.4, "r": 200, "g": 230, "b": 255, "a": 200, "rot_speed": 0.0},
        ]

        for layer in core_layers:
            # Pulsing radius
            rot = layer["rot_speed"]
            pulse = math.sin(self.time_step * rot if rot != 0 else self.time_step * 0.5) * 8
            r = max(4, base_radius * layer["scale"] + pulse * max(0.3, self.amplitude_multiplier))
            
            grad = QRadialGradient(cx, cy, r)
            grad.setColorAt(0.0, QColor(layer["r"], layer["g"], layer["b"], layer["a"]))
            grad.setColorAt(1.0, QColor(layer["r"], layer["g"], layer["b"], 0))
            
            painter.setBrush(grad)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(cx - r), int(cy - r), int(r * 2), int(r * 2))

        # 4. Inner white-hot core (always visible)
        core_r = base_radius * 0.15
        inner_grad = QRadialGradient(cx, cy, core_r)
        inner_grad.setColorAt(0.0, QColor(255, 255, 255, 220))
        inner_grad.setColorAt(0.4, QColor(180, 220, 255, 150))
        inner_grad.setColorAt(1.0, QColor(100, 180, 255, 0))
        painter.setBrush(inner_grad)
        painter.drawEllipse(int(cx - core_r), int(cy - core_r), int(core_r * 2), int(core_r * 2))

        # 5. Particles (Additive glow)
        if self.particles:
            painter.setCompositionMode(QPainter.CompositionMode_Plus)
            for p in self.particles:
                c = QColor(p.color)
                c.setAlpha(max(0, min(255, int(255 * p.life))))
                painter.setPen(Qt.NoPen)
                painter.setBrush(c)
                size = max(2, int(6 * p.life))
                painter.drawEllipse(int(p.x - size/2), int(p.y - size/2), size, size)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        # 6. Neural Mesh Lines (only when active)
        if self.amplitude_multiplier > 0.08:
            line_alpha = min(80, int(self.amplitude_multiplier * 400))
            painter.setPen(QColor(0, 242, 255, line_alpha))
            path_points = 8
            for i in range(path_points):
                angle = (i / path_points) * 2 * math.pi + self.time_step * 0.2
                x1 = cx + math.cos(angle) * (base_radius * 0.6)
                y1 = cy + math.sin(angle) * (base_radius * 0.6)
                x2 = cx + math.cos(angle) * (base_radius * (1.5 + self.amplitude_multiplier * 2))
                y2 = cy + math.sin(angle) * (base_radius * (1.5 + self.amplitude_multiplier * 2))
                painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        # 7. Subtle orbital ring
        ring_r = base_radius * 1.6
        ring_alpha = 25 + int(self.amplitude_multiplier * 60)
        painter.setPen(QColor(0, 200, 255, ring_alpha))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(int(cx - ring_r), int(cy - ring_r), int(ring_r * 2), int(ring_r * 2))



def run_visual_window(queue=None):
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    window = AssistantWindow(queue)
    window.show()
    return app, window


if __name__ == "__main__":
    run_visual_window()
