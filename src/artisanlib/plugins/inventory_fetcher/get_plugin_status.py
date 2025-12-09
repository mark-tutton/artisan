import logging
import time
from typing import Dict, Any, Optional

_log = logging.getLogger(__name__)


def get_inventory_fetcher_status() -> Dict[str, Any]:

def get_connection_pool_status() -> Dict[str, Any]:
    """Get detailed connection pool status"""
    try:
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app:
            for widget in app.topLevelWidgets():
                if hasattr(widget, "inventory_fetcher_plugin"):
                    inventory_plugin = widget.inventory_fetcher_plugin
                    if inventory_plugin and hasattr(inventory_plugin, "fetcher"):
                        fetcher = inventory_plugin.fetcher
                        if fetcher and hasattr(fetcher, "session") and fetcher.session:
                            # Get session info
                            session = fetcher.session
                            pool_info = {}

                            # Get adapter info
                            for scheme in ["http://", "https://"]:
                                try:
                                    adapter = session.get_adapter(scheme)
                                    if adapter:
                                        pool_info[scheme] = {
                                            "pool_connections": getattr(adapter, "config", {}).get(
                                                "pool_connections", "unknown"
                                            ),
                                            "pool_maxsize": getattr(adapter, "config", {}).get(
                                                "pool_maxsize", "unknown"
                                            ),
                                            "pool_block": getattr(adapter, "config", {}).get(
                                                "pool_block", "unknown"
                                            ),
                                        }
                                except Exception as e:
                                    pool_info[scheme] = {"error": str(e)}

                            return {
                                "status": "success",
                                "fetcher_closed": (
                                    fetcher._closed if hasattr(fetcher, "_closed") else False
                                ),
                                "session_closed": (
                                    session.closed if hasattr(session, "closed") else False
                                ),
                                "pool_info": pool_info,
                                "timestamp": time.time(),
                            }

        return {
            "status": "no_session",
            "message": "No active session found",
            "timestamp": time.time(),
        }

    except Exception as e:
        return {"status": "error", "message": f"Error: {e}", "timestamp": time.time()}


