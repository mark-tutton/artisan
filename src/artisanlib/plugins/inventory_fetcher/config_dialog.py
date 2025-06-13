import sys
from typing import Optional

try:
    from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                                QLineEdit, QSpinBox, QCheckBox, QPushButton,
                                QLabel, QGroupBox, QMessageBox)
    from PyQt6.QtCore import Qt
except ImportError:
    from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                                QLineEdit, QSpinBox, QCheckBox, QPushButton,
                                QLabel, QGroupBox, QMessageBox)
    from PyQt5.QtCore import Qt

from .config import InventoryFetcherConfig
from .inventory_fetcher import InventoryFetcher

class InventoryFetcherConfigDialog(QDialog):
    def __init__(self, parent, config: InventoryFetcherConfig):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Inventory Fetcher Configuration")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Server settings group
        server_group = QGroupBox("Server Settings")
        server_layout = QFormLayout()
        
        self.server_url_edit = QLineEdit(self.config.server_url)
        self.server_url_edit.setPlaceholderText("http://localhost:4000/api/inventory")
        server_layout.addRow("Server URL:", self.server_url_edit)
        
        self.api_key_edit = QLineEdit(self.config.api_key)
        self.api_key_edit.setPlaceholderText("API Key (optional)")
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        server_layout.addRow("API Key:", self.api_key_edit)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 120)
        self.timeout_spin.setValue(self.config.timeout)
        server_layout.addRow("Timeout (seconds):", self.timeout_spin)
        
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)
        
        # UI settings group
        ui_group = QGroupBox("UI Settings")
        ui_layout = QFormLayout()
        
        self.auto_fetch_checkbox = QCheckBox()
        self.auto_fetch_checkbox.setChecked(self.config.auto_fetch_on_startup)
        ui_layout.addRow("Auto-fetch on startup:", self.auto_fetch_checkbox)
        
        self.show_notifications_checkbox = QCheckBox()
        self.show_notifications_checkbox.setChecked(self.config.show_notifications)
        ui_layout.addRow("Show notifications:", self.show_notifications_checkbox)
        
        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)
        
        # Test connection button
        test_button = QPushButton("Test Connection")
        test_button.clicked.connect(self.test_connection)
        layout.addWidget(test_button)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_and_accept)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def test_connection(self):
        """Test connection to server"""
        try:
            fetcher = InventoryFetcher(
                self.server_url_edit.text(),
                self.api_key_edit.text(),
                self.timeout_spin.value()
            )
            
            if fetcher.test_connection():
                QMessageBox.information(self, "Success", "Connection successful!")
            else:
                QMessageBox.warning(self, "Warning", "Connection failed!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection error: {e}")
    
    def save_and_accept(self):
        """Save configuration and close dialog"""
        self.config.server_url = self.server_url_edit.text()
        self.config.api_key = self.api_key_edit.text()
        self.config.timeout = self.timeout_spin.value()
        self.config.auto_fetch_on_startup = self.auto_fetch_checkbox.isChecked()
        self.config.show_notifications = self.show_notifications_checkbox.isChecked()
        
        self.config.save_config()
        self.accept()