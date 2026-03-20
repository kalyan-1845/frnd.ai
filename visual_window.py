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
from PyQt5.QtGui import QFont, QPixmap, QTransform, QPainter, QColor, QLinearGradient
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

        self.wave_widget = SineWaveWidget()
        self.layout.addWidget(self.wave_widget)

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
        """Main animation loop - runs every 50ms for smooth lip-sync."""
        
        # Get real-time lip-sync state from voice module
        lip_state = advanced.voice.get_lip_sync_state()
        
        self.is_speaking = lip_state['is_speaking']
        self.audio_amplitude = lip_state['amplitude']
        
        # Update viseme smoothly
        new_target = lip_state.get('target_viseme', 'neutral')
        if new_target != self.target_viseme:
            self.target_viseme = new_target
            self.viseme_transition = 0.0
        
        # Smooth viseme transition
        if self.viseme_transition < 1.0:
            self.viseme_transition = min(1.0, self.viseme_transition + 0.15)
            if self.viseme_transition >= 1.0:
                self.current_viseme = self.target_viseme
        elif self.current_viseme != self.target_viseme:
            self.current_viseme = self.target_viseme

        if self.is_speaking:
            # ==================== SPEAKING MODE ====================
            self._set_status_text("Speaking...")
            motion = self.motion_intensity
            
            # More dynamic head movement when speaking
            self.avatar_tilt += (0.02 * motion) * self.tilt_dir
            if self.avatar_tilt >= (0.12 * motion):
                self.tilt_dir = -1
            elif self.avatar_tilt <= (-0.12 * motion):
                self.tilt_dir = 1
            
            # Head position drift during speech
            self.head_pos_x += (0.3 * motion) * self.head_pos_dir_x
            if self.head_pos_x >= (4.0 * motion):
                self.head_pos_dir_x = -1
            elif self.head_pos_x <= (-4.0 * motion):
                self.head_pos_dir_x = 1

            self.head_pos_y += (0.18 * motion) * self.head_pos_dir_y
            if self.head_pos_y >= (2.5 * motion):
                self.head_pos_dir_y = -1
            elif self.head_pos_y <= (-2.5 * motion):
                self.head_pos_dir_y = 1
            
            # Subtle vertical head movement
            self.head_tilt_y += (0.15 * motion) * self.head_tilt_dir_y
            if self.head_tilt_y >= (2.8 * motion):
                self.head_tilt_dir_y = -1
            elif self.head_tilt_y <= (-2.8 * motion):
                self.head_tilt_dir_y = 1
            
            # Depth movement when speaking
            self.avatar_depth += (0.03 * motion) * self.depth_dir
            if self.avatar_depth >= (2.2 * motion):
                self.depth_dir = -1
            elif self.avatar_depth <= (-2.2 * motion):
                self.depth_dir = 1
            
            # Breathing when speaking
            self.breathe_phase += self.breathe_speed
            self.avatar_scale = 1.0 + (math.sin(self.breathe_phase) * (0.012 * motion))
            
            # Eye movement during speech (looking around slightly)
            self.eye_offset_x = int(math.sin(self.breathe_phase * 2) * 1)
            self.eye_offset_y = int(math.cos(self.breathe_phase * 1.5) * 0.5)
            
            # Choose frame based on lip-sync
            if self.lip_sync_enabled and self.current_viseme:
                # Use viseme frame for realistic lip-sync
                self.update_avatar(f"viseme_{self.current_viseme}", mood="speaking", 
                                  custom_viseme=self.current_viseme)
            else:
                # Fallback to basic speaking frames
                frame_name = f"speak_{self.current_speak_frame}"
                self.update_avatar(frame_name)
                self.current_speak_frame = 2 if self.current_speak_frame == 1 else 1
            
            return

        # ==================== IDLE MODE ====================
        self._set_status_text("Listening...")
        self.current_speak_frame = 1
        self.idle_tick += 1
        
        # Gentle idle head movement
        motion = self.motion_intensity
        self.avatar_tilt += (0.005 * motion) * self.tilt_dir
        if self.avatar_tilt >= (0.06 * motion):
            self.tilt_dir = -1
        elif self.avatar_tilt <= (-0.06 * motion):
            self.tilt_dir = 1
        
        # Very subtle head drift
        self.head_pos_x += (0.1 * motion) * self.head_pos_dir_x
        if self.head_pos_x >= (2.0 * motion):
            self.head_pos_dir_x = -1
        elif self.head_pos_x <= (-2.0 * motion):
            self.head_pos_dir_x = 1

        self.head_pos_y += (0.04 * motion) * self.head_pos_dir_y
        if self.head_pos_y >= (1.2 * motion):
            self.head_pos_dir_y = -1
        elif self.head_pos_y <= (-1.2 * motion):
            self.head_pos_dir_y = 1
        
        # Gentle breathing in idle
        self.breathe_phase += self.breathe_speed * 0.4
        self.avatar_scale = 1.0 + (math.sin(self.breathe_phase) * (0.006 * motion))
        
        # Very subtle depth drift
        self.avatar_depth = math.sin(self.breathe_phase * 0.25) * (0.45 * motion)

        # Handle blinking
        if self.blink_ticks > 0:
            self.update_avatar("blink")
            self.blink_ticks -= 1
            return

        if self.idle_tick >= self.next_blink_tick:
            self.blink_ticks = 2
            self.idle_tick = 0
            self.next_blink_tick = random.randint(18, 45)
            self.update_avatar("blink")
            return

        # Brief expression hold driven by emotion tag in assistant output.
        if self.expression_ticks > 0:
            self.expression_ticks -= 1
            self.update_avatar(self.expression_state)
            return

        # Idle frame toggle
        self.idle_frame_toggle = not self.idle_frame_toggle
        
        # Use breathing frame occasionally
        if self.idle_frame_toggle and random.random() < 0.2:
            self.update_avatar("idle_breath")
        else:
            self.update_avatar("idle_shift" if self.idle_frame_toggle else "idle")

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


class SineWaveWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.time_step = 0
        self.amplitude_multiplier = 0.1
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_wave)
        self.timer.start(30)

    def update_wave(self):
        self.time_step += 0.15
        
        # Pull amplitude from global voice state if speaking, otherwise small idle waves
        import advanced.voice
        lip_state = advanced.voice.get_lip_sync_state()
        target_amp = lip_state['amplitude'] * 2.0 if lip_state['is_speaking'] else 0.1
        
        # Smoothly interpolate amplitude
        self.amplitude_multiplier += (target_amp - self.amplitude_multiplier) * 0.2
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        mid_y = height / 2

        # Draw background
        painter.fillRect(0, 0, width, height, QColor("#15171d"))

        # Base properties
        base_amplitude = (height * 0.4) * self.amplitude_multiplier
        frequency = 0.02
        
        # Defines phase offsets, frequencies, and colors for 3 overlapping waves
        waves = [
            {"phase": self.time_step, "freq": frequency, "amp": base_amplitude, "color": QColor(63, 112, 255, 180)},
            {"phase": self.time_step * 1.2, "freq": frequency * 1.5, "amp": base_amplitude * 0.7, "color": QColor(118, 167, 255, 120)},
            {"phase": self.time_step * 0.8, "freq": frequency * 0.8, "amp": base_amplitude * 1.2, "color": QColor(40, 70, 180, 200)}
        ]

        for wave in waves:
            path = []
            for x in range(0, width + 10, 10):
                # Calculate y position using sine wave
                y = mid_y + math.sin(x * wave["freq"] + wave["phase"]) * wave["amp"]
                # Taper the ends to 0 amplitude
                envelope = math.sin((x / width) * math.pi)
                y = mid_y + (y - mid_y) * envelope
                path.append((x, y))

            # Draw the wave line
            pen = painter.pen()
            pen.setColor(wave["color"])
            pen.setWidthF(2.5)
            painter.setPen(pen)

            for i in range(len(path) - 1):
                painter.drawLine(path[i][0], int(path[i][1]), path[i+1][0], int(path[i+1][1]))


def run_visual_window(queue=None):
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    window = AssistantWindow(queue)
    window.show()
    return app, window


if __name__ == "__main__":
    run_visual_window()
