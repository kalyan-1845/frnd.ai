"""
Security Layer — Activity Monitor
Tracks user activity, detects anomalies, and logs security events.
"""

import time
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import deque
from dataclasses import dataclass, field

# Configuration
LOG_FILE = "logs/security.log"
ACTIVITY_LOG = "logs/activity.json"
MAX_ACTIVITY_HISTORY = 1000

@dataclass
class SecurityEvent:
    """Represents a security-related event."""
    timestamp: float
    event_type: str
    severity: str  # low, medium, high, critical
    description: str
    user: str = "system"
    metadata: Dict[str, Any] = field(default_factory=dict)

class ActivityMonitor:
    """
    Monitors user activity and detects anomalous patterns.
    """
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        self.log_file = os.path.join(log_dir, "security.log")
        self.activity_file = os.path.join(log_dir, "activity.json")
        
        # Activity tracking
        self._activity_history: deque = deque(maxlen=MAX_ACTIVITY_HISTORY)
        self._command_count: Dict[str, int] = {}
        self._failed_commands: List[str] = []
        
        # Rate limiting
        self._command_timestamps: deque = deque(maxlen=100)
        self._max_commands_per_minute = 30
        
        # Anomaly detection thresholds
        self._repeated_commands_threshold = 5
        self._rapid_fire_threshold = 10  # commands in 10 seconds
        
        # Load existing activity
        self._load_activity()
    
    def _load_activity(self):
        """Load activity history from disk."""
        if os.path.exists(self.activity_file):
            try:
                with open(self.activity_file, 'r') as f:
                    data = json.load(f)
                    self._activity_history = deque(
                        data.get("history", []), 
                        maxlen=MAX_ACTIVITY_HISTORY
                    )
            except Exception:
                pass
    
    def _save_activity(self):
        """Persist activity to disk."""
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            with open(self.activity_file, 'w') as f:
                json.dump({
                    "history": list(self._activity_history)
                }, f)
        except Exception:
            pass
    
    def _log_event(self, event: SecurityEvent):
        """Log security event to file."""
        try:
            os.makedirs(self.log_dir, exist_ok=True)
            with open(self.log_file, 'a') as f:
                f.write(f\"[{datetime.fromtimestamp(event.timestamp).isoformat()}] \"
                       f\"[{event.severity.upper()}] {event.event_type}: {event.description}\\n\")
        except Exception:
            pass
    
    def track_command(self, command: str, user: str = "user", 
                     success: bool = True) -> Dict[str, Any]:
        """
        Track a command execution and check for anomalies.
        
        Returns:
            Dict with 'allowed' (bool), 'reason' (str), 'risk_level' (str)
        """
        timestamp = time.time()
        cmd_lower = command.lower().strip()
        
        # Rate limiting check
        self._command_timestamps.append(timestamp)
        recent_commands = [
            t for t in self._command_timestamps 
            if timestamp - t < 60
        ]
        
        if len(recent_commands) > self._max_commands_per_minute:
            event = SecurityEvent(
                timestamp=timestamp,
                event_type="rate_limit",
                severity="high",
                description=f"Rate limit exceeded: {len(recent_commands)} commands/minute",
                user=user
            )
            self._log_event(event)
            return {
                "allowed": False,
                "reason": "Rate limit exceeded. Please slow down.",
                "risk_level": "high"
            }
        
        # Track command count
        self._command_count[cmd_lower] = self._command_count.get(cmd_lower, 0) + 1
        
        # Check for repeated commands (possible loop/attack)
        if self._command_count[cmd_lower] > self._repeated_commands_threshold:
            event = SecurityEvent(
                timestamp=timestamp,
                event_type="repeated_command",
                severity="medium",
                description=f"Command repeated {self._command_count[cmd_lower]} times: {command[:50]}",
                user=user
            )
            self._log_event(event)
        
        # Track failed commands
        if not success:
            self._failed_commands.append({
                "command": command,
                "timestamp": timestamp,
                "user": user
            })
            
            # Check for brute force pattern
            if len(self._failed_commands) >= 5:
                recent_failures = [
                    f for f in self._failed_commands 
                    if timestamp - f["timestamp"] < 60
                ]
                if len(recent_failures) >= 5:
                    event = SecurityEvent(
                        timestamp=timestamp,
                        event_type="potential_brute_force",
                        severity="critical",
                        description=f"Multiple failed commands detected: {len(recent_failures)} in last minute",
                        user=user
                    )
                    self._log_event(event)
                    self._failed_commands = []  # Reset after alert
        
        # Record activity
        activity = {
            "timestamp": timestamp,
            "command": command,
            "user": user,
            "success": success
        }
        self._activity_history.append(activity)
        
        # Periodically save
        if len(self._activity_history) % 100 == 0:
            self._save_activity()
        
        return {
            "allowed": True,
            "reason": "",
            "risk_level": "low"
        }
    
    def get_activity_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get activity summary for the last N hours."""
        cutoff = time.time() - (hours * 3600)
        
        recent = [
            a for a in self._activity_history 
            if a.get("timestamp", 0) > cutoff
        ]
        
        successful = sum(1 for a in recent if a.get("success"))
        failed = len(recent) - successful
        
        # Most used commands
        command_freq: Dict[str, int] = {}
        for a in recent:
            cmd = a.get("command", "")[:30]
            command_freq[cmd] = command_freq.get(cmd, 0) + 1
        
        top_commands = sorted(
            command_freq.items(), 
            key=lambda x: x[1], 
            reverse=True
        )[:10]
        
        return {
            "period_hours": hours,
            "total_commands": len(recent),
            "successful": successful,
            "failed": failed,
            "success_rate": f\"{(successful/len(recent)*100):.1f}%\" if recent else "N/A",
            "top_commands": top_commands,
            "unique_users": len(set(a.get("user") for a in recent))
        }
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent security events."""
        events = []
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-limit:]:
                        events.append(line.strip())
            except Exception:
                pass
        return events
    
    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """Detect anomalous patterns in recent activity."""
        anomalies = []
        now = time.time()
        
        # Check for unusual command patterns
        recent_window = 300  # 5 minutes
        recent = [
            a for a in self._activity_history 
            if now - a.get("timestamp", 0) < recent_window
        ]
        
        if len(recent) > 50:
            anomalies.append({
                "type": "high_activity",
                "severity": "medium",
                "description": f"Unusually high activity: {len(recent)} commands in 5 minutes"
            })
        
        # Check for repeated identical commands
        command_sequence = [a.get("command", "") for a in recent[-10:]]
        if len(command_sequence) >= 5:
            if len(set(command_sequence)) == 1:
                anomalies.append({
                    "type": "repeated_commands",
                    "severity": "medium",
                    "description": "Same command repeated multiple times"
                })
        
        return anomalies


# Global instance
_monitor = None

def get_monitor() -> ActivityMonitor:
    """Get global monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = ActivityMonitor()
    return _monitor
