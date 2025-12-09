from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QDialogButtonBox, QTabWidget, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from .auth_manager import GlobalAuthManager

class AuthDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.auth_manager = GlobalAuthManager()
        self.setup_ui()
        self.connect_signals()
    
    def setup_ui(self):
        self.setWindowTitle("Artisan Authentication")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout()
        
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
        if self.auth_manager.api_key:
            self.api_key_input.setText(self.auth_manager.api_key)

        api_key_layout.addWidget(self.api_key_input)

        # Button layout
        api_key_button_layout = QHBoxLayout()
        
        self.api_key_button = QPushButton("Authenticate with API Key")
        self.api_key_button.clicked.connect(self.login_with_api_key)
        api_key_layout.addWidget(self.api_key_button)
        
        # Clear API Key button (only show if API key exists)
        if self.auth_manager.api_key:
            self.clear_api_key_button = QPushButton("Clear API Key")
            self.clear_api_key_button.clicked.connect(self.clear_api_key)
            api_key_button_layout.addWidget(self.clear_api_key_button)
        
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
        self.auth_manager.login_successful.connect(self.on_login_success)
        self.auth_manager.login_failed.connect(self.on_login_failed)
        self.auth_manager.api_key_validated.connect(self.on_api_key_validated)
    
    def login_with_google(self):
        self.status_label.setText("Opening browser for Google authentication...")
        self.google_button.setEnabled(False)
        
        import threading
        def do_login():
            success = self.auth_manager.login_with_google()
            if not success:
                self.status_label.setText("Authentication failed. Please try again.")
                self.google_button.setEnabled(True)
        
        thread = threading.Thread(target=do_login, daemon=True)
        thread.start()
    
    def login_with_api_key(self):
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
            success = self.auth_manager.login_with_api_key(api_key)
            if not success:
                self.status_label.setText("API key validation failed. Please check your key.")
                self.api_key_button.setEnabled(True)
        
        thread = threading.Thread(target=do_login, daemon=True)
        thread.start()
    
    def on_login_success(self, access_token, refresh_token):
        self.status_label.setText("Authentication successful!")
        self.accept()
    
    def on_api_key_validated(self, api_key):
        self.status_label.setText("API key validated successfully!")
        self.accept()
    
    def on_login_failed(self, error):
        self.status_label.setText(f"Authentication failed: {error}")
        self.google_button.setEnabled(True)
        self.api_key_button.setEnabled(True)

    def clear_api_key(self):
        """Clear the current API key"""
        reply = QMessageBox.question(
            self,
            "Clear API Key",
            "Are you sure you want to clear your API key?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.auth_manager.clear_api_key()
            self.api_key_input.clear()
            self.status_label.setText("API key cleared")
            
            # Remove the clear button if it exists
            if hasattr(self, 'clear_api_key_button'):
                self.clear_api_key_button.setParent(None)
                self.clear_api_key_button = None