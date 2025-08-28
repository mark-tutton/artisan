# from .inventory_fetcher_plugin import InventoryFetcherPlugin

# __all__ = ['InventoryFetcherPlugin']

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .inventory_fetcher_plugin import InventoryFetcherPlugin

try:
    from .inventory_fetcher_plugin import InventoryFetcherPlugin
    __all__ = ['InventoryFetcherPlugin']
except ImportError as e:
    logging.error(f"Failed to import InventoryFetcherPlugin: {e}")
    __all__ = []

PLUGIN_NAME = "Inventory Fetcher"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "Fetch inventory data from a server"
PLUGIN_REQUIREMENTS = ["requests"]

def get_plugin_info():
    """Get plugin information for registration"""
    return {
        "name": PLUGIN_NAME,
        "version": PLUGIN_VERSION,
        "description": PLUGIN_DESCRIPTION,
        "requirements": PLUGIN_REQUIREMENTS,
        "class": InventoryFetcherPlugin if 'InventoryFetcherPlugin' in globals() else None
    }