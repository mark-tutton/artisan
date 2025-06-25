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
from artisanlib.notifications import NotificationType

try:
    from .websocket_client import WebSocketBroadcaster, WEBSOCKETS_AVAILABLE
except ImportError:
    WebSocketBroadcaster = None
    WEBSOCKETS_AVAILABLE = False

_log = logging.getLogger(__name__)


class LiveBroadcastSignals(QObject):
    """A dedicated QObject to handle signals for the LiveBroadcastPlugin."""
    mark_event_signal = pyqtSignal(str, bool)
    toggle_monitoring_signal = pyqtSignal(bool)
    toggle_roasting_signal = pyqtSignal(bool)
    reset_roast_signal = pyqtSignal()

class LiveBroadcastPlugin(ArtisanPlugin):
    """Plugin for broadcasting live roast data and events to external servers"""
    
    mark_event_signal = pyqtSignal(str, bool)
    
    @property
    def name(self) -> str:
        return "Live Broadcast"
    
    @property
    def version(self) -> str:
        return "1.1.0"
    
    def __init__(self):
        super().__init__()
        self.signals = LiveBroadcastSignals()
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
        
        self.signals.mark_event_signal.connect(self._mark_event_on_canvas)
        
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
            
            # Connect control signals
            if hasattr(main_window.qmc, 'ToggleMonitor'):
                self.signals.toggle_monitoring_signal.connect(main_window.qmc.ToggleMonitor)
                self.logger.info("Connected toggle_monitoring_signal to qmc.onoff")
            if hasattr(main_window.qmc, 'ToggleRecorder'):
                self.signals.toggle_roasting_signal.connect(main_window.qmc.ToggleRecorder)
                self.logger.info("Connected toggle_roasting_signal to qmc.startstop")
            if hasattr(main_window.qmc, 'reset'):
                self.signals.reset_roast_signal.connect(main_window.qmc.reset)
                self.logger.info("Connected reset_roast_signal to qmc.reset")

            
            
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

                # monitoring data timer - broadcasts sensor data even when not roasting
                try:
                    self.monitoring_timer = QTimer()
                    self.monitoring_timer.timeout.connect(self._broadcast_monitoring_data)
                    self.monitoring_timer.start(1000)  # every 2 secs
                    _log.info("Started monitoring data broadcast timer")
                except Exception as e:
                    self.logger.error(f"Error starting monitoring timer: {e}")

            # Connect to roast data signals
            if hasattr(main_window, 'qmc'):
                self.logger.info("Found qmc object, connecting to signals...")
                
                # Connect to temperature update signals
                if hasattr(main_window.qmc, 'updategraphicsSignal'):
                    main_window.qmc.updategraphicsSignal.connect(self._on_data_update)
                    self.logger.info("Connected to updategraphicsSignal")
                
                # device-specific update signals (deviceUpdateSignal, sensorUpdateSignal)
                if hasattr(main_window.qmc, 'device'):
                    if hasattr(main_window.qmc, 'deviceUpdateSignal'):
                        main_window.qmc.deviceUpdateSignal.connect(self._on_device_update)
                        self.logger.info("Connected to deviceUpdateSignal")
                    
                    if hasattr(main_window.qmc, 'sensorUpdateSignal'):
                        main_window.qmc.sensorUpdateSignal.connect(self._on_sensor_update)
                        self.logger.info("Connected to sensorUpdateSignal")
                
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
        if noaction:
            return
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_event("charge")
    
    def _on_dry_end_event(self, noaction: bool = False) -> None:
        """Handle DRY END event"""
        self.logger.info(f"DRY END event triggered (noaction={noaction})")
        if noaction:
            return
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_event("dry_end")
    
    def _on_fc_start_event(self, noaction: bool = False) -> None:
        """Handle FC START event"""
        self.logger.info(f"FC START event triggered (noaction={noaction})")
        if noaction:
            return
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_event("fc_start")
    
    def _on_fc_end_event(self, noaction: bool = False) -> None:
        """Handle FC END event"""
        self.logger.info(f"FC END event triggered (noaction={noaction})")
        if noaction:
            return
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_event("fc_end")
    
    def _on_sc_start_event(self, noaction: bool = False) -> None:
        """Handle SC START event"""
        self.logger.info(f"SC START event triggered (noaction={noaction})")
        if noaction:
            return
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_event("sc_start")
    
    def _on_sc_end_event(self, noaction: bool = False) -> None:
        """Handle SC END event"""
        self.logger.info(f"SC END event triggered (noaction={noaction})")
        if noaction:
            return
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_event("sc_end")
    
    def _on_drop_event(self, noaction: bool = False) -> None:
        """Handle DROP event"""
        self.logger.info(f"DROP event triggered (noaction={noaction})")
        if noaction:
            return
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_event("drop")
    
    def _on_cool_end_event(self, noaction: bool = False) -> None:
        """Handle COOL END event"""
        self.logger.info(f"COOL END event triggered (noaction={noaction})")
        if noaction:
            return
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

        # Get extra temperature sensors
        extra_temperatures = self._get_extra_temperatures(qmc)
        
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
        
        # # Calculate rate of rise
        # ror_et = None
        # ror_bt = None
        # if len(qmc.temp1) > 1 and len(qmc.timex) > 1:
        #     try:
        #         ror_et = (qmc.temp1[-1] - qmc.temp1[-2]) / (qmc.timex[-1] - qmc.timex[-2]) * 60  # °C/min
        #     except (IndexError, ZeroDivisionError):
        #         pass
                
        # if len(qmc.temp2) > 1 and len(qmc.timex) > 1:
        #     try:
        #         ror_bt = (qmc.temp2[-1] - qmc.temp2[-2]) / (qmc.timex[-1] - qmc.timex[-2]) * 60  # °C/min
        #     except (IndexError, ZeroDivisionError):
        #         pass

        # ROR
        ror_et = getattr(qmc, 'rateofchange1', None)
        ror_bt = getattr(qmc, 'rateofchange2', None)

        # Fallback to manual calc
        if ror_et is None and len(qmc.temp1) >= 2 and len(qmc.timex) >= 2:
            try:
                ror_et = (qmc.temp1[-1] - qmc.temp1[-2]) / (qmc.timex[-1] - qmc.timex[-2]) * 60
            except (IndexError, ZeroDivisionError):
                ror_et = None

        if ror_bt is None and len(qmc.temp2) >= 2 and len(qmc.timex) >= 2:
            try:
                ror_bt = (qmc.temp2[-1] - qmc.temp2[-2]) / (qmc.timex[-1] - qmc.timex[-2]) * 60
            except (IndexError, ZeroDivisionError):
                ror_bt = None
        
        # Get monitoring state
        monitoring_state = self._get_monitoring_state(qmc)
        
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

            # Roast Info - Extra Temp Sensors
            'extra_temperatures': extra_temperatures,

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
            },

            # Monitoring Info
            'monitoring_state': monitoring_state
        }
    
    def _get_extra_temperatures(self, qmc) -> Dict[str, Any]:
        """Extract extra temperature sensor data"""
        extra_temps = {
            'sensors': [],
            'total_sensors': 0
        }
        
        try:
            # Get extra temperature 1 sensors
            if hasattr(qmc, 'extratemp1') and hasattr(qmc, 'extraname1'):
                for i, temp_list in enumerate(qmc.extratemp1):
                    if temp_list and len(temp_list) > 0:
                        sensor_name = qmc.extraname1[i] if i < len(qmc.extraname1) else f"Extra1_{i}"
                        current_temp = self._safe_get_temp(temp_list)
                        extra_temps['sensors'].append({
                            'name': sensor_name,
                            'type': 'extra1',
                            'index': i,
                            'temperature': current_temp,
                            'unit': '°F'
                        })
            
            # Get extra temperature 2 sensors
            if hasattr(qmc, 'extratemp2') and hasattr(qmc, 'extraname2'):
                for i, temp_list in enumerate(qmc.extratemp2):
                    if temp_list and len(temp_list) > 0:
                        sensor_name = qmc.extraname2[i] if i < len(qmc.extraname2) else f"Extra2_{i}"
                        current_temp = self._safe_get_temp(temp_list)
                        extra_temps['sensors'].append({
                            'name': sensor_name,
                            'type': 'extra2',
                            'index': i,
                            'temperature': current_temp,
                            'unit': '°F'
                        })
            
            extra_temps['total_sensors'] = len(extra_temps['sensors'])
            
        except Exception as e:
            self.logger.error(f"Error getting extra temperatures: {e}")
        
        return extra_temps
    
    
    def _get_monitoring_state(self, qmc) -> Dict[str, Any]:
        """Extract comprehensive monitoring state information"""
        monitoring_state = {
            'system_status': {},
            'device_status': {},
            'sensor_status': {},
            'sensor_values': {},
            'flags': {},
            'connection_status': {}
        }
        
        try:
            # Get current sensor readings from real-time values
            et_temp = getattr(qmc, 'RTtemp1', None)
            bt_temp = getattr(qmc, 'RTtemp2', None)
            
            et_active = et_temp is not None and et_temp != 0.0
            bt_active = bt_temp is not None and bt_temp != 0.0
            
            self.logger.info(f"RTtemp1 (ET): {et_temp}, RTtemp2 (BT): {bt_temp}")
            self.logger.info(f"ET active: {et_active}, BT active: {bt_active}")
            
            # System status
            monitoring_state['system_status'] = {
                'is_monitoring': getattr(qmc, 'flagon', False),
                'is_roasting': getattr(qmc, 'flagstart', False),
                'is_sampling': getattr(qmc, 'flagsampling', False),
                'is_sampling_thread_running': getattr(qmc, 'flagsamplingthreadrunning', False),
                'is_keep_on': getattr(qmc, 'flagKeepON', False),
                'is_open_completed': getattr(qmc, 'flagOpenCompleted', False),
                'uptime': self._safe_get_uptime(qmc)
            }
            
            # Device status
            monitoring_state['device_status'] = {
                'device_type': getattr(qmc, 'device', None),
                'device_logging': getattr(qmc, 'device_logging', False),
                'device_log_file': getattr(qmc, 'device_log_file_name', None),
                'phidget_manager_active': hasattr(qmc, 'phidgetManager') and qmc.phidgetManager is not None,
                'yocto_remote_flag': getattr(qmc, 'yoctoRemoteFlag', False),
                'phidget_remote_flag': getattr(qmc, 'phidgetRemoteFlag', False)
            }
            
            # Sensor status
            monitoring_state['sensor_status'] = {
                'et_sensor_active': et_active,
                'bt_sensor_active': bt_active,
                'extra_sensors_count': len(qmc.extratemp1) + len(qmc.extratemp2) if hasattr(qmc, 'extratemp1') and hasattr(qmc, 'extratemp2') else 0,
                'ambient_sensor_active': getattr(qmc, 'ambientTemp', None) is not None,
                'pressure_sensor_active': getattr(qmc, 'ambient_pressure', None) is not None,
                'humidity_sensor_active': getattr(qmc, 'ambient_humidity', None) is not None
            }
            
            # Sensor values 
            monitoring_state['sensor_values'] = {
                'et_temperature': et_temp,
                'bt_temperature': bt_temp,
                'ambient_temperature': getattr(qmc, 'ambientTemp', None),
                'ambient_pressure': getattr(qmc, 'ambient_pressure', None),
                'ambient_humidity': getattr(qmc, 'ambient_humidity', None),
                'extra_sensors': self._get_extra_sensor_values(qmc)
            }
            
            # Event flags
            monitoring_state['flags'] = {
                'auto_charge_enabled': getattr(qmc, 'autoCHARGEenabled', False),
                'auto_dry_enabled': getattr(qmc, 'autoDRYenabled', False),
                'auto_fc_enabled': getattr(qmc, 'autoFCsenabled', False),
                'auto_drop_enabled': getattr(qmc, 'autoDROPenabled', False),
                'charge_timer_flag': getattr(qmc, 'chargeTimerFlag', False),
                'auto_charge_flag': getattr(qmc, 'autoChargeFlag', False),
                'auto_drop_flag': getattr(qmc, 'autoDropFlag', False),
                'mark_tp_flag': getattr(qmc, 'markTPflag', False),
                'auto_dry_flag': getattr(qmc, 'autoDRYflag', False),
                'auto_fcs_flag': getattr(qmc, 'autoFCsFlag', False),
                'delta_et_flag': getattr(qmc, 'DeltaETflag', False),
                'delta_bt_flag': getattr(qmc, 'DeltaBTflag', False),
                'pid_button_flag': getattr(qmc, 'PIDbuttonflag', False),
                'control_button_flag': getattr(qmc, 'Controlbuttonflag', False)
            }
            
            # Connection status
            monitoring_state['connection_status'] = {
                'phidget_devices_connected': len(getattr(qmc, 'phidgetDevices', [])) if hasattr(qmc, 'phidgetDevices') else 0,
                'non_serial_devices_connected': len(getattr(qmc, 'nonSerialDevices', [])) if hasattr(qmc, 'nonSerialDevices') else 0,
                'non_temp_devices_connected': len(getattr(qmc, 'nonTempDevices', [])) if hasattr(qmc, 'nonTempDevices') else 0,
                'special_devices_connected': len(getattr(qmc, 'specialDevices', [])) if hasattr(qmc, 'specialDevices') else 0,
                'binary_devices_connected': len(getattr(qmc, 'binaryDevices', [])) if hasattr(qmc, 'binaryDevices') else 0,
                'extra_devices_connected': len(getattr(qmc, 'extradevices', [])) if hasattr(qmc, 'extradevices') else 0
            }
            
        except Exception as e:
            self.logger.error(f"Error getting monitoring state: {e}")
        
        return monitoring_state
    
    def _get_extra_sensor_values(self, qmc) -> Dict[str, Any]:
        """Get current values from extra sensors"""
        sensor_values = {
            'extra1_sensors': {},
            'extra2_sensors': {},
            'all_sensors': {}
        }
        
        try:
            # Get extra temperature 1 sensors
            if hasattr(qmc, 'extratemp1') and hasattr(qmc, 'extraname1'):
                for i, temp_list in enumerate(qmc.extratemp1):
                    if temp_list and len(temp_list) > 0:
                        sensor_name = qmc.extraname1[i] if i < len(qmc.extraname1) else f"Extra1_{i}"
                        current_temp = self._safe_get_temp(temp_list)
                        
                        sensor_values['extra1_sensors'][f"sensor_{i}"] = {
                            'name': sensor_name,
                            'temperature': current_temp,
                            'unit': '°F'
                        }
                        
                        sensor_values['all_sensors'][sensor_name] = {
                            'type': 'extra1',
                            'index': i,
                            'temperature': current_temp,
                            'unit': '°F'
                        }
            
            # Get extra temperature 2 sensors
            if hasattr(qmc, 'extratemp2') and hasattr(qmc, 'extraname2'):
                for i, temp_list in enumerate(qmc.extratemp2):
                    if temp_list and len(temp_list) > 0:
                        sensor_name = qmc.extraname2[i] if i < len(qmc.extraname2) else f"Extra2_{i}"
                        current_temp = self._safe_get_temp(temp_list)
                        
                        sensor_values['extra2_sensors'][f"sensor_{i}"] = {
                            'name': sensor_name,
                            'temperature': current_temp,
                            'unit': '°F'
                        }
                        
                        sensor_values['all_sensors'][sensor_name] = {
                            'type': 'extra2',
                            'index': i,
                            'temperature': current_temp,
                            'unit': '°F'
                        }
            
        except Exception as e:
            self.logger.error(f"Error getting extra sensor values: {e}")
        
        return sensor_values
    
    def _safe_get_uptime(self, qmc) -> float:
        """Safely get uptime value"""
        try:
            if hasattr(qmc, 'timeclock'):
                timeclock = qmc.timeclock
                if hasattr(timeclock, 'total_seconds'):
                    return timeclock.total_seconds()
                elif isinstance(timeclock, (int, float)):
                    return float(timeclock)
                else:
                    return float(timeclock) if timeclock else 0.0
            else:
                return 0.0
        except (ValueError, TypeError, AttributeError):
            return 0.0
    
    def _broadcast_roast_data(self, data: Dict[str, Any]) -> None:
        """Broadcast roast data to connected clients"""
        # if not self.broadcaster or not self.broadcaster.is_connected():
        #     self.logger.debug("Cannot broadcast roast data: broadcaster not connected")
        #     return
        if not self.broadcaster or not self.broadcaster.is_running:
            self.logger.debug("Cannot broadcast roast data: broadcaster not running")
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
    
    def _broadcast_monitoring_data(self) -> None:
        """Broadcast monitoring state data independently of roast data"""
        try:
            if not WEBSOCKETS_AVAILABLE or not self.broadcaster or not self.broadcaster.is_running:
                return
                
            if not self.main_window or not hasattr(self.main_window, 'qmc'):
                return
                
            qmc = self.main_window.qmc
            
            # Only broadcast if monitoring is active
            if not getattr(qmc, 'flagon', False):
                self.logger.info("Monitoring is not active, skipping broadcast")
                return
            
            self.logger.info("Broadcasting monitoring data")

            self.logger.info(f"temp1 exists: {hasattr(qmc, 'temp1')}, temp1 length: {len(qmc.temp1) if hasattr(qmc, 'temp1') else 'N/A'}")
            self.logger.info(f"temp2 exists: {hasattr(qmc, 'temp2')}, temp2 length: {len(qmc.temp2) if hasattr(qmc, 'temp2') else 'N/A'}")
            
            et_active = hasattr(qmc, 'temp1') and qmc.temp1 and len(qmc.temp1) > 0
            bt_active = hasattr(qmc, 'temp2') and qmc.temp2 and len(qmc.temp2) > 0
            
            # Get current temp values
            et_temp = self._safe_get_temp(qmc.temp1) if et_active else None
            bt_temp = self._safe_get_temp(qmc.temp2) if bt_active else None
            
            self.logger.info(f"ET active: {et_active}, ET temp: {et_temp}")
            self.logger.info(f"BT active: {bt_active}, BT temp: {bt_temp}")
            
            # Get monitoring state
            try:
                monitoring_state = self._get_monitoring_state(qmc)
            except Exception as e:
                self.logger.error(f"Error getting monitoring state: {e}")
                return
            
            message = {
                'type': 'monitoring_data',
                'data': {
                    'monitoring_state': monitoring_state,
                    'timestamp': time.time()
                }
            }
            
            self.broadcaster.broadcast(json.dumps(message))
            self.logger.debug("Broadcasted monitoring data")
            
        except Exception as e:
            self.logger.error(f"Error in _broadcast_monitoring_data: {e}")

    def _broadcast_roast_event(self, event_type: str) -> None:
        """Broadcast roast lifecycle events"""
        # if not self.broadcaster or not self.broadcaster.is_connected():
        #     self.logger.debug(f"Cannot broadcast roast event {event_type}: broadcaster not connected")
        #     return
        if not self.broadcaster or not self.broadcaster.is_running:
            self.logger.debug(f"Cannot broadcast roast event {event_type}: broadcaster not running")
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
        # if not self.broadcaster or not self.broadcaster.is_connected():
        #     self.logger.debug(f"Cannot broadcast event {event_name}: broadcaster not connected")
        #     return
        if not self.broadcaster or not self.broadcaster.is_running:
            self.logger.debug(f"Cannot broadcast event {event_name}: broadcaster not running")
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
        # if not self.broadcaster or not self.broadcaster.is_connected():
        #     self.logger.debug("Cannot broadcast custom event: broadcaster not connected")
        #     return
        if not self.broadcaster or not self.broadcaster.is_running:
            self.logger.debug("Cannot broadcast custom event: broadcaster not running")
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

        if hasattr(self.main_window, 'notifications'): #TODO: redo this
            title = "Live Broadcast"
            message = None
            
            if status.lower() == 'connected':
                message = "Successfully connected to the broadcast server."
            elif status.lower() == 'disconnected':
                message = "Disconnected from the broadcast server."

            if message:
                self.main_window.notifications.sendNotificationMessage(
                    title,
                    message,
                    NotificationType.ARTISAN_SYSTEM
                )
    
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


    def _on_ws_message(self, data):
        self.logger.info(f"LiveBroadcastPlugin received: {data}")

        if hasattr(self.main_window, "addserial"):
            self.main_window.addserial(f"LiveBroadcastPlugin received: {data}")

        if hasattr(self.main_window, "addmessage"):
            self.main_window.addmessage(f"LiveBroadcastPlugin received: {data}")


        msg_type = data.get("type")

        # Handle roast control messages
        if msg_type == "roast_control":
            command = data.get("command")
            if command == "toggle_monitoring":
                self.logger.info("Received command to toggle monitoring state (ON/OFF).")
                self.signals.toggle_monitoring_signal.emit(False)
            elif command == "toggle_roasting":
                self.logger.info("Received command to toggle roasting state (START/DROP).")
                self.signals.toggle_roasting_signal.emit(False)
            elif command == "reset": 
                self.logger.info("Received command to reset roast.")
                self.signals.reset_roast_signal.emit()
            else:
                self.logger.warning(f"Unknown roast_control command: {command}")

        # Handle roast_event messages
        if data.get("type") == "roast_event":
            event_name = data.get("event")
            if event_name:
                self.logger.info(f"Marking event on canvas from roast_event: {event_name}")
                # self._mark_event_on_canvas(event_name, noaction=True)
                self.signals.mark_event_signal.emit(event_name, True)
        

        
        # Handle custom_event messages 
        if data.get("type") == "custom_event":
            event_data = data.get("data", {})
            description = event_data.get("description", "").lower()
            

            event_to_mark = None
            if "charge" in description:
                event_to_mark = "charge"
            elif "dry" in description:
                event_to_mark = "dry_end"
            elif "fc start" in description:
                event_to_mark = "fc_start"
            elif "fc end" in description:
                event_to_mark = "fc_end"
            elif "sc start" in description:
                event_to_mark = "sc_start"
            elif "sc end" in description:
                event_to_mark = "sc_end"
            elif "drop" in description:
                event_to_mark = "drop"
            elif "cool" in description:
                event_to_mark = "cool_end"

            if event_to_mark:
                self.signals.mark_event_signal.emit(event_to_mark, True)

        
        # Handle pushMessage messages (wsport.py format)
        push_message = data.get("pushMessage")
            

        if push_message == "addEvent":
            event_data = data.get("data", {})
            event_name = event_data.get("event")

            event_to_mark = None
            if event_name == "firstCrackBeginningEvent":
                event_to_mark = "fc_start"
            elif event_name == "firstCrackEndEvent":
                event_to_mark = "fc_end"
            elif event_name == "secondCrackBeginningEvent":
                event_to_mark = "sc_start"
            elif event_name == "secondCrackEndEvent":
                event_to_mark = "sc_end"
            elif event_name == "colorChangeEvent":
                event_to_mark = "dry_end"
            
            if event_to_mark:
                self.signals.mark_event_signal.emit(event_to_mark, True)
        
        elif push_message == "startRoasting":
            self.signals.mark_event_signal.emit("charge", True)
        
        elif push_message == "endRoasting":
            self.signals.mark_event_signal.emit("drop", True)

    def _mark_event_on_canvas(self, event_name, noaction=False):
        qmc = getattr(self.main_window, "qmc", None)
        if not qmc:
            self.logger.error("Canvas (qmc) not found!")
            return

        if event_name == "charge" and hasattr(qmc, "markCharge"):
            qmc.markCharge(noaction)
        elif event_name == "dry_end" and hasattr(qmc, "markDryEnd"):
            qmc.markDryEnd(noaction) 
        elif event_name == "fc_start" and hasattr(qmc, "mark1Cstart"):
            qmc.mark1Cstart(noaction)
        elif event_name == "fc_end" and hasattr(qmc, "mark1Cend"):
            qmc.mark1Cend(noaction)
        elif event_name == "sc_start" and hasattr(qmc, "mark2Cstart"):
            qmc.mark2Cstart(noaction)
        elif event_name == "sc_end" and hasattr(qmc, "mark2Cend"):
            qmc.mark2Cend(noaction)
        elif event_name == "drop" and hasattr(qmc, "markDrop"):
            qmc.markDrop(noaction)
        elif event_name == 'cool_end' and hasattr(qmc, 'markCoolEnd'): 
            qmc.markCoolEnd(noaction)
        else:
            self.logger.warning(f"Unknown or unmapped event: {event_name}")

    def _on_device_update(self) -> None:
        """Handle device updates (including sensor readings)"""
        _log.info("Device update received")
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_monitoring_data()
    
    def _on_sensor_update(self) -> None:
        """Handle sensor updates"""
        _log.info("Sensor update received")
        if WEBSOCKETS_AVAILABLE:
            self._broadcast_monitoring_data()

    def cleanup(self) -> None:
        """Cleanup when plugin is disabled/unloaded"""
        if self.broadcaster:
            self.broadcaster.stop()
        
        if self.update_timer:
            self.update_timer.stop()

        if hasattr(self, 'monitoring_timer'):
            self.monitoring_timer.stop()
        
        super().cleanup()