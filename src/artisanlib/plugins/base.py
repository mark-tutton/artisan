import traceback
import sys
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

try:
    from PyQt6.QtWidgets import QMenu, QMainWindow
    from PyQt6.QtCore import QObject, pyqtSignal
except ImportError:
    from PyQt5.QtWidgets import QMenu, QMainWindow
    from PyQt5.QtCore import QObject, pyqtSignal

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

class PluginBase(QObject):
    """Base class for plugins with error handling"""
    
    # Signals for plugin state changes
    state_changed = pyqtSignal(str, str)  # plugin_name, new_state
    error_occurred = pyqtSignal(str, str)  # plugin_name, error_message
    
    def __init__(self):
        super().__init__()
        self.main_window: Optional[QMainWindow] = None
        self.state = PluginState.UNINITIALIZED
        self.errors: List[PluginError] = []
        self.initialization_time: Optional[datetime] = None
        self.last_error_time: Optional[datetime] = None
        

        self.logger = logging.getLogger(f"artisan.plugins.{self.name}")
        self._setup_logging()
        
        # Performance tracking
        self.operation_times: Dict[str, List[float]] = {}
        
    def _setup_logging(self) -> None:
        """Setup logging for the plugin"""
        # formatter with plugin context
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
        
        self.logger.setLevel(logging.INFO)
    
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
        try:
            old_state = self.state
            self.state = new_state
            self.logger.info(f"State changed: {old_state.value} -> {new_state.value}")
            self.state_changed.emit(self.name, new_state.value)
        except Exception as e:
            self.logger.error(f"Error changing state: {e}")
            self._record_error("StateChangeError", str(e))
    
    def _record_error(self, error_type: str, message: str, context: Dict[str, Any] = None) -> None:
        """Record an error with full traceback"""
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
    
    def _safe_execute(self, operation: Callable, operation_name: str, 
                     context: Dict[str, Any] = None) -> Any:
        """Safely execute an operation with error handling and timing"""
        start_time = datetime.now()
        
        try:
            self.logger.debug(f"Starting operation: {operation_name}")
            result = operation()
            

            duration = (datetime.now() - start_time).total_seconds()
            if operation_name not in self.operation_times:
                self.operation_times[operation_name] = []
            self.operation_times[operation_name].append(duration)
            
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
        return {
            "name": self.name,
            "version": self.version,
            "state": self.state.value,
            "is_active": self.is_active,
            "has_errors": self.has_errors,
            "error_count": len(self.errors),
            "initialization_time": self.initialization_time.isoformat() if self.initialization_time else None,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
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
    
    def reset_errors(self) -> None:
        """Reset error state and clear error history"""
        self.errors.clear()
        self.last_error_time = None
        if self.state == PluginState.ERROR:
            self._change_state(PluginState.ACTIVE)
        self.logger.info(f"Reset error state for {self.name}")

ArtisanPlugin = PluginBase