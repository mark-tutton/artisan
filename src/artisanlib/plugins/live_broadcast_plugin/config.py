
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
    server_port: int = 3001
    server_path: str = "/ws/roast"

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

    # Broadcast intervals based on roaster state
    broadcast_idle_interval: float = 30.0 
    broadcast_monitoring_interval: float = 10.0 
    broadcast_roasting_interval: float = 3.0   
    
    # Rate limiting and throttling
    max_messages_per_minute: int = 60          
    enable_rate_limiting: bool = True         
    batch_messages: bool = True  

    # Event filtering
    include_events: Dict[str, bool] = field(default_factory=dict)

    # Performance settings
    max_message_size: int = 1024 * 1024  # 1MB
    message_queue_size: int = 1000
    heartbeat_interval: float = 30.0

    # Logging settings
    enable_debug_logging: bool = False
    log_messages: bool = False

    def __post_init__(self):
        """Initialize configuration with validation"""
        try:
            # Set default events 
            if not self.include_events:
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

            # Load from file if exists
            self.load_config()

        except Exception as e:
            _log.error(f"Error initializing config: {e}")
            raise

    def _validate_config(self) -> None:
        """Validate configuration values"""
        try:
            # Validate server settings
            if not isinstance(self.server_host, str) or not self.server_host.strip():
                raise ValueError("server_host must be a non-empty string")

            if not isinstance(self.server_port, int) or not (1 <= self.server_port <= 65535):
                raise ValueError("server_port must be an integer between 1 and 65535")

            if not isinstance(self.server_path, str) or not self.server_path.startswith("/"):
                raise ValueError("server_path must be a string starting with '/'")

            # Validate connection settings
            if (
                not isinstance(self.reconnect_interval, (int, float))
                or self.reconnect_interval <= 0
            ):
                raise ValueError("reconnect_interval must be a positive number")

            if not isinstance(self.max_reconnect_attempts, int) or self.max_reconnect_attempts < 0:
                raise ValueError("max_reconnect_attempts must be a non-negative integer")

            # Validate broadcasting settings
            if (
                not isinstance(self.broadcast_interval, (int, float))
                or self.broadcast_interval <= 0
            ):
                raise ValueError("broadcast_interval must be a positive number")

            # Validate performance settings
            if not isinstance(self.max_message_size, int) or self.max_message_size <= 0:
                raise ValueError("max_message_size must be a positive integer")

            if not isinstance(self.message_queue_size, int) or self.message_queue_size <= 0:
                raise ValueError("message_queue_size must be a positive integer")

            if (
                not isinstance(self.heartbeat_interval, (int, float))
                or self.heartbeat_interval <= 0
            ):
                raise ValueError("heartbeat_interval must be a positive number")

        except Exception as e:
            _log.error(f"Configuration validation failed: {e}")
            raise

    def get_config_dir(self) -> Path:
        """Get configuration directory with error handling"""
        try:
            config_dir = Path.home() / ".artisan" / "plugins"
            config_dir.mkdir(parents=True, exist_ok=True)
            return config_dir
        except Exception as e:
            _log.error(f"Failed to create config directory: {e}")
            raise

    def get_config_file(self) -> Path:
        """Get configuration file path"""
        return self.get_config_dir() / "live_broadcast_config.json"

    def save_config(self, file_path: Optional[str] = None) -> None:
        """Save configuration to file with error handling"""
        try:
            config_file = Path(file_path) if file_path else self.get_config_file()

            config_file.parent.mkdir(parents=True, exist_ok=True)

            # Prepare data for saving
            config_data = asdict(self)

            # Remove non-serializable fields
            config_data.pop("config_file_path", None)

            # Save to file
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)

            _log.info(f"Configuration saved to {config_file}")

        except Exception as e:
            _log.error(f"Failed to save configuration: {e}")
            raise

    def load_config(self, file_path: Optional[str] = None) -> None:
        """Load configuration from file with error handling"""
        try:
            config_file = Path(file_path) if file_path else self.get_config_file()

            if not config_file.exists():
                _log.info(f"Configuration file not found: {config_file}")
                return

            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Update fields from loaded data with validation
            for key, value in data.items():
                if hasattr(self, key):
                    # Validate value before setting
                    if self._validate_field(key, value):
                        setattr(self, key, value)
                    else:
                        _log.warning(f"Invalid value for {key}: {value}, using default")
                else:
                    _log.warning(f"Unknown configuration key: {key}")

            # Re-validate after loading
            self._validate_config()

            _log.info(f"Configuration loaded from {config_file}")

        except json.JSONDecodeError as e:
            _log.error(f"Invalid JSON in configuration file: {e}")
            raise
        except Exception as e:
            _log.error(f"Failed to load configuration: {e}")
            raise

    def _validate_field(self, field_name: str, value: Any) -> bool:
        """Validate a specific field value"""
        try:
            if field_name == "server_host":
                return isinstance(value, str) and value.strip()
            elif field_name == "server_port":
                return isinstance(value, int) and 1 <= value <= 65535
            elif field_name == "server_path":
                return isinstance(value, str) and value.startswith("/")
            elif field_name == "reconnect_interval":
                return isinstance(value, (int, float)) and value > 0
            elif field_name == "max_reconnect_attempts":
                return isinstance(value, int) and value >= 0
            elif field_name == "broadcast_interval":
                return isinstance(value, (int, float)) and value > 0
            elif field_name == "max_message_size":
                return isinstance(value, int) and value > 0
            elif field_name == "message_queue_size":
                return isinstance(value, int) and value > 0
            elif field_name == "heartbeat_interval":
                return isinstance(value, (int, float)) and value > 0
            elif field_name in [
                "auto_start",
                "headless_mode",
                "broadcast_standard_events",
                "broadcast_custom_events",
                "broadcast_temperature_data",
                "broadcast_rate_of_rise",
                "enable_debug_logging",
                "log_messages",
            ]:
                return isinstance(value, bool)
            elif field_name == "include_events":
                return isinstance(value, dict) and all(
                    isinstance(k, str) and isinstance(v, bool) for k, v in value.items()
                )
            else:
                return True  # Unknown fields are allowed

        except Exception as e:
            _log.error(f"Error validating field {field_name}: {e}")
            return False

    def load_from_file(self, file_path: str) -> None:
        """Load configuration from specific file for headless mode"""
        try:
            self.load_config(file_path)
            self.config_file_path = file_path
            _log.info(f"Loaded configuration from {file_path}")
        except Exception as e:
            _log.error(f"Failed to load configuration from {file_path}: {e}")
            raise

    def reset_to_defaults(self) -> None:
        """Reset configuration to default values"""
        try:
            # Create a new instance with defaults
            default_config = LiveBroadcastConfig()

            # Copy default values
            for field_name, field_value in asdict(default_config).items():
                if hasattr(self, field_name):
                    setattr(self, field_name, field_value)

            _log.info("Configuration reset to defaults")

        except Exception as e:
            _log.error(f"Failed to reset configuration: {e}")
            raise

    def get_connection_url(self) -> str:
        """Get the full WebSocket connection URL"""
        return f"ws://{self.server_host}:{self.server_port}{self.server_path}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        try:
            config_dict = asdict(self)
            config_dict.pop("config_file_path", None)  # Remove non-serializable field
            return config_dict
        except Exception as e:
            _log.error(f"Failed to convert config to dict: {e}")
            return {}

    def __str__(self) -> str:
        """String representation of configuration"""
        return f"LiveBroadcastConfig(host={self.server_host}, port={self.server_port}, auto_start={self.auto_start})"
