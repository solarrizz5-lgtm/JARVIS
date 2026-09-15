import pyautogui
from jarvis.utils.logger import log_error, log_info

def execute_keyboard_action(action: dict) -> bool:
    """
    Executes a keyboard action based on the provided dictionary,
    handling PyAutoGUI fail-safe exceptions if the mouse is in a corner.
    """
    try:
        action_type = action.get("type", action.get("action", ""))
        
        log_info(f"Executing keyboard action: {action_type}")

        if action_type == "type":
            text = action.get("text", "")
            if text:
                # The interval adds a realistic, human-like typing delay per character
                pyautogui.write(text, interval=0.05)
            
            # Support press_enter flag from planner schema
            if action.get("press_enter", False):
                pyautogui.press("enter")
                
        elif action_type == "press":
            key = action.get("key", "")
            if key:
                pyautogui.press(key)
                
        elif action_type == "hotkey":
            keys = action.get("keys", [])
            if keys and isinstance(keys, list):
                pyautogui.hotkey(*keys)
            elif isinstance(keys, str):
                # Fallback if given as a comma-separated string
                pyautogui.hotkey(*keys.split(","))
                
        else:
            log_error(f"Unknown keyboard action type: {action_type}")
            return False

        return True
        
    except pyautogui.FailSafeException:
        log_error("Failsafe triggered during keyboard action! Mouse was in a screen corner.")
        return False
    except Exception as e:
        log_error(f"Failed to execute keyboard action: {e}")
        return False