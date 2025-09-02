import traceback
import sys
from typing import Dict, Type, Optional, Any, List, Callable
from datetime import datetime
from dataclasses import dataclass, field

try:
    from PyQt6.QtWidgets import QMenu, QMainWindow, QMessageBox
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex
except ImportError:
    from PyQt5.QtWidgets import QMenu, QMainWindow, QMessageBox
    from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex

import logging
from .base import PluginBase, PluginState, PluginError

logger = logging.getLogger("artisan.plugins.manager")

@dataclass
class PluginRegistration:
    """Plugin registration information"""
    plugin: PluginBase
    registration_time: datetime
    initialization_successful: bool = False
    error_count: int = 0
    last_error_time: Optional[datetime] = None

class PluginManagerWorker(QObject):
    """Worker for plugin manager operations that should run in separate threads"""
    
    # Signals for worker communication
    plugin_operation_started = pyqtSignal(str, str)  # plugin_name, operation_name
    plugin_operation_completed = pyqtSignal(str, str, object)  # plugin_name, operation_name, result
    plugin_operation_failed = pyqtSignal(str, str, str)  # plugin_name, operation_name, error_message
    
    def __init__(self):
        super().__init__()
        self._mutex = QMutex()
        self._is_running = False
        
    def execute_plugin_operation(self, plugin: PluginBase, operation_name: str, 
                               operation_func: Callable, *args, **kwargs):
        """Execute a plugin operation in this worker thread"""
        if self._is_running:
            return False
            
        self._mutex.lock()
        try:
            self._is_running = True
            self.plugin_operation_started.emit(plugin.name, operation_name)
            
            # Execute the operation
            try:
                result = operation_func(*args, **kwargs)
                self.plugin_operation_completed.emit(plugin.name, operation_name, result)
            except Exception as e:
                self.plugin_operation_failed.emit(plugin.name, operation_name, str(e))
            finally:
                self._is_running = False
                
        finally:
            self._mutex.unlock()
            
        return True

