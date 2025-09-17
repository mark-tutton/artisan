"""Unit tests for artisanlib.plugins.autosave.config module.

This module tests the AutosaveAddonConfig dataclass functionality including:
- Default value initialization
- Dictionary serialization and deserialization
- File I/O operations (load/save)
- Backward compatibility handling
- Error handling and edge cases
- Configuration validation

This test module implements comprehensive test isolation to prevent cross-file
module contamination and ensure proper mock state management.
Key Features:
- Session-level isolation for external dependencies
- File system mocking for config operations
- Test independence and proper cleanup
- Python 3.8+ compatibility with type annotations
- Comprehensive error handling tests
"""

import sys
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Generator
from unittest.mock import Mock, patch, mock_open

import pytest



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


class MockQComboBox:
    """Mock QComboBox for plugin testing."""
    
    def __init__(self, *args, **kwargs):
        self._current_text = ""
        
    def setCurrentText(self, text):
        """Mock setCurrentText method."""
        self._current_text = text
        
    def currentText(self):
        """Mock currentText method."""
        return self._current_text


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



# Mock PyQt6 modules to prevent import errors during testing
sys.modules['PyQt6'] = Mock()
sys.modules['PyQt6.QtCore'] = Mock()
sys.modules['PyQt6.QtWidgets'] = Mock()
sys.modules['PyQt6.QtGui'] = Mock()

# Mock specific PyQt6 classes that might be imported
sys.modules['PyQt6.QtCore'].QObject = MockQObject
sys.modules['PyQt6.QtCore'].QTimer = MockQTimer
sys.modules['PyQt6.QtCore'].pyqtSignal = MockPyQtSignal
sys.modules['PyQt6.QtCore'].Qt = Mock()
sys.modules['PyQt6.QtWidgets'].QCheckBox = MockQCheckBox
sys.modules['PyQt6.QtWidgets'].QLineEdit = MockQLineEdit
sys.modules['PyQt6.QtWidgets'].QComboBox = MockQComboBox
sys.modules['PyQt6.QtWidgets'].QPushButton = MockQPushButton
sys.modules['PyQt6.QtWidgets'].QLabel = MockQLabel
sys.modules['PyQt6.QtWidgets'].QGroupBox = MockQGroupBox
sys.modules['PyQt6.QtWidgets'].QVBoxLayout = MockQVBoxLayout
sys.modules['PyQt6.QtWidgets'].QHBoxLayout = MockQHBoxLayout
sys.modules['PyQt6.QtWidgets'].QApplication = MockQApplication




@pytest.fixture(scope='session', autouse=True)
def session_level_isolation() -> Generator[None, None, None]:
    """Session-level isolation fixture to prevent cross-file module contamination.
    
    This fixture ensures that external dependencies are properly isolated
    at the session level while preserving the functionality needed for
    config tests.
    """
    # Store original modules if they exist and aren't mocked
    original_modules: Dict[str, Any] = {}
    modules_to_check = [
        'json',
        'pathlib',
        'logging',
        'os',
    ]
    
    for module_name in modules_to_check:
        if module_name in sys.modules and not hasattr(sys.modules[module_name], '_mock_name'):
            original_modules[module_name] = sys.modules[module_name]
    
    yield
    
    # Restore original modules after session
    for module_name, original_module in original_modules.items():
        if module_name in sys.modules:
            sys.modules[module_name] = original_module


@pytest.fixture(autouse=True) 
def reset_config_state() -> Generator[None, None, None]:
    """Reset config test state before each test to ensure test independence."""
    
    yield
    
    # Clean up after each test
    import gc
    gc.collect()


