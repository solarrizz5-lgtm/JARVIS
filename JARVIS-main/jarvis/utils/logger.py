import json
import os
from datetime import datetime
from jarvis import config

def log_info(message):
    """Logs general system information."""
    entry = f"[{datetime.now().isoformat()}] [INFO] {message}\n"
    print(entry.strip())
    _write_log(entry)

def log_error(message):
    """Logs system errors."""
    entry = f"[{datetime.now().isoformat()}] [ERROR] {message}\n"
    print(entry.strip())
    _write_log(entry)

def log_action(goal, step, action_data, success=True):
    """Logs structured JSON data for agent actions."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "goal": goal,
        "step": step,
        "decision": action_data,
        "success": success
    }
    _write_log(json.dumps(log_entry) + "\n")

def save_error_snapshot(screenshot_img, error_msg):
    """Saves a visual snapshot when an error occurs."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(config.LOGS_DIR, f"error_{timestamp}.jpg")
    
    if screenshot_img:
        try:
            screenshot_img.save(path, format="JPEG")
            log_error(f"Saved error state to {path} | Error: {error_msg}")
        except Exception as e:
            log_error(f"Failed to save error snapshot: {e}")

def _write_log(entry):
    """Internal helper to write to the main log file."""
    try:
        with open(config.ACTION_LOG_FILE, "a") as f:
            f.write(entry)
    except Exception as e:
        print(f"[LOGGING ERROR] Could not write to {config.ACTION_LOG_FILE}: {e}")