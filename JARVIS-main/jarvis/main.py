import os
import time
import keyboard
from jarvis import config

# Import modules from the jarvis package structure
from jarvis.voice.tts import speak
from jarvis.voice.input import listen_and_transcribe
from jarvis.ai.planner import handle_user_command, run_agent
from jarvis.safety.permissions import is_command_blocked
from jarvis.utils.logger import log_info, log_error
from jarvis.ai.client import detect_api_type, get_model_info

def trigger_emergency_stop():
    """Global emergency stop callback triggered via hotkey."""
    config.AGENT_RUNNING = False
    log_error("EMERGENCY STOP ACTIVATED BY USER.")
    speak("Emergency stop activated. Halting all operations.")

def initialize_system():
    """Validates configuration and initializes safety hotkeys."""
    print("=" * 70)
    print("INITIALIZING JARVIS AGENT SYSTEM")
    print("=" * 70)
    
    model_name = getattr(config, "MODEL_NAME", "nvidia/nemotron-3-ultra-550b-a55b:free")
    api_type = detect_api_type(model_name)
    model_info = get_model_info(model_name)
    
    print(f"\n[CONFIG] Selected Model: {model_name}")
    print(f"[CONFIG] API Type: {api_type.upper()}")
    print(f"[CONFIG] Vision Support: {model_info.get('vision', False)}")
    print(f"[CONFIG] Free Tier: {model_info.get('free', False)}")
    print(f"[CONFIG] Free Tier Quota: {model_info.get('quota', 'Unknown')}")
    
    # Validate API keys based on model type
    if api_type == "gemini":
        api_key = getattr(config, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            print("\n[CRITICAL ERROR] GEMINI_API_KEY is not set!")
            print("Please get a FREE API key from: https://aistudio.google.com")
            print("  (No credit card required - completely free!)")
            print("\nSet your API key using:")
            print("  Windows (CMD): set GEMINI_API_KEY=your_key")
            print("  Windows (PowerShell): $env:GEMINI_API_KEY=\"your_key\"")
            print("  Linux/Mac: export GEMINI_API_KEY='your_key'")
            return False
        print(f"\n✓ Gemini API Key configured (length: {len(api_key)})")
    else:
        api_key = getattr(config, "OPENROUTER_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            print("\n[CRITICAL ERROR] OPENROUTER_API_KEY is not set!")
            print("Please set your API key from: https://openrouter.ai")
            print("\nSet your API key using:")
            print("  Windows (CMD): set OPENROUTER_API_KEY=your_key")
            print("  Windows (PowerShell): $env:OPENROUTER_API_KEY=\"your_key\"")
            print("  Linux/Mac: export OPENROUTER_API_KEY='your_key'")
            return False
        print(f"\n✓ OpenRouter API Key configured (length: {len(api_key)})")

    # Bind Emergency Stop Hotkey
    try:
        keyboard.add_hotkey(config.EMERGENCY_STOP_HOTKEY, trigger_emergency_stop)
        print(f"✓ Emergency stop hotkey registered: {config.EMERGENCY_STOP_HOTKEY.upper()}")
    except Exception as e:
        print(f"[WARNING] Could not register global hotkey: {e}")

    log_info(f"JARVIS initialized successfully with {api_type.upper()} API")
    return True

def main():
    if not initialize_system():
        return

    print("\n" + "=" * 70)
    print("JARVIS SYSTEM ONLINE - SLEEP MODE")
    print(f"Say 'Hey Jarvis' or 'Jarvis' to activate.")
    print(f"Press '{config.EMERGENCY_STOP_HOTKEY.upper()}' to emergency stop.")
    print("=" * 70 + "\n")

    speak("JARVIS system online, sir.")

    while True:
        try:
            # 1. Background listening for wake word
            text = listen_and_transcribe(timeout_seconds=5.0)
            if not text:
                continue

            print(f"[HEARD]: {text}")
            lower_text = text.lower()

            # 2. Wake-word detection
            if "jarvis" in lower_text or "hey jarvis" in lower_text:
                speak("Yes, sir? Standing by.")
                print("\n[JARVIS] Awake. Listening for command...")

                # 3. Capture user command
                command = listen_and_transcribe(timeout_seconds=6.0)
                
                if command:
                    print(f"[COMMAND]: {command}")
                    
                    # 4. Permission / Blocked safety check
                    if is_command_blocked(command):
                        speak("Security restriction applied. Command blocked.")
                        log_error(f"Blocked goal phrase detected in command: {command}")
                        continue

                    # 5. Route to AI Planner / Execution agent
                    handle_user_command(command)
                else:
                    print("\n[JARVIS] No command heard. Returning to sleep mode.")
                    speak("I didn't hear a command. Returning to sleep.")
            
            print("\n[JARVIS] Sleeping. Say 'Hey Jarvis' when ready.")

        except KeyboardInterrupt:
            print("\n[JARVIS] Manual shutdown requested via terminal.")
            speak("Shutting down system, sir.")
            break
        except Exception as error:
            log_error(f"Unexpected main loop error: {error}")
            time.sleep(2)

if __name__ == "__main__":
    main()
