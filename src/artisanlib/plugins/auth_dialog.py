from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QDialogButtonBox, QTabWidget, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt
import logging

_log = logging.getLogger(__name__)

class AuthDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._auth_manager = None
        
        self.setup_ui()
        self.connect_signals()
    
    @property
    def auth_manager(self):
        """Lazy initialization of GlobalAuthManager"""
        if self._auth_manager is None:
            try:
                from .auth_manager import get_auth_manager
                self._auth_manager = get_auth_manager()
                _log.debug("GlobalAuthManager retrieved for AuthDialog")
            except Exception as e:
                _log.error(f"Failed to get GlobalAuthManager: {e}", exc_info=True)
                return None
        return self._auth_manager
    
    def setup_ui(self):
        self.setWindowTitle("Artisan Authentication")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()

        # server URL configuration section
        server_url_group = QWidget()
        server_url_layout = QVBoxLayout()
        server_url_layout.setContentsMargins(0, 0, 0, 10)
        
        server_url_label = QLabel("Server URL:")
        server_url_layout.addWidget(server_url_label)
        
        server_url_input_layout = QHBoxLayout()
        self.server_url_input = QLineEdit()
        self.server_url_input.setPlaceholderText("http://localhost:5101/auth")
        
        # Load current server URL if available
        try:
            if self.auth_manager and hasattr(self.auth_manager, 'get_auth_base_url'):
                current_url = self.auth_manager.get_auth_base_url()
                if current_url:
                    # Remove /auth suffix for display
                    display_url = current_url.replace('/auth', '') if current_url.endswith('/auth') else current_url
                    self.server_url_input.setText(display_url)
        except Exception as e:
            _log.warning(f"Could not load server URL: {e}")
        
        server_url_input_layout.addWidget(self.server_url_input)
        
        self.save_url_button = QPushButton("Save")
        self.save_url_button.setMaximumWidth(80)
        self.save_url_button.clicked.connect(self.save_server_url)
        server_url_input_layout.addWidget(self.save_url_button)
        
        server_url_layout.addLayout(server_url_input_layout)
        
        server_url_hint = QLabel("Enter the base URL of your authentication server (without /auth suffix)")
        server_url_hint.setStyleSheet("color: #666; font-size: 9px;")
        server_url_hint.setWordWrap(True)
        server_url_layout.addWidget(server_url_hint)
        
        server_url_group.setLayout(server_url_layout)
        layout.addWidget(server_url_group)
        
        # Add separator
        from PyQt6.QtWidgets import QFrame
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        
        # Create tab widget for different auth methods
        self.tabs = QTabWidget()
        
        # OAuth Tab
        oauth_tab = QWidget()
        oauth_layout = QVBoxLayout()
        
        oauth_info = QLabel(
            "Authenticate using your Google account.\n"
            "Click the button below to open your browser."
        )
        oauth_info.setWordWrap(True)
        oauth_layout.addWidget(oauth_info)
        
        self.google_button = QPushButton("Login with Google")
        self.google_button.clicked.connect(self.login_with_google)
        oauth_layout.addWidget(self.google_button)
        
        oauth_layout.addStretch()
        oauth_tab.setLayout(oauth_layout)
        self.tabs.addTab(oauth_tab, "Google OAuth")
        
        # API Key Tab
        api_key_tab = QWidget()
        api_key_layout = QVBoxLayout()
        
        api_key_info = QLabel(
            "Enter your API key to authenticate.\n"
            "API keys start with 'ccr_' prefix."
        )
        api_key_info.setWordWrap(True)
        api_key_layout.addWidget(api_key_info)
        
        api_key_label = QLabel("API Key:")
        api_key_layout.addWidget(api_key_label)
        
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("ccr_...")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)

        # Load current API key if one exists
        try:
            if self.auth_manager and hasattr(self.auth_manager, 'api_key') and self.auth_manager.api_key:
                self.api_key_input.setText(self.auth_manager.api_key)
        except Exception as e:
            _log.warning(f"Could not load API key: {e}")

        api_key_layout.addWidget(self.api_key_input)

        # Button layout
        api_key_button_layout = QHBoxLayout()
        
        self.api_key_button = QPushButton("Authenticate with API Key")
        self.api_key_button.clicked.connect(self.login_with_api_key)
        api_key_layout.addWidget(self.api_key_button)
        
        # Clear API Key button (only show if API key exists)
        try:
            if self.auth_manager and hasattr(self.auth_manager, 'api_key') and self.auth_manager.api_key:
                self.clear_api_key_button = QPushButton("Clear API Key")
                self.clear_api_key_button.clicked.connect(self.clear_api_key)
                api_key_button_layout.addWidget(self.clear_api_key_button)
        except Exception as e:
            _log.warning(f"Could not check for API key: {e}")
        
        api_key_layout.addLayout(api_key_button_layout)
        
        api_key_layout.addStretch()
        api_key_tab.setLayout(api_key_layout)
        self.tabs.addTab(api_key_tab, "API Key")
        
        layout.addWidget(self.tabs)
        
        # Status label
        self.status_label = QLabel("Select an authentication method above")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Cancel button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def connect_signals(self):
        """Connect auth manager signals with error handling"""
        if self.auth_manager is None:
            _log.warning("Auth manager not available, skipping signal connections")
            return
        
        try:
            self.auth_manager.login_successful.connect(self.on_login_success)
            self.auth_manager.login_failed.connect(self.on_login_failed)
            self.auth_manager.api_key_validated.connect(self.on_api_key_validated)
            _log.debug("Auth manager signals connected")
        except Exception as e:
            _log.error(f"Failed to connect auth manager signals: {e}", exc_info=True)
    
    def login_with_google(self):
        if self.auth_manager is None:
            QMessageBox.warning(self, "Error", "Authentication manager is not available")
            return
        
        self.status_label.setText("Opening browser for Google authentication...")
        self.google_button.setEnabled(False)
        
        import threading
        def do_login():
            try:
                success = self.auth_manager.login_with_google()
                if not success:
                    from PyQt6.QtCore import QTimer
                    def update_ui():
                        self.status_label.setText("Authentication failed. Please try again.")
                        self.google_button.setEnabled(True)
                    QTimer.singleShot(0, update_ui)
            except Exception as e:
                _log.error(f"Error in Google login thread: {e}", exc_info=True)
                from PyQt6.QtCore import QTimer
                def update_ui():
                    self.status_label.setText(f"Error: {str(e)}")
                    self.google_button.setEnabled(True)
                QTimer.singleShot(0, update_ui)
        
        thread = threading.Thread(target=do_login, daemon=True)
        thread.start()
    
    def login_with_api_key(self):
        if self.auth_manager is None:
            QMessageBox.warning(self, "Error", "Authentication manager is not available")
            return
        
        api_key = self.api_key_input.text().strip()
        
        if not api_key:
            QMessageBox.warning(self, "Invalid API Key", "Please enter an API key")
            return
        
        if not api_key.startswith('ccr_'):
            QMessageBox.warning(
                self, 
                "Invalid API Key Format", 
                "API keys must start with 'ccr_' prefix"
            )
            return
        
        self.status_label.setText("Validating API key...")
        self.api_key_button.setEnabled(False)
        
        import threading
        def do_login():
            try:
                success = self.auth_manager.login_with_api_key(api_key)
                if not success:
                    from PyQt6.QtCore import QTimer
                    def update_ui():
                        self.status_label.setText("API key validation failed. Please check your key.")
                        self.api_key_button.setEnabled(True)
                    QTimer.singleShot(0, update_ui)
            except Exception as e:
                _log.error(f"Error in API key login thread: {e}", exc_info=True)
                from PyQt6.QtCore import QTimer
                def update_ui():
                    self.status_label.setText(f"Error: {str(e)}")
                    self.api_key_button.setEnabled(True)
                QTimer.singleShot(0, update_ui)
        
        thread = threading.Thread(target=do_login, daemon=True)
        thread.start()
    
    def on_login_success(self, access_token, refresh_token):
        """Handle successful login - called from signal"""
        try:
            self.status_label.setText("Authentication successful!")
            self.accept()
        except Exception as e:
            _log.error(f"Error handling login success: {e}", exc_info=True)
    
    def on_api_key_validated(self, api_key):
        """Handle API key validation - called from signal"""
        try:
            self.status_label.setText("API key validated successfully!")
            self.accept()
        except Exception as e:
            _log.error(f"Error handling API key validation: {e}", exc_info=True)
    
    def on_login_failed(self, error):
        """Handle login failure - called from signal"""
        try:
            self.status_label.setText(f"Authentication failed: {error}")
            self.google_button.setEnabled(True)
            self.api_key_button.setEnabled(True)
        except Exception as e:
            _log.error(f"Error handling login failure: {e}", exc_info=True)

    def clear_api_key(self):
        """Clear the current API key"""
        if self.auth_manager is None:
            return
        
        reply = QMessageBox.question(
            self,
            "Clear API Key",
            "Are you sure you want to clear your API key?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.auth_manager.clear_tokens()
                self.api_key_input.clear()
                self.status_label.setText("API key cleared")
                
                # Remove the clear button if it exists
                if hasattr(self, 'clear_api_key_button'):
                    self.clear_api_key_button.setParent(None)
                    self.clear_api_key_button = None
            except Exception as e:
                _log.error(f"Error clearing API key: {e}", exc_info=True)
                QMessageBox.warning(self, "Error", f"Failed to clear API key: {e}")

    def save_server_url(self):
        """Save the server URL configuration"""
        if self.auth_manager is None:
            QMessageBox.warning(self, "Error", "Authentication manager is not available")
            return
        
        url = self.server_url_input.text().strip()
        
        if not url:
            QMessageBox.warning(self, "Invalid URL", "Please enter a server URL")
            return
        
        # Remove trailing slashes
        url = url.rstrip('/')
        
        # Validate URL format
        if not (url.startswith('http://') or url.startswith('https://')):
            QMessageBox.warning(
                self,
                "Invalid URL Format",
                "URL must start with http:// or https://"
            )
            return
        
        try:
            # Add /auth suffix if not present
            if not url.endswith('/auth'):
                url = url + '/auth'
            
            self.auth_manager.set_auth_base_url(url)
            self.status_label.setText(f"Server URL saved: {url}")
            QMessageBox.information(
                self,
                "Success",
                f"Server URL has been saved:\n{url}\n\nThis will be used for all authentication requests."
            )
        except Exception as e:
            _log.error(f"Error saving server URL: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to save server URL: {str(e)}")