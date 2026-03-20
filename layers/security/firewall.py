"""
Security Layer — Firewall & Breach Detection
Monitors for suspicious activity and blocks potentially harmful operations.
"""

import re
import os
import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

class ThreatLevel(Enum):
    """Threat severity levels."""
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ThreatReport:
    """Result of a threat assessment."""
    threat_level: ThreatLevel
    blocked: bool
    reason: str
    sanitized_input: str = ""

class Firewall:
    """
    Input validation, command sanitization, and breach detection.
    Acts as a gatekeeper before any command execution.
    """
    
    def __init__(self, config_path: str = "security_config.json"):
        self.config_path = config_path
        self._blocked_patterns: List[re.Pattern] = []
        self._suspicious_patterns: List[re.Pattern] = []
        self._whitelist: List[str] = []
        self._load_config()
        
        # Attack detection
        self._failed_auth_attempts: List[float] = []
        self._suspicious_ips: Dict[str, float] = {}
        self._command_injection_attempts: List[str] = []
        
        # Rate limiting state
        self._rate_limits: Dict[str, List[float]] = {}
        self._blocked_identifiers: Dict[str, float] = {}
    
    def _load_config(self):
        """Load firewall configuration."""
        default_config = {
            "blocked_patterns": [
                r";\s*rm\s+-rf",  # Destructive delete
                r"rm\s+-rf\s+/",   # Root deletion
                r"drop\s+table",   # SQL injection
                r"exec\s*\(",      # Code injection
                r"eval\s*\(",      # Code eval
                r"<script",        # XSS
                r"\.\./",          # Path traversal
                r"\$\(",           # Command substitution
                r"`.*`",           # Command substitution
            ],
            "suspicious_patterns": [
                r"password\s*=",  # Password in plain text
                r"api[_-]?key\s*=", # API key exposure
                r"secret\s*=",     # Secret exposure
                r"localhost.*:.*", # Localhost port scan
                r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", # IP address
            ],
            "whitelist": [
                "open_folder",
                "search_google", 
                "tell_time",
                "tell_date",
                "weather",
                "news",
            ]
        }
        
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
            except Exception:
                config = default_config
        else:
            config = default_config
        
        # Compile patterns
        self._blocked_patterns = [
            re.compile(p, re.IGNORECASE) 
            for p in config.get("blocked_patterns", [])
        ]
        self._suspicious_patterns = [
            re.compile(p, re.IGNORECASE) 
            for p in config.get("suspicious_patterns", [])
        ]
        self._whitelist = config.get("whitelist", [])
    
    def assess_command(self, command: str, action: Optional[str] = None) -> ThreatReport:
        """
        Assess a command for security threats.
        
        Args:
            command: The raw user input
            action: The resolved action/tool name (if known)
            
        Returns:
            ThreatReport with threat level and blocking decision
        """
        original = command
        sanitized = self._sanitize_input(command)
        
        # Check blocked patterns
        for pattern in self._blocked_patterns:
            if pattern.search(command):
                self._log_breach("blocked_pattern", command, pattern.pattern)
                return ThreatReport(
                    threat_level=ThreatLevel.CRITICAL,
                    blocked=True,
                    reason="Command contains blocked pattern",
                    sanitized_input=sanitized
                )
        
        # Check suspicious patterns (warning but allow)
        suspicious_found = []
        for pattern in self._suspicious_patterns:
            if pattern.search(command):
                suspicious_found.append(pattern.pattern)
        
        if suspicious_found:
            self._log_breach("suspicious_pattern", command, str(suspicious_found))
        
        # Check action whitelist
        if action and action not in self._whitelist:
            # Not in whitelist - apply additional scrutiny
            if self._requires_approval(action):
                return ThreatReport(
                    threat_level=ThreatLevel.MEDIUM,
                    blocked=False,
                    reason=f"Action '{action}' requires approval",
                    sanitized_input=sanitized
                )
        
        # Check for path traversal attempts
        if ".." in command or command.startswith("/"):
            if not action or action in ["open_folder", "find_file"]:
                # These are allowed to have paths
                pass
            else:
                return ThreatReport(
                    threat_level=ThreatLevel.HIGH,
                    blocked=True,
                    reason="Path traversal attempt detected",
                    sanitized_input=sanitized
                )
        
        # Determine final threat level
        if suspicious_found:
            threat_level = ThreatLevel.LOW
        else:
            threat_level = ThreatLevel.SAFE
        
        return ThreatReport(
            threat_level=threat_level,
            blocked=False,
            reason="",
            sanitized_input=sanitized
        )
    
    def _sanitize_input(self, input_str: str) -> str:
        """Remove potentially dangerous characters from input."""
        # Remove command separators that could chain attacks
        sanitized = re.sub(r'[;&|`$]', '', input_str)
        # Remove newlines that could inject multiple commands
        sanitized = re.sub(r'[\n\r]', ' ', sanitized)
        # Normalize whitespace
        sanitized = ' '.join(sanitized.split())
        return sanitized
    
    def _requires_approval(self, action: str) -> bool:
        """Check if action requires explicit approval."""
        high_risk_actions = {
            "delete_item", "kill_process", "system_shutdown",
            "system_restart", "run_command", "run_script",
            "write_to_file", "move_file", "copy_file",
            "empty_recycle_bin", "set_wallpaper", "press_key"
        }
        return action in high_risk_actions
    
    def _log_breach(self, breach_type: str, command: str, details: str):
        """Log a security breach attempt."""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "breach_attempts.log")
        
        entry = {
            "timestamp": time.time(),
            "type": breach_type,
            "command_preview": command[:100],
            "details": details
        }
        
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass
    
    def check_rate_limit(self, identifier: str, max_requests: int = 100, 
                        window: int = 60) -> bool:
        """
        Check if identifier has exceeded rate limits.
        
        Args:
            identifier: User/session identifier
            max_requests: Max requests allowed in window
            window: Time window in seconds
            
        Returns:
            True if within limit, False if exceeded
        """
        now = time.time()
        
        if not hasattr(self, '_rate_limits'):
            self._rate_limits: Dict[str, List[float]] = {}
        
        # Clean old entries
        if identifier not in self._rate_limits:
            self._rate_limits[identifier] = []
        
        self._rate_limits[identifier] = [
            t for t in self._rate_limits[identifier]
            if now - t < window
        ]
        
        # Check limit
        if len(self._rate_limits[identifier]) >= max_requests:
            self._log_breach("rate_limit", identifier, 
                           f"{len(self._rate_limits[identifier])} requests in {window}s")
            return False
        
        self._rate_limits[identifier].append(now)
        return True
    
    def record_failed_auth(self, identifier: str):
        """Record a failed authentication attempt."""
        now = time.time()
        self._failed_auth_attempts.append(now)
        
        # Clean old entries (older than 1 hour)
        self._failed_auth_attempts = [
            t for t in self._failed_auth_attempts
            if now - t < 3600
        ]
        
        # If more than 5 failed attempts in 15 minutes, flag as attack
        recent = [t for t in self._failed_auth_attempts if now - t < 900]
        if len(recent) >= 5:
            self._log_breach("brute_force", identifier, 
                           f"{len(recent)} failed attempts in 15 minutes")
            return True
        
        return False
    
    def is_blocked(self, identifier: str) -> bool:
        """Check if identifier is temporarily blocked."""
        if hasattr(self, '_blocked_identifiers'):
            blocked_until = self._blocked_identifiers.get(identifier, 0)
            if time.time() < blocked_until:
                return True
            else:
                # Unblock after timeout
                del self._blocked_identifiers[identifier]
        return False
    
    def block_identifier(self, identifier: str, duration: int = 300):
        """Temporarily block an identifier."""
        if not hasattr(self, '_blocked_identifiers'):
            self._blocked_identifiers: Dict[str, float] = {}
        
        self._blocked_identifiers[identifier] = time.time() + duration


# Global instance
_firewall = None

def get_firewall() -> Firewall:
    """Get global firewall instance."""
    global _firewall
    if _firewall is None:
        _firewall = Firewall()
    return _firewall
