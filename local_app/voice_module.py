# voice_module.py
import threading
import numpy as np
import queue
import time
from audio_capture import AudioCapture
from tts_service import TTSService

from groq import Groq
import tempfile
import soundfile as sf
import os


class VoiceAssistant:
    def __init__(self, on_speech_callback=None):
        """
        on_speech_callback:
            A function that will receive the final transcribed text.
            Example:
                self.handle_user_message(text)
        """

        # Audio + STT
        self.audio_cap = AudioCapture()
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))

        # TTS (for speaking responses)
        self.tts = TTSService()

        # Callback to main app
        self.on_speech_callback = on_speech_callback

        # Control flags
        self.running = False
        self.thread = None
        self.is_speaking = False
        self.tts_queue = queue.Queue()
        self.tts_worker_running = True
        self.tts_worker = threading.Thread(target=self._tts_worker_loop, daemon=True)
        self.tts_worker.start()

    # ---------------------------
    # Start Voice Assistant
    # ---------------------------
    def start(self):
        if self.running:
            print("Voice Assistant already running.")
            return

        print("Starting Voice Assistant...")
        self.running = True

        self.audio_cap.start()

        self.thread = threading.Thread(
            target=self._run_loop,
            daemon=True
        )
        self.thread.start()

    # ---------------------------
    # Stop Voice Assistant
    # ---------------------------
    def stop(self):
        print("Stopping Voice Assistant...")
        self.running = False
        self.audio_cap.stop()

    # ---------------------------
    # Internal Processing Loop
    # ---------------------------
    def _run_loop(self):
        audio_buffer = np.array([], dtype=np.float32)

        # Use actual device sample rate (44100)
        CAPTURE_RATE = self.audio_cap.sample_rate
        TARGET_RATE = 16000

        SILENCE_THRESHOLD = 0.02  # Slightly higher threshold
        SILENCE_DURATION_MS = 1000  # 1 seconds of silence = end of speech
        consecutive_silence_samples = 0
        speech_detected = False

        print("Voice Assistant listening...")

        while self.running:
            try:
                chunk = self.audio_cap.audio_queue.get(timeout=0.1)
                if self.is_speaking:
                    # Clear queue while speaking
                    continue
            except queue.Empty:
                continue

            chunk = chunk.flatten()
            
            # Check if speech is happening (amplitude high)
            chunk_amplitude = np.max(np.abs(chunk))
            
            if chunk_amplitude > SILENCE_THRESHOLD:
                # Speech detected
                speech_detected = True
                consecutive_silence_samples = 0
                audio_buffer = np.concatenate((audio_buffer, chunk))
            else:
                # Silence detected
                if speech_detected:
                    consecutive_silence_samples += len(chunk)
                    audio_buffer = np.concatenate((audio_buffer, chunk))
                    
                    # Calculate silence duration
                    silence_duration = (consecutive_silence_samples / CAPTURE_RATE) * 1000
                    
                    # If silence is long enough and we have enough audio, process it
                    if silence_duration > SILENCE_DURATION_MS and len(audio_buffer) > CAPTURE_RATE * 0.5:  # At least 0.5 seconds
                        self._process_audio_buffer(audio_buffer, CAPTURE_RATE, TARGET_RATE)
                        audio_buffer = np.array([], dtype=np.float32)
                        speech_detected = False
                        consecutive_silence_samples = 0
                else:
                    # No speech detected yet, just continue
                    pass

            # Safety: If buffer gets too large (10 seconds), process it anyway
            if len(audio_buffer) > CAPTURE_RATE * 10:
                if speech_detected:
                    self._process_audio_buffer(audio_buffer, CAPTURE_RATE, TARGET_RATE)
                    audio_buffer = np.array([], dtype=np.float32)
                    speech_detected = False
                    consecutive_silence_samples = 0

    def _process_audio_buffer(self, audio_buffer, CAPTURE_RATE, TARGET_RATE):
        print("Transcribing...")

        try:
            # 🔥 Resample properly before saving
            import librosa
            audio_resampled = librosa.resample(
                audio_buffer,
                orig_sr=CAPTURE_RATE,
                target_sr=TARGET_RATE
            )

            # Create filename ONLY (no open handle)
            temp_path = tempfile.mktemp(suffix=".wav")

            # Save file
            sf.write(temp_path, audio_resampled, TARGET_RATE)

            # Transcribe
            with open(temp_path, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3-turbo"
                )

            user_text = transcription.text.strip()

            # Delete file AFTER closing it
            os.remove(temp_path)

            if user_text:
                print("[Voice Input]:", user_text)
                if self.on_speech_callback:
                    self.on_speech_callback(user_text)

        except Exception as e:
            print(f"Transcription error: {e}")
    
    # ---------------------------
    # Speak Response
    # ---------------------------
    def speak(self, text):
        """
        Queue text for TTS playback.
        """
        if not text:
            return
        self.tts_queue.put(str(text))

    def _tts_worker_loop(self):
        while self.tts_worker_running:
            try:
                text = self.tts_queue.get(timeout=0.2)
            except queue.Empty:
                continue
            self._speak_now(text)

    def _speak_now(self, text):
        self.is_speaking = True
        try:
            # Clear the audio queue to avoid processing our own voice
            while not self.audio_cap.audio_queue.empty():
                try:
                    self.audio_cap.audio_queue.get_nowait()
                except Exception:
                    break

            time.sleep(0.1)
            self.tts.speak(text)

            while not self.audio_cap.audio_queue.empty():
                try:
                    self.audio_cap.audio_queue.get_nowait()
                except Exception:
                    break
        except Exception as e:
            print(f"TTS speak error: {e}")
        finally:
            self.is_speaking = False
            print("Listening again...")
