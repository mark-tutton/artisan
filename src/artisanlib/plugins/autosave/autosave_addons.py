import os
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

from ..base import PluginBase
from .config import AutosaveAddonConfig
from ..auth_manager import GlobalAuthManager

_log = logging.getLogger(__name__)

def _validate_url(url: str) -> str:
    """Makes sure URL has proper protocol prefix"""
    if not url.startswith(('http://', 'https://')):
        return f"http://{url}"
    return url


class ServerHealthChecker(QObject):
    """Handles server health checking and connection management"""

    health_status_changed = pyqtSignal(bool)
    connection_error = pyqtSignal(str)
    token_refresh_needed = pyqtSignal()  


    def __init__(self, config: AutosaveAddonConfig):
        QObject.__init__(self)
        
        
        self.config = config
         
        # Validate URLs
        self.config.autosave_server_url = _validate_url(self.config.autosave_server_url)
        self.config.autosave_health_url = _validate_url(self.config.autosave_health_url)
        

        self.is_healthy = False
        self.last_check = 0
        self.health_timer = QTimer()
        self.health_timer.timeout.connect(self._check_server_health)
        
        # Get global auth manager
        self.auth_manager = GlobalAuthManager()

        if config.autosave_health_check_enabled:
            self.health_timer.start(config.autosave_health_check_interval * 1000)

    @property
    def name(self) -> str:
        return "ServerHealthChecker"
    
    @property
    def version(self) -> str:
        return "1.0.0"

    def _check_server_health(self) -> None:
        """Check if the server is responsive"""
        try:
            health_url = self.config.autosave_health_url
            _log.debug(f"Checking server health at: {health_url}")

            response = requests.get(
                health_url,
                timeout=self.config.autosave_connection_timeout,
                headers=self._get_auth_headers(),
            )

            _log.debug(f"Health check response: {response.status_code}")
            
            # Handle 401 Unauthorized - token might be expired
            if response.status_code == 401:
                _log.warning("Health check returned 401 - token may be expired")
                if self.config.autosave_auto_refresh and self.auth_manager.current_token:
                    _log.info("Attempting automatic token refresh...")
                    if self.auth_manager.refresh_token():
                        _log.info("Token refreshed, retrying health check")
                        # Retry health check with new token
                        response = requests.get(
                            health_url,
                            timeout=self.config.autosave_connection_timeout,
                            headers=self._get_auth_headers(),
                        )
                    else:
                        _log.error("Token refresh failed")
                        self.token_refresh_needed.emit()
                        return
            
            if response.status_code == 200:
                _log.debug(f"Response content: {response.text[:200]}...")

                try:
                    health_data = response.json()
                    server_status = health_data.get("status", "unknown")

                    if server_status == "healthy":
                        if not self.is_healthy:
                            self.is_healthy = True
                            self.health_status_changed.emit(True)
                            _log.info("Server health check passed - server reports healthy")
                    else:
                        if self.is_healthy:
                            self.is_healthy = False
                            self.health_status_changed.emit(False)
                            _log.warning(f"Server reports unhealthy status: {server_status}")
                except (ValueError, KeyError) as e:
                    _log.warning(f"Could not parse health response: {e}")
                    if not self.is_healthy:
                        self.is_healthy = True
                        self.health_status_changed.emit(True)
                        _log.info("Server health check passed (status code only)")
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
        headers = {}

        # Use global auth manager if tokens are available
        token = self.auth_manager.get_valid_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
            return headers

        # Fallback to config-based auth
        if self.config.autosave_auth_type == "api_token" and self.config.autosave_api_token:
            headers["X-API-Key"] = self.config.autosave_api_token
        elif self.config.autosave_auth_type in ["jwt", "bearer"]:
            # Use config JWT token as fallback
            if self.config.autosave_jwt_token:
                headers["Authorization"] = f"Bearer {self.config.autosave_jwt_token}"

        return headers


    def _on_auth_success_impl(self, access_token: str, refresh_token: str):
        """Handle successful authentication"""
        self.logger.info("Authentication successful - updating autosave config")
        
        # Update autosave config with new tokens
        self.config.autosave_jwt_token = access_token
        self.config.autosave_refresh_token = refresh_token
        self.config.autosave_token_expires_at = int(time.time()) + 3600  # 1 hour
        
        # Save config
        self.config.save()
        
        # Update UI
        self._update_auth_status()
    
    def _on_token_refreshed_impl(self, access_token: str, refresh_token: str):
        """Handle token refresh"""
        self.logger.info("Token refreshed - updating autosave config")
        
        # Update config with new tokens
        self.config.autosave_jwt_token = access_token
        self.config.autosave_refresh_token = refresh_token
        self.config.autosave_token_expires_at = int(time.time()) + 3600
        
        # Save config
        self.config.save()
    
    def _on_token_expired_impl(self):
        """Handle token expiration"""
        self.logger.warning("Token expired - clearing autosave config")
        
        # Clear tokens from config
        self.config.autosave_jwt_token = ""
        self.config.autosave_refresh_token = ""
        self.config.autosave_token_expires_at = 0
        
        # Save config
        self.config.save()
        
        # Update UI
        self._update_auth_status()
    
    def _update_auth_status(self):
        """Update UI to reflect auth status"""
        if hasattr(self, 'config_dialog') and self.config_dialog:
            # Update config dialog if it's open
            if hasattr(self.config_dialog, 'auth_token_edit'):
                self.config_dialog.auth_token_edit.setText(self.config.autosave_jwt_token)
            if hasattr(self.config_dialog, 'refresh_token_edit'):
                self.config_dialog.refresh_token_edit.setText(self.config.autosave_refresh_token)
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API calls"""
        token = self.get_auth_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}
    
    def make_authenticated_request(self, url: str, method: str = "GET", **kwargs) -> Optional[requests.Response]:
        """Make an authenticated API request"""
        headers = self.get_auth_headers()
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers
        
        try:
            if method.upper() == "GET":
                return requests.get(url, **kwargs)
            elif method.upper() == "POST":
                return requests.post(url, **kwargs)
            elif method.upper() == "PUT":
                return requests.put(url, **kwargs)
            elif method.upper() == "DELETE":
                return requests.delete(url, **kwargs)
        except Exception as e:
            self.logger.error(f"Authenticated request failed: {e}")
            return None


    def upload_file(self, file_path: str, file_type: str) -> bool:
        """Upload a file to the server with retry logic and token refresh"""
        if not self.is_healthy:
            _log.warning("Skipping upload - server is not healthy")
            return False

        for attempt in range(self.config.autosave_retry_attempts):
            try:
                with open(file_path, "rb") as f:
                    files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
                    data = {
                        "type": file_type,
                        "filename": os.path.basename(file_path),
                        "timestamp": str(int(time.time())),
                    }

                    _log.info(f"Attempting upload {attempt + 1}: {file_path}")

                    headers = self._get_auth_headers()
                    if "Content-Type" in headers:
                        del headers["Content-Type"]

                    response = requests.post(
                        self.config.autosave_server_url,
                        files=files,
                        data=data,
                        timeout=self.config.autosave_connection_timeout,
                        headers=headers,
                    )

                    _log.info(f"Response status: {response.status_code}")

                    if response.status_code == 200:
                        _log.info(f"File uploaded successfully: {file_path}")
                        return True
                    elif response.status_code == 401:
                        _log.warning(f"Upload failed with 401 - token may be expired")
                        if self.config.autosave_auto_refresh and self.auth_manager.current_token:
                            _log.info("Attempting token refresh for upload...")
                            if self.auth_manager.refresh_token():
                                _log.info("Token refreshed, retrying upload")
                                continue  # Retry with new token
                            else:
                                _log.error("Token refresh failed during upload")
                                self.token_refresh_needed.emit()
                                return False
                        else:
                            _log.error("No refresh token available for upload")
                            return False
                    else:
                        _log.warning(f"Upload failed (attempt {attempt + 1}): {response.status_code}")
                        _log.warning(f"Response body: {response.text}")

            except requests.exceptions.RequestException as e:
                _log.error(f"Upload error (attempt {attempt + 1}): {e}")

            if attempt < self.config.autosave_retry_attempts - 1:
                time.sleep(self.config.autosave_retry_delay)

        _log.error(f"File upload failed after {self.config.autosave_retry_attempts} attempts: {file_path}")
        return False

    def get_auth_token(self) -> Optional[str]:
        """Get current valid auth token"""
        return self.auth_manager.get_valid_token()

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API calls"""
        token = self.get_auth_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

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


