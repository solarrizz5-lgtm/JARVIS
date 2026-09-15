from jarvis.voice.input import listen_and_transcribe

def check_wakeword(listened_text: str) -> bool:
    """
    Parses transcribed text to determine if a wake-word trigger phrase was uttered.
    """
    if not listened_text:
        return False
        
    lower_text = listened_text.lower()
    wake_triggers = ["jarvis", "hey jarvis", "ok jarvis"]
    
    return any(trigger in lower_text for trigger in wake_triggers)

def listen_for_wakeword(timeout_seconds: float = 5.0) -> bool:
    """
    Performs a single listening pass specifically tuned for wake-word detection.
    """
    text = listen_and_transcribe(timeout_seconds=timeout_seconds)
    return check_wakeword(text)