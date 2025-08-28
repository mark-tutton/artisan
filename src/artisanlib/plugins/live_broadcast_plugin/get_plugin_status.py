import logging
import time
from typing import Dict, Any, Optional

_log = logging.getLogger(__name__)

def get_broadcaster_status() -> Dict[str, Any]:
    """Get the current status of the live broadcast plugin"""
    try:
        # Try to get the plugin instance from the plugin manager
        try:
            from ..manager import PluginManager
            from ..base import PluginState
            
            # Get the main application window to access plugin manager
            import sys
            from PyQt6.QtWidgets import QApplication
            
            app = QApplication.instance()
            if app:
                # Try to find the main window
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'plugin_manager'):
                        plugin_manager = widget.plugin_manager
                        break
                else:
                    # Fallback: try to get from global scope
                    plugin_manager = None
            else:
                plugin_manager = None
                
            if plugin_manager:
                # Get the live broadcast plugin
                live_broadcast_plugin = plugin_manager.get_plugin("Live Broadcast")
                if live_broadcast_plugin and live_broadcast_plugin.is_active:
                    # Plugin is active, get its status
                    try: 
                        plugin_status = live_broadcast_plugin.get_plugin_status()
                    except Exception as e: 
                        _log.warning(f"Error getting plugin status: {e}")
                        plugin_status = {
                            'state': 'error',
                            'broadcast_state': 'unknown',
                            'metrics': {},
                            'config': {}
                        }

                    # Extract connection information
                    broadcaster = getattr(live_broadcast_plugin, 'broadcaster', None)
                    if broadcaster:
                        try:
                            is_connected = broadcaster.is_connected()
                        except Exception as e:
                            _log.warning(f"Error getting broadcaster status: {e}")
                            is_connected = False
                            
                        server_url = f"{broadcaster.host}:{broadcaster.port}"
                        
                        # Get connection state
                        connection_state = "unknown"
                        try:
                            if hasattr(broadcaster, '_is_connected'):
                                if broadcaster._is_connected:
                                    connection_state = "connected"
                                elif hasattr(broadcaster, 'reconnect_attempts') and broadcaster.reconnect_attempts > 0:
                                    connection_state = "reconnecting"
                                else:
                                    connection_state = "disconnected"
                        except Exception as e:
                            _log.debug(f"Error getting connection state: {e}")
                            connection_state = "unknown"
                        
                        
                        # Get last error if any
                        last_error = None
                        try:
                            if hasattr(broadcaster, '_last_error'):
                                last_error = broadcaster._last_error
                            elif hasattr(broadcaster, 'error'):
                                last_error = getattr(broadcaster, 'error', None)
                        except Exception as e:
                            _log.debug(f"Error getting last error: {e}")
                            last_error = None
                        
                        # Get worker thread status if available
                        worker_thread_running = False
                        try:
                            if hasattr(live_broadcast_plugin, '_worker_thread'):
                                worker_thread = live_broadcast_plugin._worker_thread
                                if worker_thread:
                                    worker_thread_running = worker_thread.isRunning()
                        except Exception as e:
                            _log.debug(f"Error checking worker thread: {e}")
                        
                        return {
                            'is_connected': is_connected,
                            'server_url': server_url,
                            'last_error': last_error,
                            'plugin_loaded': True,
                            'connection_state': connection_state,
                            'plugin_state': plugin_status.get('state', 'unknown'),
                            'broadcast_state': plugin_status.get('broadcast_state', 'unknown'),
                            'worker_thread_running': worker_thread_running,
                            'metrics': plugin_status.get('metrics', {}),
                            'config': plugin_status.get('config', {}),
                            'timestamp': time.time()
                        }
                    else:
                        # Plugin active but no broadcaster
                        return {
                            'is_connected': False,
                            'server_url': 'No broadcaster',
                            'last_error': 'Broadcaster not initialized',
                            'plugin_loaded': True,
                            'connection_state': 'no_broadcaster',
                            'plugin_state': plugin_status.get('state', 'unknown'),
                            'broadcast_state': 'unknown',
                            'worker_thread_running': False,
                            'metrics': {},
                            'config': plugin_status.get('config', {}),
                            'timestamp': time.time()
                        }
                else:
                       # Plugin not active
                    return {
                        'is_connected': False,
                        'server_url': 'Plugin inactive',
                        'last_error': 'Plugin not active',
                        'plugin_loaded': False,
                        'connection_state': 'inactive',
                        'plugin_state': 'inactive',
                        'broadcast_state': 'unknown',
                        'worker_thread_running': False,
                        'metrics': {},
                        'config': {},
                        'timestamp': time.time()
                    }
            else:
                # No plugin manager found
                return {
                    'is_connected': False,
                    'server_url': 'No plugin manager',
                    'last_error': 'Plugin manager not available',
                    'plugin_loaded': False,
                    'connection_state': 'no_manager',
                    'plugin_state': 'unknown',
                    'broadcast_state': 'unknown',
                    'worker_thread_running': False,
                    'metrics': {},
                    'config': {},
                    'timestamp': time.time()
                }
                
        except ImportError as e:
            # Plugin manager not available
            return {
                'is_connected': False,
                'server_url': 'Import error',
                'last_error': f'Cannot import plugin manager: {e}',
                'plugin_loaded': False,
                'connection_state': 'import_error',
                'plugin_state': 'unknown',
                'broadcast_state': 'unknown',
                'worker_thread_running': False,
                'metrics': {},
                'config': {},
                'timestamp': time.time()
            }
            
    except Exception as e:
        _log.error(f"Error getting broadcaster status: {e}")
        return {
            'is_connected': False,
            'server_url': 'Error',
            'last_error': str(e),
            'plugin_loaded': False,
            'connection_state': 'error',
            'plugin_state': 'error',
            'broadcast_state': 'error',
            'worker_thread_running': False,
            'metrics': {},
            'config': {},
            'timestamp': time.time()
        }


