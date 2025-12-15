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
from ..auth_dialog import AuthDialog

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
        self.health_timer = QTimer(self)
        self.health_timer.timeout.connect(self._check_server_health)
        
        self._auth_manager = None

    @property
    def auth_manager(self):
        """Lazy initialization of GlobalAuthManager"""
        if self._auth_manager is None:
            from ..auth_manager import get_auth_manager
            self._auth_manager = get_auth_manager()
        return self._auth_manager

    def start(self) -> None:
        """Start the health checker timer"""
        if self.config.autosave_health_check_enabled:
            self.health_timer.start(self.config.autosave_health_check_interval * 1000)
            _log.info("Health checker timer started")

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
            if not health_url:
                _log.warning("Health URL not configured, skipping health check")
                return

            _log.debug(f"Checking server health at: {health_url}")

    
            headers = {}
            try:
                if self._auth_manager is None:
                    # Try to get auth manager
                    auth_mgr = self.auth_manager
                    if auth_mgr is None:
                        _log.debug("Auth manager not available, checking server without auth")
                    else:
                        headers = auth_mgr.get_auth_headers()
                else:
                    headers = self.auth_manager.get_auth_headers()
            except Exception as e:
                _log.warning(f"Could not get auth headers for health check: {e}")

            response = requests.get(
                health_url,
                timeout=self.config.autosave_connection_timeout,
                headers=headers,
            )

            _log.debug(f"Health check response: {response.status_code}")
            
            # Handle 401 Unauthorized - token might be expired
            if response.status_code == 401:
                _log.warning("Health check returned 401 - authentication may be expired")
                try:
                    if self._auth_manager and self.auth_manager.auth_method == "oauth":
                        if self.config.autosave_auto_refresh:
                            _log.info("Attempting automatic token refresh...")
                            if self.auth_manager.refresh_token():
                                _log.info("Token refreshed, retrying health check")
                                # Retry health check with new token
                                headers = self.auth_manager.get_auth_headers()
                                response = requests.get(
                                    health_url,
                                    timeout=self.config.autosave_connection_timeout,
                                    headers=headers,
                                )
                            else:
                                _log.error("Token refresh failed")
                                self.token_refresh_needed.emit()
                                self.is_healthy = False
                                self.health_status_changed.emit(False)
                                return
                    else:
                        # API key auth - can't refresh, just report error
                        _log.error("API key authentication failed")
                        self.token_refresh_needed.emit()
                        self.is_healthy = False
                        self.health_status_changed.emit(False)
                        return
                except Exception as e:
                    _log.warning(f"Error during token refresh: {e}")
                    self.token_refresh_needed.emit()
                    self.is_healthy = False
                    self.health_status_changed.emit(False)
                    return
            
            if response.status_code == 200:
                _log.debug(f"Response content: {response.text[:200]}...")

                try:
                    health_data = response.json()
                    server_status = health_data.get("status", "unknown")

                    if server_status == "healthy":
                        was_healthy = self.is_healthy
                        self.is_healthy = True
                        if not was_healthy:
                            self.health_status_changed.emit(True)
                        else:
                            self.health_status_changed.emit(True)
                        _log.info("Server health check passed - server reports healthy")
                    else:
                        was_healthy = self.is_healthy
                        self.is_healthy = False
                        if was_healthy:
                            self.health_status_changed.emit(False)
                        else:
                            self.health_status_changed.emit(False)
                        _log.warning(f"Server reports unhealthy status: {server_status}")
                except (ValueError, KeyError) as e:
                    _log.warning(f"Could not parse health response: {e}")
                    was_healthy = self.is_healthy
                    self.is_healthy = True
                    if not was_healthy:
                        self.health_status_changed.emit(True)
                    else:
                        self.health_status_changed.emit(True)
                    _log.info("Server health check passed (status code only)")
            else:
                was_healthy = self.is_healthy
                self.is_healthy = False
                if was_healthy:
                    self.health_status_changed.emit(False)
                else:
                    self.health_status_changed.emit(False)
                _log.warning(f"Server health check failed: {response.status_code}")

        except requests.exceptions.RequestException as e:
            was_healthy = self.is_healthy
            self.is_healthy = False
            if was_healthy:
                self.health_status_changed.emit(False)
            else:
                self.health_status_changed.emit(False)
            self.connection_error.emit(str(e))
            _log.error(f"Server health check error: {e}")

        self.last_check = time.time()

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers using global auth manager"""
        return self.auth_manager.get_auth_headers()

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

                    headers = self.auth_manager.get_auth_headers()
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
                        _log.warning(f"Upload failed with 401 - authentication may be expired")
                        if self.auth_manager.auth_method == "oauth":
                            if self.config.autosave_auto_refresh:
                                _log.info("Attempting token refresh for upload...")
                                if self.auth_manager.refresh_token():
                                    _log.info("Token refreshed, retrying upload")
                                    continue  # Retry with new token
                                else:
                                    _log.error("Token refresh failed during upload")
                                    self.token_refresh_needed.emit()
                                    return False
                        else:
                            # API key auth - can't refresh
                            _log.error("API key authentication failed")
                            self.token_refresh_needed.emit()
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
        return self.auth_manager.get_auth_headers()

    def stop(self) -> None:
        """Stop the health checker"""
        self.health_timer.stop()

# Global config and health checker instances
_config = AutosaveAddonConfig.load_from_file()
_health_checker = None # ServerHealthChecker(_config)


def get_config() -> AutosaveAddonConfig:
    """Get the current config instance"""
    return _config


def get_health_checker() -> ServerHealthChecker:
    """Get the health checker instance (lazy initialization)"""
    global _health_checker
    if _health_checker is None:
        _health_checker = ServerHealthChecker(_config)
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

        def enhanced_upload_to_server(filepath: str, server_url: str, extra_params: dict = None):
            """Enhanced upload method with health checking and retry logic - runs in background thread"""
            _log.info(f"AUTOSAVE PLUGIN DEBUG - Enhanced upload called for: {filepath}")
            _log.info(f"AUTOSAVE PLUGIN DEBUG - Server URL: {server_url}")
            _log.info(f"AUTOSAVE PLUGIN DEBUG - Extra params: {extra_params}")
            _log.info(f"AUTOSAVE PLUGIN DEBUG - Health checker status: {health_checker.is_healthy}")
            
            if not health_checker.is_healthy:
                _log.warning(f"AUTOSAVE PLUGIN DEBUG - Skipping upload - server is not healthy: {filepath}")
                return None

            # Run upload in background thread to avoid blocking UI
            import threading
            
            def do_upload():
                """Perform upload in background thread"""
                try:
                    success = health_checker.upload_file(
                        filepath, extra_params.get("format", "unknown") if extra_params else "unknown"
                    )
                    
                    if success:
                        _log.info(f"AUTOSAVE PLUGIN DEBUG - File uploaded successfully via plugin: {filepath}")
                        from PyQt6.QtCore import QTimer
                        def update_ui_success():
                            if hasattr(aw, "addmessage"):
                                aw.addmessage(f"Uploaded {filepath} to server.")
                        QTimer.singleShot(0, update_ui_success)
                    else:
                        _log.error(f"AUTOSAVE PLUGIN DEBUG - File upload failed via plugin: {filepath}")
                        from PyQt6.QtCore import QTimer
                        def update_ui_failure():
                            if hasattr(aw, "addmessage"):
                                aw.addmessage(f"Upload failed: {filepath}")
                        QTimer.singleShot(0, update_ui_failure)
                except Exception as e:
                    _log.error(f"AUTOSAVE PLUGIN DEBUG - Upload error: {e}", exc_info=True)
                    from PyQt6.QtCore import QTimer
                    def update_ui_error():
                        if hasattr(aw, "addmessage"):
                            aw.addmessage(f"Upload error: {e}")
                    QTimer.singleShot(0, update_ui_error)
            
            thread = threading.Thread(target=do_upload, daemon=True)
            thread.start()
            
            return True
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

    # Authentication section - use global auth manager
    authLabel = QLabel(QApplication.translate("Label", "Authentication:"))
    authStatusLabel = QLabel("Checking...")
    authStatusLabel.setStyleSheet("color: orange;")
    
    # Button to open auth dialog
    authButton = QPushButton(QApplication.translate("Button", "🔐 Authenticate"))
    
    def on_auth_button_clicked():
        """Open global authentication dialog"""
        try:
            from ..auth_manager import get_auth_manager
            auth_manager = get_auth_manager()
            if auth_manager is None:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(None, "Authentication Error", 
                                  "Authentication system is not available. Please ensure the application is fully loaded.")
                return
            
            dialog = AuthDialog()
            if dialog.exec():
                update_auth_status()
                _log.info("Authentication successful")
            else:
                update_auth_status()
        except Exception as e:
            _log.error(f"Failed to get GlobalAuthManager or show auth dialog: {e}", exc_info=True)
            import traceback
            _log.error(traceback.format_exc())
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(None, "Authentication Error", 
                              f"Failed to open authentication dialog: {e}")
          
    authButton.clicked.connect(on_auth_button_clicked)
    
    def update_auth_status():
        """Update authentication status display"""
        try: 
            from ..auth_manager import get_auth_manager
            auth_manager = get_auth_manager()
            if auth_manager is None:
                authStatusLabel.setText("❌ Authentication unavailable")
                authStatusLabel.setStyleSheet("color: orange;")
                return
            
            if auth_manager.is_authenticated():
                token_info = auth_manager.get_token_info()
                if token_info:
                    auth_method = token_info.get('auth_method', 'unknown')
                    if auth_method == 'api_key':
                        authStatusLabel.setText(f"✅ Authenticated (API Key)")
                    elif auth_method == 'oauth':
                        if token_info.get('is_expired', False):
                            authStatusLabel.setText("⚠️ Token Expired")
                            authStatusLabel.setStyleSheet("color: orange;")
                        else:
                            expires_in = token_info.get('expires_in', 0)
                            hours = expires_in // 3600
                            minutes = (expires_in % 3600) // 60
                            authStatusLabel.setText(f"✅ Authenticated (OAuth - expires in {hours}h {minutes}m)")
                            authStatusLabel.setStyleSheet("color: green;")
                    else:
                        authStatusLabel.setText("✅ Authenticated")
                        authStatusLabel.setStyleSheet("color: green;")
                else:
                    authStatusLabel.setText("✅ Authenticated")
                    authStatusLabel.setStyleSheet("color: green;")
            else:
                authStatusLabel.setText("❌ Not authenticated")
                authStatusLabel.setStyleSheet("color: red;")
        except Exception as e:
            _log.error(f"Failed to update auth status: {e}", exc_info=True)
            import traceback
            _log.error(traceback.format_exc())
            try:
                authStatusLabel.setText("❌ Authentication unavailable")
                authStatusLabel.setStyleSheet("color: orange;")
            except:
                pass  # Widget might not exist yet
    
    from PyQt6.QtCore import QTimer
    def delayed_update_auth_status():
        try:
            update_auth_status()
        except Exception as e:
            _log.error(f"Failed to update auth status in delayed callback: {e}", exc_info=True)
    
    QTimer.singleShot(100, delayed_update_auth_status)
    
    def connect_auth_signals():
        """Connect auth manager signals - called lazily when needed"""
        try:
            auth_manager = GlobalAuthManager()
            auth_manager.login_successful.connect(update_auth_status)
            auth_manager.login_failed.connect(update_auth_status)
            auth_manager.token_refreshed.connect(update_auth_status)
            auth_manager.token_expired.connect(update_auth_status)
            return auth_manager
        except Exception as e:
            _log.warning(f"Failed to connect auth signals (QApplication may not be ready): {e}")
            return None

    _auth_manager_connector = connect_auth_signals
    
    try:
        auth_manager = connect_auth_signals()
        if auth_manager is None:
            _log.debug("Auth signal connection deferred - will retry when dialog is shown")
    except Exception as e:
        _log.debug(f"Auth signal connection deferred due to: {e}")

    # Create connection settings
    timeoutLabel = QLabel(QApplication.translate("Label", "Connection Timeout (seconds):"))
    timeoutEdit = QLineEdit(str(_config.autosave_connection_timeout))

    retryLabel = QLabel(QApplication.translate("Label", "Retry Attempts:"))
    retryEdit = QLineEdit(str(_config.autosave_retry_attempts))

    # Create server status indicator
    statusLabel = QLabel(QApplication.translate("Label", "Server Status:"))
    statusIndicator = QLabel("Checking...")
    statusIndicator.setStyleSheet("color: orange;")

    # Add token management section (for OAuth tokens only)
    tokenGroupBox = QGroupBox(QApplication.translate("GroupBox", "Token Management"))
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
    
    # Manual refresh button (only for OAuth)
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
        try: 
            auth_manager = GlobalAuthManager()
            token_info = auth_manager.get_token_info()
            
            if token_info:
                auth_method = token_info.get('auth_method', 'unknown')
                
                if auth_method == 'api_key':
                    tokenStatusIndicator.setText("API Key (no expiry)")
                    tokenStatusIndicator.setStyleSheet("color: green;")
                    tokenExpiryInfo.setText("N/A")
                    refreshTokenButton.setEnabled(False)  # Can't refresh API keys
                elif auth_method == 'oauth':
                    if token_info.get('is_expired', False):
                        tokenStatusIndicator.setText("Expired")
                        tokenStatusIndicator.setStyleSheet("color: red;")
                        refreshTokenButton.setEnabled(True)
                    else:
                        tokenStatusIndicator.setText("Valid")
                        tokenStatusIndicator.setStyleSheet("color: green;")
                        refreshTokenButton.setEnabled(True)
                    
                    # Show expiry time for OAuth tokens
                    expires_at = token_info.get('expires_at')
                    if expires_at:
                        expiry_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expires_at))
                        tokenExpiryInfo.setText(expiry_time)
                    else:
                        tokenExpiryInfo.setText("Unknown")
                else:
                    tokenStatusIndicator.setText("Unknown")
                    tokenStatusIndicator.setStyleSheet("color: orange;")
                    tokenExpiryInfo.setText("Unknown")
                    refreshTokenButton.setEnabled(False)
            else:
                tokenStatusIndicator.setText("No token")
                tokenStatusIndicator.setStyleSheet("color: red;")
                tokenExpiryInfo.setText("Unknown")
                refreshTokenButton.setEnabled(False)
        except Exception as e:
            _log.error(f"Failed to create or access GlobalAuthManager in update_token_status: {e}", exc_info=True)
            import traceback
            _log.error(traceback.format_exc())
            # Set safe defaults
            try:
                tokenStatusIndicator.setText("❌ Unavailable")
                tokenExpiryLabel.setText("")
            except:
                pass  # Widgets might not exist yet

    def on_refresh_token_clicked():
        """Handle manual token refresh (OAuth only)"""
        auth_manager = GlobalAuthManager()
        if auth_manager.auth_method == "oauth":
            if auth_manager.refresh_token():
                update_token_status()
                update_auth_status()
                _log.info("Manual token refresh successful")
            else:
                _log.error("Manual token refresh failed")
        else:
            _log.warning("Token refresh only available for OAuth tokens")

    def on_clear_tokens_clicked():
        """Handle token clearing"""
        auth_manager = GlobalAuthManager()
        auth_manager.clear_tokens()
        update_token_status()
        update_auth_status()
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
        update_auth_status()
        _log.warning("Token refresh needed - please check authentication")

    health_checker.token_refresh_needed.connect(on_token_refresh_needed)

    def on_health_status_changed(is_healthy):
        try:
            if statusIndicator and statusIndicator.parent() is not None:
                if is_healthy:
                    statusLabel.setText("Server Status: Connected")
                    statusIndicator.setText("✅ Connected")
                    statusIndicator.setStyleSheet("color: green; font-weight: bold;")
                else:
                    statusLabel.setText("Server Status: Disconnected")
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
                statusLabel.setText(f"Server Status: Error - {error_msg[:30]}...")
                statusIndicator.setText(f"Error: {error_msg[:30]}...")
                statusIndicator.setStyleSheet("color: red; font-weight: bold;")
                _log.error(f"Connection error: {error_msg}")
            else:
                _log.debug("Status indicator widget no longer exists, skipping error update")
        except RuntimeError as e:
            _log.debug(f"Status indicator widget was destroyed: {e}")
    # Connect the signals (REMOVE the incorrectly placed disconnect code below)
    health_checker.health_status_changed.connect(on_health_status_changed)
    health_checker.connection_error.connect(on_connection_error)

        # Trigger an immediate health check
    def trigger_health_check():
        """Trigger health check in a separate thread to avoid blocking UI"""
        _log.info("🔍 Triggering immediate health check...")
        
        # Update UI to show checking status
        statusLabel.setText("Checking server...")
        statusIndicator.setText("⏳")
        statusIndicator.setStyleSheet("color: orange;")
        refreshButton.setEnabled(False)  # Disable button during check
        
        import threading
        def do_health_check():
            try:
                health_checker._check_server_health()
            except Exception as e:
                _log.error(f"Error in health check thread: {e}", exc_info=True)
                # Update UI from main thread
                from PyQt6.QtCore import QTimer
                def update_ui_error():
                    statusLabel.setText(f"Error: {str(e)[:50]}")
                    statusIndicator.setText("❌")
                    statusIndicator.setStyleSheet("color: red;")
                    refreshButton.setEnabled(True)
                QTimer.singleShot(0, update_ui_error)
            else:
                # Re-enable button after check completes
                from PyQt6.QtCore import QTimer
                def update_ui_done():
                    refreshButton.setEnabled(True)
                QTimer.singleShot(0, update_ui_done)
        
        thread = threading.Thread(target=do_health_check, daemon=True)
        thread.start()
    
    # Add refresh button for manual health check
    refreshButton = QPushButton(QApplication.translate("Button", "🔄 Check Server"))
    refreshButton.clicked.connect(trigger_health_check)

    # Update token status on load - DELAY until after dialog is created
    def delayed_update_token_status():
        try:
            update_token_status()
        except Exception as e:
            _log.error(f"Failed to update token status in delayed callback: {e}", exc_info=True)
    
    # Delay by 100ms to ensure dialog is fully created
    QTimer.singleShot(100, delayed_update_token_status)

    # Add widgets
    layout.addWidget(uploadToServerCheckbox)
    layout.addWidget(QLabel(QApplication.translate("Label", "Server URL:")))
    layout.addWidget(serverUrlEdit)
    layout.addWidget(QLabel(QApplication.translate("Label", "Server Health URL:")))
    layout.addWidget(serverHealthUrlEdit)
    layout.addWidget(authLabel)
    layout.addWidget(authStatusLabel)
    layout.addWidget(authButton)
    layout.addWidget(tokenGroupBox)
    layout.addWidget(timeoutLabel)
    layout.addWidget(timeoutEdit)
    layout.addWidget(retryLabel)
    layout.addWidget(retryEdit)
    layout.addWidget(statusLabel)
    layout.addWidget(statusIndicator)
    layout.addWidget(refreshButton)

    # Statistics auto-save section
    statsGroupBox = QGroupBox(QApplication.translate("GroupBox", "Statistics Auto-Save"))
    statsLayout = QVBoxLayout()
    
    autoSaveStatsCheckbox = QCheckBox(
        QApplication.translate("CheckBox", "Auto-save statistics summary on roast end")
    )
    autoSaveStatsCheckbox.setChecked(_config.auto_save_statistics_on_roast_end)
    
    formatLabel = QLabel(QApplication.translate("Label", "Format:"))
    formatComboBox = QComboBox()
    formatComboBox.addItems(["text", "pdf", "both"])
    formatIndex = formatComboBox.findText(_config.auto_save_statistics_format)
    if formatIndex >= 0:
        formatComboBox.setCurrentIndex(formatIndex)
    
    pathLabel = QLabel(QApplication.translate("Label", "Save Path (empty = use autosave path):"))
    statsPathEdit = QLineEdit(_config.auto_save_statistics_path)
    statsPathButton = QPushButton(QApplication.translate("Button", "Browse..."))
    
    def on_stats_path_browse():
        """Browse for statistics save path"""
        path = aw.ArtisanExistingDirectoryDialog(
            msg=QApplication.translate("Form Caption", "Statistics Auto-Save Path")
        )
        if path:
            statsPathEdit.setText(path)
    
    statsPathButton.clicked.connect(on_stats_path_browse)

    autoPrintStatsCheckbox = QCheckBox(
        QApplication.translate("CheckBox", "Auto-print statistics PDF when created")
    )
    autoPrintStatsCheckbox.setChecked(_config.auto_print_statistics_pdf)
    
    statsLayout.addWidget(autoSaveStatsCheckbox)
    statsLayout.addWidget(formatLabel)
    statsLayout.addWidget(formatComboBox)
    statsLayout.addWidget(autoPrintStatsCheckbox)
    statsLayout.addWidget(pathLabel)
    statsLayout.addWidget(statsPathEdit)
    statsLayout.addWidget(statsPathButton)
    
    statsGroupBox.setLayout(statsLayout)
    layout.addWidget(statsGroupBox)

    group_box.setLayout(layout)

    # Store references
    group_box.uploadToServerCheckbox = uploadToServerCheckbox
    group_box.serverUrlEdit = serverUrlEdit
    group_box.serverHealthUrlEdit = serverHealthUrlEdit
    group_box.authStatusLabel = authStatusLabel
    group_box.authButton = authButton
    group_box.timeoutEdit = timeoutEdit
    group_box.retryEdit = retryEdit
    group_box.statusIndicator = statusIndicator
    group_box.refreshButton = refreshButton
    group_box.autoSaveStatsCheckbox = autoSaveStatsCheckbox
    group_box.statsFormatComboBox = formatComboBox
    group_box.autoPrintStatsCheckbox = autoPrintStatsCheckbox
    group_box.statsPathEdit = statsPathEdit

    def cleanup_connections():
        try:
            health_checker.health_status_changed.disconnect(on_health_status_changed)
            health_checker.connection_error.disconnect(on_connection_error)
            auth_manager.login_successful.disconnect(update_auth_status)
            auth_manager.login_failed.disconnect(update_auth_status)
            auth_manager.token_refreshed.disconnect(update_auth_status)
            auth_manager.token_expired.disconnect(update_auth_status)
            _log.debug("Disconnected health checker and auth manager signals")
        except Exception as e:
            _log.debug(f"Error disconnecting signals: {e}")

    # group_box.destroyed.connect(cleanup_connections)
    

    # Trigger initial health check after a short delay
    # QTimer.singleShot(1000, trigger_health_check)

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
    
    # Save statistics auto-save settings
    if hasattr(uploadGroupBox, 'autoSaveStatsCheckbox'):
        _config.auto_save_statistics_on_roast_end = uploadGroupBox.autoSaveStatsCheckbox.isChecked()
        _config.auto_save_statistics_format = uploadGroupBox.statsFormatComboBox.currentText()
        if hasattr(uploadGroupBox, 'autoPrintStatsCheckbox'):
            _config.auto_print_statistics_pdf = uploadGroupBox.autoPrintStatsCheckbox.isChecked()
        _config.auto_save_statistics_path = uploadGroupBox.statsPathEdit.text()

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


def cleanup():
    """Cleanup resources when plugin is unloaded"""
    if _health_checker:
        _health_checker.stop()