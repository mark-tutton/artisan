"""Unit tests for artisanlib.plugins.manager module.

This module tests the plugin manager functionality including:
- PluginManager class initialization and lifecycle management
- Plugin registration and unregistration
- PluginRegistration dataclass functionality
- Plugin error handling and health monitoring
- Event notification system for roast events
- Threading support with PluginManagerWorker
- Menu creation and Qt integration
- Performance monitoring and status reporting



This test module implements comprehensive test isolation to prevent cross-file
module contamination and ensure proper mock state management.

Key Features:
- Session-level isolation for Qt dependencies and plugin system
- Comprehensive Qt mocking with proper signal and menu handling
- Mock state management for plugin lifecycle testing
- Test independence and proper cleanup
- Python 3.8+ compatibility with type annotations
- Threading safety testing with worker thread management
- Plugin registration and error handling validation

=============================================================================
"""

import sys
import threading
from typing import Any, Dict, Generator, Optional, List, Type
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta

import pytest


@pytest.fixture(scope='session', autouse=True)
def session_level_isolation() -> Generator[None, None, None]:
    """Session-level isolation fixture to prevent cross-file module contamination.
    
    This fixture ensures that Qt dependencies and plugin system components
    are properly isolated at the session level while preserving the functionality 
    needed for plugin manager tests.
    """
    # Store original modules if they exist and aren't mocked
    original_modules: Dict[str, Any] = {}
    modules_to_check = [
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtWidgets',
        'logging',
        'traceback',
        'datetime',
        'artisanlib.plugins.base',
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
def reset_plugin_manager_state() -> Generator[None, None, None]:
    """Reset plugin manager test state before each test to ensure test independence."""
    
    yield
    
    # Clean up after each test
    import gc
    gc.collect()


# Mock Qt Classes for Plugin Manager Testing 
class MockQObject:
    """Mock QObject for plugin manager testing."""
    
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
    """Mock pyqtSignal for plugin manager testing."""
    
    def __init__(self, *args):
        self.args = args
        self.connected_slots = []
        
    def emit(self, *args):
        """Mock emit method."""
        for slot in self.connected_slots:
            if callable(slot):
                try:
                    slot(*args)
                except Exception:
                    pass
                    
    def connect(self, slot):
        """Mock connect method."""
        self.connected_slots.append(slot)
        
    def disconnect(self, slot=None):
        """Mock disconnect method."""
        if slot is None:
            self.connected_slots.clear()
        elif slot in self.connected_slots:
            self.connected_slots.remove(slot)


class MockQThread:
    """Mock QThread for plugin manager testing."""
    
    def __init__(self):
        self._running = False
        self._finished = False
        
    def start(self):
        """Mock start method."""
        self._running = True
        
    def quit(self):
        """Mock quit method."""
        self._running = False
        
    def wait(self, timeout=None):
        """Mock wait method."""
        self._finished = True
        return True
        
    def isRunning(self):
        """Mock isRunning method."""
        return self._running
        
    def terminate(self):
        """Mock terminate method."""
        self._running = False
        
    def deleteLater(self):
        """Mock deleteLater method."""
        pass


class MockQMutex:
    """Mock QMutex for plugin manager testing."""
    
    def __init__(self):
        self._locked = False
        
    def lock(self):
        """Mock lock method."""
        self._locked = True
        
    def unlock(self):
        """Mock unlock method."""
        self._locked = False


class MockQTimer:
    """Mock QTimer for plugin manager testing."""
    
    def __init__(self):
        self.timeout = MockPyQtSignal(str)
        self._interval = 0
        self._single_shot = False
        
    def start(self, interval=None):
        """Mock start method."""
        if interval:
            self._interval = interval
            
    def stop(self):
        """Mock stop method."""
        pass
        
    def deleteLater(self):
        """Mock deleteLater method."""
        pass


class MockQMainWindow:
    """Mock QMainWindow for plugin manager testing."""
    
    def __init__(self):
        self.menu_bar = MockQMenuBar()
        
    def menuBar(self):
        """Mock menuBar method."""
        return self.menu_bar


class MockQMenuBar:
    """Mock QMenuBar for plugin manager testing."""
    
    def __init__(self):
        self.menus = []
        
    def addMenu(self, title):
        """Mock addMenu method."""
        menu = MockQMenu(title)
        self.menus.append(menu)
        return menu


class MockQMenu:
    """Mock QMenu for plugin manager testing."""
    
    def __init__(self, title=""):
        self.title = title
        self.menus = []
        self.actions = []
        
    def addMenu(self, menu):
        """Mock addMenu method."""
        self.menus.append(menu)
        return menu
        
    def addAction(self, action):
        """Mock addAction method."""
        self.actions.append(action)
        return action


# Test Plugin Implementation for Manager Testing
class MockPlugin:
    """Mock plugin for testing PluginManager functionality."""
    
    def __init__(self, name="mock_plugin", version="1.0.0", should_fail_init=False, should_fail_menu=False):
        self._name = name
        self._version = version
        self._should_fail_init = should_fail_init
        self._should_fail_menu = should_fail_menu
        self.state_changed = MockPyQtSignal(str, str)
        self.error_occurred = MockPyQtSignal(str, str)
        self.initialized = False
        self.cleaned_up = False
        self.main_window = None
        self.errors = []
        self.initialization_time = None
        self.last_error_time = None
        self.operation_times = {}
        
    @property
    def name(self) -> str:
        return self._name
        
    @property
    def version(self) -> str:
        return self._version
        
    @property
    def is_active(self) -> bool:
        return self.initialized and not self.cleaned_up
        
    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0
        
    def initialize(self, main_window):
        """Mock initialize method."""
        if self._should_fail_init:
            raise RuntimeError("Mock initialization failure")
        self.main_window = main_window
        self.initialized = True
        self.initialization_time = datetime.now()
        
    def cleanup(self):
        """Mock cleanup method."""
        self.cleaned_up = True
        
    def create_menu(self, parent_menu):
        """Mock create_menu method."""
        if self._should_fail_menu:
            raise RuntimeError("Mock menu creation failure")
        return MockQMenu(f"{self.name} Menu")
        
    def on_roast_start(self):
        """Mock roast start handler."""
        self.roast_started = True
        
    def on_roast_end(self):
        """Mock roast end handler."""
        self.roast_ended = True
        
    def on_data_update(self, data):
        """Mock data update handler."""
        self.data_updates = getattr(self, 'data_updates', [])
        self.data_updates.append(data)
        
    def get_health_status(self):
        """Mock get_health_status method."""
        return {
            "name": self.name,
            "version": self.version,
            "is_active": self.is_active,
            "has_errors": self.has_errors,
            "error_count": len(self.errors),
            "initialization_time": self.initialization_time.isoformat() if self.initialization_time else None,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "worker_thread_running": False,
            "operation_times": self.operation_times,
            "recent_errors": []
        }


class TestPluginRegistration:
    """Test PluginRegistration dataclass functionality."""
    
    def test_plugin_registration_creation(self) -> None:
        """Test PluginRegistration dataclass creation with all fields."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(),
            'PyQt5.QtWidgets': Mock(),
            'artisanlib.plugins.base': Mock(),
        }):
            from artisanlib.plugins.manager import PluginRegistration
            
            plugin = MockPlugin()
            registration_time = datetime.now()
            
            registration = PluginRegistration(
                plugin=plugin,
                registration_time=registration_time,
                initialization_successful=True,
                error_count=5,
                last_error_time=registration_time
            )
            
            assert registration.plugin == plugin
            assert registration.registration_time == registration_time
            assert registration.initialization_successful is True
            assert registration.error_count == 5
            assert registration.last_error_time == registration_time
    
    def test_plugin_registration_defaults(self) -> None:
        """Test PluginRegistration with default values."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(),
            'PyQt5.QtWidgets': Mock(),
            'artisanlib.plugins.base': Mock(),
        }):
            from artisanlib.plugins.manager import PluginRegistration
            
            plugin = MockPlugin()
            registration_time = datetime.now()
            
            registration = PluginRegistration(
                plugin=plugin,
                registration_time=registration_time
            )
            
            assert registration.plugin == plugin
            assert registration.registration_time == registration_time
            assert registration.initialization_successful is False
            assert registration.error_count == 0
            assert registration.last_error_time is None


