from openai import OpenAI
import sounddevice as sd
import numpy as np
import io
import pyttsx3

class TTSService:
    def __init__(self, model="tts-1", voice="alloy"):
        self.model = model
        self.voice = voice
        self.engine = pyttsx3.init()
        
        # Optional voice tuning
        self.engine.setProperty('rate', 180)   # Speed
        self.engine.setProperty('volume', 1.0) # Volume

    def speak(self, text):
        """
        Convert text to speech and play it immediately.
        """
        # try:
        #     response = self.client.audio.speech.create(
        #         model=self.model,
        #         voice=self.voice,
        #         input=text,
        #         response_format="pcm"
        #     )
            
        #     audio_data_bytes = response.content
        #     audio_array = np.frombuffer(audio_data_bytes, dtype=np.int16)
            
        #     print("Assistant is speaking (OpenAI)...")
        #     sd.play(audio_array, samplerate=24000)
        #     sd.wait()
            
        # except Exception as e:
        #     print(f"OpenAI TTS Error: {e}")
        try:
            print("Falling back to local TTS (pyttsx3)...")
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e2:
            print(f"Local TTS Error: {e2}")
