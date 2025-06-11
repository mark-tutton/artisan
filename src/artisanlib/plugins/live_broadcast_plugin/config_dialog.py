import sys
from typing import Optional

try:
    from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                                QLineEdit, QSpinBox, QCheckBox, QPushButton,
                                QLabel, QGroupBox, QDoubleSpinBox, QMessageBox)
    from PyQt6.QtCore import Qt
except ImportError:
    from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                                QLineEdit, QSpinBox, QCheckBox, QPushButton,
                                QLabel, QGroupBox, QDoubleSpinBox, QMessageBox)
    from PyQt5.QtCore import Qt

from .config import LiveBroadcastConfig
from .websocket_client import WebSocketBroadcaster

class ConfigDialog(QDialog):
    """Configuration dialog for live broadcast plugin"""
    
    def __init__(self, config: LiveBroadcastConfig, parent=None):
        super().__init__(parent)
        self.config = config
        
        self.setWindowTitle("Live Broadcast Configuration")
        self.setModal(True)
        self.resize(400, 350)
        
        self._setup_ui()
        self._load_config()
    
    def _setup_ui(self):
        """Setup the user interface"""
        layout = QVBoxLayout()
        
        # Server settings group
        server_group = QGroupBox("Server Settings")
        server_layout = QFormLayout()
        
        self.host_edit = QLineEdit()
        server_layout.addRow("Host:", self.host_edit)
        
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        server_layout.addRow("Port:", self.port_spin)
        
        self.path_edit = QLineEdit()
        server_layout.addRow("Path:", self.path_edit)
        
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)
        
        # Connection settings group
        conn_group = QGroupBox("Connection Settings")
        conn_layout = QFormLayout()
        
        self.auto_start_check = QCheckBox()
        conn_layout.addRow("Auto-start on launch:", self.auto_start_check)
        
        self.reconnect_spin = QDoubleSpinBox()
        self.reconnect_spin.setRange(1, 60)
        self.reconnect_spin.setSuffix(" seconds")
        conn_layout.addRow("Reconnect interval:", self.reconnect_spin)
        
        self.timeout_spin = QDoubleSpinBox()
        self.timeout_spin.setRange(1, 60)
        self.timeout_spin.setSuffix(" seconds")
        conn_layout.addRow("Connection timeout:", self.timeout_spin)
        
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # Data settings group
        data_group = QGroupBox("Data Settings")
        data_layout = QFormLayout()
        
        self.broadcast_spin = QDoubleSpinBox()
        self.broadcast_spin.setRange(0.1, 10)
        self.broadcast_spin.setSuffix(" seconds")
        data_layout.addRow("Broadcast interval:", self.broadcast_spin)
        
        self.history_check = QCheckBox()
        data_layout.addRow("Include full history:", self.history_check)
        
        self.max_history_spin = QSpinBox()
        self.max_history_spin.setRange(10, 1000)
        data_layout.addRow("Max history points:", self.max_history_spin)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        # Authentication group
        auth_group = QGroupBox("Authentication")
        auth_layout = QFormLayout()
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        auth_layout.addRow("API Key:", self.api_key_edit)
        
        auth_group.setLayout(auth_layout)
        layout.addWidget(auth_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self._test_connection)
        button_layout.addWidget(self.test_button)
        
        button_layout.addStretch()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def _load_config(self):
        """Load current configuration into UI"""
        self.host_edit.setText(self.config.server_host)
        self.port_spin.setValue(self.config.server_port)
        self.path_edit.setText(self.config.server_path)
        self.auto_start_check.setChecked(self.config.auto_start)
        self.reconnect_spin.setValue(self.config.reconnect_interval)
        self.timeout_spin.setValue(self.config.connection_timeout)
        self.broadcast_spin.setValue(self.config.broadcast_interval)
        self.history_check.setChecked(self.config.include_full_history)
        self.max_history_spin.setValue(self.config.max_history_points)
        self.api_key_edit.setText(self.config.api_key or "")
    
    def _save_config(self):
        """Save UI values to configuration"""
        self.config.server_host = self.host_edit.text()
        self.config.server_port = self.port_spin.value()
        self.config.server_path = self.path_edit.text()
        self.config.auto_start = self.auto_start_check.isChecked()
        self.config.reconnect_interval = self.reconnect_spin.value()
        self.config.connection_timeout = self.timeout_spin.value()
        self.config.broadcast_interval = self.broadcast_spin.value()
        self.config.include_full_history = self.history_check.isChecked()
        self.config.max_history_points = self.max_history_spin.value()
        
        api_key = self.api_key_edit.text().strip()
        self.config.api_key = api_key if api_key else None
        
        self.config.save_config()
    
    def _test_connection(self):
        """Test connection to the configured server"""
        try:
            # Create a temporary broadcaster for testing
            test_broadcaster = WebSocketBroadcaster(
                host=self.host_edit.text(),
                port=self.port_spin.value(),
                path=self.path_edit.text()
            )
            
            # Set up connection handlers
            connected = False
            error_msg = None
            
            def on_connect():
                nonlocal connected
                connected = True
            
            def on_disconnect():
                pass
            
            test_broadcaster.add_connection_handler(on_connect)
            test_broadcaster.add_disconnection_handler(on_disconnect)
            
            # Start the broadcaster
            test_broadcaster.start()
            
            # Wait a bit for connection
            import time
            time.sleep(2)
            
            # Check result
            if connected:
                QMessageBox.information(
                    self, 
                    "Connection Test", 
                    "Successfully connected to the server!"
                )
            else:
                QMessageBox.warning(
                    self, 
                    "Connection Test", 
                    "Failed to connect to the server.\n\n"
                    "Please check:\n"
                    "- Server is running\n"
                    "- Host and port are correct\n"
                    "- Network connectivity"
                )
            
            # Clean up
            test_broadcaster.stop()
            
        except Exception as e:
            QMessageBox.critical(
                self, 
                "Connection Test Error", 
                f"Error testing connection:\n{str(e)}"
            )
    
    def accept(self):
        """Save configuration and close dialog"""
        self._save_config()
        super().accept()