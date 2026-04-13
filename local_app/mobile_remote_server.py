"""
Mobile Remote Control Server for FaceTalkAI.
"""

import cgi
import json
import re
import socket
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

MOBILE_WEB_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>FaceTalk AI Remote</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #fff;
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 420px; margin: 0 auto; }
        h1 {
            text-align: center;
            font-size: 24px;
            margin-bottom: 20px;
            color: #00d9ff;
        }
        .status {
            background: rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 20px;
            text-align: center;
            border: 2px solid #00ff88;
        }
        .status-line {
            font-size: 12px;
            margin-top: 5px;
            color: rgba(255,255,255,0.78);
        }
        .command-input {
            width: 100%;
            padding: 15px;
            font-size: 16px;
            border: none;
            border-radius: 12px;
            background: rgba(255,255,255,0.15);
            color: #fff;
            margin-bottom: 15px;
        }
        .command-input::placeholder { color: rgba(255,255,255,0.5); }
        .btn {
            width: 100%;
            padding: 15px;
            font-size: 16px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            margin-bottom: 10px;
            transition: transform 0.1s, opacity 0.1s;
        }
        .btn:active { transform: scale(0.98); opacity: 0.8; }
        .btn-primary { background: #00d9ff; color: #000; font-weight: bold; }
        .btn-voice { background: #ff4757; color: #fff; }
        .btn-voice.listening { background: #2ed573; animation: pulse 1s infinite; }
        .button-row {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        .panel-buttons {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-top: 15px;
        }
        .panel-btn, .quick-btn {
            padding: 14px 8px;
            font-size: 12px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.25);
            border-radius: 10px;
            color: #fff;
        }
        .quick-commands {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-top: 20px;
        }
        .response-box {
            background: rgba(0,0,0,0.3);
            border-radius: 12px;
            padding: 15px;
            margin-top: 20px;
            min-height: 120px;
            max-height: 260px;
            overflow-y: auto;
        }
        .response-item {
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .response-item:last-child { border-bottom: none; }
        .response-time { font-size: 12px; color: #888; }
    </style>
</head>
<body>
    <div class="container">
        <h1>FaceTalk AI Remote</h1>

        <div class="status" id="status">
            <strong>Connected to Desktop</strong>
            <div class="status-line" id="ip-display"></div>
            <div class="status-line" id="voice-state">Desktop voice: checking...</div>
            <div class="status-line" id="camera-state">Camera: checking...</div>
            <div class="status-line" id="mobile-mic-state">Mobile mic: checking...</div>
            <div class="status-line" id="desktop-audio-state">Desktop audio: checking...</div>
        </div>

        <input type="text" class="command-input" id="commandInput" placeholder="Type a command or chat..." autocomplete="off">
        <input type="file" id="audioFileInput" accept="audio/*" capture style="display:none">
        <button class="btn btn-primary" onclick="sendCommand()">Send</button>

        <div class="button-row">
            <button class="btn btn-voice" id="mobileVoiceStartBtn" onclick="startMobileVoice()">Start Mobile Mic</button>
            <button class="btn btn-voice" id="mobileVoiceStopBtn" onclick="stopMobileVoice()">Stop Mobile Mic</button>
        </div>

        <div class="button-row">
            <button class="btn btn-primary" onclick="controlDesktopVoice('start')">Start Desktop Voice</button>
            <button class="btn btn-primary" onclick="controlDesktopVoice('stop')">Stop Desktop Voice</button>
        </div>

        <div class="panel-buttons">
            <button class="panel-btn" onclick="switchPanel('face')">Face</button>
            <button class="panel-btn" onclick="switchPanel('chat')">Chat</button>
            <button class="panel-btn" onclick="switchPanel('voice')">Voice</button>
            <button class="panel-btn" onclick="switchPanel('dashboard')">Dashboard</button>
        </div>

        <div class="quick-commands">
            <button class="quick-btn" onclick="quickCmd('open browser')">Browser</button>
            <button class="quick-btn" onclick="quickCmd('take screenshot')">Screenshot</button>
            <button class="quick-btn" onclick="quickCmd('open word')">Word</button>
            <button class="quick-btn" onclick="quickCmd('open excel')">Excel</button>
            <button class="quick-btn" onclick="quickCmd('open powerpoint')">PowerPoint</button>
            <button class="quick-btn" onclick="quickCmd('start presentation')">Present</button>
            <button class="quick-btn" onclick="quickCmd('next slide')">Next Slide</button>
            <button class="quick-btn" onclick="quickCmd('minimize FaceTalk')">Min FaceTalk</button>
        </div>

        <div class="response-box" id="responses">
            <div class="response-item">
                <div>Ready to receive commands...</div>
                <div class="response-time">Just now</div>
            </div>
        </div>
    </div>

    <script>
        let mediaRecorder = null;
        let mediaStream = null;
        let recordedChunks = [];
        let isListening = false;

        document.getElementById('ip-display').textContent = 'Server: ' + window.location.host;
        document.getElementById('audioFileInput').addEventListener('change', async function(event) {
            const file = event.target.files && event.target.files[0];
            if (!file) return;
            await setMobileMicState(true);
            await uploadMobileAudio(file);
            await setMobileMicState(false);
            event.target.value = '';
            refreshStatus();
        });

        async function sendCommand(cmd) {
            const command = cmd || document.getElementById('commandInput').value.trim();
            if (!command) return;

            document.getElementById('commandInput').value = '';
            addResponse('You: ' + command);

            try {
                const response = await fetch('/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command })
                });
                const data = await response.json();
                addResponse('Jarvis: ' + (data.response || data.message || 'Done'));
                refreshStatus();
            } catch (err) {
                addResponse('Error: Could not reach desktop');
            }
        }

        function quickCmd(cmd) { sendCommand(cmd); }
        function switchPanel(panel) { sendCommand('switch to ' + panel + ' panel'); }

        function addResponse(text) {
            const box = document.getElementById('responses');
            const time = new Date().toLocaleTimeString();
            const item = document.createElement('div');
            item.className = 'response-item';
            item.innerHTML = '<div>' + text + '</div><div class="response-time">' + time + '</div>';
            box.insertBefore(item, box.firstChild);
            if (box.children.length > 12) box.removeChild(box.lastChild);
        }

        async function setMobileMicState(active) {
            await fetch('/mobile-mic-state', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ active })
            });
        }

        async function controlDesktopVoice(action) {
            try {
                const response = await fetch('/desktop-voice', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action })
                });
                const data = await response.json();
                addResponse('Jarvis: ' + (data.response || 'Done'));
                refreshStatus();
            } catch (err) {
                addResponse('Error: Could not control desktop voice.');
            }
        }

        async function startMobileVoice() {
            if (isListening) return;

            const prefersNativeCapture = !window.isSecureContext;
            if (prefersNativeCapture) {
                addResponse('Opening phone voice capture...');
                document.getElementById('audioFileInput').click();
                return;
            }

            if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia || !window.MediaRecorder) {
                addResponse('Live mobile mic is unavailable here. Opening phone audio capture instead.');
                document.getElementById('audioFileInput').click();
                return;
            }

            try {
                mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
                recordedChunks = [];
                mediaRecorder = new MediaRecorder(mediaStream);

                mediaRecorder.ondataavailable = function(event) {
                    if (event.data && event.data.size > 0) {
                        recordedChunks.push(event.data);
                    }
                };

                mediaRecorder.onstop = async function() {
                    const blob = new Blob(recordedChunks, { type: mediaRecorder.mimeType || 'audio/webm' });
                    await uploadMobileAudio(blob);
                    recordedChunks = [];
                    if (mediaStream) {
                        mediaStream.getTracks().forEach(track => track.stop());
                        mediaStream = null;
                    }
                    isListening = false;
                    document.getElementById('mobileVoiceStartBtn').classList.remove('listening');
                    document.getElementById('mobileVoiceStartBtn').textContent = 'Start Mobile Mic';
                    await setMobileMicState(false);
                    refreshStatus();
                };

                await setMobileMicState(true);
                mediaRecorder.start();
                isListening = true;
                document.getElementById('mobileVoiceStartBtn').classList.add('listening');
                document.getElementById('mobileVoiceStartBtn').textContent = 'Recording...';
                addResponse('Mobile mic started. Speak, then tap Stop Mobile Mic.');
                refreshStatus();
            } catch (err) {
                addResponse('Live mobile mic failed. Opening phone audio capture instead.');
                document.getElementById('audioFileInput').click();
                try { await setMobileMicState(false); } catch (e) {}
            }
        }

        function stopMobileVoice() {
            if (mediaRecorder && isListening) {
                mediaRecorder.stop();
            }
        }

        async function uploadMobileAudio(blob) {
            const formData = new FormData();
            const filename = blob.name || (blob.type && blob.type.includes('mp4') ? 'mobile_voice.mp4' : 'mobile_voice.webm');
            formData.append('audio', blob, filename);
            addResponse('Uploading mobile voice...');

            try {
                const response = await fetch('/mobile-audio', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                if (data.transcript) {
                    addResponse('You (Mobile Voice): ' + data.transcript);
                }
                addResponse('Jarvis: ' + (data.response || 'Done'));
            } catch (err) {
                addResponse('Error: Mobile audio upload failed.');
            }
        }

        async function refreshStatus() {
            try {
                const response = await fetch('/status');
                const data = await response.json();
                if (data.mobile_url) {
                    document.getElementById('ip-display').textContent = 'Server: ' + data.mobile_url;
                }
                document.getElementById('voice-state').textContent = 'Desktop voice: ' + (data.voice_running ? 'running' : 'stopped');
                document.getElementById('camera-state').textContent = 'Camera: ' + (data.camera_running ? 'running' : 'stopped');
                document.getElementById('mobile-mic-state').textContent = 'Mobile mic: ' + (data.mobile_mic_active ? 'active' : 'inactive');
                document.getElementById('desktop-audio-state').textContent = 'Desktop audio: ' + (data.desktop_audio_device || 'unknown');
            } catch (err) {
                document.getElementById('voice-state').textContent = 'Desktop voice: unavailable';
                document.getElementById('camera-state').textContent = 'Camera: unavailable';
                document.getElementById('mobile-mic-state').textContent = 'Mobile mic: unavailable';
                document.getElementById('desktop-audio-state').textContent = 'Desktop audio: unavailable';
            }
        }

        document.getElementById('commandInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendCommand();
        });

        refreshStatus();
        setInterval(refreshStatus, 3000);
    </script>
