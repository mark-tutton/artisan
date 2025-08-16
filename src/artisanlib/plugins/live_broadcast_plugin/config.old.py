import json
import os
from typing import Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class LiveBroadcastConfig:
    """Configuration for live broadcast plugin"""
    
    # Server settings
    server_host: str = "localhost"
    server_port: int = 3001
    server_path: str = "/ws/roast"
    
    # Connection settings
    reconnect_interval: float = 5.0
    max_reconnect_attempts: int = 10
    
    # Broadcasting settings
    auto_start: bool = False
    broadcast_interval: float = 1.0
    
    # Event broadcasting settings
    broadcast_standard_events: bool = True
    broadcast_custom_events: bool = True
    broadcast_temperature_data: bool = True
    broadcast_rate_of_rise: bool = True
    
    # Event filtering
    include_events: Dict[str, bool] = None
    
    def __post_init__(self):
        if self.include_events is None:
            self.include_events = {
                'charge': True,
                'dry_end': True,
                'fc_start': True,
                'fc_end': True,
                'sc_start': True,
                'sc_end': True,
                'drop': True,
                'cool_end': True
            }
        self.load_config()
    
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

