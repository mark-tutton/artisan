from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
try:
    from PyQt6.QtWidgets import QMenu, QMainWindow
except ImportError:
    from PyQt5.QtWidgets import QMenu, QMainWindow
import logging

class ArtisanPlugin(ABC):
    """Base class for plugins"""
    
    def __init__(self):
        self.main_window: Optional[QMainWindow] = None
        self.logger = logging.getLogger(f"artisan.plugins.{self.name}")
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""
        pass
        
    @abstractmethod
    def initialize(self, main_window: QMainWindow) -> None:
        """Initialize the plugin"""
        self.main_window = main_window
        self.logger.info(f"Initializing {self.name} v{self.version}")
    
    @abstractmethod
    def cleanup(self) -> None:
        """Cleanup when plugin is disabled/unloaded"""
        self.logger.info(f"Cleaning up {self.name}")
    
    def create_menu(self, parent_menu: QMenu) -> Optional[QMenu]:
        """Create plugin menu items"""
        return None
    
    def on_roast_start(self) -> None:
        """Called when a roast starts"""
        pass
    
    def on_roast_end(self) -> None:
        """Called when a roast ends"""
        pass
    
    def on_data_update(self, data: Dict[str, Any]) -> None:
        """Called when new roast data is available"""
        pass