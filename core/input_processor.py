"""
Perfect Input Processing System for BKR 2.0 - Human Clone Edition.

Features:
- Accurate input understanding with context awareness
- Fast topic detection and classification
- Smart intent recognition
- Teaching-focused response optimization
- Safety-first processing to prevent system damage
"""

import re
import json
from typing import Dict, List, Tuple, Optional
import config
from core.logger import log_event, log_error

class InputProcessor:
    """
    Advanced input processing system that accurately understands user intent
    and optimizes responses for teaching and safety.
    """
    
    def __init__(self):
        self.teaching_keywords = {
            "education": ["teach", "learn", "study", "explain", "understand", "knowledge"],
            "programming": ["code", "program", "python", "javascript", "html", "css", "debug"],
            "math": ["calculate", "math", "algebra", "geometry", "equation", "formula"],
            "science": ["science", "physics", "chemistry", "biology", "experiment", "research"],
            "language": ["english", "translate", "grammar", "vocabulary"],
            "general": ["what", "why", "how", "when", "where", "who", "which"]
        }
        
        self.safety_keywords = {
            "dangerous": ["delete", "format", "destroy", "break", "corrupt", "remove", "erase"],
            "system": ["registry", "system32", "windows", "boot", "startup", "driver"],
            "network": ["hack", "crack", "bypass", "exploit", "virus", "malware"]
        }
        
        self.emotion_keywords = {
            "happy": ["happy", "good", "great", "excellent", "wonderful", "amazing"],
            "sad": ["sad", "depressed", "unhappy", "down", "lonely", "hurt"],
            "angry": ["angry", "mad", "frustrated", "annoyed", "upset", "furious"],
            "stressed": ["stressed", "overwhelmed", "anxious", "worried", "nervous", "tired"],
            "confused": ["confused", "lost", "uncertain", "don't understand", "what", "why"]
        }
        
        self.conversation_patterns = {
            "greeting": r"^(hello|hi|hey|good morning|good afternoon|good evening|namaste)",
            "question": r"^(what|why|how|when|where|who|which|can you|could you|would you)",
            "command": r"^(please|can you|could you|would you|let's|start|begin|open|close|run|execute)",
            "teaching": r"^(teach me|learn|explain|help me understand|what is|how to|can you teach)",
            "safety_check": r"^(is it safe|can i|should i|will it|does it|can this)"
        }
        
        self.last_input_context = {}
        self.conversation_history = []
        
    def process_input(self, user_input: str) -> Dict:
        """
        Process user input and return structured analysis for optimal response.
        """
        if not user_input or not user_input.strip():
            return {
                "original_input": "",
                "processed_input": "",
                "intent_type": "empty",
                "topic_category": "none",
                "emotion": "neutral",
                "safety_level": "safe",
                "teaching_focus": False,
                "response_priority": "none",
                "context": {},
                "confidence": 0.0
            }
        
        # Clean and normalize input
        cleaned_input = self._clean_input(user_input)
        
        # Analyze input components
        intent_analysis = self._analyze_intent(cleaned_input)
        topic_analysis = self._analyze_topic(cleaned_input)
        emotion_analysis = self._analyze_emotion(cleaned_input)
        safety_analysis = self._analyze_safety(cleaned_input)
        
        # Generate response optimization
        response_optimization = self._optimize_response(
            intent_analysis, topic_analysis, emotion_analysis, safety_analysis
        )
        
        # Update context
        self._update_context(cleaned_input, intent_analysis, topic_analysis)
        
        # Log the processing
        log_event("InputProcessed", f"input='{cleaned_input[:50]}' intent={intent_analysis['type']} topic={topic_analysis['category']}")
        
        return {
            "original_input": user_input,
            "processed_input": cleaned_input,
            "intent_type": intent_analysis["type"],
            "topic_category": topic_analysis["category"],
            "emotion": emotion_analysis["detected"],
            "safety_level": safety_analysis["level"],
            "teaching_focus": response_optimization["teaching_focus"],
            "response_priority": response_optimization["priority"],
            "context": {
                "keywords": intent_analysis["keywords"],
                "confidence": intent_analysis["confidence"],
                "topic_keywords": topic_analysis["keywords"],
                "emotion_keywords": emotion_analysis["keywords"],
                "safety_keywords": safety_analysis["keywords"]
            },
            "confidence": max(intent_analysis["confidence"], topic_analysis["confidence"])
        }
    
    def _clean_input(self, text: str) -> str:
        """Clean and normalize input text."""
        # Remove extra whitespace
        text = " ".join(text.split())
        
        # Remove special characters that might interfere with processing
        text = re.sub(r'[^\w\s.,?!]', ' ', text)
        
        # Normalize common abbreviations
        text = text.lower()
        text = re.sub(r'\bi m\b', 'i am', text)
        text = re.sub(r'\bi ve\b', 'i have', text)
        text = re.sub(r'\bi ll\b', 'i will', text)
        text = re.sub(r'\bi d\b', 'i would', text)
        
        return text.strip()
    
    def _analyze_intent(self, text: str) -> Dict:
        """Analyze the intent behind the user's input."""
        text_lower = text.lower()
        
        # Check conversation patterns
        for pattern_name, pattern in self.conversation_patterns.items():
            if re.search(pattern, text_lower):
                return {
                    "type": pattern_name,
                    "keywords": [pattern_name],
                    "confidence": 0.8,
                    "details": f"Matched {pattern_name} pattern"
                }
        
        # Check for specific commands
        command_keywords = ["open", "close", "run", "execute", "start", "begin", "stop", "exit"]
        if any(keyword in text_lower for keyword in command_keywords):
            return {
                "type": "command",
                "keywords": [kw for kw in command_keywords if kw in text_lower],
                "confidence": 0.9,
                "details": "Detected command intent"
            }
        
        # Check for questions
        question_words = ["what", "why", "how", "when", "where", "who", "which"]
        if any(text_lower.startswith(word) for word in question_words):
            return {
                "type": "question",
                "keywords": [word for word in question_words if text_lower.startswith(word)],
                "confidence": 0.95,
                "details": "Detected question intent"
            }
        
        # Default to general conversation
        return {
            "type": "general",
            "keywords": ["general"],
            "confidence": 0.5,
            "details": "Default general conversation"
        }
    
    def _analyze_topic(self, text: str) -> Dict:
        """Analyze the topic category of the input."""
        text_lower = text.lower()
        topic_scores = {}
        
        # Score each topic category
        for category, keywords in self.teaching_keywords.items():
            score = 0
            found_keywords = []
            
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
                    found_keywords.append(keyword)
            
            if score > 0:
                topic_scores[category] = {
                    "score": score,
                    "keywords": found_keywords,
                    "confidence": min(1.0, score / len(keywords))
                }
        
        # Find the highest scoring topic
        if topic_scores:
            best_category = max(topic_scores.keys(), key=lambda k: topic_scores[k]["score"])
            return {
                "category": best_category,
                "keywords": topic_scores[best_category]["keywords"],
                "confidence": topic_scores[best_category]["confidence"],
                "details": f"Topic: {best_category} (score: {topic_scores[best_category]['score']})"
            }
        
        # Default to general if no specific topic found
        return {
            "category": "general",
            "keywords": [],
            "confidence": 0.3,
            "details": "No specific topic detected"
        }
    
    def _analyze_emotion(self, text: str) -> Dict:
        """Analyze the emotional state from the input."""
        text_lower = text.lower()
        emotion_scores = {}
        
        # Score each emotion
        for emotion, keywords in self.emotion_keywords.items():
            score = 0
            found_keywords = []
            
            for keyword in keywords:
                if keyword in text_lower:
                    score += 1
                    found_keywords.append(keyword)
            
            if score > 0:
                emotion_scores[emotion] = {
                    "score": score,
                    "keywords": found_keywords,
                    "confidence": min(1.0, score / len(keywords))
                }
        
        # Find the highest scoring emotion
        if emotion_scores:
            best_emotion = max(emotion_scores.keys(), key=lambda k: emotion_scores[k]["score"])
            return {
                "detected": best_emotion,
                "keywords": emotion_scores[best_emotion]["keywords"],
                "confidence": emotion_scores[best_emotion]["confidence"],
                "details": f"Emotion: {best_emotion} (score: {emotion_scores[best_emotion]['score']})"
            }
        
        # Default to neutral
        return {
            "detected": "neutral",
            "keywords": [],
            "confidence": 1.0,
            "details": "Neutral emotion detected"
        }
    
    def _analyze_safety(self, text: str) -> Dict:
        """Analyze potential safety concerns in the input."""
        text_lower = text.lower()
        safety_issues = []
        
        # Check for dangerous keywords
        for category, keywords in self.safety_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    safety_issues.append(f"{category}:{keyword}")
        
        if safety_issues:
            return {
                "level": "dangerous",
                "keywords": safety_issues,
                "confidence": 1.0,
                "details": f"Safety concerns detected: {', '.join(safety_issues)}"
            }
        
        # Check for safety-related questions
        safety_questions = ["is it safe", "can i", "should i", "will it", "does it", "can this"]
        if any(phrase in text_lower for phrase in safety_questions):
            return {
                "level": "caution",
                "keywords": ["safety_question"],
                "confidence": 0.8,
                "details": "Safety-related question detected"
            }
        
        # Default to safe
        return {
            "level": "safe",
            "keywords": [],
            "confidence": 1.0,
            "details": "No safety concerns detected"
        }
    
    def _optimize_response(self, intent: Dict, topic: Dict, emotion: Dict, safety: Dict) -> Dict:
        """Optimize response based on all analysis."""
        
        # Determine if this should be teaching-focused
        teaching_focus = (
            intent["type"] in ["question", "teaching"] or
            topic["category"] in ["education", "programming", "math", "science", "language"] or
            any(word in intent.get("keywords", []) for word in ["teach", "learn", "explain"])
        )
        
        # Determine response priority
        if safety["level"] == "dangerous":
            priority = "safety_warning"
        elif emotion["detected"] in ["stressed", "confused", "sad"]:
            priority = "empathy_support"
        elif teaching_focus:
            priority = "teaching"
        elif intent["type"] == "command":
            priority = "action"
        else:
            priority = "conversation"
        
        return {
            "teaching_focus": teaching_focus,
            "priority": priority,
            "response_style": self._get_response_style(priority, emotion["detected"]),
            "response_length": self._get_response_length(priority, topic["confidence"])
        }
    
    def _get_response_style(self, priority: str, emotion: str) -> str:
        """Determine the appropriate response style."""
        if priority == "safety_warning":
            return "direct_warning"
        elif priority == "empathy_support":
            return "empathetic"
        elif priority == "teaching":
            return "educational"
        elif emotion == "angry":
            return "calm"
        else:
            return "friendly"
    
    def _get_response_length(self, priority: str, topic_confidence: float) -> str:
        """Determine appropriate response length."""
        if priority == "safety_warning":
            return "very_short"  # 1-2 sentences
        elif priority == "empathy_support":
            return "short"  # 2-3 sentences
        elif topic_confidence > 0.7:
            return "medium"  # 3-5 sentences
        else:
            return "concise"  # 1-3 sentences
    def _update_context(self, cleaned_input: str, intent: Dict, topic: Dict):
        """Update conversation context for better understanding."""
        self.conversation_history.append({
            "input": cleaned_input,
            "intent": intent["type"],
            "topic": topic["category"],
            "timestamp": time.time()
        })
        
        # Keep only last 10 interactions
        if len(self.conversation_history) > 10:
            self.conversation_history.pop(0)
        
        # Update last input context
        self.last_input_context = {
            "last_intent": intent["type"],
            "last_topic": topic["category"],
            "last_keywords": intent.get("keywords", []),
            "recent_topics": [item["topic"] for item in self.conversation_history[-5:]]
        }
    
    def get_context_summary(self) -> Dict:
        """Get a summary of current conversation context."""
        return {
            "last_input_context": self.last_input_context,
            "conversation_history_length": len(self.conversation_history),
            "recent_topics": self.last_input_context.get("recent_topics", []),
            "current_focus": self.last_input_context.get("last_topic", "general")
        }
    
    def is_teaching_request(self, processed_input: Dict) -> bool:
        """Check if the input is a teaching request."""
        return (
            processed_input["intent_type"] in ["question", "teaching"] or
            processed_input["teaching_focus"] or
            processed_input["topic_category"] in ["education", "programming", "math", "science", "language"]
        )
    
    def should_warn_about_safety(self, processed_input: Dict) -> bool:
        """Check if safety warning is needed."""
        return processed_input["safety_level"] == "dangerous"
    
    def get_response_guidance(self, processed_input: Dict) -> Dict:
        """Get guidance for generating the optimal response."""
        return {
            "response_style": processed_input["context"].get("response_style", "friendly"),
            "response_length": processed_input["context"].get("response_length", "medium"),
            "teaching_mode": processed_input["teaching_focus"],
            "empathy_mode": processed_input["emotion"] in ["stressed", "confused", "sad"],
            "safety_mode": processed_input["safety_level"] != "safe",
            "topic_focus": processed_input["topic_category"],
            "confidence": processed_input["confidence"]
        }

# Global instance
input_processor = InputProcessor()

def process_user_input(user_input: str) -> Dict:
    """Global function to process user input."""
    return input_processor.process_input(user_input)

def get_input_context() -> Dict:
    """Global function to get current input context."""
    return input_processor.get_context_summary()

def is_teaching_request(user_input: str) -> bool:
    """Global function to check if input is a teaching request."""
    processed = process_user_input(user_input)
    return input_processor.is_teaching_request(processed)

def should_warn_about_safety(user_input: str) -> bool:
    """Global function to check if safety warning is needed."""
    processed = process_user_input(user_input)
    return input_processor.should_warn_about_safety(processed)

def get_response_guidance(user_input: str) -> Dict:
    """Global function to get response guidance."""
    processed = process_user_input(user_input)
    return input_processor.get_response_guidance(processed)