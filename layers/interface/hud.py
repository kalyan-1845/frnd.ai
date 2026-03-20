"""
Heads-Up Display (HUD) - Non-intrusive Overlay System
====================================================

Provides a transparent overlay for displaying information on top of the user's workspace.
Features:
- System performance indicators
- Reminders
- Notifications
- AI suggestions
- Non-blocking, minimal design, transparent overlay
"""

import logging
from typing import Optional, Dict, Any
from enum import Enum
import time

try:
    from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QVBoxLayout
    from PyQt5.QtCore import Qt, QTimer, QPoint
    from PyQt5.QtGui import QFont, QColor, QPalette
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    logging.warning("PyQt5 not available. HUD functionality will be limited.")

logger = logging.getLogger(__name__)


class HUDPosition(Enum):
    """Positions for HUD display."""
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    TOP_CENTER = "top_center"
    BOTTOM_CENTER = "bottom_center"


class HUDTheme(Enum):
    """Visual themes for HUD."""
    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    MINIMAL = "minimal"


class HUDWidget(QWidget if PYQT_AVAILABLE else object):
    """
    Heads-Up Display widget - transparent overlay window.
    """
    
    def __init__(self, parent=None):
        if not PYQT_AVAILABLE:
            raise ImportError("PyQt5 is required for HUD functionality")
            
        super().__init__(parent)
        self._setup_window()
        self._setup_ui()
        self._setup_timer()
        
        # HUD state
        self.visible = True
        self.position = HUDPosition.TOP_RIGHT
        self.theme = HUDTheme.DEFAULT
        self.content_blocks = []  # List of text blocks to display
        self.last_update = time.time()
        
        logger.info("HUD widget initialized")
    
    def _setup_window(self):
        """Configure window properties for transparent overlay."""
        # Set window flags for overlay behavior
        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |  # Always on top
            Qt.FramelessWindowHint |   # No window frame
            Qt.Tool |                  # Don't show in taskbar
            Qt.X11BypassWindowManagerHint  # Bypass window manager on Linux
        )
        
        # Set attributes for transparency
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)  # Allow mouse events if needed
        
        # Initial size and position
        self.resize(300, 100)
        self.move(50, 50)  # Will be repositioned based on position setting
    
    def _setup_ui(self):
        """Set up the user interface."""
        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.setLayout(self.layout)
        
        # Label for displaying content
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.layout.addWidget(self.label)
        
        # Apply default theme
        self._apply_theme(self.theme)
    
    def _setup_timer(self):
        """Set up update timer for refreshing display."""
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_display)
        self.timer.start(1000)  # Update every second
    
    def _apply_theme(self, theme: HUDTheme):
        """Apply visual theme to HUD."""
        self.theme = theme
        
        if theme == HUDTheme.DEFAULT:
            bg_color = QColor(0, 0, 0, 180)  # Semi-transparent black
            text_color = QColor(255, 255, 255, 255)  # White
        elif theme == HUDTheme.DARK:
            bg_color = QColor(0, 0, 0, 200)
            text_color = QColor(200, 200, 200, 255)
        elif theme == HUDTheme.LIGHT:
            bg_color = QColor(255, 255, 255, 180)
            text_color = QColor(0, 0, 0, 255)
        elif theme == HUDTheme.MINIMAL:
            bg_color = QColor(0, 0, 0, 100)  # Very transparent
            text_color = QColor(255, 255, 255, 200)
        else:
            bg_color = QColor(0, 0, 0, 180)
            text_color = QColor(255, 255, 255, 255)
        
        # Set background
        palette = self.palette()
        palette.setColor(QPalette.Window, bg_color)
        self.setPalette(palette)
        
        # Set text style
        font = QFont()
        font.setPointSize(9)
        font.setFamily("Arial")
        self.label.setFont(font)
        self.label.setStyleSheet(f"color: {text_color.name()};")
    
    def set_position(self, position: HUDPosition):
        """Set HUD position on screen."""
        self.position = position
        self._reposition()
    
    def _reposition(self):
        """Reposition HUD based on current position setting."""
        if not PYQT_AVAILABLE:
            return
            
        screen_geometry = QApplication.desktop().availableGeometry()
        x, y = 0, 0
        
        # Calculate position based on enum
        if self.position == HUDPosition.TOP_LEFT:
            x, y = 10, 10
        elif self.position == HUDPosition.TOP_RIGHT:
            x, y = screen_geometry.width() - self.width() - 10, 10
        elif self.position == HUDPosition.BOTTOM_LEFT:
            x, y = 10, screen_geometry.height() - self.height() - 10
        elif self.position == HUDPosition.BOTTOM_RIGHT:
            x, y = screen_geometry.width() - self.width() - 10, screen_geometry.height() - self.height() - 10
        elif self.position == HUDPosition.TOP_CENTER:
            x, y = (screen_geometry.width() - self.width()) // 2, 10
        elif self.position == HUDPosition.BOTTOM_CENTER:
            x, y = (screen_geometry.width() - self.width()) // 2, screen_geometry.height() - self.height() - 10
        
        self.move(x, y)
    
    def add_content_block(self, title: str, content: str, priority: int = 0):
        """
        Add a content block to display.
        
        Args:
            title: Title of the block
            content: Content to display
            priority: Higher priority items shown first (0=normal, 1=high, 2=urgent)
        """
        block = {
            "title": title,
            "content": content,
            "priority": priority,
            "timestamp": time.time()
        }
        self.content_blocks.append(block)
        self._sort_content_blocks()
        self.last_update = time.time()
    
    def _sort_content_blocks(self):
        """Sort content blocks by priority and timestamp."""
        self.content_blocks.sort(
            key=lambda x: (-x["priority"], -x["timestamp"])
        )
        # Limit to max 5 blocks to prevent clutter
        if len(self.content_blocks) > 5:
            self.content_blocks = self.content_blocks[:5]
    
    def clear_content(self):
        """Clear all content blocks."""
        self.content_blocks.clear()
        self._update_display()
    
    def _update_display(self):
        """Update the HUD display with current content blocks."""
        if not self.visible or not self.content_blocks:
            self.label.setText("")
            return
        
        # Build display text
        display_lines = []
        for block in self.content_blocks:
            # Format: [TIMESTAMP] TITLE: CONTENT
            elapsed = int(time.time() - block["timestamp"])
            if elapsed < 60:
                time_str = f"{elapsed}s"
            elif elapsed < 3600:
                time_str = f"{elapsed//60}m"
            else:
                time_str = f"{elapsed//3600}h"
            
            title = block["title"]
            content = block["content"]
            
            # Truncate long content
            if len(content) > 50:
                content = content[:47] + "..."
            
            display_lines.append(f"[{time_str}] {title}: {content}")
        
        self.label.setText("\n".join(display_lines))
        self.label.adjustSize()
        self.adjustSize()
        self._reposition()  # Ensure position is correct after size change
    
    def show_hud(self):
        """Show the HUD."""
        self.visible = True
        self.show()
        self._update_display()
    
    def hide_hud(self):
        """Hide the HUD."""
        self.visible = False
        self.hide()
    
    def toggle_hud(self):
        """Toggle HUD visibility."""
        if self.visible:
            self.hide_hud()
        else:
            self.show_hud()
    
    def set_theme(self, theme: HUDTheme):
        """Set HUD theme."""
        self.theme = theme
        self._apply_theme(theme)
    
    def update_system_info(self, info_dict: Dict[str, Any]):
        """
        Update HUD with system performance information.
        
        Args:
            info_dict: Dictionary containing system metrics (cpu, memory, etc.)
        """
        # Format system info for display
        lines = []
        for key, value in info_dict.items():
            if isinstance(value, float):
                lines.append(f"{key}: {value:.1f}%")
            else:
                lines.append(f"{key}: {value}")
        
        self.add_content_block("System", "\n".join(lines), priority=1)
    
    def add_notification(self, title: str, message: str, urgency: int = 0):
        """
        Add a notification to HUD.
        
        Args:
            title: Notification title
            message: Notification message
            urgency: 0=normal, 1=high, 2=urgent
        """
        self.add_content_block(title, message, priority=urgency)
    
    def add_ai_suggestion(self, suggestion: str):
        """Add an AI suggestion to HUD."""
        self.add_content_block("AI Suggestion", suggestion, priority=0)


