import asyncio
import json
import logging
import time
import traceback
from typing import Dict, Any, Optional, List, Callable
from threading import Thread
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

try:
    from PyQt6.QtWidgets import QMenu, QMainWindow, QMessageBox, QDialog
    from PyQt6.QtGui import QAction
    from PyQt6.QtCore import QTimer, pyqtSignal, QObject
except ImportError:
    from PyQt5.QtWidgets import QMenu, QMainWindow, QMessageBox, QDialog
    from PyQt5.QtGui import QAction
    from PyQt5.QtCore import QTimer, pyqtSignal, QObject

from ..base import PluginBase
from .config import LiveBroadcastConfig
from artisanlib.notifications import NotificationType

try:
    from .websocket_client import WebSocketBroadcaster, WEBSOCKETS_AVAILABLE
except ImportError:
    WebSocketBroadcaster = None
    WEBSOCKETS_AVAILABLE = False

_log = logging.getLogger(__name__)


class BroadcastState(Enum):
    """Broadcast connection states"""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class BroadcastMetrics:
    """Broadcast performance metrics"""

    messages_sent: int = 0
    messages_failed: int = 0
    bytes_sent: int = 0
    last_send_time: Optional[datetime] = None
    last_receive_time: Optional[datetime] = None
    connection_attempts: int = 0
    successful_connections: int = 0
    failed_connections: int = 0
    total_uptime: float = 0.0
    start_time: Optional[datetime] = None


class LiveBroadcastSignals(QObject):
    """A dedicated QObject to handle signals for the LiveBroadcastPlugin."""

    mark_event_signal = pyqtSignal(str, bool)
    toggle_monitoring_signal = pyqtSignal(bool)
    toggle_roasting_signal = pyqtSignal(bool)
    reset_roast_signal = pyqtSignal()
    broadcast_state_changed = pyqtSignal(str)  # new_state
    broadcast_error = pyqtSignal(str)  # error_message


