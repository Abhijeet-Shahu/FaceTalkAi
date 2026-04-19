# config.py
"""
Configuration file for FaceTalk AI
Load environment variables and configuration settings
"""

import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

class Config:
    """Main configuration class"""
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv('SUPABASE_URL', '')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')
    
    # Groq API Configuration
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'mixtral-8x7b-32768')
    
    # Database Configuration
    DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'supabase')  # 'supabase' or 'sqlite'
    SQLITE_DB_PATH = os.getenv('SQLITE_DB_PATH', 'facetalk_local.db')
    
    # Face Recognition Settings
    FACE_RECOGNITION_TOLERANCE = float(os.getenv('FACE_RECOGNITION_TOLERANCE', '0.6'))
    FACE_DETECTION_MODEL = os.getenv('FACE_DETECTION_MODEL', 'hog')  # 'hog' or 'cnn'
    FACE_UPSAMPLE_TIMES = int(os.getenv('FACE_UPSAMPLE_TIMES', '1'))
    FACE_ENCODING_JITTER = int(os.getenv('FACE_ENCODING_JITTER', '1'))
    
    # Camera Settings
    CAMERA_TYPE = os.getenv('CAMERA_TYPE', 'iriun')  # 'iriun', 'ipwebcam', 'droidcam'
    CAMERA_IP = os.getenv('CAMERA_IP', '192.168.1.100')
    CAMERA_PORT = int(os.getenv('CAMERA_PORT', '8080'))
    CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', '640'))
    CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', '480'))
    CAMERA_FPS = int(os.getenv('CAMERA_FPS', '60'))  # Increased default FPS
    
    # Performance Settings
    FRAME_SKIP = int(os.getenv('FRAME_SKIP', '2'))  # Process every Nth frame (1=all, 2=faster)
    FACE_SCALE_FACTOR = float(os.getenv('FACE_SCALE_FACTOR', '0.25'))  # Downscale for detection
    
    # Mobile Remote Control Settings
    REMOTE_SERVER_HOST = os.getenv('REMOTE_SERVER_HOST', '0.0.0.0')  # Listen on all interfaces
    REMOTE_SERVER_PORT = int(os.getenv('REMOTE_SERVER_PORT', '8888'))  # Port for mobile commands
    ENABLE_MOBILE_REMOTE = os.getenv('ENABLE_MOBILE_REMOTE', 'True').lower() == 'true'
    
    # UI Settings
    WINDOW_WIDTH = int(os.getenv('WINDOW_WIDTH', '1280'))
    WINDOW_HEIGHT = int(os.getenv('WINDOW_HEIGHT', '720'))
    UI_THEME = os.getenv('UI_THEME', 'dark')
    UI_FONT_SIZE = int(os.getenv('UI_FONT_SIZE', '10'))
    
    # Application Settings
    APP_NAME = "FaceTalk AI"
    APP_VERSION = "1.0.0"
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'False').lower() == 'true'

    # Voice & TTS Settings
    VOICE_TYPE = os.getenv('VOICE_TYPE', 'female')  # 'male' or 'female'
    VOICE_RATE = int(os.getenv('VOICE_RATE', '145'))  # Softer default female pace
    VOICE_VOLUME = float(os.getenv('VOICE_VOLUME', '0.72'))  # Softer voice volume (0.0-1.0)
    ENABLE_CASUAL_CHAT = os.getenv('ENABLE_CASUAL_CHAT', 'True').lower() == 'true'

    # Emotion Detection Settings
    EMOTION_DETECTION_ENABLED = os.getenv('EMOTION_DETECTION_ENABLED', 'True').lower() == 'true'
    EMOTION_CACHE_TTL = int(os.getenv('EMOTION_CACHE_TTL', '15'))  # Cache emotion for N seconds
    
    # Paths
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATASET_PATH = os.path.join(BASE_DIR, 'dataset')
    ENCODINGS_PATH = os.path.join(BASE_DIR, 'encodings')
    TEMP_PATH = os.path.join(BASE_DIR, 'temp')
    LOGS_PATH = os.path.join(BASE_DIR, 'logs')
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        missing = []
        
        if cls.DATABASE_TYPE == 'supabase':
            if not cls.SUPABASE_URL:
                missing.append('SUPABASE_URL')
            if not cls.SUPABASE_KEY:
                missing.append('SUPABASE_KEY')
        
        if not cls.GROQ_API_KEY:
            missing.append('GROQ_API_KEY')
        
        if missing:
            print(f"⚠️ Missing configuration: {', '.join(missing)}")
            return False
        return True
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories"""
        directories = [cls.DATASET_PATH, cls.ENCODINGS_PATH, 
                      cls.TEMP_PATH, cls.LOGS_PATH]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"📁 Created directory: {directory}")
    
    @classmethod
    def print_config(cls):
        """Print current configuration"""
        print("\n" + "="*50)
        print(f"{cls.APP_NAME} v{cls.APP_VERSION} Configuration")
        print("="*50)
        print(f"Database Type: {cls.DATABASE_TYPE}")
        print(f"Camera Type: {cls.CAMERA_TYPE}")
        print(f"Resolution: {cls.CAMERA_WIDTH}x{cls.CAMERA_HEIGHT}")
        print(f"Face Model: {cls.FACE_DETECTION_MODEL}")
        print(f"Tolerance: {cls.FACE_RECOGNITION_TOLERANCE}")
        print(f"UI Theme: {cls.UI_THEME}")
        print(f"Voice Type: {cls.VOICE_TYPE}")
        print(f"Casual Chat: {cls.ENABLE_CASUAL_CHAT}")
        print(f"Debug Mode: {cls.DEBUG_MODE}")
        print("="*50 + "\n")


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG_MODE = True
    FACE_UPSAMPLE_TIMES = 1


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG_MODE = False
    FACE_UPSAMPLE_TIMES = 0  # Faster in production


# Select configuration based on environment
env = os.getenv('FLASK_ENV', 'development')
if env == 'production':
    config = ProductionConfig
else:
    config = DevelopmentConfig
