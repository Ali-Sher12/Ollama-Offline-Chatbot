import json
import os
from pathlib import Path
from typing import Dict, Any

CONFIG_FILE = Path(__file__).resolve().parent.parent / "data" / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "ollama_url": "http://localhost:11434",
    "selected_provider": "ollama",
    "selected_model": "llama3.2:1b",
    "web_search_enabled": False,
    "token_budget_limit": 100000,
    "remember_context": True,
    "export_docx": False,
    "keep_alive": "30m",
    "api_keys": {
        "openai": "",
        "anthropic": "",
        "gemini": "",
        "groq": "",
        "openrouter": ""
    },
    "custom_endpoints": {
        "openai": "https://api.openai.com/v1",
        "anthropic": "https://api.anthropic.com/v1",
        "gemini": "https://generativelanguage.googleapis.com/v1beta",
        "groq": "https://api.groq.com/openai/v1",
        "openrouter": "https://openrouter.ai/api/v1"
    }
}

class ConfigManager:
    def __init__(self, config_path: Path = CONFIG_FILE):
        self.config_path = config_path
        self._config = self._load()

    def _load(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            self._save(DEFAULT_CONFIG)
            return dict(DEFAULT_CONFIG)
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Merge defaults for any missing keys
                merged = dict(DEFAULT_CONFIG)
                merged.update(data)
                if "api_keys" in data:
                    merged["api_keys"] = {**DEFAULT_CONFIG["api_keys"], **data["api_keys"]}
                if "custom_endpoints" in data:
                    merged["custom_endpoints"] = {**DEFAULT_CONFIG["custom_endpoints"], **data["custom_endpoints"]}
                return merged
        except Exception:
            return dict(DEFAULT_CONFIG)

    def _save(self, data: Dict[str, Any]) -> None:
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def get_all(self) -> Dict[str, Any]:
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def update(self, new_settings: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in new_settings.items():
            if isinstance(v, dict) and k in self._config and isinstance(self._config[k], dict):
                self._config[k].update(v)
            else:
                self._config[k] = v
        self._save(self._config)
        return self._config

config_manager = ConfigManager()
