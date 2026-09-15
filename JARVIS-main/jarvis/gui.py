import datetime
import json
import math
import os
import re
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

from jarvis import config
from jarvis.ai.planner import handle_user_command
from jarvis.utils.logger import log_error, log_info
from jarvis.voice.input import listen_and_transcribe
from jarvis.voice.tts import speak

# ROOT_DIR points to JARVIS-main/
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(ROOT_DIR, "jarvis_config.json")
ACTIONS_LOG_FILE = os.path.join(ROOT_DIR, "logs", "actions.log")


def load_persistent_config():
  if os.path.exists(CONFIG_FILE):
    try:
      with open(CONFIG_FILE, "r") as f:
        data = json.load(f)
        or_key = data.get("openrouter_api_key") or data.get("api_key", "")
        gemini_key = data.get("gemini_api_key", "")
        model = data.get(
            "model_name", "nvidia/nemotron-3-ultra-550b-a55b:free"
        )

        if or_key:
          os.environ["OPENROUTER_API_KEY"] = or_key
          config.OPENROUTER_API_KEY = or_key
        if gemini_key:
          os.environ["GEMINI_API_KEY"] = gemini_key
          config.GEMINI_API_KEY = gemini_key
        if model:
          config.MODEL_NAME = model
        return or_key, gemini_key, model
    except Exception as e:
      log_error(f"Failed to load config file: {e}")
  return (
      os.getenv("OPENROUTER_API_KEY", ""),
      os.getenv("GEMINI_API_KEY", ""),
      getattr(config, "MODEL_NAME", "nvidia/nemotron-3-ultra-550b-a55b:free"),
  )


def save_persistent_config(or_key, gemini_key, model):
  data = {
      "openrouter_api_key": or_key,
      "gemini_api_key": gemini_key,
      "model_name": model,
  }
  try:
    with open(CONFIG_FILE, "w") as f:
      json.dump(data, f, indent=4)
  except Exception as e:
    log_error(f"Failed to save config file: {e}")

  os.environ["OPENROUTER_API_KEY"] = or_key
  config.OPENROUTER_API_KEY = or_key
  os.environ["GEMINI_API_KEY"] = gemini_key
  config.GEMINI_API_KEY = gemini_key
  config.MODEL_NAME = model

  try:
    if or_key:
      os.system(f'setx OPENROUTER_API_KEY "{or_key}" >nul')
    if gemini_key:
      os.system(f'setx GEMINI_API_KEY "{gemini_key}" >nul')
  except Exception:
    pass


class RoundedBox(tk.Canvas):

  """Custom Canvas Widget to render smooth rounded-corner frames."""

  def __init__(
      self,
      parent,
      width,
      height,
      radius=15,
      bg_color="#0b0f19",
      border_color="#00f0ff",
      **kwargs,
  ):
    super().__init__(
        parent,
        width=width,
        height=height,
        bg=parent["bg"],
        highlightthickness=0,
        **kwargs,
    )
    self.radius = radius
    self.bg_color = bg_color
    self.border_color = border_color
    self.w = width
    self.h = height
    self.draw_rounded_rect()

  def draw_rounded_rect(self):
    self.delete("all")
    r = self.radius
    w, h = self.w, self.h

    self.create_arc(
        (0, 0, 2 * r, 2 * r),
        start=90,
        extent=90,
        fill=self.bg_color,
        outline=self.border_color,
    )
    self.create_arc(
        (w - 2 * r, 0, w, 2 * r),
        start=0,
        extent=90,
        fill=self.bg_color,
        outline=self.border_color,
    )
    self.create_arc(
        (0, h - 2 * r, 2 * r, h),
        start=180,
        extent=90,
        fill=self.bg_color,
        outline=self.border_color,
    )
    self.create_arc(
        (w - 2 * r, h - 2 * r, w, h),
        start=270,
        extent=90,
        fill=self.bg_color,
        outline=self.border_color,
    )

    self.create_rectangle(
        r, 0, w - r, h, fill=self.bg_color, outline=self.bg_color
    )
    self.create_rectangle(
        0, r, w, h - r, fill=self.bg_color, outline=self.bg_color
    )

    self.create_line(r, 0, w - r, 0, fill=self.border_color)
    self.create_line(r, h, w - r, h, fill=self.border_color)
    self.create_line(0, r, 0, h - r, fill=self.border_color)
    self.create_line(w, r, w, h - r, fill=self.border_color)


