# voice_module.py
import os
import queue
import tempfile
import threading
import time

import numpy as np
import soundfile as sf
from groq import Groq

from audio_capture import AudioCapture
from tts_service import TTSService


class VoiceAssistant:
    def __init__(self, on_speech_callback=None, voice_type="female"):
        self.audio_cap = AudioCapture()
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.tts = TTSService(voice_type=voice_type)
        self.on_speech_callback = on_speech_callback
        self.voice_type = voice_type

        self.running = False
        self.thread = None
        self.is_speaking = False
        self.tts_queue = queue.Queue()
        self.tts_worker_running = True
        self.tts_worker = None
        self.tts_worker_error_count = 0
        self.current_response_cancelled = False
        self._start_tts_worker()

    def start(self):
        if self.running:
            print("Voice Assistant already running.")
            return

        print("Starting Voice Assistant...")
        self.running = True
        self._clear_audio_queue()
        self.audio_cap.start()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def stop(self):
        print("Stopping Voice Assistant...")
        self.running = False
        self.audio_cap.stop()
        self.is_speaking = False
        self._clear_audio_queue()
        self.stop_speaking()

    def _start_tts_worker(self):
        if self.tts_worker is not None and self.tts_worker.is_alive():
            return

        self.tts_worker = threading.Thread(target=self._tts_worker_loop, daemon=True)
        self.tts_worker.start()
        print("TTS worker thread started")

    def _clear_audio_queue(self):
        while not self.audio_cap.audio_queue.empty():
            try:
                self.audio_cap.audio_queue.get_nowait()
            except Exception:
                break

    def set_voice_type(self, voice_type):
        self.voice_type = (voice_type or "female").lower()
        self.tts.set_voice_type(self.voice_type)

    def _run_loop(self):
        audio_buffer = np.array([], dtype=np.float32)
        capture_rate = self.audio_cap.sample_rate
        target_rate = 16000

        silence_threshold = 0.02
        silence_duration_ms = 1000
        consecutive_silence_samples = 0
        speech_detected = False

        print("Voice Assistant listening...")

        while self.running:
            try:
                chunk = self.audio_cap.audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            chunk = chunk.flatten()
            chunk_amplitude = np.max(np.abs(chunk))

            if chunk_amplitude > silence_threshold:
                speech_detected = True
                consecutive_silence_samples = 0
                audio_buffer = np.concatenate((audio_buffer, chunk))
            else:
                if speech_detected:
                    consecutive_silence_samples += len(chunk)
                    audio_buffer = np.concatenate((audio_buffer, chunk))
                    silence_duration = (consecutive_silence_samples / capture_rate) * 1000

                    if silence_duration > silence_duration_ms and len(audio_buffer) > capture_rate * 0.5:
                        self._process_audio_buffer(audio_buffer, capture_rate, target_rate)
                        audio_buffer = np.array([], dtype=np.float32)
                        speech_detected = False
                        consecutive_silence_samples = 0

            if len(audio_buffer) > capture_rate * 10 and speech_detected:
                self._process_audio_buffer(audio_buffer, capture_rate, target_rate)
                audio_buffer = np.array([], dtype=np.float32)
                speech_detected = False
                consecutive_silence_samples = 0

    def _process_audio_buffer(self, audio_buffer, capture_rate, target_rate):
        print("Transcribing...")
        temp_path = tempfile.mktemp(suffix=".wav")
        try:
            # Keep the original sample rate to avoid SciPy/librosa native dependency issues.
            sf.write(temp_path, audio_buffer, capture_rate)
            user_text = self.transcribe_file(temp_path)
            if user_text:
                print("[Voice Input]:", user_text)
                if self.on_speech_callback:
                    self.on_speech_callback(user_text)
        except Exception as e:
            print(f"Transcription error: {e}")
        finally:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass

    def transcribe_file(self, file_path):
        with open(file_path, "rb") as audio_file:
            transcription = self.client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3-turbo",
            )
        return (transcription.text or "").strip()

    def transcribe_bytes(self, audio_bytes, suffix=".webm"):
        temp_path = tempfile.mktemp(suffix=suffix)
        try:
            with open(temp_path, "wb") as temp_file:
                temp_file.write(audio_bytes)
            return self.transcribe_file(temp_path)
        finally:
            try:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass
    
    # stop speaking method to clear TTS queue and stop current speech immediately
    def stop_speaking(self):
        self.current_response_cancelled = True
        try:
            while not self.tts_queue.empty():
                self.tts_queue.get_nowait()
        except Exception:
            pass
        try:
            self.tts.stop()
        except Exception as e:
            print(f"Voice stop_speaking error: {e}")
        self.is_speaking = False

    # speak method
    def speak(self, text):
        if not text:
            return

        self.current_response_cancelled = False
        if self.tts_worker is None or not self.tts_worker.is_alive():
            self._start_tts_worker()

        self.tts_queue.put(str(text))

    # if TTS Stop working 
    def _tts_worker_loop(self):
        while self.tts_worker_running:
            try:
                text = self.tts_queue.get(timeout=0.2)
                self._speak_now(text)
                self.tts_worker_error_count = 0
            except queue.Empty:
                continue
            except Exception as e:
                print(f"TTS Worker Error: {e}")
                self.tts_worker_error_count += 1
                if self.tts_worker_error_count > 5:
                    print("TTS Worker crashed too many times, restarting...")
                    self.tts_worker_error_count = 0
                    try:
                        self.tts = TTSService(voice_type=self.voice_type)
                    except Exception as reinit_error:
                        print(f"TTS reinitialize failed: {reinit_error}")

    def _speak_now(self, text):
        self.is_speaking = True
        try:
            self._clear_audio_queue()
            time.sleep(0.1)
            if self.current_response_cancelled:
                return
            self.tts.speak(text)
            self._clear_audio_queue()
        except Exception as e:
            print(f"TTS speak error: {e}")
        finally:
            self.is_speaking = False
            print("Listening again...")
