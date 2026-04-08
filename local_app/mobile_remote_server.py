# mobile_remote_server.py
"""
Mobile Remote Control Server for FaceTalkAI
Allows controlling the desktop app from mobile devices via WiFi

Usage:
1. Start the server on desktop
2. Connect mobile to same WiFi network
3. Open browser on mobile and go to http://<desktop-ip>:8888
4. Use voice or text commands to control desktop
"""

import threading
import json
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import os
from datetime import datetime

# HTML template for mobile web interface
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
        .container { max-width: 400px; margin: 0 auto; }
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
        }
        .status.connected { border: 2px solid #00ff88; }
        .status.disconnected { border: 2px solid #ff4444; }
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
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
        .quick-commands {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-top: 20px;
        }
        .quick-btn {
            padding: 20px 10px;
            font-size: 14px;
            background: rgba(255,255,255,0.1);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 12px;
            color: #fff;
        }
        .response-box {
            background: rgba(0,0,0,0.3);
            border-radius: 12px;
            padding: 15px;
            margin-top: 20px;
            min-height: 100px;
            max-height: 200px;
            overflow-y: auto;
        }
        .response-item {
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .response-item:last-child { border-bottom: none; }
        .response-time { font-size: 12px; color: #888; }
        .panel-buttons {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-top: 15px;
        }
        .panel-btn {
            padding: 12px 5px;
            font-size: 12px;
            background: #0f3460;
            border: 1px solid #00d9ff;
            border-radius: 8px;
            color: #00d9ff;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎙️ FaceTalk AI Remote</h1>
        
        <div class="status connected" id="status">
            <strong>Connected to Desktop</strong>
            <div style="font-size: 12px; margin-top: 5px;" id="ip-display"></div>
        </div>

        <input type="text" class="command-input" id="commandInput" 
               placeholder="Type a command..." autocomplete="off">
        
        <button class="btn btn-primary" onclick="sendCommand()">Send Command</button>
        
        <button class="btn btn-voice" id="voiceBtn" onclick="toggleVoice()">
            🎤 Hold to Speak
        </button>

        <div class="panel-buttons">
            <button class="panel-btn" onclick="switchPanel('face')">👤 Face</button>
            <button class="panel-btn" onclick="switchPanel('chat')">💬 Chat</button>
            <button class="panel-btn" onclick="switchPanel('voice')">🎙️ Voice</button>
            <button class="panel-btn" onclick="switchPanel('dashboard')">📊 Dashboard</button>
        </div>

        <div class="quick-commands">
            <button class="quick-btn" onclick="quickCmd('open browser')">🌐 Browser</button>
            <button class="quick-btn" onclick="quickCmd('take screenshot')">📸 Screenshot</button>
            <button class="quick-btn" onclick="quickCmd('volume up')">🔊 Vol Up</button>
            <button class="quick-btn" onclick="quickCmd('volume down')">🔉 Vol Down</button>
            <button class="quick-btn" onclick="quickCmd('open notepad')">📝 Notepad</button>
            <button class="quick-btn" onclick="quickCmd('open calculator')">🧮 Calculator</button>
            <button class="quick-btn" onclick="quickCmd('lock computer')">🔒 Lock</button>
            <button class="quick-btn" onclick="quickCmd('minimize windows')">⬇️ Minimize</button>
        </div>

        <div class="response-box" id="responses">
            <div class="response-item">
                <div>Ready to receive commands...</div>
                <div class="response-time">Just now</div>
            </div>
        </div>
    </div>

    <script>
        let recognition = null;
        let isListening = false;

        document.getElementById('ip-display').textContent = 'Server: ' + window.location.host;

        // Send command via fetch
        async function sendCommand(cmd) {
            const command = cmd || document.getElementById('commandInput').value.trim();
            if (!command) return;
            
            document.getElementById('commandInput').value = '';
            addResponse('You: ' + command, 'sending...');
            
            try {
                const response = await fetch('/command', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ command: command })
                });
                const data = await response.json();
                addResponse('Desktop: ' + (data.response || data.message || 'Done'), 'completed');
            } catch (err) {
                addResponse('Error: Could not reach desktop', 'failed');
            }
        }

        function quickCmd(cmd) { sendCommand(cmd); }
        
        function switchPanel(panel) { sendCommand('switch to ' + panel + ' panel'); }

        function addResponse(text, status) {
            const box = document.getElementById('responses');
            const time = new Date().toLocaleTimeString();
            const item = document.createElement('div');
            item.className = 'response-item';
            item.innerHTML = '<div>' + text + '</div><div class="response-time">' + time + '</div>';
            box.insertBefore(item, box.firstChild);
            if (box.children.length > 10) box.removeChild(box.lastChild);
        }

        // Voice recognition (Web Speech API)
        function toggleVoice() {
            const btn = document.getElementById('voiceBtn');
            
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                alert('Voice recognition not supported in this browser. Use Chrome on Android.');
                return;
            }

            if (isListening) {
                recognition.stop();
                isListening = false;
                btn.classList.remove('listening');
                btn.textContent = '🎤 Hold to Speak';
                return;
            }

            recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.lang = 'en-US';

            recognition.onstart = function() {
                isListening = true;
                btn.classList.add('listening');
                btn.textContent = '🔴 Listening...';
            };

            recognition.onresult = function(event) {
                const transcript = event.results[0][0].transcript;
                document.getElementById('commandInput').value = transcript;
                sendCommand(transcript);
            };

            recognition.onerror = function(event) {
                console.error('Speech error:', event.error);
                addResponse('Voice error: ' + event.error, 'failed');
            };

            recognition.onend = function() {
                isListening = false;
                btn.classList.remove('listening');
                btn.textContent = '🎤 Hold to Speak';
            };

            recognition.start();
        }

        // Handle Enter key
        document.getElementById('commandInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') sendCommand();
        });
    </script>
