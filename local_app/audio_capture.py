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

    def _callback(self, indata, frames, time, status):
        if status:
            print(f"Audio Status: {status}")
        self.audio_queue.put(indata.copy())

    def start(self):
        self.running = True

        try:
            default_input = sd.default.device[0]
        except Exception:
            default_input = None

        device_index = default_input if default_input is not None and default_input >= 0 else None

        try:
            device_info = sd.query_devices(device_index, "input")
        except Exception:
            device_index = None
            device_info = sd.query_devices(None, "input")

        # Use the device's default sample rate
        self.sample_rate = int(device_info["default_samplerate"])

        print(f"Starting audio stream on device {device_index if device_index is not None else 'default'}")
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

    def read(self):
        return self.audio_queue.get()
