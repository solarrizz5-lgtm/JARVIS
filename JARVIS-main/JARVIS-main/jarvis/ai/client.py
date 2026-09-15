import os
import json
import time
import requests
from jarvis import config
from jarvis.utils.logger import log_error, log_info

# ============================================================
# MODEL REGISTRY - Free Tier Only
# ============================================================
FREE_TIER_MODELS = {
    # OpenRouter Models
    "nvidia/nemotron-3-ultra-550b-a55b:free": {
        "provider": "openrouter",
        "api_type": "openrouter",
        "vision": True,
        "json_mode": True,
        "context": "1M",
        "quota": "No daily limit (20 req/min rate limit)",
        "free": True
    },
    "meta-llama/llama-3.3-70b-instruct:free": {
        "provider": "openrouter",
        "api_type": "openrouter",
        "vision": True,
        "json_mode": True,
        "context": "128K",
        "quota": "No daily limit (20 req/min rate limit)",
        "free": True
    },
    "openrouter/free": {
        "provider": "openrouter",
        "api_type": "openrouter",
        "vision": True,
        "json_mode": False,
        "context": "varies",
        "quota": "Auto-selects best free model",
        "free": True
    },
    # Google Gemini Models (FREE TIER ONLY)
    "gemini-3.6-flash": {
        "provider": "google",
        "api_type": "gemini",
        "vision": True,
        "json_mode": False,
        "context": "1M",
        "quota": "20 requests/day",
        "free": True
    },
    "gemini-3.5-flash": {
        "provider": "google",
        "api_type": "gemini",
        "vision": True,
        "json_mode": False,
        "context": "1M",
        "quota": "20 requests/day",
        "free": True
    },
    "gemini-3.5-flash-lite": {
        "provider": "google",
        "api_type": "gemini",
        "vision": True,
        "json_mode": False,
        "context": "1M",
        "quota": "500 requests/day",
        "free": True
    },
}

def detect_api_type(model_name: str) -> str:
    """
    Detect which API service to use based on model name.
    
    Returns:
        "openrouter" - Use OpenRouter API
        "gemini" - Use Google Gemini API
    """
    model_lower = model_name.lower()
    
    # Gemini models
    if "gemini" in model_lower:
        return "gemini"
    
    # OpenRouter models have provider prefix (nvidia/, meta-, openrouter/)
    if any(prefix in model_lower for prefix in ["nvidia/", "meta-", "openrouter/"]):
        return "openrouter"
    
    # Default to OpenRouter if unsure
    return "openrouter"

def get_model_info(model_name: str) -> dict:
    """
    Get capability information about a model.
    """
    return FREE_TIER_MODELS.get(model_name, {
        "provider": "unknown",
        "vision": False,
        "json_mode": False,
        "free": False
    })

def validate_api_key(api_key: str, api_type: str) -> bool:
    """
    Validate that API key looks reasonable.
    """
    if not api_key or not isinstance(api_key, str):
        log_error(f"[{api_type.upper()}] API key is empty or invalid type")
        return False
    if len(api_key) < 10:
        log_error(f"[{api_type.upper()}] API key too short (length: {len(api_key)})")
        return False
    return True

