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
        QComboBox,
        QTabWidget,
        QWidget,
        QTextEdit,
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
        QComboBox,
        QTabWidget,
        QWidget,
        QTextEdit,
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
        self.resize(600, 500)

        layout = QVBoxLayout()

        # Create tab widget
        tab_widget = QTabWidget()

        # Gateway tab
        gateway_tab = self.create_gateway_tab()
        tab_widget.addTab(gateway_tab, "Gateway")

        # Legacy tab
        legacy_tab = self.create_legacy_tab()
        tab_widget.addTab(legacy_tab, "Legacy")

        # UI settings tab
        ui_tab = self.create_ui_tab()
        tab_widget.addTab(ui_tab, "UI Settings")

        layout.addWidget(tab_widget)

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

        self.initialize_ui_state()

    def create_gateway_tab(self) -> QWidget:
        """Create gateway configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout()

        # Gateway settings group
        gateway_group = QGroupBox("Gateway Settings")
        gateway_layout = QFormLayout()

        self.use_gateway_checkbox = QCheckBox()
        self.use_gateway_checkbox.setChecked(self.config.use_gateway)
        self.use_gateway_checkbox.stateChanged.connect(self.on_gateway_mode_changed)
        gateway_layout.addRow("Use Gateway:", self.use_gateway_checkbox)

        self.gateway_url_edit = QLineEdit(self.config.gateway_url)
        self.gateway_url_edit.setPlaceholderText("http://localhost:5101")
        gateway_layout.addRow("Gateway URL:", self.gateway_url_edit)

        self.gateway_auth_type_combo = QComboBox()
        self.gateway_auth_type_combo.addItems(["google", "jwt", "api_key"])
        self.gateway_auth_type_combo.setCurrentText(self.config.gateway_auth_type)
        self.gateway_auth_type_combo.currentTextChanged.connect(self.on_auth_type_changed)
        gateway_layout.addRow("Auth Type:", self.gateway_auth_type_combo)

        gateway_group.setLayout(gateway_layout)
        layout.addWidget(gateway_group)

        # Authentication settings group
        auth_group = QGroupBox("Authentication Settings")
        auth_layout = QFormLayout()

        self.jwt_token_edit = QLineEdit(self.config.jwt_token)
        self.jwt_token_edit.setPlaceholderText("JWT Token (for Google/JWT auth)")
        self.jwt_token_edit.setEchoMode(QLineEdit.EchoMode.Password)
        auth_layout.addRow("JWT Token:", self.jwt_token_edit)

        self.gateway_api_key_edit = QLineEdit(self.config.gateway_api_key)
        self.gateway_api_key_edit.setPlaceholderText("API Key (for API key auth)")
        self.gateway_api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        auth_layout.addRow("Gateway API Key:", self.gateway_api_key_edit)

        self.gateway_username_edit = QLineEdit(self.config.gateway_username)
        self.gateway_username_edit.setPlaceholderText("Username (optional)")
        auth_layout.addRow("Username:", self.gateway_username_edit)

        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)

        # Security settings group
        security_group = QGroupBox("Security Settings")
        security_layout = QFormLayout()

        self.use_ssl_checkbox = QCheckBox()
        self.use_ssl_checkbox.setChecked(self.config.use_ssl)
        security_layout.addRow("Use SSL:", self.use_ssl_checkbox)

        self.validate_ssl_checkbox = QCheckBox()
        self.validate_ssl_checkbox.setChecked(self.config.validate_ssl_cert)
        security_layout.addRow("Validate SSL Cert:", self.validate_ssl_checkbox)

        security_group.setLayout(security_layout)
        layout.addWidget(security_group)

        tab.setLayout(layout)
        return tab

    def create_legacy_tab(self) -> QWidget:
        """Create legacy configuration tab"""
        tab = QWidget()
        layout = QVBoxLayout()

        # Server settings group
        server_group = QGroupBox("Legacy Server Settings")
        server_layout = QFormLayout()

        self.server_url_edit = QLineEdit(self.config.server_url)
        self.server_url_edit.setPlaceholderText("http://localhost:3000")
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

        tab.setLayout(layout)
        return tab

    def create_ui_tab(self) -> QWidget:
        """Create UI settings tab"""
        tab = QWidget()
        layout = QVBoxLayout()

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

        # Connection settings group
        conn_group = QGroupBox("Connection Settings")
        conn_layout = QFormLayout()

        self.connection_timeout_spin = QSpinBox()
        self.connection_timeout_spin.setRange(5, 120)
        self.connection_timeout_spin.setValue(self.config.connection_timeout)
        conn_layout.addRow("Connection Timeout:", self.connection_timeout_spin)

        self.retry_attempts_spin = QSpinBox()
        self.retry_attempts_spin.setRange(1, 10)
        self.retry_attempts_spin.setValue(self.config.retry_attempts)
        conn_layout.addRow("Retry Attempts:", self.retry_attempts_spin)

        self.retry_delay_spin = QSpinBox()
        self.retry_delay_spin.setRange(1, 60)
        self.retry_delay_spin.setValue(self.config.retry_delay)
        conn_layout.addRow("Retry Delay (seconds):", self.retry_delay_spin)

        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)

        tab.setLayout(layout)
        return tab

    def initialize_ui_state(self):
        """Initialize UI state after all tabs are created"""
        # Update UI based on current settings
        self.on_gateway_mode_changed()
        self.on_auth_type_changed()

    def on_gateway_mode_changed(self):
        """Handle gateway mode checkbox change"""
        use_gateway = self.use_gateway_checkbox.isChecked()
        self.gateway_url_edit.setEnabled(use_gateway)
        self.gateway_auth_type_combo.setEnabled(use_gateway)
        self.jwt_token_edit.setEnabled(use_gateway)
        self.gateway_api_key_edit.setEnabled(use_gateway)
        self.gateway_username_edit.setEnabled(use_gateway)
        self.use_ssl_checkbox.setEnabled(use_gateway)
        self.validate_ssl_checkbox.setEnabled(use_gateway)

        # Enable/disable legacy fields
        self.server_url_edit.setEnabled(not use_gateway)
        self.api_key_edit.setEnabled(not use_gateway)

        self.on_auth_type_changed()

    def on_auth_type_changed(self):
        """Handle auth type change"""
        if not self.use_gateway_checkbox.isChecked():
            return

        auth_type = self.gateway_auth_type_combo.currentText()

        # Show/hide fields based on auth type
        if auth_type in ["google", "jwt"]:
            self.jwt_token_edit.setVisible(True)
            self.gateway_api_key_edit.setVisible(False)
            self.gateway_username_edit.setVisible(False)
        elif auth_type == "api_key":
            self.jwt_token_edit.setVisible(False)
            self.gateway_api_key_edit.setVisible(True)
            self.gateway_username_edit.setVisible(True)
        else:
            self.jwt_token_edit.setVisible(False)
            self.gateway_api_key_edit.setVisible(False)
            self.gateway_username_edit.setVisible(False)

    def test_connection(self):
        """Test connection to server"""
        try:
            # Create a temporary config for testing
            test_config = InventoryFetcherConfig()
            test_config.use_gateway = self.use_gateway_checkbox.isChecked()
            test_config.gateway_url = self.gateway_url_edit.text()
            test_config.gateway_auth_type = self.gateway_auth_type_combo.currentText()
            test_config.jwt_token = self.jwt_token_edit.text()
            test_config.gateway_api_key = self.gateway_api_key_edit.text()
            test_config.gateway_username = self.gateway_username_edit.text()
            test_config.use_ssl = self.use_ssl_checkbox.isChecked()
            test_config.validate_ssl_cert = self.validate_ssl_checkbox.isChecked()
            test_config.server_url = self.server_url_edit.text()
            test_config.api_key = self.api_key_edit.text()
            test_config.timeout = self.timeout_spin.value()

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
        self.config.use_gateway = self.use_gateway_checkbox.isChecked()
        self.config.gateway_url = self.gateway_url_edit.text()
        self.config.gateway_auth_type = self.gateway_auth_type_combo.currentText()
        self.config.jwt_token = self.jwt_token_edit.text()
        self.config.gateway_api_key = self.gateway_api_key_edit.text()
        self.config.gateway_username = self.gateway_username_edit.text()
        self.config.use_ssl = self.use_ssl_checkbox.isChecked()
        self.config.validate_ssl_cert = self.validate_ssl_checkbox.isChecked()

        # Legacy settings
        self.config.server_url = self.server_url_edit.text()
        self.config.api_key = self.api_key_edit.text()
        self.config.timeout = self.timeout_spin.value()

        # UI settings
        self.config.auto_fetch_on_startup = self.auto_fetch_checkbox.isChecked()
        self.config.show_notifications = self.show_notifications_checkbox.isChecked()

        # Connection settings
        self.config.connection_timeout = self.connection_timeout_spin.value()
        self.config.retry_attempts = self.retry_attempts_spin.value()
        self.config.retry_delay = self.retry_delay_spin.value()

        self.config.save_config()
        self.accept()
