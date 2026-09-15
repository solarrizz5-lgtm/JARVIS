import os
import time
import requests
from jarvis import config
from jarvis.utils.logger import log_error, log_info

def call_openrouter_api(payload_or_messages, max_retries: int = 4) -> dict:
    """
    Sends requests to OpenRouter using a single primary model without triggering
    OpenRouter's multi-model fallback array limit (max 3 items).
    
    Args:
        payload_or_messages: Request payload or list of messages
        max_retries: Maximum number of retry attempts
        
    Returns:
        Response JSON dict with standardized OpenAI-compatible format
        
    Raises:
        Exception: If max retries exceeded or API returns error
    """
    api_key = getattr(config, "OPENROUTER_API_KEY", "") or os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not configured")
    
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

    # Construct payload ensuring NO 'models' array is passed to prevent 400 errors
    if isinstance(payload_or_messages, list):
        payload = {
            "model": primary_model,
            "messages": payload_or_messages
        }
    elif isinstance(payload_or_messages, dict):
        payload = payload_or_messages.copy()
        payload.pop("models", None)  # Strip out multi-model array if present
        if "model" not in payload:
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

    backoff_delay = 3
    
    for attempt in range(max_retries):
        try:
            response = requests.post(
                url, 
                headers=headers, 
                json=payload, 
                timeout=45
            )
            
            if response.status_code == 429:
                log_info(f"OpenRouter Rate Limit (429). Retrying in {backoff_delay}s...")
                time.sleep(backoff_delay)
                backoff_delay *= 2
                continue
                
            if response.status_code != 200:
                log_error(f"OpenRouter API returned status {response.status_code}: {response.text}")
                response.raise_for_status()
                
            return response.json()
            
        except requests.exceptions.RequestException as e:
            log_error(f"OpenRouter API request failed (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise e
            time.sleep(backoff_delay)
            backoff_delay *= 2
            
    raise Exception("Max retries exceeded for OpenRouter API call.")

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
        raise ValueError("GEMINI_API_KEY not configured")
    
    model_name = getattr(config, "MODEL_NAME", "gemini-2.5-flash")
    clean_model_name = model_name.split("/")[-1] if "/" in model_name else model_name
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    
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
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            if response.status_code == 429:
                log_info(f"Gemini Rate Limit (429). Retrying in {backoff_delay}s...")
                time.sleep(backoff_delay)
                backoff_delay *= 2
                continue
            if response.status_code != 200:
                log_error(f"Gemini API returned status {response.status_code}: {response.text}")
                response.raise_for_status()
            
            # Map Gemini response structure back to OpenAI/OpenRouter style format for compatibility
            gemini_data = response.json()
            text_result = gemini_data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": text_result
                    }
                }]
            }
        except requests.exceptions.RequestException as e:
            log_error(f"Gemini API request failed (Attempt {attempt + 1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                raise e
            time.sleep(backoff_delay)
            backoff_delay *= 2

    raise Exception("Max retries exceeded for Gemini API call.")
