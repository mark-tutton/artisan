import logging
import time
from typing import Dict, Any, Optional

_log = logging.getLogger(__name__)

def get_inventory_fetcher_status() -> Dict[str, Any]:
    """Get the current status of the inventory fetcher plugin"""
    try:
        # Try to get the plugin instance from the main window
        try:
            from PyQt6.QtWidgets import QApplication
            
            app = QApplication.instance()
            if app:
                # Try to find the main window
                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'inventory_fetcher_plugin'):
                        inventory_plugin = widget.inventory_fetcher_plugin
                        break
                else:
                    # Fallback: try to get from global scope
                    inventory_plugin = None
            else:
                inventory_plugin = None
                
            if inventory_plugin and hasattr(inventory_plugin, 'fetcher'):
                # Plugin is active, get its status
                try: 
                    plugin_status = getattr(inventory_plugin, 'get_plugin_status', lambda: {})()
                except Exception as e: 
                    _log.warning(f"Error getting plugin status: {e}")
                    plugin_status = {
                        'state': 'active',
                        'fetch_state': 'unknown',
                        'metrics': {},
                        'config': {}
                    }

                # Extract connection information
                inventory_fetcher = inventory_plugin.fetcher
                if inventory_fetcher:
                    try:
                        # Test connection to server
                        is_connected = inventory_fetcher.test_connection()
                    except Exception as e:
                        _log.warning(f"Error testing connection: {e}")
                        is_connected = False
                        
                    # Get server URL and connection info
                    server_url = inventory_fetcher.server_url
                    auth_type = getattr(inventory_fetcher, 'auth_type', 'unknown')
                    
                    # Get connection state
                    connection_state = "unknown"
                    try:
                        if hasattr(inventory_fetcher, '_lock'):
                            connection_state = "connected" if is_connected else "disconnected"
                        else:
                            connection_state = "no_lock"
                    except Exception as e:
                        _log.debug(f"Error getting connection state: {e}")
                        connection_state = "unknown"
                    
                    # Get last error if any
                    last_error = None
                    try:
                        if hasattr(inventory_plugin, '_last_error'):
                            last_error = inventory_plugin._last_error
                        elif hasattr(inventory_plugin, 'error'):
                            last_error = getattr(inventory_plugin, 'error', None)
                    except Exception as e:
                        _log.debug(f"Error getting last error: {e}")
                        last_error = None
                    
                    # Get worker thread status if available
                    worker_thread_running = False
                    try:
                        if hasattr(inventory_plugin, '_worker_thread'):
                            worker_thread = inventory_plugin._worker_thread
                            if worker_thread:
                                worker_thread_running = worker_thread.isRunning()
                    except Exception as e:
                        _log.debug(f"Error checking worker thread: {e}")
                    
                    # Get authentication status
                    auth_status = "unknown"
                    try:
                        if auth_type == "jwt" and inventory_fetcher.jwt_token:
                            # Validate JWT token
                            jwt_validation = inventory_fetcher.validate_jwt_token()
                            auth_status = "jwt_valid" if jwt_validation.get('valid') else "jwt_invalid"
                        elif auth_type == "api_token" and inventory_fetcher.api_key:
                            auth_status = "api_token"
                        elif auth_type == "none" and inventory_fetcher.api_key:
                            auth_status = "legacy_api_key"
                        else:
                            auth_status = "no_auth"
                    except Exception as e:
                        _log.debug(f"Error checking auth status: {e}")
                        auth_status = "auth_error"
                    
                    # Get server info if available
                    server_info = {}
                    try:
                        if is_connected:
                            server_info = inventory_fetcher.get_server_info()
                    except Exception as e:
                        _log.debug(f"Error getting server info: {e}")
                    
                    return {
                        'is_connected': is_connected,
                        'server_url': server_url,
                        'last_error': last_error,
                        'plugin_loaded': True,
                        'connection_state': connection_state,
                        'plugin_state': plugin_status.get('state', 'active'),
                        'fetch_state': plugin_status.get('fetch_state', 'unknown'),
                        'auth_status': auth_status,
                        'auth_type': auth_type,
                        'worker_thread_running': worker_thread_running,
                        'server_info': server_info,
                        'metrics': plugin_status.get('metrics', {}),
                        'config': plugin_status.get('config', {}),
                        'timestamp': time.time()
                    }
                else:
                    # Plugin active but no inventory fetcher
                    return {
                        'is_connected': False,
                        'server_url': 'No inventory fetcher',
                        'last_error': 'Inventory fetcher not initialized',
                        'plugin_loaded': True,
                        'connection_state': 'no_fetcher',
                        'plugin_state': 'active',
                        'fetch_state': 'unknown',
                        'auth_status': 'unknown',
                        'auth_type': 'unknown',
                        'worker_thread_running': False,
                        'server_info': {},
                        'metrics': {},
                        'config': {},
                        'timestamp': time.time()
                    }
            else:
                # Plugin not found
                return {
                    'is_connected': False,
                    'server_url': 'Plugin not found',
                    'last_error': 'Inventory fetcher plugin not found on main window',
                    'plugin_loaded': False,
                    'connection_state': 'not_found',
                    'plugin_state': 'unknown',
                    'fetch_state': 'unknown',
                    'auth_status': 'unknown',
                    'auth_type': 'unknown',
                    'worker_thread_running': False,
                    'server_info': {},
                    'metrics': {},
                    'config': {},
                    'timestamp': time.time()
                }
                
        except ImportError as e:
            # PyQt not available
            return {
                'is_connected': False,
                'server_url': 'Import error',
                'last_error': f'Cannot import PyQt: {e}',
                'plugin_loaded': False,
                'connection_state': 'import_error',
                'plugin_state': 'unknown',
                'fetch_state': 'unknown',
                'auth_status': 'unknown',
                'auth_type': 'unknown',
                'worker_thread_running': False,
                'server_info': {},
                'metrics': {},
                'config': {},
                'timestamp': time.time()
            }
            
    except Exception as e:
        _log.error(f"Error getting inventory fetcher status: {e}")
        return {
            'is_connected': False,
            'server_url': 'Error',
            'last_error': str(e),
            'plugin_loaded': False,
            'connection_state': 'error',
            'plugin_state': 'error',
            'fetch_state': 'error',
            'auth_status': 'error',
            'auth_type': 'error',
            'worker_thread_running': False,
            'server_info': {},
            'metrics': {},
            'config': {},
            'timestamp': time.time()
        }


