import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

_log = logging.getLogger(__name__)

@dataclass
class InventoryFetcherConfig:
    """Configuration for beans fetcher plugin with JWT support"""
    
    # Server settings 
    server_url: str = ""
    api_key: str = ""
    timeout: int = 30
    
    # Authentication settings
    auth_type: str = "none"  # "none", "api_token", "jwt", "bearer"
    jwt_token: str = ""
    jwt_issuer: Optional[str] = None
    jwt_audience: Optional[str] = None
    jwt_validation_enabled: bool = True
    
    # Security settings
    use_ssl: bool = False
    validate_ssl_cert: bool = True
    enforce_secure_connection: bool = False
    
    # Connection settings
    connection_timeout: int = 30
    retry_attempts: int = 3
    retry_delay: int = 5
    health_check_enabled: bool = True
    health_check_interval: int = 300  # seconds (5 minutes)
    
    # UI settings
    auto_fetch_on_startup: bool = False
    show_notifications: bool = True
    
    # File paths
    config_file: str = "inventory_fetcher_config.json"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "server_url": self.server_url,
            "api_key": self.api_key,
            "timeout": self.timeout,
            "auth_type": self.auth_type,
            "jwt_token": self.jwt_token,
            "jwt_issuer": self.jwt_issuer,
            "jwt_audience": self.jwt_audience,
            "jwt_validation_enabled": self.jwt_validation_enabled,
            "use_ssl": self.use_ssl,
            "validate_ssl_cert": self.validate_ssl_cert,
            "enforce_secure_connection": self.enforce_secure_connection,
            "connection_timeout": self.connection_timeout,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay,
            "health_check_enabled": self.health_check_enabled,
            "health_check_interval": self.health_check_interval,
            "auto_fetch_on_startup": self.auto_fetch_on_startup,
            "show_notifications": self.show_notifications,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InventoryFetcherConfig':
        """Create config from dictionary with backward compatibility"""
        # Handle backward compatibility for old config format
        if 'server_url' in data and 'server_host' not in data:
            # Old format - parse server_url into components
            server_url = data.pop('server_url', '')
            
            # Clean up the server_url 
            server_url = server_url.strip()
            
            if server_url.startswith('http:// '):
                server_url = server_url.replace('http:// ', 'http://')
            elif server_url.startswith('https:// '):
                server_url = server_url.replace('https:// ', 'https://')
            
            if server_url.startswith('https://'):
                data['use_ssl'] = True
                server_url = server_url[8:]  # Remove 'https://'
            elif server_url.startswith('http://'):
                data['use_ssl'] = False
                server_url = server_url[7:]  # Remove 'http://'
            else:
                data['use_ssl'] = False
            
            # Parse host:port and clean up
            if ':' in server_url:
                host, port = server_url.rsplit(':', 1)
                data['server_url'] = f"{host.strip()}:{port.strip()}"
            else:
                data['server_url'] = server_url.strip()
        
        return cls(**data)
    
    def save_config(self) -> None:
        """Save configuration to file"""
        try:
            config_dir = Path.home() / ".artisan" / "plugins" / "inventory_fetcher"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / self.config_file
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            
            _log.info(f"✅ Saved inventory fetcher config to {config_path}")
        except Exception as e:
            _log.error(f"❌ Failed to save config: {e}")
            raise
    
    @classmethod
    def load_config(cls) -> 'InventoryFetcherConfig':
        """Load configuration from file"""
        try:
            config_dir = Path.home() / ".artisan" / "plugins" / "inventory_fetcher"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_path = config_dir / cls.config_file
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                _log.info(f"✅ Loaded inventory fetcher config from {config_path}")
                return cls.from_dict(data)
            else:
                _log.info(f"📁 No config file found at {config_path}, using defaults")
                return cls()
        except Exception as e:
            _log.error(f"❌ Failed to load config: {e}")
            return cls()
        
    def validate_server_url(self) -> bool:
        """Validate and clean the server URL"""
        if not self.server_url:
            return False
            
        self.server_url = self.server_url.strip()
        
        if self.server_url.startswith('http:// '):
            self.server_url = self.server_url.replace('http:// ', 'http://')
        elif self.server_url.startswith('https:// '):
            self.server_url = self.server_url.replace('https:// ', 'https://')
        
        # Validate format
        if self.server_url.startswith(('http://', 'https://')):
            # Has protocol, validate the rest
            parts = self.server_url.split('://', 1)
            if len(parts) != 2 or not parts[1]:
                return False
            host_port = parts[1].strip()
        else:
            # No protocol, validate host:port format
            host_port = self.server_url.strip()
        
        # Validate host:port
        if ':' in host_port:
            host, port = host_port.rsplit(':', 1)
            try:
                port_num = int(port.strip())
                if not (1 <= port_num <= 65535):
                    return False
            except ValueError:
                return False
        else:
            # No port specified, that's fine
            pass
            
        return True
    
    def get_clean_server_url(self) -> str:
        """Get a clean, validated server URL"""
        if self.validate_server_url():
            return self.server_url
        else:
            # Return a default if validation fails
            return "http://localhost:3000"