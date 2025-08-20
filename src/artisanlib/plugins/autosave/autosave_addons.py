import json
import logging
import time
import requests
from typing import Dict, Any, Optional, Tuple
from PyQt6.QtWidgets import (
    QCheckBox,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QApplication,
    QGroupBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from .config import AutosaveAddonConfig

_log = logging.getLogger(__name__)


class ServerHealthChecker(QObject):
    """Handles server health checking and connection management"""

    health_status_changed = pyqtSignal(bool)  # True if server is healthy
    connection_error = pyqtSignal(str)  

    def __init__(self, config: AutosaveAddonConfig):
        super().__init__()
        self.config = config
        self.is_healthy = False
        self.last_check = 0
        self.health_timer = QTimer()
        self.health_timer.timeout.connect(self._check_server_health)

        if config.autosave_health_check_enabled:
            self.health_timer.start(config.autosave_health_check_interval * 1000)

    def _check_server_health(self) -> None:
        """Check if the server is responsive"""
        try:
            response = requests.get(
                f"{self.config.autosave_server_url}/health",
                timeout=self.config.autosave_connection_timeout,
                headers=self._get_auth_headers(),
            )

            if response.status_code == 200:
                if not self.is_healthy:
                    self.is_healthy = True
                    self.health_status_changed.emit(True)
                    _log.info("Server health check passed")
            else:
                if self.is_healthy:
                    self.is_healthy = False
                    self.health_status_changed.emit(False)
                    _log.warning(f"Server health check failed: {response.status_code}")

        except requests.exceptions.RequestException as e:
            if self.is_healthy:
                self.is_healthy = False
                self.health_status_changed.emit(False)
                self.connection_error.emit(str(e))
                _log.error(f"Server health check error: {e}")

        self.last_check = time.time()

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers based on config"""
        headers = {"Content-Type": "application/json"}

        if self.config.autosave_auth_type == "api_token" and self.config.autosave_api_token:
            headers["X-API-Key"] = self.config.autosave_api_token
        elif self.config.autosave_auth_type == "jwt" and self.config.autosave_jwt_token:
            headers["Authorization"] = f"Bearer {self.config.autosave_jwt_token}"
        elif self.config.autosave_auth_type == "bearer" and self.config.autosave_jwt_token:
            headers["Authorization"] = f"Bearer {self.config.autosave_jwt_token}"

        return headers

    def upload_file(self, file_path: str, file_type: str) -> bool:
        """Upload a file to the server with retry logic"""
        if not self.is_healthy:
            _log.warning("Skipping upload - server is not healthy")
            return False

        for attempt in range(self.config.autosave_retry_attempts):
            try:
                with open(file_path, "rb") as f:
                    files = {"file": (file_path, f, "application/octet-stream")}
                    data = {"type": file_type}

                    response = requests.post(
                        # f"{self.config.autosave_server_url}/upload",
                        f"{self.config.autosave_server_url}",
                        files=files,
                        data=data,
                        timeout=self.config.autosave_connection_timeout,
                        headers=self._get_auth_headers(),
                    )

                    if response.status_code == 200:
                        _log.info(f"File uploaded successfully: {file_path}")
                        return True
                    else:
                        _log.warning(
                            f"Upload failed (attempt {attempt + 1}): {response.status_code}"
                        )

            except requests.exceptions.RequestException as e:
                _log.error(f"Upload error (attempt {attempt + 1}): {e}")

            if attempt < self.config.autosave_retry_attempts - 1:
                time.sleep(self.config.autosave_retry_delay)

        _log.error(
            f"File upload failed after {self.config.autosave_retry_attempts} attempts: {file_path}"
        )
        return False

    def stop(self) -> None:
        """Stop the health checker"""
        self.health_timer.stop()


# Global config and health checker instances
_config = AutosaveAddonConfig.load_from_file()
_health_checker = ServerHealthChecker(_config)


def get_config() -> AutosaveAddonConfig:
    """Get the current config instance"""
    return _config


def get_health_checker() -> ServerHealthChecker:
    """Get the health checker instance"""
    return _health_checker


def save_config() -> bool:
    """Save the current config to file"""
    return _config.save_to_file()


def get_server_upload_values(uploadToServerCheckbox, serverUrlEdit):
    """Get the values from server upload widgets"""
    return {
        "autosave_upload_to_server": uploadToServerCheckbox.isChecked(),
        "autosave_server_url": serverUrlEdit.text(),
    }


def get_format_values(autopdfcheckbox, imageTypesComboBox, pathEdit, format_number):
    """Get the values from format widgets"""
    return {
        f"autosave_pdf_{format_number}": autopdfcheckbox.isChecked(),
        f"autosave_image_type_{format_number}": imageTypesComboBox.currentText(),
        f"autosave_path_{format_number}": pathEdit.text(),
    }


def apply_format_values(aw, values, format_number):
    """Apply format values to qmc object"""
    for key, value in values.items():
        setattr(aw.qmc, key, value)


def apply_server_upload_values(aw, values):
    """Apply server upload values to qmc object"""
    for key, value in values.items():
        setattr(aw.qmc, key, value)


def create_server_upload_widgets(aw):
    """Create server upload widgets for autosave"""

    # Create main group box
    group_box = QGroupBox(QApplication.translate("GroupBox", "Server Upload Settings"))
    layout = QVBoxLayout()

    # Create the checkbox
    uploadToServerCheckbox = QCheckBox(
        QApplication.translate("CheckBox", "Upload to external server")
    )
    uploadToServerCheckbox.setChecked(_config.autosave_upload_to_server)

    # Create the server URL input
    serverUrlEdit = QLineEdit(_config.autosave_server_url)
    serverUrlEdit.setPlaceholderText("http://localhost:4000/upload")

    # Create authentication type selector
    authTypeLabel = QLabel(QApplication.translate("Label", "Authentication:"))
    authTypeCombo = QComboBox()
    authTypeCombo.addItems(["None", "API Token", "JWT Token", "Bearer Token"])

    # Set current auth type
    auth_type_map = {"none": 0, "api_token": 1, "jwt": 2, "bearer": 3}
    current_index = auth_type_map.get(_config.autosave_auth_type, 0)
    authTypeCombo.setCurrentIndex(current_index)

    # Create API token input
    apiTokenLabel = QLabel(QApplication.translate("Label", "API Token:"))
    apiTokenEdit = QLineEdit(_config.autosave_api_token)
    apiTokenEdit.setPlaceholderText("Enter your API token")
    apiTokenEdit.setEchoMode(QLineEdit.EchoMode.Password)

    # Create JWT token input
    jwtTokenLabel = QLabel(QApplication.translate("Label", "JWT Token:"))
    jwtTokenEdit = QLineEdit(_config.autosave_jwt_token)
    jwtTokenEdit.setPlaceholderText("Enter your JWT token")
    jwtTokenEdit.setEchoMode(QLineEdit.EchoMode.Password)

    # Create connection settings
    timeoutLabel = QLabel(QApplication.translate("Label", "Connection Timeout (seconds):"))
    timeoutEdit = QLineEdit(str(_config.autosave_connection_timeout))

    retryLabel = QLabel(QApplication.translate("Label", "Retry Attempts:"))
    retryEdit = QLineEdit(str(_config.autosave_retry_attempts))

    # Create server status indicator
    statusLabel = QLabel(QApplication.translate("Label", "Server Status:"))
    statusIndicator = QLabel("Unknown")
    statusIndicator.setStyleSheet("color: gray;")

    # Connect auth type changes to show/hide token fields
    def on_auth_type_changed(index):
        apiTokenLabel.setVisible(index == 1)  # API Token
        apiTokenEdit.setVisible(index == 1)
        jwtTokenLabel.setVisible(index in [2, 3])  # JWT or Bearer
        jwtTokenEdit.setVisible(index in [2, 3])

    authTypeCombo.currentIndexChanged.connect(on_auth_type_changed)
    on_auth_type_changed(current_index)  # Initial state

    # Connect health checker signals
    def on_health_status_changed(is_healthy):
        if is_healthy:
            statusIndicator.setText("Connected")
            statusIndicator.setStyleSheet("color: green;")
        else:
            statusIndicator.setText("Disconnected")
            statusIndicator.setStyleSheet("color: red;")

    _health_checker.health_status_changed.connect(on_health_status_changed)

    # Add widgets 
    layout.addWidget(uploadToServerCheckbox)
    layout.addWidget(QLabel(QApplication.translate("Label", "Server URL:")))
    layout.addWidget(serverUrlEdit)
    layout.addWidget(authTypeLabel)
    layout.addWidget(authTypeCombo)
    layout.addWidget(apiTokenLabel)
    layout.addWidget(apiTokenEdit)
    layout.addWidget(jwtTokenLabel)
    layout.addWidget(jwtTokenEdit)
    layout.addWidget(timeoutLabel)
    layout.addWidget(timeoutEdit)
    layout.addWidget(retryLabel)
    layout.addWidget(retryEdit)
    layout.addWidget(statusLabel)
    layout.addWidget(statusIndicator)

    group_box.setLayout(layout)

    # Store references 
    group_box.uploadToServerCheckbox = uploadToServerCheckbox
    group_box.serverUrlEdit = serverUrlEdit
    group_box.authTypeCombo = authTypeCombo
    group_box.apiTokenEdit = apiTokenEdit
    group_box.jwtTokenEdit = jwtTokenEdit
    group_box.timeoutEdit = timeoutEdit
    group_box.retryEdit = retryEdit
    group_box.statusIndicator = statusIndicator

    return group_box


def create_additional_format_widgets(aw, format_number):
    """Create additional format widgets for autosave (format 2, 3, etc.)"""

    # Get config values
    if format_number == 2:
        enabled = _config.autosave_pdf_2
        image_type = _config.autosave_image_type_2
        path = _config.autosave_path_2
    elif format_number == 3:
        enabled = _config.autosave_pdf_3
        image_type = _config.autosave_image_type_3
        path = _config.autosave_path_3
    else:
        enabled = False
        image_type = "PDF"
        path = ""

    # Create checkbox for this format
    autopdfcheckbox = QCheckBox(QApplication.translate("CheckBox", f"Auto-save as {format_number}"))
    autopdfcheckbox.setChecked(enabled)

    # Create label
    autopdflabel = QLabel(QApplication.translate("Label", f"Format {format_number}:"))

    # Create image types combo box
    imageTypesComboBox = QComboBox()
    imageTypesComboBox.addItems(["PDF", "PNG", "JPG", "SVG"])
    index = imageTypesComboBox.findText(image_type)
    if index >= 0:
        imageTypesComboBox.setCurrentIndex(index)

    # Create path button
    pathButton = QPushButton(QApplication.translate("Button", "Browse..."))

    # Create path edit
    pathEdit = QLineEdit(path)

    return autopdfcheckbox, autopdflabel, imageTypesComboBox, pathButton, pathEdit


def save_widget_values_to_config(
    uploadGroupBox,
    autopdfcheckbox2,
    imageTypesComboBox2,
    pathEdit2,
    autopdfcheckbox3,
    imageTypesComboBox3,
    pathEdit3,
):
    """Save widget values to config and persist to file"""

    # Update config with widget values
    _config.autosave_upload_to_server = uploadGroupBox.uploadToServerCheckbox.isChecked()
    _config.autosave_server_url = uploadGroupBox.serverUrlEdit.text()

    # Map auth type from combo box
    auth_type_map = {0: "none", 1: "api_token", 2: "jwt", 3: "bearer"}
    _config.autosave_auth_type = auth_type_map[uploadGroupBox.authTypeCombo.currentIndex()]

    _config.autosave_api_token = uploadGroupBox.apiTokenEdit.text()
    _config.autosave_jwt_token = uploadGroupBox.jwtTokenEdit.text()

    try:
        _config.autosave_connection_timeout = int(uploadGroupBox.timeoutEdit.text())
        _config.autosave_retry_attempts = int(uploadGroupBox.retryEdit.text())
    except ValueError:
        pass  # Keep default values if invalid

    if autopdfcheckbox2:
        _config.autosave_pdf_2 = autopdfcheckbox2.isChecked()
        _config.autosave_image_type_2 = imageTypesComboBox2.currentText()
        _config.autosave_path_2 = pathEdit2.text()

    if autopdfcheckbox3:
        _config.autosave_pdf_3 = autopdfcheckbox3.isChecked()
        _config.autosave_image_type_3 = imageTypesComboBox3.currentText()
        _config.autosave_path_3 = pathEdit3.text()

    # Save to file
    return save_config()


def load_config_to_qmc(aw):
    """Load config values into qmc object for backward compatibility"""
    qmc = aw.qmc

    # Set qmc attributes from config
    qmc.autosaveimage2 = _config.autosave_pdf_2
    qmc.autosaveimageformat2 = _config.autosave_image_type_2
    qmc.autosavealsopath2 = _config.autosave_path_2

    qmc.autosaveimage3 = _config.autosave_pdf_3
    qmc.autosaveimageformat3 = _config.autosave_image_type_3
    qmc.autosavealsopath3 = _config.autosave_path_3

    qmc.autosave_upload_to_server = _config.autosave_upload_to_server
    qmc.autosave_server_url = _config.autosave_server_url
    qmc.autosave_api_token = _config.autosave_api_token
    qmc.autosave_jwt_token = _config.autosave_jwt_token
    qmc.autosave_auth_type = _config.autosave_auth_type


def cleanup():
    """Cleanup resources when plugin is unloaded"""
    if _health_checker:
        _health_checker.stop()
