import json
import os
from typing import Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class InventoryFetcherConfig:
    """Configuration for beans fetcher plugin"""
    
    # Server settings
    server_url: str = ""
    api_key: str = ""
    timeout: int = 30
    
    # UI settings
    auto_fetch_on_startup: bool = False
    show_notifications: bool = True
    
    # File paths
    config_file: str = "inventory_fetcher_config.json"
    
    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            config_dir = os.path.expanduser("~/.artisan")
            os.makedirs(config_dir, exist_ok=True)
            config_path = os.path.join(config_dir, self.config_file)
            
            with open(config_path, 'w') as f:
                json.dump(asdict(self), f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    @classmethod
    def load_config(cls) -> 'InventoryFetcherConfig':
        """Load configuration from file"""
        try:
            config_dir = os.path.expanduser("~/.artisan")
            config_path = os.path.join(config_dir, cls.config_file)
            
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    data = json.load(f)
                return cls(**data)
            else:
                return cls()
        except Exception as e:
            print(f"Error loading config: {e}")
            return cls()