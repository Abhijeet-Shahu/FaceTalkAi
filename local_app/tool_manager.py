import glob
import os
import platform
import shutil
import subprocess
import ctypes
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime

import paperclip
import psutil
import pyautogui
import requests
import sounddevice as sd


class ToolManager:
    def __init__(
        self,
        switch_panel_callback=None,
        start_camera_callback=None,
        stop_camera_callback=None,
        stop_voice_callback=None,
        start_voice_callback=None,
        set_language_callback=None
    ):
        self.switch_panel_callback = switch_panel_callback
        self.start_camera_callback = start_camera_callback
        self.stop_camera_callback = stop_camera_callback
        self.stop_voice_callback = stop_voice_callback
        self.start_voice_callback = start_voice_callback
        self.set_language_callback = set_language_callback

        self.tools = {
            "open_browser": self.open_browser,
            "open_notepad": self.open_notepad,
            "open_calculator": self.open_calculator,
            "open_youtube": self.open_youtube,
            "open_website": self.open_website,
            "open_whatsapp": self.open_whatsapp,
            "open_instagram": self.open_instagram,
            "open_facebook": self.open_facebook,
            "open_any_app": self.open_any_app,
            "open_task_manager": self.open_task_manager,
            "open_settings": self.open_settings,
            "open_control_panel": self.open_control_panel,
            "open_word": self.open_word,
            "open_excel": self.open_excel,
            "open_powerpoint": self.open_powerpoint,
            "shutdown_computer": self.shutdown_computer,
            "restart_computer": self.restart_computer,
            "lock_computer": self.lock_computer,
            "take_screenshot": self.take_screenshot,
            "get_time": self.get_time,
            "get_date": self.get_date,
            "search_google": self.search_google,
            "minimize_windows": self.minimize_windows,
            "switch_window": self.switch_window,
            "activate_window": self.activate_window,
            "minimize_window": self.minimize_window,
            "maximize_window": self.maximize_window,
            "show_desktop": self.show_desktop,
            "refresh_window": self.refresh_window,
            "refresh_desktop": self.refresh_desktop,
            "volume_up": self.volume_up,
            "volume_down": self.volume_down,
            "mute_volume": self.mute_volume,
            "system_status": self.system_status,
            "get_system_info": self.get_system_info,
            "list_processes": self.list_processes,
            "kill_process": self.kill_process,
            "list_drives": self.list_drives,
            "run_command": self.run_command,
            "type_text": self.type_text,
            "type_secret": self.type_secret,
            "press_key": self.press_key,
            "move_mouse": self.move_mouse,
            "mouse_click": self.mouse_click,
            "scroll_page": self.scroll_page,
            "read_clipboard": self.read_clipboard,
            "write_file": self.write_file,
            "append_file": self.append_file,
            "replace_in_file": self.replace_in_file,
            "read_file": self.read_file,
            "create_folder": self.create_folder,
            "delete_file": self.delete_file,
            "delete_folder": self.delete_folder,
            "move_file": self.move_file,
            "copy_file": self.copy_file,
            "rename_file": self.rename_file,
            "list_files": self.list_files,
            "open_file": self.open_file,
            "open_folder": self.open_folder,
            "find_files": self.find_files,
            "download_image": self.download_image,
            "download_video": self.download_video,
            "set_environment_var": self.set_environment_var,
            "get_environment_var": self.get_environment_var,
            "switch_panel": self.switch_panel,
            "start_camera": self.start_camera_tool,
            "stop_camera": self.stop_camera_tool,
            "start_voice_assistant": self.start_voice_assistant_tool,
            "stop_voice_assistant": self.stop_voice_assistant_tool,
            "set_language": self.set_language_tool,
            "save_document": self.save_document,
            "save_document_as": self.save_document_as,
            "new_slide": self.new_slide,
            "duplicate_slide": self.duplicate_slide,
            "start_presentation": self.start_presentation,
            "next_slide": self.next_slide,
            "previous_slide": self.previous_slide,
            "end_presentation": self.end_presentation,
        }

    def execute(self, tool_name, args=None):
        tool = self.tools.get(tool_name)
        if tool:
            return tool(args or {})
        return f"Tool '{tool_name}' not found."

    def _normalize_path(self, path):
        if not path:
            return None
        return os.path.abspath(os.path.expanduser(str(path)))

    def _ensure_parent_dir(self, path):
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    def _downloads_dir(self):
        downloads = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(downloads, exist_ok=True)
        return downloads

    def _safe_filename_from_url(self, url, default_name):
        parsed = urllib.parse.urlparse(url)
        basename = os.path.basename(parsed.path or "")
        return basename or default_name

    def _run_subprocess(self, command, shell=False):
        result = subprocess.run(
            command,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=20
        )
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        return result.returncode, stdout, stderr

    def _list_windows_titles(self):
        if platform.system() != "Windows":
            return []

        user32 = ctypes.windll.user32
        titles = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def enum_proc(hwnd, lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value.strip()
            if title:
                titles.append(title)
            return True

        user32.EnumWindows(enum_proc, 0)
        return titles

    def _find_window_handle(self, title_fragment):
        if platform.system() != "Windows" or not title_fragment:
            return None

        user32 = ctypes.windll.user32
        matches = []
        fragment = str(title_fragment).lower()

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        def enum_proc(hwnd, lparam):
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd)
            if length == 0:
                return True
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buffer, length + 1)
            title = buffer.value.strip()
            if title and fragment in title.lower():
                matches.append((hwnd, title))
            return True

        user32.EnumWindows(enum_proc, 0)
        return matches[0] if matches else None

    def _show_window(self, title_fragment, mode):
        found = self._find_window_handle(title_fragment)
        if not found:
            return f"Window not found: {title_fragment}"

        hwnd, title = found
        user32 = ctypes.windll.user32
        show_map = {"min": 6, "max": 3, "restore": 9}

        if mode == "min":
            user32.ShowWindow(hwnd, show_map[mode])
            action = "Minimized"
        else:
            user32.ShowWindow(hwnd, 9)
            try:
                user32.BringWindowToTop(hwnd)
                user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
            if mode == "max":
                user32.ShowWindow(hwnd, show_map[mode])
                action = "Maximized"
            else:
                action = "Activated"

        if mode == "min":
            try:
                user32.SetForegroundWindow(hwnd)
            except Exception:
                pass
        return f"{action} window: {title}"

    def open_any_app(self, args):
        app_name = args.get("app", "")
        if not app_name:
            return "No application name provided."

        try:
            if platform.system() == "Windows":
                os.startfile(app_name)
            else:
                subprocess.Popen([app_name])
            return f"Opening {app_name}"
        except Exception:
            try:
                if platform.system() == "Windows":
                    subprocess.Popen(app_name, shell=True)
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

    def open_website(self, args=None):
        website = (args or {}).get("website") or (args or {}).get("url")
        if not website:
            return "Please provide a website or URL."

        website = str(website).strip()
        known_sites = {
            "whatsapp": "https://web.whatsapp.com",
            "instagram": "https://www.instagram.com",
            "facebook": "https://www.facebook.com",
            "youtube": "https://www.youtube.com",
            "gmail": "https://mail.google.com",
        }

        lowered = website.lower()
        url = known_sites.get(lowered, website)
        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        webbrowser.open(url)
        return f"Opening website: {url}"

    def open_whatsapp(self, args=None):
        webbrowser.open("https://web.whatsapp.com")
        return "Opening WhatsApp Web"

    def open_instagram(self, args=None):
        webbrowser.open("https://www.instagram.com")
        return "Opening Instagram"

    def open_facebook(self, args=None):
        webbrowser.open("https://www.facebook.com")
        return "Opening Facebook"

    def search_google(self, args=None):
        query = (args or {}).get("query")
        if query:
            webbrowser.open(f"https://www.google.com/search?q={query}")
            return f"Searching Google for: {query}"
        return "What would you like to search for?"

    def open_notepad(self, args=None):
        os.system("notepad")
        return "Opening Notepad."

    def open_calculator(self, args=None):
        os.system("calc")
        return "Opening Calculator."

    def open_task_manager(self, args=None):
        if platform.system() == "Windows":
            subprocess.Popen(["taskmgr"])
            return "Opening Task Manager."
        return "Task Manager shortcut is only configured for Windows."

    def open_settings(self, args=None):
        try:
            if platform.system() == "Windows":
                os.startfile("ms-settings:")
                return "Opening Windows Settings."
            return "System settings shortcut is only configured for Windows."
        except Exception as e:
            return f"Failed to open settings: {str(e)}"

    def open_control_panel(self, args=None):
        try:
            if platform.system() == "Windows":
                subprocess.Popen(["control"])
                return "Opening Control Panel."
            return "Control Panel shortcut is only configured for Windows."
        except Exception as e:
            return f"Failed to open Control Panel: {str(e)}"

    def open_word(self, args=None):
        for app in ["winword", "WINWORD.EXE"]:
            result = self.open_any_app({"app": app})
            if result.startswith("Opening"):
                return "Opening Microsoft Word."
        return "Failed to open Microsoft Word."

    def open_excel(self, args=None):
        for app in ["excel", "EXCEL.EXE"]:
            result = self.open_any_app({"app": app})
            if result.startswith("Opening"):
                return "Opening Microsoft Excel."
        return "Failed to open Microsoft Excel."

    def open_powerpoint(self, args=None):
        for app in ["powerpnt", "POWERPNT.EXE"]:
            result = self.open_any_app({"app": app})
            if result.startswith("Opening"):
                return "Opening Microsoft PowerPoint."
        return "Failed to open Microsoft PowerPoint."

    def take_screenshot(self, args=None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{timestamp}.png"
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        return f"Screenshot saved as {filename}"

    def get_time(self, args=None):
        return f"The current time is {datetime.now().strftime('%I:%M %p')}"

    def get_date(self, args=None):
        return f"Today's date is {datetime.now().strftime('%B %d, %Y')}"

    def lock_computer(self, args=None):
        if platform.system() == "Windows":
            os.system("rundll32.exe user32.dll,LockWorkStation")
        else:
            os.system("gnome-screensaver-command -l")
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
        try:
            pyautogui.hotkey("win", "d")
            return "Minimizing all windows."
        except Exception as e:
            return f"Failed to minimize all windows: {str(e)}"

    def switch_window(self, args=None):
        pyautogui.hotkey("alt", "tab")
        return "Switching windows."

    def activate_window(self, args=None):
        title = (args or {}).get("title") or (args or {}).get("window")
        if not title:
            return "Window title is required."
        return self._show_window(title, "restore")

    def minimize_window(self, args=None):
        title = (args or {}).get("title") or (args or {}).get("window")
        if not title:
            return "Window title is required."
        return self._show_window(title, "min")

    def maximize_window(self, args=None):
        title = (args or {}).get("title") or (args or {}).get("window")
        if not title:
            return "Window title is required."
        return self._show_window(title, "max")

    def diagnostic_report(self):
        """
        Non-destructive health check for tool availability.
        """
        report = {
            "tool_count": len(self.tools),
            "registered_tools": sorted(self.tools.keys()),
            "windows_titles_sample": self._list_windows_titles()[:12],
            "audio_inputs": [],
            "app_checks": {},
        }

        try:
            for device in sd.query_devices():
                if int(device.get("max_input_channels", 0) or 0) > 0:
                    report["audio_inputs"].append(str(device.get("name", "")))
        except Exception as e:
            report["audio_inputs_error"] = str(e)

        command_checks = {
            "notepad": ["where", "notepad"],
            "calc": ["where", "calc"],
            "taskmgr": ["where", "taskmgr"],
            "control": ["where", "control"],
        }
        for name, command in command_checks.items():
            try:
                returncode, stdout, stderr = self._run_subprocess(command)
                report["app_checks"][name] = {
                    "ok": returncode == 0,
                    "output": stdout or stderr,
                }
            except Exception as e:
                report["app_checks"][name] = {"ok": False, "output": str(e)}

        return report

    def show_desktop(self, args=None):
        pyautogui.hotkey("win", "d")
        return "Showing desktop."

    def refresh_window(self, args=None):
        pyautogui.press("f5")
        return "Refreshing the current window."

    def refresh_desktop(self, args=None):
        pyautogui.hotkey("win", "d")
        pyautogui.press("f5")
        return "Refreshing the desktop."

    def volume_up(self, args=None):
        steps = int((args or {}).get("steps", 5))
        for _ in range(max(1, min(50, steps))):
            pyautogui.press("volumeup")
        return "Volume increased."

    def volume_down(self, args=None):
        steps = int((args or {}).get("steps", 5))
        for _ in range(max(1, min(50, steps))):
            pyautogui.press("volumedown")
        return "Volume decreased."

    def mute_volume(self, args=None):
        pyautogui.press("volumemute")
        return "Volume muted."

    def system_status(self, args=None):
        cpu = psutil.cpu_percent(interval=1)
        ram = psutil.virtual_memory().percent
        disk = psutil.disk_usage(os.path.abspath(os.sep)).percent
        return f"CPU usage is {cpu} percent. RAM usage is {ram} percent. Disk usage is {disk} percent."

    def type_text(self, args=None):
        text = (args or {}).get("text")
        if not text:
            return "No text provided."
        pyautogui.write(str(text), interval=0.05)
        return f"Typing: {text}"

    def type_secret(self, args=None):
        secret = (args or {}).get("text") or (args or {}).get("secret") or (args or {}).get("password") or (args or {}).get("pin")
        if not secret:
            return "No secret text provided."

        pyautogui.write(str(secret), interval=0.04)
        return "Typed the secret value."

    def press_key(self, args=None):
        key = (args or {}).get("key")
        if not key:
            return "No key provided."
        pyautogui.press(str(key))
        return f"Pressed key: {key}"

    def move_mouse(self, args=None):
        x = (args or {}).get("x")
        y = (args or {}).get("y")
        if x is None or y is None:
            return "Invalid coordinates provided."
        pyautogui.moveTo(int(x), int(y), duration=0.5)
        return f"Moving mouse to ({x}, {y})"

    def mouse_click(self, args=None):
        click_type = (args or {}).get("click_type", "left")
        if click_type == "left":
            pyautogui.click()
        elif click_type == "right":
            pyautogui.rightClick()
        elif click_type == "double":
            pyautogui.doubleClick()
        else:
            return "Invalid click type provided."
        return f"Performed {click_type} mouse click."

    def scroll_page(self, args=None):
        amount = int((args or {}).get("amount", 700))
        direction = str((args or {}).get("direction", "down")).lower()
        if direction == "up":
            pyautogui.scroll(abs(amount))
            return "Scrolled up."
        pyautogui.scroll(-abs(amount))
        return "Scrolled down."

    def read_clipboard(self, args=None):
        return f"Clipboard content: {paperclip.paste()}"

    def switch_panel(self, args=None):
        if not self.switch_panel_callback:
            return "Panel switching is not available."

        panel = str((args or {}).get("panel", "")).strip().lower()
        aliases = {
            "face": "face",
            "face recognition": "face",
            "recognition": "face",
            "chat": "chat",
            "chatbot": "chat",
            "voice": "voice",
            "voice assistant": "voice",
            "assistant": "voice",
            "dashboard": "dashboard",
            "stats": "dashboard",
            "statistics": "dashboard",
        }

        target_panel = aliases.get(panel, panel)
        if target_panel not in {"face", "chat", "voice", "dashboard"}:
            return "Please specify panel: face, chat, voice, or dashboard."

        try:
            self.switch_panel_callback(target_panel)
            return f"Switched to {target_panel} panel."
        except Exception as e:
            return f"Failed to switch panel: {str(e)}"

    def start_camera_tool(self, args=None):
        if not self.start_camera_callback:
            return "Camera control is not available."
        try:
            self.start_camera_callback()
            return "Starting camera."
        except Exception as e:
            return f"Failed to start camera: {str(e)}"

    def stop_camera_tool(self, args=None):
        if not self.stop_camera_callback:
            return "Camera control is not available."
        try:
            self.stop_camera_callback()
            return "Stopping camera."
        except Exception as e:
            return f"Failed to stop camera: {str(e)}"

    def stop_voice_assistant_tool(self, args=None):
        if not self.stop_voice_callback:
            return "Voice assistant control is not available."
        try:
            self.stop_voice_callback()
            return "Stopping voice assistant."
        except Exception as e:
            return f"Failed to stop voice assistant: {str(e)}"

    def start_voice_assistant_tool(self, args=None):
        if not self.start_voice_callback:
            return "Voice assistant control is not available."
        try:
            self.start_voice_callback()
            return "Starting voice assistant."
        except Exception as e:
            return f"Failed to start voice assistant: {str(e)}"

    def set_language_tool(self, args=None):
        if not self.set_language_callback:
            return "Language switching is not available."

        language = str((args or {}).get("language", "")).strip().lower()
        if not language:
            return "Please specify a language like English or Hindi."

        try:
            return self.set_language_callback(language)
        except Exception as e:
            return f"Failed to switch language: {str(e)}"

    def save_document(self, args=None):
        pyautogui.hotkey("ctrl", "s")
        return "Saved the current document."

    def save_document_as(self, args=None):
        pyautogui.press("f12")
        return "Opened Save As."

    def new_slide(self, args=None):
        pyautogui.hotkey("ctrl", "m")
        return "Inserted a new slide."

    def duplicate_slide(self, args=None):
        pyautogui.hotkey("ctrl", "d")
        return "Duplicated the current slide or selection."

    def start_presentation(self, args=None):
        from_beginning = bool((args or {}).get("from_beginning", True))
        if from_beginning:
            pyautogui.press("f5")
            return "Started the presentation from the beginning."
        pyautogui.hotkey("shift", "f5")
        return "Started the presentation from the current slide."

    def next_slide(self, args=None):
        pyautogui.press("right")
        return "Moved to the next slide."

    def previous_slide(self, args=None):
        pyautogui.press("left")
        return "Moved to the previous slide."

    def end_presentation(self, args=None):
        pyautogui.press("esc")
        return "Ended the presentation."

    def write_file(self, args=None):
        file_path = self._normalize_path((args or {}).get("path") or (args or {}).get("file_path"))
        content = (args or {}).get("content") or (args or {}).get("text")
        if not file_path or content is None:
            return "File path and content are required."

        try:
            self._ensure_parent_dir(file_path)
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(str(content))
            return f"Successfully wrote to {os.path.basename(file_path)}"
        except Exception as e:
            return f"Failed to write file: {str(e)}"

    def append_file(self, args=None):
        file_path = self._normalize_path((args or {}).get("path") or (args or {}).get("file_path"))
        content = (args or {}).get("content") or (args or {}).get("text")
        if not file_path or content is None:
            return "File path and content are required."

        try:
            self._ensure_parent_dir(file_path)
            with open(file_path, "a", encoding="utf-8") as file:
                file.write(str(content))
                if not str(content).endswith("\n"):
                    file.write("\n")
            return f"Successfully appended to {os.path.basename(file_path)}"
        except Exception as e:
            return f"Failed to append to file: {str(e)}"

    def replace_in_file(self, args=None):
        file_path = self._normalize_path((args or {}).get("path") or (args or {}).get("file_path"))
        old_text = (args or {}).get("old_text") or (args or {}).get("find")
        new_text = (args or {}).get("new_text") or (args or {}).get("replace")
        if not file_path or old_text is None or new_text is None:
            return "Path, old_text, and new_text are required."

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()

            if str(old_text) not in content:
                return "Text to replace was not found."

            updated = content.replace(str(old_text), str(new_text))
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(updated)
            return f"Updated text in {os.path.basename(file_path)}"
        except Exception as e:
            return f"Failed to edit file: {str(e)}"

    def read_file(self, args=None):
        file_path = self._normalize_path((args or {}).get("path") or (args or {}).get("file_path"))
        if not file_path:
            return "No file path provided."

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            if len(content) > 1000:
                return f"File content (first 1000 chars): {content[:1000]}..."
            return f"File content: {content}"
        except FileNotFoundError:
            return f"File not found: {file_path}"
        except Exception as e:
            return f"Failed to read file: {str(e)}"

    def create_folder(self, args=None):
        folder_path = self._normalize_path((args or {}).get("path") or (args or {}).get("folder_path") or (args or {}).get("directory"))
        if not folder_path:
            return "No folder path provided."

        try:
            os.makedirs(folder_path, exist_ok=True)
            return f"Successfully created folder: {os.path.basename(folder_path)}"
        except Exception as e:
            return f"Failed to create folder: {str(e)}"

    def delete_file(self, args=None):
        file_path = self._normalize_path((args or {}).get("path") or (args or {}).get("file_path"))
        if not file_path:
            return "No file path provided."

        try:
            if not os.path.exists(file_path):
                return f"File not found: {file_path}"
            os.remove(file_path)
            return f"Successfully deleted {os.path.basename(file_path)}"
        except Exception as e:
            return f"Failed to delete file: {str(e)}"

    def delete_folder(self, args=None):
        folder_path = self._normalize_path((args or {}).get("path") or (args or {}).get("folder_path") or (args or {}).get("directory"))
        if not folder_path:
            return "No folder path provided."

        try:
            if not os.path.exists(folder_path):
                return f"Folder not found: {folder_path}"
            shutil.rmtree(folder_path)
            return f"Successfully deleted folder: {os.path.basename(folder_path)}"
        except Exception as e:
            return f"Failed to delete folder: {str(e)}"

    def move_file(self, args=None):
        src = self._normalize_path((args or {}).get("src") or (args or {}).get("source") or (args or {}).get("from"))
        dest = self._normalize_path((args or {}).get("dest") or (args or {}).get("destination") or (args or {}).get("to"))
        if not src or not dest:
            return "Source and destination paths are required."

        try:
            if not os.path.exists(src):
                return f"File not found: {src}"
            self._ensure_parent_dir(dest)
            shutil.move(src, dest)
            return f"Successfully moved {os.path.basename(src)} to {dest}"
        except Exception as e:
            return f"Failed to move file: {str(e)}"

    def copy_file(self, args=None):
        src = self._normalize_path((args or {}).get("src") or (args or {}).get("source") or (args or {}).get("from"))
        dest = self._normalize_path((args or {}).get("dest") or (args or {}).get("destination") or (args or {}).get("to"))
        if not src or not dest:
            return "Source and destination paths are required."

        try:
            if not os.path.exists(src):
                return f"File not found: {src}"
            self._ensure_parent_dir(dest)
            shutil.copy2(src, dest)
            return f"Successfully copied {os.path.basename(src)} to {dest}"
        except Exception as e:
            return f"Failed to copy file: {str(e)}"

    def rename_file(self, args=None):
        src = self._normalize_path((args or {}).get("src") or (args or {}).get("source") or (args or {}).get("path"))
        new_name = (args or {}).get("new_name") or (args or {}).get("name")
        if not src or not new_name:
            return "Path and new_name are required."

        try:
            if not os.path.exists(src):
                return f"File not found: {src}"
            dest = os.path.join(os.path.dirname(src), str(new_name))
            os.rename(src, dest)
            return f"Renamed to {os.path.basename(dest)}"
        except Exception as e:
            return f"Failed to rename file: {str(e)}"

    def list_files(self, args=None):
        folder_path = self._normalize_path((args or {}).get("path") or (args or {}).get("folder_path") or (args or {}).get("directory") or ".")
        try:
            if not os.path.exists(folder_path):
                return f"Folder not found: {folder_path}"

            items = os.listdir(folder_path)
            files = [item for item in items if os.path.isfile(os.path.join(folder_path, item))]
            folders = [item for item in items if os.path.isdir(os.path.join(folder_path, item))]

            result = [f"Contents of {folder_path}:"]
            if folders:
                result.append("Folders: " + ", ".join(folders[:10]))
            if files:
                result.append("Files: " + ", ".join(files[:10]))
            if not folders and not files:
                result.append("Folder is empty.")
            return "\n".join(result)
        except Exception as e:
            return f"Failed to list files: {str(e)}"

    def open_file(self, args=None):
        file_path = self._normalize_path((args or {}).get("path") or (args or {}).get("file_path"))
        if not file_path:
            return "No file path provided."

        try:
            if not os.path.exists(file_path):
                return f"File not found: {file_path}"

            if platform.system() == "Windows":
                os.startfile(file_path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", file_path])
            else:
                subprocess.Popen(["xdg-open", file_path])
            return f"Opening {os.path.basename(file_path)}..."
        except Exception as e:
            return f"Failed to open file: {str(e)}"

    def find_files(self, args=None):
        pattern = (args or {}).get("pattern") or (args or {}).get("search")
        search_path = self._normalize_path((args or {}).get("path") or ".")
        if not pattern:
            return "Search pattern is required."

        try:
            full_pattern = os.path.join(search_path, "**", str(pattern))
            files = glob.glob(full_pattern, recursive=True)
            if not files:
                return f"No files found matching: {pattern}"

            lines = [f"Found {len(files)} file(s) matching {pattern}:"]
            for file in files[:10]:
                lines.append(file)
            if len(files) > 10:
                lines.append(f"... and {len(files) - 10} more")
            return "\n".join(lines)
        except Exception as e:
            return f"Failed to search for files: {str(e)}"

    def download_image(self, args=None):
        url = (args or {}).get("url")
        filename = (args or {}).get("filename")
        if not url:
            return "Image URL is required."

        try:
            target_name = filename or self._safe_filename_from_url(url, "downloaded_image.jpg")
            target_path = os.path.join(self._downloads_dir(), target_name)
            urllib.request.urlretrieve(url, target_path)
            return f"Image downloaded to {target_path}"
        except Exception as e:
            return f"Failed to download image: {str(e)}"

    def download_video(self, args=None):
        url = (args or {}).get("url")
        filename = (args or {}).get("filename")
        if not url:
            return "Video URL is required."

        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            target_name = filename or self._safe_filename_from_url(url, "downloaded_video.mp4")
            target_path = os.path.join(self._downloads_dir(), target_name)

            with open(target_path, "wb") as file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        file.write(chunk)

            return f"Video downloaded to {target_path}"
        except Exception as e:
            return f"Failed to download video: {str(e)}"

    def get_system_info(self, args=None):
        try:
            info = [
                "System Information:",
                f"OS: {platform.system()} {platform.release()}",
                f"Python: {platform.python_version()}",
                f"Processor: {platform.processor()}",
                f"CPU Cores: {psutil.cpu_count()}",
                f"CPU Usage: {psutil.cpu_percent(interval=1)}%",
                f"RAM Total: {psutil.virtual_memory().total / (1024**3):.2f} GB",
                f"RAM Used: {psutil.virtual_memory().used / (1024**3):.2f} GB",
                f"Disk Usage: {psutil.disk_usage(os.path.abspath(os.sep)).percent}%",
            ]
            return "\n".join(info)
        except Exception as e:
            return f"Failed to get system info: {str(e)}"

    def list_processes(self, args=None):
        try:
            processes = []
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    processes.append(f"{proc.info['name']} (PID: {proc.info['pid']})")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            lines = ["Running processes (top 20):"]
            lines.extend(processes[:20])
            if len(processes) > 20:
                lines.append(f"... and {len(processes) - 20} more")
            return "\n".join(lines)
        except Exception as e:
            return f"Failed to list processes: {str(e)}"

    def kill_process(self, args=None):
        process_name = (args or {}).get("name") or (args or {}).get("process")
        process_pid = (args or {}).get("pid")

        try:
            if process_pid:
                proc = psutil.Process(int(process_pid))
                proc_name = proc.name()
                proc.kill()
                return f"Successfully killed process: {proc_name} (PID: {process_pid})"

            if process_name:
                killed = False
                for proc in psutil.process_iter(["pid", "name"]):
                    try:
                        if process_name.lower() in proc.info["name"].lower():
                            proc.kill()
                            killed = True
                    except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError):
                        continue
                return f"Successfully killed process: {process_name}" if killed else f"Process not found: {process_name}"

            return "Process name or PID is required."
        except Exception as e:
            return f"Failed to kill process: {str(e)}"

    def list_drives(self, args=None):
        try:
            if platform.system() != "Windows":
                return "Drive listing is only configured for Windows."

            drives = []
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                drive = f"{letter}:\\"
                if os.path.exists(drive):
                    drives.append(drive)
            return "Available drives: " + ", ".join(drives) if drives else "No drives found."
        except Exception as e:
            return f"Failed to list drives: {str(e)}"

    def run_command(self, args=None):
        command = (args or {}).get("command")
        if not command:
            return "No command provided."

        blocked_terms = ["format ", "rd /s", "del /f", "cipher /w", "bcdedit", "reg delete", "diskpart"]
        lowered = str(command).lower()
        if any(term in lowered for term in blocked_terms):
            return "That command is blocked for safety."

        try:
            returncode, stdout, stderr = self._run_subprocess(str(command), shell=True)
            output = stdout or stderr or "Command completed."
            output = output[:1500]
            if returncode == 0:
                return f"Command completed successfully:\n{output}"
            return f"Command failed with code {returncode}:\n{output}"
        except Exception as e:
            return f"Failed to run command: {str(e)}"

    def set_environment_var(self, args=None):
        var_name = (args or {}).get("name") or (args or {}).get("var")
        var_value = (args or {}).get("value")
        if not var_name or var_value is None:
            return "Variable name and value are required."

        try:
            os.environ[str(var_name)] = str(var_value)
            return f"Successfully set {var_name} = {var_value}"
        except Exception as e:
            return f"Failed to set environment variable: {str(e)}"

    def get_environment_var(self, args=None):
        var_name = (args or {}).get("name") or (args or {}).get("var")
        if not var_name:
            return "No variable name provided."

        try:
            return f"{var_name} = {os.getenv(str(var_name), 'Not found')}"
        except Exception as e:
            return f"Failed to get environment variable: {str(e)}"

    def open_folder(self, args=None):
        folder_path = self._normalize_path((args or {}).get("path") or (args or {}).get("folder_path") or (args or {}).get("directory") or ".")
        try:
            if not os.path.isdir(folder_path):
                return f"Folder not found: {folder_path}"

            if platform.system() == "Windows":
                os.startfile(folder_path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", folder_path])
            else:
                subprocess.Popen(["xdg-open", folder_path])
            return f"Opening folder: {folder_path}"
        except Exception as e:
            return f"Failed to open folder: {str(e)}"
