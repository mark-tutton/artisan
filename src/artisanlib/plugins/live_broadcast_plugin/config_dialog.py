import sys
import logging
import os
import traceback
from typing import Optional, Dict, Any

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
        QDoubleSpinBox,
        QMessageBox,
        QTabWidget,
        QWidget,
        QTextEdit,
        QProgressBar,
    )
    from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, QMutex, QObject
    from PyQt6.QtGui import QFont, QIcon
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
        QDoubleSpinBox,
        QMessageBox,
        QTabWidget,
        QWidget,
        QTextEdit,
        QProgressBar,
    )
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, QMutex, QObject
    from PyQt5.QtGui import QFont, QIcon

from .config import LiveBroadcastConfig
from .websocket_client import SOCKETIO_AVAILABLE
from ..auth_manager import GlobalAuthManager

_log = logging.getLogger(__name__)

class LiveBroadcastConfigDialog(QDialog):
    # Signals
    config_saved = pyqtSignal()
    config_tested = pyqtSignal(bool, str)  # success, message


    def __init__(self, parent, config: LiveBroadcastConfig):
        super().__init__(parent)
        self.config = config
        self.auth_manager = GlobalAuthManager()
    
        self._ensure_config_loaded()
        
        self.test_in_progress = False
        self._config_mutex = QMutex()
        self.original_config = config.to_dict() if hasattr(config, 'to_dict') else {}
        
        self.setup_ui()
        self.connect_signals()
        self.update_auth_status()
        self.load_config()
        self.setup_validation()

    def _ensure_config_loaded(self):
        """Ensure the config is loaded from the saved file"""
        try:
            config_file = self.config.get_config_file()
            if os.path.exists(config_file):
                # Load the saved config
                self.config.load_from_file(config_file)
                _log.info(f"Config dialog loaded configuration from {config_file}")
            else:
                _log.info("No saved configuration found for config dialog")
        except Exception as e:
            _log.error(f"Failed to load configuration in dialog: {e}")

    def exec(self):
        """Execute the dialog (PyQt6 compatibility)"""
        try:
            # Try PyQt6 first
            return super().exec()
        except AttributeError:
            # Fallback to PyQt5
            return super().exec_()

    def setup_ui(self):
        try:
            self.setWindowTitle("Live Broadcast Configuration")
            self.setModal(True)
            self.resize(600, 700)

            # Set window icon if available
            try:
                self.setWindowIcon(QIcon(":/icons/broadcast.png"))
            except:
                pass

            # Create tab widget
            self.tab_widget = QTabWidget()

            # Create tabs
            self.setup_server_tab()
            self.setup_broadcasting_tab()
            self.setup_events_tab()
            self.setup_advanced_tab()

            # Add tabs to widget
            self.tab_widget.addTab(self.server_widget, "Server")
            self.tab_widget.addTab(self.broadcasting_widget, "Broadcasting")
            self.tab_widget.addTab(self.events_widget, "Events")
            self.tab_widget.addTab(self.advanced_widget, "Advanced")

            # Setup buttons
            self.setup_buttons()

            # Main layout 
            layout = QVBoxLayout()
            
            # Add auth status section
            auth_group = QGroupBox("Authentication Status")
            auth_layout = QVBoxLayout(auth_group)
            
            self.auth_status_label = QLabel("Not authenticated")
            self.auth_status_label.setStyleSheet("color: red; font-weight: bold;")
            auth_layout.addWidget(self.auth_status_label)
            
            self.login_button = QPushButton("Login")
            self.login_button.clicked.connect(self.show_login_dialog)
            auth_layout.addWidget(self.login_button)
            
            # Add auth group to main layout
            layout.addWidget(auth_group)
            
            # Add tab widget to main layout
            layout.addWidget(self.tab_widget)
            layout.addLayout(self.button_layout)
            self.setLayout(layout)

        except Exception as e:
            _log.error(f"Error setting up UI: {e}")
            self.show_error("Setup Error", f"Failed to setup configuration dialog: {e}")
            raise

    def connect_signals(self):
        # Connect to auth manager signals
        self.auth_manager.login_successful.connect(self.on_auth_success)
        self.auth_manager.login_failed.connect(self.on_auth_failed)
        self.auth_manager.token_refreshed.connect(self.on_token_refreshed)
        self.auth_manager.token_expired.connect(self.on_token_expired)

    def update_auth_status(self):
        """Update the authentication status display"""
        if self.auth_manager.is_authenticated():
            token_info = self.auth_manager.get_token_info()
            if token_info:
                expires_in = token_info.get('expires_in', 0)
                self.auth_status_label.setText(f"Authenticated (expires in {expires_in}s)")
                self.auth_status_label.setStyleSheet("color: green; font-weight: bold;")
                self.login_button.setText("Re-login")
            else:
                self.auth_status_label.setText("Authenticated")
                self.auth_status_label.setStyleSheet("color: green; font-weight: bold;")
                self.login_button.setText("Re-login")
        else:
            self.auth_status_label.setText("Not authenticated")
            self.auth_status_label.setStyleSheet("color: red; font-weight: bold;")
            self.login_button.setText("Login")

    def show_login_dialog(self):
        """Show the login dialog"""
        from ..auth_dialog import AuthDialog
        dialog = AuthDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.update_auth_status()

    def on_auth_success(self, access_token: str, refresh_token: str):
        """Handle successful authentication"""
        self.update_auth_status()

    def on_auth_failed(self, error: str):
        """Handle authentication failure"""
        self.update_auth_status()

    def on_token_refreshed(self, access_token: str, refresh_token: str):
        """Handle token refresh"""
        self.update_auth_status()

    def on_token_expired(self):
        """Handle token expiration"""
        self.update_auth_status()

    def setup_server_tab(self):
        """Setup server configuration tab"""
        try:
            self.server_widget = QWidget()
            layout = QVBoxLayout()

            # Server settings group
            server_group = QGroupBox("Server Settings")
            server_layout = QFormLayout()

            self.host_edit = QLineEdit()
            self.host_edit.setPlaceholderText("localhost")
            self.host_edit.setToolTip("Socket.IO server hostname or IP address")
            server_layout.addRow("Host:", self.host_edit)

            self.port_spin = QSpinBox()
            self.port_spin.setRange(1, 65535)
            self.port_spin.setValue(5100)
            self.port_spin.setToolTip("Socket.IO server port")
            server_layout.addRow("Port:", self.port_spin)

            self.path_edit = QLineEdit()
            self.path_edit.setPlaceholderText("/socket.io/")
            self.path_edit.setToolTip("Socket.IO server path")
            server_layout.addRow("Path:", self.path_edit)

            # Add roaster ID field
            self.roaster_id_edit = QLineEdit()
            self.roaster_id_edit.setPlaceholderText("Leave empty for auto-generated ID")
            self.roaster_id_edit.setToolTip("Custom roaster identifier (leave empty to auto-generate)")
            server_layout.addRow("Roaster ID:", self.roaster_id_edit)


            server_group.setLayout(server_layout)
            layout.addWidget(server_group)

            # Security and Authentication group
            security_group = QGroupBox("Security & Authentication")
            security_layout = QFormLayout()

            self.use_ssl_check = QCheckBox("Use SSL/TLS (WSS)")
            self.use_ssl_check.setToolTip("Enable secure WebSocket connection")
            security_layout.addRow(self.use_ssl_check)

            self.validate_ssl_check = QCheckBox("Validate SSL Certificate")
            self.validate_ssl_check.setToolTip("Validate server SSL certificate")
            self.validate_ssl_check.setChecked(True)
            security_layout.addRow(self.validate_ssl_check)

            self.enforce_secure_check = QCheckBox("Enforce Secure Connection")
            self.enforce_secure_check.setToolTip("Force secure connections in production")
            self.enforce_secure_check.setChecked(True)
            security_layout.addRow(self.enforce_secure_check)

            security_group.setLayout(security_layout)
            layout.addWidget(security_group)

            # Connection settings group
            conn_group = QGroupBox("Connection Settings")
            conn_layout = QFormLayout()

            self.reconnect_interval_spin = QDoubleSpinBox()
            self.reconnect_interval_spin.setRange(1.0, 60.0)
            self.reconnect_interval_spin.setSuffix(" seconds")
            self.reconnect_interval_spin.setToolTip("Time to wait between reconnection attempts")
            conn_layout.addRow("Reconnect Interval:", self.reconnect_interval_spin)

            self.max_reconnect_spin = QSpinBox()
            self.max_reconnect_spin.setRange(0, 100)
            self.max_reconnect_spin.setToolTip(
                "Maximum number of reconnection attempts (0 = unlimited)"
            )
            conn_layout.addRow("Max Reconnect Attempts:", self.max_reconnect_spin)

            self.heartbeat_interval_spin = QDoubleSpinBox()
            self.heartbeat_interval_spin.setRange(10.0, 300.0)
            self.heartbeat_interval_spin.setSuffix(" seconds")
            self.heartbeat_interval_spin.setToolTip("Interval for heartbeat messages")
            conn_layout.addRow("Heartbeat Interval:", self.heartbeat_interval_spin)

            self.connection_refresh_spin = QDoubleSpinBox()
            self.connection_refresh_spin.setRange(300.0, 7200.0)  # 5 min to 2 hours
            self.connection_refresh_spin.setValue(3600.0)
            self.connection_refresh_spin.setSuffix(" seconds")
            self.connection_refresh_spin.setToolTip("Interval to refresh JWT token and connection")
            conn_layout.addRow("Connection Refresh:", self.connection_refresh_spin)

            conn_group.setLayout(conn_layout)
            layout.addWidget(conn_group)

            # Test connection section
            test_group = QGroupBox("Test Connection")
            test_layout = QVBoxLayout()

            self.test_button = QPushButton("Test Connection")
            self.test_button.clicked.connect(self.test_connection)
            self.test_button.setToolTip("Test the WebSocket connection with current settings")
            test_layout.addWidget(self.test_button)

            self.test_progress = QProgressBar()
            self.test_progress.setVisible(False)
            test_layout.addWidget(self.test_progress)

            self.test_result_label = QLabel("")
            self.test_result_label.setWordWrap(True)
            test_layout.addWidget(self.test_result_label)

            test_group.setLayout(test_layout)
            layout.addWidget(test_group)

            # Socket.IO availability warning
            if not SOCKETIO_AVAILABLE:
                warning_label = QLabel("⚠️ socketio library not available")
                warning_label.setStyleSheet("color: red; font-weight: bold;")
                layout.addWidget(warning_label)

                install_label = QLabel("Install with: pip install python-socketio")
                install_label.setStyleSheet("color: gray;")
                layout.addWidget(install_label)

            layout.addStretch()
            self.server_widget.setLayout(layout)

        except Exception as e:
            _log.error(f"Error setting up server tab: {e}")
            raise

    def setup_broadcasting_tab(self):
        """Setup broadcasting configuration tab"""
        try:
            self.broadcasting_widget = QWidget()
            layout = QVBoxLayout()

            # Broadcasting settings group
            broadcast_group = QGroupBox("Broadcasting Settings")
            broadcast_layout = QFormLayout()

            self.auto_start_check = QCheckBox("Auto-start on plugin load")
            self.auto_start_check.setToolTip(
                "Automatically start broadcasting when the plugin loads"
            )
            broadcast_layout.addRow(self.auto_start_check)

            self.headless_mode_check = QCheckBox("Headless mode")
            self.headless_mode_check.setToolTip("Enable headless mode (no GUI dialogs)")
            broadcast_layout.addRow(self.headless_mode_check)

            self.broadcast_interval_spin = QDoubleSpinBox()
            self.broadcast_interval_spin.setRange(0.1, 10.0)
            self.broadcast_interval_spin.setSuffix(" seconds")
            self.broadcast_interval_spin.setToolTip("Interval between data broadcasts")
            broadcast_layout.addRow("Broadcast Interval:", self.broadcast_interval_spin)

            broadcast_group.setLayout(broadcast_layout)
            layout.addWidget(broadcast_group)

            # Data broadcasting group
            data_group = QGroupBox("Data Broadcasting")
            data_layout = QFormLayout()

            self.broadcast_temp_data_check = QCheckBox("Broadcast temperature data")
            data_layout.addRow(self.broadcast_temp_data_check)

            self.broadcast_ror_check = QCheckBox("Broadcast rate of rise")
            data_layout.addRow(self.broadcast_ror_check)

            self.broadcast_standard_events_check = QCheckBox("Broadcast standard events")
            data_layout.addRow(self.broadcast_standard_events_check)

            self.broadcast_custom_events_check = QCheckBox("Broadcast custom events")
            data_layout.addRow(self.broadcast_custom_events_check)

            data_group.setLayout(data_layout)
            layout.addWidget(data_group)

            # Performance settings group
            perf_group = QGroupBox("Performance Settings")
            perf_layout = QFormLayout()

            self.max_message_size_spin = QSpinBox()
            self.max_message_size_spin.setRange(1024, 10 * 1024 * 1024)  # 1KB to 10MB
            self.max_message_size_spin.setSuffix(" bytes")
            self.max_message_size_spin.setToolTip("Maximum size of individual messages")
            perf_layout.addRow("Max Message Size:", self.max_message_size_spin)

            self.message_queue_size_spin = QSpinBox()
            self.message_queue_size_spin.setRange(10, 10000)
            self.message_queue_size_spin.setToolTip("Maximum number of messages in queue")
            perf_layout.addRow("Message Queue Size:", self.message_queue_size_spin)

            perf_group.setLayout(perf_layout)
            layout.addWidget(perf_group)

            layout.addStretch()
            self.broadcasting_widget.setLayout(layout)

        except Exception as e:
            _log.error(f"Error setting up broadcasting tab: {e}")
            raise

    def setup_events_tab(self):
        """Setup events configuration tab"""
        try:
            self.events_widget = QWidget()
            layout = QVBoxLayout()

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

            # Event information
            info_group = QGroupBox("Event Information")
            info_layout = QVBoxLayout()

            info_text = QTextEdit()
            info_text.setReadOnly(True)
            info_text.setMaximumHeight(150)
            info_text.setPlainText(
                "Events are automatically detected and broadcast when they occur during roasting.\n\n"
                "• CHARGE: When beans are added to the roaster\n"
                "• DRY END: End of drying phase\n"
                "• FC START: Start of first crack\n"
                "• FC END: End of first crack\n"
                "• SC START: Start of second crack\n"
                "• SC END: End of second crack\n"
                "• DROP: When beans are dropped from the roaster\n"
                "• COOL END: End of cooling phase"
            )
            info_layout.addWidget(info_text)

            info_group.setLayout(info_layout)
            layout.addWidget(info_group)

            layout.addStretch()
            self.events_widget.setLayout(layout)

        except Exception as e:
            _log.error(f"Error setting up events tab: {e}")
            raise

    def setup_advanced_tab(self):
        """Setup advanced configuration tab"""
        try:
            self.advanced_widget = QWidget()
            layout = QVBoxLayout()

            logging_group = QGroupBox("Logging Settings")
            logging_layout = QFormLayout()

            self.enable_debug_logging_check = QCheckBox("Enable debug logging")
            self.enable_debug_logging_check.setToolTip("Enable detailed debug logging")
            logging_layout.addRow(self.enable_debug_logging_check)

            self.log_messages_check = QCheckBox("Log messages")
            self.log_messages_check.setToolTip("Log all sent and received messages")
            logging_layout.addRow(self.log_messages_check)

            logging_group.setLayout(logging_layout)
            layout.addWidget(logging_group)

            # Configuration management group
            config_group = QGroupBox("Configuration Management")
            config_layout = QVBoxLayout()

            reset_button = QPushButton("Reset to Defaults")
            reset_button.clicked.connect(self.reset_to_defaults)
            reset_button.setToolTip("Reset all settings to default values")
            config_layout.addWidget(reset_button)

            export_button = QPushButton("Export Configuration")
            export_button.clicked.connect(self.export_config)
            export_button.setToolTip("Export current configuration to file")
            config_layout.addWidget(export_button)

            import_button = QPushButton("Import Configuration")
            import_button.clicked.connect(self.import_config)
            import_button.setToolTip("Import configuration from file")
            config_layout.addWidget(import_button)

            config_group.setLayout(config_layout)
            layout.addWidget(config_group)

            # Configuration info
            info_group = QGroupBox("Configuration Information")
            info_layout = QVBoxLayout()

            self.config_info_text = QTextEdit()
            self.config_info_text.setReadOnly(True)
            self.config_info_text.setMaximumHeight(100)
            info_layout.addWidget(self.config_info_text)

            info_group.setLayout(info_layout)
            layout.addWidget(info_group)

            layout.addStretch()
            self.advanced_widget.setLayout(layout)

        except Exception as e:
            _log.error(f"Error setting up advanced tab: {e}")
            raise

    def setup_buttons(self):
        """Setup dialog buttons"""
        try:
            self.button_layout = QHBoxLayout()

            # Status label
            self.status_label = QLabel("")
            self.status_label.setStyleSheet("color: gray;")
            self.button_layout.addWidget(self.status_label)

            self.button_layout.addStretch()

            # Save button
            self.save_button = QPushButton("Save")
            self.save_button.clicked.connect(self.save_and_accept)
            self.save_button.setToolTip("Save configuration and close dialog")
            self.button_layout.addWidget(self.save_button)

            # OK button
            self.ok_button = QPushButton("OK")
            self.ok_button.clicked.connect(self.accept)
            self.ok_button.setToolTip("Save configuration and close dialog")
            self.button_layout.addWidget(self.ok_button)

            # Cancel button
            self.cancel_button = QPushButton("Cancel")
            self.cancel_button.clicked.connect(self.reject)
            self.cancel_button.setToolTip("Cancel changes and close dialog")
            self.button_layout.addWidget(self.cancel_button)

        except Exception as e:
            _log.error(f"Error setting up buttons: {e}")
            raise

    def setup_validation(self):
        """Setup input validation"""
        try:
            # Connect validation signals
            self.host_edit.textChanged.connect(self.validate_host)
            self.port_spin.valueChanged.connect(self.validate_port)
            self.path_edit.textChanged.connect(self.validate_path)

            # Setup validation timer
            self.validation_timer = QTimer()
            self.validation_timer.setSingleShot(True)
            self.validation_timer.timeout.connect(self.validate_all)

        except Exception as e:
            _log.error(f"Error setting up validation: {e}")

    def load_config(self):
        """Load configuration into UI with error handling"""
        self._config_mutex.lock()
        try:
            # Server settings
            self.host_edit.setText(self.config.server_host)
            self.port_spin.setValue(self.config.server_port)
            self.path_edit.setText(self.config.server_path)
            
            # Roaster ID
            self.roaster_id_edit.setText(self.config.roaster_id)


            # Security settings
            self.use_ssl_check.setChecked(self.config.use_ssl)
            self.validate_ssl_check.setChecked(self.config.validate_ssl_cert)
            self.enforce_secure_check.setChecked(self.config.enforce_secure_connection)

            # Connection settings
            self.reconnect_interval_spin.setValue(self.config.reconnect_interval)
            self.max_reconnect_spin.setValue(self.config.max_reconnect_attempts)
            self.heartbeat_interval_spin.setValue(self.config.heartbeat_interval)
            self.connection_refresh_spin.setValue(self.config.connection_refresh_interval)

            # Broadcasting settings
            self.auto_start_check.setChecked(self.config.auto_start)
            self.headless_mode_check.setChecked(self.config.headless_mode)
            self.broadcast_interval_spin.setValue(self.config.broadcast_interval)

            # Data broadcasting
            self.broadcast_temp_data_check.setChecked(self.config.broadcast_temperature_data)
            self.broadcast_ror_check.setChecked(self.config.broadcast_rate_of_rise)
            self.broadcast_standard_events_check.setChecked(self.config.broadcast_standard_events)
            self.broadcast_custom_events_check.setChecked(self.config.broadcast_custom_events)

            # Performance settings
            self.max_message_size_spin.setValue(self.config.max_message_size)
            self.message_queue_size_spin.setValue(self.config.message_queue_size)

            # Logging settings
            self.enable_debug_logging_check.setChecked(self.config.enable_debug_logging)
            self.log_messages_check.setChecked(self.config.log_messages)

            # Individual events
            events = self.config.include_events
            self.charge_check.setChecked(events.get("charge", True))
            self.dry_end_check.setChecked(events.get("dry_end", True))
            self.fc_start_check.setChecked(events.get("fc_start", True))
            self.fc_end_check.setChecked(events.get("fc_end", True))
            self.sc_start_check.setChecked(events.get("sc_start", True))
            self.sc_end_check.setChecked(events.get("sc_end", True))
            self.drop_check.setChecked(events.get("drop", True))
            self.cool_end_check.setChecked(events.get("cool_end", True))

            # Update configuration info
            self.update_config_info()

            _log.debug("Configuration loaded into UI")

        except Exception as e:
            _log.error(f"Error loading configuration: {e}")
            self.show_error("Load Error", f"Failed to load configuration: {e}")
        finally:
            self._config_mutex.unlock()

    def save_config(self):
        """Save UI configuration with validation"""
        self._config_mutex.lock()
        try:
            # Validate before saving
            if not self.validate_all():
                raise ValueError("Configuration validation failed")

            # Server settings
            self.config.server_host = self.host_edit.text().strip()
            self.config.server_port = self.port_spin.value()
            self.config.server_path = self.path_edit.text().strip()

            # Roaster ID
            self.config.roaster_id = self.roaster_id_edit.text().strip()

            # Security settings
            self.config.use_ssl = self.use_ssl_check.isChecked()
            self.config.validate_ssl_cert = self.validate_ssl_check.isChecked()
            self.config.enforce_secure_connection = self.enforce_secure_check.isChecked()

            # Connection settings
            self.config.reconnect_interval = self.reconnect_interval_spin.value()
            self.config.max_reconnect_attempts = self.max_reconnect_spin.value()
            self.config.heartbeat_interval = self.heartbeat_interval_spin.value()
            self.config.connection_refresh_interval = self.connection_refresh_spin.value()

            # Broadcasting settings
            self.config.auto_start = self.auto_start_check.isChecked()
            self.config.headless_mode = self.headless_mode_check.isChecked()
            self.config.broadcast_interval = self.broadcast_interval_spin.value()

            # Data broadcasting
            self.config.broadcast_temperature_data = self.broadcast_temp_data_check.isChecked()
            self.config.broadcast_rate_of_rise = self.broadcast_ror_check.isChecked()
            self.config.broadcast_standard_events = self.broadcast_standard_events_check.isChecked()
            self.config.broadcast_custom_events = self.broadcast_custom_events_check.isChecked()

            # Performance settings
            self.config.max_message_size = self.max_message_size_spin.value()
            self.config.message_queue_size = self.message_queue_size_spin.value()

            # Logging settings
            self.config.enable_debug_logging = self.enable_debug_logging_check.isChecked()
            self.config.log_messages = self.log_messages_check.isChecked()

            # Individual events
            self.config.include_events = {
                "charge": self.charge_check.isChecked(),
                "dry_end": self.dry_end_check.isChecked(),
                "fc_start": self.fc_start_check.isChecked(),
                "fc_end": self.fc_end_check.isChecked(),
                "sc_start": self.sc_start_check.isChecked(),
                "sc_end": self.sc_end_check.isChecked(),
                "drop": self.drop_check.isChecked(),
                "cool_end": self.cool_end_check.isChecked(),
            }

            _log.debug("Configuration saved from UI")

        except Exception as e:
            _log.error(f"Error saving configuration: {e}")
            raise
        finally:
            self._config_mutex.unlock()

    def validate_host(self) -> bool:
        """Validate host input"""
        try:
            host = self.host_edit.text().strip()
            if not host:
                self.show_field_error(self.host_edit, "Host cannot be empty")
                return False

            # Basic host validation
            if len(host) > 255:
                self.show_field_error(self.host_edit, "Host too long")
                return False

            self.clear_field_error(self.host_edit)
            return True

        except Exception as e:
            _log.error(f"Error validating host: {e}")
            return False

    def validate_port(self) -> bool:
        """Validate port input"""
        try:
            port = self.port_spin.value()
            if not (1 <= port <= 65535):
                self.show_field_error(self.port_spin, "Port must be between 1 and 65535")
                return False

            self.clear_field_error(self.port_spin)
            return True

        except Exception as e:
            _log.error(f"Error validating port: {e}")
            return False

    def validate_path(self) -> bool:
        """Validate path input"""
        try:
            path = self.path_edit.text().strip()
            if not path.startswith("/"):
                self.show_field_error(self.path_edit, "Path must start with '/'")
                return False

            self.clear_field_error(self.path_edit)
            return True

        except Exception as e:
            _log.error(f"Error validating path: {e}")
            return False

    def validate_all(self) -> bool:
        """Validate all configuration fields"""
        try:
            valid = True
            valid &= self.validate_host()
            valid &= self.validate_port()
            valid &= self.validate_path()

            # Update status
            if valid:
                self.status_label.setText("Configuration is valid")
                self.status_label.setStyleSheet("color: green;")
            else:
                self.status_label.setText("Configuration has errors")
                self.status_label.setStyleSheet("color: red;")

            return valid

        except Exception as e:
            _log.error(f"Error validating configuration: {e}")
            return False

    def show_field_error(self, widget, message: str):
        """Show error for a specific field"""
        try:
            widget.setStyleSheet("border: 2px solid red;")
            widget.setToolTip(f"Error: {message}")
        except Exception as e:
            _log.error(f"Error showing field error: {e}")

    def clear_field_error(self, widget):
        """Clear error for a specific field"""
        try:
            widget.setStyleSheet("")
            widget.setToolTip("")
        except Exception as e:
            _log.error(f"Error clearing field error: {e}")

    def save_and_accept(self):
        """Save configuration and accept dialog"""
        try:
            self.save_config()
            self.config.save_config()

            self.config_saved.emit()
            self.show_success("Configuration Saved", "Configuration has been saved successfully.")
            self.accept()

        except Exception as e:
            _log.error(f"Error saving configuration: {e}")
            self.show_error("Save Error", f"Failed to save configuration: {e}")

    def test_connection(self):
        """Test WebSocket connection with comprehensive error handling"""
        if not SOCKETIO_AVAILABLE:
            self.show_warning(
                "Test Connection",
                "socketio library not available. Install with: pip install python-socketio",
            )
            return

        if self.test_in_progress:
            return

        try:
            self.test_in_progress = True
            self.test_button.setEnabled(False)
            self.test_progress.setVisible(True)
            self.test_progress.setRange(0, 0)  # Indeterminate progress
            self.test_result_label.setText("Testing connection...")

            # Get current settings
            host = self.host_edit.text().strip()
            port = self.port_spin.value()
            path = self.path_edit.text().strip()

            if not host or not path:
                self.show_error("Test Connection", "Please enter valid host and path")
                return

            # Start test in background
            self._start_connection_test(host, port, path)

        except Exception as e:
            _log.error(f"Error starting connection test: {e}")
            self.show_error("Test Error", f"Failed to start connection test: {e}")
            self._reset_test_ui()

    def _start_connection_test(self, host: str, port: int, path: str):
        """Start connection test using QThread"""
        try:
            from .websocket_client import SocketIOBroadcaster
            import asyncio

            class ConnectionTestWorker(QObject):
                test_completed = pyqtSignal(bool, str)

                def __init__(self, host, port, path):
                    super().__init__()
                    self.host = host
                    self.port = port
                    self.path = path

                def run_test(self):
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        async def test():
                            try:
                                test_broadcaster = SocketIOBroadcaster(
                                    self.host, self.port, self.path
                                )
                                test_broadcaster.start()

                                # Wait for connection
                                await asyncio.sleep(2)

                                if test_broadcaster.is_connected():
                                    test_broadcaster.stop()
                                    return True, "Connection successful"
                                else:
                                    test_broadcaster.stop()
                                    return False, "Connection failed - no response from server"

                            except Exception as e:
                                return False, f"Connection failed: {str(e)}"

                        result, message = loop.run_until_complete(test())
                        loop.close()

                        # Emit result signal
                        self.test_completed.emit(result, message)

                    except Exception as e:
                        self.test_completed.emit(False, f"Test error: {str(e)}")

            # Create worker and thread
            self.test_worker = ConnectionTestWorker(host, port, path)
            self.test_thread = QThread()

            # Move worker to thread
            self.test_worker.moveToThread(self.test_thread)

            # Connect signals
            self.test_thread.started.connect(self.test_worker.run_test)
            self.test_worker.test_completed.connect(self._handle_test_result)
            self.test_worker.test_completed.connect(self.test_thread.quit)
            self.test_worker.test_completed.connect(self.test_worker.deleteLater)
            self.test_thread.finished.connect(self.test_thread.deleteLater)

            # Start thread
            self.test_thread.start()

        except Exception as e:
            _log.error(f"Error setting up connection test: {e}")
            self.config_tested.emit(False, f"Test setup error: {str(e)}")

    def _handle_test_result(self, success: bool, message: str):
        """Handle connection test result"""
        try:
            self._reset_test_ui()

            if success:
                self.show_success("Test Connection", message)
            else:
                self.show_warning("Test Connection", message)

        except Exception as e:
            _log.error(f"Error handling test result: {e}")

    def _reset_test_ui(self):
        """Reset test UI elements"""
        try:
            self.test_in_progress = False
            self.test_button.setEnabled(True)
            self.test_progress.setVisible(False)
        except Exception as e:
            _log.error(f"Error resetting test UI: {e}")

    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        try:
            reply = QMessageBox.question(
                self,
                "Reset Configuration",
                "Are you sure you want to reset all settings to default values?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.config.reset_to_defaults()
                self.load_config()
                self.show_success("Reset Complete", "Configuration has been reset to defaults.")

        except Exception as e:
            _log.error(f"Error resetting configuration: {e}")
            self.show_error("Reset Error", f"Failed to reset configuration: {e}")

    def export_config(self):
        """Export configuration to file"""
        try:
            from PyQt6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Configuration",
                f"live_broadcast_config_{int(time.time())}.json",
                "JSON Files (*.json)",
            )

            if file_path:
                self.save_config()
                self.config.save_config(file_path)
                self.show_success("Export Complete", f"Configuration exported to {file_path}")

        except Exception as e:
            _log.error(f"Error exporting configuration: {e}")
            self.show_error("Export Error", f"Failed to export configuration: {e}")

    def import_config(self):
        """Import configuration from file"""
        try:
            from PyQt6.QtWidgets import QFileDialog

            file_path, _ = QFileDialog.getOpenFileName(
                self, "Import Configuration", "", "JSON Files (*.json)"
            )

            if file_path:
                self.config.load_from_file(file_path)
                self.load_config()
                self.show_success("Import Complete", f"Configuration imported from {file_path}")

        except Exception as e:
            _log.error(f"Error importing configuration: {e}")
            self.show_error("Import Error", f"Failed to import configuration: {e}")

    def update_config_info(self):
        """Update configuration information display"""
        try:
            info = f"Configuration File: {self.config.get_config_file()}\n"
            info += f"Connection URL: {self.config.get_connection_url()}\n"
            info += f"Auto-start: {'Yes' if self.config.auto_start else 'No'}\n"
            info += f"Headless Mode: {'Yes' if self.config.headless_mode else 'No'}"

            self.config_info_text.setPlainText(info)

        except Exception as e:
            _log.error(f"Error updating config info: {e}")

    def show_success(self, title: str, message: str):
        """Show success message"""
        QMessageBox.information(self, title, message)

    def show_warning(self, title: str, message: str):
        """Show warning message"""
        QMessageBox.warning(self, title, message)

    def show_error(self, title: str, message: str):
        """Show error message"""
        QMessageBox.critical(self, title, message)

    def accept(self):
        """Handle OK button click"""
        try:
            self.save_config()
            super().accept()
        except Exception as e:
            _log.error(f"Error accepting dialog: {e}")
            self.show_error("Error", f"Failed to save configuration: {e}")

    def reject(self):
        """Handle Cancel button click"""
        try:
            # Restore original configuration
            for key, value in self.original_config.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)

            super().reject()

        except Exception as e:
            _log.error(f"Error rejecting dialog: {e}")
            super().reject()

    def closeEvent(self, event):
        """Handle dialog close event with thread cleanup"""
        try:
            if self.test_in_progress:
                reply = QMessageBox.question(
                    self,
                    "Close Dialog",
                    "A connection test is in progress. Do you want to cancel it and close?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )

                if reply == QMessageBox.StandardButton.Yes:
                    # Clean up test thread if running
                    if hasattr(self, "test_thread") and self.test_thread.isRunning():
                        self.test_thread.quit()
                        self.test_thread.wait(1000)  # Wait up to 1 second

                    self._reset_test_ui()
                    event.accept()
                else:
                    event.ignore()
            else:
                event.accept()

        except Exception as e:
            _log.error(f"Error handling close event: {e}")
            event.accept()