def get_health_check_status() -> Dict[str, Any]:
    """Get comprehensive health check status for the inventory fetcher"""
    try:
        # Get basic status
        status = get_inventory_fetcher_status()

        # Get connection health
        connection_health = get_connection_health()

        # Get connection pool status
        pool_status = get_connection_pool_status()

        # Combine all status information
        health_status = {
            "timestamp": time.time(),
            "overall_healthy": connection_health.get("healthy", False),
            "connection_health": connection_health,
            "inventory_status": status,
            "pool_status": pool_status,
            "thread_safe": is_plugin_thread_safe(),
        }

        # Determine overall health
        if not connection_health.get("healthy", False):
            health_status["status"] = "unhealthy"
            health_status["message"] = connection_health.get("message", "Unknown health issue")
        elif not status.get("connected", False):
            health_status["status"] = "disconnected"
            health_status["message"] = "Not connected to server"
        elif not health_status["thread_safe"]:
            health_status["status"] = "threading_issue"
            health_status["message"] = "Threading configuration issue"
        else:
            health_status["status"] = "healthy"
            health_status["message"] = "All systems operational"

        return health_status

    except Exception as e:
        _log.error(f"Error getting health check status: {e}")
        return {
            "timestamp": time.time(),
            "status": "error",
            "overall_healthy": False,
            "message": f"Health check failed: {e}",
            "connection_health": {"healthy": False, "status": "error"},
            "inventory_status": {"status": "error"},
            "pool_status": {"status": "error"},
            "thread_safe": False,
        }


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
                    if hasattr(widget, "inventory_fetcher_plugin"):
                        inventory_plugin = widget.inventory_fetcher_plugin
                        break
                else:
                    # Fallback: try to get from global scope
                    inventory_plugin = None
            else:
                inventory_plugin = None

            if inventory_plugin and hasattr(inventory_plugin, "fetcher"):
                # Plugin is active, get its status
                try:
                    plugin_status = getattr(inventory_plugin, "get_plugin_status", lambda: {})()
                except Exception as e:
                    _log.warning(f"Error getting plugin status: {e}")
                    plugin_status = {
                        "state": "active",
                        "fetch_state": "unknown",
                        "metrics": {},
                        "config": {},
                    }

                # Extract connection information
                inventory_fetcher = inventory_plugin.fetcher
                if inventory_fetcher:
                    # Check if fetcher is closed to avoid connection leaks
                    if hasattr(inventory_fetcher, "_closed") and inventory_fetcher._closed:
                        return {
                            "status": "plugin_closed",
                            "plugin_loaded": True,  # Plugin is loaded but closed
                            "message": "Inventory fetcher is closed",
                            "timestamp": time.time(),
                            "plugin_status": plugin_status,
                        }

                    # DON'T test connection during status check - this can hang the app
                    # Instead, determine connection status from existing data
                    is_connected = False
                    try:
                        # Check if we have beans data (indicates successful connection)
                        beans_count = 0
                        if hasattr(inventory_plugin, "beans_data"):
                            beans_count = len(inventory_plugin.beans_data)

                        # Check if we have a recent successful fetch
                        last_fetch_time = 0
                        if hasattr(inventory_plugin, "_last_fetch_time"):
                            last_fetch_time = inventory_plugin._last_fetch_time

                        # Consider connected if we have data or recent fetch
                        current_time = time.time()
                        recent_fetch = (current_time - last_fetch_time) < 3600  # Within last hour

                        is_connected = beans_count > 0 or recent_fetch

                    except Exception as e:
                        _log.debug(f"Error determining connection status: {e}")
                        is_connected = False

                    # Get server URL and connection info from config, not fetcher
                    config = inventory_plugin.config
                    server_url = config.get_effective_url() if config else "unknown"
                    # Fixed: Remove use_gateway check since new config always uses gateway
                    auth_type = "global_auth"  # New config always uses global auth manager

                    # Get connection state
                    connection_state = "unknown"
                    try:
                        if hasattr(inventory_fetcher, "_lock"):
                            connection_state = "connected" if is_connected else "disconnected"
                        else:
                            connection_state = "no_lock"
                    except Exception as e:
                        _log.debug(f"Error getting connection state: {e}")
                        connection_state = "unknown"

                    # Get last error if any
                    last_error = None
                    try:
                        if hasattr(inventory_plugin, "_last_error"):
                            last_error = inventory_plugin._last_error
                        elif hasattr(inventory_plugin, "error"):
                            last_error = getattr(inventory_plugin, "error", None)
                    except Exception as e:
                        _log.debug(f"Error getting last error: {e}")
                        last_error = None

                    # Get worker thread status if available
                    worker_thread_running = False
                    try:
                        if hasattr(inventory_plugin, "_worker_thread"):
                            worker_thread = inventory_plugin._worker_thread
                            if worker_thread:
                                worker_thread_running = worker_thread.isRunning()
                    except Exception as e:
                        _log.debug(f"Error checking worker thread: {e}")

                    # Get authentication status - simplified for new config
                    auth_status = "unknown"
                    try:
                        if config:
                            # Check if global auth manager is authenticated
                            if hasattr(inventory_plugin, 'auth_manager') and inventory_plugin.auth_manager.is_authenticated():
                                auth_status = "authenticated"
                            else:
                                auth_status = "not_authenticated"
                        else:
                            auth_status = "no_config"
                    except Exception as e:
                        _log.debug(f"Error getting auth status: {e}")
                        auth_status = "error"

                    # Get beans count
                    beans_count = 0
                    try:
                        if hasattr(inventory_plugin, "beans_data"):
                            beans_count = len(inventory_plugin.beans_data)
                    except Exception as e:
                        _log.debug(f"Error getting beans count: {e}")

                    # Get fetch status
                    fetch_in_progress = False
                    try:
                        if hasattr(inventory_plugin, "_fetch_in_progress"):
                            fetch_in_progress = inventory_plugin._fetch_in_progress
                    except Exception as e:
                        _log.debug(f"Error getting fetch status: {e}")

                    # Get last fetch time
                    last_fetch_time = 0
                    try:
                        if hasattr(inventory_plugin, "_last_fetch_time"):
                            last_fetch_time = inventory_plugin._last_fetch_time
                    except Exception as e:
                        _log.debug(f"Error getting last fetch time: {e}")

                    # Get session info if available
                    session_info = {}
                    try:
                        if hasattr(inventory_fetcher, "session") and inventory_fetcher.session:
                            # Get connection pool info without creating new connections
                            adapter = inventory_fetcher.session.get_adapter("http://")
                            if adapter:
                                session_info = {
                                    "pool_connections": getattr(adapter, "config", {}).get(
                                        "pool_connections", "unknown"
                                    ),
                                    "pool_maxsize": getattr(adapter, "config", {}).get(
                                        "pool_maxsize", "unknown"
                                    ),
                                    "closed": (
                                        inventory_fetcher._closed
                                        if hasattr(inventory_fetcher, "_closed")
                                        else False
                                    ),
                                }
                    except Exception as e:
                        _log.debug(f"Error getting session info: {e}")

                    return {
                        "status": "active",
                        "plugin_loaded": True,  # Plugin is loaded and active
                        "connected": is_connected,
                        "server_url": server_url,
                        "auth_type": auth_type,
                        "auth_status": auth_status,
                        "connection_state": connection_state,
                        "beans_count": beans_count,
                        "fetch_in_progress": fetch_in_progress,
                        "last_fetch_time": last_fetch_time,
                        "worker_thread_running": worker_thread_running,
                        "last_error": last_error,
                        "session_info": session_info,
                        "timestamp": time.time(),
                        "plugin_status": plugin_status,
                    }
                else:
                    return {
                        "status": "no_fetcher",
                        "plugin_loaded": True,  # Plugin is loaded but no fetcher
                        "message": "No fetcher instance available",
                        "timestamp": time.time(),
                        "plugin_status": plugin_status,
                    }
            else:
                return {
                    "status": "plugin_not_found",
                    "plugin_loaded": False,  # Plugin not found
                    "message": "Inventory fetcher plugin not found or not active",
                    "timestamp": time.time(),
                }

        except ImportError:
            # Fallback for PyQt5
            try:
                from PyQt5.QtWidgets import QApplication

                app = QApplication.instance()
                if app:
                    for widget in app.topLevelWidgets():
                        if hasattr(widget, "inventory_fetcher_plugin"):
                            inventory_plugin = widget.inventory_fetcher_plugin
                            break
                    else:
                        inventory_plugin = None
                else:
                    inventory_plugin = None

                if inventory_plugin:
                    return {
                        "status": "active_pyqt5",
                        "plugin_loaded": True,  # Plugin found in PyQt5
                        "message": "Plugin found (PyQt5)",
                        "timestamp": time.time(),
                    }
                else:
                    return {
                        "status": "not_found_pyqt5",
                        "plugin_loaded": False,  # Plugin not found in PyQt5
                        "message": "Plugin not found (PyQt5)",
                        "timestamp": time.time(),
                    }
            except Exception as e:
                return {
                    "status": "error_pyqt5",
                    "plugin_loaded": False,  # Error in PyQt5
                    "message": f"Error with PyQt5: {e}",
                    "timestamp": time.time(),
                }

    except Exception as e:
        _log.error(f"Error getting inventory fetcher status: {e}")
        return {
            "status": "error",
            "plugin_loaded": False,  # Error getting status
            "message": f"Error: {e}",
            "timestamp": time.time(),
        }


