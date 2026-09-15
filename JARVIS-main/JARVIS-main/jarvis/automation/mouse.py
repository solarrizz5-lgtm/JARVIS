import pyautogui
from jarvis.utils.logger import log_error, log_info

# Safety first: moving the mouse to any corner of the screen aborts the script
pyautogui.FAILSAFE = True
# Adds a default 0.5-second pause after every PyAutoGUI action to ensure UI responsiveness
pyautogui.PAUSE = 0.5

def execute_mouse_action(action: dict, screen_width: int = None, screen_height: int = None) -> bool:
    """
    Executes a mouse action based on the provided dictionary.
    Converts percentage coordinates (0-100) to actual pixel coordinates,
    with strict clamping to prevent out-of-bounds errors and failsafe triggers.
    """
    try:
        action_type = action.get("type", action.get("action", ""))
        x_percent = action.get("x")
        y_percent = action.get("y")
        
        # Get actual screen dimensions if not provided
        if screen_width is None or screen_height is None:
            screen_width, screen_height = pyautogui.size()
        
        x = None
        y = None
        if x_percent is not None and y_percent is not None:
            # Clamp percentage strictly between 5 and 95 to prevent AI hallucinated out-of-bound values
            x_percent = max(5.0, min(95.0, float(x_percent)))
            y_percent = max(5.0, min(95.0, float(y_percent)))
            
            # Convert percentage coordinates to pixel coordinates
            x = int(x_percent * screen_width / 100)
            y = int(y_percent * screen_height / 100)
            
            # Final safety pixel clamp
            x = max(0, min(x, screen_width - 1))
            y = max(0, min(y, screen_height - 1))
        
        log_info(f"Executing mouse action: {action_type} at ({x_percent}%, {y_percent}%) = ({x}, {y}) pixels")

        if action_type in ["click", "left_click"]:
            if x is not None and y is not None:
                pyautogui.click(x=x, y=y)
            else:
                pyautogui.click()
                
        elif action_type == "right_click":
            if x is not None and y is not None:
                pyautogui.rightClick(x=x, y=y)
            else:
                pyautogui.rightClick()
                
        elif action_type == "double_click":
            if x is not None and y is not None:
                pyautogui.doubleClick(x=x, y=y)
            else:
                pyautogui.doubleClick()

        elif action_type == "move":
            if x is not None and y is not None:
                pyautogui.moveTo(x, y, duration=0.3)
                
        elif action_type == "drag":
            if x is not None and y is not None:
                pyautogui.dragTo(x, y, duration=0.5)

        elif action_type == "scroll":
            amount = action.get("amount", -100) # Negative is usually scroll down
            pyautogui.scroll(amount)
            
        else:
            log_error(f"Unknown mouse action type: {action_type}")
            return False

        return True
        
    except pyautogui.FailSafeException:
        log_error("Failsafe triggered! Mouse was moved to a screen corner.")
        return False
    except Exception as e:
        log_error(f"Failed to execute mouse action: {e}")
        return False
