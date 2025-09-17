"""Unit tests for artisanlib.plugins.autosave module.

This module tests the autosave plugin functionality including:
- AutosaveAddonConfig dataclass and configuration management
- ServerHealthChecker class and health monitoring
- Widget creation and UI integration
- Configuration loading and saving
- Server upload functionality
- Integration with main application

This test module implements comprehensive test isolation to prevent cross-file
module contamination and ensure proper mock state management.
Key Features:
- Session-level isolation for Qt dependencies
- Comprehensive Qt mocking with proper inheritance
- File I/O mocking for config operations
- Network request mocking for server health checks
- Proper exception handling and error testing
"""

import json
import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional


# Mock Qt Classes for Plugin Testing
class MockQObject:
    """Mock QObject for plugin base testing."""
    
    def __init__(self, *args, **kwargs):
        self.signals = {}
        self._deleted = False
        
    def deleteLater(self):
        """Mock deleteLater method."""
        self._deleted = True
        
    def moveToThread(self, thread):
        """Mock moveToThread method."""
        self._thread = thread


class MockPyQtSignal:
    """Mock pyqtSignal for plugin testing."""
    
    def __init__(self, *args, **kwargs):
        self.connected = []
        
    def connect(self, slot):
        """Mock signal connection."""
        self.connected.append(slot)
        
    def emit(self, *args):
        """Mock signal emission."""
        for slot in self.connected:
            slot(*args)


class MockQTimer:
    """Mock QTimer for plugin testing."""
    
    def __init__(self, *args, **kwargs):
        self.timeout = MockPyQtSignal()
        self._running = False
        
    def start(self, interval):
        """Mock timer start."""
        self._running = True
        
    def stop(self):
        """Mock timer stop."""
        self._running = False


class MockQCheckBox:
    """Mock QCheckBox for plugin testing."""
    
    def __init__(self, *args, **kwargs):
        self._checked = False
        self._text = ""
        
    def setChecked(self, checked):
        """Mock setChecked method."""
        self._checked = checked
        
    def isChecked(self):
        """Mock isChecked method."""
        return self._checked
        
    def setText(self, text):
        """Mock setText method."""
        self._text = text
        
    def text(self):
        """Mock text method."""
        return self._text


class MockQLineEdit:
    """Mock QLineEdit for plugin testing."""
    
    def __init__(self, *args, **kwargs):
        self._text = ""
        
    def setText(self, text):
        """Mock setText method."""
        self._text = text
        
    def text(self):
        """Mock text method."""
        return self._text
    
    def setPlaceholderText(self, text):
         """Mock setPlaceholderText method."""
         self._placeholder_text = text
         
    def placeholderText(self):
        """Mock placeholderText method."""
        return self._placeholder_text

    def setEchoMode(self, mode):
        """Mock setEchoMode method."""
        self._echo_mode = mode
        
    def EchoMode(self):
        """Mock echoMode method."""
        return self._echo_mode


class MockQComboBox:
    """Mock QComboBox for plugin testing."""
    
    def __init__(self, *args, **kwargs):
        self._current_text = ""
    
    def setCurrentIndex(self, index):
        """Mock setCurrentIndex method."""
        self._current_index = index
        
    def currentIndex(self):
        """Mock currentIndex method."""
        return self._current_index
        
    def setCurrentText(self, text):
        """Mock setCurrentText method."""
        self._current_text = text
        
    def currentText(self):
        """Mock currentText method."""
        return self._current_text
    
    def findText(self, text):
        """Mock findText method."""
        return self._items.index(text)

    def addItems(self, items):
        """Mock addItems method."""
        self._items = items
        
    def items(self):
        """Mock items method."""
        return self._items


class MockQPushButton:
    """Mock QPushButton for plugin testing."""
    
    def __init__(self, *args, **kwargs):
        self._text = ""
        
    def setText(self, text):
        """Mock setText method."""
        self._text = text
        
    def text(self):
        """Mock text method."""
        return self._text


class MockQLabel:
    """Mock QLabel for plugin testing."""
    
    def __init__(self, *args, **kwargs):
        self._text = ""
        
    def setText(self, text):
        """Mock setText method."""
        self._text = text
        
    def text(self):
        """Mock text method."""
        return self._text


