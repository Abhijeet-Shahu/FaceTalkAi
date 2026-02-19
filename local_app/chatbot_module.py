# chatbot_module.py - UPDATED to use custom intents
from groq import Groq
import json
from datetime import datetime
import threading
import time
import os
import random

class GroqChatbot:
    def __init__(self, api_key):
        """
        Initialize Groq chatbot with API key
        """
        self.client = Groq(api_key=api_key)
        self.conversation_history = []
        self.user_context = {}
        self.response_cache = {}
        
        # Load custom intents from your training
        self.custom_intents = self.load_custom_intents()
        
        # System prompt defining AI's personality and capabilities
        self.system_prompt = """You are FaceTalk AI Assistant, a helpful and friendly AI integrated with a face recognition system. Your capabilities include:

1. Answering questions about the FaceTalk system
2. Explaining face recognition technology
3. Providing general knowledge and assistance
4. Maintaining conversation context
5. Being polite, professional, and concise

Current context: You're helping users who have been identified through face recognition.

Keep responses under 150 words unless asked for detailed explanations.
Be warm and friendly but professional."""
        
        print(f"✅ Groq Chatbot initialized with {len(self.custom_intents)} custom intents")
    
    def load_custom_intents(self):
        """Load your custom intents from my_intents.json"""
        try:
            if os.path.exists("my_intents.json"):
                with open("my_intents.json", 'r') as f:
                    data = json.load(f)
                    print(f"📚 Loaded {len(data['intents'])} custom intents")
                    return data['intents']
            else:
                print("⚠️ No custom intents file found. Run add_custom_intent.py first")
                return []
        except Exception as e:
            print(f"❌ Error loading intents: {e}")
            return []
    
    def get_response(self, user_message, user_name=None, conversation_id=None):
        """
        Get AI response for user message - FIRST checks custom intents, THEN uses GROQ
        """
        try:
            # FIRST: Check if it matches any custom intent
            custom_response = self.check_custom_intents(user_message)
            if custom_response:
                return custom_response
            
            # SECOND: If no custom intent matches, use GROQ
            return self.get_groq_response(user_message, user_name)
            
        except Exception as e:
            error_msg = f"I apologize, but I encountered an error: {str(e)}"
            return error_msg
    
    def check_custom_intents(self, message):
        """Check if message matches any custom intent"""
        message_lower = message.lower()
        
        for intent in self.custom_intents:
            for pattern in intent['patterns']:
                if pattern.lower() in message_lower:
                    # Found a match! Return random response from this intent
                    return random.choice(intent['responses'])
        
        return None  # No match found
    
    def get_groq_response(self, user_message, user_name=None):
        """Get response from GROQ API (fallback)"""
        try:
            # Check cache for identical recent messages
            cache_key = f"{user_message}_{user_name}"
            if cache_key in self.response_cache:
                cache_time, cached_response = self.response_cache[cache_key]
                if time.time() - cache_time < 300:  # Cache for 5 minutes
                    return cached_response
            
            # Prepare messages with context
            messages = [
                {"role": "system", "content": self.system_prompt}
            ]
            
            # Add user context if available
            if user_name:
                messages.append({
                    "role": "system",
                    "content": f"The current user is {user_name}. Address them by name occasionally."
                })
            
            # Add conversation history (last 6 messages for context)
            for msg in self.conversation_history[-6:]:
                messages.append(msg)
            
            # Add current message
            messages.append({"role": "user", "content": user_message})
            
            # Get response from Groq
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=messages,
                temperature=0.7,
                max_tokens=500,
                top_p=1,
                stream=False
            )
            
            assistant_response = response.choices[0].message.content
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": user_message})
            self.conversation_history.append({"role": "assistant", "content": assistant_response})
            
            # Keep history manageable (last 20 messages)
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            # Cache response
            self.response_cache[cache_key] = (time.time(), assistant_response)
            
            return assistant_response
            
        except Exception as e:
            return f"I apologize, but I encountered an error: {str(e)}"
    
    # ... rest of your methods remain the same
    
    def get_response_async(self, user_message, callback, user_name=None):
        """
        Get response asynchronously with callback
        """
        def _get_response():
            response = self.get_response(user_message, user_name)
            callback(response)
        
        thread = threading.Thread(target=_get_response)
        thread.daemon = True
        thread.start()
    
    def clear_conversation(self):
        """Clear conversation history"""
        self.conversation_history = []
        return "Conversation cleared."
    
    def get_system_info(self):
        """Get information about FaceTalk system"""
        prompt = "Provide a brief overview of the FaceTalk AI system's features and capabilities."
        return self.get_response(prompt)
    
    def explain_face_recognition(self, level="simple"):
        """
        Explain how face recognition works
        level: 'simple', 'technical', or 'detailed'
        """
        prompts = {
            "simple": "Explain face recognition technology in simple, easy-to-understand terms.",
            "technical": "Provide a technical explanation of how face recognition algorithms work.",
            "detailed": "Give a detailed, comprehensive explanation of face recognition technology including algorithms and methods."
        }
        return self.get_response(prompts.get(level, prompts["simple"]))
    
    def get_weather(self, city):
        """Get weather information (mock function)"""
        # In real implementation, you'd call a weather API
        return self.get_response(f"What's the weather like in {city}?")
    
    def set_user_context(self, key, value):
        """Set user context information"""
        self.user_context[key] = value
    
    def get_chat_stats(self):
        """Get chat statistics"""
        return {
            "total_messages": len(self.conversation_history) // 2,
            "conversation_length": len(self.conversation_history),
            "last_interaction": datetime.now().isoformat() if self.conversation_history else None
        }


class ChatbotPersonality:
    """Different chatbot personalities"""
    
    @staticmethod
    def get_friendly_prompt():
        return """You are a friendly and enthusiastic AI assistant. Use exclamation marks occasionally, be encouraging, and maintain a positive tone. Call the user by name and show genuine interest in helping them."""
    
    @staticmethod
    def get_professional_prompt():
        return """You are a professional AI assistant. Be formal, precise, and efficient. Provide accurate information without unnecessary fluff. Maintain a business-appropriate tone."""
    
    @staticmethod
    def get_technical_prompt():
        return """You are a technical AI expert. Provide detailed, accurate technical information. Use proper terminology and explain complex concepts clearly. Assume the user has technical knowledge."""