</body>
</html>
"""


class MobileRemoteHandler(BaseHTTPRequestHandler):
    """HTTP request handler for mobile remote commands"""
    
    tool_manager = None
    command_callback = None
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass
    
    def _set_headers(self, content_type='text/html', status=200):
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_OPTIONS(self):
        self._set_headers()
    
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/' or parsed_path.path == '/index.html':
            self._set_headers('text/html')
            self.wfile.write(MOBILE_WEB_PAGE.encode())
        
        elif parsed_path.path == '/status':
            self._set_headers('application/json')
            response = {
                'status': 'online',
                'app': 'FaceTalk AI',
                'timestamp': datetime.now().isoformat()
            }
            self.wfile.write(json.dumps(response).encode())
        
        else:
            self.send_error(404, 'Not Found')
    
    def do_POST(self):
        parsed_path = urlparse(self.path)
        
        if parsed_path.path == '/command':
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data.decode())
                command = data.get('command', '').strip()
                
                if not command:
                    self._set_headers('application/json', 400)
                    self.wfile.write(json.dumps({'error': 'No command provided'}).encode())
                    return
                
                # Process the command
                response = self._process_command(command)
                
                self._set_headers('application/json')
                self.wfile.write(json.dumps(response).encode())
                
            except json.JSONDecodeError:
                self._set_headers('application/json', 400)
                self.wfile.write(json.dumps({'error': 'Invalid JSON'}).encode())
            except Exception as e:
                self._set_headers('application/json', 500)
                self.wfile.write(json.dumps({'error': str(e)}).encode())
        else:
            self.send_error(404, 'Not Found')
    
    def _process_command(self, command):
        """Process incoming command and execute via tool manager"""
        print(f"📱 Mobile command received: {command}")
        
        # First try quick routing
        result = self._quick_route(command)
        if result:
            return result
        
        # If callback is set, use it (for integration with main app)
        if MobileRemoteHandler.command_callback:
            try:
                response = MobileRemoteHandler.command_callback(command)
                return {'response': response, 'status': 'success'}
            except Exception as e:
                return {'response': f'Error: {str(e)}', 'status': 'error'}
        
        # Direct tool execution if tool manager is available
        if MobileRemoteHandler.tool_manager:
            return self._execute_with_tool_manager(command)
        
        return {'response': 'Command received but no handler configured', 'status': 'pending'}
    
    def _quick_route(self, command):
        """Quick pattern matching for common commands"""
        cmd = command.lower()
        
        # Panel switching
        panel_keywords = {
            'face': ['face panel', 'face tab', 'switch to face', 'open face', 'face recognition'],
            'chat': ['chat panel', 'chat tab', 'switch to chat', 'open chat', 'chatbot'],
            'voice': ['voice panel', 'voice tab', 'switch to voice', 'open voice', 'assistant'],
            'dashboard': ['dashboard panel', 'dashboard tab', 'switch to dashboard', 'stats', 'statistics']
        }
        
        for panel, keywords in panel_keywords.items():
            if any(kw in cmd for kw in keywords):
                if MobileRemoteHandler.tool_manager:
                    result = MobileRemoteHandler.tool_manager.execute('switch_panel', {'panel': panel})
                    return {'response': result, 'status': 'success', 'tool': 'switch_panel'}
        
        return None
    
    def _execute_with_tool_manager(self, command):
        """Execute command using tool manager with pattern matching"""
        cmd = command.lower()
        
        tool_patterns = {
            'open browser': ('open_browser', {}),
            'open notepad': ('open_notepad', {}),
            'open calculator': ('open_calculator', {}),
            'take screenshot': ('take_screenshot', {}),
            'what time': ('get_time', {}),
            'get time': ('get_time', {}),
            'what date': ('get_date', {}),
            'get date': ('get_date', {}),
            'open youtube': ('open_youtube', {}),
            'minimize': ('minimize_windows', {}),
            'volume up': ('volume_up', {}),
            'volume down': ('volume_down', {}),
            'mute': ('mute_volume', {}),
            'system status': ('system_status', {}),
            'lock computer': ('lock_computer', {}),
            'lock screen': ('lock_computer', {}),
            'start camera': ('start_camera', {}),
            'open camera': ('start_camera', {}),
            'stop camera': ('stop_camera', {}),
            'close camera': ('stop_camera', {}),
            'stop voice': ('stop_voice_assistant', {}),
            'stop listening': ('stop_voice_assistant', {}),
        }
        
        for pattern, (tool_name, args) in tool_patterns.items():
            if pattern in cmd:
                result = MobileRemoteHandler.tool_manager.execute(tool_name, args)
                return {'response': result, 'status': 'success', 'tool': tool_name}
        
        # If no pattern matched, return generic response
        return {
            'response': f'Command "{command}" received. Try specific commands like "open browser" or "take screenshot".',
            'status': 'unrecognized'
        }


class MobileRemoteServer:
    """Mobile Remote Control Server"""
    
    def __init__(self, host='0.0.0.0', port=8888, tool_manager=None, command_callback=None):
        self.host = host
        self.port = port
        self.server = None
        self.server_thread = None
        self.is_running = False
        
        # Set class-level references for the handler
        MobileRemoteHandler.tool_manager = tool_manager
        MobileRemoteHandler.command_callback = command_callback
    
    def get_local_ip(self):
        """Get local IP address for mobile connection"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return '127.0.0.1'
    
    def start(self):
        """Start the mobile remote server"""
        if self.is_running:
            print("⚠️ Mobile remote server already running")
            return False
        
        try:
            self.server = HTTPServer((self.host, self.port), MobileRemoteHandler)
            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()
            self.is_running = True
            
            local_ip = self.get_local_ip()
            print(f"\n{'='*50}")
            print(f"📱 Mobile Remote Server Started!")
            print(f"{'='*50}")
            print(f"🌐 Local URL: http://localhost:{self.port}")
            print(f"📱 Mobile URL: http://{local_ip}:{self.port}")
            print(f"{'='*50}")
            print(f"Open the mobile URL on your phone (same WiFi network)")
            print(f"{'='*50}\n")
            
            return True
        except Exception as e:
            print(f"❌ Failed to start mobile remote server: {e}")
            return False
    
    def _run_server(self):
        """Run server in thread"""
        try:
            self.server.serve_forever()
        except Exception as e:
            print(f"Server error: {e}")
    
    def stop(self):
        """Stop the mobile remote server"""
        if self.server:
            self.server.shutdown()
            self.is_running = False
            print("📱 Mobile remote server stopped")
    
    def set_tool_manager(self, tool_manager):
        """Update the tool manager reference"""
        MobileRemoteHandler.tool_manager = tool_manager
    
    def set_command_callback(self, callback):
        """Set callback for processing commands (integration with main app)"""
        MobileRemoteHandler.command_callback = callback


# Standalone test
if __name__ == '__main__':
    print("Starting Mobile Remote Server in standalone mode...")
    server = MobileRemoteServer(port=8888)
    server.start()
    
    try:
        while True:
            pass
    except KeyboardInterrupt:
        server.stop()
        print("\nServer stopped.")