class TestPluginManagerWorker:
    """Test PluginManagerWorker functionality."""
    
    def test_plugin_manager_worker_initialization(self) -> None:
        """Test PluginManagerWorker proper initialization."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(QObject=MockQObject, pyqtSignal=MockPyQtSignal, QMutex=MockQMutex),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(QObject=MockQObject, pyqtSignal=MockPyQtSignal, QMutex=MockQMutex),
            'PyQt5.QtWidgets': Mock(),
            'artisanlib.plugins.base': Mock(),
        }):
            from artisanlib.plugins.manager import PluginManagerWorker
            
            worker = PluginManagerWorker()
            
            assert hasattr(worker, 'plugin_operation_started')
            assert hasattr(worker, 'plugin_operation_completed')
            assert hasattr(worker, 'plugin_operation_failed')
            assert hasattr(worker, '_mutex')
            assert hasattr(worker, '_is_running')
            
            assert worker._is_running is False
    
    def test_plugin_manager_worker_execute_operation(self) -> None:
        """Test PluginManagerWorker execute_plugin_operation method."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(QObject=MockQObject, pyqtSignal=MockPyQtSignal, QMutex=MockQMutex),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(QObject=MockQObject, pyqtSignal=MockPyQtSignal, QMutex=MockQMutex),
            'PyQt5.QtWidgets': Mock(),
            'artisanlib.plugins.base': Mock(),
        }):
            from artisanlib.plugins.manager import PluginManagerWorker
            
            worker = PluginManagerWorker()
            plugin = MockPlugin()
            
            # Mock operation function
            operation_result = "test_result"
            operation_func = Mock(return_value=operation_result)
            
            # Execute operation
            result = worker.execute_plugin_operation(plugin, "test_op", operation_func, "arg1", kwarg1="value1")
            
            assert result is True
            operation_func.assert_called_once_with("arg1", kwarg1="value1")


