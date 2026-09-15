import os
import time
import requests
import json
from jarvis import config
from jarvis.utils.logger import log_error, log_info

# Model capability mapping
MODEL_CAPABILITIES = {
    "vision": ["gpt-4-vision", "claude-3-vision", "gemini", "llava", "nemotron-3-ultra"],
    "json_mode": ["gpt-4", "gpt-3.5-turbo", "claude-3", "gemini", "llama", "nemotron-3"],
}

FREE_FALLBACK_MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openrouter/free",
]

def get_model_capabilities(model_name: str) -> dict:
    """Determine which capabilities a model supports based on its name."""
    model_lower = model_name.lower()
    capabilities = {
        "vision": False,
        "json_mode": False,
    }
    
    for cap, models in MODEL_CAPABILITIES.items():
        for supported_model in models:
            if supported_model in model_lower:
                capabilities[cap] = True
                break
    
    return capabilities

def validate_api_key(api_key: str) -> bool:
    """Validate that API key looks reasonable (basic check)."""
    if not api_key or not isinstance(api_key, str):
        return False
    if len(api_key) < 10:
        return False
    return True

def call_openrouter_api(payload_or_messages, max_retries: int = 4, model_override: str = None) -> dict:
    """
    Sends requests to OpenRouter using a single primary model without triggering
    OpenRouter's multi-model fallback array limit (max 3 items).
    
    Args:
        payload_or_messages: Request payload or list of messages
        max_retries: Maximum number of retry attempts
        model_override: Override the configured model name
        
    Returns:
        Response JSON dict with standardized OpenAI-compatible format
        
    Raises:
        Exception: If max retries exceeded or API returns error
    """
    api_key = getattr(config, "OPENROUTER_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("[CRITICAL] OPENROUTER_API_KEY not configured. Please set your API key.")
    
    if not validate_api_key(api_key):
        raise ValueError(f"[CRITICAL] API key format invalid or too short. Expected minimum 10 characters, got {len(api_key)}.")
    
    base_url = getattr(config, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    url = f"{base_url}/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5000",
        "X-Title": "Jarvis Assistant"
    }
    
    # Determine model to use
    primary_model = model_override or getattr(config, "MODEL_NAME", "nvidia/nemotron-3-ultra-550b-a55b:free")
    if not primary_model or not isinstance(primary_model, str):
        primary_model = "nvidia/nemotron-3-ultra-550b-a55b:free"
    
    log_info(f"Using OpenRouter model: {primary_model}")
    
    # Get model capabilities to determine feature support
    capabilities = get_model_capabilities(primary_model)
    
    # Construct payload ensuring proper model and message structure
    if isinstance(payload_or_messages, list):
        payload = {
            "model": primary_model,
            "messages": payload_or_messages
        }
    elif isinstance(payload_or_messages, dict):
        payload = payload_or_messages.copy()
        # Remove problematic fields
        payload.pop("models", None)  # Strip out multi-model array if present
        payload.pop("model", None)   # Remove old model field to ensure fresh assignment
        
        # Always set model explicitly
        payload["model"] = primary_model
        
        # Handle Gemini-style contents conversion to OpenAI messages
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
    
    # Only include response_format if model supports JSON mode
    if capabilities["json_mode"] and "response_format" in payload:
        log_info("Model supports JSON mode, keeping response_format")
    elif "response_format" in payload:
        log_info(f"Model {primary_model} may not support JSON mode, attempting anyway")
        # Don't remove it - let OpenRouter handle it
    
    # Validate payload structure
    if "messages" not in payload:
        raise ValueError("Payload missing 'messages' field")
    
    if not isinstance(payload["messages"], list):
        raise ValueError("'messages' must be a list")
    
    if not payload["messages"]:
        raise ValueError("'messages' list is empty")
    
    log_info(f"Sending request to OpenRouter: model={payload['model']}, messages={len(payload['messages'])}")
    
    backoff_delay = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Log payload for debugging (without sensitive data)
            debug_payload = payload.copy()
            debug_payload["messages"] = f"[{len(payload['messages'])} message(s)]"
            log_info(f"API Payload: {json.dumps(debug_payload, indent=2)[:500]}...")  # First 500 chars
            
            response = requests.post(
                url, 
                headers=headers, 
                json=payload, 
                timeout=45
            )
            
            # Log response status
            log_info(f"OpenRouter Response Status: {response.status_code}")
            
            if response.status_code == 429:
                log_info(f"OpenRouter Rate Limit (429). Retrying in {backoff_delay}s...")
                time.sleep(backoff_delay)
                backoff_delay *= 2
                continue
            
            if response.status_code == 400:
                error_text = response.text
                log_error(f"OpenRouter API returned 400 Bad Request: {error_text}")
                last_error = error_text
                
                # Try fallback model on 400 error
                if attempt < max_retries - 1 and primary_model not in FREE_FALLBACK_MODELS:
                    log_info(f"Attempting with fallback model...")
                    return call_openrouter_api(payload_or_messages, max_retries=1, model_override=FREE_FALLBACK_MODELS[0])
                
                response.raise_for_status()
                
            if response.status_code != 200:
                error_text = response.text
                log_error(f"OpenRouter API returned status {response.status_code}: {error_text}")
                last_error = error_text
                response.raise_for_status()
            
            result = response.json()
            log_info("OpenRouter API call successful")
            return result
            
        except requests.exceptions.RequestException as e:
            log_error(f"OpenRouter API request failed (Attempt {attempt + 1}/{max_retries}): {str(e)}")
            last_error = str(e)
            if attempt == max_retries - 1:
                raise Exception(f"Max retries exceeded for OpenRouter API call. Last error: {last_error}")
            time.sleep(backoff_delay)
            backoff_delay *= 2
        except ValueError as e:
            log_error(f"Payload validation error: {e}")
            raise
            
    raise Exception(f"Max retries exceeded for OpenRouter API call. Last error: {last_error}")

def call_gemini_api(payload_or_messages, max_retries: int = 4) -> dict:
    """
    Direct handler for Google Gemini API when MODEL_NAME is set to a Gemini model.
    
    Args:
        payload_or_messages: Request payload or list of messages
        max_retries: Maximum number of retry attempts
        
    Returns:
        Response dict in OpenAI-compatible format for consistency
        
    Raises:
        Exception: If max retries exceeded or API returns error
    """
    api_key = getattr(config, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not configured. Use OpenRouter API instead.")
    
    model_name = getattr(config, "MODEL_NAME", "gemini-2.5-flash")
    clean_model_name = model_name.split("/")[-1] if "/" in model_name else model_name
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
    log_info(f"Using Gemini model: {clean_model_name}")
    
    # Format payload for Gemini API structure
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

    backoff_delay = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            log_info(f"Gemini Response Status: {response.status_code}")
            
            if response.status_code == 429:
                log_info(f"Gemini Rate Limit (429). Retrying in {backoff_delay}s...")
                time.sleep(backoff_delay)
                backoff_delay *= 2
                continue
            
            if response.status_code != 200:
                error_text = response.text
                log_error(f"Gemini API returned status {response.status_code}: {error_text}")
                last_error = error_text
                response.raise_for_status()
            
            # Map Gemini response structure back to OpenAI/OpenRouter style format for compatibility
            gemini_data = response.json()
            text_result = gemini_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            
            if not text_result:
                raise ValueError("Empty text result from Gemini API")
            
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": text_result
                    }
                }]
            }
        except requests.exceptions.RequestException as e:
            log_error(f"Gemini API request failed (Attempt {attempt + 1}/{max_retries}): {str(e)}")
            last_error = str(e)
            if attempt == max_retries - 1:
                raise Exception(f"Max retries exceeded for Gemini API call. Last error: {last_error}")
            time.sleep(backoff_delay)
            backoff_delay *= 2

    raise Exception(f"Max retries exceeded for Gemini API call. Last error: {last_error}")
