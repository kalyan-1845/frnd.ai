"""
Teaching Engine for BKR 2.0 - Human Clone Edition.

Features:
- Smart tutoring system with personalized learning
- Step-by-step explanation engine
- Interactive learning with examples and practice
- Progress tracking and adaptive teaching
- Subject-specific teaching modes
"""

import re
import json
import time
import random
from typing import Dict, List, Tuple, Optional
import config
from core.logger import log_event, log_error
from advanced.memory import MemorySystem

class TeachingEngine:
    """
    Advanced teaching engine that provides personalized, step-by-step
    learning experiences for users.
    """
    
    def __init__(self, memory_system: MemorySystem):
        self.memory = memory_system
        self.learning_styles = {
            "visual": ["show", "visual", "diagram", "chart", "graph", "picture"],
            "auditory": ["explain", "tell", "describe", "read", "listen", "voice"],
            "kinesthetic": ["practice", "do", "try", "exercise", "example", "action"],
            "reading": ["read", "text", "book", "article", "document", "write"],
            "logical": ["reason", "logic", "proof", "derivation", "why"],
            "creative": ["story", "imagine", "metaphor", "analogy", "art"],
            "social": ["discuss", "talk", "chat", "collaborate", "group"]
        }
        
        self.subject_expertise = {
            "programming": {
                "keywords": ["code", "program", "python", "javascript", "html", "css", "debug", "algorithm", "software"],
                "levels": ["beginner", "intermediate", "advanced"],
                "topics": ["basics", "functions", "data structures", "algorithms", "web development", "debugging", "AI", "machine learning"]
            },
            "math": {
                "keywords": ["math", "algebra", "geometry", "equation", "formula", "calculate", "solve", "maths", "arithmetic"],
                "levels": ["beginner", "intermediate", "advanced"],
                "topics": ["arithmetic", "algebra", "geometry", "calculus", "statistics", "trigonometry"]
            },
            "science": {
                "keywords": ["science", "physics", "chemistry", "biology", "experiment", "research", "nature", "space"],
                "levels": ["beginner", "intermediate", "advanced"],
                "topics": ["basic concepts", "experiments", "theories", "applications", "astronomy", "evolution"]
            },
            "language": {
                "keywords": ["english", "translate", "grammar", "vocabulary", "learn", "speaking", "writing"],
                "levels": ["beginner", "intermediate", "advanced"],
                "topics": ["grammar", "vocabulary", "conversation", "writing", "phonetics"]
            },
            "general": {
                "keywords": ["learn", "study", "understand", "knowledge", "education", "info", "fact"],
                "levels": ["beginner", "intermediate", "advanced"],
                "topics": ["general knowledge", "skills", "concepts", "history", "geography"]
            }
        }
        
        self.teaching_methods = {
            "step_by_step": ["explain", "how to", "steps", "process"],
            "example_based": ["example", "show me", "demonstrate", "illustrate"],
            "question_answer": ["what is", "why", "how", "when", "where", "who"],
            "practice_oriented": ["practice", "exercise", "quiz", "test", "solve"],
            "feynman": ["simple", "plain english", "like i'm five", "eli5"],
            "socratic": ["question", "ask me", "guide", "inquiry"],
            "storytelling": ["story", "narrative", "tale", "analogy"],
            "first_principles": ["break down", "fundamental", "basics", "from scratch"],
            "deep_dive": ["advanced", "deep", "complex", "everything", "expert"]
        }
        
        self.user_progress = {}
        self.current_lesson = None
        self.lesson_history = []
        
    def analyze_learning_request(self, user_input: str) -> Dict:
        """
        Analyze user's learning request and determine teaching approach.
        """
        input_lower = user_input.lower().strip()
        
        # Determine subject
        subject = self._identify_subject(input_lower)
        
        # Determine learning style
        learning_style = self._identify_learning_style(input_lower)
        
        # Determine teaching method
        teaching_method = self._identify_teaching_method(input_lower)
        
        # Determine complexity level
        complexity = self._identify_complexity(input_lower)
        
        # Check user's current level
        user_level = self._get_user_level(subject)
        
        return {
            "subject": subject,
            "learning_style": learning_style,
            "teaching_method": teaching_method,
            "complexity": complexity,
            "user_level": user_level,
            "topic": self._extract_topic(input_lower, subject),
            "confidence": self._calculate_confidence(input_lower, subject, learning_style)
        }
    
    def create_lesson_plan(self, analysis: Dict) -> Dict:
        """
        Create a structured lesson plan based on user analysis.
        """
        subject = analysis["subject"]
        user_level = analysis["user_level"]
        topic = analysis["topic"]
        
        # Determine teaching method to use (with variety)
        method = analysis["teaching_method"]
        if method == "question_answer" and analysis["confidence"] < 0.8:
            # Add variety if confidence is low by picking a random advanced method
            method = random.choice(list(self.teaching_methods.keys()))
            
        # Create lesson structure
        lesson_plan = {
            "subject": subject,
            "topic": topic,
            "level": user_level,
            "method": method,
            "style": analysis["learning_style"],
            "duration": self._estimate_duration(user_level, topic),
            "steps": [],
            "examples": [],
            "practice": [],
            "assessment": []
        }
        
        # Generate lesson steps based on method
        if method == "step_by_step":
            lesson_plan["steps"] = self._create_step_by_step_lesson(subject, topic, user_level)
        elif method == "example_based":
            lesson_plan["steps"] = self._create_example_based_lesson(subject, topic, user_level)
        elif method == "question_answer":
            lesson_plan["steps"] = self._create_qa_lesson(subject, topic, user_level)
        elif method == "feynman":
            lesson_plan["steps"] = [f"ELI5 of {topic}", f"Simplifying {topic} core", f"Analogy for {topic}", f"Common misconceptions about {topic}"]
        elif method == "socratic":
            lesson_plan["steps"] = [f"Foundational question on {topic}", f"Exploring {topic} implications", f"Critical challenge for {topic}", f"Synthesizing {topic}"]
        elif method == "storytelling":
            lesson_plan["steps"] = [f"The Tale of {topic}", f"Challenges in the {topic} world", f"The {topic} epiphany", f"Lesson learned from {topic}"]
        elif method == "first_principles":
            lesson_plan["steps"] = [f"Deconstructing {topic}", f"Rebuilding {topic} from basics", f"Why {topic} must exist", f"Mastering {topic} fundamentals"]
        elif method == "deep_dive":
            lesson_plan["steps"] = [f"Exhaustive overview of {topic}", f"Under-the-hood of {topic}", f"Edge cases in {topic}", f"Advanced {topic} mastery"]
        else:
            lesson_plan["steps"] = self._create_general_lesson(subject, topic, user_level)
        
        # Add examples and practice
        lesson_plan["examples"] = self._generate_examples(subject, topic, user_level)
        lesson_plan["practice"] = self._generate_practice(subject, topic, user_level)
        lesson_plan["assessment"] = self._generate_assessment(subject, topic, user_level)
        
        return lesson_plan
    
    def _identify_subject(self, input_text: str) -> str:
        """Identify the subject from user input."""
        for subject, info in self.subject_expertise.items():
            for keyword in info["keywords"]:
                if keyword in input_text:
                    return subject
        return "general"
    
    def _identify_learning_style(self, input_text: str) -> str:
        """Identify the user's preferred learning style."""
        for style, keywords in self.learning_styles.items():
            for keyword in keywords:
                if keyword in input_text:
                    return style
        return "reading"  # Default learning style
    
    def _identify_teaching_method(self, input_text: str) -> str:
        """Identify the preferred teaching method."""
        for method, keywords in self.teaching_methods.items():
            for keyword in keywords:
                if keyword in input_text:
                    return method
        return "question_answer"  # Default method
    
    def _identify_complexity(self, input_text: str) -> str:
        """Identify the complexity level requested."""
        if any(word in input_text for word in ["advanced", "expert", "complex"]):
            return "advanced"
        elif any(word in input_text for word in ["intermediate", "medium", "moderate"]):
            return "intermediate"
        else:
            return "beginner"
    
    def _get_user_level(self, subject: str) -> str:
        """Get user's current level for the subject."""
        try:
            user_level = self.memory.get_user_role()
            if user_level in ["student", "beginner"]:
                return "beginner"
            elif user_level in ["professor", "teacher", "expert"]:
                return "advanced"
            else:
                return "intermediate"
        except:
            return "beginner"
    
    def _extract_topic(self, input_text: str, subject: str) -> str:
        """Extract the specific topic from user input."""
        # Clean input
        clean_text = re.sub(r"^(teach me|help me learn|explain|learn about|study)\s+", "", input_text).strip()
        
        # Look for keywords
        topic_keywords = self.subject_expertise[subject]["topics"]
        for keyword in topic_keywords:
            if keyword.lower() in input_text.lower():
                return keyword
        
        # If no specific keyword, return the cleaned text as topic
        if len(clean_text) > 2:
            return clean_text
            
        return "general concepts"
    
    def _calculate_confidence(self, input_text: str, subject: str, learning_style: str) -> float:
        """Calculate confidence in the analysis."""
        confidence = 0.5  # Base confidence
        
        # Increase confidence based on keyword matches
        subject_keywords = self.subject_expertise[subject]["keywords"]
        for keyword in subject_keywords:
            if keyword in input_text:
                confidence += 0.1
        
        # Increase confidence for specific learning style
        if learning_style != "reading":  # Default
            confidence += 0.1
        
        return min(1.0, confidence)
    
    def _estimate_duration(self, level: str, topic: str) -> str:
        """Estimate lesson duration."""
        if level == "beginner":
            return "10-15 minutes"
        elif level == "intermediate":
            return "15-25 minutes"
        else:
            return "25-40 minutes"
    
    def _create_step_by_step_lesson(self, subject: str, topic: str, level: str) -> List[str]:
        """Create a step-by-step lesson structure."""
        steps = [
            f"Step 1: Introduction to {topic}",
            f"Step 2: Key concepts and terminology",
            f"Step 3: Core principles and fundamentals",
            f"Step 4: Practical application",
            f"Step 5: Common pitfalls and solutions",
            f"Step 6: Summary and next steps"
        ]
        return steps
    
    def _create_example_based_lesson(self, subject: str, topic: str, level: str) -> List[str]:
        """Create an example-based lesson structure."""
        steps = [
            f"Example 1: Basic {topic} demonstration",
            f"Example 2: Intermediate {topic} application",
            f"Example 3: Advanced {topic} scenario",
            f"Example 4: Real-world {topic} use case",
            f"Example 5: Troubleshooting common issues"
        ]
        return steps
    
    def _create_qa_lesson(self, subject: str, topic: str, level: str) -> List[str]:
        """Create a question-and-answer lesson structure."""
        steps = [
            f"Q1: What is {topic} and why is it important?",
            f"Q2: How does {topic} work in practice?",
            f"Q3: What are the key components of {topic}?",
            f"Q4: When should you use {topic}?",
            f"Q5: What are common mistakes with {topic}?"
        ]
        return steps
    
    def _create_general_lesson(self, subject: str, topic: str, level: str) -> List[str]:
        """Create a general lesson structure."""
        steps = [
            f"Overview of {topic}",
            f"Key concepts and principles",
            f"Practical applications",
            f"Tips and best practices",
            f"Summary and review"
        ]
        return steps
    
    def _generate_examples(self, subject: str, topic: str, level: str) -> List[str]:
        """Generate relevant examples for the lesson."""
        examples = []
        
        if subject == "programming":
            examples = [
                f"Simple {topic} code example",
                f"Complete {topic} implementation",
                f"Common {topic} patterns"
            ]
        elif subject == "math":
            examples = [
                f"Basic {topic} problem with solution",
                f"Step-by-step {topic} calculation",
                f"Real-world {topic} application"
            ]
        elif subject == "language":
            examples = [
                f"Common {topic} usage examples",
                f"Grammar rules for {topic}",
                f"Vocabulary related to {topic}"
            ]
        else:
            examples = [
                f"Example of {topic} in action",
                f"Case study: {topic} application",
                f"Practical demonstration of {topic}"
            ]
        
        return examples
    
    def _generate_practice(self, subject: str, topic: str, level: str) -> List[str]:
        """Generate practice exercises for the lesson."""
        practice = []
        
        if level == "beginner":
            practice = [
                f"Exercise 1: Basic {topic} identification",
                f"Exercise 2: Simple {topic} application",
                f"Exercise 3: {topic} concept review"
            ]
        elif level == "intermediate":
            practice = [
                f"Exercise 1: Intermediate {topic} problems",
                f"Exercise 2: {topic} implementation challenge",
                f"Exercise 3: {topic} troubleshooting"
            ]
        else:
            practice = [
                f"Exercise 1: Advanced {topic} scenarios",
                f"Exercise 2: Complex {topic} problems",
                f"Exercise 3: {topic} optimization techniques"
            ]
        
        return practice
    
    def _generate_assessment(self, subject: str, topic: str, level: str) -> List[str]:
        """Generate assessment questions for the lesson."""
        assessment = []
        
        if level == "beginner":
            assessment = [
                f"Question 1: What is the definition of {topic}?",
                f"Question 2: Can you identify examples of {topic}?",
                f"Question 3: How would you apply {topic} in a simple case?"
            ]
        elif level == "intermediate":
            assessment = [
                f"Question 1: Explain the principles of {topic}",
                f"Question 2: Solve this {topic} problem",
                f"Question 3: Compare different approaches to {topic}"
            ]
        else:
            assessment = [
                f"Question 1: Analyze this complex {topic} scenario",
                f"Question 2: Design a solution using {topic}",
                f"Question 3: Evaluate the effectiveness of {topic} approaches"
            ]
        
        return assessment
    
    def deliver_lesson(self, lesson_plan: Dict) -> str:
        """Deliver the lesson step by step."""
        subject = lesson_plan["subject"]
        topic = lesson_plan["topic"]
        level = lesson_plan["level"]
        
        # Start the lesson
        method_name = lesson_plan.get("method", "Standard").replace("_", " ").title()
        style_name = lesson_plan.get("style", "Reading").title()
        
        lesson_intro = f"📚 **Welcome to your {subject} lesson!**\n\n"
        lesson_intro += f"**Topic:** {topic}\n"
        lesson_intro += f"**Approach:** {method_name} ({style_name} style)\n"
        lesson_intro += f"**Level:** {level}\n"
        lesson_intro += f"**Duration:** {lesson_plan['duration']}\n\n"
        lesson_intro += "Let's begin!\n\n"
        
        # Deliver steps
        lesson_content = lesson_intro
        
        for i, step in enumerate(lesson_plan["steps"], 1):
            lesson_content += f"**Step {i}:** {step}\n\n"
            
            # Add examples after each step
            if i <= len(lesson_plan["examples"]):
                lesson_content += f"**Example:** {lesson_plan['examples'][i-1]}\n\n"
            
            # Add practice after every 2 steps
            if i % 2 == 0 and (i//2 - 1) < len(lesson_plan["practice"]):
                lesson_content += f"**Practice Exercise:** {lesson_plan['practice'][i//2 - 1]}\n\n"
        
        # Add final assessment
        lesson_content += "**Final Assessment:**\n\n"
        for i, question in enumerate(lesson_plan["assessment"], 1):
            lesson_content += f"{i}. {question}\n"
        
        lesson_content += "\n**Great job!** You've completed the lesson. Keep practicing to reinforce your learning!"
        
        # Update user progress
        self._update_user_progress(subject, topic, level)
        
        return lesson_content
    
    def _update_user_progress(self, subject: str, topic: str, level: str):
        """Update user's learning progress."""
        if subject not in self.user_progress:
            self.user_progress[subject] = {}
        
        if topic not in self.user_progress[subject]:
            self.user_progress[subject][topic] = {
                "level": level,
                "completed": 0,
                "attempts": 0,
                "last_completed": time.time()
            }
        
        self.user_progress[subject][topic]["completed"] += 1
        self.user_progress[subject][topic]["last_completed"] = time.time()
        
        # Save progress to memory
        try:
            self.memory.store_preference(f"learning_progress_{subject}_{topic}", 
                                       json.dumps(self.user_progress[subject][topic]))
        except:
            pass
    
    def get_learning_recommendations(self, subject: str = None) -> List[str]:
        """Get personalized learning recommendations."""
        recommendations = []
        
        if subject:
            # Specific subject recommendations
            subject_info = self.subject_expertise.get(subject, self.subject_expertise["general"])
            recommendations.append(f"📚 **Recommended {subject} Topics:**")
            for topic in subject_info["topics"][:3]:
                recommendations.append(f"- {topic}")
        else:
            # General recommendations
            recommendations.append("📚 **Personalized Learning Recommendations:**")
            recommendations.append("- Review topics you've recently studied")
            recommendations.append("- Practice with interactive exercises")
            recommendations.append("- Explore related subjects")
            recommendations.append("- Set specific learning goals")
        
        return recommendations

# Global teaching engine instance
teaching_engine = TeachingEngine(None)  # Will be set when initialized

def analyze_learning_request(user_input: str) -> Dict:
    """Global function to analyze learning request."""
    return teaching_engine.analyze_learning_request(user_input)

def create_lesson_plan(analysis: Dict) -> Dict:
    """Global function to create lesson plan."""
    return teaching_engine.create_lesson_plan(analysis)

def deliver_lesson(lesson_plan: Dict) -> str:
    """Global function to deliver lesson."""
    return teaching_engine.deliver_lesson(lesson_plan)

def get_learning_recommendations(subject: str = None) -> List[str]:
    """Global function to get learning recommendations."""
    return teaching_engine.get_learning_recommendations(subject)
