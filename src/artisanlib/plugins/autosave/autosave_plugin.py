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
        
        # DO NOT start health checker immediately - delay until QApplication is fully ready
        # The timer will try to access auth_manager which requires QApplication to be ready
        
        # Trigger delayed initialization after QApplication event loop is running
        from PyQt6.QtCore import QTimer

        def delayed_start():
            """Start health checker after QApplication is ready"""
            self.logger.info("DEBUG: delayed_start() called")
            try:
                # Check if QApplication is ready
                from PyQt6.QtWidgets import QApplication
                self.logger.info("DEBUG: Checking QApplication.instance()")
                app = QApplication.instance()
                if app is None:
                    self.logger.warning("QApplication not ready, deferring health checker start")
                    # Retry after another second
                    QTimer.singleShot(1000, delayed_start)
                    return
                
                self.logger.info("DEBUG: QApplication is ready, starting health checker")
                health_checker.start()
                self.logger.info("DEBUG: Health checker started")
                
                # Also trigger initial health check (but it will be safe now)
                self.logger.info("DEBUG: About to call _check_server_health")
                health_checker._check_server_health()
                self.logger.info("DEBUG: _check_server_health completed")
            except Exception as e:
                self.logger.error(f"DEBUG: CRASH in delayed_start: {e}")
                import traceback
                self.logger.error(traceback.format_exc())

        # Use a longer delay (3 seconds) to ensure QApplication event loop is fully running
        QTimer.singleShot(3000, delayed_start)

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

    def _on_roast_end_impl(self):
        """Handle roast end - auto save statistics summary if enabled"""
        self.logger.info("DEBUG: _on_roast_end_impl called")
        try:
            config = get_config()
            self.logger.info(f"DEBUG: config.auto_save_statistics_on_roast_end = {config.auto_save_statistics_on_roast_end}")
            # Check if auto-save statistics is enabled
            if not config.auto_save_statistics_on_roast_end:
                self.logger.info("DEBUG: Auto-save statistics disabled, returning early")
                return
            
            if not self.main_window:
                self.logger.warning("Main window not available for auto-save statistics")
                return
            
            self.logger.info("DEBUG: Starting statistics save process")
            # Generate filename based on roast title/batch
            prefix = ''
            if self.main_window.qmc.batchcounter > -1 and self.main_window.qmc.roastbatchnr > 0:
                prefix = self.main_window.qmc.batchprefix + str(self.main_window.qmc.roastbatchnr)
            elif self.main_window.qmc.batchprefix:
                prefix = self.main_window.qmc.batchprefix
            
            filename_base = self.main_window.generateFilename(prefix=prefix)
            # Remove .alog extension
            if filename_base.endswith('.alog'):
                filename_base = filename_base[:-5]  # Remove .alog
            
            # Add operator to filename if available
            if self.main_window.qmc.operator and self.main_window.qmc.operator.strip():
                operator_clean = self.main_window.removeDisallowedFilenameChars(self.main_window.qmc.operator.strip())
                filename_base = f"{filename_base}_{operator_clean}"
            
            # Add roast UUID to filename if available
            if self.main_window.qmc.roastUUID:
                filename_base = f"{filename_base}_{self.main_window.qmc.roastUUID}"
            
            save_path = config.auto_save_statistics_path or self.main_window.qmc.autosavepath
            
            self.logger.info(f"DEBUG: filename_base={filename_base}, save_path={save_path}, format={config.auto_save_statistics_format}")
            
            if not save_path:
                self.logger.warning("No save path configured for auto-save statistics")
                return
            
            import os
            from PyQt6.QtCore import QDir
            from PyQt6.QtWidgets import QApplication
            
            # Ensure directory exists
            os.makedirs(save_path, exist_ok=True)
            
            # Save statistics based on format preference
            if config.auto_save_statistics_format == 'pdf':
                self.logger.info("DEBUG: Attempting PDF save")
                # Save as PDF (image from graph)
                try:
                    # Check if statistics summary is enabled and create the rectangle if needed
                    if not self.main_window.qmc.statssummary:
                        self.logger.warning("Statistics summary is disabled, cannot save PDF. Falling back to text format.")
                        # Fall back to text
                        statstr = self.main_window.qmc.statsSummary(txt=True)
                        if statstr:
                            txt_path = os.path.join(save_path, filename_base + '_stats.txt')
                            with open(txt_path, 'w', encoding='utf8') as file:
                                file.write(statstr)
                            self.logger.info(f"Auto-saved statistics text to {txt_path}")
                        return
                    
                    # Redraw to ensure stats summary rectangle is created
                    self.main_window.qmc.redraw()
                    QApplication.processEvents()
                    
                    # Call statsSummary() to create the rectangle if it doesn't exist
                    if self.main_window.qmc.stats_summary_rect is None:
                        self.main_window.qmc.statsSummary()
                        QApplication.processEvents()
                    
                    if self.main_window.qmc.stats_summary_rect is not None:
                        from matplotlib.transforms import Bbox
                        rect_extents = self.main_window.qmc.stats_summary_rect.get_bbox()
                        rect_extents_display = self.main_window.qmc.ax.transData.transform(rect_extents)
                        rect_extents_bbox_inches = self.main_window.qmc.fig.dpi_scale_trans.inverted().transform(rect_extents_display)
                        rect_bbox_inches = Bbox.from_extents(*list(rect_extents_bbox_inches))
                        
                        pdf_path = os.path.join(save_path, filename_base + '_stats.pdf')
                        self.main_window.qmc.fig.set_layout_engine('none')
                        self.main_window.qmc.fig.savefig(pdf_path, bbox_inches=rect_bbox_inches, pad_inches=0)
                        self.main_window.qmc.fig.set_layout_engine('tight', **self.main_window.qmc.tight_layout_params)
                        self.logger.info(f"Auto-saved statistics PDF to {pdf_path}")

                        self.logger.info(f"DEBUG: auto_print_statistics_pdf = {config.auto_print_statistics_pdf}")
                        if config.auto_print_statistics_pdf:
                            self.logger.info("DEBUG: Attempting to print PDF")
                            success = self._print_pdf(pdf_path)
                            if success:
                                self.logger.info("DEBUG: Print command executed successfully")
                            else:
                                self.logger.warning("DEBUG: Print command failed")
                        else:
                            self.logger.info("DEBUG: Auto-print is disabled in config")

                    else:
                        self.logger.warning("stats_summary_rect is still None after redraw and statsSummary(). Falling back to text format.")
                        # Fall back to text
                        statstr = self.main_window.qmc.statsSummary(txt=True)
                        if statstr:
                            txt_path = os.path.join(save_path, filename_base + '_stats.txt')
                            with open(txt_path, 'w', encoding='utf8') as file:
                                file.write(statstr)
                            self.logger.info(f"Auto-saved statistics text to {txt_path}")
                except Exception as e:
                    self.logger.error(f"Failed to auto-save statistics PDF: {e}", exc_info=True)
            
            elif config.auto_save_statistics_format == 'text':
                self.logger.info("DEBUG: Attempting text save")
                # Save as text
                try:
                    statstr = self.main_window.qmc.statsSummary(txt=True)
                    self.logger.info(f"DEBUG: statsSummary returned: {statstr[:100] if statstr else 'None/Empty'}")
                    if statstr:
                        txt_path = os.path.join(save_path, filename_base + '_stats.txt')
                        with open(txt_path, 'w', encoding='utf8') as file:
                            file.write(statstr)
                        self.logger.info(f"Auto-saved statistics text to {txt_path}")
                    else:
                        self.logger.warning("DEBUG: statsSummary returned empty/None, cannot save text")
                except Exception as e:
                    self.logger.error(f"Failed to auto-save statistics text: {e}", exc_info=True)
            
            elif config.auto_save_statistics_format == 'both':
                self.logger.info("DEBUG: Attempting both PDF and text save")
                # Save both PDF and text
                try:
                    # Save text first (always works)
                    statstr = self.main_window.qmc.statsSummary(txt=True)
                    self.logger.info(f"DEBUG: statsSummary returned: {statstr[:100] if statstr else 'None/Empty'}")
                    if statstr:
                        txt_path = os.path.join(save_path, filename_base + '_stats.txt')
                        with open(txt_path, 'w', encoding='utf8') as file:
                            file.write(statstr)
                        self.logger.info(f"Auto-saved statistics text to {txt_path}")
                    
                    # Save PDF if stats summary is enabled
                    if self.main_window.qmc.statssummary:
                        self.main_window.qmc.redraw()
                        QApplication.processEvents()
                        
                        if self.main_window.qmc.stats_summary_rect is None:
                            self.main_window.qmc.statsSummary()
                            QApplication.processEvents()
                        
                        if self.main_window.qmc.stats_summary_rect is not None:
                            from matplotlib.transforms import Bbox
                            rect_extents = self.main_window.qmc.stats_summary_rect.get_bbox()
                            rect_extents_display = self.main_window.qmc.ax.transData.transform(rect_extents)
                            rect_extents_bbox_inches = self.main_window.qmc.fig.dpi_scale_trans.inverted().transform(rect_extents_display)
                            rect_bbox_inches = Bbox.from_extents(*list(rect_extents_bbox_inches))
                            
                            pdf_path = os.path.join(save_path, filename_base + '_stats.pdf')
                            self.main_window.qmc.fig.set_layout_engine('none')
                            self.main_window.qmc.fig.savefig(pdf_path, bbox_inches=rect_bbox_inches, pad_inches=0)
                            self.main_window.qmc.fig.set_layout_engine('tight', **self.main_window.qmc.tight_layout_params)
                            self.logger.info(f"Auto-saved statistics PDF to {pdf_path}")
                        else:
                            self.logger.warning("stats_summary_rect is still None, skipping PDF save")
                    else:
                        self.logger.warning("Statistics summary is disabled, skipping PDF save")
                except Exception as e:
                    self.logger.error(f"Failed to auto-save statistics: {e}", exc_info=True)
            else:
                self.logger.warning(f"DEBUG: Unknown format '{config.auto_save_statistics_format}', expected 'pdf', 'text', or 'both'")
        except Exception as e:
            self.logger.error(f"DEBUG: Error in roast end statistics handler: {e}", exc_info=True)

    def _print_pdf(self, pdf_path: str) -> bool:
        """Print a PDF file using cross-platform commands"""
        import subprocess
        import platform
        import shutil
        
        try:
            system = platform.system()
            
            if system == 'Darwin':  # macOS
                # Use lp (CUPS) command
                result = subprocess.run(
                    ['lp', pdf_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    self.logger.info(f"PDF sent to printer: {pdf_path}")
                    return True
                else:
                    self.logger.warning(f"Failed to print PDF: {result.stderr}")
                    return False
                    
            elif system == 'Linux':
                # Use lp (CUPS) command
                result = subprocess.run(
                    ['lp', pdf_path],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    self.logger.info(f"PDF sent to printer: {pdf_path}")
                    return True
                else:
                    self.logger.warning(f"Failed to print PDF: {result.stderr}")
                    return False
                    
            elif system == 'Windows':
                # Try using the default print command
                try:
                    import win32print
                    import win32api
                    
                    # Get default printer
                    printer_name = win32print.GetDefaultPrinter()
                    if printer_name:
                        win32api.ShellExecute(
                            0,
                            "print",
                            pdf_path,
                            f'/d:"{printer_name}"',
                            ".",
                            0
                        )
                        self.logger.info(f"PDF sent to printer '{printer_name}': {pdf_path}")
                        return True
                except ImportError:
                    # Fall back to using the print command
                    pass
                
                # Fallback: use the print command
                result = subprocess.run(
                    ['print', '/D:', pdf_path],
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    self.logger.info(f"PDF sent to printer: {pdf_path}")
                    return True
                else:
                    self.logger.warning(f"Failed to print PDF: {result.stderr}")
                    return False
            else:
                self.logger.warning(f"Unsupported platform for printing: {system}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"Print command timed out for: {pdf_path}")
            return False
        except Exception as e:
            self.logger.error(f"Error printing PDF {pdf_path}: {e}", exc_info=True)
            return False