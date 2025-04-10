# /src/plugins/rest_plugin/config_dialog.py
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                           QLabel, QLineEdit, QPushButton)

class RESTPluginConfigDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Base URL
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Server URL:"))
        self.url_edit = QLineEdit(self.config.base_url)
        url_layout.addWidget(self.url_edit)
        layout.addLayout(url_layout)
        
        # API Key
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("API Key:"))
        self.key_edit = QLineEdit(self.config.api_key)
        key_layout.addWidget(self.key_edit)
        layout.addLayout(key_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        self.setWindowTitle("REST Plugin Configuration")
        
    def save(self):
        self.config.base_url = self.url_edit.text()
        self.config.api_key = self.key_edit.text()
        self.accept()