from fastapi import FastAPI
from pydantic import BaseModel
from groq import Groq
import os
import json
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class Message(BaseModel):
    text: str

@app.post("/process")
def process_message(message: Message):

    system_prompt = """
You are a system controller AI.

Available tools:
- open_browser
- open_notepad
- open_calculator
- shutdown_computer
- restart_computer
- lock_computer
- take_screenshot
- get_time
- get_date
- search_google
- open_youtube
- open_any_app
- minimize_windows
- volume_up
- volume_down
- mute_volume
- system_status
- type_text
- press_key
- move_mouse
- mouse_click
- switch_window
- read_clipboard

Return ONLY valid JSON.

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

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message.text}
        ],
        temperature=0
    )

    output = response.choices[0].message.content

    try:
        parsed = json.loads(output)
        return parsed
    except:
        return {
            "type": "chat",
            "response": output
        }