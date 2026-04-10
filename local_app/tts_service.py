import threading

import pyttsx3
from dotenv import load_dotenv

load_dotenv()


class TTSService:
    def __init__(self, model="tts-1", voice="alloy", voice_type="female"):
        self.model = model
        self.voice = voice
        self.voice_type = (voice_type or "female").lower()
        self._engine = None
        self._engine_thread_id = None
        self._lock = threading.RLock()

    def set_voice_type(self, voice_type):
        requested = (voice_type or "female").lower()
        if requested not in {"male", "female"}:
            requested = "female"

        with self._lock:
            if requested != self.voice_type:
                self.voice_type = requested
                self._reset_engine()

    def _reset_engine(self):
        if self._engine is not None:
            try:
                self._engine.stop()
            except Exception:
                pass

        self._engine = None
        self._engine_thread_id = None

    def _get_engine(self):
        current_thread_id = threading.get_ident()

        if self._engine is None or self._engine_thread_id != current_thread_id:
            self._reset_engine()
            self._engine = pyttsx3.init()
            self._engine_thread_id = current_thread_id
            self._configure_engine()

        return self._engine

    def _configure_engine(self):
        if self.voice_type == "male":
            self._set_male_voice()
        else:
            self._set_female_voice()

        self._apply_voice_tuning()

    def _set_female_voice(self):
        try:
            voices = self._engine.getProperty("voices")
            female_voice = None
            for voice in voices:
                voice_name = voice.name.lower()
                if any(kw in voice_name for kw in ["zira", "female", "woman", "hazel", "susan", "linda", "microsoft zira"]):
                    female_voice = voice
                    break

            if female_voice is None and len(voices) > 1:
                female_voice = voices[1]

            if female_voice:
                self._engine.setProperty("voice", female_voice.id)
                print(f"TTS: using female voice - {female_voice.name}")
        except Exception as e:
            print(f"TTS female voice setup error: {e}")

    def _set_male_voice(self):
        try:
            voices = self._engine.getProperty("voices")
            male_voice = None
            for voice in voices:
                voice_name = voice.name.lower()
                if any(kw in voice_name for kw in ["david", "male", "man", "mark", "james", "microsoft david"]):
                    male_voice = voice
                    break

            if male_voice is None and len(voices) > 0:
                male_voice = voices[0]

            if male_voice:
                self._engine.setProperty("voice", male_voice.id)
                print(f"TTS: using male voice - {male_voice.name}")
        except Exception as e:
            print(f"TTS male voice setup error: {e}")

    def _apply_voice_tuning(self):
        try:
            from config import Config

            default_rate = 145 if self.voice_type == "male" else 165
            default_volume = 0.78 if self.voice_type == "male" else 0.9
            voice_rate = getattr(Config, "VOICE_RATE", default_rate)
            voice_volume = getattr(Config, "VOICE_VOLUME", default_volume)
        except Exception:
            voice_rate = 145 if self.voice_type == "male" else 165
            voice_volume = 0.78 if self.voice_type == "male" else 0.9

        self._engine.setProperty("rate", voice_rate)
        self._engine.setProperty("volume", voice_volume)

    def speak(self, text):
        if not text or not str(text).strip():
            return

        with self._lock:
            phrase = str(text).strip()
            try:
                self._reset_engine()
                engine = self._get_engine()
                engine.say(phrase)
                engine.runAndWait()
            except Exception as e:
                print(f"TTS error: {e}")
                try:
                    self._reset_engine()
                    engine = self._get_engine()
                    engine.say(phrase)
                    engine.runAndWait()
                except Exception as retry_error:
                    print(f"TTS retry error: {retry_error}")
            finally:
                self._reset_engine()

    def stop(self):
        with self._lock:
            try:
                if self._engine is not None:
                    self._engine.stop()
            except Exception as e:
                print(f"TTS stop error: {e}")
            finally:
                self._reset_engine()