class MockQGroupBox:
    """Mock QGroupBox for plugin testing."""
    
    def __init__(self, title="", *args, **kwargs):
        self._title = title
        self._layout = None
        
    def setTitle(self, title):
        """Mock setTitle method."""
        self._title = title
        
    def title(self):
        """Mock title method."""
        return self._title
        
    def setLayout(self, layout):
        """Mock setLayout method."""
        self._layout = layout


class MockQVBoxLayout:
    """Mock QVBoxLayout for plugin testing."""
    
    def __init__(self, *args, **kwargs):
        self._widgets = []
        
    def addWidget(self, widget):
        """Mock addWidget method."""
        self._widgets.append(widget)


class MockQHBoxLayout:
    """Mock QHBoxLayout for plugin testing."""
    
    def __init__(self, *args, **kwargs):
        self._widgets = []
        
    def addWidget(self, widget):
        """Mock addWidget method."""
        self._widgets.append(widget)


class MockQApplication:
    """Mock QApplication for plugin testing."""
    
    @staticmethod
    def translate(context, text):
        """Mock translate method."""
        return text


# Test Classes
class TestAutosaveAddonConfig:
    """Test cases for AutosaveAddonConfig class."""

    def test_config_default_values(self) -> None:
        """Test config default values."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config = AutosaveAddonConfig()
            
            # Test default values
            assert config.autosave_pdf_2 is False
            assert config.autosave_image_type_2 == "PDF"
            assert config.autosave_path_2 == ""
            assert config.autosave_pdf_3 is False
            assert config.autosave_image_type_3 == "PDF Report"
            assert config.autosave_path_3 == ""
            assert config.autosave_upload_to_server is False
            assert config.autosave_server_url == "http://localhost:5101"
            assert config.autosave_health_url == "http://localhost:5101/api/files/health"
            assert config.autosave_api_token == ""
            assert config.autosave_jwt_token == ""
            assert config.autosave_auth_type == "none"
            assert config.autosave_connection_timeout == 30
            assert config.autosave_retry_attempts == 3
            assert config.autosave_retry_delay == 5
            assert config.autosave_health_check_enabled is True
            assert config.autosave_health_check_interval == 300
            assert config.enabled is True
            assert config.auto_save_on_roast_end is True

    def test_config_to_dict(self) -> None:
        """Test config to_dict method."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config = AutosaveAddonConfig()
            config.autosave_pdf_2 = True
            config.autosave_path_2 = "/test/path"
            config.autosave_upload_to_server = True
            
            data = config.to_dict()
            
            assert data["autosave_pdf_2"] is True
            assert data["autosave_path_2"] == "/test/path"
            assert data["autosave_upload_to_server"] is True
            assert data["autosave_health_url"] == "http://localhost:5101/api/files/health"

    def test_config_from_dict(self) -> None:
        """Test config from_dict method."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            data = {
                "autosave_pdf_2": True,
                "autosave_path_2": "/test/path",
                "autosave_upload_to_server": True
            }
            
            config = AutosaveAddonConfig.from_dict(data)
            
            assert config.autosave_pdf_2 is True
            assert config.autosave_path_2 == "/test/path"
            assert config.autosave_upload_to_server is True

    def test_config_from_dict_health_url_backward_compatibility(self) -> None:
        """Test config from_dict with backward compatibility for health_url."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            # Old config without health_url
            data = {
                "autosave_server_url": "http://example.com:8080"
            }
            
            config = AutosaveAddonConfig.from_dict(data)
            
            assert config.autosave_health_url == "http://example.com:8080/api/files/health"

    def test_config_load_from_file_existing(self) -> None:
        """Test config load_from_file with existing file."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }), tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            # Write test config to file
            config_data = {
                "autosave_pdf_2": True,
                "autosave_path_2": "/test/path",
                "autosave_upload_to_server": True
            }
            json.dump(config_data, temp_file)
            temp_file.flush()
            
            # Load config from file
            config = AutosaveAddonConfig.load_from_file(temp_file.name)
            
            assert config.autosave_pdf_2 is True
            assert config.autosave_path_2 == "/test/path"
            assert config.autosave_upload_to_server is True
            
            # Cleanup
            Path(temp_file.name).unlink()
    
    def test_config_load_from_file_nonexistent(self) -> None:
        """Test config load_from_file with nonexistent file."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            # Load config from nonexistent file
            config = AutosaveAddonConfig.load_from_file("/nonexistent/path/config.json")
            
            # Should return default config
            assert config.autosave_pdf_2 is False
            assert config.autosave_server_url == "http://localhost:5101"
    
    def test_config_save_to_file(self) -> None:
        """Test config save_to_file method."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }), tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config = AutosaveAddonConfig()
            config.autosave_pdf_2 = True
            config.autosave_path_2 = "/test/path"
            
            # Save config to file
            result = config.save_to_file(temp_file.name)
            
            assert result is True
            
            # Verify file was written correctly
            with open(temp_file.name, 'r') as f:
                saved_data = json.load(f)
                
            assert saved_data["autosave_pdf_2"] is True
            assert saved_data["autosave_path_2"] == "/test/path"
            
            # Cleanup
            Path(temp_file.name).unlink()


class TestServerHealthChecker:
    """Test ServerHealthChecker functionality."""
    
    def test_health_checker_initialization(self) -> None:
        """Test ServerHealthChecker proper initialization."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            from artisanlib.plugins.autosave.autosave_addons import ServerHealthChecker
            
            config = AutosaveAddonConfig()
            config.autosave_health_check_enabled = False  # Disable for test
            
            checker = ServerHealthChecker(config)
            
            assert checker.config == config
            assert checker.is_healthy is False
            assert checker.last_check == 0
            assert hasattr(checker, 'health_timer')
            assert hasattr(checker, 'health_status_changed')
            assert hasattr(checker, 'connection_error')
    
    def test_health_checker_auth_headers_none(self) -> None:
        """Test health checker auth headers with no auth."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            from artisanlib.plugins.autosave.autosave_addons import ServerHealthChecker
            
            config = AutosaveAddonConfig()
            config.autosave_auth_type = "none"
            config.autosave_health_check_enabled = False
            
            checker = ServerHealthChecker(config)
            headers = checker._get_auth_headers()
            
            assert headers == {}
    
    def test_health_checker_auth_headers_api_token(self) -> None:
        """Test health checker auth headers with API token."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            from artisanlib.plugins.autosave.autosave_addons import ServerHealthChecker
            
            config = AutosaveAddonConfig()
            config.autosave_auth_type = "api_token"
            config.autosave_api_token = "test_token"
            config.autosave_health_check_enabled = False
            
            checker = ServerHealthChecker(config)
            headers = checker._get_auth_headers()
            
            assert headers == {"X-API-Key": "test_token"}
    
    def test_health_checker_auth_headers_jwt(self) -> None:
        """Test health checker auth headers with JWT token."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            from artisanlib.plugins.autosave.autosave_addons import ServerHealthChecker
            
            config = AutosaveAddonConfig()
            config.autosave_auth_type = "jwt"
            config.autosave_jwt_token = "test_jwt_token"
            config.autosave_health_check_enabled = False
            
            checker = ServerHealthChecker(config)
            headers = checker._get_auth_headers()
            
            assert headers == {"Authorization": "Bearer test_jwt_token"}
    
    def test_health_checker_successful_health_check(self) -> None:
        """Test successful server health check."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }), patch('requests.get') as mock_get:
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            from artisanlib.plugins.autosave.autosave_addons import ServerHealthChecker
            
            config = AutosaveAddonConfig()
            config.autosave_health_check_enabled = False
            
            # Mock successful response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_get.return_value = mock_response
            
            checker = ServerHealthChecker(config)
            checker._check_server_health()
            
            assert checker.is_healthy is True
            assert checker.last_check > 0
            mock_get.assert_called_once()

    def test_health_checker_failed_health_check(self) -> None:
        """Test failed server health check."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }), patch('requests.get') as mock_get:
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            from artisanlib.plugins.autosave.autosave_addons import ServerHealthChecker
            
            config = AutosaveAddonConfig()
            config.autosave_health_check_enabled = False
            
            # Mock failed response
            mock_response = Mock()
            mock_response.status_code = 500
            mock_get.return_value = mock_response
            
            checker = ServerHealthChecker(config)
            checker.is_healthy = True  # Start as healthy
            checker._check_server_health()
            
            assert checker.is_healthy is False
            assert checker.last_check > 0
            mock_get.assert_called_once()


class TestAutosaveWidgets:
    """Test autosave widget creation functionality."""
    
    def test_create_server_upload_widgets(self) -> None:
        """Test server upload widgets creation."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(
                QCheckBox=MockQCheckBox,
                QLineEdit=MockQLineEdit,
                QComboBox=MockQComboBox,
                QPushButton=MockQPushButton,
                QLabel=MockQLabel,
                QGroupBox=MockQGroupBox,
                QVBoxLayout=MockQVBoxLayout,
                QHBoxLayout=MockQHBoxLayout,
            ),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(
                QCheckBox=MockQCheckBox,
                QLineEdit=MockQLineEdit,
                QComboBox=MockQComboBox,
                QPushButton=MockQPushButton,
                QLabel=MockQLabel,
                QGroupBox=MockQGroupBox,
                QVBoxLayout=MockQVBoxLayout,
                QHBoxLayout=MockQHBoxLayout,
            ),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            from artisanlib.plugins.autosave.autosave_addons import create_server_upload_widgets
            
            config = AutosaveAddonConfig()
            widgets = create_server_upload_widgets(config)
            
            assert isinstance(widgets, dict)
            assert "upload_checkbox" in widgets
            assert "server_url_edit" in widgets
            assert "auth_type_combo" in widgets
            assert "api_token_edit" in widgets
            assert "jwt_token_edit" in widgets
            assert "test_connection_button" in widgets
    
    def test_create_additional_format_widgets(self) -> None:
        """Test additional format widgets creation."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(
                QCheckBox=MockQCheckBox,
                QLineEdit=MockQLineEdit,
                QComboBox=MockQComboBox,
                QPushButton=MockQPushButton,
                QLabel=MockQLabel,
                QGroupBox=MockQGroupBox,
                QVBoxLayout=MockQVBoxLayout,
                QHBoxLayout=MockQHBoxLayout,
            ),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(
                QCheckBox=MockQCheckBox,
                QLineEdit=MockQLineEdit,
                QComboBox=MockQComboBox,
                QPushButton=MockQPushButton,
                QLabel=MockQLabel,
                QGroupBox=MockQGroupBox,
                QVBoxLayout=MockQVBoxLayout,
                QHBoxLayout=MockQHBoxLayout,
            ),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            from artisanlib.plugins.autosave.autosave_addons import create_additional_format_widgets
            
            config = AutosaveAddonConfig()
            widgets = create_additional_format_widgets(config, format_number=2)
            
            assert isinstance(widgets, dict)
            assert "format2_checkbox" in widgets
            assert "format2_type_combo" in widgets
            assert "format2_path_edit" in widgets


class TestAutosaveIntegration:
    """Test autosave integration functionality."""
    
    def test_load_config_to_qmc(self) -> None:
        """Test loading config to qmc object."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.autosave_addons import load_config_to_qmc
            
            # Mock qmc object
            qmc = Mock()
            qmc.autosave_pdf_2 = False
            qmc.autosave_path_2 = ""
            qmc.autosave_upload_to_server = False
            
            # Load config
            load_config_to_qmc(qmc)
            
            # Verify config was loaded
            assert hasattr(qmc, 'autosave_pdf_2')
            assert hasattr(qmc, 'autosave_path_2')
            assert hasattr(qmc, 'autosave_upload_to_server')
    
    def test_should_upload_to_server(self) -> None:
        """Test should_upload_to_server function."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.autosave_addons import should_upload_to_server
            
            # Mock qmc object with upload enabled
            qmc = Mock()
            qmc.autosave_upload_to_server = True
            qmc.autosave_server_url = "http://test.com"
            
            result = should_upload_to_server(qmc)
            assert result is True
            
            # Mock qmc object with upload disabled
            qmc.autosave_upload_to_server = False
            result = should_upload_to_server(qmc)
            assert result is False

    def test_save_widget_values_to_config(self) -> None:
        """Test saving widget values to config."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(),
            'requests': Mock(),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            from artisanlib.plugins.autosave.autosave_addons import save_widget_values_to_config
            
            config = AutosaveAddonConfig()
            
            # Mock widgets
            widgets = {
                "upload_checkbox": MockQCheckBox(),
                "server_url_edit": MockQLineEdit(),
                "auth_type_combo": MockQComboBox(),
                "api_token_edit": MockQLineEdit(),
                "format2_checkbox": MockQCheckBox(),
                "format2_path_edit": MockQLineEdit(),
            }
            
            # Set widget values
            widgets["upload_checkbox"].setChecked(True)
            widgets["server_url_edit"].setText("http://test.com")
            widgets["auth_type_combo"].setCurrentText("api_token")
            widgets["api_token_edit"].setText("test_token")
            widgets["format2_checkbox"].setChecked(True)
            widgets["format2_path_edit"].setText("/test/path")
            
            # Save widget values to config
            save_widget_values_to_config(widgets, config)
            
            # Verify config was updated
            assert config.autosave_upload_to_server is True
            assert config.autosave_server_url == "http://test.com"
            assert config.autosave_auth_type == "api_token"
            assert config.autosave_api_token == "test_token"
            assert config.autosave_pdf_2 is True
            assert config.autosave_path_2 == "/test/path"