</body>
</html>
"""


class MobileRemoteHandler(BaseHTTPRequestHandler):
    tool_manager = None
    command_callback = None
    status_callback = None
    audio_callback = None
    mobile_mic_callback = None

    def log_message(self, format, *args):
        pass

    def _set_headers(self, content_type="text/html", status=200):
        self.send_response(status)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path in {"/", "/index.html"}:
            self._set_headers("text/html")
            self.wfile.write(MOBILE_WEB_PAGE.encode())
            return

        if parsed_path.path == "/status":
            self._set_headers("application/json")
            response = {
                "status": "online",
                "app": "FaceTalk AI",
                "timestamp": datetime.now().isoformat()
            }
            if MobileRemoteHandler.status_callback:
                try:
                    response.update(MobileRemoteHandler.status_callback() or {})
                except Exception as e:
                    response["status_error"] = str(e)
            self.wfile.write(json.dumps(response).encode())
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        parsed_path = urlparse(self.path)

        if parsed_path.path == "/command":
            self._handle_command_post()
            return

        if parsed_path.path == "/mobile-mic-state":
            self._handle_mobile_mic_state_post()
            return

        if parsed_path.path == "/mobile-audio":
            self._handle_mobile_audio_post()
            return

        if parsed_path.path == "/desktop-voice":
            self._handle_desktop_voice_post()
            return

        self.send_error(404, "Not Found")

    def _handle_command_post(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode())
            command = data.get("command", "").strip()
            if not command:
                self._set_headers("application/json", 400)
                self.wfile.write(json.dumps({"error": "No command provided"}).encode())
                return

            response = self._process_command(command)
            self._set_headers("application/json")
            self.wfile.write(json.dumps(response).encode())
        except json.JSONDecodeError:
            self._set_headers("application/json", 400)
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
        except Exception as e:
            self._set_headers("application/json", 500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_mobile_mic_state_post(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode() or "{}")
            active = bool(data.get("active", False))
            result = {"mobile_mic_active": active}
            if MobileRemoteHandler.mobile_mic_callback:
                callback_result = MobileRemoteHandler.mobile_mic_callback(active)
                if isinstance(callback_result, dict):
                    result.update(callback_result)
            self._set_headers("application/json")
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            self._set_headers("application/json", 500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_mobile_audio_post(self):
        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE": self.headers.get("Content-Type", ""),
                },
            )

            audio_field = form["audio"] if "audio" in form else None
            if not audio_field or not getattr(audio_field, "file", None):
                self._set_headers("application/json", 400)
                self.wfile.write(json.dumps({"error": "No audio file provided"}).encode())
                return

            audio_bytes = audio_field.file.read()
            filename = getattr(audio_field, "filename", "mobile_voice.webm")
            content_type = getattr(audio_field, "type", "audio/webm")

            if not MobileRemoteHandler.audio_callback:
                self._set_headers("application/json", 500)
                self.wfile.write(json.dumps({"error": "Mobile audio handler not configured"}).encode())
                return

            response = MobileRemoteHandler.audio_callback(audio_bytes, filename, content_type)
            self._set_headers("application/json")
            self.wfile.write(json.dumps(response).encode())
        except Exception as e:
            self._set_headers("application/json", 500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _handle_desktop_voice_post(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            data = json.loads(post_data.decode() or "{}")
            action = str(data.get("action", "")).strip().lower()
            if not MobileRemoteHandler.tool_manager:
                raise RuntimeError("Tool manager not configured")

            if action == "start":
                response = MobileRemoteHandler.tool_manager.execute("start_voice_assistant", {})
            elif action == "stop":
                response = MobileRemoteHandler.tool_manager.execute("stop_voice_assistant", {})
            else:
                response = "Invalid desktop voice action."

            self._set_headers("application/json")
            self.wfile.write(json.dumps({"status": "success", "response": response}).encode())
        except Exception as e:
            self._set_headers("application/json", 500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def _process_command(self, command):
        print(f"Mobile command received: {command}")

        result = self._quick_route(command)
        if result:
            return result

        if MobileRemoteHandler.command_callback:
            try:
                response = MobileRemoteHandler.command_callback(command)
                return {"response": response, "status": "success"}
            except Exception as e:
                return {"response": f"Error: {str(e)}", "status": "error"}

        if MobileRemoteHandler.tool_manager:
            return self._execute_with_tool_manager(command)

        return {"response": "Command received but no handler configured", "status": "pending"}

    def _quick_route(self, command):
        cmd = command.lower()
        panel_keywords = {
            "face": ["face panel", "face tab", "switch to face", "open face", "face recognition"],
            "chat": ["chat panel", "chat tab", "switch to chat", "open chat", "chatbot"],
            "voice": ["voice panel", "voice tab", "switch to voice", "open voice", "assistant"],
            "dashboard": ["dashboard panel", "dashboard tab", "switch to dashboard", "stats", "statistics"],
        }

        for panel, keywords in panel_keywords.items():
            if any(keyword in cmd for keyword in keywords) and MobileRemoteHandler.tool_manager:
                result = MobileRemoteHandler.tool_manager.execute("switch_panel", {"panel": panel})
                return {"response": result, "status": "success", "tool": "switch_panel"}

        if ("start voice" in cmd or "start listening" in cmd) and MobileRemoteHandler.tool_manager:
            result = MobileRemoteHandler.tool_manager.execute("start_voice_assistant", {})
            return {"response": result, "status": "success", "tool": "start_voice_assistant"}

        if ("stop voice" in cmd or "stop listening" in cmd) and MobileRemoteHandler.tool_manager:
            result = MobileRemoteHandler.tool_manager.execute("stop_voice_assistant", {})
            return {"response": result, "status": "success", "tool": "stop_voice_assistant"}

        return None

    def _execute_with_tool_manager(self, command):
        cmd = command.lower()

        youtube_match = re.search(
            r"(?:search|find|look up)\s+(.*?)\s+(?:on\s+youtube|in\s+youtube)",
            cmd
        ) or re.search(r"(?:youtube\s+search|search\s+youtube\s+for)\s+(.+)", cmd)
        if youtube_match:
            query = youtube_match.group(1).strip(" ?.")
            if query:
                result = MobileRemoteHandler.tool_manager.execute("search_youtube", {"query": query})
                return {"response": result, "status": "success", "tool": "search_youtube"}

        if "minimize " in cmd and "facetalk" in cmd:
            result = MobileRemoteHandler.tool_manager.execute("minimize_window", {"title": "FaceTalk"})
            return {"response": result, "status": "success", "tool": "minimize_window"}
        if "maximize " in cmd and "facetalk" in cmd:
            result = MobileRemoteHandler.tool_manager.execute("maximize_window", {"title": "FaceTalk"})
            return {"response": result, "status": "success", "tool": "maximize_window"}

        tool_patterns = {
            "open browser": ("open_browser", {}),
            "open notepad": ("open_notepad", {}),
            "open calculator": ("open_calculator", {}),
            "open word": ("open_word", {}),
            "open excel": ("open_excel", {}),
            "open powerpoint": ("open_powerpoint", {}),
            "open power point": ("open_powerpoint", {}),
            "take screenshot": ("take_screenshot", {}),
            "what time": ("get_time", {}),
            "get time": ("get_time", {}),
            "what date": ("get_date", {}),
            "get date": ("get_date", {}),
            "open youtube": ("open_youtube", {}),
            "minimize": ("minimize_windows", {}),
            "volume up": ("volume_up", {}),
            "volume down": ("volume_down", {}),
            "mute": ("mute_volume", {}),
            "system status": ("system_status", {}),
            "lock computer": ("lock_computer", {}),
            "lock screen": ("lock_computer", {}),
            "start camera": ("start_camera", {}),
            "open camera": ("start_camera", {}),
            "stop camera": ("stop_camera", {}),
            "close camera": ("stop_camera", {}),
            "start voice": ("start_voice_assistant", {}),
            "start listening": ("start_voice_assistant", {}),
            "stop voice": ("stop_voice_assistant", {}),
            "stop listening": ("stop_voice_assistant", {}),
            "start presentation": ("start_presentation", {}),
            "present powerpoint": ("start_presentation", {}),
            "next slide": ("next_slide", {}),
            "previous slide": ("previous_slide", {}),
            "duplicate slide": ("duplicate_slide", {}),
            "new slide": ("new_slide", {}),
            "save document": ("save_document", {}),
            "save as": ("save_document_as", {}),
        }

        for pattern, (tool_name, args) in tool_patterns.items():
            if pattern in cmd:
                result = MobileRemoteHandler.tool_manager.execute(tool_name, args)
                return {"response": result, "status": "success", "tool": tool_name}

        return {
            "response": f'Command "{command}" received. Try commands like "open word", "start presentation", or "minimize FaceTalk".',
            "status": "unrecognized"
        }


class MobileRemoteServer:
    def __init__(
        self,
        host="0.0.0.0",
        port=8888,
        tool_manager=None,
        command_callback=None,
        status_callback=None,
        audio_callback=None,
        mobile_mic_callback=None,
    ):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.is_running = False
        MobileRemoteHandler.tool_manager = tool_manager
        MobileRemoteHandler.command_callback = command_callback
        MobileRemoteHandler.status_callback = status_callback
        MobileRemoteHandler.audio_callback = audio_callback
        MobileRemoteHandler.mobile_mic_callback = mobile_mic_callback

    def get_local_ip(self):
        candidates = []

        try:
            hostname = socket.gethostname()
            for info in socket.getaddrinfo(hostname, None, socket.AF_INET):
                ip = info[4][0]
                if ip and not ip.startswith("127."):
                    candidates.append(ip)
        except Exception:
            pass

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            sock.close()
            if ip and not ip.startswith("127."):
                candidates.insert(0, ip)
        except Exception:
            pass

        for ip in candidates:
            if ip and not ip.startswith("127."):
                return ip

        return "127.0.0.1"

    def start(self):
        if self.is_running:
            print("Mobile remote server already running")
            return False

        try:
            ThreadingHTTPServer.allow_reuse_address = True
            self.server = ThreadingHTTPServer((self.host, self.port), MobileRemoteHandler)
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            self.is_running = True

            local_ip = self.get_local_ip()
            bind_host = self.host if self.host != "0.0.0.0" else local_ip
            print(f"\n{'=' * 50}")
            print("Mobile Remote Server Started!")
            print(f"{'=' * 50}")
            print(f"Local URL: http://localhost:{self.port}")
            print(f"Mobile URL: http://{local_ip}:{self.port}")
            print(f"Bound Host: http://{bind_host}:{self.port}")
            print(f"{'=' * 50}")
            print("Open the mobile URL on your phone (same WiFi network)")
            print(f"{'=' * 50}\n")
            return True
        except Exception as e:
            print(f"Failed to start mobile remote server: {e}")
            return False

    def _run_server(self):
        try:
            self.server.serve_forever()
        except Exception as e:
            print(f"Server error: {e}")

    def stop(self):
        if self.server:
            self.server.shutdown()
            self.is_running = False
            print("Mobile remote server stopped")

    def set_tool_manager(self, tool_manager):
        MobileRemoteHandler.tool_manager = tool_manager

    def set_command_callback(self, callback):
        MobileRemoteHandler.command_callback = callback

    def set_status_callback(self, callback):
        MobileRemoteHandler.status_callback = callback

    def set_audio_callback(self, callback):
        MobileRemoteHandler.audio_callback = callback

    def set_mobile_mic_callback(self, callback):
        MobileRemoteHandler.mobile_mic_callback = callback


if __name__ == "__main__":
    server = MobileRemoteServer(port=8888)
    server.start()
    try:
        while True:
            pass
    except KeyboardInterrupt:
        server.stop()
