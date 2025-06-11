import asyncio
import json
import logging
import time
from typing import Dict, Any, Optional, List
from threading import Thread

try:
    from PyQt6.QtWidgets import QMenu, QMainWindow, QMessageBox
    from PyQt6.QtGui import QAction
    from PyQt6.QtCore import QTimer, pyqtSignal, QObject
except ImportError:
    from PyQt5.QtWidgets import QMenu, QMainWindow, QMessageBox
    from PyQt5.QtGui import QAction
    from PyQt5.QtCore import QTimer, pyqtSignal, QObject

from ..base import ArtisanPlugin
from .config import LiveBroadcastConfig

# Try to import WebSocketBroadcaster, but handle missing dependency gracefully
try:
    from .websocket_client import WebSocketBroadcaster, WEBSOCKETS_AVAILABLE
except ImportError:
    WebSocketBroadcaster = None
    WEBSOCKETS_AVAILABLE = False

_log = logging.getLogger(__name__)

class LiveBroadcastPlugin(ArtisanPlugin):
    """Plugin for broadcasting live roast data to external servers"""
    
    @property
    def name(self) -> str:
        return "Live Broadcast"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def __init__(self):
        super().__init__()
        self.config = LiveBroadcastConfig()
        self.broadcaster: Optional[WebSocketBroadcaster] = None
        self.update_timer: Optional[QTimer] = None
        self.last_broadcast_time = 0
        self.broadcast_interval = 1.0  # seconds
        
    def initialize(self, main_window: QMainWindow) -> None:
        super().initialize(main_window)
        
        # Check if websockets is available
        if not WEBSOCKETS_AVAILABLE:
            self.logger.warning(
                "websockets library not available. Live broadcasting functionality will be disabled. "
                "Install with: pip install websockets"
            )
            return
        
        # Connect to roast data signals
        if hasattr(main_window, 'qmc'):
            # Connect to temperature update signals
            if hasattr(main_window.qmc, 'updategraphicsSignal'):
                main_window.qmc.updategraphicsSignal.connect(self._on_data_update)
            
            # Connect to roast start/end signals
            if hasattr(main_window.qmc, 'flagstart'):
                # Monitor roast state changes
                self.update_timer = QTimer()
                self.update_timer.timeout.connect(self._check_roast_state)
                self.update_timer.start(1000)  # Check every second
        
        # Start broadcaster if auto-start is enabled
        if self.config.auto_start:
            self._start_broadcaster()
    
    def create_menu(self, parent_menu: QMenu) -> QMenu:
        menu = QMenu(self.name, parent_menu)
        
        if not WEBSOCKETS_AVAILABLE:
            # Show warning if websockets is not available
            warning_action = QAction("⚠️ websockets library required", menu)
            warning_action.setEnabled(False)
            menu.addAction(warning_action)
            
            install_action = QAction("Install: pip install websockets", menu)
            install_action.setEnabled(False)
            menu.addAction(install_action)
            
            return menu
        
        # Server controls
        self.start_action = QAction("Start Broadcasting", menu)
        self.start_action.triggered.connect(self._start_broadcaster)
        menu.addAction(self.start_action)
        
        self.stop_action = QAction("Stop Broadcasting", menu)
        self.stop_action.triggered.connect(self._stop_broadcaster)
        menu.addAction(self.stop_action)
        
        menu.addSeparator()
        
        # Configuration
        config_action = QAction("Configure", menu)
        config_action.triggered.connect(self._configure)
        menu.addAction(config_action)
        
        # Status
        self.status_action = QAction("Status: Disconnected", menu)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        
        return menu
    
    def on_roast_start(self) -> None:
        """Called when a roast starts"""
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_roast_event("roast_started")
    
    def on_roast_end(self) -> None:
        """Called when a roast ends"""
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_roast_event("roast_ended")
    
    def on_data_update(self, data: Dict[str, Any]) -> None:
        """Called when new roast data is available"""
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_roast_data(data)
    
    def _check_roast_state(self) -> None:
        """Monitor roast state changes"""
        if not self.main_window or not hasattr(self.main_window, 'qmc'):
            return
            
        qmc = self.main_window.qmc
        
        # Check if roast just started
        if qmc.flagstart and not hasattr(self, '_roast_started'):
            self._roast_started = True
            self.on_roast_start()
        
        # Check if roast just ended
        elif not qmc.flagstart and hasattr(self, '_roast_started'):
            self._roast_started = False
            self.on_roast_end()
    
    def _on_data_update(self) -> None:
        """Handle temperature data updates"""
        if not WEBSOCKETS_AVAILABLE:
            return
            
        current_time = time.time()
        
        # Throttle broadcasts to avoid overwhelming the server
        if current_time - self.last_broadcast_time < self.broadcast_interval:
            return
            
        self.last_broadcast_time = current_time
        
        # Get current roast data
        roast_data = self._get_current_roast_data()
        if roast_data:
            self.on_data_update(roast_data)
    
    def _safe_get_timeindex(self, qmc, index: int) -> Optional[float]:
        """Safely get time value from timeindex"""
        try:
            if (hasattr(qmc, 'timeindex') and 
                hasattr(qmc, 'timex') and 
                len(qmc.timeindex) > index and 
                qmc.timeindex[index] > -1 and 
                len(qmc.timex) > qmc.timeindex[index]):
                return qmc.timex[qmc.timeindex[index]]
        except (IndexError, AttributeError):
            pass
        return None
    
    def _safe_get_weight(self, qmc, index: int) -> float:
        """Safely get weight value"""
        try:
            if hasattr(qmc, 'weight') and len(qmc.weight) > index:
                return qmc.weight[index]
        except (IndexError, AttributeError):
            pass
        return 0.0
    
    def _safe_get_temp(self, temp_list, index: int = -1) -> Optional[float]:
        """Safely get temperature value"""
        try:
            if temp_list and len(temp_list) > 0:
                if index == -1:
                    return temp_list[-1]
                elif 0 <= index < len(temp_list):
                    return temp_list[index]
        except (IndexError, AttributeError):
            pass
        return None
    
    def _get_current_roast_data(self) -> Optional[Dict[str, Any]]:
        """Extract current roast data from the application"""
        if not self.main_window or not hasattr(self.main_window, 'qmc'):
            return None
            
        qmc = self.main_window.qmc
        
        # Basic roast info
        # TOOD: add more info like roaster, operator, batch, inventory, etc
        data = {
            "timestamp": time.time(),
            "roast_uuid": getattr(qmc, 'roastUUID', None),
            "title": getattr(qmc, 'title', ''),
            "beans": getattr(qmc, 'beans', ''),
            "weight": {
                "in": self._safe_get_weight(qmc, 0),
                "out": self._safe_get_weight(qmc, 1),
                "unit": self._safe_get_weight(qmc, 2) if self._safe_get_weight(qmc, 2) else "kg"
            },
            "roast_state": {
                "is_recording": getattr(qmc, 'flagstart', False),
                "charge_time": self._safe_get_timeindex(qmc, 0),
                "drop_time": self._safe_get_timeindex(qmc, 6),
                "current_time": self._safe_get_temp(getattr(qmc, 'timex', []), -1) or 0
            }
        }

        #TODO: get roast events like gas, air changes, slider changes, button presses
        
        # Temperature data
        temp1 = getattr(qmc, 'temp1', [])
        temp2 = getattr(qmc, 'temp2', [])
        timex = getattr(qmc, 'timex', [])
        
        if temp1 and temp2 and timex:
            # Get last 100 points safely
            max_points = min(100, len(timex))
            start_idx = max(0, len(timex) - max_points)
            
            data["temperatures"] = {
                "environmental_temp": self._safe_get_temp(temp1),
                "bean_temp": self._safe_get_temp(temp2),
                "time_series": {
                    "time": timex[start_idx:] if timex else [],
                    "environmental_temp": temp1[start_idx:] if temp1 else [],
                    "bean_temp": temp2[start_idx:] if temp2 else []
                }
            }
        
        # Rate of rise
        delta1 = getattr(qmc, 'delta1', [])
        delta2 = getattr(qmc, 'delta2', [])
        
        if delta1 or delta2:
            data["rate_of_rise"] = {
                "environmental_ror": self._safe_get_temp(delta1),
                "bean_ror": self._safe_get_temp(delta2)
            }
        
        # Events
        specialevents = getattr(qmc, 'specialevents', [])
        specialeventstype = getattr(qmc, 'specialeventstype', [])
        specialeventsStrings = getattr(qmc, 'specialeventsStrings', [])
        
        if specialevents:
            data["events"] = []
            for i, event_time in enumerate(specialevents):
                if (i < len(specialeventstype) and 
                    i < len(specialeventsStrings)):
                    data["events"].append({
                        "time": event_time,
                        "type": specialeventstype[i],
                        "description": specialeventsStrings[i]
                    })
        
        # Ambient conditions
        data["ambient"] = {
            "temperature": getattr(qmc, 'ambientTemp', 0),
            "humidity": getattr(qmc, 'ambient_humidity', 0),
            "pressure": getattr(qmc, 'ambient_pressure', 0)
        }
        
        return data
    
    def _broadcast_roast_data(self, data: Dict[str, Any]) -> None:
        """Broadcast roast data to connected clients"""
        if not WEBSOCKETS_AVAILABLE or not self.broadcaster or not self.broadcaster.is_connected:
            return
            
        try:
            message = {
                "type": "roast_data",
                "data": data
            }
            self.broadcaster.broadcast(json.dumps(message))
            self._update_status("Connected")
        except Exception as e:
            self.logger.error(f"Failed to broadcast roast data: {e}")
            self._update_status("Error")
    
    def _broadcast_roast_event(self, event_type: str) -> None:
        """Broadcast roast events"""
        if not WEBSOCKETS_AVAILABLE or not self.broadcaster or not self.broadcaster.is_connected:
            return
            
        try:
            message = {
                "type": "roast_event",
                "event": event_type,
                "timestamp": time.time(),
                "roast_uuid": getattr(self.main_window.qmc, 'roastUUID', None) if self.main_window else None
            }
            self.broadcaster.broadcast(json.dumps(message))
        except Exception as e:
            self.logger.error(f"Failed to broadcast roast event: {e}")
    
    def _start_broadcaster(self) -> None:
        """Start the WebSocket broadcaster"""
        if not WEBSOCKETS_AVAILABLE:
            QMessageBox.warning(
                self.main_window,
                "WebSocket Library Missing",
                "The websockets library is required for live broadcasting.\n\n"
                "Please install it with:\n"
                "pip install websockets"
            )
            return
            
        try:
            if not self.broadcaster:
                self.broadcaster = WebSocketBroadcaster(
                    host=self.config.server_host,
                    port=self.config.server_port,
                    path=self.config.server_path
                )
            
            self.broadcaster.start()
            self._update_status("Connecting...")
            
            # Update menu actions
            if hasattr(self, 'start_action'):
                self.start_action.setEnabled(False)
            if hasattr(self, 'stop_action'):
                self.stop_action.setEnabled(True)
                
        except Exception as e:
            self.logger.error(f"Failed to start broadcaster: {e}")
            self._update_status("Failed to start")
    
    def _stop_broadcaster(self) -> None:
        """Stop the WebSocket broadcaster"""
        if not WEBSOCKETS_AVAILABLE:
            return
            
        try:
            if self.broadcaster:
                self.broadcaster.stop()
                self.broadcaster = None
            
            self._update_status("Disconnected")
            
            # Update menu actions
            if hasattr(self, 'start_action'):
                self.start_action.setEnabled(True)
            if hasattr(self, 'stop_action'):
                self.stop_action.setEnabled(False)
                
        except Exception as e:
            self.logger.error(f"Failed to stop broadcaster: {e}")
    
    def _configure(self) -> None:
        """Open configuration dialog"""
        if not WEBSOCKETS_AVAILABLE:
            QMessageBox.warning(
                self.main_window,
                "WebSocket Library Missing",
                "The websockets library is required for live broadcasting.\n\n"
                "Please install it with:\n"
                "pip install websockets"
            )
            return
            
        from .config_dialog import ConfigDialog
        dialog = ConfigDialog(self.config, self.main_window)
        if dialog.exec():
            # Restart broadcaster if running
            if self.broadcaster and self.broadcaster.is_connected:
                self._stop_broadcaster()
                self._start_broadcaster()
    
    def _update_status(self, status: str) -> None:
        """Update status in menu"""
        if hasattr(self, 'status_action'):
            self.status_action.setText(f"Status: {status}")
    
    def cleanup(self) -> None:
        """Cleanup plugin resources"""
        if self.update_timer:
            self.update_timer.stop()
        
        if self.broadcaster:
            self.broadcaster.stop()
        
        super().cleanup()