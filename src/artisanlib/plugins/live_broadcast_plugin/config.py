import json
import os
from typing import Optional
from dataclasses import dataclass, asdict

@dataclass
class LiveBroadcastConfig:
    """Configuration for live broadcast plugin"""
    
    # Server settings
    server_host: str = "localhost"
    server_port: int = 3000
    server_path: str = "/ws/roast"
    
    # Connection settings
    auto_start: bool = False
    reconnect_interval: float = 5.0
    connection_timeout: float = 10.0
    
    # Data settings
    broadcast_interval: float = 1.0
    include_full_history: bool = False
    max_history_points: int = 100
    
    # Authentication
    api_key: Optional[str] = None
    
    def save_config(self) -> None:
        """Save configuration to file"""
        config_dir = os.path.expanduser("~/.artisan/plugins")
        os.makedirs(config_dir, exist_ok=True)
        
        config_file = os.path.join(config_dir, "live_broadcast_config.json")
        
        with open(config_file, 'w') as f:
            json.dump(asdict(self), f, indent=2)
    
    def load_config(self) -> None:
        """Load configuration from file"""
        config_file = os.path.expanduser("~/.artisan/plugins/live_broadcast_config.json")
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    data = json.load(f)
                
                # Update fields from loaded data
                for key, value in data.items():
                    if hasattr(self, key):
                        setattr(self, key, value)
            except Exception as e:
                print(f"Failed to load config: {e}")
    
    def __post_init__(self):
        """Load config after initialization"""
        self.load_config()