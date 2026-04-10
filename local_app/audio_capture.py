import sounddevice as sd
import numpy as np
import queue

class AudioCapture:
    def __init__(self, frame_duration_ms=30):
        self.sample_rate = None  # Will be set when stream starts
        self.frame_duration_ms = frame_duration_ms
        self.block_size = None # Will be calculated based on sample rate
        self.audio_queue = queue.Queue()
        self.running = False
        self.stream = None
        self.device_index = None
        self.device_name = None

    def _callback(self, indata, frames, time, status):
        if status:
            print(f"Audio Status: {status}")
        self.audio_queue.put(indata.copy())

    def _pick_input_device(self):
        try:
            devices = sd.query_devices()
        except Exception:
            devices = []

        iriun_candidates = []
        other_candidates = []

        for index, device in enumerate(devices):
            max_input_channels = int(device.get("max_input_channels", 0) or 0)
            if max_input_channels <= 0:
                continue

            name = str(device.get("name", "") or "")
            lowered = name.lower()
            if "iriun" in lowered:
                iriun_candidates.append((index, name))
            else:
                other_candidates.append((index, name))

        if iriun_candidates:
            return iriun_candidates[0]

        try:
            default_input = sd.default.device[0]
            if default_input is not None and int(default_input) >= 0:
                device = sd.query_devices(int(default_input), "input")
                return int(default_input), str(device.get("name", "default input"))
        except Exception:
            pass

        if other_candidates:
            return other_candidates[0]

        return None, None

    def start(self):
        self.running = True

        device_index, device_name = self._pick_input_device()
        self.device_index = device_index
        self.device_name = device_name or "default"

        try:
            device_info = sd.query_devices(device_index, "input")
        except Exception:
            device_index = None
            self.device_index = None
            self.device_name = "default"
            device_info = sd.query_devices(None, "input")

        # Use the device's default sample rate
        self.sample_rate = int(device_info["default_samplerate"])

        print(f"Starting audio stream on device {device_index if device_index is not None else 'default'}")
        print(f"Input device name: {self.device_name}")
        print(f"Using sample rate: {self.sample_rate}")

        self.stream = sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            blocksize=int(self.sample_rate * self.frame_duration_ms / 1000),
            callback=self._callback,
            device=device_index
        )

        self.stream.start()
        print("Audio stream started successfully.")


    def stop(self):
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None

        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break

    def get_device_info(self):
        return {
            "device_index": self.device_index,
            "device_name": self.device_name,
            "sample_rate": self.sample_rate,
        }

    def read(self):
        return self.audio_queue.get()
