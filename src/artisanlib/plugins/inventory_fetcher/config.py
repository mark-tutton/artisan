import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

_log = logging.getLogger(__name__)

@dataclass
class InventoryFetcherConfig:
    """Configuration for beans fetcher plugin with Gateway authentication support"""
    
    # Gateway settings
    use_gateway: bool = True
    gateway_url: str = "http://localhost:5101"
    
    # Legacy server settings 
    server_url: str = ""
    api_key: str = ""
    timeout: int = 30
    
    # Authentication settings
    auth_type: str = "gateway"  # "none", "api_token", "jwt", "bearer", "gateway"
    jwt_token: str = ""
    jwt_issuer: Optional[str] = None
    jwt_audience: Optional[str] = None
    jwt_validation_enabled: bool = True
    
    # Gateway-specific settings
    gateway_auth_type: str = "jwt"  # "google", "jwt", "api_key"
    gateway_username: str = ""
    gateway_password: str = ""
    gateway_api_key: str = ""
    gateway_refresh_token: str = ""
    
    # Security settings
    use_ssl: bool = True  # Default to True for gateway
    validate_ssl_cert: bool = True
    enforce_secure_connection: bool = True
    
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
            "use_gateway": self.use_gateway,
            "gateway_url": self.gateway_url,
            "server_url": self.server_url,
            "api_key": self.api_key,
            "timeout": self.timeout,
            "auth_type": self.auth_type,
            "jwt_token": self.jwt_token,
            "jwt_issuer": self.jwt_issuer,
            "jwt_audience": self.jwt_audience,
            "jwt_validation_enabled": self.jwt_validation_enabled,
            "gateway_auth_type": self.gateway_auth_type,
            "gateway_username": self.gateway_username,
            "gateway_password": self.gateway_password,
            "gateway_api_key": self.gateway_api_key,
            "gateway_refresh_token": self.gateway_refresh_token,
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
        if 'use_gateway' not in data:
            # Old config - migrate to gateway mode
            data['use_gateway'] = True
            if 'server_url' in data and data['server_url']:
                # Convert old server_url to gateway_url
                old_url = data['server_url']
                if old_url.startswith(('http://', 'https://')):
                    data['gateway_url'] = old_url
                else:
                    data['gateway_url'] = f"http://{old_url}"
                data['server_url'] = ""  
        
        # Handle server_url format
        if 'server_url' in data and 'server_host' not in data:
            # Parse server_url into components
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
            
            _log.info(f"Saved inventory fetcher config to {config_path}")
        except Exception as e:
            _log.error(f"Failed to save config: {e}")
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
                _log.info(f"Loaded inventory fetcher config from {config_path}")
                return cls.from_dict(data)
            else:
                _log.info(f"No config file found at {config_path}, using defaults")
                return cls()
        except Exception as e:
            _log.error(f"Failed to load config: {e}")
            return cls()
        
    def validate_gateway_url(self) -> bool:
        """Validate and clean the gateway URL"""
        if not self.gateway_url:
            return False
            
        self.gateway_url = self.gateway_url.strip()
        
        if self.gateway_url.startswith('http:// '):
            self.gateway_url = self.gateway_url.replace('http:// ', 'http://')
        elif self.gateway_url.startswith('https:// '):
            self.gateway_url = self.gateway_url.replace('https:// ', 'https://')
        
        # Validate format
        if self.gateway_url.startswith(('http://', 'https://')):
            # Has protocol, validate the rest
            parts = self.gateway_url.split('://', 1)
            if len(parts) != 2 or not parts[1]:
                return False
            host_port = parts[1].strip()
        else:
            # No protocol, validate host:port format
            host_port = self.gateway_url.strip()
        
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
            # No port specified
            pass
            
        return True
    
    def get_clean_gateway_url(self) -> str:
        """Get a clean, validated gateway URL"""
        if self.validate_gateway_url():
            return self.gateway_url
        else:
            # Return a default 
            return "http://localhost:5101"
    
    def get_effective_url(self) -> str:
        """Get the effective URL to use for requests"""
        if self.use_gateway:
            return self.get_clean_gateway_url()
        else:
            return self.server_url
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on configuration"""
        headers = {}
        
        if self.use_gateway:
            if self.gateway_auth_type == "google" and self.jwt_token:
                headers["Authorization"] = f"Bearer {self.jwt_token}"
            elif self.gateway_auth_type == "api_key" and self.gateway_api_key:
                headers["X-API-Key"] = self.gateway_api_key
            elif self.gateway_auth_type == "jwt" and self.jwt_token:
                headers["Authorization"] = f"Bearer {self.jwt_token}"
        else:
            # Legacy authentication
            if self.auth_type == "api_token" and self.api_key:
                headers["X-API-Key"] = self.api_key
            elif self.auth_type in ["jwt", "bearer"] and self.jwt_token:
                headers["Authorization"] = f"Bearer {self.jwt_token}"
        
        return headers