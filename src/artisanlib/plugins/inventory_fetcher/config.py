import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

_log = logging.getLogger(__name__)

@dataclass
class InventoryFetcherConfig:
    """Configuration for inventory fetcher plugin using global auth manager"""
    
    # Gateway settings
    gateway_url: str = "http://localhost:5101"
    
    # Health check settings
    health_check_enabled: bool = True
    health_check_interval: int = 300  # seconds (5 minutes)
    health_check_url: str = "/api/inventory/health"

    # Inventory endpoint settings
    inventory_endpoint: str = "/api/inventory/available/artisan"
    
    
    # UI settings
    auto_fetch_on_startup: bool = False
    show_notifications: bool = True
    
    # File paths
    config_file: str = "inventory_fetcher_config.json"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            "gateway_url": self.gateway_url,
            "health_check_enabled": self.health_check_enabled,
            "health_check_interval": self.health_check_interval,
            "health_check_url": self.health_check_url,
            "inventory_endpoint": self.inventory_endpoint,
            "auto_fetch_on_startup": self.auto_fetch_on_startup,
            "show_notifications": self.show_notifications,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InventoryFetcherConfig':
        """Create config from dictionary with backward compatibility"""
        # Handle migration from old config format
        if 'use_gateway' in data and data['use_gateway']:
            # Migrate from old gateway config
            if 'gateway_url' in data:
                data['gateway_url'] = data['gateway_url']
            elif 'server_url' in data and data['server_url']:
                # Convert old server_url to gateway_url
                old_url = data['server_url']
                if not old_url.startswith(('http://', 'https://')):
                    old_url = f"http://{old_url}"
                data['gateway_url'] = old_url
        
        # Set default inventory_endpoint if not present (backward compatibility)
        if 'inventory_endpoint' not in data:
            data['inventory_endpoint'] = "/api/inventory/available/artisan"
        
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
    
    def get_effective_url(self) -> str:
        """Get the effective URL to use for requests"""
        return self.gateway_url