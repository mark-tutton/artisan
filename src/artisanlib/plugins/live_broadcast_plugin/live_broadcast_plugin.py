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
    """Plugin for broadcasting live roast data and events to external servers"""
    
    @property
    def name(self) -> str:
        return "Live Broadcast"
    
    @property
    def version(self) -> str:
        return "1.1.0"
    
    def __init__(self):
        super().__init__()
        self.config = LiveBroadcastConfig()
        self.broadcaster: Optional[WebSocketBroadcaster] = None
        self.update_timer: Optional[QTimer] = None
        self.last_broadcast_time = 0
        self.broadcast_interval = 1.0  # seconds
        
        # Track event states to avoid duplicate broadcasts
        self.last_event_states = {
            'charge': False,
            'dry_end': False,
            'fc_start': False,
            'fc_end': False,
            'sc_start': False,
            'sc_end': False,
            'drop': False,
            'cool_end': False
        }
        
    def initialize(self, main_window: QMainWindow) -> None:
        super().initialize(main_window)
        
        # Check if websockets is available
        if not WEBSOCKETS_AVAILABLE:
            self.logger.warning(
                "websockets library not available. Live broadcasting functionality will be disabled. "
                "Install with: pip install websockets"
            )
            return
        
        self.logger.info("Initializing Live Broadcast Plugin...")
        
        # Connect to roast data signals
        if hasattr(main_window, 'qmc'):
            self.logger.info("Found qmc object, connecting to signals...")
            
            # Connect to temperature update signals
            if hasattr(main_window.qmc, 'updategraphicsSignal'):
                main_window.qmc.updategraphicsSignal.connect(self._on_data_update)
                self.logger.info("Connected to updategraphicsSignal")
            
            # Connect to event signals
            signal_connections = [
                ('markChargeSignal', self._on_charge_event),
                ('markDRYSignal', self._on_dry_end_event),
                ('markFCsSignal', self._on_fc_start_event),
                ('markFCeSignal', self._on_fc_end_event),
                ('markSCsSignal', self._on_sc_start_event),
                ('markSCeSignal', self._on_sc_end_event),
                ('markDropSignal', self._on_drop_event),
                ('markCoolSignal', self._on_cool_end_event),
            ]
            
            for signal_name, handler in signal_connections:
                if hasattr(main_window.qmc, signal_name):
                    signal = getattr(main_window.qmc, signal_name)
                    signal.connect(handler)
                    self.logger.info(f"Connected to {signal_name}")
                else:
                    self.logger.warning(f"Signal {signal_name} not found on qmc")
            
            # Connect to custom event signals
            if hasattr(main_window.qmc, 'eventRecordSignal'):
                main_window.qmc.eventRecordSignal.connect(self._on_custom_event)
                self.logger.info("Connected to eventRecordSignal")
            
            # Connect to roast start/end signals
            if hasattr(main_window.qmc, 'flagstart'):
                # Monitor roast state changes
                self.update_timer = QTimer()
                self.update_timer.timeout.connect(self._check_roast_state)
                self.update_timer.start(1000)  # Check every second
                self.logger.info("Started roast state monitoring timer")
        else:
            self.logger.error("qmc object not found on main_window")
        
        # Start broadcaster if auto-start is enabled
        if self.config.auto_start:
            self.logger.info("Auto-start enabled, starting broadcaster...")
            self._start_broadcaster()
        else:
            self.logger.info("Auto-start disabled, broadcaster not started")

        if self.broadcaster:
            self.broadcaster.add_message_callback(self._on_ws_message)
    
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
        
        # Debug actions
        debug_menu = QMenu("Debug", menu)
        
        test_event_action = QAction("Test Event Broadcast", debug_menu)
        test_event_action.triggered.connect(self._test_event_broadcast)
        debug_menu.addAction(test_event_action)
        
        test_data_action = QAction("Test Data Broadcast", debug_menu)
        test_data_action.triggered.connect(self._test_data_broadcast)
        debug_menu.addAction(test_data_action)
        
        status_action = QAction("Show Status", debug_menu)
        status_action.triggered.connect(self._show_status)
        debug_menu.addAction(status_action)
        
        menu.addMenu(debug_menu)
        
        # Status
        self.status_action = QAction("Status: Disconnected", menu)
        self.status_action.setEnabled(False)
        menu.addAction(self.status_action)
        
        return menu
    
    def on_roast_start(self) -> None:
        """Called when a roast starts"""
        self.logger.info("Roast started")
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_roast_event("roast_started")
    
    def on_roast_end(self) -> None:
        """Called when a roast ends"""
        self.logger.info("Roast ended")
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
        
        # Check for event state changes
        self._check_event_states()
    
    def _check_event_states(self) -> None:
        """Check for changes in event states and broadcast them"""
        if not self.main_window or not hasattr(self.main_window, 'qmc'):
            return
            
        qmc = self.main_window.qmc
        
        # Check standard events
        events_to_check = [
            ('charge', 0),
            ('dry_end', 1),
            ('fc_start', 2),
            ('fc_end', 3),
            ('sc_start', 4),
            ('sc_end', 5),
            ('drop', 6),
            ('cool_end', 7)
        ]
        
        for event_name, timeindex_idx in events_to_check:
            current_state = qmc.timeindex[timeindex_idx] > 0
            if current_state != self.last_event_states[event_name]:
                self.last_event_states[event_name] = current_state
                if current_state:
                    self.logger.info(f"Event state changed: {event_name} is now active")
                    self._broadcast_event(event_name)
    
    def _on_charge_event(self, noaction: bool = False) -> None:
        """Handle CHARGE event"""
        self.logger.info(f"CHARGE event triggered (noaction={noaction})")
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_event("charge")
    
    def _on_dry_end_event(self, noaction: bool = False) -> None:
        """Handle DRY END event"""
        self.logger.info(f"DRY END event triggered (noaction={noaction})")
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_event("dry_end")
    
    def _on_fc_start_event(self, noaction: bool = False) -> None:
        """Handle FC START event"""
        self.logger.info(f"FC START event triggered (noaction={noaction})")
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_event("fc_start")
    
    def _on_fc_end_event(self, noaction: bool = False) -> None:
        """Handle FC END event"""
        self.logger.info(f"FC END event triggered (noaction={noaction})")
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_event("fc_end")
    
    def _on_sc_start_event(self, noaction: bool = False) -> None:
        """Handle SC START event"""
        self.logger.info(f"SC START event triggered (noaction={noaction})")
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_event("sc_start")
    
    def _on_sc_end_event(self, noaction: bool = False) -> None:
        """Handle SC END event"""
        self.logger.info(f"SC END event triggered (noaction={noaction})")
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_event("sc_end")
    
    def _on_drop_event(self, noaction: bool = False) -> None:
        """Handle DROP event"""
        self.logger.info(f"DROP event triggered (noaction={noaction})")
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_event("drop")
    
    def _on_cool_end_event(self, noaction: bool = False) -> None:
        """Handle COOL END event"""
        self.logger.info(f"COOL END event triggered (noaction={noaction})")
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_event("cool_end")
    
    def _on_custom_event(self, event_index: int) -> None:
        """Handle custom events"""
        self.logger.info(f"Custom event triggered: index={event_index}")
        if not WEBSOCKETS_AVAILABLE or not self.main_window:
            return
            
        qmc = self.main_window.qmc
        
        # Get custom event data
        if (hasattr(qmc, 'specialevents') and 
            hasattr(qmc, 'specialeventstype') and 
            hasattr(qmc, 'specialeventsvalue') and 
            hasattr(qmc, 'specialeventsStrings') and
            len(qmc.specialevents) > event_index):
            
            event_data = {
                'type': 'custom_event',
                'event_index': event_index,
                'time': qmc.specialevents[event_index] if event_index < len(qmc.specialevents) else 0,
                'event_type': qmc.specialeventstype[event_index] if event_index < len(qmc.specialeventstype) else 4,
                'value': qmc.specialeventsvalue[event_index] if event_index < len(qmc.specialeventsvalue) else 0,
                'description': qmc.specialeventsStrings[event_index] if event_index < len(qmc.specialeventsStrings) else '',
                'timestamp': time.time()
            }
            
            self._broadcast_custom_event(event_data)
    
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
        
        # Get current temperatures
        current_et = self._safe_get_temp(qmc.temp1)
        current_bt = self._safe_get_temp(qmc.temp2)
        
        # Get event times
        charge_time = self._safe_get_timeindex(qmc, 0)
        dry_end_time = self._safe_get_timeindex(qmc, 1)
        fc_start_time = self._safe_get_timeindex(qmc, 2)
        fc_end_time = self._safe_get_timeindex(qmc, 3)
        sc_start_time = self._safe_get_timeindex(qmc, 4)
        sc_end_time = self._safe_get_timeindex(qmc, 5)
        drop_time = self._safe_get_timeindex(qmc, 6)
        cool_end_time = self._safe_get_timeindex(qmc, 7)
        
        # Get event temperatures
        charge_temp = self._safe_get_temp(qmc.temp2, qmc.timeindex[0]) if qmc.timeindex[0] > -1 else None
        dry_end_temp = self._safe_get_temp(qmc.temp2, qmc.timeindex[1]) if qmc.timeindex[1] > -1 else None
        fc_start_temp = self._safe_get_temp(qmc.temp2, qmc.timeindex[2]) if qmc.timeindex[2] > -1 else None
        fc_end_temp = self._safe_get_temp(qmc.temp2, qmc.timeindex[3]) if qmc.timeindex[3] > -1 else None
        sc_start_temp = self._safe_get_temp(qmc.temp2, qmc.timeindex[4]) if qmc.timeindex[4] > -1 else None
        sc_end_temp = self._safe_get_temp(qmc.temp2, qmc.timeindex[5]) if qmc.timeindex[5] > -1 else None
        drop_temp = self._safe_get_temp(qmc.temp2, qmc.timeindex[6]) if qmc.timeindex[6] > -1 else None
        cool_end_temp = self._safe_get_temp(qmc.temp2, qmc.timeindex[7]) if qmc.timeindex[7] > -1 else None
        
        # Get custom events
        custom_events = []
        if hasattr(qmc, 'specialevents') and hasattr(qmc, 'specialeventstype'):
            for i, event_time in enumerate(qmc.specialevents):
                if i < len(qmc.specialeventstype):
                    custom_events.append({
                        'time': event_time,
                        'type': qmc.specialeventstype[i],
                        'value': qmc.specialeventsvalue[i] if i < len(qmc.specialeventsvalue) else 0,
                        'description': qmc.specialeventsStrings[i] if i < len(qmc.specialeventsStrings) else ''
                    })
        
        # Calculate time since charge
        time_since_charge = None
        if charge_time is not None and len(qmc.timex) > 0:
            time_since_charge = qmc.timex[-1] - charge_time
        
        # Calculate rate of rise
        ror_et = None
        ror_bt = None
        if len(qmc.temp1) > 1 and len(qmc.timex) > 1:
            try:
                ror_et = (qmc.temp1[-1] - qmc.temp1[-2]) / (qmc.timex[-1] - qmc.timex[-2]) * 60  # °C/min
            except (IndexError, ZeroDivisionError):
                pass
                
        if len(qmc.temp2) > 1 and len(qmc.timex) > 1:
            try:
                ror_bt = (qmc.temp2[-1] - qmc.temp2[-2]) / (qmc.timex[-1] - qmc.timex[-2]) * 60  # °C/min
            except (IndexError, ZeroDivisionError):
                pass
        
        return {
            'type': 'roast_data',

            ## Roaster Info
            'roastertype': getattr(qmc, 'roastertype', None),
            'operator': getattr(qmc, 'operator', None),

            ## Roast Info
            'timestamp': time.time(),
            "roast_uuid": getattr(qmc, 'roastUUID', None),
            "title": getattr(qmc, 'title', None),
            # "roast_date": getattr(qmc, 'roastdate', None),
            # "roast_time": getattr(qmc, 'roasttime', None),
            'roast_time': qmc.timex[-1] if qmc.timex else 0,
            'time_since_charge': time_since_charge,

            ## Roast Info - Batch Info
            "roast_batch_number": getattr(qmc, 'roastbatchnr', None),
            "roast_batch_prefix": getattr(qmc, 'roastbatchprefix', None),
            "roast_batch_pos": getattr(qmc, 'roastbatchpos', None),

            ## Roast Info - Bean Info
            "bean_name": getattr(qmc, 'bean_name', None),
            "weight": {
                "in": self._safe_get_weight(qmc, 0),
                "out": self._safe_get_weight(qmc, 1),
                "unit": self._safe_get_weight(qmc, 2) if self._safe_get_weight(qmc, 2) else "kg"
            },

            ## Roast Info - Background Profile Info 
            "background_profile": {
                "background_path": getattr(qmc, 'backgroundpath', None),
                "background_uuid": getattr(qmc, 'backgroundUUID', None),
            },

            ## Roast Info - Ambient Temperature Info
            'ambient_temperature': getattr(qmc, 'ambientTemp', None),
            'ambient_humidity': getattr(qmc, 'ambient_humidity', None),

            ## Roast Info - Current Temperatures
            'current_temperatures': {
                'et': current_et,
                'bt': current_bt
            },
            'rate_of_rise': {
                'et': ror_et,
                'bt': ror_bt
            },

            ## Roast Info - Events
            'events': {
                'charge': {
                    'time': charge_time,
                    'temperature': charge_temp
                },
                'dry_end': {
                    'time': dry_end_time,
                    'temperature': dry_end_temp
                },
                'fc_start': {
                    'time': fc_start_time,
                    'temperature': fc_start_temp
                },
                'fc_end': {
                    'time': fc_end_time,
                    'temperature': fc_end_temp
                },
                'sc_start': {
                    'time': sc_start_time,
                    'temperature': sc_start_temp
                },
                'sc_end': {
                    'time': sc_end_time,
                    'temperature': sc_end_temp
                },
                'drop': {
                    'time': drop_time,
                    'temperature': drop_temp
                },
                'cool_end': {
                    'time': cool_end_time,
                    'temperature': cool_end_temp
                }
            },

            ## Roast Info - Custom Events
            'custom_events': custom_events,

            ## Roast Info - Roast State
            'roast_state': {
                'is_roasting': qmc.flagstart,
                'is_monitoring': qmc.flagon
            }
        }
    
    def _broadcast_roast_data(self, data: Dict[str, Any]) -> None:
        """Broadcast roast data to connected clients"""
        if not self.broadcaster or not self.broadcaster.is_connected():
            self.logger.debug("Cannot broadcast roast data: broadcaster not connected")
            return
            
        try:
            message = {
                'type': 'roast_data',
                'data': data,
                'timestamp': time.time()
            }
            
            self.broadcaster.broadcast(json.dumps(message))
            self.logger.debug("Broadcasted roast data")
            
        except Exception as e:
            self.logger.error(f"Error broadcasting roast data: {e}")
    
    def _broadcast_roast_event(self, event_type: str) -> None:
        """Broadcast roast lifecycle events"""
        if not self.broadcaster or not self.broadcaster.is_connected():
            self.logger.debug(f"Cannot broadcast roast event {event_type}: broadcaster not connected")
            return
            
        try:
            message = {
                'type': 'roast_event',
                'event': event_type,
                'timestamp': time.time()
            }
            
            self.broadcaster.broadcast(json.dumps(message))
            self.logger.info(f"Broadcasted roast event: {event_type}")
            
        except Exception as e:
            self.logger.error(f"Error broadcasting roast event: {e}")
    
    def _broadcast_event(self, event_name: str) -> None:
        """Broadcast standard roast events"""
        if not self.broadcaster or not self.broadcaster.is_connected():
            self.logger.debug(f"Cannot broadcast event {event_name}: broadcaster not connected")
            return
            
        try:
            # Get event data
            event_data = self._get_event_data(event_name)
            
            message = {
                'type': 'roast_event',
                'event': event_name,
                'data': event_data,
                'timestamp': time.time()
            }
            
            self.broadcaster.broadcast(json.dumps(message))
            self.logger.info(f"Broadcasted {event_name} event")
            
        except Exception as e:
            self.logger.error(f"Error broadcasting {event_name} event: {e}")
    
    def _broadcast_custom_event(self, event_data: Dict[str, Any]) -> None:
        """Broadcast custom events"""
        if not self.broadcaster or not self.broadcaster.is_connected():
            self.logger.debug("Cannot broadcast custom event: broadcaster not connected")
            return
            
        try:
            message = {
                'type': 'custom_event',
                'data': event_data,
                'timestamp': time.time()
            }
            
            self.broadcaster.broadcast(json.dumps(message))
            self.logger.info(f"Broadcasted custom event: {event_data.get('description', 'Unknown')}")
            
        except Exception as e:
            self.logger.error(f"Error broadcasting custom event: {e}")
    
    def _get_event_data(self, event_name: str) -> Dict[str, Any]:
        """Get data for a specific event"""
        if not self.main_window or not hasattr(self.main_window, 'qmc'):
            return {}
            
        qmc = self.main_window.qmc
        
        # Map event names to timeindex positions
        event_map = {
            'charge': 0,
            'dry_end': 1,
            'fc_start': 2,
            'fc_end': 3,
            'sc_start': 4,
            'sc_end': 5,
            'drop': 6,
            'cool_end': 7
        }
        
        if event_name not in event_map:
            return {}
            
        timeindex_idx = event_map[event_name]
        event_time = self._safe_get_timeindex(qmc, timeindex_idx)
        event_temp = self._safe_get_temp(qmc.temp2, qmc.timeindex[timeindex_idx]) if qmc.timeindex[timeindex_idx] > -1 else None
        
        # Calculate time since charge
        time_since_charge = None
        if event_time is not None and qmc.timeindex[0] > -1:
            charge_time = qmc.timex[qmc.timeindex[0]]
            time_since_charge = event_time - charge_time
        
        return {
            'event_name': event_name,
            'time': event_time,
            'time_since_charge': time_since_charge,
            'temperature': event_temp,
            'roast_time': qmc.timex[-1] if qmc.timex else 0
        }
    
    def _start_broadcaster(self) -> None:
        """Start the WebSocket broadcaster"""
        if not WEBSOCKETS_AVAILABLE:
            self.logger.error("Cannot start broadcaster: websockets library not available")
            return
            
        try:
            if self.broadcaster is None:
                self.broadcaster = WebSocketBroadcaster(
                    host=self.config.server_host,
                    port=self.config.server_port,
                    path=self.config.server_path,
                    reconnect_interval=self.config.reconnect_interval,
                    max_reconnect_attempts=self.config.max_reconnect_attempts
                )

                 # Register the message callback
                self.broadcaster.add_message_callback(self._on_ws_message)
                print("LiveBroadcastPlugin: WebSocket message callback registered")
                self.logger.info("LiveBroadcastPlugin: WebSocket message callback registered")
                
                # Connect status signals
                self.broadcaster.connected.connect(lambda: self._update_status("Connected"))
                self.broadcaster.disconnected.connect(lambda: self._update_status("Disconnected"))
                self.broadcaster.error.connect(lambda msg: self._update_status(f"Error: {msg}"))
            
            self.broadcaster.start()
            self._update_status("Connecting...")
            self.logger.info(f"Started broadcaster to {self.config.server_host}:{self.config.server_port}{self.config.server_path}")
            
        except Exception as e:
            self.logger.error(f"Error starting broadcaster: {e}")
            self._update_status(f"Error: {e}")
    
    def _stop_broadcaster(self) -> None:
        """Stop the WebSocket broadcaster"""
        if self.broadcaster:
            try:
                self.broadcaster.stop()
                self._update_status("Disconnected")
                self.logger.info("Stopped broadcaster")
            except Exception as e:
                self.logger.error(f"Error stopping broadcaster: {e}")
    
    def _configure(self) -> None:
        """Open configuration dialog"""
        try:
            from .config_dialog import LiveBroadcastConfigDialog
            dialog = LiveBroadcastConfigDialog(self.main_window, self.config)
            if dialog.exec():
                # Save configuration
                self.config.save_config()
                
                # Restart broadcaster if it's running
                if self.broadcaster and self.broadcaster.is_connected():
                    self._stop_broadcaster()
                    self._start_broadcaster()
                    
        except Exception as e:
            self.logger.error(f"Error opening config dialog: {e}")
            QMessageBox.warning(self.main_window, "Configuration Error", 
                              f"Error opening configuration dialog: {e}")
    
    def _update_status(self, status: str) -> None:
        """Update the status display"""
        if hasattr(self, 'status_action'):
            self.status_action.setText(f"Status: {status}")
        self.logger.info(f"Broadcaster status: {status}")
    
    def _test_event_broadcast(self) -> None:
        """Test event broadcasting"""
        self.logger.info("Testing event broadcast...")
        self._broadcast_event("charge")
    
    def _test_data_broadcast(self) -> None:
        """Test data broadcasting"""
        self.logger.info("Testing data broadcast...")
        test_data = {
            'type': 'roast_data',
            'timestamp': time.time(),
            'roast_time': 0,
            'time_since_charge': 0,
            'current_temperatures': {
                'et': 25.0,
                'bt': 25.0
            },
            'rate_of_rise': {
                'et': 0.0,
                'bt': 0.0
            },
            'events': {},
            'custom_events': [],
            'roast_state': {
                'is_roasting': False,
                'is_monitoring': False
            }
        }
        self._broadcast_roast_data(test_data)
    
    def _show_status(self) -> None:
        """Show current status"""
        status_info = []
        status_info.append(f"Plugin: {self.name} v{self.version}")
        status_info.append(f"WebSockets available: {WEBSOCKETS_AVAILABLE}")
        
        if self.broadcaster:
            status_info.append(f"Broadcaster connected: {self.broadcaster.is_connected()}")
            status_info.append(f"Server: {self.config.server_host}:{self.config.server_port}{self.config.server_path}")
        else:
            status_info.append("Broadcaster: None")
        
        if self.main_window and hasattr(self.main_window, 'qmc'):
            qmc = self.main_window.qmc
            status_info.append(f"Roast active: {qmc.flagstart}")
            status_info.append(f"Monitor active: {qmc.flagon}")
            status_info.append(f"Event states: {self.last_event_states}")
        
        status_text = "\n".join(status_info)
        self.logger.info(f"Status:\n{status_text}")
        QMessageBox.information(self.main_window, "Live Broadcast Status", status_text)

    def _show_incoming_message(self, data):
        msg = json.dumps(data, indent=2)
        def show_msgbox():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self.main_window, "Incoming WebSocket Message", msg)
        QTimer.singleShot(0, show_msgbox)


    ## TODO: handle starting and stopping roasting, monitoring mode (on/off) 
    def _on_ws_message(self, data):
        self.logger.info(f"LiveBroadcastPlugin received: {data}")

        if hasattr(self.main_window, "addserial"):
            self.main_window.addserial(f"LiveBroadcastPlugin received: {data}")

        if hasattr(self.main_window, "addmessage"):
            self.main_window.addmessage(f"LiveBroadcastPlugin received: {data}")
        
        # Handle custom_event messages 
        if data.get("type") == "custom_event":
            event_data = data.get("data", {})
            description = event_data.get("description", "").lower()
            
            if "charge" in description:
                self._mark_event_on_canvas("charge")
            elif "dry" in description:
                self._mark_event_on_canvas("dry_end")
            elif "fc start" in description:
                self._mark_event_on_canvas("fc_start")
            elif "fc end" in description:
                self._mark_event_on_canvas("fc_end")
            elif "sc start" in description:
                self._mark_event_on_canvas("sc_start")
            elif "sc end" in description:
                self._mark_event_on_canvas("sc_end")
            elif "drop" in description:
                self._mark_event_on_canvas("drop")
            elif "cool" in description:
                self._mark_event_on_canvas("cool_end")
        
        # Handle pushMessage messages (wsport.py format)
            push_message = data.get("pushMessage")
            
            if push_message == "addEvent":
                event_data = data.get("data", {})
                event_name = event_data.get("event")
                
                if event_name == "firstCrackBeginningEvent":
                    self._mark_event_on_canvas("fc_start")
                elif event_name == "firstCrackEndEvent":
                    self._mark_event_on_canvas("fc_end")
                elif event_name == "secondCrackBeginningEvent":
                    self._mark_event_on_canvas("sc_start")
                elif event_name == "secondCrackEndEvent":
                    self._mark_event_on_canvas("sc_end")
                elif event_name == "colorChangeEvent":
                    self._mark_event_on_canvas("dry_end")
            
            elif push_message == "startRoasting":
                self._mark_event_on_canvas("charge")
            
            elif push_message == "endRoasting":
                self._mark_event_on_canvas("drop")

    def _mark_event_on_canvas(self, event_name):
        qmc = getattr(self.main_window, "qmc", None)
        if not qmc:
            self.logger.error("Canvas (qmc) not found!")
            return

        # Map event_name to the correct method / signal
        if event_name == "charge" and hasattr(qmc, "markCharge"):
            qmc.markCharge()
        elif event_name == "dry_end" and hasattr(qmc, "markDryEnd"):
            qmc.markDryEnd() 
        elif event_name == "fc_start" and hasattr(qmc, "mark1Cstart"):
            qmc.mark1Cstart()
        elif event_name == "fc_end" and hasattr(qmc, "mark1Cend"):
            qmc.mark1Cend()
        elif event_name == "sc_start" and hasattr(qmc, "mark2Cstart"):
            qmc.mark2Cstart()
        elif event_name == "sc_end" and hasattr(qmc, "mark2Cend"):
            qmc.mark2Cend()
        elif event_name == "drop" and hasattr(qmc, "markDrop"):
            qmc.markDrop()
        elif event_name == 'cool_end' and hasattr(qmc, 'markCoolEnd'): 
            qmc.markCoolEnd()
        else:
            self.logger.warning(f"Unknown or unmapped event: {event_name}")

    def cleanup(self) -> None:
        """Cleanup when plugin is disabled/unloaded"""
        if self.broadcaster:
            self.broadcaster.stop()
        
        if self.update_timer:
            self.update_timer.stop()
        
        super().cleanup()