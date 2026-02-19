import time
import numpy as np
import queue
import signal
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
from audio_capture import AudioCapture
from transcriber import RealtimeTranscriber
from llm_service import LLMService
from tts_service import TTSService

def main():
    print("Initializing Voice Assistant...")
    
    # 1. Initialize Components
    try:
        audio_cap = AudioCapture()
        transcriber = RealtimeTranscriber(model_size="base.en")
        llm = LLMService(system_prompt="You are a helpful, witty voice assistant. Keep answers short and fun.")
        tts = TTSService()
    except Exception as e:
        print(f"Error initializing components: {e}")
        return

    # 2. State Variables
    audio_buffer = np.array([], dtype=np.float32)
    SAMPLE_RATE = 16000
    SILENCE_THRESHOLD = 0.01
    SILENCE_DURATION_MS = 700  # slightly longer to avoid cutting off mid-sentence
    consecutive_silence_samples = 0
    
    print("\n" + "="*50)
    print("Voice Assistant Ready! Speak into your microphone.")
    print("Press Ctrl+C to stop.")
    print("="*50 + "\n")
    
    audio_cap.start()
    
    try:
        while True:
            # --- Audio Capture & VAD Loop ---
            while True:
                try:
                    chunk = audio_cap.audio_queue.get(timeout=0.1) # Non-blocking get
                except queue.Empty:
                    continue
                
                chunk = chunk.flatten()
                audio_buffer = np.concatenate((audio_buffer, chunk))
                
                # Check amplitude for silence
                if np.max(np.abs(chunk)) < SILENCE_THRESHOLD:
                    consecutive_silence_samples += len(chunk)
                else:
                    consecutive_silence_samples = 0
                
                # Check if user stopped speaking
                silence_duration = (consecutive_silence_samples / SAMPLE_RATE) * 1000
                if silence_duration > SILENCE_DURATION_MS and len(audio_buffer) > SAMPLE_RATE: # At least 1 sec of audio
                    break
            
            # --- Transcription (STT) ---
            print("\n[Thinking...]")
            user_text = transcriber.transcribe(audio_buffer)
            
            # Reset buffer immediately for next turn
            audio_buffer = np.array([], dtype=np.float32)
            consecutive_silence_samples = 0
            
            if not user_text.strip():
                print("...didn't catch that.")
                continue
                
            print(f"User: {user_text}")
            
            # --- LLM Response ---
            ai_response = llm.get_response(user_text)
            print(f"Assistant: {ai_response}")
            
            # --- Text-to-Speech (TTS) ---
            # Stop capturing while speaking to avoid hearing itself?
            # Ideally yes, or use echo cancellation. For now, we just pause processing? 
            # Actually, `tts.speak` is blocking in our implementation, so we effectively pause.
            # However, the audio_capture thread is STILL recording in the background!
            # We should clear the queue after speaking to avoid processing the assistant's own voice
            # if the mic picks it up.
            
            tts.speak(ai_response)
            
            # Clear any audio captured while the assistant was speaking
            while not audio_cap.audio_queue.empty():
                audio_cap.audio_queue.get()
            
            print("\n[Listening...]")

    except KeyboardInterrupt:
        print("\nStopping...")
        audio_cap.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()
