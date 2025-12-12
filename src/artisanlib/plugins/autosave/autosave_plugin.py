"""Autosave plugin that extends PluginBase """

from typing import Optional
from ..base import PluginBase
from .config import AutosaveAddonConfig
from .autosave_addons import (
    get_config,
    save_config,
    get_health_checker,
    create_server_upload_widgets,
    create_additional_format_widgets,
    save_widget_values_to_config,
    load_config_to_qmc,
    integrate_with_automaticsave,
    should_upload_to_server,
    cleanup as cleanup_addons
)

class AutosavePlugin(PluginBase):
    """Autosave plugin with proper PluginBase integration"""
    
    @property
    def name(self) -> str:
        return "Autosave"
    
    @property
    def version(self) -> str:
        return "2.0.0"
    
        def _initialize_plugin(self) -> None:
        """Initialize the autosave plugin"""
        # Load config and setup health checker
        config = get_config()
        health_checker = get_health_checker()
        
        health_checker.start()
        
        # Trigger initial health check after a short delay
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1000, health_checker._check_server_health)

        # Set qmc.autosave_upload_to_server, qmc.autosave_server_url
        if self.main_window:
            try:
                load_config_to_qmc(self.main_window)
                self.logger.info("Autosave config loaded into qmc")
            except Exception as e:
                self.logger.error(f"Failed to load config to qmc: {e}")
        
        # Integrate with automaticsave method
        if self.main_window:
            try:
                integrate_with_automaticsave(self.main_window)
                self.logger.info("Autosave integration with automaticsave() completed")
            except Exception as e:
                self.logger.error(f"Failed to integrate with automaticsave: {e}")
        else:
            self.logger.warning("Main window not available for autosave integration")
        
        self.logger.info("Autosave plugin initialized")
        
    def _cleanup_plugin(self) -> None:
        """Cleanup the autosave plugin"""
        cleanup_addons()
        self.logger.info("Autosave plugin cleaned up")
    
    def _on_auth_success_impl(self, access_token: str, refresh_token: str):
        """Handle successful authentication"""
        self.logger.info("Authentication successful - autosave can now upload")
    
    def _on_auth_failed_impl(self, error: str):
        """Handle authentication failure"""
        self.logger.warning(f"Authentication failed: {error}")
    
    def _on_token_refreshed_impl(self, access_token: str, refresh_token: str):
        """Handle token refresh"""
        self.logger.info("Token refreshed - autosave uploads will continue")
    
    def _on_token_expired_impl(self):
        """Handle token expiration"""
        self.logger.warning("Token expired - autosave uploads may fail")