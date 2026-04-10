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
import re
from voice_module import VoiceAssistant
from tool_manager import ToolManager
from intent_engine import IntentEngine
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import json
from mobile_remote_server import MobileRemoteServer
from config import Config

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
            groq_api_key=os.getenv("GROQ_API_KEY"),
            on_unknown_face_callback=self.handle_unknown_face_enrollment
        )
        self.intent_engine = IntentEngine(api_key=os.getenv("GROQ_API_KEY"))
        
        # Initialize voice assistant
        self.voice = VoiceAssistant(
            on_speech_callback=self.handle_voice_input,
            voice_type="male"
        )
        self.mobile_mic_active = False
        self.resume_desktop_voice_after_mobile = False
        self.current_language = "english"
        
        self.tool_manager = ToolManager(
            switch_panel_callback=self.switch_panel,
            start_camera_callback=self.start_camera_from_voice,
            stop_camera_callback=self.stop_camera_from_voice,
            stop_voice_callback=self.stop_voice_from_voice,
            start_voice_callback=self.start_voice_from_remote,
            set_language_callback=self.set_assistant_language
        )
        
        # Initialize Mobile Remote Server for controlling from phone
        self.mobile_server = None
        if getattr(Config, 'ENABLE_MOBILE_REMOTE', True):
            self.mobile_server = MobileRemoteServer(
                host=getattr(Config, 'REMOTE_SERVER_HOST', '0.0.0.0'),
                port=getattr(Config, 'REMOTE_SERVER_PORT', 8888),
                tool_manager=self.tool_manager,
                command_callback=self.handle_mobile_command,
                status_callback=self.get_mobile_status,
                audio_callback=self.handle_mobile_audio,
                mobile_mic_callback=self.handle_mobile_mic_state
            )
            self.mobile_server.start()
        
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
        self.attendance_log_cooldown_sec = 20
        self.last_space_toggle_ts = 0.0
        self.space_toggle_debounce_sec = 0.35
        self.startup_notes = []
        self.last_attendance_log_at = {}
        self.enrollment_dialog_open = False
        self.last_unknown_prompt_ts = 0.0
        self.unknown_prompt_cooldown_sec = 12
        self.response_generation = 0
        
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
            ("Face Recognition", self.show_face_tab, 2),
            ("AI Chatbot", self.show_chat_tab, 3),
            ("Voice Assistant", self.show_voice_tab, 4),
            ("Dashboard", self.show_dashboard_tab, 5),
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
            text="Camera: Off",
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
            text="Start Camera",
            command=self.start_camera,
            fg_color="green",
            hover_color="darkgreen",
            height=40
        )
        self.start_btn.grid(row=0, column=0, padx=5, sticky="ew")
        
        self.stop_btn = ctk.CTkButton(
            control_frame,
            text="Stop Camera",
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
            text="User Information",
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
            text="Recent Activity",
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

        self.load_saved_chat_history()

        if self.startup_notes:
            self.insert_chat_message("System startup diagnostics:\n")
            for note in self.startup_notes[-8:]:
                self.insert_chat_message(f"{note}\n")
            self.insert_chat_message("\n")
            self.startup_notes = []

    def load_saved_chat_history(self):
        """Load saved chat history from Supabase into the chat window."""
        if not hasattr(self, 'chat_history'):
            return

        try:
            user_id = self.current_user['id'] if self.current_user else None
            history = self.db.get_chat_history(user_id=user_id, limit=100)
            if not history:
                return

            self.chat_history.delete("1.0", "end")
            for item in history:
                message = (item.get("message") or "").strip()
                response = (item.get("response") or "").strip()
                if message:
                    self.insert_chat_message(f"You: {message}\n\n")
                if response:
                    self.insert_chat_message(f"Jarvis: {response}\n\n")
        except Exception as e:
            print(f"Chat history load error: {e}")
    
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
            text="Voice",
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
            text="Status: Listening..." if getattr(self.voice, "running", False) else "Status: Stopped",
            font=ctk.CTkFont(size=14),
            text_color=("gray70", "gray70")
        )
        self.voice_status_label.grid(row=2, column=0, padx=20, pady=5)
        
        # Control buttons
        button_frame = ctk.CTkFrame(voice_card, fg_color="transparent")
        button_frame.grid(row=3, column=0, padx=20, pady=30)
        
        self.voice_start_btn = ctk.CTkButton(
            button_frame,
            text="Start Listening",
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
            text="Stop Listening",
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

    def update_voice_status_ui(self, status_text):
        if hasattr(self, "voice_status_label") and self.voice_status_label.winfo_exists():
            self.voice_status_label.configure(text=status_text)
    
    def setup_dashboard_tab(self):
        """Dashboard tab with modern design and charts"""
        
        # Clear existing widgets
        for widget in self.dashboard_frame.winfo_children():
            widget.destroy()
        
        # Configure grid
        self.dashboard_frame.grid_columnconfigure((0, 1), weight=1)
        self.dashboard_frame.grid_rowconfigure(1, weight=1)
        self.dashboard_frame.grid_rowconfigure(2, weight=1)
        
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
            text="Refresh Dashboard",
            command=self.refresh_dashboard,
            height=40
        ).grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")

        diagnostics_frame = ctk.CTkFrame(self.dashboard_frame)
        diagnostics_frame.grid(row=2, column=0, columnspan=2, padx=0, pady=(15, 0), sticky="nsew")
        diagnostics_frame.grid_columnconfigure(0, weight=1)
        diagnostics_frame.grid_rowconfigure(1, weight=1)

        header_frame = ctk.CTkFrame(diagnostics_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header_frame,
            text="Safe Tool Test",
            font=ctk.CTkFont(size=18, weight="bold")
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header_frame,
            text="Run Tool Test",
            command=self.run_safe_tool_test,
            height=36,
            width=150
        ).grid(row=0, column=1, sticky="e")

        self.tool_test_output = ctk.CTkTextbox(
            diagnostics_frame,
            font=ctk.CTkFont(size=12),
            wrap="word"
        )
        self.tool_test_output.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.tool_test_output.insert("end", "Run the safe tool test to check audio devices, window targets, and non-destructive tool availability.\n")
        self.tool_test_output.configure(state="disabled")

        # Initial load
        self.refresh_dashboard()

    def run_safe_tool_test(self):
        """Run a non-destructive tool diagnostic and show the results in the dashboard."""
        if not hasattr(self, "tool_test_output"):
            return

        self.tool_test_output.configure(state="normal")
        self.tool_test_output.delete("1.0", "end")
        self.tool_test_output.insert("end", "Running safe tool test...\n")
        self.tool_test_output.configure(state="disabled")

        def worker():
            try:
                report = self.tool_manager.diagnostic_report()
                lines = [
                    f"Registered tools: {report.get('tool_count', 0)}",
                    "",
                    "Audio inputs:",
                ]

                audio_inputs = report.get("audio_inputs", [])
                if audio_inputs:
                    lines.extend([f"- {name}" for name in audio_inputs[:12]])
                else:
                    lines.append("- No input devices detected")

                lines.append("")
                lines.append("Visible windows sample:")
                window_titles = report.get("windows_titles_sample", [])
                if window_titles:
                    lines.extend([f"- {title}" for title in window_titles[:10]])
                else:
                    lines.append("- No visible windows detected")

                lines.append("")
                lines.append("Basic app command checks:")
                for name, result in report.get("app_checks", {}).items():
                    status = "OK" if result.get("ok") else "FAIL"
                    output = str(result.get("output", "") or "").strip()
                    lines.append(f"- {name}: {status}")
                    if output:
                        lines.append(f"  {output}")

                iriun_inputs = [name for name in audio_inputs if "iriun" in name.lower()]
                lines.append("")
                if iriun_inputs:
                    lines.append("Iriun audio detected:")
                    lines.extend([f"- {name}" for name in iriun_inputs])
                else:
                    lines.append("Iriun audio not detected.")

                report_text = "\n".join(lines)
            except Exception as e:
                report_text = f"Tool test failed: {str(e)}"

            def update_ui():
                self.tool_test_output.configure(state="normal")
                self.tool_test_output.delete("1.0", "end")
                self.tool_test_output.insert("end", report_text)
                self.tool_test_output.configure(state="disabled")

            self.window.after(0, update_ui)

        threading.Thread(target=worker, daemon=True).start()
    
    def update_time(self):
        """Update time in status bar"""
        current_time = datetime.now().strftime("%H:%M:%S")
        self.time_label.configure(text=current_time)
        self.window.after(1000, self.update_time)
    
    def handle_mobile_command(self, command):
        """Handle commands received from mobile remote control"""
        print(f"Processing mobile command: {command}")
        user_id = self.current_user['id'] if self.current_user else None

        try:
            self.window.after(0, lambda: self.insert_chat_message(f"Mobile: {command}\n"))
            response = self.process_chat_message(command, source="chat")
            self.window.after(0, lambda r=response: self.display_chat_response(r))
            return response
        except Exception as e:
            error_msg = f"Error processing command: {str(e)}"
            self.db.save_chat_message(user_id, f"[Mobile] {command}", error_msg)
            print(error_msg)
            return error_msg

    def handle_voice_input(self, text, source="desktop"):
        """Handle voice input"""
        cleaned = (text or "").strip()
        if not cleaned:
            return

        lowered_cleaned = cleaned.lower()
        if "jarvis" not in lowered_cleaned and lowered_cleaned not in {"stop", "stop talking", "stop speaking", "stop response"}:
            return

        normalized = re.sub(r"\b(?:hey|ok|okay)?\s*jarvis\b[:,]?\s*", "", cleaned, count=1, flags=re.IGNORECASE).strip()
        if not normalized:
            normalized = cleaned

        if len(normalized) < 2:
            return

        lowered = normalized.lower()
        if lowered in {"stop", "stop talking", "stop speaking", "stop response"}:
            self.interrupt_current_response()
            self.window.after(0, lambda: self.insert_chat_message("System: Response interrupted.\n"))
            return

        speaker_label = "You (Mobile Voice)" if source == "mobile" else "You (Voice)"
        self.window.after(0, lambda m=normalized, label=speaker_label: self.insert_chat_message(f"{label}: {m}\n"))
        
        threading.Thread(
            target=self.get_chat_response,
            args=(normalized, "voice"),
            daemon=True
        ).start()

    def handle_mobile_mic_state(self, active):
        active = bool(active)
        if active == self.mobile_mic_active:
            return {"mobile_mic_active": self.mobile_mic_active}

        self.mobile_mic_active = active
        if active:
            self.resume_desktop_voice_after_mobile = bool(getattr(self.voice, "running", False))
            if getattr(self.voice, "running", False):
                self.window.after(0, self.stop_voice)
            self.window.after(0, lambda: self.update_voice_status_ui("Status: Mobile mic active"))
            self.window.after(0, lambda: self.status_label.configure(text="● Mobile mic priority active"))
        else:
            should_resume = self.resume_desktop_voice_after_mobile
            self.resume_desktop_voice_after_mobile = False
            if should_resume:
                self.window.after(0, self.start_voice)
            else:
                self.window.after(0, lambda: self.update_voice_status_ui("Status: Stopped"))
                self.window.after(0, lambda: self.status_label.configure(text="● Mobile mic released"))

        return {"mobile_mic_active": self.mobile_mic_active}

    def handle_mobile_audio(self, audio_bytes, filename=None, content_type=None):
        suffix = os.path.splitext(filename or "")[1] or ".webm"
        try:
            transcript = self.voice.transcribe_bytes(audio_bytes, suffix=suffix)
            transcript = (transcript or "").strip()
            if not transcript:
                return {"status": "error", "response": "No speech detected from mobile audio."}

            self.window.after(0, lambda t=transcript: self.insert_chat_message(f"You (Mobile Voice): {t}\n"))
            response_text = self.process_chat_message(transcript, source="voice")
            self.window.after(0, lambda r=response_text: self.display_chat_response(r))
            if response_text:
                self.window.after(0, lambda r=response_text: self.voice.speak(r))
            return {"status": "success", "transcript": transcript, "response": response_text}
        except Exception as e:
            error_message = f"Mobile audio error: {str(e)}"
            print(error_message)
            return {"status": "error", "response": error_message}

    def interrupt_current_response(self):
        self.response_generation += 1
        try:
            self.voice.stop_speaking()
        except Exception as e:
            print(f"Interrupt error: {e}")
        self.window.after(0, lambda: self.status_label.configure(text="● Response interrupted"))

    def set_assistant_language(self, language):
        language_map = {
            "english": "english",
            "eng": "english",
            "en": "english",
            "hindi": "hindi",
            "hind": "hindi",
            "hi": "hindi",
        }
        normalized = language_map.get(str(language or "").strip().lower())
        if not normalized:
            return "Supported languages are English and Hindi."

        self.current_language = normalized
        label = normalized.capitalize()
        self.window.after(0, lambda l=label: self.status_label.configure(text=f"● Language switched to {l}"))
        self.window.after(0, lambda l=label: self.post_startup_note(f"Assistant language set to {l}."))
        return f"Language switched to {label}."
    
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

    def get_mobile_status(self):
        mobile_url = None
        if self.mobile_server and getattr(self.mobile_server, "is_running", False):
            mobile_url = f"http://{self.mobile_server.get_local_ip()}:{self.mobile_server.port}"

        audio_device = {}
        try:
            audio_device = self.voice.audio_cap.get_device_info()
        except Exception:
            audio_device = {}

        return {
            "voice_running": bool(getattr(self.voice, "running", False)),
            "camera_running": bool(self.running),
            "current_user": self.current_user.get("name") if self.current_user else None,
            "mobile_url": mobile_url,
            "mobile_mic_active": self.mobile_mic_active,
            "desktop_audio_device": audio_device.get("device_name")
        }

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
            diagnostics = self.tool_manager.diagnostic_report()
            audio_inputs = diagnostics.get("audio_inputs", [])
            windows_titles = diagnostics.get("windows_titles_sample", [])
            iriun_audio = [name for name in audio_inputs if "iriun" in name.lower()]
            if iriun_audio:
                self.window.after(0, lambda names=", ".join(iriun_audio): self.post_startup_note(f"Iriun audio detected: {names}"))
            elif audio_inputs:
                sample_inputs = ", ".join(audio_inputs[:5])
                self.window.after(0, lambda names=sample_inputs: self.post_startup_note(f"Audio inputs: {names}"))

            if windows_titles:
                sample_titles = ", ".join(windows_titles[:4])
                self.window.after(0, lambda titles=sample_titles: self.post_startup_note(f"Visible windows sample: {titles}"))
        except Exception as e:
            self.window.after(0, lambda err=str(e): self.post_startup_note(f"Tool diagnostics error: {err}"))

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
            self.camera_status_label.configure(text="Camera: On")
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
        self.camera_status_label.configure(text="Camera: Off")
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

            if user_info:
                previous_user_id = self.current_user.get("id") if self.current_user else None
                self.current_user = user_info
                self.update_user_info(user_info)
                self.maybe_greet_user(user_info, now)
                self.sidebar_user_name.configure(text=user_info["name"])
                self.sidebar_user_status.configure(text="● Online", text_color="green")
                self.log_user_detection(user_info, now)
                if hasattr(self, 'chat_history') and previous_user_id != user_info.get("id"):
                    self.load_saved_chat_history()
            elif (now - self.last_detection_ts) > self.absence_reset_sec:
                self.active_user_id = None
                self.current_user = None
                self.sidebar_user_name.configure(text="Not Logged In")
                self.sidebar_user_status.configure(text="● Offline", text_color="gray50")
                if hasattr(self, 'chat_history'):
                    self.load_saved_chat_history()

        except Exception as e:
            print(f"Display error: {e}")

    def log_user_detection(self, user_info, now_ts):
        user_id = user_info.get("id")
        if user_id is None or str(user_id).startswith("pending_"):
            return

        last_logged_ts = self.last_attendance_log_at.get(user_id, 0.0)
        if (now_ts - last_logged_ts) < self.attendance_log_cooldown_sec:
            return

        self.db.log_attendance(user_id, "login", user_info.get("confidence"))
        self.last_attendance_log_at[user_id] = now_ts
        self.add_to_log(f"Recognized {user_info['name']} ({user_info.get('department', '--')})")
    
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

        # Display emotion with confidence score
        emotion = user_info.get('emotion', '--')
        emotion_scores = user_info.get('emotion_scores', {})

        if emotion and emotion != '--' and emotion_scores:
            # Get the confidence of the detected emotion
            emotion_confidence = emotion_scores.get(emotion, 0)
            emotion_text = f"Emotion: {emotion.capitalize()} ({emotion_confidence:.0f}%)"
        else:
            emotion_text = f"Emotion: {emotion if emotion else '--'}"

        self.user_emotion_label.configure(text=emotion_text)
    
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

    def process_chat_message(self, message, source="chat"):
        """Run the AI/tool pipeline and return the final response text."""
        user_id = self.current_user['id'] if self.current_user else None
        lowered_message = str(message or "").strip().lower()
        if lowered_message in {"jarvis stop", "stop", "stop talking", "stop speaking", "stop response"}:
            self.interrupt_current_response()
            result = "Stopping current response."
            self.db.save_chat_message(user_id, message, result)
            return result

        try:
            recent_memory = self.db.get_recent_chat_memory(user_id=user_id, limit=12)
        except Exception:
            recent_memory = []

        payload = {
            "text": message,
            "user_id": user_id,
            "user_name": self.current_user.get("name") if self.current_user else None,
            "history": recent_memory,
            "language": self.current_language
        }

        try:
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/process",
                    json=payload,
                    timeout=20
                )
            except requests.exceptions.Timeout:
                response = requests.post(
                    "http://127.0.0.1:8000/process",
                    json={
                        "text": message,
                        "user_id": user_id,
                        "user_name": self.current_user.get("name") if self.current_user else None,
                        "history": [],
                        "language": self.current_language
                    },
                    timeout=20
                )

            if not response.ok:
                result = f"Error: AI server HTTP {response.status_code}: {response.text[:180]}"
                self.db.save_chat_message(user_id, message, result)
                return result

            try:
                data = response.json()
            except ValueError:
                result = f"Error: AI server returned invalid JSON: {response.text[:180]}"
                self.db.save_chat_message(user_id, message, result)
                return result

            print("Intent Engine Response:", data)

            if data.get("type") == "tool":
                tool_name = data.get("tool")
                args = data.get("args", {})
                result = self.tool_manager.execute(tool_name, args)
                self.db.save_chat_message(user_id, message, result)
                if source == "voice":
                    self.db.save_voice_command(user_id, message, result, True)
                return result

            result = data.get("response", "No response")
            self.db.save_chat_message(user_id, message, result)
            if source == "voice":
                self.db.save_voice_command(user_id, message, result, True)
            return result

        except requests.exceptions.ConnectionError:
            result = "Error: AI server is not running. Start it from ai_server with: uvicorn app:app --reload"
        except requests.exceptions.Timeout:
            result = "Error: AI server request timed out."
        except Exception as e:
            result = f"Error: {str(e)}"

        self.db.save_chat_message(user_id, message, result)
        return result

    def get_chat_response(self, message, source="chat"):
        """Get chatbot response"""
        generation = self.response_generation
        result = self.process_chat_message(message, source=source)
        if generation != self.response_generation:
            return
        self.window.after(0, self.display_chat_response, result)
        if result and "stop_voice_assistant" not in result.lower():
            self.window.after(0, lambda r=result: self.voice.speak(r))
    
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

    def start_voice_from_remote(self):
        """Start voice assistant from remote command"""
        self.window.after(0, self.start_voice)
    
    def start_voice(self):
        """Start voice assistant"""
        if self.mobile_mic_active:
            self.update_voice_status_ui("Status: Mobile mic active")
            self.status_label.configure(text="● Mobile mic has priority over desktop mic")
            return
        if getattr(self.voice, "running", False):
            self.update_voice_status_ui("Status: Listening...")
            return
        try:
            self.voice.start()
        except Exception as e:
            self.update_voice_status_ui("Status: Error")
            self.status_label.configure(text=f"Voice start failed: {str(e)}")
            self.display_chat_response(f"Error: Voice start failed: {str(e)}")
            return
        self.update_voice_status_ui("Status: Listening...")
        self.status_label.configure(text="● Voice Assistant Active")
    
    def stop_voice(self):
        """Stop voice assistant"""
        if not getattr(self.voice, "running", False):
            if self.mobile_mic_active:
                self.update_voice_status_ui("Status: Mobile mic active")
            else:
                self.update_voice_status_ui("Status: Stopped")
            return
        self.voice.stop()
        if self.mobile_mic_active:
            self.update_voice_status_ui("Status: Mobile mic active")
            self.status_label.configure(text="● Desktop mic paused for mobile mic")
        else:
            self.update_voice_status_ui("Status: Stopped")
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

        # Stop mobile remote server
        if hasattr(self, 'mobile_server') and self.mobile_server:
            self.mobile_server.stop()

        self.window.destroy()

    def handle_unknown_face_enrollment(self, face_data):
        """Handle unknown face detection and ask for details once per cooldown."""
        now_ts = time.time()
        if self.enrollment_dialog_open:
            return
        if (now_ts - self.last_unknown_prompt_ts) < self.unknown_prompt_cooldown_sec:
            return

        self.enrollment_dialog_open = True
        self.last_unknown_prompt_ts = now_ts

        def show_enrollment_dialog():
            dialog = ctk.CTkToplevel(self.window)
            dialog.title("New Person Detected")
            dialog.geometry("400x500")
            dialog.resizable(False, False)
            dialog.grab_set()

            dialog.transient(self.window)
            dialog.update_idletasks()
            x = self.window.winfo_x() + (self.window.winfo_width() // 2) - 200
            y = self.window.winfo_y() + (self.window.winfo_height() // 2) - 250
            dialog.geometry(f"+{x}+{y}")

            self.status_label.configure(text="● New person detected. Waiting for details.")
            self.add_to_log("New person detected. Asking for name and details.")
            self.window.after(0, lambda: self.voice.speak("I found a new person. Please enter your name and details so I can remember you next time."))

            def close_dialog():
                self.enrollment_dialog_open = False
                dialog.destroy()

            dialog.protocol("WM_DELETE_WINDOW", close_dialog)

            ctk.CTkLabel(
                dialog,
                text="New Person Detected",
                font=ctk.CTkFont(size=18, weight="bold")
            ).pack(padx=20, pady=(20, 10))

            ctk.CTkLabel(
                dialog,
                text="Please provide your details so the system can remember you",
                font=ctk.CTkFont(size=12),
                text_color="gray70"
            ).pack(padx=20, pady=(0, 20))

            form_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            form_frame.pack(padx=20, pady=0, fill="both", expand=True)

            ctk.CTkLabel(form_frame, text="Name:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10, 0))
            name_entry = ctk.CTkEntry(form_frame, placeholder_text="Enter your name", height=35)
            name_entry.pack(fill="x", pady=(5, 15))

            ctk.CTkLabel(form_frame, text="Email:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10, 0))
            email_entry = ctk.CTkEntry(form_frame, placeholder_text="Enter your email (optional)", height=35)
            email_entry.pack(fill="x", pady=(5, 15))

            ctk.CTkLabel(form_frame, text="Department:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10, 0))
            dept_entry = ctk.CTkEntry(form_frame, placeholder_text="Enter your department or details", height=35)
            dept_entry.pack(fill="x", pady=(5, 15))

            def save_enrollment():
                name = name_entry.get().strip()
                email = email_entry.get().strip() or None
                department = dept_entry.get().strip() or None

                if not name:
                    messagebox.showwarning("Missing Name", "Please enter your name")
                    return

                def enroll():
                    try:
                        user_id = self.db.add_user(
                            name=name,
                            face_encoding=face_data["face_encoding"],
                            email=email,
                            department=department or "General",
                            profile_image=face_data.get("profile_image")
                        )

                        if user_id:
                            self.face_recognizer.load_known_faces()
                            self.insert_chat_message(f"System: Welcome {name}. Your face and details have been saved.\n")
                            self.window.after(0, lambda: self.voice.speak(f"Welcome {name}. I will remember you from now on."))
                            self.window.after(0, lambda: self.status_label.configure(text=f"● Saved new person: {name}"))
                            self.add_to_log(f"Saved new person profile for {name}")
                        else:
                            self.insert_chat_message(f"System: Failed to register {name}. Please try again.\n")
                    except Exception as e:
                        print(f"Enrollment error: {e}")
                        self.insert_chat_message(f"System: Error during registration: {str(e)}\n")
                    finally:
                        self.enrollment_dialog_open = False

                threading.Thread(target=enroll, daemon=True).start()
                dialog.destroy()

            def skip_enrollment():
                self.enrollment_dialog_open = False
                self.add_to_log("Skipped new person enrollment")
                dialog.destroy()

            button_frame = ctk.CTkFrame(dialog, fg_color="transparent")
            button_frame.pack(padx=20, pady=(20, 20), fill="x")

            save_btn = ctk.CTkButton(
                button_frame,
                text="Save & Remember",
                command=save_enrollment,
                fg_color="green",
                hover_color="darkgreen",
                height=40
            )
            save_btn.pack(side="left", padx=(0, 10), fill="x", expand=True)

            skip_btn = ctk.CTkButton(
                button_frame,
                text="Skip",
                command=skip_enrollment,
                fg_color="transparent",
                border_width=1,
                border_color="gray50",
                height=40
            )
            skip_btn.pack(side="left", fill="x", expand=True)

            name_entry.focus()

        self.window.after(100, show_enrollment_dialog)
    
    def run(self):
        """Run the application"""
        self.window.mainloop()

if __name__ == "__main__":
    app = FaceTalkAI()
    app.run()


