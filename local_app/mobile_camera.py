import cv2
import threading
import time


class MobileCamera:
    """
    Camera connector with source priority support.
    Optimized for speed with reduced latency frame capture.

    camera_type options:
    - "auto": prefer Iriun webcam first, then fallback to local camera
    - "local": local camera only
    - "iriun": prefer Iriun webcam (RECOMMENDED)
    - "ipwebcam": Android IP Webcam URL
    """

    def __init__(self, camera_type="iriun", ip_address=None, port=8080, target_fps=60):
        self.camera_type = camera_type
        self.ip_address = ip_address
        self.port = port
        self.target_fps = target_fps
        self.frame_delay = 1.0 / target_fps  # Dynamic delay based on target FPS
        self.cap = None
        self.is_running = False
        self.frame = None
        self.lock = threading.Lock()
        self.connected_source = None
        self.thread = None
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.actual_fps = 0

    def connect(self):
        try:
            if self.camera_type == "auto":
                return self._connect_auto()
            if self.camera_type == "local":
                return self._connect_local(prefer_non_iriun=False)
            if self.camera_type == "iriun":
                return self._connect_iriun()
            if self.camera_type == "ipwebcam":
                return self._connect_ipwebcam()
            print(f"Unknown camera type: {self.camera_type}")
            return False
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def _list_windows_camera_names(self):
        """
        Optional device-name enumeration on Windows.
        Uses pygrabber if installed; otherwise returns [].
        """
        try:
            from pygrabber.dshow_graph import FilterGraph
            graph = FilterGraph()
            devices = graph.get_input_devices()
            return devices if devices else []
        except Exception:
            return []

    def _open_index(self, index):
        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            cap.release()
            return None

        ret, frame = cap.read()
        if not ret or frame is None:
            cap.release()
            return None
        return cap

    def _start_capture_thread(self):
        self.is_running = True
        self.thread = threading.Thread(target=self._update_frame, daemon=True)
        self.thread.start()

    def _connect_auto(self):
        # PRIORITY: Try Iriun first (better quality mobile camera)
        print("Trying Iriun webcam first (priority)...")
        if self._connect_iriun():
            return True

        print("Iriun not available. Trying local camera...")
        return self._connect_local(prefer_non_iriun=True)

    def _connect_local(self, prefer_non_iriun=False):
        device_names = self._list_windows_camera_names()
        index_order = list(range(6))

        if prefer_non_iriun and device_names:
            non_iriun = []
            iriun = []
            for i in range(min(6, len(device_names))):
                name = (device_names[i] or "").lower()
                if "iriun" in name:
                    iriun.append(i)
                else:
                    non_iriun.append(i)
            index_order = non_iriun + iriun + [i for i in index_order if i not in (non_iriun + iriun)]

        for i in index_order:
            cap = self._open_index(i)
            if cap is not None:
                self.cap = cap
                self.connected_source = f"local:{i}"
                print(f"Local camera connected at index {i}")
                self._start_capture_thread()
                return True

        print("No local camera found")
        return False

    def _connect_iriun(self):
        print("Looking for Iriun webcam...")
        device_names = self._list_windows_camera_names()

        preferred = []
        if device_names:
            preferred = [i for i, name in enumerate(device_names[:6]) if "iriun" in (name or "").lower()]

        scan_order = preferred + [i for i in range(6) if i not in preferred]
        for i in scan_order:
            cap = self._open_index(i)
            if cap is not None:
                self.cap = cap
                self.connected_source = f"iriun:{i}"
                print(f"Iriun connected at index {i}")
                self._start_capture_thread()
                return True

        print("Iriun not found")
        return False

    def _connect_ipwebcam(self):
        if not self.ip_address:
            print("IP address required for IP Webcam")
            return False

        url = f"http://{self.ip_address}:{self.port}/video"
        self.cap = cv2.VideoCapture(url)
        if self.cap.isOpened():
            self.connected_source = "ipwebcam"
            print(f"IP webcam connected at {url}")
            self._start_capture_thread()
            return True
        return False

    def _update_frame(self):
        """Optimized frame capture with minimal latency"""
        while self.is_running and self.cap:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
                self.frame_count += 1
                
                # Calculate actual FPS every second
                now = time.time()
                if now - self.last_fps_time >= 1.0:
                    self.actual_fps = self.frame_count / (now - self.last_fps_time)
                    self.frame_count = 0
                    self.last_fps_time = now
            
            # Minimal sleep - just yield to other threads (faster than 0.03s)
            time.sleep(0.005)  # 5ms delay = up to 200 FPS potential

    def get_frame(self):
        with self.lock:
            if self.frame is not None:
                return True, self.frame.copy()
            return False, None

    def release(self):
        self.is_running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        print("Camera released")

    def get_fps(self):
        """Return current actual FPS"""
        return self.actual_fps
