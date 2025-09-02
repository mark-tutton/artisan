import traceback
import sys
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

try:
    from PyQt6.QtWidgets import QMenu, QMainWindow
    from PyQt6.QtCore import QObject, pyqtSignal, QThread, QMutex, QTimer
except ImportError:
    from PyQt5.QtWidgets import QMenu, QMainWindow
    from PyQt5.QtCore import QObject, pyqtSignal, QThread, QMutex, QTimer

import logging

class PluginState(Enum):
    """Plugin lifecycle states"""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    ERROR = "error"
    CLEANING_UP = "cleaning_up"
    DISABLED = "disabled"

@dataclass
class PluginError:
    """Structured error information"""
    timestamp: datetime
    error_type: str
    message: str
    traceback: str
    context: Dict[str, Any] = field(default_factory=dict)

class PluginWorker(QObject):
    """Worker object for plugin operations that should run in separate threads"""
    
    # Signals for worker communication
    operation_started = pyqtSignal(str)  # operation_name
    operation_completed = pyqtSignal(str, object)  # operation_name, result
    operation_failed = pyqtSignal(str, str)  # operation_name, error_message
    progress_updated = pyqtSignal(str, int)  # operation_name, progress_percentage
    
    def __init__(self):
        super().__init__()
        self._mutex = QMutex()
        self._is_running = False
        self._current_operation = None
        
    def start_operation(self, operation_name: str, operation_func: Callable, *args, **kwargs):
        """Start a long-running operation in this worker thread"""
        if self._is_running:
            return False
            
        self._mutex.lock()
        try:
            self._is_running = True
            self._current_operation = operation_name
            self.operation_started.emit(operation_name)
            
            # Execute the operation
            try:
                result = operation_func(*args, **kwargs)
                self.operation_completed.emit(operation_name, result)
            except Exception as e:
                self.operation_failed.emit(operation_name, str(e))
            finally:
                self._is_running = False
                self._current_operation = None
                
        finally:
            self._mutex.unlock()
            
        return True
    
    def stop_operation(self):
        """Stop the current operation"""
        self._mutex.lock()
        try:
            self._is_running = False
        finally:
            self._mutex.unlock()

