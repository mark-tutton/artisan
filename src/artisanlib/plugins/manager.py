from typing import Dict, Type, Optional, Any
from PyQt6.QtWidgets import QMenu, QMainWindow
import logging
from .base import ArtisanPlugin

logger = logging.getLogger("artisan.plugins.manager")

class PluginManager:
    def __init__(self, main_window: QMainWindow):
        self.main_window = main_window
        self.plugins: Dict[str, ArtisanPlugin] = {}
        self.plugin_menu: Optional[QMenu] = None
        logger.info("Plugin manager initialized")
    
    def register_plugin(self, plugin_class: Type[ArtisanPlugin]) -> None:
        """Register a new plugin"""
        try:
            plugin = plugin_class()
            name = plugin.name
            
            if name in self.plugins:
                logger.warning(f"Plugin {name} already registered")
                return
                
            self.plugins[name] = plugin
            plugin.initialize(self.main_window)
            
            # Create plugin menu 
            if self.plugin_menu is None:
                menubar = self.main_window.menuBar()
                self.plugin_menu = menubar.addMenu("Plugins")
            
            # Add plugin menu items
            plugin_menu = plugin.create_menu(self.plugin_menu)
            if plugin_menu:
                self.plugin_menu.addMenu(plugin_menu)
                
            logger.info(f"Plugin {name} v{plugin.version} registered successfully")
            
        except Exception as e:
            logger.error(f"Failed to register plugin: {str(e)}")
            raise
    
    def get_plugin(self, name: str) -> Optional[ArtisanPlugin]:
        """Get a plugin by name"""
        return self.plugins.get(name)
    
    def unregister_plugin(self, plugin_name: str) -> None:
        """Unregister a plugin"""
        if plugin_name in self.plugins:
            try:
                plugin = self.plugins[plugin_name]
                plugin.cleanup()
                del self.plugins[plugin_name]
                logger.info(f"Plugin {plugin_name} unregistered")
            except Exception as e:
                logger.error(f"Error unregistering plugin {plugin_name}: {str(e)}")
    
    def notify_all(self, event: str, data: Any = None) -> None:
        """Notify all plugins of an event"""
        for plugin in self.plugins.values():
            try:
                handler = getattr(plugin, f"on_{event}", None)
                if handler:
                    handler(data) if data is not None else handler()
            except Exception as e:
                logger.error(f"Error in plugin {plugin.name} handling {event}: {str(e)}")
    
    def notify_roast_start(self) -> None:
        """Notify all plugins that a roast has started"""
        self.notify_all("roast_start")
    
    def notify_roast_end(self) -> None:
        """Notify all plugins that a roast has ended"""
        self.notify_all("roast_end")
    
    def notify_data_update(self, data: Dict[str, Any]) -> None:
        """Notify all plugins of new roast data"""
        self.notify_all("data_update", data)