from fastapi import FastAPI
from pydantic import BaseModel
from groq import Groq
import os
import json
from dotenv import load_dotenv
from typing import List, Optional, Dict, Any
import concurrent.futures as cf

load_dotenv()

app = FastAPI()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

class Message(BaseModel):
    text: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    history: Optional[List[Dict[str, Any]]] = None
    language: Optional[str] = "english"


@app.get("/health")
def health():
    return {
        "ok": True,
        "groq_key_configured": bool(os.getenv("GROQ_API_KEY"))
    }


def quick_route_tool(text: str):
    t = (text or "").lower()

    if "stop voice" in t or "stop listening" in t or "turn off voice" in t:
        return {"type": "tool", "tool": "stop_voice_assistant", "args": {}}
    if "start voice" in t or "start listening" in t or "turn on voice" in t:
        return {"type": "tool", "tool": "start_voice_assistant", "args": {}}
    if "start camera" in t or "open camera" in t:
        return {"type": "tool", "tool": "start_camera", "args": {}}
    if "stop camera" in t or "close camera" in t:
        return {"type": "tool", "tool": "stop_camera", "args": {}}
    if "open browser" in t:
        return {"type": "tool", "tool": "open_browser", "args": {}}
    if "open youtube" in t:
        return {"type": "tool", "tool": "open_youtube", "args": {}}
    if "open whatsapp" in t:
        return {"type": "tool", "tool": "open_whatsapp", "args": {}}
    if "open instagram" in t:
        return {"type": "tool", "tool": "open_instagram", "args": {}}
    if "open facebook" in t:
        return {"type": "tool", "tool": "open_facebook", "args": {}}
    if "what time" in t or "time now" in t:
        return {"type": "tool", "tool": "get_time", "args": {}}
    if "what date" in t or "today date" in t:
        return {"type": "tool", "tool": "get_date", "args": {}}
    if "switch language to hindi" in t or "change language to hindi" in t:
        return {"type": "tool", "tool": "set_language", "args": {"language": "hindi"}}
    if "switch language to english" in t or "change language to english" in t:
        return {"type": "tool", "tool": "set_language", "args": {"language": "english"}}

    panel_map = {
        "face": ["face panel", "face tab", "face recognition"],
        "chat": ["chat panel", "chat tab", "chatbot"],
        "voice": ["voice panel", "voice tab", "assistant panel"],
        "dashboard": ["dashboard panel", "dashboard tab", "stats panel"],
    }
    for panel, phrases in panel_map.items():
        if any(p in t for p in phrases):
            return {"type": "tool", "tool": "switch_panel", "args": {"panel": panel}}

    return None

@app.post("/process")
def process_message(message: Message):
    quick = quick_route_tool(message.text)
    if quick:
        return quick

    system_prompt = """
You are FaceTalk AI, an assistant that can both chat naturally and control the local app/tools.

Available tools:
- open_browser
- open_notepad
- open_calculator
- open_task_manager
- open_settings
- open_control_panel
- shutdown_computer
- restart_computer
- lock_computer
- take_screenshot
- get_time
- get_date
- search_google
- open_youtube
- open_website
- open_whatsapp
- open_instagram
- open_facebook
- open_any_app
- open_word
- open_excel
- open_powerpoint
- minimize_windows
- activate_window
- minimize_window
- maximize_window
- volume_up
- volume_down
- mute_volume
- show_desktop
- refresh_window
- refresh_desktop
- system_status
- get_system_info
- list_processes
- kill_process
- list_drives
- run_command
- type_text
- type_secret
- save_document
- save_document_as
- new_slide
- duplicate_slide
- start_presentation
- next_slide
- previous_slide
- end_presentation
- press_key
- move_mouse
- mouse_click
- scroll_page
- switch_window
- read_clipboard
- write_file
- append_file
- replace_in_file
- read_file
- create_folder
- delete_file
- delete_folder
- move_file
- copy_file
- rename_file
- list_files
- open_file
- open_folder
- find_files
- download_image
- download_video
- switch_panel (args: {"panel": "face|chat|voice|dashboard"})
- start_camera
- stop_camera
- start_voice_assistant
- stop_voice_assistant
- set_language (args: {"language": "english|hindi"})

Return ONLY valid JSON.

Rules:
- If the user is asking to control the app, system, tabs, camera, or voice state, return a tool response.
- If the user is asking for explanation, help, guidance, brainstorming, troubleshooting, or learning, return a chat response.
- In chat mode, respond like a capable AI agent: clear, helpful, and able to give detailed answers when useful.
- Default to a basic to mid-level answer: useful, clear, and not too long.
- Give a detailed answer only if the user asks for detail, deep explanation, full steps, comprehensive information, or advanced guidance.
- Keep answers natural and readable for chat and voice, but prioritize usefulness over extreme brevity.
- Never wrap the JSON in markdown.
- Always reply in the currently selected assistant language.

If user asks to change tab/panel/screen in the app, use `switch_panel`.
If user asks to open/start camera, use `start_camera`.
If user asks to close/stop camera, use `stop_camera`.
If user asks to start voice assistant/listening, use `start_voice_assistant`.
If user asks to stop/turn off voice assistant/listening, use `stop_voice_assistant`.
If user asks to switch the assistant language, use `set_language`.

If command is tool:
{
  "type": "tool",
  "tool": "tool_name",
  "args": {}
}

If normal chat:
{
  "type": "chat",
  "response": "your reply"
}
"""

    memory_context = ""
    if message.history:
        memory_lines = []
        for item in message.history[-4:]:
            user_msg = str(item.get("message", ""))[:180]
            ai_msg = str(item.get("response", ""))[:220]
            memory_lines.append(f"User: {user_msg}\nAssistant: {ai_msg}")
        memory_context = "\n\nRecent memory:\n" + "\n---\n".join(memory_lines)

    user_context = f"\nCurrent user: {message.user_name}" if message.user_name else ""
    selected_language = (message.language or "english").strip().lower()
    if selected_language not in {"english", "hindi"}:
        selected_language = "english"
    language_context = f"\nCurrent assistant language: {selected_language}. Respond in {selected_language}."

    if not os.getenv("GROQ_API_KEY"):
        return {
            "type": "chat",
            "response": "GROQ_API_KEY is missing on AI server."
        }

    def run_groq():
        return client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt + user_context + language_context + memory_context},
                {"role": "user", "content": message.text}
            ],
            temperature=0.2,
            max_tokens=700
        )

    try:
        with cf.ThreadPoolExecutor(max_workers=1) as executor:
            response = executor.submit(run_groq).result(timeout=12)
    except cf.TimeoutError:
        return {
            "type": "chat",
            "response": "I am facing a temporary AI delay. Please try again."
        }
    except Exception as e:
        return {
            "type": "chat",
            "response": f"AI server error: {str(e)}"
        }

    output = response.choices[0].message.content

    try:
        parsed = json.loads(output)
        return parsed
    except:
        return {
            "type": "chat",
            "response": output
        }
