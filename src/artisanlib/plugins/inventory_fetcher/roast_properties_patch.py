import logging
from typing import Dict, Any, Optional

try:
    from PyQt6.QtWidgets import (
        QComboBox,
        QPushButton,
        QHBoxLayout,
        QVBoxLayout,
        QLabel,
        QFrame,
        QWidget,
        QSizePolicy,
        QCompleter,
    )
    from PyQt6.QtCore import pyqtSlot, QTimer, QMutex
except ImportError:
    from PyQt5.QtWidgets import (
        QComboBox,
        QPushButton,
        QHBoxLayout,
        QVBoxLayout,
        QLabel,
        QFrame,
        QWidget,
        QSizePolicy,
        QCompleter,
    )
    from PyQt5.QtCore import pyqtSlot, QTimer, QMutex

_log = logging.getLogger(__name__)

def setup_inventory_integration(roast_properties_dialog, inventory_plugin):
    """Set up inventory integration for the roast properties dialog with thread safety"""
    try:
        _log.info("DEBUG: Starting inventory integration setup...")
        _log.info(" Starting inventory integration setup...")

        # Register the dialog with the plugin
        inventory_plugin.register_roast_properties_dialog(roast_properties_dialog)
        _log.info("DEBUG: Dialog registered with plugin")

        # Create inventory combo box
        inventory_combo = QComboBox(roast_properties_dialog)
        inventory_combo.setObjectName("inventory_combo")
        inventory_combo.addItem("Select/Search from inventory...")
        inventory_combo.setMinimumWidth(200)
        _log.info("DEBUG: Combo box created")

         # Enable search 
        inventory_combo.setEditable(True)
        inventory_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        inventory_combo.completer().setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

        inventory_combo.setMaxVisibleItems(10) 

        inventory_combo.lineEdit().setPlaceholderText("Type to search...")
        
        inventory_combo.lineEdit().focusInEvent = lambda event: inventory_combo.lineEdit().setPlaceholderText("")
        inventory_combo.lineEdit().focusOutEvent = lambda event: inventory_combo.lineEdit().setPlaceholderText("Type to search...")
        
        
        

        # Create refresh button
        refresh_button = QPushButton("Refresh", roast_properties_dialog)
        refresh_button.setObjectName("inventory_refresh_button")
        refresh_button.clicked.connect(
            lambda: refresh_inventory(roast_properties_dialog, inventory_plugin)
        )
        _log.info("DEBUG: Refresh button created")

        # Create layout for inventory controls
        inventory_layout = QHBoxLayout()
        inventory_layout.addWidget(QLabel("Inventory:"))
        inventory_layout.addWidget(inventory_combo, 1)
        inventory_layout.addWidget(refresh_button, 0)
        inventory_layout.addStretch(0)

        # Create separator and spacing
        spacer_frame = QFrame()
        try:
            # PyQt6
            spacer_frame.setFrameShape(QFrame.FrameShape.HLine)
            spacer_frame.setFrameShadow(QFrame.FrameShadow.Sunken)
        except AttributeError:
            try:
                # PyQt5
                spacer_frame.setFrameShape(QFrame.HLine)
                spacer_frame.setFrameShadow(QFrame.Sunken)
            except AttributeError:
                # Fallback - just create a simple line
                spacer_frame.setMaximumHeight(1)
                spacer_frame.setMinimumHeight(1)
                spacer_frame.setStyleSheet("background-color: gray;")

        spacer_frame.setMaximumHeight(2)
        spacer_frame.setMinimumHeight(2)

        inventory_container_widget = QWidget()
        inventory_container_layout = QVBoxLayout(inventory_container_widget)
        inventory_container_layout.addWidget(spacer_frame)
        inventory_container_layout.addSpacing(8)
        inventory_container_layout.addLayout(inventory_layout)
        inventory_container_layout.addSpacing(4)

        if hasattr(roast_properties_dialog, "layout"):
            main_layout = roast_properties_dialog.layout()
            if main_layout:
                last_index = main_layout.count() - 1
                if last_index >= 0:
                    main_layout.insertWidget(last_index, inventory_container_widget)

        inventory_combo.currentIndexChanged.connect(
            lambda index: on_inventory_bean_selected(
                roast_properties_dialog, inventory_plugin, index
            )
        )

        if hasattr(inventory_plugin, "signals"):
            try:
                inventory_plugin._inventory_updated_slot = lambda beans_data: on_inventory_updated(
                    roast_properties_dialog, beans_data
                )
                inventory_plugin._fetch_completed_slot = lambda beans_data: on_fetch_completed(
                    roast_properties_dialog, beans_data
                )
                inventory_plugin._fetch_failed_slot = lambda error: on_fetch_failed(
                    roast_properties_dialog, error
                )

                inventory_plugin.signals.inventory_updated.connect(
                    inventory_plugin._inventory_updated_slot
                )
                inventory_plugin.signals.fetch_completed.connect(
                    inventory_plugin._fetch_completed_slot
                )
                inventory_plugin.signals.fetch_failed.connect(inventory_plugin._fetch_failed_slot)
            except Exception as e:
                _log.warning(f"Could not connect to plugin signals: {e}")

        # store references for later use
        roast_properties_dialog.inventory_combo = inventory_combo
        roast_properties_dialog.inventory_plugin = inventory_plugin
        roast_properties_dialog._inventory_mutex = QMutex() 

        # init population
        refresh_inventory(roast_properties_dialog, inventory_plugin)

        # Restore previously selected bean if available
        restore_selected_bean(roast_properties_dialog, inventory_plugin)

        _log.info("Inventory integration set up successfully")

    except Exception as e:
        _log.error(f"ERROR: Failed to set up inventory integration: {e}")
        _log.error(f"Error setting up inventory integration: {e}")
        import traceback

        traceback.print_exc()


