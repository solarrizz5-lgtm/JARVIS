# 🤖 J.A.R.V.I.S. // AI Assistant Core

> **API Setup, Configuration, and Troubleshooting Guide**
> Comprehensive documentation for integrating OpenRouter and Gemini models into your J.A.R.V.I.S. environment.

---

## 🚀 Quick Start

**1. Obtain an OpenRouter API Key**

* Navigate to [OpenRouter.ai](https://openrouter.ai/) and log in.
* Go to **Settings → API Keys**.
* Create and copy your new key (must start with `sk-or-...`).

**2. Configure Your Environment**
Choose one of the following methods to inject your key into the system:

**Method A: Environment Variable (Recommended)**

```bash
# Windows (CMD)
set OPENROUTER_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:OPENROUTER_API_KEY="your_api_key_here"

# Linux/Mac
export OPENROUTER_API_KEY="your_api_key_here"

```

**Method B: Configuration File**
Create or edit `jarvis_config.json` in the root `JARVIS-main` directory:

```json
{
  "openrouter_api_key": "your_api_key_here",
  "model_name": "nvidia/nemotron-3-ultra-550b-a55b:free"
}

```

**3. Initialize System**

```bash
cd JARVIS-main
python jarvis/main.py

```

---

Here is the updated section formatted to match your requested layout exactly:

## 🧠 Model Compatibility & Selection

J.A.R.V.I.S. requires models with **Vision Capability**, **Long Context**, and strict **JSON Instruction Following**.

| Model ID | Tier | Vision | JSON | Context | Status | Tokens |
| --- | --- | --- | --- | --- | --- | --- |
| `nvidia/nemotron-3-ultra-550b-a55b:free` | Free | ✅ | ✅ | 1M | ✅ **Working** | No Token Usage |
| `google/gemini-3.6-flash` | Free / Paid | ✅ | ✅ | 1M | ✅ **Working (Recommended)** | Token Usage Medium |
| `google/gemini-3.5-flash-lite` | Free / Paid | ✅ | ✅ | 1M | ✅ **Working (Recommended)** | Token Usage Very Low |
| `google/gemini-3.1-pro` | Free / Paid | ✅ | ✅ | 1M | ✅ **Working** | Token Usage Very High |

---

## 🛠️ Diagnostics & Troubleshooting

### Resolving 400 Bad Request Errors

If the API returns a status 400, verify the following:

* **Verify API Key:** Ensure it is 30+ characters, starts with `sk-or-`, and contains no spaces. Test visibility via `echo %OPENROUTER_API_KEY%` (Windows) or `echo $OPENROUTER_API_KEY` (Mac/Linux).
* **Validate Model Name:** Check [OpenRouter Models](https://openrouter.ai/models) to ensure the model ID matches your `jarvis_config.json` exactly.
* **Enable Debug Mode:** Run J.A.R.V.I.S. with extended logging to inspect payloads.
```bash
# Windows
set JARVIS_DEBUG=true
python jarvis/main.py

```



### Common Error Codes

* **"OPENROUTER_API_KEY not configured"**
*Fix:* Apply your key using Method A or B.
* **"Model X not found"**
*Fix:* Update `config.py` or `jarvis_config.json` with a valid model ID from the table above.
* **"Rate limit exceeded (429)"**
*Fix:* The free tier allows ~20 requests/minute. Wait 60 seconds before retrying, or upgrade to a paid tier.

---

## 🧪 System Testing

Run this standalone script to verify API connectivity without launching the full GUI:

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
    print("✅ API call successful")
    print(f"Response: {result['choices'][0]['message']['content']}")
except Exception as e:
    print(f"❌ API call failed: {e}")

```

Execute via terminal: `python test_api.py`

---

## 📊 API Rate Limits Overview

* **Free Tier:** 20 requests/minute | 200 requests/day | No payment method required.
* **Paid Tier:** Unlimited requests/minute | Premium model access | Requires purchased credits.

Check [OpenRouter Status](https://status.openrouter.ai) for live API health or visit [OpenRouter Support](https://openrouter.ai/support) for account issues.
