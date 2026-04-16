import time
import queue
import numpy as np
from audio_capture import AudioCapture
from transcriber import RealtimeTranscriber

def main():
    print("Initializing...")
    
    # Initialize components
    capture = AudioCapture()
    transcriber = RealtimeTranscriber(model_size="base.en") # Use 'base' for balance
    
    # Buffer to accumulate audio chunks
    audio_buffer = np.array([], dtype=np.float32)
    
    # Timing variables
    last_transcribe_time = time.time()
    
    # Silence detection parameters
    SILENCE_THRESHOLD = 0.01  # Adjust based on mic sensitivity
    SILENCE_DURATION_MS = 500 # Wait 0.5s of silence before committing
    SAMPLE_RATE = 16000
    
    consecutive_silence_samples = 0
    
    print("Starting capture. Press Ctrl+C to stop.")
    capture.start()
    
    try:
        while True:
            # Process all available audio chunks
            # currently less reliable 
            # not guaranteed to process all chunks if they come in faster than the loop, but should be good enough for real-time
            # still need to check if queue is empty to avoid blocking, but manual check is safer
            while True:
                try:
                    chunk = capture.read() # Reads from queue, blocking=False inside check? No, Queue is thread safe but check if empty
                    # Actually AudioCapture queue is blocking by default on get(), but we want non-blocking loop
                    pass 
                except queue.Empty:
                    break
                
                # Manual empty check is safer
                if capture.audio_queue.empty():
                    break
                
                chunk = capture.audio_queue.get()
                chunk = chunk.flatten()
                
                # Update buffer
                audio_buffer = np.concatenate((audio_buffer, chunk))
                
                # Check silence
                chunk_amplitude = np.max(np.abs(chunk))
                if chunk_amplitude < SILENCE_THRESHOLD:
                    consecutive_silence_samples += len(chunk)
                else:
                    consecutive_silence_samples = 0
            
            # Run transcription periodically (e.g., every 0.5s) if buffer has data
            current_time = time.time()
            if (current_time - last_transcribe_time > 0.5) and (len(audio_buffer) > 0):
                
                # Only transcribe if we have enough audio (> 1s) to be meaningful
                if len(audio_buffer) / SAMPLE_RATE > 1.0:
                    text = transcriber.transcribe(audio_buffer)
                    
                    # Print partial result (overwrite line)
                    # \033[K clears the line from cursor
                    print(f"\rUser: {text}\033[K", end="", flush=True)
                
                last_transcribe_time = current_time
                
                # If silence detected for long enough, commit the line and clear buffer
                silence_duration = (consecutive_silence_samples / SAMPLE_RATE) * 1000
                if silence_duration > SILENCE_DURATION_MS and len(audio_buffer) > 0:
                     # Transcribe one last time to be sure
                    text = transcriber.transcribe(audio_buffer)
                    print(f"\rUser (Final): {text}\033[K") # New line
                    
                    # Clear buffer
                    audio_buffer = np.array([], dtype=np.float32)
                    consecutive_silence_samples = 0

            time.sleep(0.05) # Prevent busy loop

    except KeyboardInterrupt:
        print("\nStopping...")
        capture.stop()

if __name__ == "__main__":
    main()