class PluginBase(QObject):
    """Base class for plugins with proper threading support"""
    
    # Signals for plugin state changes
    state_changed = pyqtSignal(str, str)  # plugin_name, new_state
    error_occurred = pyqtSignal(str, str)  # plugin_name, error_message
    worker_operation_started = pyqtSignal(str)  # operation_name
    worker_operation_completed = pyqtSignal(str, object)  # operation_name, result
    worker_operation_failed = pyqtSignal(str, str)  # operation_name, error_message
    
    def __init__(self):
        super().__init__()
        self.main_window: Optional[QMainWindow] = None
        self.state = PluginState.UNINITIALIZED
        self.errors: List[PluginError] = []
        self.initialization_time: Optional[datetime] = None
        self.last_error_time: Optional[datetime] = None
        
        # Threading support
        self._worker_thread: Optional[QThread] = None
        self._worker: Optional[PluginWorker] = None
        self._mutex = QMutex()
        
        # Performance tracking
        self.operation_times: Dict[str, List[float]] = {}
        
        self.logger = logging.getLogger(f"artisan.plugins.{self.name}")
        self._setup_logging()
        self._setup_worker_thread()
        
    def _setup_logging(self) -> None:
        """Setup logging for the plugin"""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.logger.setLevel(logging.INFO)
    
    def _setup_worker_thread(self) -> None:
        """Setup worker thread for long-running operations"""
        self._worker_thread = QThread()
        self._worker = PluginWorker()
        
        # Move worker to thread
        self._worker.moveToThread(self._worker_thread)
        
        # Connect worker signals
        self._worker.operation_started.connect(self.worker_operation_started.emit)
        self._worker.operation_completed.connect(self.worker_operation_completed.emit)
        self._worker.operation_failed.connect(self.worker_operation_failed.emit)
        
        # Connect to our own signals for external consumption
        self._worker.operation_started.connect(self._on_worker_operation_started)
        self._worker.operation_completed.connect(self._on_worker_operation_completed)
        self._worker.operation_failed.connect(self._on_worker_operation_failed)
        
        # Start the thread
        self._worker_thread.start()
        
        self.logger.debug(f"Worker thread started for {self.name}")
    
    def _on_worker_operation_started(self, operation_name: str) -> None:
        """Handle worker operation started"""
        self.logger.debug(f"Worker operation started: {operation_name}")
    
    def _on_worker_operation_completed(self, operation_name: str, result: Any) -> None:
        """Handle worker operation completed"""
        self.logger.debug(f"Worker operation completed: {operation_name}")
        self._record_operation_time(operation_name, 0.0)  # Worker handles timing
    
    def _on_worker_operation_failed(self, operation_name: str, error_message: str) -> None:
        """Handle worker operation failed"""
        self.logger.error(f"Worker operation failed: {operation_name} - {error_message}")
        self._record_error(f"{operation_name}WorkerError", error_message)
    
    def execute_in_worker(self, operation_name: str, operation_func: Callable, *args, **kwargs) -> bool:
        """Execute a long-running operation in the worker thread"""
        if not self._worker or not self._worker_thread:
            self.logger.error("Worker thread not available")
            return False
            
        try:
            # Use QTimer.singleShot to queue the operation in the worker thread
            from PyQt6.QtCore import QTimer
            
            def execute_operation():
                try:
                    self._worker.start_operation(operation_name, operation_func, *args, **kwargs)
                except Exception as e:
                    self.logger.error(f"Error executing operation {operation_name} in worker: {e}")
            
            # Queue the operation using QTimer.singleShot
            QTimer.singleShot(0, execute_operation)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to queue operation {operation_name}: {e}")
            return False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name - must be unique"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version"""
        pass
    
    @property
    def description(self) -> str:
        """Plugin description - override in subclasses"""
        return f"{self.name} v{self.version}"
    
    @property
    def is_active(self) -> bool:
        """Check if plugin is in active state"""
        return self.state == PluginState.ACTIVE
    
    @property
    def has_errors(self) -> bool:
        """Check if plugin has encountered errors"""
        return len(self.errors) > 0
    
    def _change_state(self, new_state: PluginState) -> None:
        """Safely change plugin state and emit signal"""
        self._mutex.lock()
        try:
            old_state = self.state
            self.state = new_state
            self.logger.info(f"State changed: {old_state.value} -> {new_state.value}")
            self.state_changed.emit(self.name, new_state.value)
        except Exception as e:
            self.logger.error(f"Error changing state: {e}")
            self._record_error("StateChangeError", str(e))
        finally:
            self._mutex.unlock()
    
    def _record_error(self, error_type: str, message: str, context: Dict[str, Any] = None) -> None:
        """Record an error with full traceback"""
        self._mutex.lock()
        try:
            error = PluginError(
                timestamp=datetime.now(),
                error_type=error_type,
                message=message,
                traceback=traceback.format_exc(),
                context=context or {}
            )
            self.errors.append(error)
            self.last_error_time = error.timestamp
            
            self.logger.error(f"{error_type}: {message}")
            self.logger.debug(f"Full traceback: {error.traceback}")
            
            self.error_occurred.emit(self.name, message)
            
            if self.state != PluginState.ERROR:
                self._change_state(PluginState.ERROR)
                
        except Exception as e:
            self.logger.critical(f"Failed to record error: {e}")
        finally:
            self._mutex.unlock()
    
    def _record_operation_time(self, operation_name: str, duration: float) -> None:
        """Record operation timing information"""
        self._mutex.lock()
        try:
            if operation_name not in self.operation_times:
                self.operation_times[operation_name] = []
            self.operation_times[operation_name].append(duration)
        finally:
            self._mutex.unlock()
    
    def _safe_execute(self, operation: Callable, operation_name: str, 
                     context: Dict[str, Any] = None) -> Any:
        """Safely execute an operation with error handling and timing"""
        start_time = datetime.now()
        
        try:
            self.logger.debug(f"Starting operation: {operation_name}")
            result = operation()
            
            duration = (datetime.now() - start_time).total_seconds()
            self._record_operation_time(operation_name, duration)
            
            self.logger.debug(f"Operation {operation_name} completed in {duration:.3f}s")
            return result
            
        except Exception as e:
            self._record_error(
                f"{operation_name}Error", 
                str(e), 
                context or {}
            )
            raise
    
    def initialize(self, main_window: QMainWindow) -> None:
        """Initialize the plugin with comprehensive error handling"""
        def _init_operation():
            self._change_state(PluginState.INITIALIZING)
            self.main_window = main_window
            self.initialization_time = datetime.now()
            
            self._initialize_plugin()
            
            self._change_state(PluginState.ACTIVE)
            self.logger.info(f"Initialized {self.name} v{self.version}")
        
        try:
            self._safe_execute(_init_operation, "initialize")
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name}: {e}")
            self._change_state(PluginState.ERROR)
            raise
    
    def _initialize_plugin(self) -> None:
        """Subclass-specific initialization - override in subclasses"""
        pass
    
    def cleanup(self) -> None:
        """Cleanup the plugin with error handling"""
        def _cleanup_operation():
            self._change_state(PluginState.CLEANING_UP)
            
            # Stop worker thread
            if self._worker_thread:
                self._worker_thread.quit()
                self._worker_thread.wait(5000)  # Wait up to 5 seconds
                if self._worker_thread.isRunning():
                    self._worker_thread.terminate()
                    self._worker_thread.wait()
                
                self._worker_thread.deleteLater()
                self._worker_thread = None
                self._worker = None
            
            self._cleanup_plugin()
            self._change_state(PluginState.DISABLED)
            self.logger.info(f"Cleaned up {self.name}")
        
        try:
            self._safe_execute(_cleanup_operation, "cleanup")
        except Exception as e:
            self.logger.error(f"Error during cleanup of {self.name}: {e}")
    
    def _cleanup_plugin(self) -> None:
        """Subclass-specific cleanup - override in subclasses"""
        pass
    
    def create_menu(self, parent_menu: QMenu) -> Optional[QMenu]:
        """Create plugin menu items with error handling"""
        def _menu_operation():
            return self._create_plugin_menu(parent_menu)
        
        try:
            return self._safe_execute(_menu_operation, "create_menu")
        except Exception as e:
            self.logger.error(f"Failed to create menu for {self.name}: {e}")
            return None
    
    def _create_plugin_menu(self, parent_menu: QMenu) -> Optional[QMenu]:
        """Subclass-specific menu creation - override in subclasses"""
        return None
    
    def on_roast_start(self) -> None:
        """Called when a roast starts - with error handling"""
        def _roast_start_operation():
            self._on_roast_start_impl()
        
        try:
            self._safe_execute(_roast_start_operation, "roast_start")
        except Exception as e:
            self.logger.error(f"Error in roast start handler for {self.name}: {e}")
    
    def _on_roast_start_impl(self) -> None:
        """Subclass-specific roast start handling - override in subclasses"""
        pass
    
    def on_roast_end(self) -> None:
        """Called when a roast ends - with error handling"""
        def _roast_end_operation():
            self._on_roast_end_impl()
        
        try:
            self._safe_execute(_roast_end_operation, "roast_end")
        except Exception as e:
            self.logger.error(f"Error in roast end handler for {self.name}: {e}")
    
    def _on_roast_end_impl(self) -> None:
        """Subclass-specific roast end handling - override in subclasses"""
        pass
    
    def on_data_update(self, data: Dict[str, Any]) -> None:
        """Called when new roast data is available - with error handling"""
        def _data_update_operation():
            self._on_data_update_impl(data)
        
        try:
            self._safe_execute(_data_update_operation, "data_update", {"data_keys": list(data.keys())})
        except Exception as e:
            self.logger.error(f"Error in data update handler for {self.name}: {e}")
    
    def _on_data_update_impl(self, data: Dict[str, Any]) -> None:
        """Subclass-specific data update handling - override in subclasses"""
        pass
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of the plugin"""
        self._mutex.lock()
        try:
            return {
                "name": self.name,
                "version": self.version,
                "state": self.state.value,
                "is_active": self.is_active,
                "has_errors": self.has_errors,
                "error_count": len(self.errors),
                "initialization_time": self.initialization_time.isoformat() if self.initialization_time else None,
                "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
                "worker_thread_running": self._worker_thread.isRunning() if self._worker_thread else False,
                "operation_times": {
                    op: {
                        "count": len(times),
                        "avg_time": sum(times) / len(times) if times else 0,
                        "min_time": min(times) if times else 0,
                        "max_time": max(times) if times else 0
                    }
                    for op, times in self.operation_times.items()
                },
                "recent_errors": [
                    {
                        "timestamp": error.timestamp.isoformat(),
                        "type": error.error_type,
                        "message": error.message
                    }
                    for error in self.errors[-5:] 
                ]
            }
        finally:
            self._mutex.unlock()
    
    def reset_errors(self) -> None:
        """Reset error state and clear error history"""
        self._mutex.lock()
        try:
            self.errors.clear()
            self.last_error_time = None
            if self.state == PluginState.ERROR:
                self._change_state(PluginState.ACTIVE)
            self.logger.info(f"Reset error state for {self.name}")
        finally:
            self._mutex.unlock()

ArtisanPlugin = PluginBase