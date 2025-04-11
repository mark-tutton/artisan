from typing import Optional, Dict, Any
from PyQt6.QtWidgets import QMenu, QAction, QMainWindow
from ..base import ArtisanPlugin
from .config import WebSocketConfig
from .server import WebSocketServer

class WebSocketPlugin(ArtisanPlugin):
    @property
    def name(self) -> str:
        return "WebSocket Server"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def __init__(self):
        super().__init__()
        self.config = WebSocketConfig()
        self.server: Optional[WebSocketServer] = None
    
    def initialize(self, main_window: QMainWindow) -> None:
        super().initialize(main_window)
        if self.config.auto_start:
            self._start_server()
        self.main_window.sendmessageSignal.connect(self._handle_message)
    
    def create_menu(self, parent_menu: QMenu) -> QMenu:
        menu = QMenu(self.name, parent_menu)
        
        # Server controls
        self.start_action = QAction("Start Server", menu)
        self.start_action.triggered.connect(self._start_server)
        menu.addAction(self.start_action)
        
        self.stop_action = QAction("Stop Server", menu)
        self.stop_action.triggered.connect(self._stop_server)
        menu.addAction(self.stop_action)
        
        menu.addSeparator()
        
        # Configuration
        config_action = QAction("Configure", menu)
        config_action.triggered.connect(self._configure)
        menu.addAction(config_action)
        
        return menu
    
    def on_data_update(self, data: Dict[str, Any]) -> None:
        """Broadcast roast data to clients"""
        if self.server and self.server.is_running:
            self.server.broadcast_data(data)
    
    def _handle_message(self, message: str, error: bool = False, status: str = "") -> None:
        """Handle messages from the plugin"""
        if error:
            self.logger.error(message)
        else:
            self.logger.info(message)
    
    def _show_status(self, message: str, error: bool = False) -> None:
        """Show status messages in UI"""
        if hasattr(self.main_window, 'sendmessageSignal'):
            self.main_window.sendmessageSignal.emit(message, error, "WebSocket Plugin")