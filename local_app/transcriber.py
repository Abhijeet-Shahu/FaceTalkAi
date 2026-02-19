from faster_whisper import WhisperModel
import numpy as np

class RealtimeTranscriber:
    def __init__(self, model_size="tiny.en", device="cpu", compute_type="int8"):
        """
        Initialize the transcription model.
        
        Args:
            model_size (str): Size of the Whisper model (tiny, base, small, medium, large)
            device (str): Device to run the model on (cuda or cpu)
            compute_type (str): Type of quantization (int8, float16, float32)
        """
        print(f"Loading Whisper model '{model_size}' on {device}...")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print("Model loaded.")

    def transcribe(self, audio_data):
        """
        Transcribe audio data.
        
        Args:
            audio_data (np.array): Audio data as a float32 numpy array.
            
        Returns:
            str: The transcribed text.
        """
        segments, info = self.model.transcribe(
            audio_data, 
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500)
        )
        
        text = ""
        for segment in segments:
            text += segment.text
            
        return text.strip()
