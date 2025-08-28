import logging
from typing import Dict, List, Any, Optional

try:
    from PyQt6.QtWidgets import QComboBox, QWidget
    from PyQt6.QtCore import pyqtSignal, QMutex, QTimer
except ImportError:
    from PyQt5.QtWidgets import QComboBox, QWidget
    from PyQt5.QtCore import pyqtSignal, QMutex, QTimer

class InventoryComboBox(QComboBox):
    """Custom combo box that integrates with inventory fetcher plugin with thread safety"""
    
    bean_selected = pyqtSignal(dict)  
    inventory_refresh_requested = pyqtSignal()
    
    def __init__(self, parent: QWidget, inventory_plugin=None):
        super().__init__(parent)
        self.inventory_plugin = inventory_plugin
        self.logger = logging.getLogger(__name__)
        
        # Thread safety
        self._mutex = QMutex()
        self._beans_data = []
        self._populate_pending = False
        
        # Connect to inventory plugin signals 
        if self.inventory_plugin:
            self._connect_plugin_signals()
        
        # Connect selection change
        self.currentIndexChanged.connect(self.on_selection_changed)
    
    def _connect_plugin_signals(self):
        """Connect to plugin signals with thread safety"""
        try:
            if self.inventory_plugin:
                try:
                    self.inventory_plugin.signals.inventory_updated.disconnect(self.on_inventory_updated)
                except:
                    pass
                
                # Connect to inventory updates
                self.inventory_plugin.signals.inventory_updated.connect(self.on_inventory_updated)
                
                # Connect to fetch completion/failure signals
                if hasattr(self.inventory_plugin.signals, 'fetch_completed'):
                    self.inventory_plugin.signals.fetch_completed.connect(self.on_fetch_completed)
                if hasattr(self.inventory_plugin.signals, 'fetch_failed'):
                    self.inventory_plugin.signals.fetch_failed.connect(self.on_fetch_failed)
                    
        except Exception as e:
            self.logger.error(f"Error connecting plugin signals: {e}")
    
    def set_inventory_plugin(self, plugin):
        """Set the inventory plugin reference with thread safety"""
        try:
            # Disconnect from old plugin
            if self.inventory_plugin:
                try:
                    self.inventory_plugin.signals.inventory_updated.disconnect(self.on_inventory_updated)
                except:
                    pass
            
            self.inventory_plugin = plugin
            self._connect_plugin_signals()
            
        except Exception as e:
            self.logger.error(f"Error setting inventory plugin: {e}")
    
    def on_inventory_updated(self, beans_data: List[Dict[str, Any]]):
        """Handle inventory updates from the plugin with thread safety"""
        try:
            QTimer.singleShot(0, lambda: self._update_inventory_safe(beans_data))
        except Exception as e:
            self.logger.error(f"Error handling inventory update: {e}")
    
    def _update_inventory_safe(self, beans_data: List[Dict[str, Any]]):
        """Safely update inventory data in main thread"""
        try:
            self._mutex.lock()
            try:
                self._beans_data = beans_data
                self._populate_pending = True
                
                QTimer.singleShot(0, self.populate_combo)
                
            finally:
                self._mutex.unlock()
                
        except Exception as e:
            self.logger.error(f"Error updating inventory safely: {e}")
    
    def on_fetch_completed(self, beans_data: List[Dict[str, Any]]):
        """Handle fetch completion signal"""
        try:
            self.logger.debug("Fetch completed, updating combo box")
            self.on_inventory_updated(beans_data)
        except Exception as e:
            self.logger.error(f"Error handling fetch completion: {e}")
    
    def on_fetch_failed(self, error_message: str):
        """Handle fetch failure signal"""
        try:
            self.logger.warning(f"Fetch failed: {error_message}")
            # Could add visual feedback here (e.g., error icon, tooltip)
        except Exception as e:
            self.logger.error(f"Error handling fetch failure: {e}")
    
    def populate_combo(self):
        """Populate the combo box with inventory data with thread safety"""
        try:
            self._mutex.lock()
            try:
                if not self._populate_pending:
                    return
                    
                self.clear()
                self.addItem("Select a bean from inventory...")
                
                for bean in self._beans_data:
                    name = bean.get('name', 'Unknown')
                    if 'origin' in bean and bean['origin']:
                        name += f" ({bean['origin']})"
                    if 'variety' in bean and bean['variety']:
                        name += f" - {bean['variety']}"
                    # TODO: add more info
                    
                    self.addItem(name, bean)
                
                self._populate_pending = False
                
            finally:
                self._mutex.unlock()
                
        except Exception as e:
            self.logger.error(f"Error populating combo box: {e}")
    
    def on_selection_changed(self, index: int):
        """Handle selection changes with thread safety"""
        try:
            if index > 0 and self.inventory_plugin:  # Skip "Select a bean..." item
                bean_data = self.itemData(index)
                if bean_data:
                    # Emit signal for external listeners
                    self.bean_selected.emit(bean_data)
                    
                    # Auto-populate roast properties if dialog is registered
                    QTimer.singleShot(0, lambda: self._populate_roast_properties_safe(bean_data))
                    
        except Exception as e:
            self.logger.error(f"Error handling selection change: {e}")
    
    def _populate_roast_properties_safe(self, bean_data: Dict[str, Any]):
        """Safely populate roast properties in main thread"""
        try:
            if self.inventory_plugin and hasattr(self.inventory_plugin, 'populate_roast_properties_fields'):
                self.inventory_plugin.populate_roast_properties_fields(bean_data)
        except Exception as e:
            self.logger.error(f"Error populating roast properties: {e}")
    
    def get_selected_bean(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected bean data with thread safety"""
        try:
            self._mutex.lock()
            try:
                index = self.currentIndex()
                if index > 0:  # Skip "Select a bean..." item
                    return self.itemData(index)
                return None
            finally:
                self._mutex.unlock()
        except Exception as e:
            self.logger.error(f"Error getting selected bean: {e}")
            return None
    
    def refresh_inventory(self):
        """Refresh inventory data with thread safety"""
        try:
            if self.inventory_plugin:
                # Emit signal to request refresh (plugin will handle threading)
                self.inventory_refresh_requested.emit()
                
                # Also call directly if the plugin supports it
                if hasattr(self.inventory_plugin, 'fetch_beans'):
                    self.inventory_plugin.fetch_beans()
            else:
                self.logger.warning("No inventory plugin available for refresh")
                
        except Exception as e:
            self.logger.error(f"Error refreshing inventory: {e}")
    
    def get_beans_data(self) -> List[Dict[str, Any]]:
        """Get current beans data with thread safety"""
        try:
            self._mutex.lock()
            try:
                return self._beans_data.copy() 
            finally:
                self._mutex.unlock()
        except Exception as e:
            self.logger.error(f"Error getting beans data: {e}")
            return []
    
    def set_beans_data(self, beans_data: List[Dict[str, Any]]):
        """Set beans data with thread safety"""
        try:
            self.on_inventory_updated(beans_data)
        except Exception as e:
            self.logger.error(f"Error setting beans data: {e}")