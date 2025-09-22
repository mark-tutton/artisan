from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QDialogButtonBox
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
        
        layout = QVBoxLayout()
        
        # Google OAuth button
        self.google_button = QPushButton("Login with Google")
        self.google_button.clicked.connect(self.login_with_google)
        layout.addWidget(self.google_button)
        
        # Status label
        self.status_label = QLabel("Click 'Login with Google' to authenticate")
        layout.addWidget(self.status_label)
        
        # Cancel button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def connect_signals(self):
        self.auth_manager.login_successful.connect(self.on_login_success)
        self.auth_manager.login_failed.connect(self.on_login_failed)
    
    def login_with_google(self):
        self.status_label.setText("Opening browser for Google authentication...")
        self.google_button.setEnabled(False)
        
        if self.auth_manager.login_with_google():
            self.accept()
    
    def on_login_success(self, access_token, refresh_token):
        self.status_label.setText("Authentication successful!")
        self.accept()
    
    def on_login_failed(self, error):
        self.status_label.setText(f"Authentication failed: {error}")
        self.google_button.setEnabled(True)