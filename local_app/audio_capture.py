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

        # Get device info
        device_index = 11  # Realtek WASAPI
        device_info = sd.query_devices(device_index, 'input')

        # Use the device's default sample rate
        self.sample_rate = int(device_info['default_samplerate'])

        print(f"Starting audio stream on device {device_index}")
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

    def read(self):
        return self.audio_queue.get()
