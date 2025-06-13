import logging
from typing import Dict, List, Any, Optional

try:
    from PyQt6.QtWidgets import QMenu, QComboBox, QPushButton, QMessageBox, QDialog
    from PyQt6.QtGui import QAction
    from PyQt6.QtCore import QTimer, pyqtSignal, QObject
except ImportError:
    from PyQt5.QtWidgets import QMenu, QComboBox, QPushButton, QMessageBox, QDialog
    from PyQt5.QtGui import QAction
    from PyQt5.QtCore import QTimer, pyqtSignal, QObject

from ..base import ArtisanPlugin
from .config import InventoryFetcherConfig
from .inventory_fetcher import InventoryFetcher
from .config_dialog import InventoryFetcherConfigDialog

class InventorySignals(QObject):
    """QObject for handling signals"""
    inventory_updated = pyqtSignal(list)

class InventoryFetcherPlugin(ArtisanPlugin):
    """Plugin for fetching beans data from external server"""
    
    @property
    def name(self) -> str:
        """Plugin name"""
        return "Inventory Fetcher"
    
    @property
    def version(self) -> str:
        """Plugin version"""
        return "1.0.0"
    
    def __init__(self):
        super().__init__()
        
        self.signals = InventorySignals()
        
        self.config = InventoryFetcherConfig.load_config()
        self.fetcher = None
        self.beans_data = []
        self.roast_properties_dialog = None
        
    def initialize(self, main_window) -> None:
        """Initialize the plugin"""
        super().initialize(main_window)
        
        # create fetcher if server URL is configured
        if self.config.server_url:
            self.fetcher = InventoryFetcher(
                self.config.server_url,
                self.config.api_key,
                self.config.timeout
            )
            
            # auto-fetch on startup if enabled
            if self.config.auto_fetch_on_startup:
                QTimer.singleShot(1000, self.fetch_beans)
    
    def cleanup(self) -> None:
        """Cleanup the plugin"""
        super().cleanup()
    
    def create_menu(self, parent_menu: QMenu) -> QMenu:
        """Create plugin menu items"""
        # Main plugin menu
        plugin_menu = QMenu("Inventory Fetcher", parent_menu)
        parent_menu.addMenu(plugin_menu)
        
        # Configure action
        configure_action = QAction("Configure", self.main_window)
        configure_action.triggered.connect(self.show_config_dialog)
        plugin_menu.addAction(configure_action)
        
        # Fetch beans action
        fetch_action = QAction("Fetch Inventory", self.main_window)
        fetch_action.triggered.connect(self.fetch_beans)
        plugin_menu.addAction(fetch_action)
        
        # Refresh action
        refresh_action = QAction("Refresh Inventory", self.main_window)
        refresh_action.triggered.connect(self.refresh_beans)
        plugin_menu.addAction(refresh_action)
        
        plugin_menu.addSeparator()
        
        # About action
        about_action = QAction("About", self.main_window)
        about_action.triggered.connect(self.show_about)
        plugin_menu.addAction(about_action)
        
        return plugin_menu
    
    def show_config_dialog(self):
        """Show configuration dialog"""
        dialog = InventoryFetcherConfigDialog(self.main_window, self.config)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # recreate fetcher with new config
            if self.config.server_url:
                self.fetcher = InventoryFetcher(
                    self.config.server_url,
                    self.config.api_key,
                    self.config.timeout
                )

    def fetch_beans(self):
        """Fetch beans from server"""
        if not self.fetcher:
            QMessageBox.warning(self.main_window, "Warning", "Please configure server URL first!")
            return

        try:
            self.logger.info("Fetching beans from server")
            result = self.fetcher.fetch_beans()
            if isinstance(result, dict) and "data" in result:
                self.beans_data = result["data"]
            else:
                self.beans_data = result

            if self.config.show_notifications:
                self.main_window.sendmessage(f"Fetched {len(self.beans_data)} beans from server")

            self.logger.info(f"Successfully fetched {len(self.beans_data)} beans")
            self.signals.inventory_updated.emit(self.beans_data)

        except Exception as e:
            self.logger.error(f"Failed to fetch beans: {e}")
            if self.config.show_notifications:
                QMessageBox.critical(self.main_window, "Error", f"Failed to fetch beans: {e}")
    
    def refresh_beans(self):
        """Refresh beans data"""
        self.fetch_beans()
    
    def get_beans_data(self) -> List[Dict[str, Any]]:
        """Get current beans data"""
        return self.beans_data
    
    def populate_beans_combo(self, combo_box: QComboBox):
        combo_box.clear()
        combo_box.addItem("Select a bean...")
        if hasattr(self.main_window, "addmessage"):
            self.main_window.addmessage(f"Populating inventory_combo with beans_data of type: {type(self.beans_data)} length: {len(self.beans_data)}")
        for i, bean in enumerate(self.beans_data):
            if hasattr(self.main_window, "addmessage"):
                self.main_window.addmessage(f"DEBUG: Bean {i}: {bean}")
            combo_box.addItem(bean.get('name', 'Unknown'), bean)
        if hasattr(self.main_window, "addmessage"):
            self.main_window.addmessage(f"DEBUG: Combo count after population: {combo_box.count()}")
    
    def get_selected_bean(self, combo_box: QComboBox) -> Optional[Dict[str, Any]]:
        """Get selected bean data from combo box"""
        index = combo_box.currentIndex()
        if index > 0:  # skip "Select a bean..." item
            return combo_box.itemData(index)
        return None
    
    def register_roast_properties_dialog(self, dialog):
        """Register the roast properties dialog for integration"""
        self.roast_properties_dialog = dialog
        self.logger.info("Roast properties dialog registered for inventory integration")
    
    def populate_roast_properties_fields(self, bean_data: Dict[str, Any]): # TODO: this is not used yet---being handled in roast_properties_patch.py -- remove dupe logic
        """Populate roast properties fields with bean data"""
        if not self.roast_properties_dialog:
            return
        
        try:
            # populate basic bean information
            if 'name' in bean_data:
                self.roast_properties_dialog.beansedit.setPlainText(bean_data['name'])
            
            # populate density if available
            if 'density' in bean_data:
                density = bean_data['density']
                if isinstance(density, (int, float)):
                    self.roast_properties_dialog.bean_density_in_edit.setText(str(density))
            
            # Populate moisture if available
            if 'moisture' in bean_data:
                moisture = bean_data['moisture']
                if isinstance(moisture, (int, float)):
                    self.roast_properties_dialog.moisture_greens_edit.setText(str(moisture))
            
            # Populate bean size if available
            if 'bean_size_min' in bean_data:
                size_min = bean_data['bean_size_min']
                if isinstance(size_min, (int, float)):
                    self.roast_properties_dialog.bean_size_min_edit.setText(str(size_min))
            
            if 'bean_size_max' in bean_data:
                size_max = bean_data['bean_size_max']
                if isinstance(size_max, (int, float)):
                    self.roast_properties_dialog.bean_size_max_edit.setText(str(size_max))
            
            # TODO: populate title field, stock, blend, store fields
            
            self.logger.info(f"Populated roast properties with bean data: {bean_data.get('name', 'Unknown')}")
            
        except Exception as e:
            self.logger.error(f"Error populating roast properties: {e}")
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.information(
            self.main_window,
            "About Inventory Fetcher",
            f"<h3>Inventory Fetcher Plugin</h3>"
            f"<p><b>Version:</b> {self.version}</p>"
            f"<p>Fetches beans data from external inventory server.</p>"
            f"<p>Configure the server URL and API key in the plugin settings.</p>"
        )