import json
import time
from jarvis import config
from jarvis.ai.client import call_api, detect_api_type
from jarvis.ai.vision import capture_screen_b64
from jarvis.ai.memory import AgentMemory
from jarvis.voice.tts import speak
from jarvis.utils.logger import log_info, log_error, log_action, save_error_snapshot

memory = AgentMemory()

def parse_decision(raw_response: str) -> dict:
    """Clean and strictly validate model JSON response."""
    if not raw_response:
        raise ValueError("Empty model response received.")
        
    clean = raw_response.strip()
    if clean.startswith("```json"):
        clean = clean[7:]
    elif clean.startswith("```"):
        clean = clean[3:]
    if clean.endswith("```"):
        clean = clean[:-3]
    
    clean_json = clean.strip()
    decision = json.loads(clean_json)
    
    if not isinstance(decision, dict):
        raise ValueError("Invalid schema: parsed output is not a JSON object.")
        
    if "action" not in decision and "type" not in decision:
        raise ValueError("Invalid schema: missing 'action' or 'type' key in decision.")
        
    return decision

def get_next_action(goal: str, screen_b64: str, step_number: int) -> str:
    """Prompt the vision model for the single next UI action."""
    prompt = f"""You are an autonomous GUI control agent operating like JARVIS.
MISSION: {goal}
CURRENT STEP: {step_number}

CRITICAL RULES:
1. Choose exactly one next action based on the screenshot.
2. Ensure x and y coordinates are percentages (5-95) relative to the screen dimensions.
3. Include a "speak" field ONLY when you want JARVIS to voice something aloud to the user.
4. Return ONLY raw, valid JSON matching one of these schemas:

{{"action":"click","x":50,"y":50,"speak":"Optional spoken text","reason":"Internal logic explanation"}}
{{"action":"double_click","x":50,"y":50,"speak":"","reason":""}}
{{"action":"right_click","x":50,"y":50,"speak":"","reason":""}}
{{"action":"type","text":"text to type","press_enter":false,"speak":"","reason":""}}
{{"action":"press","key":"enter","speak":"","reason":""}}
{{"action":"hotkey","keys":["ctrl","l"],"speak":"","reason":""}}
{{"action":"wait","seconds":3,"speak":"","reason":""}}
{{"action":"requires_user_intervention","speak":"I need your help with this part sir","reason":""}}
{{"action":"done","speak":"Task complete, sir.","reason":""}}
"""

    current_model = getattr(config, "MODEL_NAME", "nvidia/nemotron-3-ultra-550b-a55b:free")
    api_type = detect_api_type(current_model)

    # Format multimodal payload depending on whether OpenRouter or Gemini REST is used
    if api_type == "gemini":
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": screen_b64
                            }
                        }
                    ]
                }
            ]
        }
    else:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{screen_b64}"
                        }
                    }
                ]
            }
        ]
        payload = {"messages": messages}
    
    try:
        data = call_api(payload)
        if not data or "choices" not in data or not data["choices"]:
            raise ValueError("Invalid API response structure: missing choices array")
        
        choice = data["choices"][0]
        if "message" not in choice or "content" not in choice["message"]:
            raise ValueError("Invalid API response structure: missing message content")
        
        return choice["message"]["content"]
    except Exception as e:
        log_error(f"Failed to get next action from AI: {e}")
        raise

def run_agent(goal: str):
    """Executes the multi-step vision-action loop with dynamic model-driven speech."""
    step_number = 0
    consecutive_errors = 0
    recent_actions = []

    log_info(f"Initiating agent task: '{goal}'")
    speak("Working on it, sir.")

    from jarvis.automation.mouse import execute_mouse_action
    from jarvis.automation.keyboard import execute_keyboard_action

    while step_number < config.MAX_STEPS_PER_MISSION:
        if not config.AGENT_RUNNING:
            log_error("Agent halted by emergency stop.")
            break

        step_number += 1
        raw_image = None

        try:
            screen_b64, native_w, native_h, raw_image = capture_screen_b64()
            raw_response = get_next_action(goal, screen_b64, step_number)
            decision = parse_decision(raw_response)

            action_type = decision.get("action")
            reason = decision.get("reason", "No reason provided.")
            spoken_text = decision.get("speak")

            log_info(f"Step {step_number}: {str(action_type).upper()} | Reason: {reason}")

            if spoken_text and spoken_text.strip():
                speak(spoken_text.strip())

            # Infinite Loop Detection
            action_signature = (action_type, decision.get("x"), decision.get("y"), decision.get("text"))
            recent_actions.append(action_signature)
            if len(recent_actions) > 4:
                recent_actions.pop(0)

            if len(recent_actions) == 4 and all(a == recent_actions[0] for a in recent_actions):
                speak("I am stuck in an action loop. Halting task execution.")
                log_error("Agent stuck in repetitive action loop.")
                break

            log_action(goal, step_number, decision, success=True)

            completed = False
            if action_type in ["click", "double_click", "right_click"]:
                execute_mouse_action(decision, native_w, native_h)
            elif action_type in ["type", "press", "hotkey"]:
                execute_keyboard_action(decision)
            elif action_type == "wait":
                time.sleep(float(decision.get("seconds", 3)))
            elif action_type in ["requires_user_intervention", "done"]:
                completed = True

            if completed:
                break

            consecutive_errors = 0
            time.sleep(config.ACTION_DELAY_SECONDS)

        except Exception as error:
            log_action(goal, step_number, {"error": str(error)}, success=False)
            if raw_image:
                save_error_snapshot(raw_image, str(error))

            consecutive_errors += 1
            if consecutive_errors >= config.MAX_CONSECUTIVE_ERRORS:
                speak("Encountered repeated errors. Aborting sequence.")
                log_error("Max consecutive errors hit. Sequence aborted.")
                break

            retry_delay = min(2 ** consecutive_errors, 30)
            time.sleep(retry_delay)

def handle_user_command(command: str):
    """Classifies user input as conversational QA or GUI desktop task using persistent memory."""
    memory.add_turn("user", command)
    
    # Context formatted cleanly as plain text string to prevent Gemini nested array syntax errors
    context_str = json.dumps(memory.get_context())
    
    classification_prompt = f"""Recent Context: {context_str}
Current User Command: "{command}"

Classify command: Is it a conversational question, or a desktop GUI task?
Return ONLY raw JSON matching one of these two formats:
{{"type": "chat", "answer": "Response to speak aloud"}}
{{"type": "automation", "mission": "Detailed task description"}}
"""

    current_model = getattr(config, "MODEL_NAME", "nvidia/nemotron-3-ultra-550b-a55b:free")
    api_type = detect_api_type(current_model)

    if api_type == "gemini":
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": classification_prompt}]
                }
            ]
        }
    else:
        payload = {
            "messages": [
                {"role": "user", "content": classification_prompt}
            ]
        }

    try:
        data = call_api(payload)
        if not data or "choices" not in data or not data["choices"]:
            raise ValueError("Invalid API response structure from server.")
        
        res_text = data["choices"][0].get("message", {}).get("content", "")
        if not res_text:
            raise ValueError("Empty response content from API.")
        
        parsed = parse_decision(res_text)

        if parsed.get("type") == "chat":
            ans = parsed.get("answer", "Standing by.")
            memory.add_turn("assistant", ans)
            log_info(f"JARVIS Response: {ans}")
            speak(ans)
        else:
            mission = parsed.get("mission", command)
            memory.add_turn("assistant", f"Executing: {mission}")
            run_agent(mission)

    except Exception as error:
        log_error(f"Command routing error: {error}. Falling back to default execution.")
        speak("Processing request.")
        run_agent(command)