def get_inventory_fetcher_status_safe() -> Dict[str, Any]:
    """Get inventory fetcher status with additional safety checks for threading"""
    try:
        status = get_inventory_fetcher_status()
        
        if status.get('plugin_loaded'):
            try:
                from PyQt6.QtWidgets import QApplication
                
                app = QApplication.instance()
                if app:
                    for widget in app.topLevelWidgets():
                        if hasattr(widget, 'inventory_fetcher_plugin'):
                            inventory_plugin = widget.inventory_fetcher_plugin
                            break
                    else:
                        inventory_plugin = None
                        
                    if inventory_plugin:
                        # Get thread safety information
                        try:
                            if hasattr(inventory_plugin, '_mutex'):
                                mutex_available = True
                            else:
                                mutex_available = False
                                
                            if hasattr(inventory_plugin, '_worker_thread'):
                                worker_thread = inventory_plugin._worker_thread
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
            'fetch_state': 'error',
            'auth_status': 'error',
            'auth_type': 'error',
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
        status = get_inventory_fetcher_status()
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


def get_connection_health() -> Dict[str, Any]:
    """Get detailed connection health information"""
    try:
        status = get_inventory_fetcher_status()
        
        if not status.get('plugin_loaded'):
            return {
                'healthy': False,
                'status': 'plugin_not_loaded',
                'message': 'Inventory fetcher plugin is not loaded'
            }
        
        if not status.get('is_connected'):
            return {
                'healthy': False,
                'status': 'disconnected',
                'message': f"Not connected to server: {status.get('last_error', 'Unknown error')}"
            }
        
        # Check authentication
        auth_status = status.get('auth_status', 'unknown')
        if auth_status in ['jwt_invalid', 'auth_error']:
            return {
                'healthy': False,
                'status': 'auth_failed',
                'message': f"Authentication failed: {auth_status}"
            }
        
        # Check worker thread
        if not status.get('worker_thread_running', False):
            return {
                'healthy': False,
                'status': 'worker_thread_down',
                'message': 'Worker thread is not running'
            }
        
        # All checks passed
        return {
            'healthy': True,
            'status': 'healthy',
            'message': f"Connected to {status.get('server_url', 'unknown server')}",
            'auth_type': status.get('auth_type', 'unknown'),
            'connection_state': status.get('connection_state', 'unknown')
        }
        
    except Exception as e:
        _log.error(f"Error getting connection health: {e}")
        return {
            'healthy': False,
            'status': 'error',
            'message': f"Error checking health: {e}"
        }