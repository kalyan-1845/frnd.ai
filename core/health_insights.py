"""
Health Insights Module
=====================
Enhanced health monitoring, break reminders, and productivity tracking.

Features:
- Smart break reminders based on work patterns
- Posture and eye strain alerts
- Productivity analytics
- Wellness recommendations
"""
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    import psutil
except ImportError:
    psutil = None

from core.logger import log_event, log_error


@dataclass
class HealthMetrics:
    """Health-related metrics."""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    active_time_minutes: int = 0
    break_count: int = 0
    last_break: Optional[float] = None
    focus_sessions: int = 0


@dataclass
class WellnessRecommendation:
    """A wellness recommendation."""
    title: str
    message: str
    priority: str  # "high", "medium", "low"
    category: str  # "break", "posture", "hydration", "eyes", "movement"


class HealthInsights:
    """
    Enhanced health insights and productivity tracking.
    """
    
    def __init__(self):
        self.metrics = HealthMetrics()
        self.session_start = time.time()
        self.break_reminder_interval = 1800  # 30 minutes
        self.last_break_reminder = 0
        self.work_streak = 0
        self.daily_stats = {
            "total_active_time": 0,
            "breaks_taken": 0,
            "focus_sessions": 0,
            "commands_executed": 0,
        }
        log_event("HealthInsights initialized")
    
    def record_activity(self):
        """Record user activity."""
        self.metrics.active_time_minutes += 1
        self.daily_stats["total_active_time"] += 1
        self.work_streak += 1
    
    def record_break(self):
        """Record a break taken."""
        self.metrics.break_count += 1
        self.metrics.last_break = time.time()
        self.daily_stats["breaks_taken"] += 1
        self.work_streak = 0
        log_event("Break recorded", f"breaks_today={self.daily_stats['breaks_taken']}")
    
    def record_command(self):
        """Record command execution."""
        self.daily_stats["commands_executed"] += 1
    
    def should_remind_break(self) -> bool:
        """Check if it's time for a break reminder."""
        current_time = time.time()
        elapsed = current_time - self.last_break_reminder
        
        # Adaptive reminder based on work streak
        if self.work_streak > 60:  # 60 minutes of continuous work
            return True
        
        return elapsed > self.break_reminder_interval and self.work_streak > 30
    
    def get_break_reminder(self) -> Optional[WellnessRecommendation]:
        """Generate a smart break reminder."""
        if not self.should_remind_break():
            return None
        
        self.last_break_reminder = time.time()
        
        # Different reminders based on time of day and streak
        hour = datetime.now().hour
        
        if self.work_streak > 90:
            return WellnessRecommendation(
                title="Time for a Break!",
                message="You've been working for over 90 minutes. Take a 5-minute break to rest your eyes and stretch.",
                priority="high",
                category="break"
            )
        elif self.work_streak > 60:
            return WellnessRecommendation(
                title="Eye Rest Reminder",
                message="Look away from the screen for 20 seconds. Focus on something 20 feet away.",
                priority="medium",
                category="eyes"
            )
        elif hour >= 2 and hour < 8:
            return WellnessRecommendation(
                title="Late Night Session",
                message="It's late. Consider wrapping up soon for better rest.",
                priority="medium",
                category="break"
            )
        else:
            return WellnessRecommendation(
                title="Quick Break",
                message="Stand up, stretch, and hydrate. Your body will thank you!",
                priority="low",
                category="movement"
            )
    
    def get_productivity_insight(self) -> str:
        """Generate productivity insight based on daily stats."""
        active = self.daily_stats["total_active_time"]
        breaks = self.daily_stats["breaks_taken"]
        commands = self.daily_stats["commands_executed"]
        
        if active == 0:
            return "Start your day by asking me something!"
        
        # Calculate productivity score
        break_ratio = breaks / max(1, active / 30)  # breaks per 30 min
        command_rate = commands / max(1, active)  # commands per minute
        
        if break_ratio < 0.3 and active > 60:
            return "You're on a long streak! Remember to take breaks for better focus."
        elif command_rate > 2:
            return f"Great productivity today! {commands} commands in {active} minutes."
        elif active > 120:
            return f"You've been active for {active} minutes. Great consistency!"
        else:
            return "Steady progress today. Keep it up!"
    
    def get_wellness_tips(self) -> List[WellnessRecommendation]:
        """Get list of wellness tips based on current state."""
        tips = []
        hour = datetime.now().hour
        
        # Time-based tips
        if hour >= 22 or hour < 6:
            tips.append(WellnessRecommendation(
                title="Late Night",
                message="Consider winding down. Blue light from screens affects sleep quality.",
                priority="high",
                category="break"
            ))
        
        if hour >= 6 and hour < 8:
            tips.append(WellnessRecommendation(
                title="Morning Routine",
                message="Start with a glass of water and some light stretching.",
                priority="low",
                category="hydration"
            ))
        
        # Posture tips
        tips.append(WellnessRecommendation(
            title="Posture Check",
            message="Sit up straight! Your spine will thank you later.",
            priority="medium",
            category="posture"
        ))
        
        # Hydration
        tips.append(WellnessRecommendation(
            title="Stay Hydrated",
            message="Have you had water recently? Proper hydration boosts cognitive function.",
            priority="medium",
            category="hydration"
        ))
        
        return tips
    
    def get_daily_summary(self) -> Dict[str, Any]:
        """Get summary of today's health metrics."""
        return {
            "active_time_minutes": self.daily_stats["total_active_time"],
            "breaks_taken": self.daily_stats["breaks_taken"],
            "commands_executed": self.daily_stats["commands_executed"],
            "focus_sessions": self.daily_stats["focus_sessions"],
            "productivity_insight": self.get_productivity_insight(),
            "wellness_tips": [
                {"title": t.title, "message": t.message, "category": t.category}
                for t in self.get_wellness_tips()[:3]
            ],
        }
    
    def reset_daily(self):
        """Reset daily stats (call at start of new day)."""
        self.daily_stats = {
            "total_active_time": 0,
            "breaks_taken": 0,
            "focus_sessions": 0,
            "commands_executed": 0,
        }
        log_event("Daily stats reset")


# Global instance
_health_insights: Optional[HealthInsights] = None


def get_health_insights() -> HealthInsights:
    """Get global health insights instance."""
    global _health_insights
    if _health_insights is None:
        _health_insights = HealthInsights()
    return _health_insights


def check_wellbeing() -> Optional[WellnessRecommendation]:
    """Check if there's a wellbeing reminder."""
    return get_health_insights().get_break_reminder()


__all__ = [
    "HealthInsights",
    "HealthMetrics", 
    "WellnessRecommendation",
    "get_health_insights",
    "check_wellbeing",
]