class JarvisGUI:

  def __init__(self, root):
    self.root = root
    self.root.title("J.A.R.V.I.S. // QUANTUM HUD")
    self.root.geometry("400x740")
    self.root.configure(bg="#050811")
    self.root.resizable(False, False)

    load_persistent_config()

    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "TLabel",
        background="#050811",
        foreground="#00f0ff",
        font=("Segoe UI", 10, "bold"),
    )
    style.configure(
        "TButton",
        background="#0f172a",
        foreground="#00f0ff",
        font=("Segoe UI", 9, "bold"),
        borderwidth=1,
    )

    # Outer Neon Frame
    self.neon_outer_frame = tk.Frame(root, bg="#00bcd4", bd=2, relief="flat")
    self.neon_outer_frame.pack(fill="both", expand=True, padx=8, pady=8)

    self.main_container = tk.Frame(self.neon_outer_frame, bg="#050811")
    self.main_container.pack(fill="both", expand=True, padx=2, pady=2)

    # Header Title
    title_label = tk.Label(
        self.main_container,
        text="J.A.R.V.I.S. // CORE INTERFACE",
        bg="#050811",
        fg="#38bdf8",
        font=("Segoe UI", 11, "bold"),
    )
    title_label.pack(pady=(15, 5))

    # Dynamic Radar Canvas
    self.canvas_size = 170
    self.canvas = tk.Canvas(
        self.main_container,
        width=self.canvas_size,
        height=self.canvas_size,
        bg="#050811",
        highlightthickness=0,
    )
    self.canvas.pack(pady=5)
    self.canvas.bind("<Button-1>", lambda e: self.trigger_manual_listen())

    # Rounded Status Panel Box
    self.status_box = RoundedBox(
        self.main_container,
        width=340,
        height=55,
        radius=12,
        bg_color="#0b0f19",
        border_color="#00f0ff",
    )
    self.status_box.pack(pady=10)

    self.status_label = tk.Label(
        self.status_box,
        text="STATUS: INITIALIZING...",
        bg="#0b0f19",
        fg="#34d399",
        font=("Segoe UI", 9, "bold"),
    )
    self.status_box.create_window(170, 27, window=self.status_label)

    # Rounded Action Log Panel Box
    self.log_box = RoundedBox(
        self.main_container,
        width=340,
        height=110,
        radius=12,
        bg_color="#0a0f1d",
        border_color="#1e293b",
    )
    self.log_box.pack(pady=5)

    self.log_text = tk.Label(
        self.log_box,
        text="[SYSTEM]: Quantum link established.",
        bg="#0a0f1d",
        fg="#94a3b8",
        font=("Consolas", 8),
        anchor="nw",
        justify="left",
        wraplength=310,
    )
    self.log_box.create_window(170, 55, window=self.log_text)

    # Dedicated Rounded Error Diagnostic Terminal Box
    self.error_box = RoundedBox(
        self.main_container,
        width=340,
        height=110,
        radius=12,
        bg_color="#180a0a",
        border_color="#ef4444",
    )
    self.error_box.pack(pady=10)

    self.error_text = tk.Label(
        self.error_box,
        text="[DIAGNOSTICS]: NO ERRORS DETECTED",
        bg="#180a0a",
        fg="#f87171",
        font=("Consolas", 8, "bold"),
        anchor="nw",
        justify="left",
        wraplength=310,
    )
    self.error_box.create_window(170, 55, window=self.error_text)

    # 3 Control Buttons Frame
    self.btn_frame = tk.Frame(self.main_container, bg="#050811")
    self.btn_frame.pack(fill="x", padx=25, pady=10)

    self.btn_frame.grid_columnconfigure(0, weight=1)
    self.btn_frame.grid_columnconfigure(1, weight=1)
    self.btn_frame.grid_columnconfigure(2, weight=1)

    self.listen_btn = ttk.Button(
        self.btn_frame, text="⚡ Listen", command=self.trigger_manual_listen
    )
    self.listen_btn.grid(row=0, column=0, padx=4, sticky="ew", ipady=6)

    self.settings_btn = ttk.Button(
        self.btn_frame, text="⚙ Config", command=self.open_settings
    )
    self.settings_btn.grid(row=0, column=1, padx=4, sticky="ew", ipady=6)

    self.stop_btn = ttk.Button(
        self.btn_frame, text="🛑 Halt", command=self.emergency_stop
    )
    self.stop_btn.grid(row=0, column=2, padx=4, sticky="ew", ipady=6)

    self.running = True
    self.pulse_phase = 0.0

    self.start_animations()
    self.start_log_watcher()
    self.start_background_loop()

  def get_timestamp(self):
    return datetime.datetime.now().strftime("%H:%M:%S")

  def parse_error_code(self, raw_err: str) -> str:
    err_str = str(raw_err)
    timestamp = self.get_timestamp()

    match = re.search(r"\b(200|400|401|403|429|500|502|503)\b", err_str)
    code = match.group(1) if match else None

    if code == "429" or "rate limit" in err_str.lower():
      return (
          f"[{timestamp}] [HTTP 429 RATE LIMIT]\nModel rate limit exceeded."
          " Switch models in Config or wait."
      )
    elif code == "400" or "bad request" in err_str.lower():
      return (
          f"[{timestamp}] [HTTP 400 BAD REQUEST]\nInvalid request format or"
          " prompt rejected by API."
      )
    elif (
        code in ["401", "403"]
        or "unauthorized" in err_str.lower()
        or "forbidden" in err_str.lower()
    ):
      return (
          f"[{timestamp}] [HTTP {code or '401/403'} AUTH ERROR]\nInvalid API"
          " Key. Check settings."
      )
    elif code in ["500", "502", "503"]:
      return (
          f"[{timestamp}] [HTTP {code} SERVER ERROR]\nAPI provider server"
          " outage or overload."
      )
    elif code == "200":
      return f"[{timestamp}] [HTTP 200 OK] Request succeeded."

    return f"[{timestamp}] [ERROR / EXCEPTION]\n{err_str}"

  def update_status(self, text, log_msg="", error_msg=""):
    self.root.after(
        0, lambda: self._safe_update_status(text, log_msg, error_msg)
    )

  def _safe_update_status(self, text, log_msg, error_msg):
    self.status_label.config(text=text)
    timestamp = self.get_timestamp()

    if log_msg:
      self.log_text.config(text=f"[{timestamp}] {log_msg}")

    if error_msg:
      parsed = self.parse_error_code(error_msg)
      self.error_text.config(text=parsed)

  def start_log_watcher(self):
    """Monitors logs/actions.log strictly in read-only mode."""

    def watch_logs():
      # Non-creating check for actions.log in the root logs directory
      while self.running and not os.path.exists(ACTIONS_LOG_FILE):
        time.sleep(1)

      if not self.running:
        return

      with open(ACTIONS_LOG_FILE, "r", encoding="utf-8") as f:
        f.seek(0, os.SEEK_END)
        while self.running:
          line = f.readline()
          if line:
            clean = line.strip()
            if clean:
              is_error = any(
                  term in clean.lower()
                  for term in [
                      "error",
                      "exception",
                      "failed",
                      "400",
                      "401",
                      "403",
                      "429",
                      "500",
                      "503",
                      "rate limit",
                  ]
              )

              if is_error:
                self.update_status("STATUS: ERROR DETECTED", error_msg=clean)
              else:
                self.update_status(
                    self.status_label.cget("text"), log_msg=clean
                )
          else:
            time.sleep(0.5)

    threading.Thread(target=watch_logs, daemon=True).start()

  def trigger_manual_listen(self):
    if not self.get_api_key():
      messagebox.showerror(
          "API Key Missing",
          "Required API Key for the selected model is not set. Please update it"
          " in Settings.",
      )
      return
    config.AGENT_RUNNING = True
    threading.Thread(target=self._listen_task, daemon=True).start()

  def _listen_task(self):
    if not config.AGENT_RUNNING:
      return
    self.update_status("STATUS: LISTENING...", "Listening for user command...")
    speak("Yes, sir? Standing by.")
    try:
      command = listen_and_transcribe(timeout_seconds=6.0)
      if command and config.AGENT_RUNNING:
        self.update_status("STATUS: EXECUTING", f"Command: {command}")
        handle_user_command(command)
        if config.AGENT_RUNNING:
          self.update_status(
              "STATUS: STANDBY (LISTENING)",
              "Task complete. Listening for commands...",
          )
      else:
        if config.AGENT_RUNNING:
          self.update_status(
              "STATUS: STANDBY (LISTENING)", "No command detected. Listening..."
          )
    except Exception as e:
      self.update_status("STATUS: ERROR", error_msg=str(e))

  def emergency_stop(self):
    config.AGENT_RUNNING = False
    self.update_status(
        "STATUS: HALTED",
        "Emergency override activated!",
        error_msg="AGENT HALTED VIA GUI OVERRIDE",
    )
    speak("Emergency stop activated.")
    log_error("Emergency stop triggered via GUI.")

  def open_settings(self):
    settings_win = tk.Toplevel(self.root)
    settings_win.title("JARVIS // SETTINGS")
    settings_win.geometry("400x390")
    settings_win.configure(bg="#050811")
    settings_win.resizable(False, False)
    settings_win.grab_set()

    tk.Label(
        settings_win,
        text="OpenRouter API Key:",
        bg="#050811",
        fg="#00f0ff",
        font=("Segoe UI", 9, "bold"),
    ).pack(anchor="w", padx=25, pady=(10, 2))
    or_key_entry = tk.Entry(
        settings_win,
        width=40,
        show="*",
        font=("Consolas", 9),
        bg="#0f172a",
        fg="#f8fafc",
        insertbackground="#fff",
        relief="flat",
    )
    or_key_entry.pack(padx=25, ipady=3)

    tk.Label(
        settings_win,
        text="Google Gemini API Key:",
        bg="#050811",
        fg="#00f0ff",
        font=("Segoe UI", 9, "bold"),
    ).pack(anchor="w", padx=25, pady=(10, 2))
    gemini_key_entry = tk.Entry(
        settings_win,
        width=40,
        show="*",
        font=("Consolas", 9),
        bg="#0f172a",
        fg="#f8fafc",
        insertbackground="#fff",
        relief="flat",
    )
    gemini_key_entry.pack(padx=25, ipady=3)

    current_or, current_gemini, current_model = load_persistent_config()
    if current_or:
      or_key_entry.insert(0, current_or)
    if current_gemini:
      gemini_key_entry.insert(0, current_gemini)

    tk.Label(
        settings_win,
        text="Primary Model Name:",
        bg="#050811",
        fg="#00f0ff",
        font=("Segoe UI", 9, "bold"),
    ).pack(anchor="w", padx=25, pady=(10, 2))

    models = [
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "google/gemini-3.6-flash",
        "google/gemini-3.5-flash-lite",
        "google/gemini-3.1-pro",
        "openai/gpt-4o",
    ]
    model_dropdown = ttk.Combobox(
        settings_win, values=models, width=38, state="readonly"
    )
    model_dropdown.pack(padx=25, ipady=2)

    if current_model in models:
      model_dropdown.set(current_model)
    else:
      model_dropdown.set("nvidia/nemotron-3-ultra-550b-a55b:free")

    def save_and_close():
      new_or = or_key_entry.get().strip()
      new_gemini = gemini_key_entry.get().strip()
      new_model = model_dropdown.get().strip()

      if ("google/" in new_model or "gemini" in new_model) and not new_gemini:
        if not messagebox.askyesno(
            "Warning",
            "You selected a Google Gemini model but did not provide a Gemini"
            " API key. Continue anyway?",
            parent=settings_win,
        ):
          return

      if not new_or and not new_gemini:
        messagebox.showerror(
            "Error",
            "At least one API Key must be provided.",
            parent=settings_win,
        )
        return

      save_persistent_config(new_or, new_gemini, new_model)
      messagebox.showinfo(
          "Success",
          "Core configuration updated successfully!",
          parent=settings_win,
      )
      settings_win.destroy()

    save_btn = ttk.Button(
        settings_win, text="Save Configuration", command=save_and_close
    )
    save_btn.pack(pady=20, ipadx=10, ipady=3)

  def get_api_key(self):
    current_model = getattr(config, "MODEL_NAME", "")
    if "google/" in current_model or "gemini" in current_model:
      return os.getenv("GEMINI_API_KEY", "") or getattr(
          config, "GEMINI_API_KEY", ""
      )
    return os.getenv("OPENROUTER_API_KEY", "") or getattr(
        config, "OPENROUTER_API_KEY", ""
    )

  def start_animations(self):
    def animate():
      if not self.running:
        return

      self.canvas.delete("all")
      cx, cy = self.canvas_size / 2, self.canvas_size / 2

      self.pulse_phase += 0.08
      current_status = self.status_label.cget("text")

      if "HALTED" in current_status or "ERROR" in current_status:
        accent_color = "#ef4444"
      elif "EXECUTING" in current_status:
        accent_color = "#a855f7"
      elif "LISTENING" in current_status:
        accent_color = "#34d399"
      else:
        accent_color = "#00f0ff"

      pulse_offset = math.sin(self.pulse_phase) * 5
      self.canvas.create_oval(
          cx - 65 - pulse_offset,
          cy - 65 - pulse_offset,
          cx + 65 + pulse_offset,
          cy + 65 + pulse_offset,
          outline=accent_color,
          width=2,
      )
      self.canvas.create_arc(
          cx - 55,
          cy - 55,
          cx + 55,
          cy + 55,
          start=15,
          extent=120,
          outline="#ff007f",
          width=2,
          style="arc",
      )
      self.canvas.create_arc(
          cx - 55,
          cy - 55,
          cx + 55,
          cy + 55,
          start=195,
          extent=120,
          outline="#00f0ff",
          width=2,
          style="arc",
      )

      mic_w, mic_h = 18, 30
      self.canvas.create_oval(
          cx - mic_w,
          cy - mic_h,
          cx + mic_w,
          cy + mic_h - 10,
          outline="#ffffff",
          width=2,
          fill="#050811",
      )
      self.canvas.create_line(
          cx - 15, cy + 18, cx + 15, cy + 18, fill=accent_color, width=2
      )

      self.root.after(40, animate)

    animate()

  def start_background_loop(self):
    def background_loop():
      if self.get_api_key():
        speak("JARVIS online. Systems nominal. Standing by.")
        self.update_status(
            "STATUS: STANDBY (LISTENING)", "Listening for commands..."
        )
      else:
        self.update_status(
            "STATUS: API KEY MISSING",
            error_msg="CONFIGURE API KEYS IN SETTINGS PANEL",
        )
        return

      while self.running:
        if not config.AGENT_RUNNING:
          time.sleep(1)
          continue

        try:
          command = listen_and_transcribe(timeout_seconds=6.0)
          if command and config.AGENT_RUNNING:
            self.update_status("STATUS: EXECUTING", f"Command: {command}")
            handle_user_command(command)
            if config.AGENT_RUNNING:
              self.update_status(
                  "STATUS: STANDBY (LISTENING)", "Listening for commands..."
              )
        except Exception as e:
          self.update_status("STATUS: ERROR", error_msg=str(e))

        time.sleep(0.5)

    threading.Thread(target=background_loop, daemon=True).start()


if __name__ == "__main__":
  root = tk.Tk()
  app = JarvisGUI(root)
  root.mainloop()