class PluginManager(QObject):
    """Plugin manager with proper threading support"""
    
    # Signals for plugin manager events
    plugin_registered = pyqtSignal(str)  # plugin_name
    plugin_unregistered = pyqtSignal(str)  # plugin_name
    plugin_error = pyqtSignal(str, str)  # plugin_name, error_message
    plugin_state_changed = pyqtSignal(str, str)  # plugin_name, new_state
    
    def __init__(self, main_window: QMainWindow):
        super().__init__()
        self.main_window = main_window
        self.plugins: Dict[str, PluginRegistration] = {}
        self.plugin_menu: Optional[QMenu] = None
        self.health_check_timer: Optional[QTimer] = None
        
        # Threading support
        self._worker_thread: Optional[QThread] = None
        self._worker: Optional[PluginManagerWorker] = None
        self._mutex = QMutex()
        
        # Error tracking
        self.total_errors = 0
        self.critical_errors = 0
        
        # Performance tracking
        self.operation_times: Dict[str, List[float]] = {}
        
        logger.info("Plugin manager initialized")
        self._setup_health_monitoring()
        self._setup_worker_thread()
    
    def _setup_worker_thread(self) -> None:
        """Setup worker thread for plugin operations"""
        self._worker_thread = QThread()
        self._worker = PluginManagerWorker()
        
        # Move worker to thread
        self._worker.moveToThread(self._worker_thread)
        
        # Connect worker signals
        self._worker.plugin_operation_started.connect(self._on_plugin_operation_started)
        self._worker.plugin_operation_completed.connect(self._on_plugin_operation_completed)
        self._worker.plugin_operation_failed.connect(self._on_plugin_operation_failed)
        
        # Start the thread
        self._worker_thread.start()
        
        logger.debug("Plugin manager worker thread started")
    
    def _on_plugin_operation_started(self, plugin_name: str, operation_name: str) -> None:
        """Handle plugin operation started"""
        logger.debug(f"Plugin operation started: {plugin_name} - {operation_name}")
    
    def _on_plugin_operation_completed(self, plugin_name: str, operation_name: str, result: Any) -> None:
        """Handle plugin operation completed"""
        logger.debug(f"Plugin operation completed: {plugin_name} - {operation_name}")
    
    def _on_plugin_operation_failed(self, plugin_name: str, operation_name: str, error_message: str) -> None:
        """Handle plugin operation failed"""
        logger.error(f"Plugin operation failed: {plugin_name} - {operation_name}: {error_message}")
        self._on_plugin_error(plugin_name, error_message)
    
    def _setup_health_monitoring(self) -> None:
        """Setup periodic health monitoring"""
        self.health_check_timer = QTimer()
        self.health_check_timer.timeout.connect(self._health_check)
        self.health_check_timer.start(30000)  # 30 seconds
    
    def _safe_execute(self, operation: Callable, operation_name: str, 
                     context: Dict[str, Any] = None) -> Any:
        start_time = datetime.now()
        
        try:
            logger.debug(f"Starting operation: {operation_name}")
            result = operation()
            
            # timing
            duration = (datetime.now() - start_time).total_seconds()
            if operation_name not in self.operation_times:
                self.operation_times[operation_name] = []
            self.operation_times[operation_name].append(duration)
            
            logger.debug(f"Operation {operation_name} completed in {duration:.3f}s")
            return result
            
        except Exception as e:
            self._record_error(operation_name, str(e), context or {})
            raise
    
    def _record_error(self, operation: str, message: str, context: Dict[str, Any] = None) -> None:
        """Record an error in the plugin manager"""
        self._mutex.lock()
        try:
            self.total_errors += 1
            logger.error(f"Plugin manager error in {operation}: {message}")
            logger.debug(f"Error context: {context}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")
        finally:
            self._mutex.unlock()
    
    def register_plugin(self, plugin_class: Type[PluginBase]) -> bool:
        """Register a new plugin with comprehensive error handling"""
        def _register_operation():
            plugin = plugin_class()
            name = plugin.name
            
            # validate plugin
            if not name or not name.strip():
                raise ValueError("Plugin must have a valid name")
            
            if name in self.plugins:
                logger.warning(f"Plugin {name} already registered")
                return False
            
            # Create registration record
            registration = PluginRegistration(
                plugin=plugin,
                registration_time=datetime.now()
            )
            
            # Connect plugin signals
            plugin.state_changed.connect(self._on_plugin_state_changed)
            plugin.error_occurred.connect(self._on_plugin_error)
            
            # Initialize plugin
            try:
                plugin.initialize(self.main_window)
                registration.initialization_successful = True
                
                # Create plugin menu 
                self._create_plugin_menu(plugin)
                
                # Store registration
                self.plugins[name] = registration
                
                logger.info(f"Plugin {name} v{plugin.version} registered successfully")
                self.plugin_registered.emit(name)
                
                return True
                
            except Exception as e:
                registration.initialization_successful = False
                registration.error_count += 1
                registration.last_error_time = datetime.now()
                
                logger.error(f"Failed to initialize plugin {name}: {e}")
                logger.debug(f"Initialization traceback: {traceback.format_exc()}")
                
                self.plugins[name] = registration
                self.plugin_error.emit(name, f"Initialization failed: {e}")
                
                return False
        
        try:
            return self._safe_execute(_register_operation, "register_plugin")
        except Exception as e:
            logger.error(f"Failed to register plugin: {e}")
            return False
    
    def _create_plugin_menu(self, plugin: PluginBase) -> None:
        try:
            # Create plugin menu if it doesn't exist
            if self.plugin_menu is None:
                menubar = self.main_window.menuBar()
                self.plugin_menu = menubar.addMenu("Plugins")
            
            # Add plugin menu items
            plugin_menu = plugin.create_menu(self.plugin_menu)
            if plugin_menu:
                self.plugin_menu.addMenu(plugin_menu)
                
        except Exception as e:
            logger.error(f"Failed to create menu for {plugin.name}: {e}")
    
    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """Get a plugin by name"""
        self._mutex.lock()
        try:
            registration = self.plugins.get(name)
            return registration.plugin if registration else None
        finally:
            self._mutex.unlock()
    
    def get_plugin_registration(self, name: str) -> Optional[PluginRegistration]:
        """Get plugin registration information"""
        self._mutex.lock()
        try:
            return self.plugins.get(name)
        finally:
            self._mutex.unlock()
    
    def unregister_plugin(self, plugin_name: str) -> bool:
        def _unregister_operation():
            if plugin_name not in self.plugins:
                logger.warning(f"Plugin {plugin_name} not found for unregistration")
                return False
            
            registration = self.plugins[plugin_name]
            plugin = registration.plugin
            
            try:
                # Disconnect signals
                plugin.state_changed.disconnect()
                plugin.error_occurred.disconnect()
                
                # Cleanup plugin
                plugin.cleanup()
                
                # Remove from registry
                del self.plugins[plugin_name]
                
                logger.info(f"Plugin {plugin_name} unregistered")
                self.plugin_unregistered.emit(plugin_name)
                
                return True
                
            except Exception as e:
                logger.error(f"Error unregistering plugin {plugin_name}: {e}")
                return False
        
        try:
            return self._safe_execute(_unregister_operation, "unregister_plugin")
        except Exception as e:
            logger.error(f"Failed to unregister plugin {plugin_name}: {e}")
            return False
    
    def _on_plugin_state_changed(self, plugin_name: str, new_state: str) -> None:
        """Handle plugin state changes"""
        logger.debug(f"Plugin {plugin_name} state changed to {new_state}")
        self.plugin_state_changed.emit(plugin_name, new_state)
    
    def _on_plugin_error(self, plugin_name: str, error_message: str) -> None:
        """Handle plugin errors"""
        self._mutex.lock()
        try:
            if plugin_name in self.plugins:
                registration = self.plugins[plugin_name]
                registration.error_count += 1
                registration.last_error_time = datetime.now()
            
            self.total_errors += 1
            logger.error(f"Plugin {plugin_name} error: {error_message}")
            self.plugin_error.emit(plugin_name, error_message)
        finally:
            self._mutex.unlock()
    
    def notify_all(self, event: str, data: Any = None) -> None:
        """Notify all plugins of an event"""
        def _notify_operation():
            active_plugins = [
                reg.plugin for reg in self.plugins.values()
                if reg.plugin.is_active
            ]
            
            for plugin in active_plugins:
                try:
                    handler = getattr(plugin, f"on_{event}", None)
                    if handler:
                        handler(data) if data is not None else handler()
                except Exception as e:
                    logger.error(f"Error in plugin {plugin.name} handling {event}: {e}")
                    self._on_plugin_error(plugin.name, f"Event handler error: {e}")
        
        try:
            self._safe_execute(_notify_operation, f"notify_{event}")
        except Exception as e:
            logger.error(f"Failed to notify plugins of {event}: {e}")
    
    def notify_roast_start(self) -> None:
        """Notify all plugins that a roast has started"""
        self.notify_all("roast_start")
    
    def notify_roast_end(self) -> None:
        """Notify all plugins that a roast has ended"""
        self.notify_all("roast_end")
    
    def notify_data_update(self, data: Dict[str, Any]) -> None:
        """Notify all plugins of new roast data"""
        self.notify_all("data_update", data)
    
    def _health_check(self) -> None:
        """Periodic health check of all plugins"""
        def _health_operation():
            for name, registration in self.plugins.items():
                plugin = registration.plugin
                
                # Check if plugin is in error state
                if (plugin.state == PluginState.ERROR and 
                    registration.last_error_time and
                    (datetime.now() - registration.last_error_time).total_seconds() > 300):  # 5 minutes
                    
                    logger.warning(f"Plugin {name} has been in error state for 5+ minutes")
                
                if plugin.has_errors:
                    logger.info(f"Plugin {name} health: {plugin.get_health_status()}")
        
        try:
            self._safe_execute(_health_operation, "health_check")
        except Exception as e:
            logger.error(f"Health check failed: {e}")
    
    def get_manager_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the plugin manager"""
        self._mutex.lock()
        try:
            return {
                "total_plugins": len(self.plugins),
                "active_plugins": len([p for p in self.plugins.values() if p.plugin.is_active]),
                "plugins_with_errors": len([p for p in self.plugins.values() if p.plugin.has_errors]),
                "total_errors": self.total_errors,
                "critical_errors": self.critical_errors,
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
                "plugins": {
                    name: {
                        "registration_time": reg.registration_time.isoformat(),
                        "initialization_successful": reg.initialization_successful,
                        "error_count": reg.error_count,
                        "last_error_time": reg.last_error_time.isoformat() if reg.last_error_time else None,
                        "health_status": reg.plugin.get_health_status()
                    }
                    for name, reg in self.plugins.items()
                }
            }
        finally:
            self._mutex.unlock()
    
    def cleanup(self) -> None:
        """Cleanup the plugin manager"""
        try:
            logger.info("Cleaning up plugin manager")
            
            # stop health monitoring
            if self.health_check_timer:
                self.health_check_timer.stop()
                self.health_check_timer.deleteLater()
            
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
            
            # Cleanup all plugins
            plugin_names = list(self.plugins.keys())
            for name in plugin_names:
                self.unregister_plugin(name)
            
            logger.info("Plugin manager cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during plugin manager cleanup: {e}")