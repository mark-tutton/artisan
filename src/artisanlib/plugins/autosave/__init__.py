"""Autosave addons plugin for Artisan"""

try:
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
        cleanup
    )
    from .autosave_plugin import AutosavePlugin
except (ImportError, SystemError, OSError) as e:
    import sys
    if 'PyInstaller' in sys.modules or not hasattr(sys, 'frozen'):
        AutosaveAddonConfig = None
        get_config = None
        save_config = None
        get_health_checker = None
        create_server_upload_widgets = None
        create_additional_format_widgets = None
        save_widget_values_to_config = None
        load_config_to_qmc = None
        integrate_with_automaticsave = None
        should_upload_to_server = None
        cleanup = None
        AutosavePlugin = None
    else:
        # Real import error, re-raise
        raise

__all__ = [
    'AutosaveAddonConfig',
    'AutosavePlugin',
    'get_config',
    'save_config',
    'get_health_checker',
    'create_server_upload_widgets',
    'create_additional_format_widgets',
    'save_widget_values_to_config',
    'load_config_to_qmc',
    'integrate_with_automaticsave',
    'should_upload_to_server',
    'cleanup'
]