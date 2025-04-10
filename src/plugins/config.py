# /src/plugins/rest_plugin/config.py
from typing import Dict, Any
import json
import os

class RESTPluginConfig:
    def __init__(self):
        self.config_file = os.path.expanduser('~/.artisan/rest_plugin_config.json')
        self.config: Dict[str, Any] = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_config(self) -> None:
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f)

    @property
    def base_url(self) -> str:
        return self.config.get('base_url', '')

    @base_url.setter
    def base_url(self, value: str) -> None:
        self.config['base_url'] = value
        self.save_config()

    @property
    def api_key(self) -> str:
        return self.config.get('api_key', '')

    @api_key.setter
    def api_key(self, value: str) -> None:
        self.config['api_key'] = value
        self.save_config()