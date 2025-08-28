import logging

_log = logging.getLogger(__name__)

def get_broadcaster_status():
    """Get the current status of the live broadcast plugin"""
    try:
        # Try to get the plugin instance from the plugin manager
        # First, try to import the plugin manager
        try:
            from ..manager import PluginManager
            from ..base import PluginState
            
            # Get the main application window to access plugin manager
            # This is a bit of a hack, but it's the cleanest way to access the plugin
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
                    plugin_status = live_broadcast_plugin.get_plugin_status()
                    
                    # Extract connection information
                    broadcaster = getattr(live_broadcast_plugin, 'broadcaster', None)
                    if broadcaster:
                        is_connected = broadcaster.is_connected()
                        server_url = f"{broadcaster.host}:{broadcaster.port}"
                        
                        # Get connection state
                        if hasattr(broadcaster, '_is_connected'):
                            if broadcaster._is_connected:
                                connection_state = "connected"
                            elif broadcaster.reconnect_attempts > 0:
                                connection_state = "reconnecting"
                            else:
                                connection_state = "disconnected"
                        else:
                            connection_state = "unknown"
                        
                        # Get last error if any
                        last_error = None
                        if hasattr(broadcaster, '_last_error'):
                            last_error = broadcaster._last_error
                        elif hasattr(broadcaster, 'error'):
                            last_error = getattr(broadcaster, 'error', None)
                        
                        return {
                            'is_connected': is_connected,
                            'server_url': server_url,
                            'last_error': last_error,
                            'plugin_loaded': True,
                            'connection_state': connection_state,
                            'plugin_state': plugin_status.get('state', 'unknown'),
                            'broadcast_state': plugin_status.get('broadcast_state', 'unknown'),
                            'metrics': plugin_status.get('metrics', {}),
                            'config': plugin_status.get('config', {})
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
                            'metrics': {},
                            'config': plugin_status.get('config', {})
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
                        'metrics': {},
                        'config': {}
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
                    'metrics': {},
                    'config': {}
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
                'metrics': {},
                'config': {}
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
            'metrics': {},
            'config': {}
        }
