

"""
Patch for roast properties dialog to integrate with inventory fetcher plugin
"""
import logging
from typing import Dict, Any, Optional

try:
    from PyQt6.QtWidgets import QComboBox, QPushButton, QHBoxLayout, QVBoxLayout, QLabel, QFrame
    from PyQt6.QtCore import pyqtSlot
except ImportError:
    from PyQt5.QtWidgets import QComboBox, QPushButton, QHBoxLayout, QVBoxLayout, QLabel, QFrame
    from PyQt5.QtCore import pyqtSlot

_log = logging.getLogger(__name__)

def setup_inventory_integration(roast_properties_dialog, inventory_plugin):
    """
    Set up inventory integration for the roast properties dialog
    
    Args:
        roast_properties_dialog: The editGraphDlg instance
        inventory_plugin: The InventoryFetcherPlugin instance
    """
    try:
        # Register the dialog with the plugin
        inventory_plugin.register_roast_properties_dialog(roast_properties_dialog)
        
        # Create inventory combo box
        inventory_combo = QComboBox(roast_properties_dialog)
        inventory_combo.setObjectName("inventory_combo")
        inventory_combo.addItem("Select from inventory...")
        
        # Create refresh button
        refresh_button = QPushButton("Refresh", roast_properties_dialog)
        refresh_button.setObjectName("inventory_refresh_button")
        refresh_button.clicked.connect(lambda: refresh_inventory(roast_properties_dialog, inventory_plugin))
        
        # Create layout for inventory controls
        inventory_layout = QHBoxLayout()
        inventory_layout.addWidget(QLabel("Inventory:"))
        inventory_layout.addWidget(inventory_combo)
        inventory_layout.addWidget(refresh_button)
        inventory_layout.addStretch()
        
        # Find a good place to add the inventory controls
        # Look for the beans edit field and add the inventory controls near it
        if hasattr(roast_properties_dialog, 'beansedit'):
            # Get the parent layout of the beans edit field
            beans_parent = roast_properties_dialog.beansedit.parent()
            if beans_parent and hasattr(beans_parent, 'layout'):
                layout = beans_parent.layout()
                if layout:
                    # Add inventory controls after the beans field
                    layout.addLayout(inventory_layout)
        
        # Connect inventory combo box selection
        inventory_combo.currentIndexChanged.connect(
            lambda index: on_inventory_bean_selected(roast_properties_dialog, inventory_plugin, index)
        )
        
        # store references for later use
        roast_properties_dialog.inventory_combo = inventory_combo
        roast_properties_dialog.inventory_plugin = inventory_plugin
        
        # init population
        refresh_inventory(roast_properties_dialog, inventory_plugin)
        
        print(f"DEBUG: Combo box items after setup: {[inventory_combo.itemText(i) for i in range(inventory_combo.count())]}")
        
        _log.info("Inventory integration set up successfully")
            
    except Exception as e:
        _log.error(f"Error setting up inventory integration: {e}")

def refresh_inventory(roast_properties_dialog, inventory_plugin):
    """Refresh the inventory data and populate the combo box"""
    try:
        # Fetch fresh data
        inventory_plugin.fetch_beans()
        
        # Populate the combo box
        if hasattr(roast_properties_dialog, 'inventory_combo'):
            inventory_plugin.populate_beans_combo(roast_properties_dialog.inventory_combo)
            
            combo = roast_properties_dialog.inventory_combo
            items = [combo.itemText(i) for i in range(combo.count())]
            _log.info(f"Combo box populated with {len(items)} items: {items}")
        else:
            _log.error("No inventory_combo found to populate")
            
        _log.info("Inventory refreshed successfully")
        
    except Exception as e:
        _log.error(f"Error refreshing inventory: {e}")

def on_inventory_bean_selected(roast_properties_dialog, inventory_plugin, index):
    """Handle inventory bean selection"""
    try:
        if index > 0:  # skip "Select from inventory..." item
            bean_data = inventory_plugin.get_selected_bean(roast_properties_dialog.inventory_combo)
            if bean_data:
                populate_fields_from_inventory(roast_properties_dialog, bean_data)
                mark_inventory_fields(roast_properties_dialog, True)
            else:
                mark_inventory_fields(roast_properties_dialog, False)
        else:
            mark_inventory_fields(roast_properties_dialog, False)
            
    except Exception as e:
        _log.error(f"Error handling inventory selection: {e}")

def populate_fields_from_inventory(roast_properties_dialog, bean_data: Dict[str, Any]):
    """Populate roast properties fields with inventory data"""
    try:
        # populate basic bean information
        if 'name' in bean_data and hasattr(roast_properties_dialog, 'beansedit'):
            roast_properties_dialog.beansedit.setPlainText(bean_data['name'])
        
        # populate density if available
        if 'density' in bean_data and hasattr(roast_properties_dialog, 'bean_density_in_edit'):
            density = bean_data['density']
            if isinstance(density, (int, float)):
                roast_properties_dialog.bean_density_in_edit.setText(str(density))
        
        # populate moisture if available
        if 'moisture' in bean_data and hasattr(roast_properties_dialog, 'moisture_greens_edit'):
            moisture = bean_data['moisture']
            if isinstance(moisture, (int, float)):
                roast_properties_dialog.moisture_greens_edit.setText(str(moisture))
        
        # populate bean size if available (screen)
        if 'bean_size_min' in bean_data and hasattr(roast_properties_dialog, 'bean_size_min_edit'):
            size_min = bean_data['bean_size_min']
            if isinstance(size_min, (int, float)):
                roast_properties_dialog.bean_size_min_edit.setText(str(size_min))
        
        if 'bean_size_max' in bean_data and hasattr(roast_properties_dialog, 'bean_size_max_edit'):
            size_max = bean_data['bean_size_max']
            if isinstance(size_max, (int, float)):
                roast_properties_dialog.bean_size_max_edit.setText(str(size_max))
        
        # TODO: populate title field, stock, blend, store fields
        
        _log.info(f"Populated fields with inventory data: {bean_data.get('name', 'Unknown')}")
        
    except Exception as e:
        _log.error(f"Error populating fields from inventory: {e}")

def mark_inventory_fields(roast_properties_dialog, marked: bool):
    """Mark fields that were populated from inventory"""
    try:
        if marked:
            _log.info("Fields marked as populated from inventory")
        else:
            _log.info("Fields unmarked")
            
    except Exception as e:
        _log.error(f"Error marking inventory fields: {e}")

def debug_inventory_combo(roast_properties_dialog):
    """Debug method to check inventory combo box state"""
    if hasattr(roast_properties_dialog, 'inventory_combo'):
        combo = roast_properties_dialog.inventory_combo
        items = [combo.itemText(i) for i in range(combo.count())]
        print(f"Inventory combo items: {items}")
        print(f"Current index: {combo.currentIndex()}")
        print(f"Current text: {combo.currentText()}")
        return items
    else:
        print("No inventory_combo found")
        return []