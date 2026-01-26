import sys
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QFormLayout,
        QLineEdit,
        QSpinBox,
        QCheckBox,
        QPushButton,
        QLabel,
        QGroupBox,
        QMessageBox,
    )
    from PyQt6.QtCore import Qt
except ImportError:
    from PyQt5.QtWidgets import (
        QDialog,
        QVBoxLayout,
        QHBoxLayout,
        QFormLayout,
        QLineEdit,
        QSpinBox,
        QCheckBox,
        QPushButton,
        QLabel,
        QGroupBox,
        QMessageBox,
    )
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
        self.resize(400, 300)

        layout = QVBoxLayout()

        # Gateway settings group
        gateway_group = QGroupBox("Gateway Settings")
        gateway_layout = QFormLayout()

        self.gateway_url_edit = QLineEdit(self.config.gateway_url)
        self.gateway_url_edit.setPlaceholderText("http://localhost:5101")
        gateway_layout.addRow("Gateway URL:", self.gateway_url_edit)

        # Inventory endpoint field
        self.inventory_endpoint_edit = QLineEdit(self.config.inventory_endpoint)
        self.inventory_endpoint_edit.setPlaceholderText("/api/inventory/available/artisan")
        gateway_layout.addRow("Inventory Endpoint:", self.inventory_endpoint_edit)

        gateway_group.setLayout(gateway_layout)
        layout.addWidget(gateway_group)

         # Health check settings group
        health_group = QGroupBox("Health Check Settings")
        health_layout = QFormLayout()

        self.health_check_checkbox = QCheckBox()
        self.health_check_checkbox.setChecked(self.config.health_check_enabled)
        health_layout.addRow("Enable Health Check:", self.health_check_checkbox)

        self.health_interval_spin = QSpinBox()
        self.health_interval_spin.setRange(60, 3600)  # 1 minute to 1 hour
        self.health_interval_spin.setValue(self.config.health_check_interval)
        self.health_interval_spin.setSuffix(" seconds")
        health_layout.addRow("Health Check Interval:", self.health_interval_spin)

        # Add health check URL field
        self.health_check_url_edit = QLineEdit(self.config.health_check_url)
        self.health_check_url_edit.setPlaceholderText("/gateway/health")
        health_layout.addRow("Health Check URL:", self.health_check_url_edit)

        health_group.setLayout(health_layout)
        layout.addWidget(health_group)

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
            # Create a temporary config for testing
            test_config = InventoryFetcherConfig()
            test_config.gateway_url = self.gateway_url_edit.text()
            test_config.health_check_enabled = self.health_check_checkbox.isChecked()
            test_config.health_check_interval = self.health_interval_spin.value()
            test_config.health_check_url = self.health_check_url_edit.text()

            fetcher = InventoryFetcher(test_config)

            if fetcher.test_connection():
                QMessageBox.information(self, "Success", "Connection successful!")
            else:
                QMessageBox.warning(self, "Warning", "Connection failed!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Connection error: {e}")

    def save_and_accept(self):
        """Save configuration and close dialog"""
        # Gateway settings
        self.config.gateway_url = self.gateway_url_edit.text()
        self.config.inventory_endpoint = self.inventory_endpoint_edit.text()
        
        # Health check settings
        self.config.health_check_enabled = self.health_check_checkbox.isChecked()
        self.config.health_check_interval = self.health_interval_spin.value()
        self.config.health_check_url = self.health_check_url_edit.text() 
        
        # UI settings
        self.config.auto_fetch_on_startup = self.auto_fetch_checkbox.isChecked()
        self.config.show_notifications = self.show_notifications_checkbox.isChecked()

        self.config.save_config()
        self.accept()