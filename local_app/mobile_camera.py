import cv2
import threading
import time


class MobileCamera:
    """
    Camera connector with source priority support.

    camera_type options:
    - "auto": prefer built-in/local camera, then fallback to Iriun
    - "local": local camera only
    - "iriun": prefer Iriun webcam
    - "ipwebcam": Android IP Webcam URL
    """

    def __init__(self, camera_type="iriun", ip_address=None, port=8080):
        self.camera_type = camera_type
        self.ip_address = ip_address
        self.port = port
        self.cap = None
        self.is_running = False
        self.frame = None
        self.lock = threading.Lock()
        self.connected_source = None
        self.thread = None

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
        print("Trying built-in/local camera first...")
        if self._connect_local(prefer_non_iriun=True):
            return True

        print("Local camera not available. Trying Iriun...")
        return self._connect_iriun()

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
        while self.is_running and self.cap:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
            time.sleep(0.03)

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
