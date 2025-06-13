import logging
from typing import Dict, List, Any, Optional

try:
    from PyQt6.QtWidgets import QComboBox, QWidget
    from PyQt6.QtCore import pyqtSignal
except ImportError:
    from PyQt5.QtWidgets import QComboBox, QWidget
    from PyQt5.QtCore import pyqtSignal

class InventoryComboBox(QComboBox):
    """Custom combo box that integrates with inventory fetcher plugin"""
    
    bean_selected = pyqtSignal(dict)  # Signal emitted when a bean is selected
    
    def __init__(self, parent: QWidget, inventory_plugin=None):
        super().__init__(parent)
        self.inventory_plugin = inventory_plugin
        self.logger = logging.getLogger(__name__)
        self.beans_data = []
        
        # Connect to inventory plugin signals 
        if self.inventory_plugin:
            self.inventory_plugin.inventory_updated.connect(self.on_inventory_updated)
        
        # Connect selection change
        self.currentIndexChanged.connect(self.on_selection_changed)
    
    def set_inventory_plugin(self, plugin):
        """Set the inventory plugin reference"""
        self.inventory_plugin = plugin
        if self.inventory_plugin:
            self.inventory_plugin.inventory_updated.connect(self.on_inventory_updated)
    
    def on_inventory_updated(self, beans_data: List[Dict[str, Any]]):
        """Handle inventory updates from the plugin"""
        self.beans_data = beans_data
        self.populate_combo()
    
    def populate_combo(self):
        """Populate the combo box with inventory data"""
        self.clear()
        self.addItem("Select a bean from inventory...")
        
        for bean in self.beans_data:
            name = bean.get('name', 'Unknown')
            if 'origin' in bean and bean['origin']:
                name += f" ({bean['origin']})"
            if 'variety' in bean and bean['variety']:
                name += f" - {bean['variety']}"
            # TODO: add more info
            
            self.addItem(name, bean)
    
    def on_selection_changed(self, index: int):
        """Handle selection changes"""
        if index > 0 and self.inventory_plugin:  # Skip "Select a bean..." item
            bean_data = self.itemData(index)
            if bean_data:
                self.bean_selected.emit(bean_data)
                # Auto-populate roast properties if dialog is registered
                self.inventory_plugin.populate_roast_properties_fields(bean_data)
    
    def get_selected_bean(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected bean data"""
        index = self.currentIndex()
        if index > 0:  # Skip "Select a bean..." item
            return self.itemData(index)
        return None
    
    def refresh_inventory(self):
        """Refresh inventory data"""
        if self.inventory_plugin:
            self.inventory_plugin.fetch_beans()