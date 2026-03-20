"""
Predictive Productivity Module
==============================
AI-powered productivity predictions and smart scheduling.

Features:
- User pattern learning
- Task suggestions based on time/context
- Smart daily scheduling
- Workflow automation suggestions
"""
import time
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import defaultdict

from core.logger import log_event, log_error


@dataclass
class UserPattern:
    """Represents a learned user pattern."""
    hour: int
    day_of_week: int  # 0=Monday, 6=Sunday
    common_commands: List[str] = field(default_factory=list)
    focus_periods: List[int] = field(default_factory=list)  # hours
    productivity_score: float = 0.0


@dataclass
class TaskSuggestion:
    """A suggested task."""
    task: str
    reason: str
    confidence: float  # 0-1
    time_estimate: int  # minutes


class PredictiveProductivity:
    """
    Predictive productivity engine.
    Learns user patterns and provides intelligent suggestions.
    """
    
    def __init__(self, memory_file: str = "user_patterns.json"):
        self.memory_file = memory_file
        self.patterns: Dict[int, UserPattern] = {}
        self.command_history: List[Dict] = []
        self.task_patterns: Dict[str, int] = defaultdict(int)  # task -> count
        self.load_patterns()
        log_event("PredictiveProductivity initialized")
    
    def record_command(self, command: str, timestamp: Optional[float] = None):
        """Record a command for pattern learning."""
        timestamp = timestamp or time.time()
        dt = datetime.fromtimestamp(timestamp)
        
        entry = {
            "command": command,
            "hour": dt.hour,
            "day": dt.weekday(),
            "timestamp": timestamp,
        }
        self.command_history.append(entry)
        
        # Update task patterns
        self.task_patterns[command.lower()] += 1
        
        # Keep only last 1000 entries
        if len(self.command_history) > 1000:
            self.command_history = self.command_history[-1000:]
        
        # Save periodically
        if len(self.command_history) % 50 == 0:
            self.save_patterns()
    
    def predict_time_slot(self) -> str:
        """Predict the best time slot for tasks."""
        now = datetime.now()
        hour = now.hour
        day = now.weekday()
        
        # Morning peak: 9-12
        if 9 <= hour < 12:
            return "peak_morning"
        # Afternoon: 14-17
        elif 14 <= hour < 17:
            return "peak_afternoon"
        # Evening: 19-21
        elif 19 <= hour < 21:
            return "evening"
        # Late night
        elif hour >= 22 or hour < 6:
            return "late_night"
        else:
            return "low_energy"
    
    def suggest_task(self) -> Optional[TaskSuggestion]:
        """Suggest a task based on patterns."""
        now = datetime.now()
        hour = now.hour
        day = now.weekday()
        
        # Get commands for this hour on this day
        similar_commands = [
            e["command"] for e in self.command_history
            if e["hour"] == hour and e["day"] == day
        ]
        
        if not similar_commands:
            # Try just this hour
            similar_commands = [
                e["command"] for e in self.command_history
                if e["hour"] == hour
            ]
        
        if not similar_commands:
            return None
        
        # Find most common
        from collections import Counter
        common = Counter(similar_commands).most_common(1)
        
        if common:
            task, count = common[0]
            confidence = min(1.0, count / 10)  # Max confidence at 10 occurrences
            
            return TaskSuggestion(
                task=task,
                reason=f"Based on your patterns around {hour}:00",
                confidence=confidence,
                time_estimate=5,  # Default 5 minutes
            )
        
        return None
    
    def get_daily_schedule_suggestion(self) -> List[str]:
        """Get smart daily schedule suggestions."""
        now = datetime.now()
        hour = now.hour
        suggestions = []
        
        if hour < 9:
            suggestions.append("Morning: Review your goals for the day")
            suggestions.append("Morning: Handle high-priority tasks")
        elif 9 <= hour < 12:
            suggestions.append("Focus time: Deep work on important tasks")
        elif 12 <= hour < 14:
            suggestions.append("Lunch break: Step away from the screen")
        elif 14 <= hour < 17:
            suggestions.append("Afternoon: Meetings and collaborations")
            suggestions.append("Afternoon: Administrative tasks")
        elif 17 <= hour < 19:
            suggestions.append("Wrap up: Review completed tasks")
            suggestions.append("Plan tomorrow's priorities")
        else:
            suggestions.append("Evening: Light tasks or learning")
            suggestions.append("Consider winding down soon")
        
        return suggestions
    
    def get_productivity_score(self) -> float:
        """Calculate current productivity score."""
        if not self.command_history:
            return 0.5
        
        now = time.time()
        recent = [e for e in self.command_history if now - e["timestamp"] < 3600]  # Last hour
        
        if not recent:
            return 0.3
        
        # Score based on consistency and variety
        variety = len(set(e["command"] for e in recent))
        consistency = len(recent) / 10  # 10 commands = full score
        
        score = min(1.0, (variety * 0.3 + consistency * 0.7))
        return round(score, 2)
    
    def get_insights(self) -> Dict[str, Any]:
        """Get productivity insights."""
        return {
            "current_time_slot": self.predict_time_slot(),
            "suggestion": self.suggest_task(),
            "daily_schedule": self.get_daily_schedule_suggestion(),
            "productivity_score": self.get_productivity_score(),
            "total_commands_today": len(self.command_history),
            "top_tasks": [
                {"task": task, "count": count}
                for task, count in sorted(
                    self.task_patterns.items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
            ],
        }
    
    def load_patterns(self):
        """Load patterns from file."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    data = json.load(f)
                    self.command_history = data.get('history', [])
                    self.task_patterns = defaultdict(int, data.get('patterns', {}))
                log_event("Patterns loaded", f"commands={len(self.command_history)}")
            except Exception as e:
                log_error("LoadPatterns", e)
    
    def save_patterns(self):
        """Save patterns to file."""
        try:
            with open(self.memory_file, 'w') as f:
                json.dump({
                    'history': self.command_history[-500:],  # Keep last 500
                    'patterns': dict(self.task_patterns),
                }, f)
        except Exception as e:
            log_error("SavePatterns", e)


# Global instance
_predictive_productivity: Optional[PredictiveProductivity] = None


def get_predictive_productivity() -> PredictiveProductivity:
    """Get global predictive productivity instance."""
    global _predictive_productivity
    if _predictive_productivity is None:
        _predictive_productivity = PredictiveProductivity()
    return _predictive_productivity


def get_smart_suggestion() -> Optional[TaskSuggestion]:
    """Get a smart task suggestion."""
    return get_predictive_productivity().suggest_task()


__all__ = [
    "PredictiveProductivity",
    "UserPattern",
    "TaskSuggestion",
    "get_predictive_productivity",
    "get_smart_suggestion",
]
