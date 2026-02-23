# main.py
import os
import webbrowser
import customtkinter as ctk
from customtkinter import *
import pyautogui
import requests
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
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
import time
from voice_module import VoiceAssistant
from tool_manager import ToolManager
from intent_engine import IntentEngine
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json

load_dotenv()

# Configure CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class FaceTalkAI:
    def __init__(self):
        self.window = ctk.CTk()
        self.window.title("FaceTalk AI - Intelligent Face Recognition System")
        self.window.geometry("1400x800")
        
        # Initialize Supabase
        self.db = SupabaseManager(
            url=os.getenv('SUPABASE_URL'),
            key=os.getenv('SUPABASE_KEY')
        )
        
        # Initialize modules
        self.face_recognizer = FaceRecognizer(
            self.db,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
        self.intent_engine = IntentEngine(api_key=os.getenv("GROQ_API_KEY"))
        
        # Initialize voice assistant
        self.voice = VoiceAssistant(
            on_speech_callback=self.handle_voice_input
        )
        
        self.tool_manager = ToolManager(
            switch_panel_callback=self.switch_panel,
            start_camera_callback=self.start_camera_from_voice,
            stop_camera_callback=self.stop_camera_from_voice,
            stop_voice_callback=self.stop_voice_from_voice
        )
        
        # Video capture
        self.cap = None
        self.running = False
        self.current_user = None
        self.frame_queue = queue.Queue(maxsize=2)
        self.active_user_id = None
        self.last_detection_ts = 0.0
        self.last_greeted_at = {}
        self.greeting_cooldown_sec = 30
        self.absence_reset_sec = 4
        self.last_space_toggle_ts = 0.0
        self.space_toggle_debounce_sec = 0.35
        self.startup_notes = []
        
        # Setup UI
        self.setup_ui()
        self.window.after(250, self.run_startup_checks)
        
        # Bind window close event
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.window.bind_all("<space>", self.handle_space_voice_toggle)
    
    def setup_ui(self):
        """Create the main UI with modern design"""
        
        # Configure grid layout
        self.window.grid_columnconfigure(1, weight=1)
        self.window.grid_rowconfigure(0, weight=1)
        
        # Create sidebar
        self.create_sidebar()
        
        # Create main content area
        self.create_main_content()
        
        # Create status bar
        self.create_status_bar()
        
        # Initialize with face tab
        self.show_face_tab()
    
    def create_sidebar(self):
        """Create modern sidebar navigation"""
        
        # Sidebar frame
        self.sidebar = ctk.CTkFrame(self.window, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")
        self.sidebar.grid_rowconfigure(6, weight=1)
        
        # Logo/Title
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=20, pady=(30, 20))
        
        title_label = ctk.CTkLabel(
            logo_frame,
            text="FaceTalk AI",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=("#1E88E5", "#64B5F6")
        )
        title_label.pack()
        
        subtitle_label = ctk.CTkLabel(
            logo_frame,
            text="Intelligent Recognition",
            font=ctk.CTkFont(size=12),
            text_color=("gray70", "gray70")
        )
        subtitle_label.pack()
        
        # Separator
        separator = ctk.CTkFrame(self.sidebar, height=2, fg_color=("gray80", "gray30"))
        separator.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        # Navigation buttons
        nav_buttons = [
            ("🔍 Face Recognition", self.show_face_tab, 2),
            ("💬 AI Chatbot", self.show_chat_tab, 3),
            ("🎤 Voice Assistant", self.show_voice_tab, 4),
            ("📊 Dashboard", self.show_dashboard_tab, 5),
        ]
        
        for text, command, row in nav_buttons:
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                command=command,
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                anchor="w",
                height=40,
                font=ctk.CTkFont(size=14)
            )
            btn.grid(row=row, column=0, padx=20, pady=5, sticky="ew")
        
        # User info at bottom
        user_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        user_frame.grid(row=6, column=0, padx=20, pady=20, sticky="s")
        
        self.sidebar_user_name = ctk.CTkLabel(
            user_frame,
            text="Not Logged In",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.sidebar_user_name.pack()
        
        self.sidebar_user_status = ctk.CTkLabel(
            user_frame,
            text="● Offline",
            text_color="gray50",
            font=ctk.CTkFont(size=11)
        )
        self.sidebar_user_status.pack()
    
    def create_main_content(self):
        """Create main content area with tabs"""
        
        # Main content frame
        self.main_content = ctk.CTkFrame(self.window, corner_radius=10)
        self.main_content.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(0, weight=1)
        
        # Create frames for each tab (hidden initially)
        self.face_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.chat_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.voice_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.dashboard_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
    
    def create_status_bar(self):
        """Create modern status bar"""
        
        self.status_bar = ctk.CTkFrame(self.window, height=40, corner_radius=0)
        self.status_bar.grid(row=1, column=1, sticky="ew", padx=20, pady=(0, 20))
        self.status_bar.grid_columnconfigure(0, weight=1)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.status_bar,
            text="● Ready",
            text_color="green",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        # Camera status with icon
        self.camera_status_frame = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        self.camera_status_frame.grid(row=0, column=1, padx=15, pady=10, sticky="e")
        
        self.camera_status_label = ctk.CTkLabel(
            self.camera_status_frame,
            text="📷 Camera: Off",
            font=ctk.CTkFont(size=12)
        )
        self.camera_status_label.pack(side="left", padx=5)
        
        # Time
        self.time_label = ctk.CTkLabel(
            self.camera_status_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="gray70"
        )
        self.time_label.pack(side="left", padx=10)
        
        # Update time
        self.update_time()
    
    def show_face_tab(self):
        """Show face recognition tab"""
        self.hide_all_tabs()
        self.face_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.setup_face_tab()
    
    def show_chat_tab(self):
        """Show chatbot tab"""
        self.hide_all_tabs()
        self.chat_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.setup_chat_tab()
    
    def show_voice_tab(self):
        """Show voice assistant tab"""
        self.hide_all_tabs()
        self.voice_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.setup_voice_tab()
    
    def show_dashboard_tab(self):
        """Show dashboard tab"""
        self.hide_all_tabs()
        self.dashboard_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.setup_dashboard_tab()
    
    def hide_all_tabs(self):
        """Hide all tab frames"""
        for frame in [self.face_frame, self.chat_frame, self.voice_frame, self.dashboard_frame]:
            frame.grid_remove()
    
    def setup_face_tab(self):
        """Face recognition tab with modern design"""
        
        # Clear existing widgets
        for widget in self.face_frame.winfo_children():
            widget.destroy()
        
        # Configure grid
        self.face_frame.grid_columnconfigure(0, weight=3)
        self.face_frame.grid_columnconfigure(1, weight=1)
        self.face_frame.grid_rowconfigure(0, weight=1)
        
        # Video feed panel
        video_panel = ctk.CTkFrame(self.face_frame)
        video_panel.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")
        video_panel.grid_rowconfigure(0, weight=1)
        video_panel.grid_columnconfigure(0, weight=1)
        
        # Video label with placeholder
        self.video_label = ctk.CTkLabel(
            video_panel,
            text="Camera Feed\n\nClick 'Start Camera' to begin",
            font=ctk.CTkFont(size=16),
            fg_color=("gray85", "gray25"),
            corner_radius=10
        )
        self.video_label.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        # Camera controls
        control_frame = ctk.CTkFrame(video_panel, fg_color="transparent")
        control_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        control_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.start_btn = ctk.CTkButton(
            control_frame,
            text="▶ Start Camera",
            command=self.start_camera,
            fg_color="green",
            hover_color="darkgreen",
            height=40
        )
        self.start_btn.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.stop_btn = ctk.CTkButton(
            control_frame,
            text="⏹ Stop Camera",
            command=self.stop_camera,
            fg_color="red",
            hover_color="darkred",
            state="disabled",
            height=40
        )
        self.stop_btn.grid(row=0, column=1, padx=5, sticky="ew")
        
        # Info panel
        info_panel = ctk.CTkFrame(self.face_frame)
        info_panel.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="nsew")
        info_panel.grid_columnconfigure(0, weight=1)
        
        # User info card
        user_card = ctk.CTkFrame(info_panel)
        user_card.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        
        ctk.CTkLabel(
            user_card,
            text="👤 User Information",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")
        
        # User info labels
        self.user_name_label = ctk.CTkLabel(
            user_card,
            text="Name: --",
            font=ctk.CTkFont(size=13),
            anchor="w"
        )
        self.user_name_label.grid(row=1, column=0, padx=15, pady=2, sticky="w")
        
        self.user_email_label = ctk.CTkLabel(
            user_card,
            text="Email: --",
            font=ctk.CTkFont(size=13),
            anchor="w"
        )
        self.user_email_label.grid(row=2, column=0, padx=15, pady=2, sticky="w")
        
        self.user_dept_label = ctk.CTkLabel(
            user_card,
            text="Department: --",
            font=ctk.CTkFont(size=13),
            anchor="w"
        )
        self.user_dept_label.grid(row=3, column=0, padx=15, pady=2, sticky="w")
        
        self.user_confidence_label = ctk.CTkLabel(
            user_card,
            text="Confidence: --",
            font=ctk.CTkFont(size=13),
            anchor="w"
        )
        self.user_confidence_label.grid(row=4, column=0, padx=15, pady=2, sticky="w")
        
        self.user_age_label = ctk.CTkLabel(
            user_card,
            text="Approx Age: --",
            font=ctk.CTkFont(size=13),
            anchor="w"
        )
        self.user_age_label.grid(row=5, column=0, padx=15, pady=2, sticky="w")
        
        self.user_emotion_label = ctk.CTkLabel(
            user_card,
            text="Emotion: --",
            font=ctk.CTkFont(size=13),
            anchor="w"
        )
        self.user_emotion_label.grid(row=6, column=0, padx=15, pady=(2, 15), sticky="w")
        
        # Activity log
        log_card = ctk.CTkFrame(info_panel)
        log_card.grid(row=1, column=0, padx=10, pady=(5, 10), sticky="nsew")
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            log_card,
            text="📋 Recent Activity",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=15, pady=(15, 10), sticky="w")
        
        # Text widget with scrollbar
        self.log_text = ctk.CTkTextbox(
            log_card,
            font=ctk.CTkFont(size=12),
            wrap="word"
        )
        self.log_text.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        
        info_panel.grid_rowconfigure(1, weight=1)
    
    def setup_chat_tab(self):
        """Chatbot tab with modern design"""
        
        # Clear existing widgets
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        
        # Configure grid
        self.chat_frame.grid_columnconfigure(0, weight=1)
        self.chat_frame.grid_rowconfigure(0, weight=1)
        
        # Chat container
        chat_container = ctk.CTkFrame(self.chat_frame)
        chat_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        chat_container.grid_columnconfigure(0, weight=1)
        chat_container.grid_rowconfigure(0, weight=1)
        
        # Chat history
        self.chat_history = ctk.CTkTextbox(
            chat_container,
            font=ctk.CTkFont(size=13),
            wrap="word"
        )
        self.chat_history.grid(row=0, column=0, padx=15, pady=(15, 5), sticky="nsew")
        
        # Configure tags for colored text (using customtkinter doesn't support tags, so we'll insert plain text)
        
        # Input area
        input_frame = ctk.CTkFrame(chat_container, fg_color="transparent")
        input_frame.grid(row=1, column=0, padx=15, pady=15, sticky="ew")
        input_frame.grid_columnconfigure(0, weight=1)
        
        self.chat_input = ctk.CTkEntry(
            input_frame,
            placeholder_text="Type your message here...",
            font=ctk.CTkFont(size=13),
            height=40
        )
        self.chat_input.grid(row=0, column=0, padx=(0, 10), sticky="ew")
        self.chat_input.bind('<Return>', lambda e: self.send_message())
        
        self.send_btn = ctk.CTkButton(
            input_frame,
            text="Send",
            command=self.send_message,
            width=100,
            height=40
        )
        self.send_btn.grid(row=0, column=1, padx=0)
        
        # Clear button
        self.clear_btn = ctk.CTkButton(
            chat_container,
            text="Clear Chat",
            command=self.clear_chat,
            fg_color="transparent",
            border_width=1,
            border_color=("gray50", "gray50"),
            text_color=("gray10", "gray90"),
            height=35
        )
        self.clear_btn.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="w")

        if self.startup_notes:
            self.insert_chat_message("System startup diagnostics:\n")
            for note in self.startup_notes[-8:]:
                self.insert_chat_message(f"{note}\n")
            self.insert_chat_message("\n")
            self.startup_notes = []
    
    def setup_voice_tab(self):
        """Voice assistant tab with modern design"""
        
        # Clear existing widgets
        for widget in self.voice_frame.winfo_children():
            widget.destroy()
        
        # Center content
        self.voice_frame.grid_columnconfigure(0, weight=1)
        self.voice_frame.grid_rowconfigure(0, weight=1)
        
        # Voice card
        voice_card = ctk.CTkFrame(self.voice_frame, width=500, height=400)
        voice_card.grid(row=0, column=0, padx=50, pady=50)
        voice_card.grid_columnconfigure(0, weight=1)
        voice_card.grid_propagate(False)
        
        # Voice icon
        icon_label = ctk.CTkLabel(
            voice_card,
            text="🎤",
            font=ctk.CTkFont(size=72)
        )
        icon_label.grid(row=0, column=0, padx=20, pady=(40, 20))
        
        # Title
        ctk.CTkLabel(
            voice_card,
            text="Voice Assistant",
            font=ctk.CTkFont(size=24, weight="bold")
        ).grid(row=1, column=0, padx=20, pady=10)
        
        # Status
        self.voice_status_label = ctk.CTkLabel(
            voice_card,
            text="Status: Stopped",
            font=ctk.CTkFont(size=14),
            text_color=("gray70", "gray70")
        )
        self.voice_status_label.grid(row=2, column=0, padx=20, pady=5)
        
        # Control buttons
        button_frame = ctk.CTkFrame(voice_card, fg_color="transparent")
        button_frame.grid(row=3, column=0, padx=20, pady=30)
        
        self.voice_start_btn = ctk.CTkButton(
            button_frame,
            text="▶ Start Listening",
            command=self.start_voice,
            fg_color="green",
            hover_color="darkgreen",
            width=180,
            height=45,
            font=ctk.CTkFont(size=14)
        )
        self.voice_start_btn.grid(row=0, column=0, padx=5)
        
        self.voice_stop_btn = ctk.CTkButton(
            button_frame,
            text="⏹ Stop Listening",
            command=self.stop_voice,
            fg_color="red",
            hover_color="darkred",
            width=180,
            height=45,
            font=ctk.CTkFont(size=14)
        )
        self.voice_stop_btn.grid(row=0, column=1, padx=5)
        
        # Command hint
        ctk.CTkLabel(
            voice_card,
            text="Say 'Jarvis' followed by your command | Press Space to toggle listening",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray50")
        ).grid(row=4, column=0, padx=20, pady=(0, 40))
    
    def setup_dashboard_tab(self):
        """Dashboard tab with modern design and charts"""
        
        # Clear existing widgets
        for widget in self.dashboard_frame.winfo_children():
            widget.destroy()
        
        # Configure grid
        self.dashboard_frame.grid_columnconfigure((0, 1), weight=1)
        self.dashboard_frame.grid_rowconfigure(1, weight=1)
        
        # Stats cards
        stats_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        stats_frame.grid(row=0, column=0, columnspan=2, padx=0, pady=(0, 15), sticky="ew")
        stats_frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Total users card
        user_card = ctk.CTkFrame(stats_frame, corner_radius=15)
        user_card.grid(row=0, column=0, padx=5, sticky="nsew")
        
        ctk.CTkLabel(
            user_card,
            text="Total Users",
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray50")
        ).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        self.total_users_label = ctk.CTkLabel(
            user_card,
            text="0",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        self.total_users_label.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
        # Today's attendance card
        attendance_card = ctk.CTkFrame(stats_frame, corner_radius=15)
        attendance_card.grid(row=0, column=1, padx=5, sticky="nsew")
        
        ctk.CTkLabel(
            attendance_card,
            text="Today's Attendance",
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray50")
        ).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        self.today_attendance_label = ctk.CTkLabel(
            attendance_card,
            text="0",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        self.today_attendance_label.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
        # Unknown faces card
        unknown_card = ctk.CTkFrame(stats_frame, corner_radius=15)
        unknown_card.grid(row=0, column=2, padx=5, sticky="nsew")
        
        ctk.CTkLabel(
            unknown_card,
            text="Unknown Faces",
            font=ctk.CTkFont(size=14),
            text_color=("gray50", "gray50")
        ).grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        self.unknown_label = ctk.CTkLabel(
            unknown_card,
            text="0",
            font=ctk.CTkFont(size=32, weight="bold")
        )
        self.unknown_label.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
        # Recent activity table
        activity_frame = ctk.CTkFrame(self.dashboard_frame)
        activity_frame.grid(row=1, column=0, columnspan=2, padx=0, pady=0, sticky="nsew")
        activity_frame.grid_columnconfigure(0, weight=1)
        activity_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            activity_frame,
            text="Recent Activity",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")
        
        # Treeview for activity (using ttk Treeview as customtkinter doesn't have one)
        tree_frame = ctk.CTkFrame(activity_frame)
        tree_frame.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        # Create treeview with scrollbar
        columns = ('Time', 'User', 'Action', 'Confidence')
        self.activity_tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show='headings',
            height=12
        )
        
        # Configure treeview style
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview", 
                        background="#2b2b2b",
                        foreground="white",
                        fieldbackground="#2b2b2b")
        style.configure("Treeview.Heading", 
                        background="#1f1f1f",
                        foreground="white")
        
        for col in columns:
            self.activity_tree.heading(col, text=col)
            self.activity_tree.column(col, width=150)
        
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.activity_tree.yview)
        self.activity_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.activity_tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll.grid(row=0, column=1, sticky="ns")
        
        # Refresh button
        ctk.CTkButton(
            activity_frame,
            text="🔄 Refresh Dashboard",
            command=self.refresh_dashboard,
            height=40
        ).grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        # Initial load
        self.refresh_dashboard()
    
    def update_time(self):
        """Update time in status bar"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.configure(text=current_time)
        self.window.after(1000, self.update_time)
    
    def handle_voice_input(self, text):
        """Handle voice input"""
        if "jarvis" not in text.lower():
            return
        
        # Show message in chat
        self.window.after(0, lambda: self.insert_chat_message(f"You (Voice): {text}\n"))
        
        threading.Thread(
            target=self.get_chat_response,
            args=(text,),
            daemon=True
        ).start()
    
    def insert_chat_message(self, message, is_user=True):
        """Insert message into chat history"""
        if hasattr(self, 'chat_history'):
            self.chat_history.insert("end", message)
            self.chat_history.see("end")

    def post_startup_note(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        note = f"[Startup {timestamp}] {message}"
        self.startup_notes.append(note)
        print(note)
        if hasattr(self, 'chat_history'):
            self.insert_chat_message(f"System: {message}\n")

    def run_startup_checks(self):
        threading.Thread(target=self._startup_checks_worker, daemon=True).start()

    def _startup_checks_worker(self):
        missing = []
        for env_name in ["SUPABASE_URL", "SUPABASE_KEY", "GROQ_API_KEY"]:
            if not os.getenv(env_name):
                missing.append(env_name)

        if missing:
            msg = f"Missing env vars: {', '.join(missing)}"
            self.window.after(0, lambda m=msg: self.post_startup_note(m))
        else:
            self.window.after(0, lambda: self.post_startup_note("Environment variables loaded."))

        deepface_enabled = bool(getattr(self.face_recognizer, "demographics_enabled", False))
        if deepface_enabled:
            self.window.after(0, lambda: self.post_startup_note("Age/Emotion model is available."))
        else:
            self.window.after(0, lambda: self.post_startup_note("Age/Emotion disabled (install deepface)."))

        try:
            r = requests.get("http://127.0.0.1:8000/health", timeout=3)
            if r.ok:
                data = r.json()
                groq_on_server = data.get("groq_key_configured", False)
                msg = f"AI server online. GROQ key on server: {'yes' if groq_on_server else 'no'}."
                self.window.after(0, lambda m=msg: self.post_startup_note(m))
            else:
                msg = f"AI server health failed (HTTP {r.status_code})."
                self.window.after(0, lambda m=msg: self.post_startup_note(m))
        except Exception:
            self.window.after(
                0,
                lambda: self.post_startup_note("AI server unreachable. Start: uvicorn app:app --reload (ai_server)")
            )

    def handle_space_voice_toggle(self, event):
        """Toggle voice assistant on Space key press."""
        widget = event.widget
        if isinstance(widget, (ctk.CTkEntry, ctk.CTkTextbox, tk.Entry, tk.Text)):
            return

        now_ts = time.time()
        if now_ts - self.last_space_toggle_ts < self.space_toggle_debounce_sec:
            return "break"

        self.last_space_toggle_ts = now_ts
        self.toggle_voice_assistant()
        return "break"

    def toggle_voice_assistant(self):
        if getattr(self.voice, "running", False):
            self.stop_voice()
        else:
            self.start_voice()
    
    def start_camera(self):
        """Start video capture"""
        if self.running:
            self.status_label.configure(text="● Camera is already running")
            return
        
        try:
            from mobile_camera import MobileCamera
            self.camera = MobileCamera(camera_type="auto")
            
            if not self.camera.connect():
                messagebox.showerror("Camera Error", "Unable to connect to built-in camera or Iriun webcam.")
                return
            
            self.running = True
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.camera_status_label.configure(text="📷 Camera: On")
            source = getattr(self.camera, "connected_source", "unknown")
            self.status_label.configure(text=f"● Camera active ({source})")
            
            self.video_thread = threading.Thread(target=self.process_video, daemon=True)
            self.video_thread.start()
            
        except Exception as e:
            messagebox.showerror("Camera Error", f"An error occurred while starting the camera: {str(e)}")
    
    def stop_camera(self):
        """Stop video capture"""
        if not self.running:
            self.status_label.configure(text="● Camera is already stopped")
            return
        
        self.running = False
        time.sleep(0.1)
        
        if hasattr(self, 'camera') and self.camera:
            self.camera.release()
            self.camera = None
        
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.camera_status_label.configure(text="📷 Camera: Off")
        self.status_label.configure(text="● Camera stopped")
        
        # Clear video display
        self.video_label.configure(text="Camera Feed\n\nClick 'Start Camera' to begin")
    
    def process_video(self):
        """Process video frames"""
        while self.running:
            try:
                if hasattr(self, 'camera') and self.camera:
                    ret, frame = self.camera.get_frame()
                    if ret and frame is not None:
                        processed_frame, user_info = self.face_recognizer.process_frame(frame)
                        self.window.after(0, self.update_video_display, processed_frame, user_info)
            except Exception as e:
                print(f"Video processing error: {e}")
            
            time.sleep(0.03)
    
    def update_video_display(self, frame, user_info):
        """Update video display"""
        try:
            now = time.time()
            
            # Convert frame for display
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(frame_rgb)
            
            # Resize to fit label while maintaining aspect ratio
            label_width = self.video_label.winfo_width()
            label_height = self.video_label.winfo_height()
            
            if label_width > 1 and label_height > 1:
                img_ratio = img.width / img.height
                label_ratio = label_width / label_height
                
                if img_ratio > label_ratio:
                    new_width = label_width
                    new_height = int(label_width / img_ratio)
                else:
                    new_height = label_height
                    new_width = int(label_height * img_ratio)
                
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            imgtk = ImageTk.PhotoImage(image=img)
            
            # Update video label
            self.video_label.configure(image=imgtk, text="")
            self.video_label.image = imgtk
            
            # Update user info
            if user_info:
                self.current_user = user_info
                self.update_user_info(user_info)
                self.maybe_greet_user(user_info, now)
                
                # Update sidebar user info
                self.sidebar_user_name.configure(text=user_info['name'])
                self.sidebar_user_status.configure(text="● Online", text_color="green")
                
                # Log attendance
                self.db.log_attendance(user_info['id'], 'login', user_info['confidence'])
                self.add_to_log(f"✅ {user_info['name']} recognized")
                
        except Exception as e:
            print(f"Display error: {e}")
    
    def maybe_greet_user(self, user_info, now_ts):
        """Greet user if conditions met"""
        user_name = user_info.get("name")
        if not user_name:
            return
        
        user_id = user_info.get("id")
        user_key = user_id if user_id is not None else f"name:{str(user_name).strip().lower()}"
        was_absent = (now_ts - self.last_detection_ts) > self.absence_reset_sec
        switched_user = user_key != self.active_user_id
        last_greeted_ts = self.last_greeted_at.get(user_key, 0.0)
        cooldown_over = (now_ts - last_greeted_ts) >= self.greeting_cooldown_sec
        
        if (switched_user or was_absent) and cooldown_over:
            greeting = f"Welcome {user_name}. Good to see you."
            threading.Thread(target=self.voice.speak, args=(greeting,), daemon=True).start()
            self.add_to_log(f"Greeted {user_name}")
            self.status_label.configure(text=f"● Greeted {user_name}")
            self.last_greeted_at[user_key] = now_ts
        
        self.active_user_id = user_key
        self.last_detection_ts = now_ts
    
    def update_user_info(self, user_info):
        """Update user info display"""
        self.user_name_label.configure(text=f"Name: {user_info['name']}")
        self.user_email_label.configure(text=f"Email: {user_info.get('email', '--')}")
        self.user_dept_label.configure(text=f"Department: {user_info.get('department', '--')}")
        self.user_confidence_label.configure(text=f"Confidence: {user_info['confidence']:.2%}")
        self.user_age_label.configure(text=f"Approx Age: {user_info.get('age', '--')}")
        self.user_emotion_label.configure(text=f"Emotion: {user_info.get('emotion', '--')}")
    
    def add_to_log(self, message):
        """Add message to activity log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
    
    def send_message(self):
        """Send message to chatbot"""
        message = self.chat_input.get().strip()
        if not message:
            return
        
        # Display user message
        self.insert_chat_message(f"You: {message}\n\n")
        
        # Clear input
        self.chat_input.delete(0, "end")
        
        # Get response in separate thread
        threading.Thread(target=self.get_chat_response, args=(message,), daemon=True).start()
    
    def get_chat_response(self, message):
        """Get chatbot response"""
        try:
            user_id = self.current_user['id'] if self.current_user else None
            recent_memory = self.db.get_recent_chat_memory(user_id=user_id, limit=12)
            payload = {
                "text": message,
                "user_id": user_id,
                "user_name": self.current_user.get("name") if self.current_user else None,
                "history": recent_memory
            }

            try:
                response = requests.post(
                    "http://127.0.0.1:8000/process",
                    json=payload
                    
                )
            except requests.exceptions.Timeout:
                # Retry once with minimal context to reduce LLM latency.
                response = requests.post(
                    "http://127.0.0.1:8000/process",
                    json={
                        "text": message,
                        "user_id": user_id,
                        "user_name": self.current_user.get("name") if self.current_user else None,
                        "history": []
                    }
                )

            if not response.ok:
                self.window.after(
                    0,
                    self.display_chat_response,
                    f"Error: AI server HTTP {response.status_code}: {response.text[:180]}"
                )
                return

            try:
                data = response.json()
            except ValueError:
                self.window.after(
                    0,
                    self.display_chat_response,
                    f"Error: AI server returned invalid JSON: {response.text[:180]}"
                )
                return

            print("Intent Engine Response:", data)
            
            if data.get("type") == "tool":
                tool_name = data.get("tool")
                args = data.get("args", {})
                
                result = self.tool_manager.execute(tool_name, args)
                self.db.save_chat_message(user_id, message, result)
                
                self.window.after(0, self.display_chat_response, result)
                if tool_name != "stop_voice_assistant":
                    self.window.after(0, lambda: self.voice.speak(result))
                return
            
            elif data.get("type") == "chat":
                result = data.get("response", "No response")
                self.db.save_chat_message(user_id, message, result)
                
                self.window.after(0, self.display_chat_response, result)
                self.window.after(0, lambda: self.voice.speak(result))
                return
        
        except requests.exceptions.ConnectionError:
            self.window.after(
                0,
                self.display_chat_response,
                "Error: AI server is not running. Start it from ai_server with: uvicorn app:app --reload"
            )
        except requests.exceptions.Timeout:
            self.window.after(
                0,
                self.display_chat_response,
                "Error: AI server request timed out."
            )
        except Exception as e:
            self.window.after(0, self.display_chat_response, f"Error: {str(e)}")
    
    def display_chat_response(self, response):
        """Display chatbot response"""
        self.insert_chat_message(f"Jarvis: {response}\n\n")
    
    def clear_chat(self):
        """Clear chat history"""
        if hasattr(self, 'chat_history'):
            self.chat_history.delete("1.0", "end")
    
    def switch_panel(self, panel_name):
        """Switch between panels"""
        tab_map = {
            "face": self.show_face_tab,
            "chat": self.show_chat_tab,
            "voice": self.show_voice_tab,
            "dashboard": self.show_dashboard_tab
        }
        
        func = tab_map.get(panel_name)
        if func:
            self.window.after(0, func)
    
    def start_camera_from_voice(self):
        """Start camera from voice command"""
        self.window.after(0, self.start_camera)
    
    def stop_camera_from_voice(self):
        """Stop camera from voice command"""
        self.window.after(0, self.stop_camera)
    
    def stop_voice_from_voice(self):
        """Stop voice assistant from voice command"""
        self.window.after(0, self.stop_voice)
    
    def start_voice(self):
        """Start voice assistant"""
        if getattr(self.voice, "running", False):
            self.voice_status_label.configure(text="Status: Listening...")
            return
        try:
            self.voice.start()
        except Exception as e:
            self.voice_status_label.configure(text="Status: Error")
            self.status_label.configure(text=f"Voice start failed: {str(e)}")
            self.display_chat_response(f"Error: Voice start failed: {str(e)}")
            return
        self.voice_status_label.configure(text="Status: Listening...")
        self.status_label.configure(text="● Voice Assistant Active")
    
    def stop_voice(self):
        """Stop voice assistant"""
        if not getattr(self.voice, "running", False):
            self.voice_status_label.configure(text="Status: Stopped")
            return
        self.voice.stop()
        self.voice_status_label.configure(text="Status: Stopped")
        self.status_label.configure(text="● Voice Assistant Stopped")
    
    def refresh_dashboard(self):
        """Refresh dashboard statistics"""
        try:
            # Get total users
            users = self.db.supabase.table('users').select('*', count='exact').execute()
            self.total_users_label.configure(text=str(users.count))
            
            # Get today's attendance
            today = datetime.now().date().isoformat()
            attendance = self.db.supabase.table('attendance_logs') \
                .select('*', count='exact') \
                .gte('timestamp', f"{today}T00:00:00") \
                .lte('timestamp', f"{today}T23:59:59") \
                .execute()
            self.today_attendance_label.configure(text=str(attendance.count))
            
            # Get unknown faces
            unknown = self.db.supabase.table('attendance_logs') \
                .select('*', count='exact') \
                .eq('action', 'unknown_face') \
                .execute()
            self.unknown_label.configure(text=str(unknown.count))
            
            # Update activity tree
            recent = self.db.get_recent_activity(10)
            for item in self.activity_tree.get_children():
                self.activity_tree.delete(item)
            
            for log in recent:
                self.activity_tree.insert('', 'end', values=(
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
        time.sleep(0.2)
        
        if hasattr(self, 'camera') and self.camera:
            self.camera.release()
        
        if hasattr(self, 'voice'):
            self.voice.stop()
        
        self.window.destroy()
    
    def run(self):
        """Run the application"""
        self.window.mainloop()

if __name__ == "__main__":
    app = FaceTalkAI()
    app.run()