def get_broadcaster_status_safe() -> Dict[str, Any]:
    """Get broadcaster status with additional safety checks for threading"""
    try:
        # Add a small delay to avoid overwhelming the system
        time.sleep(0.01)
        
        # Get the basic status
        status = get_broadcaster_status()
        
        # Add threading-specific information
        if status.get('plugin_loaded'):
            try:
                from ..manager import PluginManager
                from PyQt6.QtWidgets import QApplication
                
                app = QApplication.instance()
                if app:
                    for widget in app.topLevelWidgets():
                        if hasattr(widget, 'plugin_manager'):
                            plugin_manager = widget.plugin_manager
                            break
                    else:
                        plugin_manager = None
                        
                    if plugin_manager:
                        live_broadcast_plugin = plugin_manager.get_plugin("Live Broadcast")
                        if live_broadcast_plugin:
                            # Get thread safety information
                            try:
                                if hasattr(live_broadcast_plugin, '_mutex'):
                                    mutex_available = True
                                else:
                                    mutex_available = False
                                    
                                if hasattr(live_broadcast_plugin, '_worker_thread'):
                                    worker_thread = live_broadcast_plugin._worker_thread
                                    if worker_thread:
                                        thread_id = worker_thread.currentThreadId() if hasattr(worker_thread, 'currentThreadId') else 'unknown'
                                        thread_running = worker_thread.isRunning()
                                    else:
                                        thread_id = 'none'
                                        thread_running = False
                                else:
                                    thread_id = 'none'
                                    thread_running = False
                                    
                                status.update({
                                    'threading_info': {
                                        'mutex_available': mutex_available,
                                        'worker_thread_id': thread_id,
                                        'worker_thread_running': thread_running,
                                        'main_thread_id': app.thread().currentThreadId() if hasattr(app.thread(), 'currentThreadId') else 'unknown'
                                    }
                                })
                            except Exception as e:
                                _log.debug(f"Error getting threading info: {e}")
                                status['threading_info'] = {
                                    'error': str(e),
                                    'mutex_available': False,
                                    'worker_thread_id': 'error',
                                    'worker_thread_running': False,
                                    'main_thread_id': 'error'
                                }
            except Exception as e:
                _log.debug(f"Error getting threading information: {e}")
                status['threading_info'] = {
                    'error': str(e),
                    'mutex_available': False,
                    'worker_thread_id': 'error',
                    'worker_thread_running': False,
                    'main_thread_id': 'error'
                }
        
        return status
        
    except Exception as e:
        _log.error(f"Error in safe status check: {e}")
        return {
            'is_connected': False,
            'server_url': 'Safe check error',
            'last_error': str(e),
            'plugin_loaded': False,
            'connection_state': 'error',
            'plugin_state': 'error',
            'broadcast_state': 'error',
            'worker_thread_running': False,
            'threading_info': {
                'error': str(e),
                'mutex_available': False,
                'worker_thread_id': 'error',
                'worker_thread_running': False,
                'main_thread_id': 'error'
            },
            'metrics': {},
            'config': {},
            'timestamp': time.time()
        }

def is_plugin_thread_safe() -> bool:
    """Check if the plugin is properly configured for threading"""
    try:
        status = get_broadcaster_status()
        if status.get('plugin_loaded'):
            threading_info = status.get('threading_info', {})
            return (
                threading_info.get('mutex_available', False) and
                threading_info.get('worker_thread_running', False)
            )
        return False
    except Exception as e:
        _log.error(f"Error checking thread safety: {e}")
        return False