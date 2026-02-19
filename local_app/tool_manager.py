# tool_manager.py
import os
import webbrowser
import subprocess
import pyautogui
from datetime import datetime
import platform

class ToolManager:

    def __init__(self):
        self.tools = {
            "open_browser": self.open_browser,
            "open_notepad": self.open_notepad,
            "open_calculator": self.open_calculator,
            "shutdown_computer": self.shutdown_computer,
            "restart_computer": self.restart_computer,
            "lock_computer": self.lock_computer,
            "take_screenshot": self.take_screenshot,
            "get_time": self.get_time,
            "get_date": self.get_date,
            "search_google": self.search_google,
            "open_youtube": self.open_youtube,
            "open_any_app": self.open_any_app,
            "minimize_windows": self.minimize_windows,
            "volume_up": self.volume_up,
            "volume_down": self.volume_down,
            "mute_volume": self.mute_volume
        }

    def execute(self, tool_name, args=None):
        tool = self.tools.get(tool_name)
        if tool:
            return tool(args)
        return f"Tool '{tool_name}' not found."

    def open_any_app(self, args):
        if not args:
            return "No application specified."

        app_name = args.get("app", "")
        if not app_name:
            return "No application name provided."

        try:
            if platform.system() == "Windows":
                os.system(f"start {app_name}")
            else:
                subprocess.Popen([app_name])
            return f"Opening {app_name}"
        except Exception as e:
            return f"Failed to open application: {str(e)}"
        
    def open_browser(self, args=None):
        url = "https://www.google.com"
        if args and args.get("url"):
            url = args.get("url")
        webbrowser.open(url)
        return f"Opening browser at {url}"

    def open_youtube(self, args=None):
        webbrowser.open("https://youtube.com")
        return "Opening YouTube"

    def search_google(self, args=None):
        if args and args.get("query"):
            query = args.get("query")
            webbrowser.open(f"https://www.google.com/search?q={query}")
            return f"Searching Google for: {query}"
        return "What would you like to search for?"

    def open_notepad(self, args=None):
        os.system("notepad")
        return "Opening Notepad."
    
    def open_calculator(self, args=None):
        os.system("calc")
        return "Opening Calculator."
    
    def take_screenshot(self, args=None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        return f"Screenshot saved as {filename}"

    def get_time(self, args=None):
        current_time = datetime.now().strftime('%I:%M %p')
        return f"The current time is {current_time}"

    def get_date(self, args=None):
        current_date = datetime.now().strftime('%B %d, %Y')
        return f"Today's date is {current_date}"
    
    def lock_computer(self, args=None):
        if platform.system() == "Windows":
            os.system("rundll32.exe user32.dll,LockWorkStation")
        else:
            os.system("gnome-screensaver-command -l")  # Linux
        return "Locking computer."
    
    def shutdown_computer(self, args=None):
        if platform.system() == "Windows":
            os.system("shutdown /s /t 5")
        else:
            os.system("shutdown -h now")
        return "Shutting down computer in 5 seconds."
    
    def restart_computer(self, args=None):
        if platform.system() == "Windows":
            os.system("shutdown /r /t 5")
        else:
            os.system("shutdown -r now")
        return "Restarting computer in 5 seconds."
    
    def minimize_windows(self, args=None):
        if platform.system() == "Windows":
            pyautogui.hotkey('win', 'd')
        return "Minimizing all windows."
    
    def volume_up(self, args=None):
        if platform.system() == "Windows":
            for _ in range(5):
                pyautogui.press('volumeup')
        return "Volume increased."
    
    def volume_down(self, args=None):
        if platform.system() == "Windows":
            for _ in range(5):
                pyautogui.press('volumedown')
        return "Volume decreased."
    
    def mute_volume(self, args=None):
        if platform.system() == "Windows":
            pyautogui.press('volumemute')
        return "Volume muted."