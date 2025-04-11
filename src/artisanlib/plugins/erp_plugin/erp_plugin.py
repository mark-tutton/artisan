from typing import Optional, Dict, Any
from PyQt6.QtWidgets import QMenu, QAction, QMainWindow
from ..base import ArtisanPlugin
from .config import ERPConfig
from .client import NetSuiteClient

class ERPPlugin(ArtisanPlugin):
    @property
    def name(self) -> str:
        return "NetSuite ERP"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def __init__(self):
        super().__init__()
        self.config = ERPConfig()
        self.client: Optional[NetSuiteClient] = None
        self.current_work_order = None
    
    def initialize(self, main_window: QMainWindow) -> None:
        super().initialize(main_window)
        self.client = NetSuiteClient(
            account=self.config.account,
            token=self.config.token
        )
    
    def create_menu(self, parent_menu: QMenu) -> QMenu:
        menu = QMenu(self.name, parent_menu)
        
        # Work Orders
        work_orders_menu = QMenu("Work Orders", menu)
        actions = {
            "View Work Orders": self._view_work_orders,
            "Start Work Order": self._start_work_order,
            "Complete Work Order": self._complete_work_order
        }
        for name, handler in actions.items():
            action = QAction(name, work_orders_menu)
            action.triggered.connect(handler)
            work_orders_menu.addAction(action)
        menu.addMenu(work_orders_menu)
        
        # Configuration
        config_action = QAction("Configure", menu)
        config_action.triggered.connect(self._configure)
        menu.addAction(config_action)
        
        return menu
    
    def on_roast_end(self) -> None:
        """Update work order on roast completion"""
        if self.current_work_order and self.config.auto_complete:
            self._complete_current_work_order()