# intent_engine.py
import json
import webbrowser
from groq import Groq
import os
from datetime import datetime

class IntentEngine:
    def __init__(self, api_key=None):
        self.client = None
        self.enabled = False
        if api_key:
            self.client = Groq(api_key=api_key)
            self.enabled = True
        else:
            print("⚠️ IntentEngine disabled: No GROQ_API_KEY provided")
    
    def classify(self, text):
        if not self.enabled:
            return {"type": "chat"}

        prompt = f"""
        You are an AI that classifies user commands into specific tools/actions.

        Available tools and their arguments:
        1. open_browser - opens web browser (args: {{"url": "optional url"}})
        2. open_notepad - opens notepad (no args)
        3. open_calculator - opens calculator (no args)
        4. open_youtube - opens YouTube (no args)
        5. open_website - opens a specific website (args: {{"website": "instagram"}} or {{"url": "https://..."}})
        6. open_whatsapp - opens WhatsApp Web (no args)
        7. open_instagram - opens Instagram (no args)
        8. open_facebook - opens Facebook (no args)
        9. take_screenshot - takes screenshot (no args)
        10. lock_computer - locks computer (no args)
        11. shutdown_computer - shuts down computer (no args)
        12. restart_computer - restarts computer (no args)
        13. search_google - searches Google (args: {{"query": "search term"}})
        14. get_time - tells current time (no args)
        15. get_date - tells current date (no args)
        16. open_any_app - opens any application (args: {{"app": "app_name.exe"}})
        17. minimize_windows - minimizes all windows (no args)
        18. volume_up - increases volume (args: {{"steps": 5}})
        19. volume_down - decreases volume (args: {{"steps": 5}})
        20. mute_volume - mutes volume (no args)
        21. type_text - types visible text (args: {{"text": "hello"}})
        22. type_secret - types secret text like password or PIN without repeating it in the result (args: {{"password": "1234"}} or {{"pin": "1234"}})
        23. scroll_page - scrolls current page (args: {{"direction": "down", "amount": 700}})
        24. write_file - writes a file (args: {{"path": "file path", "content": "text"}})
        25. append_file - appends to a file (args: {{"path": "file path", "content": "text"}})
        26. replace_in_file - replaces text in a file (args: {{"path": "file path", "old_text": "find", "new_text": "replace"}})
        27. read_file - reads a file (args: {{"path": "file path"}})
        28. create_folder - creates a folder (args: {{"path": "folder path"}})
        29. delete_file - deletes a file (args: {{"path": "file path"}})
        30. delete_folder - deletes a folder (args: {{"path": "folder path"}})
        31. move_file - moves a file (args: {{"src": "from path", "dest": "to path"}})
        32. copy_file - copies a file (args: {{"src": "from path", "dest": "to path"}})
        33. rename_file - renames a file (args: {{"path": "file path", "new_name": "new.ext"}})
        34. list_files - lists files in a folder (args: {{"path": "folder path"}})
        35. open_file - opens a file (args: {{"path": "file path"}})
        36. open_folder - opens a folder (args: {{"path": "folder path"}})
        37. find_files - finds files (args: {{"pattern": "*.txt", "path": "optional folder"}})
        38. download_image - downloads an image to Downloads (args: {{"url": "https://..."}})
        39. download_video - downloads a direct video file to Downloads (args: {{"url": "https://...mp4"}})
        40. get_system_info - detailed system info (no args)
        41. list_processes - lists processes (no args)
        42. kill_process - closes a process (args: {{"name": "chrome"}} or {{"pid": 1234}})
        43. list_drives - lists drives (no args)
        44. run_command - runs a shell command (args: {{"command": "dir"}})
        45. open_task_manager - opens task manager (no args)
        46. open_settings - opens Windows settings (no args)
        47. open_control_panel - opens control panel (no args)
        48. refresh_window - presses refresh/F5 (no args)
        49. refresh_desktop - shows and refreshes desktop (no args)
        50. switch_panel - switches app tabs (args: {{"panel": "face|chat|voice|dashboard"}})
        51. start_camera - starts camera (no args)
        52. stop_camera - stops camera (no args)
        53. stop_voice_assistant - stops voice listening (no args)

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