def is_plugin_thread_safe() -> bool:
    """Check if the plugin is properly configured for threading"""
    try:
        status = get_inventory_fetcher_status()
        if status.get("plugin_loaded"):
            threading_info = status.get("threading_info", {})
            return threading_info.get("mutex_available", False) and threading_info.get(
                "worker_thread_running", False
            )
        return False
    except Exception as e:
        _log.error(f"Error checking thread safety: {e}")
        return False


def get_connection_health() -> Dict[str, Any]:
    """Get detailed connection health information"""
    try:
        status = get_inventory_fetcher_status()

        if not status.get("plugin_loaded"):
            return {
                "healthy": False,
                "status": "plugin_not_loaded",
                "message": "Inventory fetcher plugin is not loaded",
            }

        # Fix: Use 'connected' instead of 'is_connected'
        if not status.get("connected", False):
            return {
                "healthy": False,
                "status": "disconnected",
                "message": f"Not connected to server: {status.get('last_error', 'Unknown error')}",
            }

        # Check authentication
        auth_status = status.get("auth_status", "unknown")
        if auth_status in ["jwt_invalid", "auth_error"]:
            return {
                "healthy": False,
                "status": "auth_failed",
                "message": f"Authentication failed: {auth_status}",
            }

        # Check worker thread - make this optional since it might not always be running
        worker_thread_running = status.get("worker_thread_running", False)
        if worker_thread_running is False and status.get("beans_count", 0) == 0:
            # Only consider it unhealthy if no beans are loaded and no worker thread
            return {
                "healthy": False,
                "status": "worker_thread_down",
                "message": "Worker thread is not running and no data loaded",
            }

        # All checks passed
        return {
            "healthy": True,
            "status": "healthy",
            "message": f"Connected to {status.get('server_url', 'unknown server')}",
            "auth_type": status.get("auth_type", "unknown"),
            "connection_state": status.get("connection_state", "unknown"),
        }

    except Exception as e:
        _log.error(f"Error getting connection health: {e}")
        return {"healthy": False, "status": "error", "message": f"Error checking health: {e}"}