class LiveBroadcastPlugin(PluginBase):
    @property
    def name(self) -> str:
        return "Live Broadcast"

    @property
    def version(self) -> str:
        return "2.0.0"

    @property
    def description(self) -> str:
        return f"{self.name} v{self.version} - Real-time roast data broadcasting"

    def __init__(self):
        super().__init__()

        # Core components
        self.signals = LiveBroadcastSignals()
        self.config = LiveBroadcastConfig()
        self.broadcaster: Optional[WebSocketBroadcaster] = None

        # Timers
        self.update_timer: Optional[QTimer] = None
        self.monitoring_timer: Optional[QTimer] = None
        self.health_check_timer: Optional[QTimer] = None

        # State tracking
        self.broadcast_state = BroadcastState.DISCONNECTED
        self.last_broadcast_time = 0
        self.broadcast_interval = 1.0  # seconds

        # Event tracking
        self.last_event_states = {
            "charge": False,
            "dry_end": False,
            "fc_start": False,
            "fc_end": False,
            "sc_start": False,
            "sc_end": False,
            "drop": False,
            "cool_end": False,
        }

        # Performance metrics
        self.metrics = BroadcastMetrics()

        # Connection health
        self.last_heartbeat = 0
        self.heartbeat_interval = 30  # seconds

        # Error recovery
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5

        # Headless mode detection
        self.headless_mode = False

    def _initialize_plugin(self) -> None:
        """Initialize the plugin with comprehensive error handling"""
        try:
            # Check headless mode
            self.headless_mode = getattr(self.config, "headless_mode", False)

            # Connect signals
            self.signals.mark_event_signal.connect(self._mark_event_on_canvas)

            # Check websockets availability
            if not WEBSOCKETS_AVAILABLE:
                self._record_error(
                    "WebSocketsUnavailable",
                    "websockets library not available. Live broadcasting functionality will be disabled.",
                    {"install_command": "pip install websockets"},
                )
                return

            self.logger.info(
                f"Initializing Live Broadcast Plugin (headless: {self.headless_mode})..."
            )

            # Setup main window connections
            self._setup_main_window_connections()

            # Setup timers
            self._setup_timers()

            # Start broadcaster if auto-start is enabled
            if self.config.auto_start:
                self.logger.info("Auto-start enabled, starting broadcaster...")
                self._start_broadcaster()
            else:
                self.logger.info("Auto-start disabled, broadcaster not started")

        except Exception as e:
            self._record_error("InitializationError", str(e))
            raise

    def _setup_main_window_connections(self) -> None:
        """Setup connections to main window signals"""
        try:
            if not hasattr(self.main_window, "qmc"):
                self._record_error("MainWindowError", "qmc object not found on main_window")
                return

            qmc = self.main_window.qmc
            self.logger.info("Setting up main window connections...")

            # Temperature update signals
            if hasattr(qmc, "updategraphicsSignal"):
                qmc.updategraphicsSignal.connect(self._on_data_update)
                self.logger.info("Connected to updategraphicsSignal")

            # Control signals
            self._connect_control_signals(qmc)

            # Event signals
            self._connect_event_signals(qmc)

            # Custom event signals
            if hasattr(qmc, "eventRecordSignal"):
                qmc.eventRecordSignal.connect(self._on_custom_event)
                self.logger.info("Connected to eventRecordSignal")

            # Device update signals
            self._connect_device_signals(qmc)

        except Exception as e:
            self._record_error("ConnectionSetupError", str(e))

    def _connect_control_signals(self, qmc) -> None:
        """Connect control signals"""
        try:
            signal_connections = [
                ("ToggleMonitor", self.signals.toggle_monitoring_signal),
                ("ToggleRecorder", self.signals.toggle_roasting_signal),
                ("reset", self.signals.reset_roast_signal),
            ]

            for method_name, signal in signal_connections:
                if hasattr(qmc, method_name):
                    signal.connect(getattr(qmc, method_name))
                    self.logger.info(f"Connected {signal.__class__.__name__} to qmc.{method_name}")
                else:
                    self.logger.warning(f"Method {method_name} not found on qmc")

        except Exception as e:
            self._record_error("ControlSignalError", str(e))

    def _connect_event_signals(self, qmc) -> None:
        """Connect event signals"""
        try:
            signal_connections = [
                ("markChargeSignal", self._on_charge_event),
                ("markDRYSignal", self._on_dry_end_event),
                ("markFCsSignal", self._on_fc_start_event),
                ("markFCeSignal", self._on_fc_end_event),
                ("markSCsSignal", self._on_sc_start_event),
                ("markSCeSignal", self._on_sc_end_event),
                ("markDropSignal", self._on_drop_event),
                ("markCoolSignal", self._on_cool_end_event),
            ]

            for signal_name, handler in signal_connections:
                if hasattr(qmc, signal_name):
                    signal = getattr(qmc, signal_name)
                    signal.connect(handler)
                    self.logger.info(f"Connected to {signal_name}")
                else:
                    self.logger.warning(f"Signal {signal_name} not found on qmc")

        except Exception as e:
            self._record_error("EventSignalError", str(e))

    def _connect_device_signals(self, qmc) -> None:
        """Connect device update signals"""
        try:
            if hasattr(qmc, "device"):
                device_signals = [
                    ("deviceUpdateSignal", self._on_device_update),
                    ("sensorUpdateSignal", self._on_sensor_update),
                ]

                for signal_name, handler in device_signals:
                    if hasattr(qmc, signal_name):
                        signal = getattr(qmc, signal_name)
                        signal.connect(handler)
                        self.logger.info(f"Connected to {signal_name}")

        except Exception as e:
            self._record_error("DeviceSignalError", str(e))

    def _setup_timers(self) -> None:
        """Setup timers"""
        try:
            # Roast state monitoring timer
            if hasattr(self.main_window.qmc, "flagstart"):
                self.update_timer = QTimer()
                self.update_timer.timeout.connect(self._check_roast_state)
                self.update_timer.start(1000)  # Check every second
                self.logger.info("Started roast state monitoring timer")

            # Monitoring data broadcast timer
            self.monitoring_timer = QTimer()
            self.monitoring_timer.timeout.connect(self._broadcast_monitoring_data)
            self.monitoring_timer.start(1000)  # every second
            self.logger.info("Started monitoring data broadcast timer")

            # Health check timer
            self.health_check_timer = QTimer()
            self.health_check_timer.timeout.connect(self._health_check)
            self.health_check_timer.start(30000)  # every 30 seconds
            self.logger.info("Started health check timer")

        except Exception as e:
            self._record_error("TimerSetupError", str(e))

    def _create_plugin_menu(self, parent_menu: QMenu) -> Optional[QMenu]:
        """Create plugin menu with headless mode support"""
        if self.headless_mode:
            self.logger.info("Skipping menu creation in headless mode")
            return None

        try:
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
            status_action = QAction("Show Status", menu)
            status_action.triggered.connect(self._show_status)
            menu.addAction(status_action)

            menu.addSeparator()

            # Test actions
            test_event_action = QAction("Test Event Broadcast", menu)
            test_event_action.triggered.connect(self._test_event_broadcast)
            menu.addAction(test_event_action)

            test_data_action = QAction("Test Data Broadcast", menu)
            test_data_action.triggered.connect(self._test_data_broadcast)
            menu.addAction(test_data_action)

            return menu

        except Exception as e:
            self._record_error("MenuCreationError", str(e))
            return None

    def _on_roast_start_impl(self) -> None:
        """Handle roast start"""
        try:
            self.logger.info("Roast started - beginning data broadcast")
            self.metrics.start_time = datetime.now()
            self._broadcast_roast_event("roast_start")
        except Exception as e:
            self._record_error("RoastStartError", str(e))

    def _on_roast_end_impl(self) -> None:
        """Handle roast end"""
        try:
            self.logger.info("Roast ended - finalizing data broadcast")
            if self.metrics.start_time:
                self.metrics.total_uptime += (
                    datetime.now() - self.metrics.start_time
                ).total_seconds()
            self._broadcast_roast_event("roast_end")
        except Exception as e:
            self._record_error("RoastEndError", str(e))

    def _on_data_update_impl(self, data: Dict[str, Any]) -> None:
        """Handle data updates"""
        try:
            self._broadcast_roast_data(data)
        except Exception as e:
            self._record_error("DataUpdateError", str(e), {"data_keys": list(data.keys())})

    def _check_roast_state(self) -> None:
        """Check roast state"""
        try:
            if not hasattr(self.main_window, "qmc"):
                return

            qmc = self.main_window.qmc

            # Check if roasting has started
            if hasattr(qmc, "flagstart") and qmc.flagstart:
                if not hasattr(self, "_roast_started") or not self._roast_started:
                    self._roast_started = True
                    self._on_roast_start_impl()

            # Check if roasting has ended
            elif hasattr(self, "_roast_started") and self._roast_started:
                self._roast_started = False
                self._on_roast_end_impl()

        except Exception as e:
            self._record_error("RoastStateCheckError", str(e))

    def _check_event_states(self) -> None:
        """Check event states"""
        try:
            if not hasattr(self.main_window, "qmc"):
                return

            qmc = self.main_window.qmc

            # Check each event state
            for event_name, last_state in self.last_event_states.items():
                current_state = self._get_event_state(qmc, event_name)
                if current_state != last_state:
                    self.last_event_states[event_name] = current_state
                if current_state:
                    self._broadcast_roast_event(event_name)

        except Exception as e:
            self._record_error("EventStateCheckError", str(e))

    def _get_event_state(self, qmc, event_name: str) -> bool:
        """Get current state of an event"""
        try:
            # Map event names to qmc attributes
            event_map = {
                "charge": "timeindex",
                "dry_end": "timeindex",
                "fc_start": "timeindex",
                "fc_end": "timeindex",
                "sc_start": "timeindex",
                "sc_end": "timeindex",
                "drop": "timeindex",
                "cool_end": "timeindex",
            }

            if event_name in event_map:
                attr_name = event_map[event_name]
                if hasattr(qmc, attr_name):
                    timeindex = getattr(qmc, attr_name)
                    # Check if the specific event index is set
                    event_indices = {
                        "charge": 0,
                        "dry_end": 1,
                        "fc_start": 2,
                        "fc_end": 3,
                        "sc_start": 4,
                        "sc_end": 5,
                        "drop": 6,
                        "cool_end": 7,
                    }
                    if event_name in event_indices:
                        return (
                            len(timeindex) > event_indices[event_name]
                            and timeindex[event_indices[event_name]] != -1
                        )

            return False

        except Exception as e:
            self._record_error("EventStateError", str(e), {"event_name": event_name})
            return False

    def _on_charge_event(self, noaction: bool = False) -> None:
        """Handle charge event"""
        try:
            if not noaction:
                self._broadcast_roast_event("charge")
        except Exception as e:
            self._record_error("ChargeEventError", str(e))

    def _on_dry_end_event(self, noaction: bool = False) -> None:
        """Handle dry end event"""
        try:
            if not noaction:
                self._broadcast_roast_event("dry_end")
        except Exception as e:
            self._record_error("DryEndEventError", str(e))

    def _on_fc_start_event(self, noaction: bool = False) -> None:
        """Handle FC start event"""
        try:
            if not noaction:
                self._broadcast_roast_event("fc_start")
        except Exception as e:
            self._record_error("FCStartEventError", str(e))

    def _on_fc_end_event(self, noaction: bool = False) -> None:
        """Handle FC end event"""
        try:
            if not noaction:
                self._broadcast_roast_event("fc_end")
        except Exception as e:
            self._record_error("FCEndEventError", str(e))

    def _on_sc_start_event(self, noaction: bool = False) -> None:
        """Handle SC start event"""
        try:
            if not noaction:
                self._broadcast_roast_event("sc_start")
        except Exception as e:
            self._record_error("SCStartEventError", str(e))

    def _on_sc_end_event(self, noaction: bool = False) -> None:
        """Handle SC end event"""
        try:
            if not noaction:
                self._broadcast_roast_event("sc_end")
        except Exception as e:
            self._record_error("SCEndEventError", str(e))

    def _on_drop_event(self, noaction: bool = False) -> None:
        """Handle drop event"""
        try:
            if not noaction:
                self._broadcast_roast_event("drop")
        except Exception as e:
            self._record_error("DropEventError", str(e))

    def _on_cool_end_event(self, noaction: bool = False) -> None:
        """Handle cool end event"""
        try:
            if not noaction:
                self._broadcast_roast_event("cool_end")
        except Exception as e:
            self._record_error("CoolEndEventError", str(e))

    def _on_custom_event(self, event_index: int) -> None:
        """Handle custom event"""
        try:
            if not hasattr(self.main_window, "qmc"):
                return

            qmc = self.main_window.qmc

            # Get custom event data
            event_data = self._get_custom_event_data(qmc, event_index)
            if event_data:
                self._broadcast_custom_event(event_data)

        except Exception as e:
            self._record_error("CustomEventError", str(e), {"event_index": event_index})

    def _get_custom_event_data(self, qmc, event_index: int) -> Optional[Dict[str, Any]]:
        """Get custom event data"""
        try:
            if not hasattr(qmc, "etypesf") or not hasattr(qmc, "eventsvalues"):
                return None

            event_type = qmc.etypesf(event_index)
            event_value = qmc.eventsvalues(event_index)

            return {
                "type": "custom_event",
                "event_type": event_type,
                "event_value": event_value,
                "event_index": event_index,
                "timestamp": time.time(),
            }

        except Exception as e:
            self._record_error("CustomEventDataError", str(e), {"event_index": event_index})
            return None

    def _on_data_update(self) -> None:
        """Handle data updates"""
        try:
            if not hasattr(self.main_window, "qmc"):
                return

            qmc = self.main_window.qmc

            # Get current roast data
            roast_data = self._get_current_roast_data()
            if roast_data:
                self._broadcast_roast_data(roast_data)

        except Exception as e:
            self._record_error("DataUpdateError", str(e))

    def _safe_get_timeindex(self, qmc, index: int) -> Optional[float]:
        """Safely get time index"""
        try:
            if hasattr(qmc, "timeindex") and len(qmc.timeindex) > index:
                return qmc.timeindex[index]
            return None
        except Exception as e:
            self._record_error("TimeIndexError", str(e), {"index": index})
        return None

    def _safe_get_weight(self, qmc, index: int) -> float:
        """Safely get weight"""
        try:
            if hasattr(qmc, "weight") and len(qmc.weight) > index:
                return qmc.weight[index]
            return 0.0
        except Exception as e:
            self._record_error("WeightError", str(e), {"index": index})
        return 0.0

    def _safe_get_temp(self, temp_list, index: int = -1) -> Optional[float]:
        """Safely get temperature"""
        try:
            if temp_list and len(temp_list) > abs(index):
                return temp_list[index]
            return None
        except Exception as e:
            self._record_error(
                "TemperatureError",
                str(e),
                {"index": index, "list_length": len(temp_list) if temp_list else 0},
            )
        return None

    def _get_current_roast_data(self) -> Optional[Dict[str, Any]]:
        """Get current roast data with comprehensive error handling"""
        try:
            if not hasattr(self.main_window, "qmc"):
                return None

            qmc = self.main_window.qmc

            # Get basic roast data
            roast_data = {
                "type": "roast_data",
                "timestamp": time.time(),
                "current_temperatures": {},
                "rate_of_rise": {},
                "roast_time": 0,
                "roast_state": {
                    "is_roasting": getattr(qmc, "flagstart", False),
                    "is_monitoring": getattr(qmc, "flagon", False),
                },
            }

            # Get temperatures
            try:
                if hasattr(qmc, "temp1") and qmc.temp1:
                    roast_data["current_temperatures"]["et"] = self._safe_get_temp(qmc.temp1)
                if hasattr(qmc, "temp2") and qmc.temp2:
                    roast_data["current_temperatures"]["bt"] = self._safe_get_temp(qmc.temp2)
            except Exception as e:
                self._record_error("TemperatureDataError", str(e))

            # Get rate of rise
            try:
                if hasattr(qmc, "rateofchange1"):
                    roast_data["rate_of_rise"]["et"] = qmc.rateofchange1
                if hasattr(qmc, "rateofchange2"):
                    roast_data["rate_of_rise"]["bt"] = qmc.rateofchange2
            except Exception as e:
                self._record_error("RateOfRiseError", str(e))

            # Get roast time
            try:
                if hasattr(qmc, "timex") and qmc.timex:
                    roast_data["roast_time"] = qmc.timex[-1] if qmc.timex else 0
            except Exception as e:
                self._record_error("RoastTimeError", str(e))

            # Get events
            try:
                events = {}
                event_names = [
                    "charge",
                    "dry_end",
                    "fc_start",
                    "fc_end",
                    "sc_start",
                    "sc_end",
                    "drop",
                    "cool_end",
                ]
                for i, event_name in enumerate(event_names):
                    time_index = self._safe_get_timeindex(qmc, i)
                    if time_index is not None and time_index != -1:
                        events[event_name] = {
                            "time": time_index,
                            "temperature": (
                                self._safe_get_temp(qmc.temp2, int(time_index))
                                if hasattr(qmc, "temp2")
                                else None
                            ),
                        }
                roast_data["events"] = events
            except Exception as e:
                self._record_error("EventsDataError", str(e))

            # Get extra temperatures
            try:
                roast_data["extra_temperatures"] = self._get_extra_temperatures(qmc)
            except Exception as e:
                self._record_error("ExtraTemperaturesError", str(e))

            # Get monitoring state
            try:
                roast_data["monitoring_state"] = self._get_monitoring_state(qmc)
            except Exception as e:
                self._record_error("MonitoringStateError", str(e))

            return roast_data

        except Exception as e:
            self._record_error("RoastDataError", str(e))
            return None

    def _get_extra_temperatures(self, qmc) -> Dict[str, Any]:
        """Get extra temperatures"""
        try:
            extra_data = {"sensors": [], "total_sensors": 0}

            # Get extra temperature data
            if hasattr(qmc, "extratemp1") and hasattr(qmc, "extratemp2"):
                sensors = []

                # Process extra1 temperatures
                for i, temp in enumerate(qmc.extratemp1):
                    if temp is not None and temp != 0:
                        sensor_name = (
                            f"Extra1_{i}"
                            if not hasattr(qmc, "extraname1") or i >= len(qmc.extraname1)
                            else qmc.extraname1[i]
                        )
                        sensors.append(
                            {
                                "name": sensor_name,
                                "type": "extra1",
                                "index": i,
                                "temperature": temp,
                                "unit": "°F",
                            }
                        )

                # Process extra2 temperatures
                for i, temp in enumerate(qmc.extratemp2):
                    if temp is not None and temp != 0:
                        sensor_name = (
                            f"Extra2_{i}"
                            if not hasattr(qmc, "extraname2") or i >= len(qmc.extraname2)
                            else qmc.extraname2[i]
                        )
                        sensors.append(
                            {
                                "name": sensor_name,
                                "type": "extra2",
                                "index": i,
                                "temperature": temp,
                                "unit": "°F",
                            }
                        )

                extra_data["sensors"] = sensors
                extra_data["total_sensors"] = len(sensors)

            return extra_data

        except Exception as e:
            self._record_error("ExtraTemperaturesError", str(e))
            return {"sensors": [], "total_sensors": 0}

    def _get_monitoring_state(self, qmc) -> Dict[str, Any]:
        """Get monitoring state"""
        try:
            monitoring_state = {
                "system_status": {},
                "device_status": {},
                "sensor_status": {},
                "sensor_values": {},
                "flags": {},
                "connection_status": {},
            }

            # System status
            try:
                monitoring_state["system_status"] = {
                    "is_monitoring": getattr(qmc, "flagon", False),
                    "is_roasting": getattr(qmc, "flagstart", False),
                    "is_sampling": getattr(qmc, "flagstart", False),
                    "is_sampling_thread_running": getattr(qmc, "sampling_thread_running", False),
                    "is_keep_on": getattr(qmc, "keep_on", False),
                    "is_open_completed": getattr(qmc, "open_completed", False),
                    "uptime": self._safe_get_uptime(qmc),
                }
            except Exception as e:
                self._record_error("SystemStatusError", str(e))

            # Device status
            try:
                monitoring_state["device_status"] = {
                    "device_type": getattr(qmc, "device", 0),
                    "device_logging": getattr(qmc, "device_logging", False),
                    "device_log_file": getattr(qmc, "device_log_file", ""),
                    "phidget_manager_active": getattr(qmc, "phidget_manager_active", False),
                    "yocto_remote_flag": getattr(qmc, "yocto_remote_flag", False),
                    "phidget_remote_flag": getattr(qmc, "phidget_remote_flag", False),
                }
            except Exception as e:
                self._record_error("DeviceStatusError", str(e))

            # Sensor status
            try:
                monitoring_state["sensor_status"] = {
                    "et_sensor_active": bool(getattr(qmc, "temp1", [])),
                    "bt_sensor_active": bool(getattr(qmc, "temp2", [])),
                    "extra_sensors_count": len(getattr(qmc, "extratemp1", []))
                    + len(getattr(qmc, "extratemp2", [])),
                    "ambient_sensor_active": getattr(qmc, "ambientTemp", None) is not None,
                    "pressure_sensor_active": getattr(qmc, "pressure", None) is not None,
                    "humidity_sensor_active": getattr(qmc, "humidity", None) is not None,
                }
            except Exception as e:
                self._record_error("SensorStatusError", str(e))

            # Sensor values
            try:
                monitoring_state["sensor_values"] = self._get_extra_sensor_values(qmc)
            except Exception as e:
                self._record_error("SensorValuesError", str(e))

            # Flags
            try:
                monitoring_state["flags"] = {
                    "auto_charge_enabled": getattr(qmc, "auto_charge_enabled", False),
                    "auto_dry_enabled": getattr(qmc, "auto_dry_enabled", False),
                    "auto_fc_enabled": getattr(qmc, "auto_fc_enabled", False),
                    "auto_drop_enabled": getattr(qmc, "auto_drop_enabled", False),
                    "charge_timer_flag": getattr(qmc, "charge_timer_flag", False),
                    "auto_charge_flag": getattr(qmc, "auto_charge_flag", False),
                    "auto_drop_flag": getattr(qmc, "auto_drop_flag", False),
                    "mark_tp_flag": getattr(qmc, "mark_tp_flag", False),
                    "auto_dry_flag": getattr(qmc, "auto_dry_flag", False),
                    "auto_fcs_flag": getattr(qmc, "auto_fcs_flag", False),
                    "delta_et_flag": getattr(qmc, "delta_et_flag", False),
                    "delta_bt_flag": getattr(qmc, "delta_bt_flag", False),
                    "pid_button_flag": getattr(qmc, "pid_button_flag", False),
                    "control_button_flag": getattr(qmc, "control_button_flag", False),
                }
            except Exception as e:
                self._record_error("FlagsError", str(e))

            # Connection status
            try:
                monitoring_state["connection_status"] = {
                    "phidget_devices_connected": getattr(qmc, "phidget_devices_connected", 0),
                    "non_serial_devices_connected": getattr(qmc, "non_serial_devices_connected", 0),
                    "non_temp_devices_connected": getattr(qmc, "non_temp_devices_connected", 0),
                    "special_devices_connected": getattr(qmc, "special_devices_connected", 0),
                    "binary_devices_connected": getattr(qmc, "binary_devices_connected", 0),
                    "extra_devices_connected": getattr(qmc, "extra_devices_connected", 0),
                }
            except Exception as e:
                self._record_error("ConnectionStatusError", str(e))

            return monitoring_state

        except Exception as e:
            self._record_error("MonitoringStateError", str(e))
            return {}

    def _get_extra_sensor_values(self, qmc) -> Dict[str, Any]:
        """Get extra sensor values"""
        try:
            sensor_values = {
                "et_temperature": None,
                "bt_temperature": None,
                "ambient_temperature": None,
                "ambient_pressure": None,
                "ambient_humidity": None,
                "extra_sensors": {"extra1_sensors": {}, "extra2_sensors": {}, "all_sensors": {}},
            }

            # Get ET and BT temperatures
            try:
                if hasattr(qmc, "RTtemp1"):
                    sensor_values["et_temperature"] = qmc.RTtemp1
                if hasattr(qmc, "RTtemp2"):
                    sensor_values["bt_temperature"] = qmc.RTtemp2
            except Exception as e:
                self._record_error("ETBTError", str(e))

            # Get ambient values
            try:
                if hasattr(qmc, "ambientTemp"):
                    sensor_values["ambient_temperature"] = qmc.ambientTemp
                if hasattr(qmc, "pressure"):
                    sensor_values["ambient_pressure"] = qmc.pressure
                if hasattr(qmc, "humidity"):
                    sensor_values["ambient_humidity"] = qmc.humidity
            except Exception as e:
                self._record_error("AmbientError", str(e))

            # Get extra sensor values
            try:
                if hasattr(qmc, "extratemp1"):
                    for i, temp in enumerate(qmc.extratemp1):
                        if temp is not None and temp != 0:
                            sensor_name = f"sensor_{i}"
                            if hasattr(qmc, "extraname1") and i < len(qmc.extraname1):
                                sensor_name = qmc.extraname1[i] or f"sensor_{i}"

                            sensor_values["extra_sensors"]["extra1_sensors"][sensor_name] = {
                                "name": sensor_name,
                                "temperature": temp,
                                "unit": "°F",
                            }

                            sensor_values["extra_sensors"]["all_sensors"][sensor_name] = {
                                "type": "extra1",
                                "index": i,
                                "temperature": temp,
                                "unit": "°F",
                            }

                if hasattr(qmc, "extratemp2"):
                    for i, temp in enumerate(qmc.extratemp2):
                        if temp is not None and temp != 0:
                            sensor_name = f"sensor_{i}"
                            if hasattr(qmc, "extraname2") and i < len(qmc.extraname2):
                                sensor_name = qmc.extraname2[i] or f"sensor_{i}"

                            sensor_values["extra_sensors"]["extra2_sensors"][sensor_name] = {
                                "name": sensor_name,
                                "temperature": temp,
                                "unit": "°F",
                            }

                            sensor_values["extra_sensors"]["all_sensors"][sensor_name] = {
                                "type": "extra2",
                                "index": i,
                                "temperature": temp,
                                "unit": "°F",
                            }
            except Exception as e:
                self._record_error("ExtraSensorValuesError", str(e))

            return sensor_values

        except Exception as e:
            self._record_error("SensorValuesError", str(e))
            return {}

    def _safe_get_uptime(self, qmc) -> float:
        """Safely get uptime"""
        try:
            if hasattr(qmc, "uptime"):
                return qmc.uptime
            return 0.0
        except Exception as e:
            self._record_error("UptimeError", str(e))
            return 0.0

    def _broadcast_roast_data(self, data: Dict[str, Any]) -> None:
        """Broadcast roast data"""
        try:
            if not self.broadcaster or not self.broadcaster.is_running:
                return

            message = json.dumps(data)
            self.broadcaster.broadcast(message)

            # Update metrics
            self.metrics.messages_sent += 1
            self.metrics.bytes_sent += len(message.encode("utf-8"))
            self.metrics.last_send_time = datetime.now()

        except Exception as e:
            self._record_error("BroadcastDataError", str(e))
            self.metrics.messages_failed += 1
            self.consecutive_failures += 1

    def _broadcast_monitoring_data(self) -> None:
        """Broadcast monitoring data"""
        try:
            if not hasattr(self.main_window, "qmc"):
                return

            qmc = self.main_window.qmc

            # Get monitoring state
            monitoring_state = self._get_monitoring_state(qmc)

            # Create monitoring message
            monitoring_data = {
                "type": "monitoring_data",
                "monitoring_state": monitoring_state,
                "timestamp": time.time(),
            }

            self._broadcast_roast_data(monitoring_data)

        except Exception as e:
            self._record_error("MonitoringDataError", str(e))

    def _broadcast_roast_event(self, event_type: str) -> None:
        """Broadcast roast event"""
        try:
            if not self.broadcaster or not self.broadcaster.is_running:
                return

            event_data = self._get_event_data(event_type)
            if event_data:
                self._broadcast_roast_data(event_data)

        except Exception as e:
            self._record_error("BroadcastEventError", str(e), {"event_type": event_type})

    def _broadcast_event(self, event_name: str) -> None:
        """Broadcast event"""
        try:
            if not self.broadcaster or not self.broadcaster.is_running:
                return

            event_data = {"type": "roast_event", "event": event_name, "timestamp": time.time()}

            # Add event-specific data
            if hasattr(self.main_window, "qmc"):
                qmc = self.main_window.qmc
                event_data["data"] = {
                    "time": self._safe_get_uptime(qmc),
                    "temperature": (
                        self._safe_get_temp(qmc.temp2) if hasattr(qmc, "temp2") else None
                    ),
                }

            self._broadcast_roast_data(event_data)

        except Exception as e:
            self._record_error("BroadcastEventError", str(e), {"event_name": event_name})

    def _broadcast_custom_event(self, event_data: Dict[str, Any]) -> None:
        """Broadcast custom event"""
        try:
            if not self.broadcaster or not self.broadcaster.is_running:
                return

            custom_data = {
                "type": "custom_event",
                "event_data": event_data,
                "timestamp": time.time(),
            }

            self._broadcast_roast_data(custom_data)

        except Exception as e:
            self._record_error("BroadcastCustomEventError", str(e))

    def _get_event_data(self, event_name: str) -> Dict[str, Any]:
        """Get event data"""
        try:
            if not hasattr(self.main_window, "qmc"):
                return {}

            qmc = self.main_window.qmc

            event_data = {
                "type": "roast_event",
                "event": event_name,
                "data": {
                    "time": self._safe_get_uptime(qmc),
                    "temperature": (
                        self._safe_get_temp(qmc.temp2) if hasattr(qmc, "temp2") else None
                    ),
                },
            }

            return event_data

        except Exception as e:
            self._record_error("EventDataError", str(e), {"event_name": event_name})
            return {}

    def _start_broadcaster(self) -> None:
        """Start broadcaster"""
        try:
            if self.broadcaster and self.broadcaster.is_running:
                self.logger.info("Broadcaster already running")
                return

            self._change_broadcast_state(BroadcastState.CONNECTING)

            self.broadcaster = WebSocketBroadcaster(
                host=self.config.server_host,
                port=self.config.server_port,
                path=self.config.server_path,
                reconnect_interval=self.config.reconnect_interval,
                max_reconnect_attempts=self.config.max_reconnect_attempts,
            )

            # Add connection handlers
            self.broadcaster.add_connection_handler(self._on_connected)
            self.broadcaster.add_disconnection_handler(self._on_disconnected)

            # Add message callback
            self.broadcaster.add_message_callback(self._on_ws_message)

            # Start broadcaster
            self.broadcaster.start()

            self.metrics.connection_attempts += 1
            self.logger.info("Broadcaster started successfully")

        except Exception as e:
            self._record_error("StartBroadcasterError", str(e))
            self._change_broadcast_state(BroadcastState.ERROR)
            self.metrics.failed_connections += 1

    def _stop_broadcaster(self) -> None:
        """Stop broadcaster"""
        try:
            if self.broadcaster:
                self.broadcaster.stop()
                self.broadcaster = None

            self._change_broadcast_state(BroadcastState.DISCONNECTED)
            self.logger.info("Broadcaster stopped")

        except Exception as e:
            self._record_error("StopBroadcasterError", str(e))

    def _on_connected(self) -> None:
        """Handle connection"""
        try:
            self._change_broadcast_state(BroadcastState.CONNECTED)
            self.metrics.successful_connections += 1
            self.consecutive_failures = 0
            self.logger.info("Connected to broadcast server")

            # # Send notification if not in headless mode
            # if not self.headless_mode and hasattr(self.main_window, "sendNotificationMessage"):
            #     self.main_window.sendNotificationMessage(
            #         "Live Broadcast",
            #         "Connected to broadcast server",
            #         NotificationType.ARTISAN_SYSTEM,
            #     )

        except Exception as e:
            self._record_error("ConnectionHandlerError", str(e))

    def _on_disconnected(self) -> None:
        """Handle disconnection"""
        try:
            self._change_broadcast_state(BroadcastState.DISCONNECTED)
            self.logger.info("Disconnected from broadcast server")

            # # Send notification if not in headless mode
            # if not self.headless_mode and hasattr(self.main_window, "sendNotificationMessage"):
            #     self.main_window.sendNotificationMessage(
            #         "Live Broadcast",
            #         "Disconnected from broadcast server",
            #         NotificationType.ARTISAN_SYSTEM,
            #     )

        except Exception as e:
            self._record_error("DisconnectionHandlerError", str(e))

    def _change_broadcast_state(self, new_state: BroadcastState) -> None:
        """Change broadcast state and emit signal"""
        try:
            old_state = self.broadcast_state
            self.broadcast_state = new_state
            self.logger.info(f"Broadcast state changed: {old_state.value} -> {new_state.value}")
            self.signals.broadcast_state_changed.emit(new_state.value)
        except Exception as e:
            self._record_error("BroadcastStateChangeError", str(e))

    def _configure(self) -> None:
        """Show configuration dialog with headless mode support"""
        if self.headless_mode:
            self.logger.warning("Configuration dialog not available in headless mode")
            return

        try:
            from .config_dialog import LiveBroadcastConfigDialog

            dialog = LiveBroadcastConfigDialog(self.main_window, self.config)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.config.save_config()
                self.logger.info("Configuration updated and saved")
        except Exception as e:
            self._record_error("ConfigurationError", str(e))

    def _show_status(self) -> None:
        """Show status with headless mode support"""
        if self.headless_mode:
            self.logger.info(f"Broadcast status: {self.broadcast_state.value}")
            return

        try:
            status_text = f"Broadcast Status: {self.broadcast_state.value}\n"
            status_text += f"Messages Sent: {self.metrics.messages_sent}\n"
            status_text += f"Messages Failed: {self.metrics.messages_failed}\n"
            status_text += f"Connection Attempts: {self.metrics.connection_attempts}\n"
            status_text += f"Successful Connections: {self.metrics.successful_connections}\n"
            status_text += f"Failed Connections: {self.metrics.failed_connections}"

            QMessageBox.information(self.main_window, "Broadcast Status", status_text)
        except Exception as e:
            self._record_error("StatusDisplayError", str(e))

    def _test_event_broadcast(self) -> None:
        """Test event broadcast"""
        try:
            test_event = {
                "type": "test_event",
                "event": "test",
                "data": {
                    "time": time.time(),
                    "temperature": 100.0,
                    "message": "Test event from Live Broadcast Plugin",
                },
            }

            self._broadcast_roast_data(test_event)
            self.logger.info("Test event broadcast sent")

        except Exception as e:
            self._record_error("TestEventError", str(e))

    def _test_data_broadcast(self) -> None:
        """Test data broadcast"""
        try:
            test_data = {
                "type": "test_data",
                "timestamp": time.time(),
                "current_temperatures": {"et": 200.0, "bt": 180.0},
                "rate_of_rise": {"et": 5.0, "bt": 4.0},
                "roast_time": 300.0,
                "message": "Test data from Live Broadcast Plugin",
            }

            self._broadcast_roast_data(test_data)
            self.logger.info("Test data broadcast sent")

        except Exception as e:
            self._record_error("TestDataError", str(e))

    def _show_incoming_message(self, data):
        """Handle incoming messages with headless mode support"""
        if self.headless_mode:
            self.logger.info(f"Incoming message: {data}")
        else:
            try:

                def show_msgbox():
                    QMessageBox.information(self.main_window, "Incoming Message", str(data))

                QTimer.singleShot(0, show_msgbox)
            except Exception as e:
                self._record_error("IncomingMessageError", str(e))

    def _on_ws_message(self, data):
        """Handle WebSocket messages with comprehensive error handling"""
        try:
            self.metrics.last_receive_time = datetime.now()

            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError as e:
                    self._record_error("JSONDecodeError", str(e), {"raw_data": data})
                    return

            if not isinstance(data, dict):
                self._record_error("InvalidMessageType", f"Expected dict, got {type(data)}")
                return

            msg_type = data.get("type")
            if not msg_type:
                self._record_error("MissingMessageType", "Message missing 'type' field")
                return

            self.logger.debug(f"Received message type: {msg_type}")

            # Handle different message types
            if msg_type == "roast_control":
                self._handle_roast_control(data)
            elif msg_type == "test":
                self._handle_test_message(data)
            elif msg_type == "ping":
                self._handle_ping(data)
            elif msg_type == "connection_established":
                self._handle_connection_established(data)
            elif msg_type == "pong":
                self._handle_pong(data)
            elif msg_type == "error":
                self._handle_server_error(data)
            else:
                self.logger.warning(f"Unknown message type: {msg_type}")

        except Exception as e:
            self._record_error("WebSocketMessageError", str(e), {"data": str(data)})

    def _handle_roast_control(self, data: Dict[str, Any]) -> None:
        """Handle roast control messages"""
        try:
            command = data.get("command")
            if not command:
                self._record_error(
                    "MissingCommand", "Roast control message missing 'command' field"
                )
                return

            self.logger.info(f"Received roast control command: {command}")

            if command == "toggle_monitoring":
                self.signals.toggle_monitoring_signal.emit(True)
            elif command == "toggle_roasting":
                self.signals.toggle_roasting_signal.emit(True)
            elif command == "reset":
                self.signals.reset_roast_signal.emit()
            else:
                self.logger.warning(f"Unknown roast control command: {command}")

        except Exception as e:
            self._record_error("RoastControlError", str(e), {"command": data.get("command")})

    def _handle_test_message(self, data: Dict[str, Any]) -> None:
        """Handle test messages"""
        try:
            message = data.get("message", "Test message received")
            self.logger.info(f"Test message: {message}")

            # Send test response
            response = {
                "type": "test_response",
                "message": f"Test response from {self.name}",
                "timestamp": time.time(),
            }

            self._broadcast_roast_data(response)

        except Exception as e:
            self._record_error("TestMessageError", str(e))

    def _handle_ping(self, data: Dict[str, Any]) -> None:
        """Handle ping messages"""
        try:
            # Send pong response
            response = {"type": "pong", "timestamp": time.time()}

            self._broadcast_roast_data(response)

        except Exception as e:
            self._record_error("PingError", str(e))

    def _handle_connection_established(self, data: Dict[str, Any]) -> None:
        """Handle connection established message from server"""
        try:
            message = data.get("message", "Connection established")
            timestamp = data.get("timestamp")
            current_state = data.get("currentState", {})

            self.logger.info(f"Server connection established: {message}")

            if timestamp:
                self.logger.debug(f"Server timestamp: {timestamp}")

            if current_state:
                self.logger.debug(f"Server current state: {current_state}")

        except Exception as e:
            self._record_error("ConnectionEstablishedError", str(e))

    def _handle_pong(self, data: Dict[str, Any]) -> None:
        """Handle pong response from server"""
        try:
            timestamp = data.get("timestamp")
            self.logger.debug(f"Received pong from server (timestamp: {timestamp})")
        except Exception as e:
            self._record_error("PongError", str(e))

    def _handle_server_error(self, data: Dict[str, Any]) -> None:
        """Handle error message from server"""
        try:
            error_message = data.get("message", "Unknown server error")
            error_code = data.get("code")

            self.logger.warning(f"Server error: {error_message}")
            if error_code:
                self.logger.warning(f"Server error code: {error_code}")

        except Exception as e:
            self._record_error("ServerErrorHandlerError", str(e))

    def _mark_event_on_canvas(self, event_name: str, noaction: bool = False) -> None:
        """Mark event on canvas"""
        try:
            if noaction:
                return

            if not hasattr(self.main_window, "qmc"):
                return

            qmc = self.main_window.qmc

            # Map event names to qmc methods
            event_methods = {
                "charge": "markCharge",
                "dry_end": "markDRY",
                "fc_start": "markFCs",
                "fc_end": "markFCe",
                "sc_start": "markSCs",
                "sc_end": "markSCe",
                "drop": "markDrop",
                "cool_end": "markCool",
            }

            if event_name in event_methods:
                method_name = event_methods[event_name]
                if hasattr(qmc, method_name):
                    method = getattr(qmc, method_name)
                    method()
                    self.logger.info(f"Marked event on canvas: {event_name}")
                else:
                    self.logger.warning(f"Method {method_name} not found on qmc")
            else:
                self.logger.warning(f"Unknown event name: {event_name}")

        except Exception as e:
            self._record_error("MarkEventError", str(e), {"event_name": event_name})

    def _on_device_update(self) -> None:
        """Handle device updates"""
        try:
            self.logger.debug("Device update received")
            # Could broadcast device status here if needed
        except Exception as e:
            self._record_error("DeviceUpdateError", str(e))

    def _on_sensor_update(self) -> None:
        """Handle sensor updates"""
        try:
            self.logger.debug("Sensor update received")
            # Could broadcast sensor status here if needed
        except Exception as e:
            self._record_error("SensorUpdateError", str(e))

    def _health_check(self) -> None:
        """Periodic health check"""
        try:
            # Check connection health
            if self.broadcaster and self.broadcaster.is_running and self.metrics.last_send_time:

                time_since_last_send = (
                    datetime.now() - self.metrics.last_send_time
                ).total_seconds()
                if time_since_last_send > 60:  # No data sent for 1 minute
                    self.logger.warning(f"No data sent for {time_since_last_send:.1f} seconds")

            # Check consecutive failures
            if self.consecutive_failures >= self.max_consecutive_failures:
                self.logger.error(
                    f"Too many consecutive failures ({self.consecutive_failures}), attempting recovery"
                )
                self._attempt_recovery()

            # Log health status periodically
            if self.has_errors:
                self.logger.info(f"Plugin health: {self.get_health_status()}")

        except Exception as e:
            self._record_error("HealthCheckError", str(e))

    def _attempt_recovery(self) -> None:
        """Attempt to recover from errors"""
        try:
            self.logger.info("Attempting error recovery...")

            # Reset consecutive failures
            self.consecutive_failures = 0

            # Restart broadcaster if needed
            if self.broadcast_state == BroadcastState.ERROR:
                self._stop_broadcaster()
                time.sleep(2)  # Wait before restarting
                self._start_broadcaster()

            # Reset error state
            self.reset_errors()

            self.logger.info("Recovery attempt completed")

        except Exception as e:
            self._record_error("RecoveryError", str(e))

    def _cleanup_plugin(self) -> None:
        """Cleanup the plugin with comprehensive error handling"""
        try:
            self.logger.info(f"Cleaning up {self.name}")

            # Stop timers
            if self.update_timer:
                self.update_timer.stop()
                self.update_timer.deleteLater()
                self.update_timer = None

            if self.monitoring_timer:
                self.monitoring_timer.stop()
                self.monitoring_timer.deleteLater()
                self.monitoring_timer = None

            if self.health_check_timer:
                self.health_check_timer.stop()
                self.health_check_timer.deleteLater()
                self.health_check_timer = None

            # Stop broadcaster
            if self.broadcaster:
                self.broadcaster.stop()
                self.broadcaster = None

            # Disconnect signals
            if hasattr(self, "signals"):
                try:
                    self.signals.mark_event_signal.disconnect()
                    self.signals.toggle_monitoring_signal.disconnect()
                    self.signals.toggle_roasting_signal.disconnect()
                    self.signals.reset_roast_signal.disconnect()
                except Exception as e:
                    self.logger.warning(f"Error disconnecting signals: {e}")

            # Update final metrics
            if self.metrics.start_time:
                self.metrics.total_uptime += (
                    datetime.now() - self.metrics.start_time
                ).total_seconds()

            self.logger.info(f"Cleanup completed for {self.name}")

        except Exception as e:
            self._record_error("CleanupError", str(e))

    def get_plugin_status(self) -> Dict[str, Any]:
        """Get comprehensive plugin status"""
        try:
            base_status = super().get_health_status()

            # Add broadcast-specific status
            broadcast_status = {
                "broadcast_state": self.broadcast_state.value,
                "headless_mode": self.headless_mode,
                "websockets_available": WEBSOCKETS_AVAILABLE,
                "broadcaster_running": self.broadcaster.is_running if self.broadcaster else False,
                "metrics": {
                    "messages_sent": self.metrics.messages_sent,
                    "messages_failed": self.metrics.messages_failed,
                    "bytes_sent": self.metrics.bytes_sent,
                    "connection_attempts": self.metrics.connection_attempts,
                    "successful_connections": self.metrics.successful_connections,
                    "failed_connections": self.metrics.failed_connections,
                    "total_uptime": self.metrics.total_uptime,
                    "last_send_time": (
                        self.metrics.last_send_time.isoformat()
                        if self.metrics.last_send_time
                        else None
                    ),
                    "last_receive_time": (
                        self.metrics.last_receive_time.isoformat()
                        if self.metrics.last_receive_time
                        else None
                    ),
                },
                "consecutive_failures": self.consecutive_failures,
                "config": {
                    "server_host": self.config.server_host,
                    "server_port": self.config.server_port,
                    "auto_start": self.config.auto_start,
                    "broadcast_interval": self.config.broadcast_interval,
                },
            }

            base_status.update(broadcast_status)
            return base_status

        except Exception as e:
            self._record_error("StatusError", str(e))
            return {"error": str(e)}


ArtisanPlugin = LiveBroadcastPlugin

