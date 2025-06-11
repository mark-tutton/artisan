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
from .websocket_client import WEBSOCKETS_AVAILABLE

class LiveBroadcastConfigDialog(QDialog):
    """Configuration dialog for live broadcast plugin"""
    
    def __init__(self, parent, config: LiveBroadcastConfig):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """Setup the user interface"""
        self.setWindowTitle("Live Broadcast Configuration")
        self.setModal(True)
        self.resize(500, 600)
        
        layout = QVBoxLayout()
        
        # Server settings group
        server_group = QGroupBox("Server Settings")
        server_layout = QFormLayout()
        
        self.host_edit = QLineEdit()
        self.host_edit.setPlaceholderText("localhost")
        server_layout.addRow("Host:", self.host_edit)
        
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(3001)
        server_layout.addRow("Port:", self.port_spin)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("/ws/roast")
        server_layout.addRow("Path:", self.path_edit)
        
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)
        
        # Connection settings group
        conn_group = QGroupBox("Connection Settings")
        conn_layout = QFormLayout()
        
        self.reconnect_interval_spin = QDoubleSpinBox()
        self.reconnect_interval_spin.setRange(1.0, 60.0)
        self.reconnect_interval_spin.setSuffix(" seconds")
        conn_layout.addRow("Reconnect Interval:", self.reconnect_interval_spin)
        
        self.max_reconnect_spin = QSpinBox()
        self.max_reconnect_spin.setRange(1, 100)
        conn_layout.addRow("Max Reconnect Attempts:", self.max_reconnect_spin)
        
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)
        
        # Broadcasting settings group
        broadcast_group = QGroupBox("Broadcasting Settings")
        broadcast_layout = QFormLayout()
        
        self.auto_start_check = QCheckBox("Auto-start on plugin load")
        broadcast_layout.addRow(self.auto_start_check)
        
        self.broadcast_interval_spin = QDoubleSpinBox()
        self.broadcast_interval_spin.setRange(0.1, 10.0)
        self.broadcast_interval_spin.setSuffix(" seconds")
        broadcast_layout.addRow("Broadcast Interval:", self.broadcast_interval_spin)
        
        broadcast_group.setLayout(broadcast_layout)
        layout.addWidget(broadcast_group)
        
        # Event broadcasting group
        event_group = QGroupBox("Event Broadcasting")
        event_layout = QFormLayout()
        
        self.broadcast_standard_events_check = QCheckBox("Broadcast standard events")
        event_layout.addRow(self.broadcast_standard_events_check)
        
        self.broadcast_custom_events_check = QCheckBox("Broadcast custom events")
        event_layout.addRow(self.broadcast_custom_events_check)
        
        self.broadcast_temp_data_check = QCheckBox("Broadcast temperature data")
        event_layout.addRow(self.broadcast_temp_data_check)
        
        self.broadcast_ror_check = QCheckBox("Broadcast rate of rise")
        event_layout.addRow(self.broadcast_ror_check)
        
        event_group.setLayout(event_layout)
        layout.addWidget(event_group)
        
        # Individual event settings
        individual_events_group = QGroupBox("Individual Event Settings")
        individual_layout = QFormLayout()
        
        self.charge_check = QCheckBox("CHARGE")
        individual_layout.addRow(self.charge_check)
        
        self.dry_end_check = QCheckBox("DRY END")
        individual_layout.addRow(self.dry_end_check)
        
        self.fc_start_check = QCheckBox("FC START")
        individual_layout.addRow(self.fc_start_check)
        
        self.fc_end_check = QCheckBox("FC END")
        individual_layout.addRow(self.fc_end_check)
        
        self.sc_start_check = QCheckBox("SC START")
        individual_layout.addRow(self.sc_start_check)
        
        self.sc_end_check = QCheckBox("SC END")
        individual_layout.addRow(self.sc_end_check)
        
        self.drop_check = QCheckBox("DROP")
        individual_layout.addRow(self.drop_check)
        
        self.cool_end_check = QCheckBox("COOL END")
        individual_layout.addRow(self.cool_end_check)
        
        individual_events_group.setLayout(individual_layout)
        layout.addWidget(individual_events_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        if not WEBSOCKETS_AVAILABLE:
            warning_label = QLabel("⚠️ websockets library not available")
            warning_label.setStyleSheet("color: red; font-weight: bold;")
            button_layout.addWidget(warning_label)
        
        button_layout.addStretch()
        
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_button)
        
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_and_write)
        button_layout.addWidget(self.save_button)

        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def load_config(self):
        """Load configuration into UI"""
        self.host_edit.setText(self.config.server_host)
        self.port_spin.setValue(self.config.server_port)
        self.path_edit.setText(self.config.server_path)
        
        self.reconnect_interval_spin.setValue(self.config.reconnect_interval)
        self.max_reconnect_spin.setValue(self.config.max_reconnect_attempts)
        
        self.auto_start_check.setChecked(self.config.auto_start)
        self.broadcast_interval_spin.setValue(self.config.broadcast_interval)
        
        self.broadcast_standard_events_check.setChecked(self.config.broadcast_standard_events)
        self.broadcast_custom_events_check.setChecked(self.config.broadcast_custom_events)
        self.broadcast_temp_data_check.setChecked(self.config.broadcast_temperature_data)
        self.broadcast_ror_check.setChecked(self.config.broadcast_rate_of_rise)
        
        # Individual events
        self.charge_check.setChecked(self.config.include_events.get('charge', True))
        self.dry_end_check.setChecked(self.config.include_events.get('dry_end', True))
        self.fc_start_check.setChecked(self.config.include_events.get('fc_start', True))
        self.fc_end_check.setChecked(self.config.include_events.get('fc_end', True))
        self.sc_start_check.setChecked(self.config.include_events.get('sc_start', True))
        self.sc_end_check.setChecked(self.config.include_events.get('sc_end', True))
        self.drop_check.setChecked(self.config.include_events.get('drop', True))
        self.cool_end_check.setChecked(self.config.include_events.get('cool_end', True))
    
    def save_config(self):
        """Save UI configuration"""
        self.config.server_host = self.host_edit.text()
        self.config.server_port = self.port_spin.value()
        self.config.server_path = self.path_edit.text()
        
        self.config.reconnect_interval = self.reconnect_interval_spin.value()
        self.config.max_reconnect_attempts = self.max_reconnect_spin.value()
        
        self.config.auto_start = self.auto_start_check.isChecked()
        self.config.broadcast_interval = self.broadcast_interval_spin.value()
        
        self.config.broadcast_standard_events = self.broadcast_standard_events_check.isChecked()
        self.config.broadcast_custom_events = self.broadcast_custom_events_check.isChecked()
        self.config.broadcast_temperature_data = self.broadcast_temp_data_check.isChecked()
        self.config.broadcast_rate_of_rise = self.broadcast_ror_check.isChecked()
        
        # Individual events
        self.config.include_events = {
            'charge': self.charge_check.isChecked(),
            'dry_end': self.dry_end_check.isChecked(),
            'fc_start': self.fc_start_check.isChecked(),
            'fc_end': self.fc_end_check.isChecked(),
            'sc_start': self.sc_start_check.isChecked(),
            'sc_end': self.sc_end_check.isChecked(),
            'drop': self.drop_check.isChecked(),
            'cool_end': self.cool_end_check.isChecked()
        }
    

    def save_and_accept(self):
        """Save configuration and accept dialog"""
        try:
            self.save_config()
            self.config.save_config()
            QMessageBox.information(self, "Configuration Saved", "Configuration has been saved successfully.")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save configuration: {e}")
    
    def save_and_write(self):
        """Save configuration and write to file"""
        try:
            self.save_config()
            self.config.save_config()
            QMessageBox.information(self, "Configuration Saved", "Configuration has been saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Failed to save configuration: {e}")


    def test_connection(self):
        """Test WebSocket connection"""
        if not WEBSOCKETS_AVAILABLE:
            QMessageBox.warning(self, "Test Connection", 
                              "websockets library not available. Install with: pip install websockets")
            return
        
        try:
            from .websocket_client import WebSocketBroadcaster
            
            host = self.host_edit.text()
            port = self.port_spin.value()
            path = self.path_edit.text()
            
            # Create temporary broadcaster for testing
            test_broadcaster = WebSocketBroadcaster(host, port, path)
            
            # Try to connect
            import asyncio
            import threading
            
            def test_connect():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    async def test():
                        try:
                            await test_broadcaster.connect()
                            await asyncio.sleep(1)
                            await test_broadcaster.disconnect()
                            return True
                        except Exception as e:
                            return str(e)
                    
                    result = loop.run_until_complete(test())
                    loop.close()
                    
                    if result is True:
                        QMessageBox.information(self, "Test Connection", 
                                              f"Successfully connected to {host}:{port}{path}")
                    else:
                        QMessageBox.warning(self, "Test Connection", 
                                          f"Connection failed: {result}")
                        
                except Exception as e:
                    QMessageBox.critical(self, "Test Connection", 
                                       f"Error testing connection: {e}")
            
            thread = threading.Thread(target=test_connect)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "Test Connection", 
                               f"Error setting up test: {e}")
    
    def accept(self):
        """Handle OK button click"""
        self.save_config()
        super().accept()