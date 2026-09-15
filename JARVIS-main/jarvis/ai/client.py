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
    """Detect which API service to use based on model name."""
    model_lower = str(model_name).lower()
    if "gemini" in model_lower:
        return "gemini"
    return "openrouter"

def get_model_info(model_name: str) -> dict:
    """Get capability information about a model."""
    return FREE_TIER_MODELS.get(model_name, {
        "provider": "unknown",
        "vision": False,
        "json_mode": False,
        "free": False
    })

def validate_api_key(api_key: str, api_type: str) -> bool:
    """Validate that API key looks reasonable."""
    if not api_key or not isinstance(api_key, str):
        log_error(f"[{api_type.upper()}] API key is empty or invalid type")
        return False
    if len(api_key) < 10:
        log_error(f"[{api_type.upper()}] API key too short (length: {len(api_key)})")
        return False
    return True

def call_openrouter_api(payload_or_messages, max_retries: int = 4) -> dict:
    """Sends requests to OpenRouter API."""
    api_key = getattr(config, "OPENROUTER_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("[CRITICAL] OPENROUTER_API_KEY not configured.")
    
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
    
    # Payload Construction
    if isinstance(payload_or_messages, list):
        payload = {"model": primary_model, "messages": payload_or_messages}
    elif isinstance(payload_or_messages, dict):
        payload = payload_or_messages.copy()
        payload["model"] = primary_model
        
        # Translate Gemini 'contents' format to OpenRouter 'messages' if needed
        if "messages" not in payload and "contents" in payload:
            messages = []
            for content in payload.pop("contents", []):
                role = "user" if content.get("role") == "user" else "assistant"
                parts = content.get("parts", [])
                content_parts = []
                for p in parts:
                    if "text" in p:
                        content_parts.append({"type": "text", "text": str(p["text"])})
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
    
    backoff_delay = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            if config.DEBUG_MODE:
                log_info(f"[OPENROUTER] Sending request (attempt {attempt + 1}/{max_retries})")
            
            response = requests.post(url, headers=headers, json=payload, timeout=90)
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
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            log_error(f"[OPENROUTER] Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
            last_error = str(e)
            if attempt == max_retries - 1:
                raise Exception(f"[OPENROUTER] Max retries exceeded: {last_error}")
            time.sleep(backoff_delay)
            backoff_delay *= 2
    
    raise Exception(f"[OPENROUTER] Max retries exceeded: {last_error}")

def call_gemini_api(payload_or_messages, max_retries: int = 4) -> dict:
    """Sends requests to Google Gemini API."""
    api_key = getattr(config, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("[CRITICAL] GEMINI_API_KEY not configured.")
    
    if not validate_api_key(api_key, "gemini"):
        raise ValueError("[CRITICAL] Invalid Gemini API key format")
    
    # Updated default fallback model
    model_name = getattr(config, "MODEL_NAME", "gemini-3.6-flash")
    clean_model_name = model_name.split("/")[-1] if "/" in model_name else model_name
    
    log_info(f"[GEMINI] Using model: {clean_model_name}")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    # Payload Formatting & Normalization
    if isinstance(payload_or_messages, dict) and "contents" in payload_or_messages:
        payload = payload_or_messages.copy()
    elif isinstance(payload_or_messages, list):
        contents = []
        for msg in payload_or_messages:
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content", "")
            
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        parts.append({"text": str(item.get("text", ""))})
                    elif isinstance(item, dict) and item.get("type") == "image_url":
                        img_url = item.get("image_url", {}).get("url", "")
                        if "base64," in img_url:
                            b64_data = img_url.split("base64,")[-1]
                            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64_data}})
                contents.append({"role": role, "parts": parts})
            else:
                contents.append({"role": role, "parts": [{"text": str(content)}]})
        payload = {"contents": contents}
    elif isinstance(payload_or_messages, dict) and "messages" in payload_or_messages:
        contents = []
        for msg in payload_or_messages.get("messages", []):
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content", "")
            if isinstance(content, list):
                parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        parts.append({"text": str(item.get("text", ""))})
                    elif isinstance(item, dict) and item.get("type") == "image_url":
                        img_url = item.get("image_url", {}).get("url", "")
                        if "base64," in img_url:
                            b64_data = img_url.split("base64,")[-1]
                            parts.append({"inline_data": {"mime_type": "image/jpeg", "data": b64_data}})
                contents.append({"role": role, "parts": parts})
            else:
                contents.append({"role": role, "parts": [{"text": str(content)}]})
        payload = {"contents": contents}
    else:
        payload = {"contents": [{"role": "user", "parts": [{"text": str(payload_or_messages)}]}]}
    
    payload.pop("response_format", None)
    
    backoff_delay = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            if config.DEBUG_MODE:
                log_info(f"[GEMINI] Sending request (attempt {attempt + 1}/{max_retries})")
            
            response = requests.post(url, headers=headers, json=payload, timeout=60)
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
            
            gemini_data = response.json()
            
            # Safe extraction of response text
            candidates = gemini_data.get("candidates", [])
            text_result = ""
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                text_result = "".join([p.get("text", "") for p in parts if "text" in p])
            
            if not text_result:
                raise ValueError("Empty text result from Gemini API response")
            
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": text_result
                    }
                }]
            }
            
        except requests.exceptions.RequestException as e:
            log_error(f"[GEMINI] Request failed (attempt {attempt + 1}/{max_retries}): {str(e)}")
            last_error = str(e)
            if attempt == max_retries - 1:
                raise Exception(f"[GEMINI] Max retries exceeded: {last_error}")
            time.sleep(backoff_delay)
            backoff_delay *= 2
    
    raise Exception(f"[GEMINI] Max retries exceeded: {last_error}")

def call_api(payload_or_messages, max_retries: int = 4) -> dict:
    """Smart routing function that detects API type and calls appropriate handler."""
    model_name = getattr(config, "MODEL_NAME", "nvidia/nemotron-3-ultra-550b-a55b:free")
    api_type = detect_api_type(model_name)
    
    log_info(f"[API ROUTER] Model: {model_name} -> Using {api_type.upper()} API")
    
    if api_type == "gemini":
        return call_gemini_api(payload_or_messages, max_retries)
    else:
        return call_openrouter_api(payload_or_messages, max_retries)