class TestAutosaveAddonConfig:
    """Test AutosaveAddonConfig dataclass functionality."""
    
    def test_config_default_values(self) -> None:
        """Test that config has correct default values."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config = AutosaveAddonConfig()
            
            # Format 2 settings
            assert config.autosave_pdf_2 is False
            assert config.autosave_image_type_2 == "PDF"
            assert config.autosave_path_2 == ""
            
            # Format 3 settings
            assert config.autosave_pdf_3 is False
            assert config.autosave_image_type_3 == "PDF Report"
            assert config.autosave_path_3 == ""
            
            # Server upload settings
            assert config.autosave_upload_to_server is False
            assert config.autosave_server_url == "http://localhost:5101"
            assert config.autosave_health_url == "http://localhost:5101/api/files/health"
            assert config.autosave_api_token == ""
            assert config.autosave_jwt_token == ""
            assert config.autosave_auth_type == "none"
            
            # Server connection settings
            assert config.autosave_connection_timeout == 30
            assert config.autosave_retry_attempts == 3
            assert config.autosave_retry_delay == 5
            assert config.autosave_health_check_enabled is True
            assert config.autosave_health_check_interval == 300
            
            # General settings
            assert config.enabled is True
            assert config.auto_save_on_roast_end is True
    
    def test_config_to_dict_complete(self) -> None:
        """Test config to_dict method returns all fields."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config = AutosaveAddonConfig()
            config_dict = config.to_dict()
            
            # Verify all expected fields are present
            expected_fields = {
                "autosave_pdf_2", "autosave_image_type_2", "autosave_path_2",
                "autosave_pdf_3", "autosave_image_type_3", "autosave_path_3",
                "autosave_upload_to_server", "autosave_server_url", "autosave_health_url",
                "autosave_api_token", "autosave_jwt_token", "autosave_auth_type", 
                "autosave_connection_timeout", "autosave_retry_attempts", "autosave_retry_delay", 
                "autosave_health_check_enabled", "autosave_health_check_interval", 
                "enabled", "auto_save_on_roast_end"
            }
            
            assert set(config_dict.keys()) == expected_fields
            assert isinstance(config_dict, dict)
    
    def test_config_to_dict_with_custom_values(self) -> None:
        """Test config to_dict method with custom values."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config = AutosaveAddonConfig()
            config.autosave_pdf_2 = True
            config.autosave_path_2 = "/test/path"
            config.autosave_upload_to_server = True
            config.autosave_server_url = "http://test.com"
            config.autosave_auth_type = "api_token"
            config.autosave_api_token = "test_token"
            config.autosave_connection_timeout = 60
            config.enabled = False
            
            config_dict = config.to_dict()
            
            assert config_dict["autosave_pdf_2"] is True
            assert config_dict["autosave_path_2"] == "/test/path"
            assert config_dict["autosave_upload_to_server"] is True
            assert config_dict["autosave_server_url"] == "http://test.com"
            assert config_dict["autosave_auth_type"] == "api_token"
            assert config_dict["autosave_api_token"] == "test_token"
            assert config_dict["autosave_connection_timeout"] == 60
            assert config_dict["enabled"] is False
    
    def test_config_from_dict_empty(self) -> None:
        """Test config from_dict method with empty dictionary."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config = AutosaveAddonConfig.from_dict({})
            
            # Should use default values
            assert config.autosave_pdf_2 is False
            assert config.autosave_server_url == "http://localhost:5101"
            assert config.autosave_auth_type == "none"
            assert config.enabled is True
    
    def test_config_from_dict_partial(self) -> None:
        """Test config from_dict method with partial data."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config_data = {
                "autosave_pdf_2": True,
                "autosave_path_2": "/test/path",
                "autosave_upload_to_server": True,
                "autosave_server_url": "http://test.com",
                "autosave_auth_type": "api_token",
                "autosave_api_token": "test_token"
            }
            
            config = AutosaveAddonConfig.from_dict(config_data)
            
            # Check set values
            assert config.autosave_pdf_2 is True
            assert config.autosave_path_2 == "/test/path"
            assert config.autosave_upload_to_server is True
            assert config.autosave_server_url == "http://test.com"
            assert config.autosave_auth_type == "api_token"
            assert config.autosave_api_token == "test_token"
            
            # Check default values for unset fields
            assert config.autosave_pdf_3 is False
            assert config.autosave_image_type_2 == "PDF"
            assert config.autosave_connection_timeout == 30
    
    def test_config_from_dict_health_url_backward_compatibility(self) -> None:
        """Test config from_dict method handles missing health_url."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config_data = {
                "autosave_server_url": "http://test.com:8080"
            }
            
            config = AutosaveAddonConfig.from_dict(config_data)
            
            assert config.autosave_health_url == "http://test.com:8080/api/files/health"
    
    def test_config_from_dict_health_url_backward_compatibility_with_trailing_slash(self) -> None:
        """Test config from_dict method handles missing health_url with trailing slash."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config_data = {
                "autosave_server_url": "http://test.com:8080/"
            }
            
            config = AutosaveAddonConfig.from_dict(config_data)
            
            assert config.autosave_health_url == "http://test.com:8080/api/files/health"
    
    def test_config_from_dict_existing_health_url(self) -> None:
        """Test config from_dict method preserves existing health_url."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config_data = {
                "autosave_server_url": "http://test.com:8080",
                "autosave_health_url": "http://custom.com/health"
            }
            
            config = AutosaveAddonConfig.from_dict(config_data)
            
            assert config.autosave_health_url == "http://custom.com/health"
    
    def test_config_roundtrip_serialization(self) -> None:
        """Test config can be serialized and deserialized correctly."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            # Create original config with custom values
            original_config = AutosaveAddonConfig()
            original_config.autosave_pdf_2 = True
            original_config.autosave_path_2 = "/test/path"
            original_config.autosave_upload_to_server = True
            original_config.autosave_server_url = "http://test.com"
            original_config.autosave_auth_type = "jwt"
            original_config.autosave_jwt_token = "test_jwt"
            original_config.autosave_connection_timeout = 45
            original_config.autosave_retry_attempts = 5
            original_config.enabled = False
            
            # Serialize to dict
            config_dict = original_config.to_dict()
            
            # Deserialize from dict
            restored_config = AutosaveAddonConfig.from_dict(config_dict)
            
            # Verify all values match
            assert restored_config.autosave_pdf_2 == original_config.autosave_pdf_2
            assert restored_config.autosave_path_2 == original_config.autosave_path_2
            assert restored_config.autosave_upload_to_server == original_config.autosave_upload_to_server
            assert restored_config.autosave_server_url == original_config.autosave_server_url
            assert restored_config.autosave_auth_type == original_config.autosave_auth_type
            assert restored_config.autosave_jwt_token == original_config.autosave_jwt_token
            assert restored_config.autosave_connection_timeout == original_config.autosave_connection_timeout
            assert restored_config.autosave_retry_attempts == original_config.autosave_retry_attempts
            assert restored_config.enabled == original_config.enabled


class TestAutosaveAddonConfigFileIO:
    """Test AutosaveAddonConfig file I/O operations."""
    
    def test_load_from_file_existing(self) -> None:
        """Test load_from_file with existing file."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }), tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            # Write test config to file
            config_data = {
                "autosave_pdf_2": True,
                "autosave_path_2": "/test/path",
                "autosave_upload_to_server": True,
                "autosave_server_url": "http://test.com",
                "autosave_auth_type": "api_token",
                "autosave_api_token": "test_token"
            }
            json.dump(config_data, temp_file)
            temp_file.flush()
            
            # Load config from file
            config = AutosaveAddonConfig.load_from_file(temp_file.name)
            
            assert config.autosave_pdf_2 is True
            assert config.autosave_path_2 == "/test/path"
            assert config.autosave_upload_to_server is True
            assert config.autosave_server_url == "http://test.com"
            assert config.autosave_auth_type == "api_token"
            assert config.autosave_api_token == "test_token"
            
            # Cleanup
            Path(temp_file.name).unlink()
    
    def test_load_from_file_nonexistent(self) -> None:
        """Test load_from_file with nonexistent file."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            # Load config from nonexistent file
            config = AutosaveAddonConfig.load_from_file("/nonexistent/path/config.json")
            
            # Should return default config
            assert config.autosave_pdf_2 is False
            assert config.autosave_server_url == "http://localhost:5101"
            assert config.autosave_auth_type == "none"
            assert config.enabled is True
    
    def test_load_from_file_none_path(self) -> None:
        """Test load_from_file with None path uses default."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }), patch('pathlib.Path.home') as mock_home, patch('pathlib.Path.mkdir') as mock_mkdir, patch('pathlib.Path.exists', return_value=False):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            mock_home.return_value = Path("/home/user")
            
            # Load config with None path
            config = AutosaveAddonConfig.load_from_file(None)
            
            # Should return default config
            assert config.autosave_pdf_2 is False
            assert config.autosave_server_url == "http://localhost:5101"
            assert config.enabled is True
            
            # Verify default path was used
            mock_mkdir.assert_called_once()
    
    def test_load_from_file_corrupted_json(self) -> None:
        """Test load_from_file with corrupted JSON file."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }), tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            # Write corrupted JSON
            temp_file.write('{"invalid": json}')
            temp_file.flush()
            
            # Load config from corrupted file
            config = AutosaveAddonConfig.load_from_file(temp_file.name)
            
            # Should return default config
            assert config.autosave_pdf_2 is False
            assert config.autosave_server_url == "http://localhost:5101"
            assert config.enabled is True
            
            # Cleanup
            Path(temp_file.name).unlink()
    
    def test_save_to_file_success(self) -> None:
        """Test save_to_file method success."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }), tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config = AutosaveAddonConfig()
            config.autosave_pdf_2 = True
            config.autosave_path_2 = "/test/path"
            config.autosave_upload_to_server = True
            config.autosave_server_url = "http://test.com"
            config.autosave_auth_type = "jwt"
            config.autosave_jwt_token = "test_jwt"
            
            # Save config to file
            result = config.save_to_file(temp_file.name)
            
            assert result is True
            
            # Verify file was written correctly
            with open(temp_file.name, 'r') as f:
                saved_data = json.load(f)
                
            assert saved_data["autosave_pdf_2"] is True
            assert saved_data["autosave_path_2"] == "/test/path"
            assert saved_data["autosave_upload_to_server"] is True
            assert saved_data["autosave_server_url"] == "http://test.com"
            assert saved_data["autosave_auth_type"] == "jwt"
            assert saved_data["autosave_jwt_token"] == "test_jwt"
            
            # Cleanup
            Path(temp_file.name).unlink()
    
    def test_save_to_file_none_path(self) -> None:
        """Test save_to_file with None path uses default."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }), patch('pathlib.Path.home') as mock_home, patch('pathlib.Path.mkdir') as mock_mkdir, patch('builtins.open', mock_open()) as mock_file:
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            mock_home.return_value = Path("/home/user")
            
            config = AutosaveAddonConfig()
            config.autosave_pdf_2 = True
            
            # Save config with None path
            result = config.save_to_file(None)
            
            assert result is True
            mock_mkdir.assert_called_once()
            mock_file.assert_called_once() # currently failing---being called twice
    
    def test_save_to_file_permission_error(self) -> None:
        """Test save_to_file with permission error."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }), patch('builtins.open', side_effect=PermissionError("Permission denied")):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config = AutosaveAddonConfig()
            
            # Save config with permission error
            result = config.save_to_file("/readonly/path/config.json")
            
            assert result is False
    
    def test_save_to_file_json_error(self) -> None:
        """Test save_to_file with JSON serialization error."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }), patch('json.dump', side_effect=TypeError("Not JSON serializable")):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config = AutosaveAddonConfig()
            
            # Save config with JSON error
            result = config.save_to_file("/test/path/config.json")
            
            assert result is False


class TestAutosaveAddonConfigEdgeCases:
    """Test AutosaveAddonConfig edge cases and error handling."""
    
    def test_config_with_invalid_auth_type(self) -> None:
        """Test config handles invalid auth type."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config_data = {
                "autosave_auth_type": "invalid_auth_type"
            }
            
            config = AutosaveAddonConfig.from_dict(config_data)
            
            # Should accept any string value
            assert config.autosave_auth_type == "invalid_auth_type"
    
    def test_config_with_negative_timeout(self) -> None:
        """Test config handles negative timeout values."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config_data = {
                "autosave_connection_timeout": -1,
                "autosave_retry_attempts": -5,
                "autosave_retry_delay": -10
            }
            
            config = AutosaveAddonConfig.from_dict(config_data)
            
            # Should accept negative values (validation would be in higher layer)
            assert config.autosave_connection_timeout == -1
            assert config.autosave_retry_attempts == -5
            assert config.autosave_retry_delay == -10
    
    def test_config_with_very_large_values(self) -> None:
        """Test config handles very large values."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config_data = {
                "autosave_connection_timeout": 999999,
                "autosave_retry_attempts": 1000,
                "autosave_retry_delay": 3600,
                "autosave_health_check_interval": 86400
            }
            
            config = AutosaveAddonConfig.from_dict(config_data)
            
            assert config.autosave_connection_timeout == 999999
            assert config.autosave_retry_attempts == 1000
            assert config.autosave_retry_delay == 3600
            assert config.autosave_health_check_interval == 86400
    
    def test_config_with_unicode_paths(self) -> None:
        """Test config handles unicode paths."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            unicode_path = "/test/路径/with/unicode/测试"
            config_data = {
                "autosave_path_2": unicode_path,
                "autosave_path_3": unicode_path,
                "autosave_server_url": "http://测试.com"
            }
            
            config = AutosaveAddonConfig.from_dict(config_data)
            
            assert config.autosave_path_2 == unicode_path
            assert config.autosave_path_3 == unicode_path
            assert config.autosave_server_url == "http://测试.com"
    
    def test_config_with_empty_strings(self) -> None:
        """Test config handles empty string values."""
        with patch.dict('sys.modules', {
            'logging': Mock(getLogger=Mock(return_value=Mock())),
        }):
            from artisanlib.plugins.autosave.config import AutosaveAddonConfig
            
            config_data = {
                "autosave_path_2": "",
                "autosave_path_3": "",
                "autosave_server_url": "",
                "autosave_api_token": "",
                "autosave_jwt_token": "",
                "autosave_auth_type": ""
            }
            
            config = AutosaveAddonConfig.from_dict(config_data)
            
            assert config.autosave_path_2 == ""
            assert config.autosave_path_3 == ""
            assert config.autosave_server_url == ""
            assert config.autosave_api_token == ""
            assert config.autosave_jwt_token == ""
            assert config.autosave_auth_type == ""


@pytest.mark.parametrize(
    'config_data,expected_values',
    [
        # Test case 1: Empty config
        ({}, {
            'autosave_pdf_2': False,
            'autosave_server_url': 'http://localhost:5101',
            'autosave_auth_type': 'none',
            'enabled': True
        }),
        # Test case 2: Partial config
        ({
            'autosave_pdf_2': True,
            'autosave_path_2': '/test/path',
            'autosave_upload_to_server': True
        }, {
            'autosave_pdf_2': True,
            'autosave_path_2': '/test/path',
            'autosave_upload_to_server': True,
            'autosave_pdf_3': False,  # Should remain default
            'autosave_auth_type': 'none'  # Should remain default
        }),
        # Test case 3: Full config
        ({
            'autosave_pdf_2': True,
            'autosave_pdf_3': True,
            'autosave_upload_to_server': True,
            'autosave_server_url': 'http://custom.com',
            'autosave_auth_type': 'api_token',
            'autosave_api_token': 'token123',
            'autosave_connection_timeout': 60,
            'enabled': False
        }, {
            'autosave_pdf_2': True,
            'autosave_pdf_3': True,
            'autosave_upload_to_server': True,
            'autosave_server_url': 'http://custom.com',
            'autosave_auth_type': 'api_token',
            'autosave_api_token': 'token123',
            'autosave_connection_timeout': 60,
            'enabled': False
        }),
    ],
)
def test_config_from_dict_parametrized(
    config_data: Dict[str, Any], 
    expected_values: Dict[str, Any]
) -> None:
    """Test config from_dict method with various data combinations."""
    with patch.dict('sys.modules', {
        'logging': Mock(getLogger=Mock(return_value=Mock())),
    }):
        from artisanlib.plugins.autosave.config import AutosaveAddonConfig
        
        config = AutosaveAddonConfig.from_dict(config_data)
        
        for key, expected_value in expected_values.items():
            assert getattr(config, key) == expected_value


@pytest.mark.parametrize(
    'server_url,expected_health_url',
    [
        ('http://localhost:5101', 'http://localhost:5101/api/files/health'),
        ('http://localhost:5101/', 'http://localhost:5101/api/files/health'),
        ('https://api.example.com', 'https://api.example.com/api/files/health'),
        ('https://api.example.com/', 'https://api.example.com/api/files/health'),
        ('http://192.168.1.100:8080', 'http://192.168.1.100:8080/api/files/health'),
        ('http://192.168.1.100:8080/', 'http://192.168.1.100:8080/api/files/health'),
    ],
)
def test_health_url_backward_compatibility_parametrized(
    server_url: str, 
    expected_health_url: str
) -> None:
    """Test health URL backward compatibility with various server URLs."""
    with patch.dict('sys.modules', {
        'logging': Mock(getLogger=Mock(return_value=Mock())),
    }):
        from artisanlib.plugins.autosave.config import AutosaveAddonConfig
        
        config_data = {
            "autosave_server_url": server_url
        }
        
        config = AutosaveAddonConfig.from_dict(config_data)
        
        assert config.autosave_health_url == expected_health_url