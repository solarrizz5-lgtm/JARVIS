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

# ============================================================
# API KEYS - Support TWO separate APIs
# ============================================================
# 1. OPENROUTER_API_KEY - For OpenRouter free models
#    Get from: https://openrouter.ai
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# 2. GEMINI_API_KEY - For Google AI Studio (Gemini) free models
#    Get from: https://aistudio.google.com (no credit card needed)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ============================================================
# MODEL SELECTION
# ============================================================
# IMPORTANT: Choose ONE model from the FREE TIER ONLY list below
#
# FREE TIER MODELS (No payment required, with rate limits):
#
# OPENROUTER MODELS:
#   "nvidia/nemotron-3-ultra-550b-a55b:free"  (550B, unlimited requests, vision, JSON)
#   "meta-llama/llama-3.3-70b-instruct:free"   (70B, unlimited requests, vision, JSON)
#
# GOOGLE GEMINI MODELS (via AI Studio):
#   "gemini-3.6-flash"        (20 requests/day, vision, fast)
#   "gemini-3.5-flash"        (20 requests/day, vision, balanced)
#   "gemini-3.5-flash-lite"   (500 requests/day, vision, cheaper)
#
# DEFAULT: Using OpenRouter's free Nemotron model
MODEL_NAME = "nvidia/nemotron-3-ultra-550b-a55b:free"

# Free tier quotas info:
# OpenRouter free tier: No daily limit, but 20 req/min rate limit
# Gemini free tier: Varies by model (20-500 req/day), resets at midnight PT

# Load persistent settings from config file if available
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            data = json.load(f)
            
            # Load OpenRouter API key
            if data.get("openrouter_api_key") or data.get("api_key"):
                loaded_key = data.get("openrouter_api_key") or data.get("api_key")
                if loaded_key and len(loaded_key) > 10:
                    OPENROUTER_API_KEY = loaded_key
                    os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY
            
            # Load Gemini API key (SEPARATE from OpenRouter)
            if data.get("gemini_api_key"):
                loaded_key = data.get("gemini_api_key")
                if loaded_key and len(loaded_key) > 10:
                    GEMINI_API_KEY = loaded_key
                    os.environ["GEMINI_API_KEY"] = GEMINI_API_KEY
            
            # Load model name
            if data.get("model_name"):
                loaded_model = data.get("model_name")
                if loaded_model and isinstance(loaded_model, str):
                    MODEL_NAME = loaded_model
    except Exception as e:
        print(f"[WARNING] Error loading config file: {e}")

# ============================================================
# API ENDPOINTS
# ============================================================
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

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
DEBUG_MODE = os.getenv("JARVIS_DEBUG", "false").lower() == "true"
