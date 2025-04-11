from typing import Optional
try:
    from PyQt6.QtWidgets import QMenu, QMainWindow
    from PyQt6.QtGui import QAction
except ImportError:
    from PyQt5.QtWidgets import QMenu, QMainWindow
    from PyQt5.QtGui import QAction 
from ..base import ArtisanPlugin
from .config import RESTPluginConfig as RESTConfig
from .client import RESTClient

class RESTPlugin(ArtisanPlugin):
    @property
    def name(self) -> str:
        return "REST API"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def __init__(self):
        super().__init__()
        self.config = RESTConfig()
        self.client: Optional[RESTClient] = None
    
    def initialize(self, main_window: QMainWindow) -> None:
        super().initialize(main_window)
        self.client = RESTClient(
            base_url=self.config.base_url,
            api_key=self.config.api_key
        )
        self.main_window.sendmessageSignal.connect(self._handle_message)
    
    def _handle_message(self, message: str, error: bool = False, status: str = "") -> None:
        """Handle erorrs"""
        if error:
            self.logger.error(message)
        else:
            self.logger.info(message)
            
    def _show_status(self, message: str, error: bool = False) -> None:
        """Show status messages in UI"""
        if hasattr(self.main_window, 'sendmessageSignal'):
            self.main_window.sendmessageSignal.emit(message, error, "REST Plugin")
    
    def create_menu(self, parent_menu: QMenu) -> QMenu:
        menu = QMenu(self.name, parent_menu)
        
        # Configure action
        config_action = QAction("Configure API", menu)
        config_action.triggered.connect(self._configure)
        menu.addAction(config_action)
        
        # Test connection action
        test_action = QAction("Test Connection", menu)
        test_action.triggered.connect(self._test_connection)
        menu.addAction(test_action)
        
        return menu
    
    def on_roast_end(self) -> None:
        """Auto-save roast data"""
        if self.config.auto_save:
            self._save_roast_data()
    
    def _configure(self) -> None:
        from .config_dialog import ConfigDialog
        dialog = ConfigDialog(self.config, self.main_window)
        if dialog.exec():
            self.client = RESTClient(
                base_url=self.config.base_url,
                api_key=self.config.api_key
            )
    
    def _save_roast_data(self) -> None:
        """Save current roast data via REST API"""
        try:
            if not self.client:
                return
                
            profile_data = self.main_window.getProfile() 
            
            success = self.client.send_roast_data(profile_data)
            
            if success:
                self.logger.info("Roast data saved successfully")
            else:
                self.logger.error("Failed to save roast data")
                
        except Exception as e:
            self.logger.exception("Error saving roast data: %s", str(e))
    
    def _test_connection(self) -> None:
        if self.client:
            self.client.test_connection()

    def _handle_error(self, message: str, exception: Optional[Exception] = None) -> None:
        error_msg = f"{message}: {str(exception)}" if exception else message
        self._show_status(error_msg, error=True)
        if hasattr(self.main_window, 'updateErrorLogSignal'):
            self.main_window.updateErrorLogSignal.emit()

    def cleanup(self) -> None:
        """Cleanup plugin resources"""
        if self.client:
            self.client = None
        if hasattr(self, 'config'):
            self.config.save_config()  