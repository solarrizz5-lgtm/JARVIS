import json
import os
from datetime import datetime
from jarvis import config
from jarvis.utils.logger import log_error, log_info

class AgentMemory:
    def __init__(self, history_file: str = None):
        self.history_file = history_file or os.path.join(config.LOGS_DIR, "conversation_history.json")
        self.history = self._load_history()

    def _load_history(self) -> list:
        """Loads previous conversation history from disk if available."""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                log_error(f"Failed to load conversation history: {e}")
        return []

    def save_history(self):
        """Persists current conversation history to disk."""
        try:
            with open(self.history_file, "w") as f:
                json.dump(self.history, f, indent=2)
        except Exception as e:
            log_error(f"Failed to save conversation history: {e}")

    def add_turn(self, role: str, content: str):
        """Adds a new interaction turn to memory and enforces a rolling window."""
        self.history.append({"role": role, "content": content, "timestamp": datetime.now().isoformat()})
        # Keep the last 10 turns for context efficiency
        if len(self.history) > 10:
            self.history.pop(0)
        self.save_history()

    def get_context(self) -> list:
        """Returns rolling history cleaned for OpenAI/OpenRouter API consumption (omitting timestamps)."""
        return [{"role": turn["role"], "content": turn["content"]} for turn in self.history]

    def clear(self):
        """Resets the history."""
        self.history = []
        if os.path.exists(self.history_file):
            os.remove(self.history_file)
        log_info("Agent memory cleared.")