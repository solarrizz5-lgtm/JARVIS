import queue
import threading
import subprocess
from jarvis import config
from jarvis.utils.logger import log_error

# Queue to handle speech requests sequentially without blocking the agent loop
_tts_queue = queue.Queue()
_tts_lock = threading.Lock()

def _tts_worker():
    """Background worker using Windows SAPI via PowerShell to ensure reliable speech output without lockups."""
    while True:
        text = _tts_queue.get()
        if text is None:
            break
        
        with _tts_lock:
            config.IS_SPEAKING = True
        
        try:
            safe_text = text.replace('"', '`"').replace("'", "''")
            
            # Use getattr for cross-platform safety (CREATE_NO_WINDOW is Windows-only)
            creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            tts_rate = getattr(config, "TTS_RATE", 175)
            rate_val = int((tts_rate - 175) / 50)
            
            cmd = [
                "powershell",
                "-Command",
                f"Add-Type -AssemblyName System.Speech; $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; $synth.Rate = {rate_val}; $synth.Speak('{safe_text}');"
            ]
            subprocess.run(cmd, capture_output=True, text=True, creationflags=creation_flags)
        except Exception as error:
            log_error(f"TTS Worker execution error: {error}")
        finally:
            with _tts_lock:
                config.IS_SPEAKING = False
            _tts_queue.task_done()

# Start the background TTS thread on module load
threading.Thread(target=_tts_worker, daemon=True).start()

def speak(text: str):
    """Adds a text string to the TTS output queue."""
    if text and text.strip():
        _tts_queue.put(text.strip())

def stop_speech():
    """Clears all pending speech tasks from the queue and resets the speaking lock."""
    with _tts_queue.mutex:
        _tts_queue.queue.clear()
    with _tts_lock:
        config.IS_SPEAKING = False
