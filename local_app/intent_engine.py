# intent_engine.py
import json
import webbrowser
from groq import Groq
import os
from datetime import datetime

class IntentEngine:
    def __init__(self, api_key):
        self.client = Groq(api_key=api_key)
    
    def classify(self, text):
        prompt = f"""
        You are an AI that classifies user commands into specific tools/actions.

        Available tools and their arguments:
        1. open_browser - opens web browser (args: {{"url": "optional url"}})
        2. open_notepad - opens notepad (no args)
        3. open_calculator - opens calculator (no args)
        4. open_youtube - opens YouTube (no args)
        5. take_screenshot - takes screenshot (no args)
        6. lock_computer - locks computer (no args)
        7. shutdown_computer - shuts down computer (no args)
        8. restart_computer - restarts computer (no args)
        9. search_google - searches Google (args: {{"query": "search term"}})
        10. get_time - tells current time (no args)
        11. get_date - tells current date (no args)
        12. open_any_app - opens any application (args: {{"app": "app_name.exe"}})
        13. minimize_windows - minimizes all windows (no args)
        14. volume_up - increases volume (no args)
        15. volume_down - decreases volume (no args)
        16. mute_volume - mutes volume (no args)

        User command: "{text}"

        Return ONLY a JSON object in one of these formats:
        For tool: {{"type": "tool", "tool": "tool_name", "args": {{...}}}}
        For chat: {{"type": "chat"}}

        Examples:
        - "open chrome" -> {{"type": "tool", "tool": "open_any_app", "args": {{"app": "chrome"}}}}
        - "search for cats" -> {{"type": "tool", "tool": "search_google", "args": {{"query": "cats"}}}}
        - "what time is it" -> {{"type": "tool", "tool": "get_time", "args": {{}}}}
        - "hello how are you" -> {{"type": "chat"}}
        """

        try:
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a command classifier. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                max_tokens=150
            )

            content = response.choices[0].message.content.strip()
            
            # Clean the response to extract just the JSON
            if content.startswith('```json'):
                content = content.replace('```json', '').replace('```', '')
            elif content.startswith('```'):
                content = content.replace('```', '')
            
            return json.loads(content)
            
        except Exception as e:
            print(f"Intent classification error: {e}")
            return {"type": "chat"}