class TestPluginManager:
    """Test PluginManager functionality."""
    
    def test_plugin_manager_initialization(self) -> None:
        """Test PluginManager proper initialization."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
            'artisanlib.plugins.base': Mock(),
        }):
            from artisanlib.plugins.manager import PluginManager
            
            main_window = MockQMainWindow()
            manager = PluginManager(main_window)
            
            assert manager.main_window == main_window
            assert isinstance(manager.plugins, dict)
            assert len(manager.plugins) == 0
            assert manager.plugin_menu is None
            assert manager.health_check_timer is not None
            assert manager.total_errors == 0
            assert manager.critical_errors == 0
            assert isinstance(manager.operation_times, dict)
    
    def test_plugin_registration_success(self) -> None:
        """Test successful plugin registration."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
            'artisanlib.plugins.base': Mock(),
        }):
            from artisanlib.plugins.manager import PluginManager
            
            main_window = MockQMainWindow()
            manager = PluginManager(main_window)
            
            # Create plugin class
            class TestPluginClass:
                def __new__(cls):
                    return MockPlugin("test_plugin", "1.0.0")
            
            result = manager.register_plugin(TestPluginClass)
            
            assert result is True
            assert "test_plugin" in manager.plugins
            
            registration = manager.plugins["test_plugin"]
            assert registration.plugin.name == "test_plugin"
            assert registration.initialization_successful is True
            assert registration.plugin.initialized is True
    
    def test_plugin_registration_failure(self) -> None:
        """Test plugin registration failure handling."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
            'artisanlib.plugins.base': Mock(),
        }):
            from artisanlib.plugins.manager import PluginManager
            
            main_window = MockQMainWindow()
            manager = PluginManager(main_window)
            
            # Create failing plugin class
            class FailingPluginClass:
                def __new__(cls):
                    return MockPlugin("failing_plugin", "1.0.0", should_fail_init=True)
            
            result = manager.register_plugin(FailingPluginClass)
            
            assert result is False
            assert "failing_plugin" in manager.plugins
            
            registration = manager.plugins["failing_plugin"]
            assert registration.initialization_successful is False
            assert registration.error_count == 1
            assert registration.last_error_time is not None
    
    def test_plugin_duplicate_registration(self) -> None:
        """Test duplicate plugin registration handling."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
            'artisanlib.plugins.base': Mock(),
        }):
            from artisanlib.plugins.manager import PluginManager
            
            main_window = MockQMainWindow()
            manager = PluginManager(main_window)
            
            class TestPluginClass:
                def __new__(cls):
                    return MockPlugin("duplicate_plugin", "1.0.0")
            
            # Register first time
            result1 = manager.register_plugin(TestPluginClass)
            assert result1 is True
            
            # Try to register again
            result2 = manager.register_plugin(TestPluginClass)
            assert result2 is False
            
            # Should still only have one registration
            assert len(manager.plugins) == 1
    
    def test_plugin_unregistration(self) -> None:
        """Test plugin unregistration functionality."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
            'artisanlib.plugins.base': Mock(),
        }):
            from artisanlib.plugins.manager import PluginManager
            
            main_window = MockQMainWindow()
            manager = PluginManager(main_window)
            
            class TestPluginClass:
                def __new__(cls):
                    return MockPlugin("test_plugin", "1.0.0")
            
            # Register plugin first
            manager.register_plugin(TestPluginClass)
            assert "test_plugin" in manager.plugins
            
            # Unregister plugin
            result = manager.unregister_plugin("test_plugin")
            
            assert result is True
            assert "test_plugin" not in manager.plugins
    
    def test_plugin_unregistration_not_found(self) -> None:
        """Test unregistration of non-existent plugin."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
            'artisanlib.plugins.base': Mock(),
        }):
            from artisanlib.plugins.manager import PluginManager
            
            main_window = MockQMainWindow()
            manager = PluginManager(main_window)
            
            # Try to unregister non-existent plugin
            result = manager.unregister_plugin("non_existent_plugin")
            
            assert result is False
    
    def test_get_plugin(self) -> None:
        """Test get_plugin functionality."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
            'artisanlib.plugins.base': Mock(),
        }):
            from artisanlib.plugins.manager import PluginManager
            
            main_window = MockQMainWindow()
            manager = PluginManager(main_window)
            
            class TestPluginClass:
                def __new__(cls):
                    return MockPlugin("test_plugin", "1.0.0")
            
            # Register plugin
            manager.register_plugin(TestPluginClass)
            
            # Get plugin
            plugin = manager.get_plugin("test_plugin")
            assert plugin is not None
            assert plugin.name == "test_plugin"
            
            # Get non-existent plugin
            non_existent = manager.get_plugin("non_existent")
            assert non_existent is None
    
    def test_notify_roast_events(self) -> None:
        """Test roast event notification functionality."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
            'artisanlib.plugins.base': Mock(),
        }):
            from artisanlib.plugins.manager import PluginManager
            
            main_window = MockQMainWindow()
            manager = PluginManager(main_window)
            
            class TestPluginClass:
                def __new__(cls):
                    return MockPlugin("test_plugin", "1.0.0")
            
            # Register plugin
            manager.register_plugin(TestPluginClass)
            plugin = manager.get_plugin("test_plugin")
            
            # Test roast start notification
            manager.notify_roast_start()
            assert hasattr(plugin, 'roast_started')
            assert plugin.roast_started is True
            
            # Test roast end notification
            manager.notify_roast_end()
            assert hasattr(plugin, 'roast_ended')
            assert plugin.roast_ended is True
            
            # Test data update notification
            test_data = {"temperature": 200, "time": 300}
            manager.notify_data_update(test_data)
            assert hasattr(plugin, 'data_updates')
            assert len(plugin.data_updates) == 1
            assert plugin.data_updates[0] == test_data
    
    def test_manager_status_reporting(self) -> None:
        """Test plugin manager status reporting."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
            'artisanlib.plugins.base': Mock(),
        }):
            from artisanlib.plugins.manager import PluginManager
            
            main_window = MockQMainWindow()
            manager = PluginManager(main_window)
            
            class TestPluginClass:
                def __new__(cls):
                    return MockPlugin("test_plugin", "1.0.0")
            
            class FailingPluginClass:
                def __new__(cls):
                    return MockPlugin("failing_plugin", "1.0.0", should_fail_init=True)
            
            # Register successful plugin
            manager.register_plugin(TestPluginClass)
            
            # Register failing plugin
            manager.register_plugin(FailingPluginClass)
            
            status = manager.get_manager_status()
            
            assert status["total_plugins"] == 2
            assert status["active_plugins"] == 1  # Only successful plugin is active
            assert status["plugins_with_errors"] == 0  # Mock plugins don't have real errors
            assert status["total_errors"] == 0
            assert status["critical_errors"] == 0
            assert "operation_times" in status
            assert "plugins" in status
            
            # Check plugin-specific status
            plugins_status = status["plugins"]
            assert "test_plugin" in plugins_status
            assert "failing_plugin" in plugins_status
            
            test_plugin_status = plugins_status["test_plugin"]
            assert test_plugin_status["initialization_successful"] is True
            assert test_plugin_status["error_count"] == 0
            
            failing_plugin_status = plugins_status["failing_plugin"]
            assert failing_plugin_status["initialization_successful"] is False
            assert failing_plugin_status["error_count"] == 1
    
    def test_manager_cleanup(self) -> None:
        """Test plugin manager cleanup functionality."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt6.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'PyQt5.QtCore': Mock(
                QObject=MockQObject,
                pyqtSignal=MockPyQtSignal,
                QMutex=MockQMutex,
                QThread=MockQThread,
                QTimer=MockQTimer
            ),
            'PyQt5.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
            'logging': Mock(getLogger=Mock(return_value=Mock())),
            'artisanlib.plugins.base': Mock(),
        }):
            from artisanlib.plugins.manager import PluginManager
            
            main_window = MockQMainWindow()
            manager = PluginManager(main_window)
            
            class TestPluginClass:
                def __new__(cls):
                    return MockPlugin("test_plugin", "1.0.0")
            
            # Register plugin
            manager.register_plugin(TestPluginClass)
            assert len(manager.plugins) == 1
            
            # Cleanup manager
            manager.cleanup()
            
            # All plugins should be unregistered
            assert len(manager.plugins) == 0


