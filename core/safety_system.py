"""
Safety System for BKR 2.0 - Human Clone Edition.

Features:
- Complete system protection to prevent damage
- Dangerous command detection and blocking
- User confirmation system for risky operations
- Safe mode enforcement
- System integrity monitoring
"""

import os
import re
import time
import threading
from typing import Dict, List, Tuple, Optional
import config
from core.logger import log_event, log_error

class SafetySystem:
    """
    Comprehensive safety system that prevents system damage
    and ensures only safe, educational operations are performed.
    """
    
    def __init__(self):
        self.safe_mode = True  # Always start in safe mode
        self.dangerous_patterns = {
            "system_destruction": [
                r"delete.*system32",
                r"format.*c:",
                r"rm.*-rf.*system",
                r"del.*system32",
                r"destroy.*windows",
                r"break.*system",
                r"corrupt.*registry"
            ],
            "file_destruction": [
                r"delete.*all.*files",
                r"erase.*everything",
                r"remove.*important",
                r"destroy.*documents",
                r"delete.*photos",
                r"format.*drive"
            ],
            "network_attacks": [
                r"hack.*network",
                r"crack.*password",
                r"bypass.*security",
                r"exploit.*vulnerability",
                r"create.*virus",
                r"make.*malware",
                r"attack.*system"
            ],
            "system_modification": [
                r"modify.*registry",
                r"change.*system32",
                r"edit.*boot",
                r"modify.*driver",
                r"change.*windows",
                r"edit.*system"
            ]
        }
        
        self.allowed_operations = {
            "education": ["teach", "learn", "explain", "study", "understand"],
            "information": ["search", "find", "lookup", "research", "read"],
            "creation": ["create", "write", "make", "build", "develop"],
            "organization": ["organize", "sort", "arrange", "manage", "track"],
            "communication": ["send", "email", "message", "chat", "talk"],
            "productivity": ["schedule", "plan", "remind", "note", "list"]
        }
        
        self.blocked_commands = {
            "dangerous": [
                "format", "delete", "remove", "destroy", "corrupt", "erase",
                "hack", "crack", "bypass", "exploit", "virus", "malware"
            ],
            "system": [
                "system32", "registry", "boot", "driver", "windows", "startup"
            ],
            "network": [
                "password", "security", "firewall", "admin", "root", "sudo"
            ]
        }
        
        self.safety_log = []
        self.confirmation_pending = None
        self.safety_lock = threading.Lock()
        
    def analyze_command(self, command: str) -> Dict:
        """
        Analyze a command for safety concerns.
        Returns safety assessment with action required.
        """
        if not command or not command.strip():
            return {
                "safe": True,
                "action": "allow",
                "reason": "Empty command",
                "risk_level": "none",
                "suggestions": []
            }
        
        command_lower = command.lower().strip()
        
        # Check for dangerous patterns
        dangerous_match = self._check_dangerous_patterns(command_lower)
        if dangerous_match:
            return {
                "safe": False,
                "action": "block",
                "reason": f"Dangerous pattern detected: {dangerous_match['type']}",
                "risk_level": "high",
                "suggestions": ["Focus on learning and education instead"]
            }
        
        # Check for blocked commands
        blocked_match = self._check_blocked_commands(command_lower)
        if blocked_match:
            return {
                "safe": False,
                "action": "block",
                "reason": f"Blocked command: {blocked_match}",
                "risk_level": "medium",
                "suggestions": ["Ask for educational alternatives"]
            }
        
        # Check for system modification attempts
        system_modification = self._check_system_modification(command_lower)
        if system_modification:
            return {
                "safe": False,
                "action": "confirm",
                "reason": "System modification detected",
                "risk_level": "medium",
                "suggestions": ["Consider if this is necessary for learning"]
            }
        
        # Check if it's an educational command
        if self._is_educational_command(command_lower):
            return {
                "safe": True,
                "action": "allow",
                "reason": "Educational command",
                "risk_level": "none",
                "suggestions": []
            }
        
        # Default safe action
        return {
            "safe": True,
            "action": "allow",
            "reason": "Safe command detected",
            "risk_level": "low",
            "suggestions": []
        }
    
    def _check_dangerous_patterns(self, command: str) -> Optional[Dict]:
        """Check for dangerous command patterns."""
        for category, patterns in self.dangerous_patterns.items():
            for pattern in patterns:
                if re.search(pattern, command, re.IGNORECASE):
                    return {
                        "type": category,
                        "pattern": pattern,
                        "command": command
                    }
        return None
    
    def _check_blocked_commands(self, command: str) -> Optional[str]:
        """Check for explicitly blocked commands."""
        for category, commands in self.blocked_commands.items():
            for blocked_cmd in commands:
                if blocked_cmd in command:
                    return blocked_cmd
        return None
    
    def _check_system_modification(self, command: str) -> bool:
        """Check for system modification attempts."""
        system_keywords = ["modify", "change", "edit", "alter", "update"]
        system_targets = ["system32", "registry", "boot", "driver", "windows", "startup", "system"]
        
        for keyword in system_keywords:
            if keyword in command:
                for target in system_targets:
                    if target in command:
                        return True
        return False
    
    def _is_educational_command(self, command: str) -> bool:
        """Check if command is educational in nature."""
        for category, keywords in self.allowed_operations.items():
            for keyword in keywords:
                if keyword in command:
                    return True
        return False
    
    def enforce_safe_mode(self, action: str, target: str = "") -> bool:
        """
        Enforce safe mode - block dangerous operations.
        Returns True if action is allowed, False if blocked.
        """
        if not self.safe_mode:
            return True  # Safe mode disabled (not recommended)
        
        # Always block these operations in safe mode
        dangerous_actions = [
            "delete", "remove", "destroy", "format", "erase", "corrupt",
            "hack", "crack", "bypass", "exploit", "virus", "malware"
        ]
        
        if action in dangerous_actions:
            self._log_safety_violation(action, target, "Blocked dangerous action in safe mode")
            return False
        
        # Block system file operations
        system_files = ["system32", "windows", "boot", "driver", "registry"]
        if any(file in target.lower() for file in system_files):
            self._log_safety_violation(action, target, "Blocked system file operation")
            return False
        
        return True
    
    def request_confirmation(self, action: str, target: str, reason: str) -> bool:
        """
        Request user confirmation for potentially risky operations.
        Returns True if user confirms, False if denied.
        """
        if not self.safe_mode:
            return True  # Skip confirmation if safe mode disabled
        
        confirmation_msg = f"⚠️ SAFETY WARNING ⚠️\n\n"
        confirmation_msg += f"Action: {action}\n"
        confirmation_msg += f"Target: {target}\n"
        confirmation_msg += f"Reason: {reason}\n\n"
        confirmation_msg += "This operation may be risky. Are you sure you want to proceed?\n"
        confirmation_msg += "Type 'yes' to confirm or 'no' to cancel."
        
        log_event("SafetyConfirmation", f"action={action} target={target} reason={reason}")
        
        # Store pending confirmation
        self.confirmation_pending = {
            "action": action,
            "target": target,
            "reason": reason,
            "timestamp": time.time()
        }
        
        return False  # Always deny by default, require explicit confirmation
    
    def verify_confirmation(self, user_response: str) -> bool:
        """Verify user confirmation for risky operations."""
        if not self.confirmation_pending:
            return False
        
        # Check if confirmation has expired (30 seconds)
        if time.time() - self.confirmation_pending["timestamp"] > 30:
            self.confirmation_pending = None
            return False
        
        response_lower = user_response.lower().strip()
        if response_lower in ["yes", "y", "confirm", "proceed"]:
            log_event("SafetyConfirmed", f"action={self.confirmation_pending['action']}")
            self.confirmation_pending = None
            return True
        elif response_lower in ["no", "n", "cancel", "stop"]:
            log_event("SafetyDenied", f"action={self.confirmation_pending['action']}")
            self.confirmation_pending = None
            return False
        
        return False
    
    def _log_safety_violation(self, action: str, target: str, reason: str):
        """Log safety violations for monitoring."""
        violation = {
            "timestamp": time.time(),
            "action": action,
            "target": target,
            "reason": reason,
            "blocked": True
        }
        
        with self.safety_lock:
            self.safety_log.append(violation)
            # Keep only last 100 violations
            if len(self.safety_log) > 100:
                self.safety_log.pop(0)
        
        log_event("SafetyViolation", f"action={action} target={target} reason={reason}")
    
    def get_safety_status(self) -> Dict:
        """Get current safety system status."""
        with self.safety_lock:
            violations_count = len(self.safety_log)
            recent_violations = [v for v in self.safety_log if time.time() - v["timestamp"] < 3600]  # Last hour
        
        return {
            "safe_mode": self.safe_mode,
            "violations_count": violations_count,
            "recent_violations": len(recent_violations),
            "pending_confirmation": self.confirmation_pending is not None,
            "blocked_operations": violations_count
        }
    
    def enable_safe_mode(self):
        """Enable safe mode (recommended)."""
        self.safe_mode = True
        log_event("SafetyMode", "enabled")
    
    def disable_safe_mode(self):
        """Disable safe mode (not recommended)."""
        self.safe_mode = False
        log_event("SafetyMode", "disabled")
    
    def get_safety_report(self) -> str:
        """Generate a safety report."""
        status = self.get_safety_status()
        
        report = "🛡️ SAFETY SYSTEM REPORT 🛡️\n\n"
        report += f"Safe Mode: {'✅ ENABLED' if status['safe_mode'] else '❌ DISABLED'}\n"
        report += f"Total Violations: {status['violations_count']}\n"
        report += f"Recent Violations (1hr): {status['recent_violations']}\n"
        report += f"Pending Confirmations: {'✅ YES' if status['pending_confirmation'] else '❌ NO'}\n"
        report += f"Blocked Operations: {status['blocked_operations']}\n\n"
        
        if status['violations_count'] > 0:
            report += "⚠️ RECENT VIOLATIONS:\n"
            with self.safety_lock:
                for violation in self.safety_log[-5:]:  # Last 5 violations
                    report += f"- {violation['action']} on {violation['target']}\n"
        
        report += "\n💡 RECOMMENDATIONS:\n"
        if not status['safe_mode']:
            report += "- Enable safe mode for maximum protection\n"
        if status['violations_count'] > 10:
            report += "- Review blocked operations\n"
        if status['recent_violations'] > 5:
            report += "- Consider stricter safety settings\n"
        
        return report
    
    def is_command_safe(self, command: str) -> bool:
        """Quick check if command is safe."""
        analysis = self.analyze_command(command)
        return analysis["safe"]
    
    def get_safe_alternatives(self, command: str) -> List[str]:
        """Get safe alternatives for blocked commands."""
        alternatives = []
        
        if "delete" in command.lower():
            alternatives.append("Organize files instead of deleting")
            alternatives.append("Archive old files for safety")
            alternatives.append("Create backups before any deletion")
        
        if "format" in command.lower():
            alternatives.append("Use disk cleanup tools instead")
            alternatives.append("Organize files and folders")
            alternatives.append("Learn about data management")
        
        if "hack" in command.lower() or "crack" in command.lower():
            alternatives.append("Learn ethical hacking and cybersecurity")
            alternatives.append("Study programming and security")
            alternatives.append("Explore penetration testing legally")
        
        if "destroy" in command.lower() or "break" in command.lower():
            alternatives.append("Learn about system repair and maintenance")
            alternatives.append("Study troubleshooting techniques")
            alternatives.append("Understand system architecture")
        
        return alternatives

# Global safety system instance
safety_system = SafetySystem()

def analyze_command_safety(command: str) -> Dict:
    """Global function to analyze command safety."""
    return safety_system.analyze_command(command)

def enforce_safe_mode(action: str, target: str = "") -> bool:
    """Global function to enforce safe mode."""
    return safety_system.enforce_safe_mode(action, target)

def request_safety_confirmation(action: str, target: str, reason: str) -> bool:
    """Global function to request safety confirmation."""
    return safety_system.request_confirmation(action, target, reason)

def verify_safety_confirmation(user_response: str) -> bool:
    """Global function to verify safety confirmation."""
    return safety_system.verify_confirmation(user_response)

def get_safety_status() -> Dict:
    """Global function to get safety status."""
    return safety_system.get_safety_status()

def get_safety_report() -> str:
    """Global function to get safety report."""
    return safety_system.get_safety_report()

def is_command_safe(command: str) -> bool:
    """Global function to check if command is safe."""
    return safety_system.is_command_safe(command)

def get_safe_alternatives(command: str) -> List[str]:
    """Global function to get safe alternatives."""
    return safety_system.get_safe_alternatives(command)