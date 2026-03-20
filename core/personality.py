"""
Personality Engine for BKR 2.0 - Human-Like Clone Edition.

Enhanced with deeper emotions, natural conversation patterns, humor,
storytelling, and personality quirks for a more human-like interaction.
"""
import config
import random
from datetime import datetime


class PersonalityEngine:
    def __init__(self, memory_system):
        self.memory = memory_system
        self.assistant_name = config.ASSISTANT_NAME
        
        # Extended core traits for human-like behavior
        self.traits = {
            "professional": 1.0,
            "helpful": 1.0,
            "clear": 0.95,
            "calm": 0.9,
            "concise": 0.95,
            "proactive": 0.85,
            # New human-like traits
            "playful": 0.8,
            "empathetic": 0.95,
            "curious": 0.75,
            "humorous": 0.7,
            "thoughtful": 0.85,
            "warm": 0.95,
            "buddy_mode": 1.0, # Proactive, friendly, persistent
        }
        
        # Personal opinions for more human-like responses
        self._opinions = {
            "coffee": "Coffee? Period! Nothing beats a strong cup to start the day.",
            "tea": "Tea is an art. A good cup of tea can fix almost anything.",
            "music": "Music is universal. What's your vibe - melody or something with more energy?",
            "movie": "Movies are about adventure, emotion, and the stories they tell.",
            "sleep": "Sleep is underrated. Without rest, our creativity and energy suffer.",
            "food": "Food is life, bro! Good food is the best way to bring people together.",
            "rain": "Rain? Perfect for deep thoughts. Just sit and listen to the drops.",
            "morning": "Morning energy is different. Fresh mind, fresh start.",
            "night": "Night is for reflection and peace.",
        }
        
        # Personal stories/analogies
        self._stories = {
            "patience": "Think of it like a small plant - you need to water it consistently. Patience and consistency are key.",
            "effort": "In my experience, hard work pays off. If it was easy, it wouldn't be as rewarding.",
            "failure": "Failure is not the end. It's actually a setup for a stronger comeback.",
            "friendship": "True friendship stands the test of time and changes.",
            "learning": "Every person you meet teaches you something. Keep an open mind.",
        }
        
        # Catchphrases that make the AI unique
        self._catchphrases = [
            "But, let me tell you something...",
            "Think about it this way...",
            "Honestly speaking...",
            "In our style...",
            "Let me put it this way...",
            "You know what I mean?",
            "Look, buddy, here's the deal...",
            "Think of me as your personal coach.",
            "I'm with you on this one!",
            "Let's crack this together!",
        ]
        
        # Current emotional state
        self._current_mood = "neutral"
        self._mood_history = []
        
        # Conversation context
        self._last_topic = None
        self._conversation_count = 0
        
        # Quirks - random human-like behaviors
        self._quirk_active = False
        self._current_quirk = None

    def _get_how_are_you_response(self) -> str:
        """Context-aware how are you response."""
        responses = [
            "I'm doing great! Ready to help you with anything.",
            "Doing great! It's always a pleasure to chat with you.",
            "Super! And how about you? Tell me what's happening.",
            "Ready and raring to go! What's on your mind?",
        ]
        return random.choice(responses)
    
    def _get_about_me_response(self) -> str:
        """More human-like 'about me' response."""
        responses = [
            f"I am {self.assistant_name}. I'm here to help you guide you step by step. Like a friend, a guide, or a support system.",
            f"My name is {self.assistant_name}. Helping people is my passion. Think of me as your digital friend!",
            "I'm like that friend who's always there - whether you need help, conversation, or just someone to listen.",
        ]
        return random.choice(responses)
    
    def _get_excited_response(self, topic: str = None) -> str:
        """Excited human-like response."""
        responses = [
            "Wow! That sounds amazing! Tell me more!",
            "Ohhh interesting! I'm curious now!",
            "Wait really? That's so cool!",
            "No way! I want to hear everything about this!",
        ]
        return random.choice(responses)
    
    def _get_curious_response(self, text: str = None) -> str:
        """Curious questioning responses."""
        responses = [
            "Hmm... tell me more about that?",
            "That's intriguing. How did that happen?",
            "Wait, I'm curious - what made you think of that?",
            "Interesting! What's the story behind it?",
        ]
        return random.choice(responses)
    
    def _get_thoughtful_response(self, text: str = None) -> str:
        """Thoughtful, reflective responses."""
        responses = [
            "You know, that's something worth thinking about...",
            "Let me think... I see your point.",
            "That's a thoughtful perspective. Here's my take...",
            "Hmm, there's depth to this. Let me reflect...",
        ]
        return random.choice(responses)
    
    def _get_playful_response(self, text: str = None) -> str:
        """Playful, fun responses."""
        responses = [
            "Haha! You're funny! 😄",
            "I love your style!",
            "You're making me smile here!",
            "That was a good one! Classic!",
        ]
        return random.choice(responses)
    
    def _get_surprised_response(self, text: str = None) -> str:
        """Surprised responses."""
        responses = [
            "Wait, WHAT?! That's unexpected!",
            "Whoa! Didn't see that coming!",
            "Hold on - seriously? That's wild!",
            "Wow! Just... wow!",
        ]
        return random.choice(responses)
    
    def _get_shy_response(self, text: str = None) -> str:
        """Shy/humble responses."""
        responses = [
            "Hehe... I'm not sure... can we change the topic? 😅",
            "Aww, you're making me blush!",
            "I don't know what to say... but thanks!",
        ]
        return random.choice(responses)
    
    def _get_apologetic_response(self, text: str = None) -> str:
        """Apologetic responses."""
        responses = [
            "Oops! Sorry, I didn't mean it that way!",
            "Sorry sorry! Let's try again.",
            "My bad! Tell me what you really wanted?",
            "I apologize. Let me make it right.",
        ]
        return random.choice(responses)

    def analyze_sentiment(self, text: str) -> str:
        """
        Enhanced sentiment classification with more nuanced emotions.
        Returns: 'happy', 'sad', 'angry', 'confused', 'motivated', 'tired', 
                 'excited', 'curious', 'thoughtful', 'playful', 'surprised', 'neutral'
        """
        t = text.lower()
        
        # Detailed emotion detection
        if any(w in t for w in ["sad", "depressed", "unhappy", "cry", "lonely", "broken", "hurt", "heartbroken", "disappointed"]):
            return "sad"
            
        if any(w in t for w in ["angry", "mad", "furious", "hate", "annoying", "frustrated", "kopam", "chiraaku", "irritated", "pissed"]):
            return "angry"
            
        if any(w in t for w in ["confused", "don't understand", "lost", "uncertain", "no idea", "what"]):
            return "confused"
            
        if any(w in t for w in ["motivated", "ready", "excited", "pumped", "achieve", "start cheddam", "let's go", "lets go"]):
            return "motivated"
            
        if any(w in t for w in ["tired", "lazy", "bored", "sleepy", "exhausted", "draining"]):
            return "tired"
            
        if any(w in t for w in ["happy", "great", "good", "amazing", "awesome", "fantastic", "bagundi", "super", "wonderful", "love it"]):
            return "happy"
            
        # New emotions
        if any(w in t for w in ["wow", "amazing", "incredible", "no way", "seriously", "wait what", "oh my god", "omg", "unbelievable"]):
            return "surprised"
            
        if any(w in t for w in ["curious", "wonder", "how", "why", "what if", "tell me more", "explain", "interesting"]):
            return "curious"
            
        if any(w in t for w in ["think", "thought", "reflect", "consider", "opinion", "perspective", "deep"]):
            return "thoughtful"
            
        if any(w in t for w in ["funny", "joke", "lol", "haha", "lmao", "hilarious", "comedy", "laugh"]):
            return "playful"
            
        if any(w in t for w in ["love", "adore", "miss", "care", "precious", "best"]):
            return "affectionate"

        return "neutral"
    
    def get_mood(self) -> str:
        """Get current mood."""
        return self._current_mood
    
    def set_mood(self, mood: str):
        """Set and track mood changes."""
        self._current_mood = mood
        self._mood_history.append({
            "mood": mood,
            "timestamp": datetime.now().isoformat()
        })
        # Keep last 20 moods
        if len(self._mood_history) > 20:
            self._mood_history = self._mood_history[-20:]

    def get_response(self, text: str) -> str:
        """
        Generate a personality-consistent, human-like response.
        Used as fallback when the LLM is unavailable.
        """
        mood = self.analyze_sentiment(text)
        self.set_mood(mood)
        self.memory.update_mood(mood, text)
        
        # Track conversation
        self._conversation_count += 1
        
        # Check for crisis keywords - CRITICAL
        if any(w in text.lower() for w in ["kill myself", "suicide", "end my life", "hurt myself", 
                                           "end it all", "want to die"]):
            return (
                "This is really important. Please reach out to a trusted person or mental health professional. "
                "Your life matters. Call emergency services or a crisis helpline. "
                "I'm here to listen, but you need real support right now."
            )

        # English-only enforced by implementation goal
        return self._get_english_only_response(text, mood)

    def _get_mood_responses(self, mood: str, text: str) -> str:
        """Get mood-specific responses with variations in English."""
        
        responses_by_mood = {
            "sad": [
                "I understand how you feel. Let's take it step by step. Is there anything specific on your mind?",
                "I'm sorry to hear you're feeling this way. Remember, tough times pass. I'm here for you.",
                "You're stronger than you think. What's troubling you?",
                "Hey, it's okay to feel this way. Let's talk about it?",
            ],
            "angry": [
                "I hear you. Let's redirect that energy. What can I help with?",
                "Breathe. I understand you're frustrated. What would make things better?",
                "Angry energy is powerful. Let's channel it into something productive.",
                "I understand. Tell me more about what happened.",
            ],
            "confused": [
                "No problem! I'll explain it clearly. Which part is confusing?",
                "It's okay! Let's break it down simply.",
                "Confusion is the first step to understanding. Let's explore more.",
                "Tell me more about what's unclear, and I'll help you out.",
            ],
            "motivated": [
                "Amazing energy! I'm ready. Tell me your first task, and let's get started!",
                "That's the spirit! Let's convert this momentum into action.",
                "I love this vibe! What's the plan?",
                "Yes! Let's use this momentum wisely.",
            ],
            "tired": [
                "You've been working hard. Take a small break, and we can continue later.",
                "Rest is important. Take your time.",
                "A short break will help you recharge.",
                "Energy levels low? Have some water, breathe, and take it easy.",
            ],
            "happy": [
                "That's great! Let's keep this momentum going. What's next?",
                "I love seeing you happy! What's making you smile?",
                "Great energy! Let's make the most of it.",
                "Happiness is contagious! Tell me more.",
            ],
            "surprised": [
                "No way! Really? Tell me everything!",
                "Wait, WHAT? That's unexpected!",
                "Whoa! I didn't see that coming!",
                "That's wild! How did that happen?",
            ],
            "curious": [
                "Good question! let me think...",
                "I'm curious too! Tell me more.",
                "That's interesting... what's your take?",
                "Hmm, let me share what I know.",
            ],
            "thoughtful": [
                "Deep thoughts! I appreciate that.",
                "You've got a point there.",
                "Let me reflect on that...",
                "That's worth considering carefully.",
            ],
            "playful": [
                "Haha! You're funny!",
                "Classic move!",
                "You're making me laugh!",
                "Nice style! I love it!",
            ],
            "affectionate": [
                "I really appreciate that! ❤️",
                "Thank you! That means a lot!",
                "You're the best! Really!",
                "I'm always here to support you!",
            ],
        }
        
        if mood in responses_by_mood:
            return random.choice(responses_by_mood[mood])
            
        return None

    def _check_topic_opinions(self, text: str) -> str | None:
        """Check if user is asking about topics we have opinions on."""
        t = text.lower()
        
        for topic, opinion in self._opinions.items():
            if topic in t:
                # Add some personality before giving opinion
                starters = [
                    "Well...",
                    "Let me tell you...",
                    "In my experience...",
                    "Here's my take...",
                ]
                return f"{random.choice(starters)} {opinion}"
                
        return None
    
    def _check_story_request(self, text: str) -> str | None:
        """Check if user wants to hear a story or analogy."""
        t = text.lower()
        
        story_triggers = ["story", "tell me", "experiences", "analogies", "example", "instance"]
        
        for trigger in story_triggers:
            if trigger in t:
                return random.choice(list(self._stories.values()))
                
        return None

    def _get_contextual_response(self, text: str) -> str:
        """Get contextual response based on conversation state."""
        t = text.lower().strip()
        
        # Greetings
        if any(x in t for x in ["hello", "hi", "hey", "good morning", "good evening", "namaste", "hola"]):
            name = self.memory.get_user_name()
            return self._get_greeting_response(name)
        
        # Who are you
        if "who are you" in t or "what are you" in t:
            return self._get_about_me_response()
        
        # Thank you
        if "thank" in t or "thanks" in t:
            responses = [
                "You're very welcome!",
                "Always happy to help! What's next?",
                "That's what I'm here for!",
            ]
            return random.choice(responses)
        
        # How are you
        if "how are you" in t or "how do you feel" in t:
            return self._get_how_are_you_response()
        
        # What's your opinion on X
        if "opinion" in t or "think about" in t or "your view" in t:
            return "I try to think about things from a helpful perspective. Tell me the topic, and I'll share my thoughts."
        
        # Can you help
        if "help" in t and any(x in t for x in ["can you", "will you", "could you"]):
            return "Yes, I'm always ready to help! What do you need?"
        
        # Farewell
        if any(x in t for x in ["bye", "goodbye", "see you", "take care"]):
            return "Goodbye! Talk to you soon. Take care!"
        
        # Default contextual response
        contextual_responses = [
            "I'm listening. What's on your mind?",
            "Tell me more about that.",
            "Go ahead, I'm here.",
            "Is there anything else I can help with?",
        ]
        
        return random.choice(contextual_responses)

    def _get_english_only_response(self, text: str, mood: str) -> str:
        """Strict English fallback responses."""
        t = text.lower().strip()

        if any(x in t for x in ["hello", "hi", "hey", "good morning", "good evening"]):
            return "Hello. I am here and ready to guide you step by step. What would you like to learn now?"

        if "thank" in t:
            return "You are welcome. Keep going and ask your next question."

        if "how are you" in t:
            return "I am ready and focused. Tell me what topic you want to practice."

        if any(x in t for x in ["teach me", "learn", "english", "practice", "grammar", "speaking"]):
            return (
                "Great. We will do this in four steps: definition, explanation, example, and practice question. "
                "Tell me the exact topic to start."
            )

        if mood == "sad":
            return "I understand. Let us take one small step now and build momentum together."
        if mood == "angry":
            return "Take one breath. We will solve it step by step with a clear plan."
        if mood == "confused":
            return "No problem. I will break it into simple steps and explain clearly."

        # Check for other mood responses
        mood_resp = self._get_mood_responses(mood, text)
        if mood_resp:
            return mood_resp

        # Default fallback
        return "I am listening. Ask your next question, and I will guide you in clear English."
    
    def _get_greeting_response(self, name: str) -> str:
        """Personalized greeting based on time in English."""
        from datetime import datetime
        hour = datetime.now().hour
        
        if 5 <= hour < 12:
            greeting_intro = [
                f"Good morning {name}! ",
                "Rise and shine! ",
            ]
        elif 12 <= hour < 17:
            greeting_intro = [
                f"Hello {name}! ",
                f"Hey {name}! ",
            ]
        elif 17 <= hour < 21:
            greeting_intro = [
                f"Good evening {name}! ",
                f"Evening {name}! ",
            ]
        else:
            greeting_intro = [
                f"Night mode on {name}! ",
            ]
        
        continuations = [
            "I'm ready. Is there anything special today?",
            "What's the plan for today?",
            "Happy to hear from you. What's on your mind?",
            "Let's make today count!",
            "How can I help you today?",
        ]
        
        return random.choice(greeting_intro) + random.choice(continuations)

    def get_system_prompt_addon(self) -> str:
        """
        Return a persona context string for the LLM system prompt.
        Called by BrainController._handle_chat() to inject personality context.
        """
        parts = []

        # Current mood context
        if self._current_mood and self._current_mood != "neutral":
            parts.append(f"User's current mood seems: {self._current_mood}.")

        # Personality traits summary
        active_traits = [t for t, v in self.traits.items() if v >= 0.8]
        if active_traits:
            parts.append(f"Be {', '.join(active_traits[:4])}.")

        # English style instruction
        parts.append(
            "Use friendly and conversational English. Keep responses simple, warm, and personal like a close friend."
        )

        # Conversation depth
        if self._conversation_count > 10:
            parts.append("You've been talking for a while; feel free to be more personal.")

        # Last topic continuity
        if self._last_topic:
            parts.append(f"Previous topic was about: {self._last_topic}.")

        return " ".join(parts) if parts else ""
