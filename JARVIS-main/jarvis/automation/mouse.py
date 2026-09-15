import pyautogui
from jarvis.utils.logger import log_error, log_info

# Safety settings
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5


def execute_mouse_action(
    action: dict,
    model_name: str = None,
    screen_width: int = None,
    screen_height: int = None,
) -> bool:
  """Executes a mouse action based on the provided dictionary.

  Coordinate Clamping Rules:
  - gemini-3.5-flash-lite: Strict 5.0% to 95.0% clamp to prevent hallucinated
  edge errors
  - All other models (e.g. nemotron, gemini-3.6-flash): Full 0.0% to 100.0% range
  allowed
  """
  try:
    action_type = action.get("type", action.get("action", ""))
    x_percent = action.get("x")
    y_percent = action.get("y")

    # Determine model source if not passed explicitly without triggering circular import errors
    if model_name is None:
      try:
        import jarvis.config as config_module

        if hasattr(config_module, "config"):
          model_name = getattr(config_module.config, "MODEL_NAME", "").lower()
        else:
          model_name = getattr(config_module, "MODEL_NAME", "").lower()
      except Exception:
        model_name = ""
    else:
      model_name = model_name.lower()

    # Set bounds based on active model architecture
    if "gemini-3.5-flash-lite" in model_name or "flash-lite" in model_name:
      min_bound, max_bound = 5.0, 95.0
    else:
      min_bound, max_bound = 0.0, 100.0

    if screen_width is None or screen_height is None:
      screen_width, screen_height = pyautogui.size()

    x = None
    y = None
    if x_percent is not None and y_percent is not None:
      # Apply dynamic percentage clamping based on active model
      x_percent = max(min_bound, min(max_bound, float(x_percent)))
      y_percent = max(min_bound, min(max_bound, float(y_percent)))

      # Convert percentage coordinates to pixel coordinates
      x = int(x_percent * screen_width / 100)
      y = int(y_percent * screen_height / 100)

      # Prevent triggering PyAutoGUI failsafe at (0,0) corner
      x = max(1, min(x, screen_width - 1))
      y = max(1, min(y, screen_height - 1))

    log_info(
        f"Executing [{model_name or 'default'}] mouse action: {action_type} at"
        f" ({x_percent:.1f}%, {y_percent:.1f}%) = ({x}, {y}) pixels"
    )

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
        pyautogui.moveTo(x, y, duration=0.2)

    elif action_type == "drag":
      if x is not None and y is not None:
        pyautogui.dragTo(x, y, duration=0.4)

    elif action_type == "scroll":
      amount = action.get("amount", -100)
      pyautogui.scroll(int(amount))

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