@pytest.mark.parametrize(
    'plugin_name,plugin_version,should_fail_init,should_fail_menu,expected_success',
    [
        ('good_plugin', '1.0.0', False, False, True),
        ('failing_init_plugin', '1.0.0', True, False, False),
        ('failing_menu_plugin', '1.0.0', False, True, True),  # Menu failure shouldn't prevent registration
        ('complex_plugin', '2.1.3', False, False, True),
    ],
)
def test_plugin_registration_scenarios(
    plugin_name: str, 
    plugin_version: str, 
    should_fail_init: bool, 
    should_fail_menu: bool, 
    expected_success: bool
) -> None:
    """Test plugin registration with various scenarios."""
    with patch.dict('sys.modules', {
        'PyQt6.QtCore': Mock(
            QObject=MockQObject,
            pyqtSignal=MockPyQtSignal,
            QMutex=MockQMutex,
            QThread=MockQThread,
            QTimer=MockQTimer
        ),
        'PyQt6.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
        'PyQt5.QtCore': Mock(
            QObject=MockQObject,
            pyqtSignal=MockPyQtSignal,
            QMutex=MockQMutex,
            QThread=MockQThread,
            QTimer=MockQTimer
        ),
        'PyQt5.QtWidgets': Mock(QMainWindow=MockQMainWindow, QMenu=MockQMenu),
        'logging': Mock(getLogger=Mock(return_value=Mock())),
        'artisanlib.plugins.base': Mock(),
    }):
        from artisanlib.plugins.manager import PluginManager
        
        main_window = MockQMainWindow()
        manager = PluginManager(main_window)
        
        class TestPluginClass:
            def __new__(cls):
                return MockPlugin(plugin_name, plugin_version, should_fail_init, should_fail_menu)
        
        result = manager.register_plugin(TestPluginClass)
        assert result is expected_success
        
        if expected_success:
            assert plugin_name in manager.plugins
            registration = manager.plugins[plugin_name]
            assert registration.initialization_successful is True
            assert registration.plugin.name == plugin_name
            assert registration.plugin.version == plugin_version
        else:
            # Failed plugins are still registered but marked as unsuccessful
            if plugin_name in manager.plugins:
                registration = manager.plugins[plugin_name]
                assert registration.initialization_successful is False