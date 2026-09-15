import numpy as np
import sounddevice as sd
import speech_recognition as sr
from jarvis import config
from jarvis.utils.logger import log_error, log_info

_recognizer = sr.Recognizer()

def listen_and_transcribe(timeout_seconds: float = None) -> str:
    """
    Records audio from the default microphone using sounddevice and 
    transcribes it using Google Speech Recognition.
    """
    # Prevent listening while Jarvis is speaking to avoid feedback loops
    if getattr(config, "IS_SPEAKING", False):
        return ""

    duration = timeout_seconds if timeout_seconds is not None else config.LISTEN_DURATION
    
    try:
        # Record raw audio buffer
        audio_np = sd.rec(
            int(duration * config.SAMPLE_RATE),
            samplerate=config.SAMPLE_RATE,
            channels=1,
            dtype='int16'
        )
        sd.wait()
        
        # Audio amplitude gate: ignore silence or near-zero background noise
        if np.linalg.norm(audio_np) < 100:
            return ""
            
        raw_audio = audio_np.tobytes()
        audio_data = sr.AudioData(raw_audio, config.SAMPLE_RATE, 2)
        
        # Transcribe audio using Google Speech Recognition API
        transcript = _recognizer.recognize_google(
            audio_data, 
            language=config.VOICE_LANGUAGE
        ).strip()
        
        return transcript

    except sr.UnknownValueError:
        # Normal occurrence when speech isn't detected or understood
        return ""
    except sr.RequestError as e:
        log_error(f"Speech recognition service request failed: {e}")
        return ""
    except Exception as error:
        log_error(f"Unexpected audio input error: {error}")
        return ""