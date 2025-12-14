import logging
import time
import requests
from typing import Dict, List, Any, Optional

try:
    from PyQt6.QtWidgets import QMenu, QComboBox, QPushButton, QMessageBox, QDialog
    from PyQt6.QtGui import QAction
    from PyQt6.QtCore import QTimer, pyqtSignal, QObject
except ImportError:
    from PyQt5.QtWidgets import QMenu, QComboBox, QPushButton, QMessageBox, QDialog
    from PyQt5.QtGui import QAction
    from PyQt5.QtCore import QTimer, pyqtSignal, QObject

from ..base import ArtisanPlugin
from ..auth_manager import GlobalAuthManager
from .config import InventoryFetcherConfig
from .inventory_fetcher import InventoryFetcher
from .config_dialog import InventoryFetcherConfigDialog

class InventorySignals(QObject):
    """QObject for handling signals"""
    inventory_updated = pyqtSignal(list)
    fetch_progress = pyqtSignal(int)  # Progress percentage
    fetch_completed = pyqtSignal(list)  # Completed beans data
    fetch_failed = pyqtSignal(str)  # Error message

class InventoryFetcherPlugin(ArtisanPlugin):
    """Plugin for fetching beans data from external server via Gateway with threading support"""
    
    @property
    def name(self) -> str:
        """Plugin name - must match what the plugin manager expects"""
        return "Inventory Fetcher"  
    
    @property
    def version(self) -> str:
        """Plugin version"""
        return "2.0.0"
    
    def __init__(self):
        super().__init__()
        
        self.signals = InventorySignals()
        
        self.config = InventoryFetcherConfig.load_config()
        self.fetcher = None
        self.beans_data = []
        self.roast_properties_dialog = None
        
        # Threading state
        self._fetch_in_progress = False
        self._last_fetch_time = 0
        self._fetch_interval = 300  # 5 minutes between fetches
        
        
    def initialize(self, main_window) -> None:
        """Initialize the plugin"""
        super().initialize(main_window)
        
        # connect auth manager signals
        try:
            self.auth_manager.login_successful.disconnect()
            self.auth_manager.login_failed.disconnect()
            self.auth_manager.token_refreshed.disconnect()
            self.auth_manager.token_expired.disconnect()
        except (TypeError, RuntimeError):
            # signals weren't connected yet, that's fine
            pass
        
        self.auth_manager.login_successful.connect(self._on_auth_success_impl)
        self.auth_manager.token_refreshed.connect(self._on_token_refreshed_impl)
        self.auth_manager.token_expired.connect(self._on_token_expired_impl)
        
        # create fetcher if server URL is configured
        if self.config.get_effective_url():
            self._create_fetcher()
            
            # auto-fetch on startup if enabled
            if self.config.auto_fetch_on_startup:
                QTimer.singleShot(1000, self.fetch_beans)

    def _create_fetcher(self):
        """Create a new fetcher instance, closing any existing one"""
        if self.fetcher:
            self.logger.info("Closing existing fetcher to prevent connection leaks")
            self.fetcher.close()
            self.fetcher = None
        
        self.logger.info(f"Auth manager exists: {self.auth_manager is not None}")
        if self.auth_manager:
            self.logger.info(f"Is authenticated: {self.auth_manager.is_authenticated()}")
            token_info = self.auth_manager.get_token_info()
            self.logger.info(f"Token info: {token_info}")
        
        # Create new fetcher
        self.fetcher = InventoryFetcher(self.config, self.auth_manager)
        self.logger.info("Created new inventory fetcher with connection pooling")

 
    def _on_auth_success_impl(self, access_token: str, refresh_token: str):
        """Handle successful authentication"""
        self.logger.info("Authentication successful - recreating fetcher")
        
        # Recreate fetcher with new tokens
        if self.config.get_effective_url():
            self._create_fetcher()



    
    def _on_token_refreshed_impl(self, access_token: str, refresh_token: str):
        """Handle token refresh"""
        self.logger.info("Token refreshed - recreating fetcher")
        
        # Recreate fetcher with new tokens
        if self.config.get_effective_url():
            self._create_fetcher()

    def _on_token_expired_impl(self):
        """Handle token expiration"""
        self.logger.warning("Token expired - clearing fetcher")
        
        # Close fetcher since no authenticate
        if self.fetcher:
            self.fetcher.close()
            self.fetcher = None

    
    def cleanup(self) -> None:
        """Cleanup the plugin"""
        try:
            # Close fetcher to prevent connection leaks
            if self.fetcher:
                self.logger.info("Cleaning up inventory fetcher")
                self.fetcher.close()
                self.fetcher = None
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
        finally:
            super().cleanup()
    
    def create_menu(self, parent_menu: QMenu) -> QMenu:
        """Create plugin menu items"""
        # Main plugin menu
        plugin_menu = QMenu("Inventory Fetcher", parent_menu)
        parent_menu.addMenu(plugin_menu)
        
        # Configure action
        configure_action = QAction("Configure", self.main_window)
        configure_action.triggered.connect(self.show_config_dialog)
        plugin_menu.addAction(configure_action)
        
        # Fetch beans action
        fetch_action = QAction("Fetch Inventory", self.main_window)
        fetch_action.triggered.connect(self.fetch_beans)
        plugin_menu.addAction(fetch_action)
        
        # Refresh action
        refresh_action = QAction("Refresh Inventory", self.main_window)
        refresh_action.triggered.connect(self.refresh_beans)
        plugin_menu.addAction(refresh_action)
        
        plugin_menu.addSeparator()
        
        # Test connection action
        test_action = QAction("Test Connection", self.main_window)
        test_action.triggered.connect(self.test_connection)
        plugin_menu.addAction(test_action)
        
        plugin_menu.addSeparator()
        
        # About action
        about_action = QAction("About", self.main_window)
        about_action.triggered.connect(self.show_about)
        plugin_menu.addAction(about_action)
        
        return plugin_menu
    
    def show_config_dialog(self):
        """Show configuration dialog"""
        try:
            dialog = InventoryFetcherConfigDialog(self.main_window, self.config)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # recreate fetcher with new config to prevent connection leaks
                if self.config.get_effective_url():
                    self._create_fetcher()
                    self.logger.info("Inventory fetcher reconfigured with new settings")
        except Exception as e:
            self._record_error("ConfigDialogError", str(e))
            self.logger.error(f"Error showing config dialog: {e}")


    def fetch_beans(self):
        """Fetch beans data from server"""
        if self._fetch_in_progress:
            self.logger.warning("Fetch already in progress, skipping")
            return

        if not self.fetcher:
            self.logger.error("No fetcher available - check server configuration")
            return

        # Check if there is authentication
        if not self.is_authenticated():
            self.logger.warning("No authentication available for inventory fetch")
            return

        self._fetch_in_progress = True
        self.logger.info("Starting beans fetch...")

        # Execute fetch in worker thread
        self.execute_in_worker("fetch_beans", self._fetch_beans_worker)


    def _fetch_beans_worker(self):
        """Worker method for fetching beans"""
        try:
            # Debug auth status
            self.logger.info(f"Auth manager exists: {self.auth_manager is not None}")
            if self.auth_manager:
                self.logger.info(f"Is authenticated: {self.auth_manager.is_authenticated()}")
                token_info = self.auth_manager.get_token_info()
                self.logger.info(f"Token info: {token_info}")
        
            headers = self.get_auth_headers()
            
            result = self.fetcher.fetch_beans()
            if result and "data" in result:
                beans_data = result["data"] 
                self.beans_data = beans_data
                self.signals.fetch_completed.emit(beans_data)
                self.logger.info(f"Successfully fetched {len(beans_data)} beans")
            else:
                self.logger.warning("No beans data received")
                self.signals.fetch_failed.emit("No beans data received")
        except Exception as e:
            self.logger.error(f"Failed to fetch beans: {e}")
            self.signals.fetch_failed.emit(str(e))
        finally:
            self._fetch_in_progress = False

    def _on_fetch_completed(self, result: List[Dict[str, Any]]) -> None:
        """Handle fetch completion in main thread"""
        try:
            self.beans_data = result
            self._fetch_in_progress = False
            self._last_fetch_time = time.time()

            if self.config.show_notifications:
                self.main_window.sendmessage(f"Fetched {len(self.beans_data)} coffees from server")

            self.logger.info(f"Fetch completed successfully: {len(self.beans_data)} coffees")
            self.signals.inventory_updated.emit(self.beans_data)
            self.signals.fetch_completed.emit(self.beans_data)
            
        except Exception as e:
            self._fetch_in_progress = False
            self._record_error("FetchCompletionError", str(e))
            self.logger.error(f"Error handling fetch completion: {e}")

    def _on_fetch_failed(self, error_message: str) -> None:
        """Handle fetch failure in main thread"""
        try:
            self._fetch_in_progress = False
            
            if self.config.show_notifications:
                QMessageBox.critical(self.main_window, "Error", f"Failed to fetch coffees: {error_message}")

            self.logger.error(f"Fetch failed: {error_message}")
            self.signals.fetch_failed.emit(error_message)
            
        except Exception as e:
            self._fetch_in_progress = False
            self._record_error("FetchFailureError", str(e))
            self.logger.error(f"Error handling fetch failure: {e}")

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API calls"""
        token = self.get_auth_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def make_authenticated_request(self, url: str, method: str = "GET", **kwargs) -> Optional[requests.Response]:
        """Make an authenticated API request"""
        headers = self.get_auth_headers()
        if 'headers' in kwargs:
            headers.update(kwargs['headers'])
        kwargs['headers'] = headers
        
        try:
            if method.upper() == "GET":
                return requests.get(url, **kwargs)
            elif method.upper() == "POST":
                return requests.post(url, **kwargs)
            elif method.upper() == "PUT":
                return requests.put(url, **kwargs)
            elif method.upper() == "DELETE":
                return requests.delete(url, **kwargs)
        except Exception as e:
            self.logger.error(f"Authenticated request failed: {e}")
            return None

    def refresh_beans(self):
        """Refresh beans data"""
        self.fetch_beans()

    def health_check(self):
        """Perform health check on server"""
        if not self.fetcher:
            self.logger.error("No fetcher available")
            return
        
        try:
            self.logger.info("Starting health check")
            result = self.fetcher.health_check()
            
            if "error" in result:
                error_msg = f"Health check failed: {result['error']}"
                self.logger.error(error_msg)
                QMessageBox.warning(self.main_window, "Health Check Failed", error_msg)
            else:
                self.logger.info("Health check successful")
                QMessageBox.information(self.main_window, "Health Check", "Server is healthy")
        
        except Exception as e:
            error_msg = f"Health check error: {e}"
            self.logger.error(error_msg)
            QMessageBox.critical(self.main_window, "Health Check Error", error_msg)
    

    
    
    def get_beans_data(self) -> List[Dict[str, Any]]:
        """Get current beans data"""
        return self.beans_data
    
    def populate_beans_combo(self, combo_box: QComboBox):
        """Populate combo box with beans data"""
        try:
            combo_box.clear()
            combo_box.setPlaceholderText("Select/Search from inventory...")
            
            if hasattr(self.main_window, "addmessage"):
                self.main_window.addmessage(f"Populating inventory_combo with beans_data of type: {type(self.beans_data)} length: {len(self.beans_data)}")
            
            for i, bean in enumerate(self.beans_data):
                if hasattr(self.main_window, "addmessage"):
                    self.main_window.addmessage(f"DEBUG: Bean {i}: {bean}")
                combo_box.addItem(bean.get('name', 'Unknown'), bean)
                
            if hasattr(self.main_window, "addmessage"):
                self.main_window.addmessage(f"DEBUG: Combo count after population: {combo_box.count()}")
                
        except Exception as e:
            self._record_error("PopulateComboError", str(e))
            self.logger.error(f"Error populating combo box: {e}")
    
    def get_selected_bean(self, combo_box: QComboBox) -> Optional[Dict[str, Any]]:
        """Get selected bean data from combo box"""
        try:
            index = combo_box.currentIndex()
            if index >= 0:  
                return combo_box.itemData(index)
            return None
        except Exception as e:
            self._record_error("GetSelectedBeanError", str(e))
            self.logger.error(f"Error getting selected bean: {e}")
            return None
    
    def register_roast_properties_dialog(self, dialog):
        """Register the roast properties dialog for integration"""
        try:
            self.roast_properties_dialog = dialog
            self.logger.info("Roast properties dialog registered for inventory integration")
        except Exception as e:
            self._record_error("RegisterDialogError", str(e))
            self.logger.error(f"Error registering roast properties dialog: {e}")
    
    def populate_roast_properties_fields(self, bean_data: Dict[str, Any]):
        """Populate roast properties fields with bean data"""
        if not self.roast_properties_dialog:
            return
        
        try:
            # populate basic bean information
            if 'name' in bean_data:
                self.roast_properties_dialog.beansedit.setPlainText(bean_data['name'])
            
            # populate density if available
            if 'density' in bean_data:
                density = bean_data['density']
                if isinstance(density, (int, float)):
                    self.roast_properties_dialog.bean_density_in_edit.setText(str(density))
            
            # Populate moisture if available
            if 'moisture' in bean_data:
                moisture = bean_data['moisture']
                if isinstance(moisture, (int, float)):
                    self.roast_properties_dialog.moisture_greens_edit.setText(str(moisture))
            
            # Populate bean size if available
            if 'bean_size_min' in bean_data:
                size_min = bean_data['bean_size_min']
                if isinstance(size_min, (int, float)):
                    self.roast_properties_dialog.bean_size_min_edit.setText(str(size_min))
            
            if 'bean_size_max' in bean_data:
                size_max = bean_data['bean_size_max']
                if isinstance(size_max, (int, float)):
                    self.roast_properties_dialog.bean_size_max_edit.setText(str(size_max))
            
            # TODO: populate title field, stock, blend, store fields
            
            self.logger.info(f"Populated roast properties with bean data: {bean_data.get('name', 'Unknown')}")
            
        except Exception as e:
            self._record_error("PopulatePropertiesError", str(e))
            self.logger.error(f"Error populating roast properties: {e}")
    
    def show_about(self):
        """Show about dialog"""
        try:
            QMessageBox.information(
                self.main_window,
                "About Inventory Fetcher",
                f"<h3>Inventory Fetcher Plugin v{self.version}</h3>"
                f"<p>Fetches beans data from external inventory server via Gateway.</p>"
                f"<p><b>Gateway Mode:</b> {self.config.use_gateway}</p>"
                f"<p><b>Gateway URL:</b> {self.config.gateway_url}</p>"
                f"<p><b>Auth Type:</b> {self.config.gateway_auth_type}</p>"
                f"<p>Configure the gateway URL and authentication in the plugin settings.</p>"
            )
        except Exception as e:
            self._record_error("AboutDialogError", str(e))
            self.logger.error(f"Error showing about dialog: {e}")

    def test_connection(self):
        """Test connection to server"""
        if not self.fetcher:
            QMessageBox.warning(self.main_window, "Warning", "Please configure server URL first!")
            return

        try:
            # Test basic connection
            if self.fetcher.test_connection():
                QMessageBox.information(self.main_window, "Success", "Connection successful!")
            else:
                QMessageBox.critical(self.main_window, "Error", "Connection failed!")
                
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Connection test failed: {e}")

    def get_plugin_status(self) -> Dict[str, Any]:
        """Get plugin status for monitoring"""
        try:
            status = {
                "name": self.name,
                "version": self.version,
                "state": self.state.value,
                "is_active": self.is_active,
                "has_errors": self.has_errors,
                "error_count": len(self.errors),
                "fetcher_configured": self.fetcher is not None,
                "fetcher_closed": self.fetcher._closed if self.fetcher else None,
                "beans_count": len(self.beans_data),
                "fetch_in_progress": self._fetch_in_progress,
                "last_fetch_time": self._last_fetch_time,
                "gateway_url": self.config.gateway_url,
                "health_check_enabled": self.config.health_check_enabled,
                "health_check_url": self.config.health_check_url,
                "auto_fetch_enabled": self.config.auto_fetch_on_startup,
                "worker_thread_running": self._worker_thread.isRunning() if self._worker_thread else False,
                "recent_errors": [
                    {
                        "timestamp": error.timestamp.isoformat(),
                        "type": error.error_type,
                        "message": error.message
                    }
                    for error in self.errors[-5:] 
                ]
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Error getting plugin status: {e}")
            return {"error": str(e)}

    def _on_worker_operation_started(self, operation_name: str) -> None:
        """Handle worker operation started"""
        if operation_name == "fetch_inventory":
            self.logger.info("Inventory fetch operation started in worker thread")
            self.signals.fetch_progress.emit(0)

    def _on_worker_operation_completed(self, operation_name: str, result: Any) -> None:
        """Handle worker operation completed"""
        if operation_name == "fetch_inventory":
            self.logger.info("Inventory fetch operation completed in worker thread")
            # Schedule the completion handler in the main thread
            QTimer.singleShot(0, lambda: self._on_fetch_completed(result))

    def _on_worker_operation_failed(self, operation_name: str, error_message: str) -> None:
        """Handle worker operation failed"""
        if operation_name == "fetch_inventory":
            self.logger.error(f"Inventory fetch operation failed in worker thread: {error_message}")
            # Schedule the failure handler in the main thread
            QTimer.singleShot(0, lambda: self._on_fetch_failed(error_message))

    def debug_auth_status(self):
        """Debug authentication status"""
        if self.auth_manager:
            self.logger.info(f"Auth manager exists: {self.auth_manager is not None}")
            self.logger.info(f"Is authenticated: {self.auth_manager.is_authenticated()}")
            self.logger.info(f"Token info: {self.auth_manager.get_token_info()}")
            self.logger.info(f"Auth base URL: {self.auth_manager.get_auth_base_url()}")
        else:
            self.logger.warning("No auth manager found")