@pytest.mark.parametrize(
    'auth_type,api_token,jwt_token,expected_headers',
    [
        ('none', '', '', {}),
        ('api_token', 'test_api_token', '', {'X-API-Key': 'test_api_token'}),
        ('jwt', '', 'test_jwt_token', {'Authorization': 'Bearer test_jwt_token'}),
        ('bearer', '', 'test_bearer_token', {'Authorization': 'Bearer test_bearer_token'}),
    ],
)
def test_health_checker_auth_headers_parametrized(
    auth_type: str, 
    api_token: str, 
    jwt_token: str, 
    expected_headers: Dict[str, str]
) -> None:
    """Test health checker auth headers with various auth types."""
    with patch.dict('sys.modules', {
        'PyQt6.QtCore': Mock(
            QObject=MockQObject,
            pyqtSignal=MockPyQtSignal,
            QTimer=MockQTimer
        ),
        'PyQt6.QtWidgets': Mock(),
        'PyQt5.QtCore': Mock(
            QObject=MockQObject,
            pyqtSignal=MockPyQtSignal,
            QTimer=MockQTimer
        ),
        'PyQt5.QtWidgets': Mock(),
        'requests': Mock(),
        'logging': Mock(getLogger=Mock(return_value=Mock())),
    }):
        from artisanlib.plugins.autosave.config import AutosaveAddonConfig
        from artisanlib.plugins.autosave.autosave_addons import ServerHealthChecker
        
        config = AutosaveAddonConfig()
        config.autosave_auth_type = auth_type
        config.autosave_api_token = api_token
        config.autosave_jwt_token = jwt_token
        config.autosave_health_check_enabled = False
        
        checker = ServerHealthChecker(config)
        headers = checker._get_auth_headers()
        
        assert headers == expected_headers


@pytest.mark.parametrize(
    'config_data,expected_values',
    [
        ({}, {
            'autosave_pdf_2': False,
            'autosave_server_url': 'http://localhost:5101',
            'autosave_auth_type': 'none'
        }),
        ({
            'autosave_pdf_2': True,
            'autosave_path_2': '/test/path',
            'autosave_upload_to_server': True
        }, {
            'autosave_pdf_2': True,
            'autosave_path_2': '/test/path',
            'autosave_upload_to_server': True
        }),
    ],
)
def test_config_from_dict_parametrized(
    config_data: Dict[str, Any], 
    expected_values: Dict[str, Any]
) -> None:
    """Test config from_dict method with various data."""
    with patch.dict('sys.modules', {
        'PyQt6.QtCore': Mock(),
        'PyQt6.QtWidgets': Mock(),
        'PyQt5.QtCore': Mock(),
        'PyQt5.QtWidgets': Mock(),
        'requests': Mock(),
        'logging': Mock(getLogger=Mock(return_value=Mock())),
    }):
        from artisanlib.plugins.autosave.config import AutosaveAddonConfig
        
        config = AutosaveAddonConfig.from_dict(config_data)
        
        for key, expected_value in expected_values.items():
            assert getattr(config, key) == expected_value