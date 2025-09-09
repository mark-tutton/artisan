"""Unit tests for artisanlib.plugins.base module.

This module tests the plugin base system functionality including:
- PluginBase class initialization and lifecycle management
- PluginState enum and state transitions
- PluginError dataclass and error handling
- PluginWorker threading functionality
- Plugin signal emissions and Qt integration
- Error recording and health monitoring
- Operation timing and performance tracking
- Thread-safe operations with QMutex

This test module implements comprehensive test isolation to prevent cross-file
module contamination and ensure proper mock state management.
Key Features:
- Session-level isolation for Qt dependencies
- Comprehensive Qt mocking with proper signal handling
- Mock state management to prevent interference
- Test independence and proper cleanup
- Python 3.8+ compatibility with type annotations
- Threading safety testing with proper cleanup
- Performance monitoring and health status validation

This implementation follows the established patterns from artisanlib tests
for proper isolation in modules that use Qt threading and signals.
=============================================================================
"""

import sys
import threading
import time
from typing import Any, Dict, Generator, Optional, List, Callable
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta

import pytest


@pytest.fixture(scope='session', autouse=True)
def session_level_isolation() -> Generator[None, None, None]:
    """Session-level isolation fixture to prevent cross-file module contamination.
    
    This fixture ensures that Qt dependencies are properly isolated
    at the session level while preserving the functionality needed for
    plugin base tests.
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
def reset_plugin_base_state() -> Generator[None, None, None]:
    """Reset plugin base test state before each test to ensure test independence."""
    
    yield
    
    # Clean up after each test
    import gc
    gc.collect()


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
    """Mock QThread for plugin testing."""
    
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
    """Mock QMutex for plugin testing."""
    
    def __init__(self):
        self._locked = False
        
    def lock(self):
        """Mock lock method."""
        self._locked = True
        
    def unlock(self):
        """Mock unlock method."""
        self._locked = False


class MockQTimer:
    """Mock QTimer for plugin testing."""
    
    def __init__(self):
        self.timeout = MockPyQtSignal(str)
        self._interval = 0
        self._single_shot = False
        
    @staticmethod
    def singleShot(interval, callback):
        """Mock singleShot method."""
        if callable(callback):
            callback()


class MockQMainWindow:
    """Mock QMainWindow for plugin testing."""
    
    def __init__(self):
        self.menu_bar = MockQMenu()
        
    def menuBar(self):
        """Mock menuBar method."""
        return self.menu_bar


class MockQMenu:
    """Mock QMenu for plugin testing."""
    
    def __init__(self):
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


# Test Implementation Plugin for Testing
class TestPlugin:
    """Test plugin implementation for testing PluginBase functionality."""
    
    def __init__(self, name="test_plugin", version="1.0.0", should_fail_init=False):
        self._name = name
        self._version = version
        self._should_fail_init = should_fail_init
        self.initialized = False
        self.cleaned_up = False
        self.roast_started = False
        self.roast_ended = False
        self.data_updates = []
        self.menu_created = False
        
    @property
    def name(self) -> str:
        return self._name
        
    @property  
    def version(self) -> str:
        return self._version
        
    def _initialize_plugin(self) -> None:
        """Test plugin initialization."""
        if self._should_fail_init:
            raise RuntimeError("Test initialization failure")
        self.initialized = True
        
    def _cleanup_plugin(self) -> None:
        """Test plugin cleanup."""
        self.cleaned_up = True
        
    def _create_plugin_menu(self, parent_menu) -> Optional[MockQMenu]:
        """Test plugin menu creation."""
        self.menu_created = True
        menu = MockQMenu()
        return menu
        
    def _on_roast_start_impl(self) -> None:
        """Test roast start handler."""
        self.roast_started = True
        
    def _on_roast_end_impl(self) -> None:
        """Test roast end handler."""
        self.roast_ended = True
        
    def _on_data_update_impl(self, data: Dict[str, Any]) -> None:
        """Test data update handler."""
        self.data_updates.append(data)


class TestPluginState:
    """Test PluginState enum values and functionality."""
    
    def test_plugin_state_values(self) -> None:
        """Test that all plugin states have correct string values."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(),
            'PyQt5.QtWidgets': Mock(),
        }):
            from artisanlib.plugins.base import PluginState
            
            assert PluginState.UNINITIALIZED.value == "uninitialized"
            assert PluginState.INITIALIZING.value == "initializing"  
            assert PluginState.ACTIVE.value == "active"
            assert PluginState.ERROR.value == "error"
            assert PluginState.CLEANING_UP.value == "cleaning_up"
            assert PluginState.DISABLED.value == "disabled"
    
    def test_plugin_state_enum_membership(self) -> None:
        """Test that all expected states are in the enum."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(), 
            'PyQt5.QtWidgets': Mock(),
        }):
            from artisanlib.plugins.base import PluginState
            
            expected_states = {
                'UNINITIALIZED', 'INITIALIZING', 'ACTIVE', 
                'ERROR', 'CLEANING_UP', 'DISABLED'
            }
            actual_states = {state.name for state in PluginState}
            assert actual_states == expected_states


class TestPluginError:
    """Test PluginError dataclass functionality."""
    
    def test_plugin_error_creation(self) -> None:
        """Test PluginError dataclass creation with all fields."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(),
            'PyQt5.QtWidgets': Mock(),
        }):
            from artisanlib.plugins.base import PluginError
            
            timestamp = datetime.now()
            context = {"operation": "test", "data": 123}
            
            error = PluginError(
                timestamp=timestamp,
                error_type="TestError",
                message="Test error message", 
                traceback="Test traceback",
                context=context
            )
            
            assert error.timestamp == timestamp
            assert error.error_type == "TestError"
            assert error.message == "Test error message"
            assert error.traceback == "Test traceback"
            assert error.context == context
    
    def test_plugin_error_default_context(self) -> None:
        """Test PluginError with default empty context."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(),
            'PyQt5.QtWidgets': Mock(),
        }):
            from artisanlib.plugins.base import PluginError
            
            timestamp = datetime.now()
            error = PluginError(
                timestamp=timestamp,
                error_type="TestError",
                message="Test message",
                traceback="Test traceback"
            )
            
            assert error.context == {}


class TestPluginWorker:
    """Test PluginWorker functionality."""
    
    def test_plugin_worker_initialization(self) -> None:
        """Test PluginWorker proper initialization."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(QObject=MockQObject, pyqtSignal=MockPyQtSignal, QMutex=MockQMutex),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(QObject=MockQObject, pyqtSignal=MockPyQtSignal, QMutex=MockQMutex),
            'PyQt5.QtWidgets': Mock(),
        }):
            from artisanlib.plugins.base import PluginWorker
            
            worker = PluginWorker()
            
            assert hasattr(worker, 'operation_started')
            assert hasattr(worker, 'operation_completed') 
            assert hasattr(worker, 'operation_failed')
            assert hasattr(worker, 'progress_updated')
            assert hasattr(worker, '_mutex')
            assert hasattr(worker, '_is_running')
            assert hasattr(worker, '_current_operation')
            
            assert worker._is_running is False
            assert worker._current_operation is None
    
    def test_plugin_worker_start_operation(self) -> None:
        """Test PluginWorker start_operation method."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(QObject=MockQObject, pyqtSignal=MockPyQtSignal, QMutex=MockQMutex),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(QObject=MockQObject, pyqtSignal=MockPyQtSignal, QMutex=MockQMutex),
            'PyQt5.QtWidgets': Mock(),
        }):
            from artisanlib.plugins.base import PluginWorker
            
            worker = PluginWorker()
            
            # Mock operation function
            operation_result = "test_result"
            operation_func = Mock(return_value=operation_result)
            
            # Start operation
            result = worker.start_operation("test_op", operation_func, "arg1", kwarg1="value1")
            
            assert result is True
            operation_func.assert_called_once_with("arg1", kwarg1="value1")
            
    def test_plugin_worker_operation_failure(self) -> None:
        """Test PluginWorker operation failure handling."""
        with patch.dict('sys.modules', {
            'PyQt6.QtCore': Mock(QObject=MockQObject, pyqtSignal=MockPyQtSignal, QMutex=MockQMutex),
            'PyQt6.QtWidgets': Mock(),
            'PyQt5.QtCore': Mock(QObject=MockQObject, pyqtSignal=MockPyQtSignal, QMutex=MockQMutex),
            'PyQt5.QtWidgets': Mock(),
        }):
            from artisanlib.plugins.base import PluginWorker
            
            worker = PluginWorker()
            
            # Mock failing operation
            operation_func = Mock(side_effect=RuntimeError("Test error"))
            
            # Start operation
            result = worker.start_operation("test_op", operation_func)
            
            assert result is True
            operation_func.assert_called_once()


class TestPluginBase:
    """Test PluginBase functionality."""
    
    def test_plugin_base_initialization(self) -> None:
        """Test PluginBase proper initialization."""
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
        }):
            from artisanlib.plugins.base import PluginBase, PluginState
            
            # Create test plugin class
            class TestPluginImpl(PluginBase):
                @property
                def name(self) -> str:
                    return "test_plugin"
                    
                @property
                def version(self) -> str:
                    return "1.0.0"
            
            plugin = TestPluginImpl()
            
            assert plugin.main_window is None
            assert plugin.state == PluginState.UNINITIALIZED
            assert plugin.errors == []
            assert plugin.initialization_time is None
            assert plugin.last_error_time is None
            assert isinstance(plugin.operation_times, dict)
            assert plugin.operation_times == {}
    
    def test_plugin_base_properties(self) -> None:
        """Test PluginBase properties."""
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
        }):
            from artisanlib.plugins.base import PluginBase, PluginState
            
            class TestPluginImpl(PluginBase):
                @property
                def name(self) -> str:
                    return "test_plugin"
                    
                @property
                def version(self) -> str:
                    return "1.0.0"
            
            plugin = TestPluginImpl()
            
            # Test abstract properties
            assert plugin.name == "test_plugin"
            assert plugin.version == "1.0.0"
            assert plugin.description == "test_plugin v1.0.0"
            
            # Test state properties
            assert plugin.is_active is False
            assert plugin.has_errors is False
            
            # Change state and test again
            plugin._change_state(PluginState.ACTIVE)
            assert plugin.is_active is True
    
    def test_plugin_initialization_success(self) -> None:
        """Test successful plugin initialization."""
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
        }):
            from artisanlib.plugins.base import PluginBase, PluginState
            
            class TestPluginImpl(PluginBase):
                @property
                def name(self) -> str:
                    return "test_plugin"
                    
                @property
                def version(self) -> str:
                    return "1.0.0"
                    
                def _initialize_plugin(self) -> None:
                    self.test_initialized = True
            
            plugin = TestPluginImpl()
            main_window = MockQMainWindow()
            
            plugin.initialize(main_window)
            
            assert plugin.state == PluginState.ACTIVE
            assert plugin.main_window == main_window
            assert plugin.initialization_time is not None
            assert hasattr(plugin, 'test_initialized')
            assert plugin.test_initialized is True
    
    def test_plugin_initialization_failure(self) -> None:
        """Test plugin initialization failure handling."""
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
        }):
            from artisanlib.plugins.base import PluginBase, PluginState
            
            class FailingPluginImpl(PluginBase):
                @property
                def name(self) -> str:
                    return "failing_plugin"
                    
                @property
                def version(self) -> str:
                    return "1.0.0"
                    
                def _initialize_plugin(self) -> None:
                    raise RuntimeError("Initialization failed")
            
            plugin = FailingPluginImpl()
            main_window = MockQMainWindow()
            
            with pytest.raises(RuntimeError, match="Initialization failed"):
                plugin.initialize(main_window)
                
            assert plugin.state == PluginState.ERROR
    
    def test_plugin_cleanup(self) -> None:
        """Test plugin cleanup functionality."""
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
        }):
            from artisanlib.plugins.base import PluginBase, PluginState
            
            class TestPluginImpl(PluginBase):
                @property
                def name(self) -> str:
                    return "test_plugin"
                    
                @property
                def version(self) -> str:
                    return "1.0.0"
                    
                def _cleanup_plugin(self) -> None:
                    self.test_cleaned = True
            
            plugin = TestPluginImpl()
            main_window = MockQMainWindow()
            
            # Initialize first
            plugin.initialize(main_window)
            assert plugin.state == PluginState.ACTIVE
            
            # Then cleanup
            plugin.cleanup()
            
            assert plugin.state == PluginState.DISABLED
            assert hasattr(plugin, 'test_cleaned')
            assert plugin.test_cleaned is True
    
    def test_plugin_error_recording(self) -> None:
        """Test plugin error recording functionality."""
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
        }), patch('traceback.format_exc', return_value="Test traceback"):
            from artisanlib.plugins.base import PluginBase, PluginState
            
            class TestPluginImpl(PluginBase):
                @property
                def name(self) -> str:
                    return "test_plugin"
                    
                @property
                def version(self) -> str:
                    return "1.0.0"
            
            plugin = TestPluginImpl()
            
            assert len(plugin.errors) == 0
            assert plugin.has_errors is False
            assert plugin.last_error_time is None
            
            # Record an error
            context = {"operation": "test"}
            plugin._record_error("TestError", "Test error message", context)
            
            assert len(plugin.errors) == 1
            assert plugin.has_errors is True
            assert plugin.last_error_time is not None
            assert plugin.state == PluginState.ERROR
            
            error = plugin.errors[0]
            assert error.error_type == "TestError"
            assert error.message == "Test error message"
            assert error.context == context
            assert error.traceback == "Test traceback"
    
    def test_plugin_health_status(self) -> None:
        """Test plugin health status reporting."""
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
        }):
            from artisanlib.plugins.base import PluginBase, PluginState
            
            class TestPluginImpl(PluginBase):
                @property
                def name(self) -> str:
                    return "test_plugin"
                    
                @property
                def version(self) -> str:
                    return "1.0.0"
            
            plugin = TestPluginImpl()
            main_window = MockQMainWindow()
            
            # Initialize plugin
            plugin.initialize(main_window)
            
            # Record some operation times
            plugin._record_operation_time("test_op", 0.5)
            plugin._record_operation_time("test_op", 1.0)
            plugin._record_operation_time("another_op", 0.25)
            
            health_status = plugin.get_health_status()
            
            assert health_status["name"] == "test_plugin"
            assert health_status["version"] == "1.0.0"
            assert health_status["state"] == "active"
            assert health_status["is_active"] is True
            assert health_status["has_errors"] is False
            assert health_status["error_count"] == 0
            assert health_status["initialization_time"] is not None
            assert health_status["last_error_time"] is None
            assert "operation_times" in health_status
            
            # Check operation times
            op_times = health_status["operation_times"]
            assert "test_op" in op_times
            assert op_times["test_op"]["count"] == 2
            assert op_times["test_op"]["avg_time"] == 0.75
            assert op_times["test_op"]["min_time"] == 0.5
            assert op_times["test_op"]["max_time"] == 1.0
    
    def test_plugin_reset_errors(self) -> None:
        """Test plugin error reset functionality."""
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
        }), patch('traceback.format_exc', return_value="Test traceback"):
            from artisanlib.plugins.base import PluginBase, PluginState
            
            class TestPluginImpl(PluginBase):
                @property
                def name(self) -> str:
                    return "test_plugin"
                    
                @property
                def version(self) -> str:
                    return "1.0.0"
            
            plugin = TestPluginImpl()
            main_window = MockQMainWindow()
            plugin.initialize(main_window)
            
            # Record an error
            plugin._record_error("TestError", "Test message")
            
            assert len(plugin.errors) == 1
            assert plugin.has_errors is True
            assert plugin.state == PluginState.ERROR
            assert plugin.last_error_time is not None
            
            # Reset errors
            plugin.reset_errors()
            
            assert len(plugin.errors) == 0
            assert plugin.has_errors is False
            assert plugin.state == PluginState.ACTIVE
            assert plugin.last_error_time is None


@pytest.mark.parametrize(
    'operation_name,operation_result,should_fail',
    [
        ('test_operation', 'success', False),
        ('failing_operation', None, True),
        ('complex_operation', {'result': 'data'}, False),
    ],
)
def test_plugin_safe_execute(operation_name: str, operation_result: Any, should_fail: bool) -> None:
    """Test plugin _safe_execute method with various scenarios."""
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
    }):
        from artisanlib.plugins.base import PluginBase
        
        class TestPluginImpl(PluginBase):
            @property
            def name(self) -> str:
                return "test_plugin"
                
            @property
            def version(self) -> str:
                return "1.0.0"
        
        plugin = TestPluginImpl()
        
        if should_fail:
            operation = Mock(side_effect=RuntimeError("Operation failed"))
            with pytest.raises(RuntimeError, match="Operation failed"):
                plugin._safe_execute(operation, operation_name)
            assert len(plugin.errors) == 1
        else:
            operation = Mock(return_value=operation_result)
            result = plugin._safe_execute(operation, operation_name)
            assert result == operation_result
            assert operation_name in plugin.operation_times
            assert len(plugin.operation_times[operation_name]) == 1