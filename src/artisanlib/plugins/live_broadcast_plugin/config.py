import json
import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from pathlib import Path

_log = logging.getLogger(__name__)

@dataclass
class LiveBroadcastConfig:
    # Server settings
    server_host: str = "localhost"
    server_port: int = 5100
    server_path: str = "/socket.io/"

    # Roaster identification
    roaster_id: str = ""  # Custom roaster identifier (empty = auto-generate)


    # Connection settings
    reconnect_interval: float = 15.0
    max_reconnect_attempts: int = 5

    # Broadcasting settings
    auto_start: bool = True
    broadcast_interval: float = 1.0

    # Headless mode settings
    headless_mode: bool = False
    config_file_path: Optional[str] = None

    # Event broadcasting settings
    broadcast_standard_events: bool = True
    broadcast_custom_events: bool = True
    broadcast_temperature_data: bool = True
    broadcast_rate_of_rise: bool = True

    min_send_interval: float = 0.03  
    connection_timeout: float = 5.0   
    max_reconnect_interval: float = 60.0  
    
    # Broadcast intervals based on roaster state
    broadcast_idle_interval: float = 30.0 
    broadcast_monitoring_interval: float = 10.0 
    broadcast_roasting_interval: float = 3.0   
    
    # Rate limiting and throttling
    max_messages_per_minute: int = 60          
    enable_rate_limiting: bool = True         
    batch_messages: bool = True  

    # Debug and logging
    enable_debug_logging: bool = False
    log_messages: bool = False

    # Socket.IO settings
    use_ssl: bool = False
    socketio_path: str = "/socket.io/"  # Socket.IO default path
     
    # Connection refresh settings
    connection_refresh_interval: float = 3600.0  # 1 hour refresh
    
    # Security
    enforce_secure_connection: bool = True  # Force WSS in production
    validate_ssl_cert: bool = True

    # JWT Authentication (for backward compatibility, now handled by global auth manager)
    auth_token: str = ""
    refresh_token: str = ""
    jwt_issuer: Optional[str] = None
    jwt_audience: Optional[str] = None
    jwt_validation_enabled: bool = True

    # Performance settings
    max_message_size: int = 1024 * 1024  # 1MB
    message_queue_size: int = 1000

    # Event settings
    include_events: Dict[str, bool] = field(default_factory=lambda: {
        "charge": True,
        "dry_end": True,
        "fc_start": True,
        "fc_end": True,
        "sc_start": True,
        "sc_end": True,
        "drop": True,
        "cool_end": True,
    })

    # Heartbeat settings
    heartbeat_interval: float = 30.0

    def __post_init__(self):
        """Initialize configuration with validation"""
        try:
            # Set default events if not provided or empty
            if not hasattr(self, 'include_events') or not isinstance(self.include_events, dict) or not self.include_events:
                self.include_events = {
                    "charge": True,
                    "dry_end": True,
                    "fc_start": True,
                    "fc_end": True,
                    "sc_start": True,
                    "sc_end": True,
                    "drop": True,
                    "cool_end": True,
                }
            
            # Validate configuration
            self._validate_config()
            
        except Exception as e:
            _log.error(f"Error in config initialization: {e}")

    def _validate_config(self):
        """Validate configuration values"""
        if self.server_port < 1 or self.server_port > 65535:
            raise ValueError("Server port must be between 1 and 65535")
        
        if not self.server_path.startswith("/"):
            raise ValueError("Server path must start with '/'")
        
        if self.reconnect_interval < 1.0:
            raise ValueError("Reconnect interval must be at least 1 second")

    def save_config(self, file_path: Optional[str] = None):
        """Save configuration to file"""
        try:
            if file_path is None:
                file_path = self.get_config_file()
            
            config_data = self.to_dict()
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
            _log.debug(f"Configuration saved to {file_path}")
            
        except Exception as e:
            _log.error(f"Failed to save configuration: {e}")
            raise

    def load_from_file(self, file_path: str):
        """Load configuration from file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Update attributes
            for key, value in config_data.items():
                if hasattr(self, key):
                    setattr(self, key, value)
                    
            _log.debug(f"Configuration loaded from {file_path}")
            
        except Exception as e:
            _log.error(f"Failed to load configuration: {e}")
            raise

    def get_config_file(self) -> str:
        """Get the configuration file path"""
        if self.config_file_path:
            return self.config_file_path
        
        # Default config file path
        config_dir = Path.home() / ".artisan" / "plugins" / "live_broadcast"
        config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir / "config.json")

    def get_connection_url(self) -> str:
        """Get the WebSocket connection URL"""
        protocol = "wss" if self.use_ssl else "ws"
        return f"{protocol}://{self.server_host}:{self.server_port}{self.server_path}"

    def reset_to_defaults(self):
        """Reset configuration to default values"""
        # Create a new instance with default values
        default_config = LiveBroadcastConfig()
        
        # Copy default values to current instance
        for key, value in default_config.to_dict().items():
            if hasattr(self, key):
                setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        try:
            config_dict = asdict(self)
            config_dict.pop("config_file_path", None) 
            return config_dict
        except Exception as e:
            _log.error(f"Failed to convert config to dict: {e}")
            return {}

    def __str__(self) -> str:
        """String representation of configuration"""
        return f"LiveBroadcastConfig(host={self.server_host}, port={self.server_port}, auto_start={self.auto_start})"