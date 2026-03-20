"""
Digital Security & Health Monitoring Module
============================================
Real-time system monitoring with anomaly detection,
threat identification, and automated responses.

Features:
- Resource monitoring (CPU, RAM, Disk, Network)
- Anomaly detection (spikes, unusual patterns)
- Malware-like process detection
- Unauthorized access monitoring
- Alert system with configurable thresholds
- Incident logging and fix suggestions
"""

import os
import sys
import time
import json
import threading
import psutil
import subprocess
from typing import Dict, List, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
from enum import Enum
import core.logger as logger
from core.logger import log_event, log_error


# ============================================================
# Configuration & Constants
# ============================================================

class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class HealthConfig:
    """Configuration for health monitoring thresholds."""
    # CPU thresholds (percentage)
    cpu_warning: float = 80.0
    cpu_critical: float = 95.0
    cpu_spike_duration: int = 300  # seconds before alert
    
    # RAM thresholds (percentage)
    ram_warning: float = 80.0
    ram_critical: float = 95.0
    ram_leak_detection: int = 600  # seconds of sustained high usage
    
    # Disk thresholds (percentage)
    disk_warning: float = 85.0
    disk_critical: float = 95.0
    
    # Network thresholds (bytes per second)
    network_warning: float = 10 * 1024 * 1024  # 10 MB/s
    network_critical: float = 50 * 1024 * 1024  # 50 MB/s
    
    # Process monitoring
    suspicious_process_check_interval: int = 60  # seconds
    high_cpu_process_threshold: float = 50.0  # % single process
    high_memory_process_threshold: float = 30.0  # % single process
    
    # Monitoring intervals
    check_interval: int = 5  # seconds between checks
    history_size: int = 720  # Keep 1 hour of data (5s * 720)
    
    # Alert settings
    alert_cooldown: int = 300  # seconds between same alerts
    enable_audio_alerts: bool = True
    enable_visual_alerts: bool = True


# ============================================================
# Malware/Threat Signatures
# ============================================================

class ThreatSignatures:
    """
    Known malware-like process patterns and suspicious behaviors.
    """
    
    # Known malicious/suspicious process names
    SUSPICIOUS_PROCESS_NAMES = frozenset([
        # Common malware names
        "cryptominer", "xmrig", "stratum", "miner", "minerd",
        "payload", "backdoor", "keylogger", "trojan", "virus",
        "malware", "injector", "hook", "logger", "spy",
        # Potentially unwanted
        "adware", "bundler", "downloader", " hijacker",
        # Network threats
        "nc.exe", "netcat", "psexec", "mimikatz",
        "lsass.exe", "wce.exe", "gsecdump",
        # Known bad processes (false positives possible - configurable)
        "teamviewer", "anydesk", "ammyy",
    ])
    
    # Suspicious process behaviors
    SUSPICIOUS_BEHAVIORS = [
        "hidden window",
        "invisible process",
        "rootkit",
        "keylogger",
        "screen capture",
        "clipboard monitor",
    ]
    
    # Known legitimate processes that use high resources
    LEGITIMATE_HIGH_USAGE = frozenset([
        "chrome.exe", "msedge.exe", "firefox.exe",  # Browsers
        "code.exe", "devenv.exe", "idea64.exe",     # IDEs
        "photoshop.exe", "illustrator.exe",          # Creative
        "unity.exe", "unrealengine",                 # Game engines
        "python.exe", "node.exe", "java.exe",        # Runtime
        "svchost.exe", "system", "csrss.exe",        # System
    ])
    
    # Ports that might indicate unauthorized access
    SUSPICIOUS_PORTS = [
        23,     # Telnet
        135,    # RPC
        139,    # NetBIOS
        445,    # SMB
        1433,   # MSSQL
        3306,   # MySQL
        5432,   # PostgreSQL
        6379,   # Redis
        27017,  # MongoDB
    ]
    
    @classmethod
    def is_suspicious_name(cls, process_name: str) -> bool:
        """Check if process name matches suspicious patterns."""
        name_lower = process_name.lower()
        for suspicious in cls.SUSPICIOUS_PROCESS_NAMES:
            if suspicious in name_lower:
                return True
        return False
    
    @classmethod
    def is_legitimate_high_usage(cls, process_name: str) -> bool:
        """Check if high resource usage is expected for this process."""
        name_lower = process_name.lower()
        return name_lower in cls.LEGITIMATE_HIGH_USAGE


