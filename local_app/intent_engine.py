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
        18. minimize_window - minimizes a specific window (args: {{"title": "FaceTalk"}})
        19. maximize_window - maximizes a specific window (args: {{"title": "FaceTalk"}})
        20. activate_window - activates a specific window (args: {{"title": "Word"}})
        21. volume_up - increases volume (args: {{"steps": 5}})
        22. volume_down - decreases volume (args: {{"steps": 5}})
        23. mute_volume - mutes volume (no args)
        24. open_word - opens Microsoft Word (no args)
        25. open_excel - opens Microsoft Excel (no args)
        26. open_powerpoint - opens Microsoft PowerPoint (no args)
        27. start_presentation - starts PowerPoint presentation (args: {{"from_beginning": true}})
        28. next_slide - moves to next slide (no args)
        29. previous_slide - moves to previous slide (no args)
        30. new_slide - inserts new slide (no args)
        31. duplicate_slide - duplicates current slide (no args)
        32. end_presentation - ends slideshow (no args)
        33. save_document - saves current document (no args)
        34. save_document_as - opens Save As (no args)
        35. type_text - types visible text (args: {{"text": "hello"}})
        36. type_secret - types secret text like password or PIN without repeating it in the result (args: {{"password": "1234"}} or {{"pin": "1234"}})
        37. scroll_page - scrolls current page (args: {{"direction": "down", "amount": 700}})
        38. write_file - writes a file (args: {{"path": "file path", "content": "text"}})
        39. append_file - appends to a file (args: {{"path": "file path", "content": "text"}})
        40. replace_in_file - replaces text in a file (args: {{"path": "file path", "old_text": "find", "new_text": "replace"}})
        41. read_file - reads a file (args: {{"path": "file path"}})
        42. create_folder - creates a folder (args: {{"path": "folder path"}})
        43. delete_file - deletes a file (args: {{"path": "file path"}})
        44. delete_folder - deletes a folder (args: {{"path": "folder path"}})
        45. move_file - moves a file (args: {{"src": "from path", "dest": "to path"}})
        46. copy_file - copies a file (args: {{"src": "from path", "dest": "to path"}})
        47. rename_file - renames a file (args: {{"path": "file path", "new_name": "new.ext"}})
        48. list_files - lists files in a folder (args: {{"path": "folder path"}})
        49. open_file - opens a file (args: {{"path": "file path"}})
        50. open_folder - opens a folder (args: {{"path": "folder path"}})
        51. find_files - finds files (args: {{"pattern": "*.txt", "path": "optional folder"}})
        52. download_image - downloads an image to Downloads (args: {{"url": "https://..."}})
        53. download_video - downloads a direct video file to Downloads (args: {{"url": "https://...mp4"}})
        54. get_system_info - detailed system info (no args)
        55. list_processes - lists processes (no args)
        56. kill_process - closes a process (args: {{"name": "chrome"}} or {{"pid": 1234}})
        57. list_drives - lists drives (no args)
        58. run_command - runs a shell command (args: {{"command": "dir"}})
        59. open_task_manager - opens task manager (no args)
        60. open_settings - opens Windows settings (no args)
        61. open_control_panel - opens control panel (no args)
        62. refresh_window - presses refresh/F5 (no args)
        63. refresh_desktop - shows and refreshes desktop (no args)
        64. switch_panel - switches app tabs (args: {{"panel": "face|chat|voice|dashboard"}})
        65. start_camera - starts camera (no args)
        66. stop_camera - stops camera (no args)
        67. start_voice_assistant - starts voice listening (no args)
        68. stop_voice_assistant - stops voice listening (no args)

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
