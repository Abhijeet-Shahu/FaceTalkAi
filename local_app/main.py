# main.py
from asyncio import subprocess
import os
import webbrowser

import pyautogui
import requests
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
from pydoc import text
import tkinter as tk
from tkinter import ttk, messagebox
import cv2
from PIL import Image, ImageTk
import threading
import numpy as np
from supabase_manager import SupabaseManager
from face_recognition_module import FaceRecognizer
from chatbot_module import GroqChatbot
import os
from dotenv import load_dotenv
from datetime import datetime
import queue

from voice_module import VoiceAssistant  # Import the voice assistant module

from tool_manager import ToolManager  # Import the tool manager


load_dotenv()  # Load environment variables from .env file

class FaceTalkAI:
    def __init__(self, root):
        self.root = root
        self.root.title("FaceTalk AI - Intelligent Face Recognition System")
        self.root.geometry("1280x720")
        self.root.configure(bg='#1a1a2e')
        
        
        # Initialize Supabase
        
        self.db = SupabaseManager(
            url=os.getenv('SUPABASE_URL'),
            key=os.getenv('SUPABASE_KEY')
        )
        
        # Initialize modules
        self.face_recognizer = FaceRecognizer(self.db)

        from intent_engine import IntentEngine

        # Initialize voice assistant with callback
        self.voice = VoiceAssistant(
            on_speech_callback=self.handle_voice_input
        ) 

        self.tool_manager = ToolManager()  # Get tools from the tool manager
        
        # Video capture
        self.cap = None
        self.running = False
        self.current_user = None
        self.frame_queue = queue.Queue(maxsize=2)
        
        # Setup UI
        self.setup_ui()
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def setup_ui(self):
        """Create the main UI with tabs"""
        
        # Create main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Tab 1: Face Recognition
        self.face_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.face_tab, text="🔍 Face Recognition")
        self.setup_face_tab()
        
        # Tab 2: Chatbot
        self.chat_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.chat_tab, text="💬 AI Chatbot")
        self.setup_chat_tab()
        
        # Tab 3: Voice Assistant (placeholder for your friend)
        self.voice_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.voice_tab, text="🎤 Voice Assistant")
        self.setup_voice_tab()
        
        # Tab 4: Dashboard
        self.dashboard_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_tab, text="📊 Dashboard")
        self.setup_dashboard_tab()
        
        # Status bar
        self.setup_status_bar()
    
    def setup_face_tab(self):
        """Face recognition tab with video feed"""
        
        # Left panel - Video feed
        left_frame = ttk.Frame(self.face_tab)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Video label
        self.video_label = ttk.Label(left_frame)
        self.video_label.pack(fill=tk.BOTH, expand=True)
        
        # Control buttons
        control_frame = ttk.Frame(left_frame)
        control_frame.pack(fill=tk.X, pady=5)
        
        self.start_btn = ttk.Button(control_frame, text="▶ Start Camera", 
                                    command=self.start_camera)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(control_frame, text="⏹ Stop Camera", 
                                   command=self.stop_camera, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Right panel - User info
        right_frame = ttk.Frame(self.face_tab, width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        right_frame.pack_propagate(False)
        
        # User info display
        self.user_info_frame = ttk.LabelFrame(right_frame, text="👤 User Information", padding=10)
        self.user_info_frame.pack(fill=tk.X, pady=5)
        
        self.user_name_label = ttk.Label(self.user_info_frame, text="Name: --", font=('Arial', 12))
        self.user_name_label.pack(anchor=tk.W, pady=2)
        
        self.user_email_label = ttk.Label(self.user_info_frame, text="Email: --")
        self.user_email_label.pack(anchor=tk.W, pady=2)
        
        self.user_dept_label = ttk.Label(self.user_info_frame, text="Department: --")
        self.user_dept_label.pack(anchor=tk.W, pady=2)
        
        self.user_lastseen_label = ttk.Label(self.user_info_frame, text="Last Seen: --")
        self.user_lastseen_label.pack(anchor=tk.W, pady=2)
        
        self.user_confidence_label = ttk.Label(self.user_info_frame, text="Confidence: --")
        self.user_confidence_label.pack(anchor=tk.W, pady=2)
        
        # Attendance log
        log_frame = ttk.LabelFrame(right_frame, text="📋 Recent Activity", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = tk.Text(log_frame, height=10, width=30, bg='#2a2a3e', fg='white')
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
    
    def setup_chat_tab(self):
        """Chatbot tab with Groq AI"""
        
        # Chat history display
        chat_frame = ttk.Frame(self.chat_tab)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Chat text area
        self.chat_history = tk.Text(chat_frame, height=20, bg='#2a2a3e', fg='white',
                                    wrap=tk.WORD, font=('Arial', 11))
        self.chat_history.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Scrollbar
        chat_scroll = ttk.Scrollbar(self.chat_history)
        chat_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.chat_history.config(yscrollcommand=chat_scroll.set)
        
        # Input frame
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        self.chat_input = ttk.Entry(input_frame, font=('Arial', 11))
        self.chat_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.chat_input.bind('<Return>', lambda e: self.send_message())
        
        self.send_btn = ttk.Button(input_frame, text="Send", command=self.send_message)
        self.send_btn.pack(side=tk.RIGHT, padx=5)
        
        # Clear button
        self.clear_btn = ttk.Button(chat_frame, text="Clear Chat", 
                                   command=self.clear_chat)
        self.clear_btn.pack(pady=5)
    
    def setup_voice_tab(self):
        """Voice assistant tab"""

        voice_frame = ttk.Frame(self.voice_tab)
        voice_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        ttk.Label(
            voice_frame,
            text="🎤 Voice Assistant",
            font=('Arial', 16, 'bold')
        ).pack(pady=20)

        self.voice_status_label = ttk.Label(
            voice_frame,
            text="Status: Stopped",
            font=('Arial', 12)
        )
        self.voice_status_label.pack(pady=10)

        ttk.Button(
            voice_frame,
            text="▶ Start Voice Assistant",
            command=self.start_voice
        ).pack(pady=10)

        ttk.Button(
            voice_frame,
            text="⏹ Stop Voice Assistant",
            command=self.stop_voice
        ).pack(pady=5)

    
    def handle_voice_input(self, text):
        """
        Called when voice assistant detects speech.
        This sends voice text into chatbot pipeline.

        """

        if "Jarvis" not in text:
            return  # Ignore if not addressed to the assistant
        
        # show msg to the client
        self.root.after(
            0,lambda: self.chat_history.insert(
                tk.END, f"You (Voice): {text}\n", 'user'
            )
        )

        threading.Thread(
            target=self.get_chat_response,
            args=(text,),
            daemon=True
        ).start()

    def setup_dashboard_tab(self):
        """Dashboard with statistics"""
        
        dashboard_frame = ttk.Frame(self.dashboard_tab)
        dashboard_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Stats cards in grid
        stats_frame = ttk.Frame(dashboard_frame)
        stats_frame.pack(fill=tk.X, pady=10)
        
        # Total users
        user_card = ttk.LabelFrame(stats_frame, text="Total Users", padding=15)
        user_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.total_users_label = ttk.Label(user_card, text="0", 
                                           font=('Arial', 24, 'bold'))
        self.total_users_label.pack()
        
        # Today's attendance
        attendance_card = ttk.LabelFrame(stats_frame, text="Today's Attendance", padding=15)
        attendance_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.today_attendance_label = ttk.Label(attendance_card, text="0", 
                                                font=('Arial', 24, 'bold'))
        self.today_attendance_label.pack()
        
        # Unknown faces
        unknown_card = ttk.LabelFrame(stats_frame, text="Unknown Faces", padding=15)
        unknown_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.unknown_label = ttk.Label(unknown_card, text="0", 
                                       font=('Arial', 24, 'bold'))
        self.unknown_label.pack()
        
        # Recent activity table
        activity_frame = ttk.LabelFrame(dashboard_frame, text="Recent Activity", padding=10)
        activity_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Treeview for activity
        columns = ('Time', 'User', 'Action', 'Confidence')
        self.activity_tree = ttk.Treeview(activity_frame, columns=columns, 
                                          show='headings', height=10)
        
        for col in columns:
            self.activity_tree.heading(col, text=col)
            self.activity_tree.column(col, width=150)
        
        self.activity_tree.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        tree_scroll = ttk.Scrollbar(activity_frame, orient=tk.VERTICAL, 
                                    command=self.activity_tree.yview)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.activity_tree.configure(yscrollcommand=tree_scroll.set)
        
        # Refresh button
        ttk.Button(dashboard_frame, text="🔄 Refresh Dashboard", 
                  command=self.refresh_dashboard).pack(pady=10)
        
        # Initial load
        self.refresh_dashboard()
    
    def setup_status_bar(self):
        """Bottom status bar"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_label = ttk.Label(status_frame, text="Ready", 
                                       relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.camera_status = ttk.Label(status_frame, text="📷 Camera: Off", 
                                       relief=tk.SUNKEN, width=20)
        self.camera_status.pack(side=tk.RIGHT)
    
    def start_camera(self):
        # Strart video capture
        try:
            from mobile_camera import MobileCamera
            self.camera = MobileCamera(camera_type="iriun")

            if not self.camera.connect():
                messagebox.showerror("Camera Error", "Unable to connect to the camera. Please ensure the mobile app is running and connected to the same network.")
                return
            
            self.running = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.camera_status.config(text="📷 Camera: On")

            self.video_thread = threading.Thread(target=self.process_video, daemon=True)
            self.video_thread.start()

        except Exception as e:
            messagebox.showerror("Camera Error", f"An error occurred while starting the camera: {str(e)}")
    
    def stop_camera(self):
        """Stop video capture"""
        self.running = False

        import time
        time.sleep(0.1)  # Wait for thread to finish

        if hasattr(self, 'camera') and self.camera:
            self.camera.release()
            self.camera = None

        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.camera_status.config(text="📷 Camera: Off")
        self.video_label.config(image='')  # Clear video display
    
    def process_video(self):
        """Process video frames in separate thread"""
        while self.running:
            try:
                if hasattr(self, 'camera') and self.camera:
                    ret,frame = self.camera.get_frame()
                    if ret and frame is not None:
                        processed_frame , user_info = self.face_recognizer.process_frame(frame)

                        # Update display in main thread
                        self.root.after(0, self.update_video_display, processed_frame, user_info)
            except Exception as e:
                print(f"Video processing error: {e}")

            import time
            time.sleep(0.03)  # Limit to ~30 FPS
    
    def update_video_display(self, frame, user_info):
        """Update video display with face recognition results"""
        try:
            # Convert frame for tkinter
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            imgtk = ImageTk.PhotoImage(image=img)
            
            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)
            
            # Update user info if recognized
            if user_info:
                self.current_user = user_info
                self.update_user_info(user_info)
                
                # Log to attendance
                self.db.log_attendance(user_info['id'], 'login', user_info['confidence'])
                self.add_to_log(f"✅ {user_info['name']} recognized")
                
        except Exception as e:
            print(f"Display error: {e}")
    
    def update_user_info(self, user_info):
        """Update user information display"""
        self.user_name_label.config(text=f"Name: {user_info['name']}")
        self.user_email_label.config(text=f"Email: {user_info.get('email', '--')}")
        self.user_dept_label.config(text=f"Department: {user_info.get('department', '--')}")
        self.user_confidence_label.config(text=f"Confidence: {user_info['confidence']:.2%}")
    
    def add_to_log(self, message):
        """Add message to activity log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
    
    def send_message(self):
        """Send message to chatbot"""
        message = self.chat_input.get().strip()
        if not message:
            return
        
        # Display user message
        self.chat_history.insert(tk.END, f"You: {message}\n", 'user')
        self.chat_history.tag_config('user', foreground='#4CAF50')
        
        # Clear input
        self.chat_input.delete(0, tk.END)
        
        # Get response in separate thread
        threading.Thread(target=self.get_chat_response, args=(message,), daemon=True).start()
    
    import requests
    def get_chat_response(self, message):
        """Get chatbot response"""
        try:
            response = requests.post(
                "http://127.0.0.1:8000/process",
                json={
                    "text": message
                }            
            )

            data = response.json()
            print("Intent Engine Response:", data)

            if data.get("type") == "tool":
                tool_name = data.get("tool")   
                args = data.get("args", {}) 
                
                result = self.tool_manager.execute(tool_name, args)

                self.root.after(0, self.display_chat_response, result)
                self.root.after(0, lambda: self.voice.speak(result))
                return
            
            elif data.get("type") == "chat":
                result = data.get("response","Not response")

                self.root.after(0, self.display_chat_response, result)
                self.root.after(0, lambda: self.voice.speak(result))
                return
            

            # Save to database if user is recognized
            if self.current_user:
                self.db.save_chat_message(self.current_user['id'], message, response)
       
        except Exception as e:
            self.root.after(0, self.display_chat_response, f"Error: {str(e)}")

    
    
    def display_chat_response(self, response):
        """Display chatbot response"""
        self.chat_history.insert(tk.END, f"Jarvis: {response}\n\n", 'ai')
        self.chat_history.tag_config('ai', foreground='#2196F3')
        self.chat_history.see(tk.END)


    def clear_chat(self):
        """Clear chat history"""
        self.chat_history.delete(1.0, tk.END)
    
    def refresh_dashboard(self):
        """Refresh dashboard statistics"""
        try:
            # Get total users
            users = self.db.supabase.table('users').select('*', count='exact').execute()
            self.total_users_label.config(text=str(users.count))
            
            # Get today's attendance
            today = datetime.now().date().isoformat()
            attendance = self.db.supabase.table('attendance_logs') \
                .select('*', count='exact') \
                .gte('timestamp', f"{today}T00:00:00") \
                .lte('timestamp', f"{today}T23:59:59") \
                .execute()
            self.today_attendance_label.config(text=str(attendance.count))
            
            # Get unknown faces
            unknown = self.db.supabase.table('attendance_logs') \
                .select('*', count='exact') \
                .eq('action', 'unknown_face') \
                .execute()
            self.unknown_label.config(text=str(unknown.count))
            
            # Update activity tree
            recent = self.db.get_recent_activity(10)
            for item in self.activity_tree.get_children():
                self.activity_tree.delete(item)
            
            for log in recent:
                self.activity_tree.insert('', tk.END, values=(
                    log['timestamp'][11:19],
                    log.get('users', {}).get('name', 'Unknown'),
                    log['action'],
                    f"{log['confidence']:.2%}" if log['confidence'] else '--'
                ))
                
        except Exception as e:
            print(f"Dashboard error: {e}")
    
    def on_closing(self):
        """Handle window closing"""
        self.running = False
        import time
        time.sleep(0.2)  # Wait for threads to finish

        if hasattr(self, 'camera') and self.camera:
            self.camera.release()

        self.root.destroy()

    def start_voice(self):
        self.voice.start()
        self.voice_status_label.config(text="Status: Listening...")
        self.status_label.config(text="Voice Assistant Active")


    def stop_voice(self):
        self.voice.stop()
        self.voice_status_label.config(text="Status: Stopped")
        self.status_label.config(text="Voice Assistant Stopped")


if __name__ == "__main__":
    root = tk.Tk()
    app = FaceTalkAI(root)
    
    # Apply dark theme
    style = ttk.Style()
    style.theme_use('clam')
    style.configure('TLabel', background='#1a1a2e', foreground='white')
    style.configure('TFrame', background='#1a1a2e')
    style.configure('TButton', padding=6)
    
    root.mainloop()