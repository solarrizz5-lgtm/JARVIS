# JARVIS API Setup and Troubleshooting Guide

## Quick Start

### 1. Get Your OpenRouter API Key

1. Visit [OpenRouter.ai](https://openrouter.ai)
2. Sign up or log in
3. Go to **Settings** → **API Keys**
4. Create a new API key
5. Copy the key (starts with `sk-or-...`)

### 2. Set Your API Key

Choose ONE method:

**Method A: Environment Variable (Recommended)**
```bash
# Windows (CMD)
set OPENROUTER_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:OPENROUTER_API_KEY="your_api_key_here"

# Linux/Mac
export OPENROUTER_API_KEY="your_api_key_here"
```

**Method B: Config File**
1. Create/edit `jarvis_config.json` in the JARVIS-main directory
2. Add:
```json
{
  "openrouter_api_key": "your_api_key_here",
  "model_name": "nvidia/nemotron-3-ultra-550b-a55b:free"
}
```

### 3. Run JARVIS
```bash
cd JARVIS-main
python jarvis/main.py
```

---

## Troubleshooting 400 Bad Request Errors

### Problem: "OpenRouter API returned status 400: Bad Request"

**Root Causes:**
1. **Invalid Model Name** - Model doesn't exist or isn't available
2. **Malformed Request** - JSON payload has syntax errors
3. **Missing/Invalid API Key** - API key is empty, too short, or invalid
4. **Unsupported Parameters** - Model doesn't support `response_format` or other options

### Solution Steps

#### Step 1: Verify API Key
```bash
# Check if API key is set
echo %OPENROUTER_API_KEY%  # Windows
echo $OPENROUTER_API_KEY   # Linux/Mac
```

**What to look for:**
- Should start with `sk-or-`
- Should be at least 30+ characters
- Should NOT contain spaces

If empty, set it using methods above.

#### Step 2: Validate Your Model Name

**Recommended Models (Tested & Working):**
```
✅ nvidia/nemotron-3-ultra-550b-a55b:free  (FREE, 550B params, vision + JSON)
✅ meta-llama/llama-3.3-70b-instruct:free   (FREE, 70B params, vision + JSON)
✅ openrouter/free                           (FREE, auto-selects best model)
```

**To check availability:**
1. Visit https://openrouter.ai/models
2. Look for your model in the list
3. Check if it has a `Free` tag
4. Copy the exact model ID

**Update your model:**
- Edit `jarvis_config.json`:
```json
{
  "model_name": "nvidia/nemotron-3-ultra-550b-a55b:free"
}
```

- Or edit `config.py`:
```python
MODEL_NAME = "nvidia/nemotron-3-ultra-550b-a55b:free"
```

#### Step 3: Check Request Format

The system will log the request. Look for messages like:
```
[INFO] Using OpenRouter model: nvidia/nemotron-3-ultra-550b-a55b:free
[INFO] Sending request to OpenRouter: model=nvidia/nemotron-3-ultra-550b-a55b:free, messages=1
```

#### Step 4: Enable Debug Mode

```bash
# Windows
set JARVIS_DEBUG=true
python jarvis/main.py

# Linux/Mac
export JARVIS_DEBUG=true
python jarvis/main.py
```

This will print:
- Complete API request payload (first 500 chars)
- Complete API response
- All error details

---

## Model Compatibility

### What JARVIS Needs

1. **Vision Capability** - Must support image inputs (for screenshots)
2. **Long Context** - Should support reasonably long prompts
3. **Instruction Following** - Should follow JSON schema instructions

### Model Capability Matrix

| Model | Free? | Vision? | JSON? | Context | Status |
|-------|-------|---------|-------|---------|--------|
| nvidia/nemotron-3-ultra-550b-a55b | ✅ | ✅ | ✅ | 1M | ✅ Working |
| meta-llama/llama-3.3-70b-instruct | ✅ | ✅ | ✅ | 128K | ✅ Working |
| openrouter/free | ✅ | ✅ | varies | varies | ✅ Working |
| gpt-4-vision | ❌ | ✅ | ✅ | 128K | ✅ Working |
| claude-3-sonnet | ❌ | ❌ | ✅ | 200K | ⚠️ No Vision |
| llama-2-70b | ✅ | ❌ | varies | 4K | ⚠️ No Vision |

---

## Common Error Messages & Fixes

### Error: "OPENROUTER_API_KEY not configured"
**Fix:** Set your API key using Method A or B above

### Error: "API key format invalid or too short"
**Fix:** 
- Check your API key is 30+ characters
- Make sure it starts with `sk-or-`
- Generate a new key if unsure

### Error: "Payload missing 'messages' field"
**Fix:** Usually a bug, contact support

### Error: "Model X not found"
**Fix:** 
- Visit https://openrouter.ai/models
- Find the correct model name
- Update config.py or jarvis_config.json

### Error: "Rate limit exceeded"
**Fix:** 
- Free tier is limited to ~20 requests/minute
- Wait a minute before retrying
- Consider upgrading to paid tier on OpenRouter

---

## Testing Your Setup

### Quick Test Script

```python
# test_api.py
import os
from jarvis.ai.client import call_openrouter_api

api_key = os.getenv("OPENROUTER_API_KEY")
if not api_key:
    print("❌ API key not set")
else:
    print(f"✅ API key set (length: {len(api_key)})")

try:
    result = call_openrouter_api([{
        "role": "user",
        "content": "Say 'Hello from JARVIS'"
    }])
    print(f"✅ API call successful")
    print(f"Response: {result['choices'][0]['message']['content']}")
except Exception as e:
    print(f"❌ API call failed: {e}")
```

Run it:
```bash
python test_api.py
```

---

## Still Having Issues?

1. **Check logs**: Look in `JARVIS-main/logs/actions.log`
2. **Enable debug**: Set `JARVIS_DEBUG=true` environment variable
3. **Verify model**: Test with `openrouter/free` (auto-selector)
4. **Check OpenRouter status**: https://status.openrouter.ai
5. **Contact support**: Visit https://openrouter.ai/support

---

## Advanced Configuration

### Use Different Free Model

**In config.py:**
```python
MODEL_NAME = "meta-llama/llama-3.3-70b-instruct:free"
```

**In jarvis_config.json:**
```json
{
  "model_name": "openrouter/free"
}
```

### Use Paid Model (for better reliability)

**Get credits on OpenRouter:**
1. Visit https://openrouter.ai/account/credits
2. Add payment method
3. Purchase credits

**Then use any model:**
```python
MODEL_NAME = "openai/gpt-4-turbo-preview"
```

---

## Model Recommendations

**Best Overall (FREE):**
```
nvidia/nemotron-3-ultra-550b-a55b:free
```
Why: 550B params, supports vision, supports JSON, 1M context, completely free

**Best Reliability (PAID):**
```
openai/gpt-4-turbo-preview
```
Why: Industry standard, most reliable, best instruction following

**Best Speed (FREE):**
```
openrouter/free
```
Why: Auto-selects fastest available free model

---

## API Rate Limits

**Free Tier (OpenRouter):**
- 20 requests/minute
- 200 requests/day
- No payment needed

**Paid Tier:**
- Depends on purchased credits
- Unlimited requests/minute
- Better model selection

---

Last Updated: September 2026
For latest info: https://openrouter.ai/docs