def get_server_upload_values(uploadToServerCheckbox, serverUrlEdit, serverHealthUrlEdit):
    """Get the values from server upload widgets"""
    return {
        "autosave_upload_to_server": uploadToServerCheckbox.isChecked(),
        "autosave_server_url": serverUrlEdit.text(),
        "autosave_health_url": serverHealthUrlEdit.text(),
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


def integrate_with_automaticsave(aw):
    """Integrate the plugin with the existing automaticsave method"""
    try:
        _log.info("AUTOSAVE PLUGIN DEBUG - Starting integration with automaticsave")
        
        health_checker = get_health_checker()
        _log.info(f"AUTOSAVE PLUGIN DEBUG - Health checker status: {health_checker.is_healthy}")
        _log.info(f"AUTOSAVE PLUGIN DEBUG - Server URL: {_config.autosave_server_url}")
        _log.info(f"AUTOSAVE PLUGIN DEBUG - Health URL: {_config.autosave_health_url}")
        _log.info(f"AUTOSAVE PLUGIN DEBUG - Upload enabled: {_config.autosave_upload_to_server}")

        def set_auth_tokens(access_token: str, refresh_token: str, expires_in: int):
            """Set authentication tokens (call this after login)"""
            health_checker.set_tokens(access_token, refresh_token, expires_in)
            _log.info("Authentication tokens set for autosave plugin")
        
        aw.set_autosave_auth_tokens = set_auth_tokens
        

        def enhanced_upload_to_server(filepath: str, server_url: str, extra_params: dict = None):
            """Enhanced upload method with health checking and retry logic"""
            _log.info(f"AUTOSAVE PLUGIN DEBUG - Enhanced upload called for: {filepath}")
            _log.info(f"AUTOSAVE PLUGIN DEBUG - Server URL: {server_url}")
            _log.info(f"AUTOSAVE PLUGIN DEBUG - Extra params: {extra_params}")
            _log.info(f"AUTOSAVE PLUGIN DEBUG - Health checker status: {health_checker.is_healthy}")
            
            if not health_checker.is_healthy:
                _log.warning(f"AUTOSAVE PLUGIN DEBUG - Skipping upload - server is not healthy: {filepath}")
                return None

            success = health_checker.upload_file(
                filepath, extra_params.get("format", "unknown") if extra_params else "unknown"
            )

            if success:
                _log.info(f"AUTOSAVE PLUGIN DEBUG - File uploaded successfully via plugin: {filepath}")
                return True
            else:
                _log.error(f"AUTOSAVE PLUGIN DEBUG - File upload failed via plugin: {filepath}")
                return None

        aw.upload_to_server = enhanced_upload_to_server
        _log.info("AUTOSAVE PLUGIN DEBUG - Plugin integrated with automaticsave method")

    except Exception as e:
        _log.error(f"AUTOSAVE PLUGIN DEBUG - Failed to integrate with automaticsave: {e}")

def should_upload_to_server(aw) -> bool:
    """Check if server upload is enabled and server is healthy"""
    try:
        upload_enabled = getattr(aw.qmc, "autosave_upload_to_server", False)
        _log.info(f"AUTOSAVE PLUGIN DEBUG - Upload enabled check: {upload_enabled}")
        
        if not upload_enabled:
            _log.info(f"AUTOSAVE PLUGIN DEBUG - Upload disabled in qmc")
            return False

        health_checker = get_health_checker()
        is_healthy = health_checker.is_healthy
        _log.info(f"AUTOSAVE PLUGIN DEBUG - Health checker status: {is_healthy}")
        
        return is_healthy

    except Exception as e:
        _log.error(f"AUTOSAVE PLUGIN DEBUG - Error checking upload status: {e}")
        return False


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
    serverUrlEdit.setPlaceholderText("http://localhost:5101/api/files/upload")

    # Create the server health URL input
    serverHealthUrlEdit = QLineEdit(_config.autosave_health_url)
    serverHealthUrlEdit.setPlaceholderText("http://localhost:5101/api/files/health")

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
    statusIndicator = QLabel("Checking...")
    statusIndicator.setStyleSheet("color: orange;")

    # Add token management section
    tokenGroupBox = QGroupBox(QApplication.translate("GroupBox", "JWT Token Management"))
    tokenLayout = QVBoxLayout()
    
    # Token status
    tokenStatusLabel = QLabel(QApplication.translate("Label", "Token Status:"))
    tokenStatusIndicator = QLabel("No token")
    tokenStatusIndicator.setStyleSheet("color: red;")
    
    # Token expiry info
    tokenExpiryLabel = QLabel(QApplication.translate("Label", "Expires:"))
    tokenExpiryInfo = QLabel("Unknown")
    
    # Auto-refresh checkbox
    autoRefreshCheckbox = QCheckBox(QApplication.translate("CheckBox", "Auto-refresh tokens"))
    autoRefreshCheckbox.setChecked(_config.autosave_auto_refresh)
    
    # Manual refresh button
    refreshTokenButton = QPushButton(QApplication.translate("Button", "🔄 Refresh Token"))
    
    # Clear tokens button
    clearTokensButton = QPushButton(QApplication.translate("Button", "🗑️ Clear Tokens"))
    
    tokenLayout.addWidget(tokenStatusLabel)
    tokenLayout.addWidget(tokenStatusIndicator)
    tokenLayout.addWidget(tokenExpiryLabel)
    tokenLayout.addWidget(tokenExpiryInfo)
    tokenLayout.addWidget(autoRefreshCheckbox)
    tokenLayout.addWidget(refreshTokenButton)
    tokenLayout.addWidget(clearTokensButton)
    
    tokenGroupBox.setLayout(tokenLayout)
    
    # Store references
    tokenGroupBox.tokenStatusIndicator = tokenStatusIndicator
    tokenGroupBox.tokenExpiryInfo = tokenExpiryInfo
    tokenGroupBox.autoRefreshCheckbox = autoRefreshCheckbox
    tokenGroupBox.refreshTokenButton = refreshTokenButton
    tokenGroupBox.clearTokensButton = clearTokensButton

    # Get the health checker and connect signals
    health_checker = get_health_checker()

    def update_token_status():
        """Update token status display"""
        if health_checker.auth_manager.current_token:
            if health_checker.auth_manager.is_token_expired():
                tokenStatusIndicator.setText("Expired")
                tokenStatusIndicator.setStyleSheet("color: red;")
            else:
                tokenStatusIndicator.setText("Valid")
                tokenStatusIndicator.setStyleSheet("color: green;")
            
            # Show expiry time
            expiry_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(health_checker.auth_manager.current_token.expires_at))
            tokenExpiryInfo.setText(expiry_time)
        else:
            tokenStatusIndicator.setText("No token")
            tokenStatusIndicator.setStyleSheet("color: red;")
            tokenExpiryInfo.setText("Unknown")

    def on_refresh_token_clicked():
        """Handle manual token refresh"""
        if health_checker.auth_manager.refresh_token():
            update_token_status()
            _log.info("Manual token refresh successful")
        else:
            _log.error("Manual token refresh failed")

    def on_clear_tokens_clicked():
        """Handle token clearing"""
        health_checker.auth_manager.clear_tokens()
        update_token_status()
        _log.info("Tokens cleared")

    def on_auto_refresh_changed(checked):
        """Handle auto-refresh setting change"""
        _config.autosave_auto_refresh = checked

    # Connect signals
    refreshTokenButton.clicked.connect(on_refresh_token_clicked)
    clearTokensButton.clicked.connect(on_clear_tokens_clicked)
    autoRefreshCheckbox.toggled.connect(on_auto_refresh_changed)
    
    # Connect token refresh needed signal
    def on_token_refresh_needed():
        update_token_status()
        _log.warning("Token refresh needed - please check authentication")

    health_checker.token_refresh_needed.connect(on_token_refresh_needed)


    # Connect auth type changes to show/hide token fields
    def on_auth_type_changed(index):
        apiTokenLabel.setVisible(index == 1)  # API Token
        apiTokenEdit.setVisible(index == 1)
        jwtTokenLabel.setVisible(index in [2, 3])  # JWT or Bearer
        jwtTokenEdit.setVisible(index in [2, 3])

    authTypeCombo.currentIndexChanged.connect(on_auth_type_changed)
    on_auth_type_changed(current_index)  # Initial state

    # Get the health checker and connect signals
    health_checker = get_health_checker()

    def on_health_status_changed(is_healthy):
        try:
            if statusIndicator and statusIndicator.parent() is not None:
                if is_healthy:
                    statusIndicator.setText("✅ Connected")
                    statusIndicator.setStyleSheet("color: green; font-weight: bold;")
                else:
                    statusIndicator.setText("❌ Disconnected")
                    statusIndicator.setStyleSheet("color: red; font-weight: bold;")
                _log.info(f"Server status updated: {'Connected' if is_healthy else 'Disconnected'}")
            else:
                _log.debug("Status indicator widget no longer exists, skipping update")
        except RuntimeError as e:
            _log.debug(f"Status indicator widget was destroyed: {e}")

    def on_connection_error(error_msg):
        try:
            if statusIndicator and statusIndicator.parent() is not None:
                statusIndicator.setText(f"Error: {error_msg[:30]}...")
                statusIndicator.setStyleSheet("color: red; font-weight: bold;")
                _log.error(f"Connection error: {error_msg}")
            else:
                _log.debug("Status indicator widget no longer exists, skipping error update")
        except RuntimeError as e:
            _log.debug(f"Status indicator widget was destroyed: {e}")

    # Connect the signals
    health_checker.health_status_changed.connect(on_health_status_changed)
    health_checker.connection_error.connect(on_connection_error)

    # Trigger an immediate health check
    def trigger_health_check():
        _log.info("🔍 Triggering immediate health check...")
        health_checker._check_server_health()

    # Add refresh button for manual health check
    refreshButton = QPushButton(QApplication.translate("Button", "🔄 Check Server"))
    refreshButton.clicked.connect(trigger_health_check)

    # Add widgets
    layout.addWidget(uploadToServerCheckbox)
    layout.addWidget(QLabel(QApplication.translate("Label", "Server URL:")))
    layout.addWidget(serverUrlEdit)
    layout.addWidget(QLabel(QApplication.translate("Label", "Server Health URL:")))
    layout.addWidget(serverHealthUrlEdit)
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
    layout.addWidget(refreshButton)

    group_box.setLayout(layout)

    # Store references
    group_box.uploadToServerCheckbox = uploadToServerCheckbox
    group_box.serverUrlEdit = serverUrlEdit
    group_box.serverHealthUrlEdit = serverHealthUrlEdit
    group_box.authTypeCombo = authTypeCombo
    group_box.apiTokenEdit = apiTokenEdit
    group_box.jwtTokenEdit = jwtTokenEdit
    group_box.timeoutEdit = timeoutEdit
    group_box.retryEdit = retryEdit
    group_box.statusIndicator = statusIndicator
    group_box.refreshButton = refreshButton

    def cleanup_connections():
        try:
            health_checker.health_status_changed.disconnect(on_health_status_changed)
            health_checker.connection_error.disconnect(on_connection_error)
            _log.debug("Disconnected health checker signals")
        except Exception as e:
            _log.debug(f"Error disconnecting signals: {e}")

    group_box.destroyed.connect(cleanup_connections)

    # Trigger initial health check after a short delay
    QTimer.singleShot(1000, trigger_health_check)

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
    imageTypesComboBox.addItems(["PDF", "PDF Report", "PNG", "JPG", "SVG", "CSV", "JSON"])
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
    _config.autosave_health_url = uploadGroupBox.serverHealthUrlEdit.text()

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
    qmc.autosave_health_url = _config.autosave_health_url
    qmc.autosave_api_token = _config.autosave_api_token
    qmc.autosave_jwt_token = _config.autosave_jwt_token
    qmc.autosave_auth_type = _config.autosave_auth_type


def cleanup():
    """Cleanup resources when plugin is unloaded"""
    if _health_checker:
        _health_checker.stop()