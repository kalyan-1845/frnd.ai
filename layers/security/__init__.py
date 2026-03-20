"""
Security Layer
==============
Authentication, activity monitoring, and breach detection.
"""

from layers.security.auth import SecurityAuth, get_auth, require_auth
from layers.security.monitor import ActivityMonitor, get_monitor
from layers.security.firewall import Firewall, get_firewall, ThreatLevel, ThreatReport

__all__ = [
    "SecurityAuth",
    "get_auth",
    "require_auth", 
    "ActivityMonitor",
    "get_monitor",
    "Firewall",
    "get_firewall",
    "ThreatLevel",
    "ThreatReport",
]
