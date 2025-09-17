import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

_log = logging.getLogger(__name__)

@dataclass
class AutosaveAddonConfig:
    """Configuration for autosave addons"""
    
    # Format 2 settings
    autosave_pdf_2: bool = False
    autosave_image_type_2: str = "PDF"
    autosave_path_2: str = ""
    
    # Format 3 settings
    autosave_pdf_3: bool = False
    autosave_image_type_3: str = "PDF Report"
    autosave_path_3: str = ""
    
    # Server upload settings
    autosave_upload_to_server: bool = False
    autosave_server_url: str = "http://localhost:5101"
    autosave_health_url: str = "http://localhost:5101/api/files/health"
    autosave_api_token: str = ""
    autosave_jwt_token: str = ""
    autosave_auth_type: str = "none"  # "none", "api_token", "jwt", "bearer"

     # JWT Token Management
    autosave_refresh_token: str = ""
    autosave_token_expires_at: int = 0  # Unix timestamp
    autosave_auto_refresh: bool = True  # Auto-refresh tokens when expired
    autosave_refresh_threshold: int = 300  # Refresh 5 minutes before expiry
    
    
    # Server connection settings
    autosave_connection_timeout: int = 30  # seconds
    autosave_retry_attempts: int = 3
    autosave_retry_delay: int = 5  # seconds
    autosave_health_check_enabled: bool = True
    autosave_health_check_interval: int = 300  # seconds (5 minutes)
    
    # more settings
    enabled: bool = True
    auto_save_on_roast_end: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "autosave_pdf_2": self.autosave_pdf_2,
            "autosave_image_type_2": self.autosave_image_type_2,
            "autosave_path_2": self.autosave_path_2,
            "autosave_pdf_3": self.autosave_pdf_3,
            "autosave_image_type_3": self.autosave_image_type_3,
            "autosave_path_3": self.autosave_path_3,
            "autosave_upload_to_server": self.autosave_upload_to_server,
            "autosave_server_url": self.autosave_server_url,
            "autosave_health_url": self.autosave_health_url,
            "autosave_api_token": self.autosave_api_token,
            "autosave_jwt_token": self.autosave_jwt_token,
            "autosave_refresh_token": self.autosave_refresh_token,
            "autosave_token_expires_at": self.autosave_token_expires_at,
            "autosave_auto_refresh": self.autosave_auto_refresh,
            "autosave_refresh_threshold": self.autosave_refresh_threshold,
          
            "autosave_auth_type": self.autosave_auth_type,
            "autosave_connection_timeout": self.autosave_connection_timeout,
            "autosave_retry_attempts": self.autosave_retry_attempts,
            "autosave_retry_delay": self.autosave_retry_delay,
            "autosave_health_check_enabled": self.autosave_health_check_enabled,
            "autosave_health_check_interval": self.autosave_health_check_interval,
            "enabled": self.enabled,
            "auto_save_on_roast_end": self.auto_save_on_roast_end
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AutosaveAddonConfig':
        """Create config from dictionary"""
        # Handle backward compatibility - if health_url is not in old config, derive it from server_url
        if 'autosave_health_url' not in data and 'autosave_server_url' in data:
            server_url = data['autosave_server_url'].rstrip('/')
            data['autosave_health_url'] = f"{server_url}/api/files/health"
        
        return cls(**data)
    
    @classmethod
    def load_from_file(cls, config_path: Optional[str] = None) -> 'AutosaveAddonConfig':
        """Load config from file"""
        if config_path is None:
            # Default config path in user's home directory
            config_dir = Path.home() / ".artisan" / "plugins" / "autosave"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / "config.json"
        else:
            # Convert string to Path object
            config_path = Path(config_path)
        
        try:
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    _log.info(f"Loaded autosave addon config from {config_path}")
                    return cls.from_dict(data)
            else:
                _log.info(f"No config file found at {config_path}, using defaults")
                return cls()
        except Exception as e:
            _log.error(f"Failed to load config from {config_path}: {e}")
            return cls()
    
    def save_to_file(self, config_path: Optional[str] = None) -> bool:
        """Save config to file"""
        try:
            if config_path is None:
                # Default config path in user's home directory
                config_dir = Path.home() / ".artisan" / "plugins" / "autosave"
                config_dir.mkdir(parents=True, exist_ok=True)
                config_path = config_dir / "config.json"
            else:
                # convert string to Path object
                config_path = Path(config_path)
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            
            _log.info(f"Saved autosave addon config to {config_path}")
            return True
        except Exception as e:
            _log.error(f"Failed to save config to {config_path}: {e}")
            return False