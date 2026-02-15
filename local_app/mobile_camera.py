# mobile_camera.py
import cv2
import numpy as np
import urllib.request
import threading
import time

class MobileCamera:
    """
    Handle mobile camera connections (Iriun Webcam, IP Webcam)
    """
    
    def __init__(self, camera_type="iriun", ip_address=None, port=8080):
        self.camera_type = camera_type
        self.ip_address = ip_address
        self.port = port
        self.cap = None
        self.is_running = False
        self.frame = None
        self.lock = threading.Lock()
        
    def connect(self):
        """Connect to mobile camera"""
        try:
            if self.camera_type == "iriun":
                return self._connect_iriun()
            elif self.camera_type == "ipwebcam":
                return self._connect_ipwebcam()
            else:
                print(f"❌ Unknown camera type: {self.camera_type}")
                return False
        except Exception as e:
            print(f"❌ Connection error: {e}")
            return False
    
    def _connect_iriun(self):
        """Connect to Iriun Webcam (appears as local webcam)"""
        print("🔍 Looking for Iriun Webcam...")
        
        # Try common indices
        for i in range(3):
            self.cap = cv2.VideoCapture(i)
            if self.cap.isOpened():
                # Test read
                ret, test_frame = self.cap.read()
                if ret and test_frame is not None:
                    print(f"✅ Iriun connected at index {i}")
                    self.is_running = True
                    
                    # Start capture thread
                    self.thread = threading.Thread(target=self._update_frame)
                    self.thread.daemon = True
                    self.thread.start()
                    
                    return True
                self.cap.release()
        
        print("❌ Iriun not found. Make sure it's running on phone and PC")
        return False
    
    def _connect_ipwebcam(self):
        """Connect to IP Webcam Android app"""
        if not self.ip_address:
            print("❌ IP address required for IP Webcam")
            return False
        
        url = f"http://{self.ip_address}:{self.port}/video"
        self.cap = cv2.VideoCapture(url)
        
        if self.cap.isOpened():
            print(f"✅ IP Webcam connected at {url}")
            self.is_running = True
            
            # Start capture thread
            self.thread = threading.Thread(target=self._update_frame)
            self.thread.daemon = True
            self.thread.start()
            
            return True
        return False
    
    def _update_frame(self):
        """Continuously update frame in background"""
        while self.is_running and self.cap:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
            time.sleep(0.03)  # ~30 FPS
    
    def get_frame(self):
        """Get latest frame"""
        with self.lock:
            if self.frame is not None:
                return True, self.frame.copy()
            return False, None
    
    def release(self):
        """Release camera"""
        self.is_running = False
        if self.cap:
            self.cap.release()
        print("📱 Camera released")