def call_openrouter_api(payload_or_messages, max_retries: int = 4) -> dict:
    """
    Sends requests to OpenRouter API.
    Handles only models prefixed with: nvidia/, meta-, openrouter/
    
    Args:
        payload_or_messages: Request payload or list of messages
        max_retries: Maximum number of retry attempts
        
    Returns:
        Response JSON in OpenAI-compatible format
    """
    # Get API key
    api_key = getattr(config, "OPENROUTER_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError(
            "[CRITICAL] OPENROUTER_API_KEY not configured.\n"
            "Get from: https://openrouter.ai\n"
            "Set with: set OPENROUTER_API_KEY=your_key (Windows) or export OPENROUTER_API_KEY='your_key' (Linux/Mac)"
        )
    
    if not validate_api_key(api_key, "openrouter"):
        raise ValueError("[CRITICAL] Invalid OpenRouter API key format")
    
    base_url = getattr(config, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    url = f"{base_url}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "Jarvis Assistant"
    }
    
    primary_model = getattr(config, "MODEL_NAME", "nvidia/nemotron-3-ultra-550b-a55b:free")
    if not primary_model or not isinstance(primary_model, str):
        primary_model = "nvidia/nemotron-3-ultra-550b-a55b:free"
    
    log_info(f"[OPENROUTER] Using model: {primary_model}")
    
    # Construct payload
    if isinstance(payload_or_messages, list):
        payload = {
            "model": primary_model,
            "messages": payload_or_messages
        }
    elif isinstance(payload_or_messages, dict):
        payload = payload_or_messages.copy()
        payload.pop("models", None)
        payload["model"] = primary_model
        
        if "messages" not in payload and "contents" in payload:
            messages = []
            for content in payload.pop("contents", []):
                role = "user" if content.get("role") == "user" else "assistant"
                parts = content.get("parts", [])
                content_parts = []
                for p in parts:
                    if "text" in p:
                        content_parts.append({"type": "text", "text": p["text"]})
                    elif "inline_data" in p:
                        img_data = p["inline_data"]
                        mime = img_data.get("mime_type", "image/jpeg")
                        b64 = img_data.get("data", "")
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{b64}"}
                        })
                messages.append({
                    "role": role, 
                    "content": content_parts if len(content_parts) > 1 else (content_parts[0]["text"] if len(content_parts) == 1 else "")
                })
            payload["messages"] = messages
    else:
        payload = {
            "model": primary_model,
            "messages": [{"role": "user", "content": str(payload_or_messages)}]
        }
    
    if "messages" not in payload:
        raise ValueError("[OPENROUTER] Payload missing 'messages' field")
    
    backoff_delay = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            if config.DEBUG_MODE:
                log_info(f"[OPENROUTER] Sending request (attempt {attempt + 1}/{max_retries})")
            
            response = requests.post(
                url, 
                headers=headers, 
                json=payload, 
                timeout=45
            )
            
            log_info(f"[OPENROUTER] Response status: {response.status_code}")
            
            if response.status_code == 429:
                log_info(f"[OPENROUTER] Rate limit (429). Retrying in {backoff_delay}s...")
                time.sleep(backoff_delay)
                backoff_delay *= 2
                continue
            
            if response.status_code != 200:
                error_text = response.text
                log_error(f"[OPENROUTER] API error {response.status_code}: {error_text}")
                last_error = error_text
                response.raise_for_status()
            
            result = response.json()
            log_info("[OPENROUTER] API call successful")
            return result
            
        except requests.exceptions.RequestException as e:
            log_error(f"[OPENROUTER] Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
            last_error = str(e)
            if attempt == max_retries - 1:
                raise Exception(f"[OPENROUTER] Max retries exceeded: {last_error}")
            time.sleep(backoff_delay)
            backoff_delay *= 2
    
    raise Exception(f"[OPENROUTER] Max retries exceeded: {last_error}")

def call_gemini_api(payload_or_messages, max_retries: int = 4) -> dict:
    """
    Sends requests to Google Gemini API (Google AI Studio).
    Handles only Gemini models (gemini-*)
    Uses separate API key from OpenRouter.
    
    Args:
        payload_or_messages: Request payload or list of messages
        max_retries: Maximum number of retry attempts
        
    Returns:
        Response JSON in OpenAI-compatible format
    """
    # Get API key (SEPARATE from OpenRouter)
    api_key = getattr(config, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError(
            "[CRITICAL] GEMINI_API_KEY not configured.\n"
            "Get FREE key from: https://aistudio.google.com (no credit card needed)\n"
            "Set with: set GEMINI_API_KEY=your_key (Windows) or export GEMINI_API_KEY='your_key' (Linux/Mac)"
        )
    
    if not validate_api_key(api_key, "gemini"):
        raise ValueError("[CRITICAL] Invalid Gemini API key format")
    
    model_name = getattr(config, "MODEL_NAME", "gemini-3.5-flash")
    clean_model_name = model_name.split("/")[-1] if "/" in model_name else model_name
    
    log_info(f"[GEMINI] Using model: {clean_model_name}")
    
    # Gemini v1beta endpoint for generateContent
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    # Convert messages to Gemini format (contents/parts)
    if isinstance(payload_or_messages, list):
        contents = []
        for msg in payload_or_messages:
            role = "user" if msg.get("role") == "user" else "model"
            text_content = msg.get("content", "")
            contents.append({
                "role": role,
                "parts": [{"text": text_content}]
            })
        payload = {"contents": contents}
    elif isinstance(payload_or_messages, dict):
        payload = payload_or_messages.copy()
        if "contents" not in payload and "messages" in payload:
            contents = []
            for msg in payload.pop("messages", []):
                role = "user" if msg.get("role") == "user" else "model"
                text_content = msg.get("content", "")
                contents.append({
                    "role": role,
                    "parts": [{"text": text_content}]
                })
            payload["contents"] = contents
    else:
        payload = {
            "contents": [{
                "role": "user",
                "parts": [{"text": str(payload_or_messages)}]
            }]
        }
    
    # Remove response_format as Gemini doesn't support it
    payload.pop("response_format", None)
    
    backoff_delay = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            if config.DEBUG_MODE:
                log_info(f"[GEMINI] Sending request (attempt {attempt + 1}/{max_retries})")
            
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            
            log_info(f"[GEMINI] Response status: {response.status_code}")
            
            if response.status_code == 429:
                log_info(f"[GEMINI] Rate limit (429). Retrying in {backoff_delay}s...")
                time.sleep(backoff_delay)
                backoff_delay *= 2
                continue
            
            if response.status_code != 200:
                error_text = response.text
                log_error(f"[GEMINI] API error {response.status_code}: {error_text}")
                last_error = error_text
                response.raise_for_status()
            
            # Parse Gemini response
            gemini_data = response.json()
            
            # Gemini returns: {"candidates": [{"content": {"parts": [{"text": "..."}]}}]}
            text_result = gemini_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            if not text_result:
                raise ValueError("Empty text result from Gemini API")
            
            # Return in OpenAI-compatible format
            result = {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": text_result
                    }
                }]
            }
            log_info("[GEMINI] API call successful")
            return result
            
        except requests.exceptions.RequestException as e:
            log_error(f"[GEMINI] Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
            last_error = str(e)
            if attempt == max_retries - 1:
                raise Exception(f"[GEMINI] Max retries exceeded: {last_error}")
            time.sleep(backoff_delay)
            backoff_delay *= 2
    
    raise Exception(f"[GEMINI] Max retries exceeded: {last_error}")

def call_api(payload_or_messages, max_retries: int = 4) -> dict:
    """
    Smart routing function that detects API type and calls appropriate handler.
    
    Args:
        payload_or_messages: Request payload or list of messages
        max_retries: Maximum number of retry attempts
        
    Returns:
        Response JSON in standardized format
    """
    model_name = getattr(config, "MODEL_NAME", "nvidia/nemotron-3-ultra-550b-a55b:free")
    api_type = detect_api_type(model_name)
    
    log_info(f"[API ROUTER] Model: {model_name} -> Using {api_type.upper()} API")
    
    if api_type == "gemini":
        return call_gemini_api(payload_or_messages, max_retries)
    else:
        return call_openrouter_api(payload_or_messages, max_retries)