def restore_selected_bean(roast_properties_dialog, inventory_plugin):
    """Restore the previously selected bean in the combo box"""
    try:
        if hasattr(roast_properties_dialog, "inventory_combo"):
            combo = roast_properties_dialog.inventory_combo
            # Get the last selected bean from the plugin
            last_selected = getattr(inventory_plugin, "_last_selected_bean", None)
            if last_selected and combo.count() > 1:
                # Find the bean in the combo box
                for i in range(1, combo.count()):  # Skip first item "Select from inventory..."
                    if combo.itemText(i) == last_selected:
                        combo.setCurrentIndex(i)
                        # Trigger the selection handler
                        on_inventory_bean_selected(roast_properties_dialog, inventory_plugin, i)
                        break
    except Exception as e:
        _log.debug(f"Error restoring selected bean: {e}")


def on_inventory_bean_selected(roast_properties_dialog, inventory_plugin, index):
    """Handle inventory bean selection with thread safety"""
    try:
        if index > 0:  # skip "Select from inventory..." item
            if hasattr(roast_properties_dialog, "inventory_combo"):
                selected_bean = roast_properties_dialog.inventory_combo.itemText(index)
                inventory_plugin._last_selected_bean = selected_bean

            QTimer.singleShot(
                0,
                lambda: _handle_bean_selection_safe(
                    roast_properties_dialog, inventory_plugin, index
                ),
            )
        else:
            mark_inventory_fields(roast_properties_dialog, False)

    except Exception as e:
        _log.error(f"Error handling inventory selection: {e}")


def refresh_inventory(roast_properties_dialog, inventory_plugin):
    """Refresh the inventory data and populate the combo box with thread safety"""
    try:
        QTimer.singleShot(
            0, lambda: _refresh_inventory_safe(roast_properties_dialog, inventory_plugin)
        )
    except Exception as e:
        _log.error(f"Error scheduling inventory refresh: {e}")


def _refresh_inventory_safe(roast_properties_dialog, inventory_plugin):
    """Safely refresh inventory in main thread"""
    try:
        # Check if plugin already has data before fetching
        existing_data = inventory_plugin.get_beans_data()
        if not existing_data:
            # Only fetch if no data
            if hasattr(inventory_plugin, "execute_in_worker"):
                inventory_plugin.execute_in_worker("refresh_inventory", inventory_plugin.fetch_beans)
            else:
                # Fallback to direct call
                inventory_plugin.fetch_beans()
        else:
            # Use existing data
            _log.info(f"Using existing inventory data ({len(existing_data)} items)")

        # Populate the combo box
        if hasattr(roast_properties_dialog, "inventory_combo"):
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
    """Handle inventory bean selection with thread safety"""
    try:
        if index > 0:  # skip "Select from inventory..." item
            QTimer.singleShot(
                0,
                lambda: _handle_bean_selection_safe(
                    roast_properties_dialog, inventory_plugin, index
                ),
            )
        else:
            mark_inventory_fields(roast_properties_dialog, False)

    except Exception as e:
        _log.error(f"Error handling inventory selection: {e}")


def _handle_bean_selection_safe(roast_properties_dialog, inventory_plugin, index):
    """Safely handle bean selection in main thread"""
    try:
        bean_data = inventory_plugin.get_selected_bean(roast_properties_dialog.inventory_combo)
        if bean_data:
            populate_fields_from_inventory(roast_properties_dialog, bean_data)
            mark_inventory_fields(roast_properties_dialog, True)

            # Update the roast title with the selected bean name
            if hasattr(roast_properties_dialog, "titleedit") and bean_data.get("name"):
                bean_name = bean_data["name"]
                roast_properties_dialog.titleedit.setEditText(bean_name)
                _log.info(f"Updated roast title to: {bean_name}")

        else:
            mark_inventory_fields(roast_properties_dialog, False)
    except Exception as e:
        _log.error(f"Error handling bean selection safely: {e}")


def on_inventory_updated(roast_properties_dialog, beans_data):
    """Handle inventory updates from plugin signals"""
    try:
        QTimer.singleShot(0, lambda: _update_combo_safe(roast_properties_dialog, beans_data))
    except Exception as e:
        _log.error(f"Error handling inventory update: {e}")