# Global HUD instance (singleton pattern)
_hud_instance = None


def get_hud() -> Optional[HUDWidget]:
    """
    Get the global HUD instance.
    
    Returns:
        HUDWidget instance or None if PyQt5 not available
    """
    global _hud_instance
    if not PYQT_AVAILABLE:
        logger.warning("PyQt5 not available, returning None for HUD")
        return None
    
    if _hud_instance is None:
        _hud_instance = HUDWidget()
    
    return _hud_instance


def initialize_hud() -> bool:
    """
    Initialize the HUD system.
    
    Returns:
        True if successful, False otherwise
    """
    if not PYQT_AVAILABLE:
        logger.error("Cannot initialize HUD: PyQt5 not available")
        return False
    
    try:
        hud = get_hud()
        if hud is None:
            return False
        
        hud.show_hud()
        logger.info("HUD initialized and shown")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize HUD: {e}")
        return False


def shutdown_hud():
    """Shutdown the HUD system."""
    global _hud_instance
    if _hud_instance is not None:
        _hud_instance.hide_hud()
        _hud_instance = None
        logger.info("HUD shutdown")


# Example usage and testing
if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create Qt application
    app = QApplication(sys.argv)
    
    # Create and show HUD
    hud = HUDWidget()
    hud.show_hud()
    
    # Add some test content
    hud.add_content_block("Test", "This is a test HUD message")
    hud.add_notification("Notification", "This is a test notification", urgency=1)
    hud.update_system_info({"CPU": 45.2, "Memory": 62.1, "Disk": 23.5})
    hud.add_ai_suggestion("Consider taking a break - you've been working for 2 hours")
    
    # Run application
    sys.exit(app.exec_())