import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .live_broadcast_plugin import LiveBroadcastPlugin

try:
    from .live_broadcast_plugin import LiveBroadcastPlugin
    __all__ = ['LiveBroadcastPlugin']
except ImportError as e:
    logging.error(f"Failed to import LiveBroadcastPlugin: {e}")
    __all__ = []

PLUGIN_NAME = "Live Broadcast"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Real-time roast data broadcasting via Socket.IO"
PLUGIN_REQUIREMENTS = ["python-socketio"]

def get_plugin_info():
    """Get plugin information for registration"""
    return {
        "name": PLUGIN_NAME,
        "version": PLUGIN_VERSION,
        "description": PLUGIN_DESCRIPTION,
        "requirements": PLUGIN_REQUIREMENTS,
        "class": LiveBroadcastPlugin if 'LiveBroadcastPlugin' in globals() else None
    }