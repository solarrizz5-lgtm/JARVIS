import json
import time
from jarvis import config
from jarvis.ai.client import call_gemini_api
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
    if clean.startswith("```json"): clean = clean[7:]
    elif clean.startswith("```"): clean = clean[3:]
    if clean.endswith("```"): clean = clean[:-3]
    
    decision = json.loads(clean.strip())
    if "action" not in decision:
        raise ValueError("Invalid schema: missing 'action' key in decision.")
    return decision

def get_next_action(goal: str, screen_b64: str, step_number: int) -> str:
    """Prompt the vision model for the single next UI action via OpenRouter chat completions."""
    prompt = f"""
You are an autonomous GUI control agent operating like JARVIS.
MISSION: {goal}
CURRENT STEP: {step_number}

CRITICAL RULES:
1. Choose exactly one next action based on the screenshot.
2. Ensure x and y coordinates are percentages (5-95) relative to the screen dimensions.
3. Include a "speak" field ONLY when you want JARVIS to voice something aloud to the user (e.g., announcing status, confirming progress, or stating completion). If silence is preferred for this step, omit or leave "speak" empty.
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
    
    payload = {
        "messages": messages,
        "response_format": {"type": "json_object"}
    }
    
    data = call_gemini_api(payload)
    return data["choices"][0]["message"]["content"]

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

            log_info(f"Step {step_number}: {action_type.upper()} | Reason: {reason}")

            # Speak dynamically if the model chose to voice something in this step
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
    context_window = memory.get_context()

    classification_prompt = f"""
Recent Context: {json.dumps(context_window)}
Current User Command: "{command}"

Classify command: Is it a conversational question, or a desktop GUI task?
Return JSON:
{{"type": "chat", "answer": "Response to speak aloud"}} OR
{{"type": "automation", "mission": "Detailed task description"}}
"""
    messages = context_window + [{"role": "user", "content": classification_prompt}]
    payload = {
        "messages": messages,
        "response_format": {"type": "json_object"}
    }

    try:
        data = call_gemini_api(payload)
        res_text = data["choices"][0]["message"]["content"]
        parsed = json.loads(res_text)

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