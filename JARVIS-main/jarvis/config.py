import os
import json
import pyautogui

# ============================================================
# PYAUTOGUI DEFAULTS
# ============================================================
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

# ============================================================
# DIRECTORIES & PERSISTENT CONFIGURATION
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)
CONFIG_FILE = os.path.join(ROOT_DIR, "jarvis_config.json")

# Defaults
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
MODEL_NAME = "nvidia/nemotron-3-ultra-550b-a55b:free"

# Load persistent settings if available
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            if data.get("openrouter_api_key") or data.get("api_key"):
                OPENROUTER_API_KEY = data.get("openrouter_api_key") or data.get("api_key")
                os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY
            if data.get("model_name"):
                MODEL_NAME = data.get("model_name")
    except Exception:
        pass

# ============================================================
# OPENROUTER & AI CONFIGURATION
# ============================================================
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# ============================================================
# VOICE & AUDIO SETTINGS
# ============================================================
VOICE_LANGUAGE = "en-US"
SAMPLE_RATE = 16000
LISTEN_DURATION = 6.0
TTS_RATE = 175

# ============================================================
# AGENT TIMINGS & LIMITS
# ============================================================
ACTION_DELAY_SECONDS = 4
MAX_WAIT_SECONDS = 15
MAX_STEPS_PER_MISSION = 25
MAX_CONSECUTIVE_ERRORS = 3

# ============================================================
# SAFETY & SECURITY
# ============================================================
EMERGENCY_STOP_HOTKEY = "ctrl+shift+j"

BLOCKED_GOAL_PHRASES = (
    "delete everything",
    "format the drive",
    "disable antivirus",
    "turn off antivirus",
    "install malware",
    "download malware",
)

# ============================================================
# DIRECTORIES & LOGGING
# ============================================================
LOGS_DIR = os.path.join(ROOT_DIR, "logs")
ACTION_LOG_FILE = os.path.join(LOGS_DIR, "actions.log")

os.makedirs(LOGS_DIR, exist_ok=True)

AGENT_RUNNING = True
IS_SPEAKING = False