# ============================================================
# Data Structures
# ============================================================

@dataclass
class MetricSnapshot:
    """Single point of metric data."""
    timestamp: float
    cpu_percent: float
    ram_percent: float
    disk_percent: float
    network_sent: int
    network_recv: int
    process_count: int

@dataclass
class Alert:
    """Represents a health/security alert."""
    timestamp: float
    level: AlertLevel
    category: str  # "cpu", "ram", "disk", "network", "security"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[str] = field(default_factory=list)

@dataclass
class Incident:
    """Security or health incident record."""
    id: str
    timestamp: float
    alert_level: AlertLevel
    category: str
    description: str
    metrics: Dict[str, Any]
    resolved: bool = False
    resolution: str = ""


# ============================================================
# Health Monitor Core
# ============================================================

class HealthMonitor:
    """
    Main health monitoring class.
    Monitors system resources and detects anomalies.
    """
    
    def __init__(self, config: HealthConfig = None):
        self.config = config or HealthConfig()
        
        # Metric history
        self._history: deque = deque(maxlen=self.config.history_size)
        
        # Alert tracking
        self._last_alerts: Dict[str, float] = {}  # category -> last alert time
        self._active_alerts: List[Alert] = []
        
        # Incident tracking
        self._incidents: List[Incident] = []
        self._incident_counter = 0
        
        # Monitoring state
        self._running = False
        self._monitor_thread: threading.Thread = None
        
        # Callbacks
        self._alert_callbacks: List[Callable[[Alert], None]] = []
        
        # Baseline metrics (learned over time)
        self._baseline: Dict[str, float] = {
            "cpu": 0.0,
            "ram": 0.0,
            "disk": 0.0,
            "network_sent": 0.0,
            "network_recv": 0.0,
        }
        self._baseline_samples = 0
        self._baseline_ready = False
        
        # Start monitoring
        self.start()
    
    def start(self):
        """Start the monitoring thread."""
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        log_event("HealthMonitor", "Started")
    
    def stop(self):
        """Stop the monitoring thread."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        log_event("HealthMonitor", "Stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self._running:
            try:
                # Collect metrics
                snapshot = self._collect_metrics()
                self._history.append(snapshot)
                
                # Update baseline
                self._update_baseline(snapshot)
                
                # Check for issues
                alerts = self._check_health(snapshot)
                
                # Process alerts
                for alert in alerts:
                    self._handle_alert(alert)
                
                # Check for suspicious processes
                if self._should_check_processes():
                    self._check_suspicious_processes()
                
            except Exception as e:
                log_error("HealthMonitor.loop", e)
            
            time.sleep(self.config.check_interval)
    
    def _collect_metrics(self) -> MetricSnapshot:
        """Collect current system metrics."""
        # CPU
        cpu = psutil.cpu_percent(interval=0.5)
        
        # RAM
        mem = psutil.virtual_memory()
        ram = mem.percent
        
        # Disk
        try:
            if os.name == 'nt':
                disk = psutil.disk_usage(os.environ.get('SystemDrive', 'C:') + '\\')
            else:
                disk = psutil.disk_usage('/')
            disk_percent = disk.percent
        except:
            disk_percent = 0
        
        # Network
        try:
            net = psutil.net_io_counters()
            net_sent = net.bytes_sent
            net_recv = net.bytes_recv
        except:
            net_sent = net_recv = 0
        
        # Process count
        process_count = len(psutil.pids())
        
        return MetricSnapshot(
            timestamp=time.time(),
            cpu_percent=cpu,
            ram_percent=ram,
            disk_percent=disk_percent,
            network_sent=net_sent,
            network_recv=net_recv,
            process_count=process_count
        )
    
    def _update_baseline(self, snapshot: MetricSnapshot):
        """Learn baseline metrics over time."""
        if self._baseline_samples < 60:  # 5 minutes of data
            self._baseline["cpu"] = (self._baseline["cpu"] * self._baseline_samples + snapshot.cpu_percent) / (self._baseline_samples + 1)
            self._baseline["ram"] = (self._baseline["ram"] * self._baseline_samples + snapshot.ram_percent) / (self._baseline_samples + 1)
            self._baseline["disk"] = (self._baseline["disk"] * self._baseline_samples + snapshot.disk_percent) / (self._baseline_samples + 1)
            self._baseline_samples += 1
        elif self._baseline_samples == 60:
            self._baseline_ready = True
            self._baseline_samples += 1
            log_event("HealthMonitor", "Baseline established")
    
    def _check_health(self, snapshot: MetricSnapshot) -> List[Alert]:
        """Check current metrics against thresholds."""
        alerts = []
        current_time = time.time()
        
        # CPU check
        if snapshot.cpu_percent >= self.config.cpu_critical:
            alerts.append(Alert(
                timestamp=current_time,
                level=AlertLevel.CRITICAL,
                category="cpu",
                message=f"CRITICAL: CPU usage at {snapshot.cpu_percent:.1f}%",
                details={"cpu": snapshot.cpu_percent},
                suggestions=self._get_cpu_suggestions(snapshot.cpu_percent)
            ))
        elif snapshot.cpu_percent >= self.config.cpu_warning:
            alerts.append(Alert(
                timestamp=current_time,
                level=AlertLevel.WARNING,
                category="cpu",
                message=f"WARNING: CPU usage at {snapshot.cpu_percent:.1f}%",
                details={"cpu": snapshot.cpu_percent},
                suggestions=self._get_cpu_suggestions(snapshot.cpu_percent)
            ))
        
        # RAM check
        if snapshot.ram_percent >= self.config.ram_critical:
            alerts.append(Alert(
                timestamp=current_time,
                level=AlertLevel.CRITICAL,
                category="ram",
                message=f"CRITICAL: RAM usage at {snapshot.ram_percent:.1f}%",
                details={"ram": snapshot.ram_percent},
                suggestions=self._get_ram_suggestions(snapshot.ram_percent)
            ))
        elif snapshot.ram_percent >= self.config.ram_warning:
            alerts.append(Alert(
                timestamp=current_time,
                level=AlertLevel.WARNING,
                category="ram",
                message=f"WARNING: RAM usage at {snapshot.ram_percent:.1f}%",
                details={"ram": snapshot.ram_percent},
                suggestions=self._get_ram_suggestions(snapshot.ram_percent)
            ))
        
        # Disk check
        if snapshot.disk_percent >= self.config.disk_critical:
            alerts.append(Alert(
                timestamp=current_time,
                level=AlertLevel.CRITICAL,
                category="disk",
                message=f"CRITICAL: Disk usage at {snapshot.disk_percent:.1f}%",
                details={"disk": snapshot.disk_percent},
                suggestions=[
                    "Run Disk Cleanup to remove temporary files",
                    "Uninstall unused applications",
                    "Move large files to external storage",
                    "Consider expanding disk capacity"
                ]
            ))
        elif snapshot.disk_percent >= self.config.disk_warning:
            alerts.append(Alert(
                timestamp=current_time,
                level=AlertLevel.WARNING,
                category="disk",
                message=f"WARNING: Disk usage at {snapshot.disk_percent:.1f}%",
                details={"disk": snapshot.disk_percent},
                suggestions=[
                    "Review and delete unnecessary files",
                    "Clear browser cache",
                    "Empty recycle bin"
                ]
            ))
        
        # Anomaly detection (if baseline ready)
        if self._baseline_ready:
            # Check for unusual CPU spike
            if snapshot.cpu_percent > self._baseline["cpu"] * 2.5 and snapshot.cpu_percent > 50:
                alerts.append(Alert(
                    timestamp=current_time,
                    level=AlertLevel.WARNING,
                    category="cpu",
                    message=f"Unusual CPU spike detected: {snapshot.cpu_percent:.1f}% (baseline: {self._baseline['cpu']:.1f}%)",
                    details={"current": snapshot.cpu_percent, "baseline": self._baseline["cpu"]},
                    suggestions=["Check for runaway processes", "Review recently installed software"]
                ))
        
        return alerts
    
    def _get_cpu_suggestions(self, usage: float) -> List[str]:
        """Get suggestions for high CPU usage."""
        suggestions = []
        
        if usage >= 95:
            suggestions = [
                "⚠️ IMMEDIATE ACTION REQUIRED",
                "1. Open Task Manager and identify high-CPU processes",
                "2. Terminate non-essential processes",
                "3. Check for malware running in background",
                "4. Consider restarting system if persists"
            ]
        elif usage >= 80:
            suggestions = [
                "1. Close unused applications",
                "2. Check for browser tabs consuming CPU",
                "3. Disable startup programs",
                "4. Run antivirus scan"
            ]
        
        return suggestions
    
    def _get_ram_suggestions(self, usage: float) -> List[str]:
        """Get suggestions for high RAM usage."""
        suggestions = []
        
        if usage >= 95:
            suggestions = [
                "⚠️ MEMORY CRITICAL - System may become unstable",
                "1. Close applications immediately",
                "2. Check Task Manager for memory leaks",
                "3. Restart system if unresponsive"
            ]
        elif usage >= 80:
            suggestions = [
                "1. Close unused programs",
                "2. Reduce browser tab count",
                "3. Disable startup programs",
                "4. Consider adding more RAM"
            ]
        
        return suggestions
    
    def _should_check_processes(self) -> bool:
        """Check if it's time to scan for suspicious processes."""
        if not hasattr(self, '_last_process_check'):
            self._last_process_check = 0
        
        if time.time() - self._last_process_check > self.config.suspicious_process_check_interval:
            self._last_process_check = time.time()
            return True
        return False
    
    def _check_suspicious_processes(self):
        """Scan for suspicious processes."""
        alerts = []
        current_time = time.time()
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'cmdline']):
            try:
                info = proc.info
                name = info.get('name', '').lower()
                
                # Check for suspicious names
                if ThreatSignatures.is_suspicious_name(name):
                    # Double-check it's not a false positive
                    if not ThreatSignatures.is_legitimate_high_usage(name):
                        alerts.append(Alert(
                            timestamp=current_time,
                            level=AlertLevel.CRITICAL,
                            category="security",
                            message=f"Suspicious process detected: {info['name']}",
                            details={
                                "pid": info['pid'],
                                "name": info['name'],
                                "cpu": info['cpu_percent'],
                                "memory": info['memory_percent']
                            },
                            suggestions=[
                                "Research this process online",
                                "Run antivirus scan",
                                "Check network connections",
                                "Consider terminating if unknown"
                            ]
                        ))
                
                # Check for unusually high CPU in single process
                if info.get('cpu_percent', 0) > self.config.high_cpu_process_threshold:
                    if not ThreatSignatures.is_legitimate_high_usage(name):
                        alerts.append(Alert(
                            timestamp=current_time,
                            level=AlertLevel.WARNING,
                            category="cpu",
                            message=f"High CPU process: {info['name']} ({info['cpu_percent']:.1f}%)",
                            details={"pid": info['pid'], "cpu": info['cpu_percent']},
                            suggestions=["Investigate this process", "Terminate if unresponsive"]
                        ))
                
                # Check for unusually high memory in single process
                if info.get('memory_percent', 0) > self.config.high_memory_process_threshold:
                    if not ThreatSignatures.is_legitimate_high_usage(name):
                        alerts.append(Alert(
                            timestamp=current_time,
                            level=AlertLevel.WARNING,
                            category="ram",
                            message=f"High memory process: {info['name']} ({info['memory_percent']:.1f}%)",
                            details={"pid": info['pid'], "memory": info['memory_percent']},
                            suggestions=["Check for memory leaks", "Consider closing this application"]
                        ))
            
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Handle alerts
        for alert in alerts:
            self._handle_alert(alert)
    
    def _handle_alert(self, alert: Alert):
        """Process and dispatch an alert."""
        current_time = time.time()
        
        # Check cooldown
        if alert.category in self._last_alerts:
            if current_time - self._last_alerts[alert.category] < self.config.alert_cooldown:
                return  # Skip - too soon
        
        # Record alert time
        self._last_alerts[alert.category] = current_time
        
        # Store alert
        self._active_alerts.append(alert)
        if len(self._active_alerts) > 100:
            self._active_alerts.pop(0)
        
        # Create incident
        self._create_incident(alert)
        
        # Log alert
        log_event(f"Alert.{alert.level.value}", f"{alert.category}: {alert.message}")
        
        # Dispatch to callbacks
        for callback in self._alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                log_error("HealthMonitor.callback", e)
    
    def _create_incident(self, alert: Alert):
        """Create an incident record from an alert."""
        self._incident_counter += 1
        incident = Incident(
            id=f"INC-{self._incident_counter:05d}",
            timestamp=alert.timestamp,
            alert_level=alert.level,
            category=alert.category,
            description=alert.message,
            metrics=alert.details
        )
        self._incidents.append(incident)
        
        # Keep only recent incidents
        if len(self._incidents) > 1000:
            self._incidents = self._incidents[-500:]
    
    def register_alert_callback(self, callback: Callable[[Alert], None]):
        """Register a callback for alerts."""
        self._alert_callbacks.append(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current health status."""
        if not self._history:
            return {"status": "initializing"}
        
        latest = self._history[-1]
        
        return {
            "status": "healthy" if latest.cpu_percent < 80 and latest.ram_percent < 80 else "warning",
            "cpu": latest.cpu_percent,
            "ram": latest.ram_percent,
            "disk": latest.disk_percent,
            "processes": latest.process_count,
            "baseline": self._baseline if self._baseline_ready else "learning",
            "active_alerts": len([a for a in self._active_alerts if time.time() - a.timestamp < 3600]),
            "recent_incidents": len([i for i in self._incidents if not i.resolved])
        }
    
    def get_metrics_history(self, duration_seconds: int = 300) -> List[Dict]:
        """Get historical metrics."""
        cutoff = time.time() - duration_seconds
        return [
            {
                "timestamp": m.timestamp,
                "cpu": m.cpu_percent,
                "ram": m.ram_percent,
                "disk": m.disk_percent,
                "processes": m.process_count
            }
            for m in self._history
            if m.timestamp > cutoff
        ]
    
    def get_alerts(self, limit: int = 20) -> List[Alert]:
        """Get recent alerts."""
        return self._active_alerts[-limit:]
    
    def get_incidents(self, unresolved_only: bool = False) -> List[Incident]:
        """Get incidents."""
        if unresolved_only:
            return [i for i in self._incidents if not i.resolved]
        return self._incidents[-50:]
    
    def resolve_incident(self, incident_id: str, resolution: str):
        """Mark an incident as resolved."""
        for incident in self._incidents:
            if incident.id == incident_id:
                incident.resolved = True
                incident.resolution = resolution
                log_event("Incident.resolved", f"{incident_id}: {resolution}")
                break


# ============================================================
# Alert System
# ============================================================

class AlertSystem:
    """
    Handles alert delivery through multiple channels.
    """
    
    def __init__(self, health_monitor: HealthMonitor = None):
        self.monitor = health_monitor
        self._alert_log_file = "logs/alerts.json"
        
        # Ensure logs directory exists
        os.makedirs("logs", exist_ok=True)
        
        # Register default callback
        if self.monitor:
            self.monitor.register_alert_callback(self._handle_alert)
    
    def _handle_alert(self, alert: Alert):
        """Default alert handler."""
        # Log to file
        self._log_alert(alert)
        
        # Print to console based on level
        if alert.level in [AlertLevel.CRITICAL, AlertLevel.EMERGENCY]:
            print(f"[🚨 {alert.level.value.upper()}] {alert.message}")
        elif alert.level == AlertLevel.WARNING:
            print(f"[⚠️  {alert.level.value.upper()}] {alert.message}")
        else:
            print(f"[ℹ️  {alert.level.value.upper()}] {alert.message}")
        
        # Print suggestions
        if alert.suggestions:
            print("   Suggestions:")
            for suggestion in alert.suggestions[:3]:  # Limit to 3
                print(f"   • {suggestion}")
    
    def _log_alert(self, alert: Alert):
        """Log alert to JSON file."""
        try:
            log_entry = {
                "timestamp": alert.timestamp,
                "level": alert.level.value,
                "category": alert.category,
                "message": alert.message,
                "details": alert.details
            }
            
            # Read existing logs
            alerts = []
            if os.path.exists(self._alert_log_file):
                try:
                    with open(self._alert_log_file, 'r') as f:
                        alerts = json.load(f)
                except:
                    alerts = []
            
            # Add new alert
            alerts.append(log_entry)
            
            # Keep only last 500
            alerts = alerts[-500:]
            
            # Write back
            with open(self._alert_log_file, 'w') as f:
                json.dump(alerts, f, indent=2)
        
        except Exception as e:
            log_error("AlertSystem.log", e)
    
    def send_desktop_notification(self, alert: Alert):
        """Send Windows desktop notification."""
        try:
            if os.name == 'nt':
                # Use PowerShell for Windows notification
                title = f"BKR Alert: {alert.level.value.upper()}"
                message = alert.message[:200]  # Truncate for notification
                
                subprocess.run([
                    'powershell', '-Command',
                    f'New-BurntToast -Title "{title}" -Text "{message}"'
                ], capture_output=True, timeout=5)
        except Exception:
            pass  # Notification failed, not critical


# ============================================================
# Security Monitor
# ============================================================

class SecurityMonitor:
    """
    Additional security-focused monitoring.
    """
    
    def __init__(self, health_monitor: HealthMonitor = None):
        self.health_monitor = health_monitor
        self._login_attempts: deque = deque(maxlen=50)
        self._failed_commands: deque = deque(maxlen=20)
    
    def check_unauthorized_access(self) -> List[Alert]:
        """Check for signs of unauthorized access."""
        alerts = []
        
        # Check for multiple failed sudo/elevation attempts
        # (This would need system integration)
        
        # Check for unusual login times
        # (Would need Windows security log access)
        
        return alerts
    
    def check_network_anomalies(self) -> List[Alert]:
        """Check for suspicious network activity."""
        alerts = []
        
        try:
            # Get network connections
            connections = psutil.net_connections()
            
            suspicious_count = 0
            for conn in connections:
                if conn.status == 'ESTABLISHED':
                    # Check suspicious ports
                    if conn.raddr and conn.raddr.port in ThreatSignatures.SUSPICIOUS_PORTS:
                        suspicious_count += 1
            
            if suspicious_count > 5:
                alerts.append(Alert(
                    timestamp=time.time(),
                    level=AlertLevel.WARNING,
                    category="network",
                    message=f"{suspicious_count} connections to suspicious ports detected",
                    details={"count": suspicious_count},
                    suggestions=[
                        "Review firewall rules",
                        "Check for unauthorized remote access",
                        "Run security scan"
                    ]
                ))
        
        except Exception as e:
            log_error("SecurityMonitor.network", e)
        
        return alerts


# ============================================================
# Global Instance & Factory
# ============================================================

_health_monitor: HealthMonitor = None
_alert_system: AlertSystem = None
_security_monitor: SecurityMonitor = None


def get_health_monitor() -> HealthMonitor:
    """Get global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


def get_alert_system() -> AlertSystem:
    """Get global alert system instance."""
    global _alert_system
    if _alert_system is None:
        _alert_system = AlertSystem(get_health_monitor())
    return _alert_system


def get_security_monitor() -> SecurityMonitor:
    """Get global security monitor instance."""
    global _security_monitor
    if _security_monitor is None:
        _security_monitor = SecurityMonitor(get_health_monitor())
    return _security_monitor


# ============================================================
# Convenience Functions
# ============================================================

def get_system_health() -> Dict[str, Any]:
    """Get current system health summary."""
    return get_health_monitor().get_status()

def get_system_metrics(duration: int = 60) -> List[Dict]:
    """Get metrics history."""
    return get_health_monitor().get_metrics_history(duration)

def get_active_alerts() -> List[Alert]:
    """Get current alerts."""
    return get_health_monitor().get_alerts()

def get_incidents(unresolved: bool = False) -> List[Incident]:
    """Get incidents."""
    return get_health_monitor().get_incidents(unresolved)

def resolve_incident(incident_id: str, resolution: str):
    """Resolve an incident."""
    return get_health_monitor().resolve_incident(incident_id, resolution)
