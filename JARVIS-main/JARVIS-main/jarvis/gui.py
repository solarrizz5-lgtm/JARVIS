import tkinter as tk
from tkinter import ttk, messagebox
import threading
import os
import json
import time
import math
from jarvis import config
from jarvis.voice.tts import speak
from jarvis.voice.input import listen_and_transcribe
from jarvis.ai.planner import handle_user_command
from jarvis.utils.logger import log_info, log_error

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(ROOT_DIR, "jarvis_config.json")

def load_persistent_config():
    """Loads saved OpenRouter API key, Google Gemini API key, and model from local JSON config file."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                or_key = data.get("openrouter_api_key") or data.get("api_key", "")
                gemini_key = data.get("gemini_api_key", "")
                model = data.get("model_name", "nvidia/nemotron-3-ultra-550b-a55b:free")
                
                if or_key:
                    os.environ["OPENROUTER_API_KEY"] = or_key
                    config.OPENROUTER_API_KEY = or_key
                if gemini_key:
                    os.environ["GEMINI_API_KEY"] = gemini_key
                    config.GEMINI_API_KEY = gemini_key
                if model:
                    config.MODEL_NAME = model
                return or_key, gemini_key, model
        except Exception:
            pass
    return os.getenv("OPENROUTER_API_KEY", ""), os.getenv("GEMINI_API_KEY", ""), getattr(config, "MODEL_NAME", "nvidia/nemotron-3-ultra-550b-a55b:free")

def save_persistent_config(or_key, gemini_key, model):
    """Saves OpenRouter API key, Google Gemini API key, and model to local JSON config file and environment."""
    data = {
        "openrouter_api_key": or_key,
        "gemini_api_key": gemini_key,
        "model_name": model
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

class JarvisGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("J.A.R.V.I.S. // QUANTUM HUD")
        self.root.geometry("400x711")  # 9:16 Aspect Ratio Portrait Window
        self.root.configure(bg="#050811")
        self.root.resizable(False, False)
        
        load_persistent_config()
        
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", background="#050811", foreground="#00f0ff", font=("Segoe UI", 10, "bold"))
        style.configure("TButton", background="#0f172a", foreground="#00f0ff", font=("Segoe UI", 9, "bold"), borderwidth=1)
        
        # Sleek Modern Fixed Border Frame
        self.neon_outer_frame = tk.Frame(root, bg="#00bcd4", bd=2, relief="flat")
        self.neon_outer_frame.pack(fill="both", expand=True, padx=8, pady=8)
        
        self.main_container = tk.Frame(self.neon_outer_frame, bg="#050811")
        self.main_container.pack(fill="both", expand=True, padx=2, pady=2)
        
        # Header Title
        title_label = tk.Label(self.main_container, text="J.A.R.V.I.S. // CORE INTERFACE", bg="#050811", fg="#38bdf8", font=("Segoe UI", 11, "bold"))
        title_label.pack(pady=(20, 10))
        
        # Interactive Neon Radar & Microphone Visual Canvas
        self.canvas_size = 180
        self.canvas = tk.Canvas(self.main_container, width=self.canvas_size, height=self.canvas_size, bg="#050811", highlightthickness=0)
        self.canvas.pack(pady=10)
        self.canvas.bind("<Button-1>", lambda e: self.trigger_manual_listen())
        
        # Status Panel
        self.status_frame = tk.Frame(self.main_container, bg="#0b0f19", bd=1, relief="solid", highlightbackground="#00f0ff", highlightthickness=1)
        self.status_frame.pack(fill="x", padx=25, pady=10)
        
        self.status_label = tk.Label(self.status_frame, text="STATUS: INITIALIZING...", bg="#0b0f19", fg="#34d399", font=("Segoe UI", 9, "bold"))
        self.status_label.pack(pady=8, padx=10)
        
        # Log Panel
        self.log_frame = tk.Frame(self.main_container, bg="#0a0f1d", bd=1, relief="solid", highlightbackground="#1e293b", highlightthickness=1)
        self.log_frame.pack(fill="x", padx=25, pady=10)
        
        self.log_text = tk.Label(self.log_frame, text="Establishing quantum link...", bg="#0a0f1d", fg="#94a3b8", font=("Consolas", 9), anchor="w", justify="left", wraplength=320)
        self.log_text.pack(fill="x", padx=10, pady=10)
        
        # Control Buttons Frame
        self.btn_frame = tk.Frame(self.main_container, bg="#050811")
        self.btn_frame.pack(fill="x", padx=25, pady=15)
        
        self.btn_frame.grid_columnconfigure(0, weight=1)
        self.btn_frame.grid_columnconfigure(1, weight=1)
        self.btn_frame.grid_columnconfigure(2, weight=1)
        
        self.listen_btn = ttk.Button(self.btn_frame, text="⚡ Listen", command=self.trigger_manual_listen)
        self.listen_btn.grid(row=0, column=0, padx=4, sticky="ew", ipady=6)
        
        self.settings_btn = ttk.Button(self.btn_frame, text="⚙ Config", command=self.open_settings)
        self.settings_btn.grid(row=0, column=1, padx=4, sticky="ew", ipady=6)
        
        self.stop_btn = ttk.Button(self.btn_frame, text="🛑 Halt", command=self.emergency_stop)
        self.stop_btn.grid(row=0, column=2, padx=4, sticky="ew", ipady=6)
        
        self.running = True
        self.pulse_phase = 0.0
        
        self.start_animations()
        self.start_background_loop()

    def get_api_key(self):
        current_model = getattr(config, "MODEL_NAME", "")
        if "google/" in current_model:
            return os.getenv("GEMINI_API_KEY", "") or getattr(config, "GEMINI_API_KEY", "")
        return os.getenv("OPENROUTER_API_KEY", "") or getattr(config, "OPENROUTER_API_KEY", "")

    def update_status(self, text, log_msg=""):
        self.root.after(0, lambda: self._safe_update_status(text, log_msg))

    def _safe_update_status(self, text, log_msg):
        self.status_label.config(text=text)
        if log_msg:
            self.log_text.config(text=log_msg)

    def open_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("JARVIS // SETTINGS")
        settings_win.geometry("400x390")
        settings_win.configure(bg="#050811")
        settings_win.resizable(False, False)
        settings_win.grab_set()

        tk.Label(settings_win, text="OpenRouter API Key:", bg="#050811", fg="#00f0ff", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=25, pady=(10, 2))
        or_key_entry = tk.Entry(settings_win, width=40, show="*", font=("Consolas", 9), bg="#0f172a", fg="#f8fafc", insertbackground="#fff", relief="flat")
        or_key_entry.pack(padx=25, ipady=3)

        tk.Label(settings_win, text="Google Gemini API Key:", bg="#050811", fg="#00f0ff", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=25, pady=(10, 2))
        gemini_key_entry = tk.Entry(settings_win, width=40, show="*", font=("Consolas", 9), bg="#0f172a", fg="#f8fafc", insertbackground="#fff", relief="flat")
        gemini_key_entry.pack(padx=25, ipady=3)

        current_or, current_gemini, current_model = load_persistent_config()
        if current_or:
            or_key_entry.insert(0, current_or)
        if current_gemini:
            gemini_key_entry.insert(0, current_gemini)

        tk.Label(settings_win, text="Primary Model Name:", bg="#050811", fg="#00f0ff", font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=25, pady=(10, 2))
        
        models = [
            "nvidia/nemotron-3-ultra-550b-a55b:free",
            "google/gemini-2.5-flash",
            "google/gemini-2.5-pro",
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o"
        ]
        model_dropdown = ttk.Combobox(settings_win, values=models, width=38, state="readonly")
        model_dropdown.pack(padx=25, ipady=2)
        
        if current_model in models:
            model_dropdown.set(current_model)
        else:
            model_dropdown.set("nvidia/nemotron-3-ultra-550b-a55b:free")

        def save_and_close():
            new_or = or_key_entry.get().strip()
            new_gemini = gemini_key_entry.get().strip()
            new_model = model_dropdown.get().strip()
            
            if "google/" in new_model and not new_gemini:
                if not messagebox.askyesno("Warning", "You selected a Google model but did not provide a Gemini API key. Continue anyway?", parent=settings_win):
                    return
            
            if not new_or and not new_gemini:
                messagebox.showerror("Error", "At least one API Key must be provided.", parent=settings_win)
                return
            
            save_persistent_config(new_or, new_gemini, new_model)
            messagebox.showinfo("Success", "Core configuration updated successfully!", parent=settings_win)
            settings_win.destroy()

        save_btn = ttk.Button(settings_win, text="Save Configuration", command=save_and_close)
        save_btn.pack(pady=20, ipadx=10, ipady=3)

    def trigger_manual_listen(self):
        if not self.get_api_key():
            messagebox.showerror("API Key Missing", "Required API Key for the selected model is not set. Please update it in Settings.")
            return
        config.AGENT_RUNNING = True
        threading.Thread(target=self._listen_task, daemon=True).start()

    def _listen_task(self):
        if not config.AGENT_RUNNING:
            return
        self.update_status("STATUS: LISTENING...", "Listening for user command...")
        speak("Yes, sir? Standing by.")
        command = listen_and_transcribe(timeout_seconds=6.0)
        if command and config.AGENT_RUNNING:
            self.update_status("STATUS: EXECUTING", f"Command: {command}")
            handle_user_command(command)
            if config.AGENT_RUNNING:
                self.update_status("STATUS: STANDBY (LISTENING)", "Task complete. Listening for commands...")
        else:
            if config.AGENT_RUNNING:
                self.update_status("STATUS: STANDBY (LISTENING)", "No command detected. Listening...")

    def emergency_stop(self):
        config.AGENT_RUNNING = False
        self.update_status("STATUS: HALTED", "Emergency override activated!")
        speak("Emergency stop activated.")
        log_error("Emergency stop triggered via GUI.")

    def start_animations(self):
        def animate():
            if not self.running:
                return
            
            self.canvas.delete("all")
            cx, cy = self.canvas_size / 2, self.canvas_size / 2
            
            self.pulse_phase += 0.08
            
            current_status = self.status_label.cget("text")
            if "HALTED" in current_status:
                accent_color = "#ef4444"
            elif "EXECUTING" in current_status:
                accent_color = "#a855f7"
            elif "LISTENING" in current_status:
                accent_color = "#34d399"
            else:
                accent_color = "#00f0ff"

            pulse_offset = math.sin(self.pulse_phase) * 5
            self.canvas.create_oval(cx - 75 - pulse_offset, cy - 75 - pulse_offset, cx + 75 + pulse_offset, cy + 75 + pulse_offset, outline=accent_color, width=2)
            self.canvas.create_arc(cx - 65, cy - 65, cx + 65, cy + 65, start=15, extent=120, outline="#ff007f", width=2, style="arc")
            self.canvas.create_arc(cx - 65, cy - 65, cx + 65, cy + 65, start=195, extent=120, outline="#00f0ff", width=2, style="arc")

            mic_w, mic_h = 22, 38
            self.canvas.create_oval(cx - mic_w, cx - mic_h - 6, cx + mic_w, cy + mic_h - 18, outline="#ffffff", width=2, fill="#050811")
            
            for dy in range(-24, 2, 6):
                self.canvas.create_line(cx - 15, cy + dy, cx + 15, cy + dy, fill=accent_color, width=1)
            
            self.canvas.create_line(cx - 18, cy - 12, cx + 18, cy - 12, fill="#ffffff", width=2)
            self.canvas.create_arc(cx - 22, cy - 10, cx + 22, cy + 28, start=180, extent=180, outline="#ffffff", width=2, style="arc")
            self.canvas.create_line(cx, cy + 28, cx, cy + 52, fill="#ffffff", width=2)
            self.canvas.create_line(cx - 8, cy + 52, cx + 8, cy + 52, fill=accent_color, width=2)

            self.root.after(40, animate)

        animate()

    def start_background_loop(self):
        def background_loop():
            if self.get_api_key():
                speak("JARVIS online. Systems nominal. Standing by.")
                self.update_status("STATUS: STANDBY (LISTENING)", "Listening for commands...")
            else:
                self.update_status("STATUS: API KEY MISSING", "Please configure your API keys in Settings.")
                return

            while self.running:
                if not config.AGENT_RUNNING:
                    self.update_status("STATUS: HALTED", "Agent execution halted.")
                    time.sleep(1)
                    continue

                try:
                    command = listen_and_transcribe(timeout_seconds=6.0)
                    if command and config.AGENT_RUNNING:
                        self.update_status("STATUS: EXECUTING", f"Command: {command}")
                        handle_user_command(command)
                        if config.AGENT_RUNNING:
                            self.update_status("STATUS: STANDBY (LISTENING)", "Listening for commands...")
                except Exception as e:
                    log_error(f"Background listener error: {e}")
                
                time.sleep(0.5)

        threading.Thread(target=background_loop, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = JarvisGUI(root)
    root.mainloop()