def on_fetch_completed(roast_properties_dialog, beans_data):
    """Handle fetch completion from plugin signals"""
    try:
        _log.info("Fetch completed, updating combo box")
        on_inventory_updated(roast_properties_dialog, beans_data)
    except Exception as e:
        _log.error(f"Error handling fetch completion: {e}")


def on_fetch_failed(roast_properties_dialog, error):
    """Handle fetch failure from plugin signals"""
    try:
        _log.warning(f"Fetch failed: {error}")
    except Exception as e:
        _log.error(f"Error handling fetch failure: {e}")


def _update_combo_safe(roast_properties_dialog, beans_data):
    """Safely update combo box in main thread"""
    try:
        if hasattr(roast_properties_dialog, "inventory_combo"):
            combo = roast_properties_dialog.inventory_combo
            combo.clear()
            combo.addItem("Select from inventory...")

            for bean in beans_data:
                name = bean.get("name", "Unknown")
                if "origin" in bean and bean["origin"]:
                    name += f" ({bean['origin']})"
                if "variety" in bean and bean["variety"]:
                    name += f" - {bean['variety']}"
                combo.addItem(name, bean)

            _log.info(f"Combo box updated with {len(beans_data)} items")
    except Exception as e:
        _log.error(f"Error updating combo box safely: {e}")


def populate_fields_from_inventory(roast_properties_dialog, bean_data: Dict[str, Any]):
    """Populate roast properties fields with inventory data with thread safety"""
    try:
        mutex = getattr(roast_properties_dialog, "_inventory_mutex", None)

        def _populate():
            try:
                # populate basic bean information
                if "name" in bean_data and hasattr(roast_properties_dialog, "beansedit"):
                    roast_properties_dialog.beansedit.setPlainText(bean_data["name"])

                # populate density if available
                if "density" in bean_data and hasattr(
                    roast_properties_dialog, "bean_density_in_edit"
                ):
                    density = bean_data["density"]
                    if isinstance(density, (int, float)):
                        roast_properties_dialog.bean_density_in_edit.setText(str(density))

                # populate moisture if available
                if "moisture" in bean_data and hasattr(
                    roast_properties_dialog, "moisture_greens_edit"
                ):
                    moisture = bean_data["moisture"]
                    if isinstance(moisture, (int, float)):
                        roast_properties_dialog.moisture_greens_edit.setText(str(moisture))

                # populate bean size if available (screen)
                if "bean_size_min" in bean_data and hasattr(
                    roast_properties_dialog, "bean_size_min_edit"
                ):
                    size_min = bean_data["bean_size_min"]
                    if isinstance(size_min, (int, float)):
                        roast_properties_dialog.bean_density_in_edit.setText(str(size_min))

                if "bean_size_max" in bean_data and hasattr(
                    roast_properties_dialog, "bean_size_max_edit"
                ):
                    size_max = bean_data["bean_size_max"]
                    if isinstance(size_max, (int, float)):
                        roast_properties_dialog.bean_size_max_edit.setText(str(size_max))

                # TODO: populate title field, stock, blend, store fields (these are only active when + is active?)

                _log.info(
                    f"Populated fields with inventory data: {bean_data.get('name', 'Unknown')}"
                )

            except Exception as e:
                _log.error(f"Error populating fields: {e}")

        if mutex:
            mutex.lock()
            try:
                QTimer.singleShot(0, _populate)
            finally:
                mutex.unlock()
        else:
            QTimer.singleShot(0, _populate)

    except Exception as e:
        _log.error(f"Error populating fields from inventory: {e}")


def mark_inventory_fields(roast_properties_dialog, marked: bool):
    """Mark fields that were populated from inventory with thread safety"""
    try:
        QTimer.singleShot(0, lambda: _mark_fields_safe(roast_properties_dialog, marked))
    except Exception as e:
        _log.error(f"Error scheduling field marking: {e}")


def _mark_fields_safe(roast_properties_dialog, marked: bool):
    """Safely mark fields in main thread"""
    try:
        if marked:
            _log.info("Fields marked as populated from inventory")
        else:
            _log.info("Fields unmarked")
    except Exception as e:
        _log.error(f"Error marking inventory fields: {e}")


def debug_inventory_combo(roast_properties_dialog):
    """Debug method to check inventory combo box state with thread safety"""
    try:
        if hasattr(roast_properties_dialog, "inventory_combo"):
            combo = roast_properties_dialog.inventory_combo
            items = [combo.itemText(i) for i in range(combo.count())]
            _log.info(f"Inventory combo items: {items}")
            _log.info(f"Current index: {combo.currentIndex()}")
            _log.info(f"Current text: {combo.currentText()}")
            return items
        else:
            _log.info("No inventory_combo found")
            return []
    except Exception as e:
        _log.error(f"Error debugging inventory combo: {e}")
        return []
