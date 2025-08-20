import asyncio
import json
import logging
import time
import weakref
from typing import Optional, Callable, List, Dict, Any
from threading import Thread, Lock
from contextlib import asynccontextmanager

try:
    import socketio

    SOCKETIO_AVAILABLE = True
except ImportError:
    socketio = None
    SOCKETIO_AVAILABLE = False

# PyQt imports
try:
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer
except ImportError:
    from PyQt5.QtCore import QObject, pyqtSignal, QTimer

_log = logging.getLogger(__name__)


class SocketIOBroadcaster(QObject):
    """Socket.IO client for broadcasting roast data"""

    # PyQt signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)
    message_received = pyqtSignal(dict)
    reconnecting = pyqtSignal()
    reconnected = pyqtSignal()

    def __init__(
        self,
        host: str = "localhost",
        port: int = 3000,
        path: str = "/socket.io/",
        secure: bool = False,
        auth_token: Optional[str] = None,
        reconnect_interval: float = 5.0,
        max_reconnect_attempts: int = 10,
        connection_timeout: float = 10.0,
        ping_interval: float = 30.0,
        connection_refresh_interval: float = 3600.0,  # 1 hour refresh
    ):
        super().__init__()

        # Validate parameters
        if not isinstance(host, str) or not host.strip():
            raise ValueError("Host must be a non-empty string")
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise ValueError("Port must be an integer between 1 and 65535")

        self.host = host.strip()
        self.port = port
        self.secure = secure
        self.path = path if path.startswith("/") else f"/{path}"
        self.auth_token = auth_token

        # Build URL with proper protocol
        protocol = "wss" if secure else "ws"
        self.url = f"{protocol}://{self.host}:{self.port}{self.path}"

        # Connection settings
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.connection_timeout = connection_timeout
        self.ping_interval = ping_interval
        self.connection_refresh_interval = connection_refresh_interval
        self.reconnect_attempts = 0

        # Connection state
        self.sio: Optional[socketio.AsyncClient] = None
        self._is_connected = False
        self.is_running = False
        self._connection_start_time: Optional[float] = None
        self._last_connection_refresh = 0

        # Threading and async
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[Thread] = None
        self._shutdown_event: Optional[asyncio.Event] = None
        self._refresh_timer: Optional[asyncio.Task] = None

        # Thread safety
        self._lock = Lock()
        self._pending_signals: List[tuple] = []

        # Event handlers
        self._connection_handlers: List[Callable[[], None]] = []
        self._disconnection_handlers: List[Callable[[], None]] = []
        self._message_callbacks: List[Callable[[Dict[str, Any]], None]] = []

        # Thread-safe signal emission
        self._signal_timer = QTimer()
        self._signal_timer.timeout.connect(self._emit_pending_signals)
        self._signal_timer.start(50)  # Check every 50ms

        # Statistics and monitoring
        self._stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "connection_attempts": 0,
            "reconnection_attempts": 0,
            "last_connection_time": None,
            "total_uptime": 0.0,
            "connection_refreshes": 0,
        }

        _log.debug(f"SocketIOBroadcaster initialized for {self.url}")

    def add_connection_handler(self, handler: Callable[[], None]) -> None:
        """Add handler for connection events"""
        if not callable(handler):
            raise ValueError("Handler must be callable")
        self._connection_handlers.append(handler)

    def add_disconnection_handler(self, handler: Callable[[], None]) -> None:
        """Add handler for disconnection events"""
        if not callable(handler):
            raise ValueError("Handler must be callable")
        self._disconnection_handlers.append(handler)

    def add_message_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Add callback for incoming messages"""
        if not callable(callback):
            raise ValueError("Callback must be callable")
        self._message_callbacks.append(callback)

    def get_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        with self._lock:
            stats = self._stats.copy()
            if self._connection_start_time:
                stats["current_uptime"] = time.time() - self._connection_start_time
            return stats

    def start(self) -> bool:
        """Start the Socket.IO client"""
        if self.is_running:
            _log.warning("Socket.IO broadcaster is already running")
            return True

        if not SOCKETIO_AVAILABLE:
            _log.error("python-socketio library is required for live broadcasting")
            return False

        try:
            with self._lock:
                self.is_running = True
                self.reconnect_attempts = 0
                self._stats["connection_attempts"] += 1

            self._thread = Thread(target=self._run_loop, daemon=True, name="SocketIOBroadcaster")
            self._thread.start()

            _log.info(f"Started Socket.IO broadcaster to {self.url}")
            return True

        except Exception as e:
            _log.error(f"Failed to start Socket.IO broadcaster: {e}")
            with self._lock:
                self.is_running = False
            return False

    def stop(self) -> bool:
        """Stop the Socket.IO client gracefully"""
        if not self.is_running:
            return True

        try:
            _log.info("Requesting Socket.IO broadcaster to stop...")

            with self._lock:
                self.is_running = False

            # Signal shutdown
            if self._loop and self._loop.is_running() and self._shutdown_event:
                try:
                    self._loop.call_soon_threadsafe(self._shutdown_event.set)
                except RuntimeError:
                    _log.warning("Event loop not running during shutdown")

            # Wait for thread to finish
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=10)
                if self._thread.is_alive():
                    _log.warning("Socket.IO thread did not stop within timeout")

            # Clean up
            self._is_connected = False
            self.sio = None
            self._connection_start_time = None

            # Update stats
            if self._connection_start_time:
                self._stats["total_uptime"] += time.time() - self._connection_start_time

            _log.info("Stopped Socket.IO broadcaster")
            return True

        except Exception as e:
            _log.error(f"Error stopping Socket.IO broadcaster: {e}")
            return False

    async def _connect_and_run(self) -> None:
        """Connect to Socket.IO server and handle messages"""
        while self.is_running:
            try:
                # Create Socket.IO client with version-compatible configuration
                client_kwargs = {
                    "logger": True,
                    "engineio_logger": True,
                    "reconnection": True,
                    "reconnection_attempts": self.max_reconnect_attempts,
                    "reconnection_delay": self.reconnect_interval,
                    "reconnection_delay_max": 30.0,
                }

                self.sio = socketio.AsyncClient(**client_kwargs)

                # Setup event handlers
                self._setup_socketio_handlers()

                # Connect with authentication if token provided
                connect_kwargs = {"wait_timeout": self.connection_timeout}

                if self.auth_token:
                    connect_kwargs["auth"] = {"token": self.auth_token}

                await self.sio.connect(self.url, **connect_kwargs)

                # Start connection refresh timer
                self._refresh_timer = asyncio.create_task(self._connection_refresh_loop())

                # Wait for shutdown or disconnection
                await self._shutdown_event.wait()

            except Exception as e:
                _log.error(f"Socket.IO connection error: {e}")
                self._handle_connection_error(f"Connection error: {e}")

            # Wait before reconnecting
            if self.is_running:
                await asyncio.sleep(self.reconnect_interval)

    def broadcast(self, message: str) -> bool:
        """Broadcast a message to connected clients. Returns True if sent successfully."""
        if not isinstance(message, str):
            _log.error("Message must be a string")
            return False

        if not self._is_connected or not self.sio or not self._loop:
            _log.debug("Cannot broadcast: not connected")
            return False

        try:
            # Validate JSON if it looks like JSON
            if message.strip().startswith("{"):
                data = json.loads(message)  # Validate JSON format
                event_type = data.get("type", "roast_data")

                # Use Socket.IO emit with acknowledgment
                asyncio.run_coroutine_threadsafe(self._emit_with_ack(event_type, data), self._loop)
            else:
                # Raw message
                asyncio.run_coroutine_threadsafe(
                    self._emit_with_ack("message", {"data": message}), self._loop
                )

            with self._lock:
                self._stats["messages_sent"] += 1
            return True

        except json.JSONDecodeError:
            _log.error("Invalid JSON message")
            return False
        except Exception as e:
            _log.error(f"Failed to queue message for broadcast: {e}")
            return False

    def is_connected(self) -> bool:
        """Check if connected to server"""
        return self._is_connected and self.sio is not None

    def _emit_pending_signals(self) -> None:
        """Emit pending signals from the main thread"""
        try:
            with self._lock:
                signals_to_emit = self._pending_signals.copy()
                self._pending_signals.clear()

            for signal_type, *args in signals_to_emit:
                try:
                    if signal_type == "connected":
                        self.connected.emit()
                    elif signal_type == "disconnected":
                        self.disconnected.emit()
                    elif signal_type == "error":
                        self.error.emit(args[0])
                    elif signal_type == "message":
                        self.message_received.emit(args[0])
                    elif signal_type == "reconnecting":
                        self.reconnecting.emit()
                    elif signal_type == "reconnected":
                        self.reconnected.emit()
                except Exception as e:
                    _log.error(f"Error emitting {signal_type} signal: {e}")
        except Exception as e:
            _log.error(f"Error in signal emission: {e}")

    def _queue_signal(self, signal_type: str, *args) -> None:
        """Queue a signal to be emitted from the main thread"""
        with self._lock:
            self._pending_signals.append((signal_type, *args))

    def _run_loop(self) -> None:
        """Run the asyncio event loop in a separate thread"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        self._shutdown_event = asyncio.Event()

        try:
            self._loop.run_until_complete(self._connect_and_run())
        except Exception as e:
            _log.error(f"Socket.IO loop error: {e}")
            self._queue_signal("error", f"Event loop error: {e}")
        finally:
            _log.info("Closing Socket.IO event loop")
            try:
                # Cancel all pending tasks
                tasks = asyncio.all_tasks(loop=self._loop)
                for task in tasks:
                    task.cancel()

                if tasks:

                    async def gather_tasks():
                        await asyncio.gather(*tasks, return_exceptions=True)

                    if self._loop.is_running():
                        self._loop.run_until_complete(gather_tasks())

                self._loop.close()
            except Exception as e:
                _log.error(f"Error during loop cleanup: {e}")

    def _setup_socketio_handlers(self) -> None:
        """Setup Socket.IO event handlers"""
        if not self.sio:
            return

        @self.sio.event
        async def connect(): # noqa
            """Handle successful connection"""
            self._is_connected = True
            self._connection_start_time = time.time()
            self.reconnect_attempts = 0
            self._stats["last_connection_time"] = time.time()

            # Emit connection signal
            self._queue_signal("connected")

            # Call connection handlers
            for handler in self._connection_handlers:
                try:
                    handler()
                except Exception as e:
                    _log.error(f"Connection handler error: {e}")

            _log.info(f"Connected to Socket.IO server at {self.url}")

            # Send identification
            try:
                await self.sio.emit(
                    "artisan_client_identification",
                    {
                        "client_type": "artisan_plugin",
                        "version": "2.0.0",
                        "capabilities": ["roast_data", "monitoring_data", "roast_events"],
                    },
                )
                _log.debug("Sent identification to server")
            except Exception as e:
                _log.error(f"Failed to send identification: {e}")

        @self.sio.event
        async def disconnect(): # noqa
            """Handle disconnection"""
            self._is_connected = False
            if self._connection_start_time:
                self._stats["total_uptime"] += time.time() - self._connection_start_time
                self._connection_start_time = None

            # Emit disconnection signal
            self._queue_signal("disconnected")

            # Call disconnection handlers
            for handler in self._disconnection_handlers:
                try:
                    handler()
                except Exception as e:
                    _log.error(f"Disconnection handler error: {e}")

            _log.info("Disconnected from Socket.IO server")

        @self.sio.event
        async def connect_error(data): 
            """Handle connection errors"""
            _log.error(f"Socket.IO connection error: {data}")
            self._handle_connection_error(f"Connection error: {data}")

        @self.sio.event
        async def reconnect(attempt_number):
            """Handle reconnection"""
            _log.info(f"Reconnecting to Socket.IO server (attempt {attempt_number})")
            self._queue_signal("reconnecting")
            self.reconnect_attempts += 1
            self._stats["reconnection_attempts"] += 1

        @self.sio.event
        async def reconnect_attempt(attempt_number):
            """Handle reconnection attempts"""
            _log.debug(f"Reconnection attempt {attempt_number}")

        @self.sio.event
        async def reconnect_failed():
            """Handle failed reconnection"""
            _log.error("Failed to reconnect to Socket.IO server")
            self._queue_signal("error", "Reconnection failed")

        # Handle custom events
        @self.sio.on("*")
        async def catch_all(event, data):
            """Handle all other events"""
            await self._handle_socketio_message(event, data)

    async def _handle_socketio_message(self, event: str, data: Any) -> None:
        """Handle incoming Socket.IO messages"""
        try:
            message_data = {"type": event, "data": data, "timestamp": time.time()}

            _log.debug(f"Received Socket.IO event: {event} with data: {data}")

            with self._lock:
                self._stats["messages_received"] += 1

            # Emit message signal
            self._queue_signal("message", message_data)

            # Call message callbacks
            for callback in self._message_callbacks:
                try:
                    callback(message_data)
                except Exception as e:
                    _log.error(f"Message callback error: {e}")

        except Exception as e:
            _log.error(f"Error handling Socket.IO message: {e}")

    async def _emit_with_ack(self, event: str, data: Any) -> None:
        """Emit Socket.IO event with acknowledgment"""
        if not self.sio or not self._is_connected:
            return

        try:
            # Use emit with acknowledgment for reliability
            await self.sio.emit(event, data, callback=self._ack_callback)
            _log.debug(f"Emitted Socket.IO event: {event}")
        except Exception as e:
            _log.error(f"Failed to emit Socket.IO event {event}: {e}")
            self._queue_signal("error", f"Emit error: {e}")

    def _ack_callback(self, *args):
        """Handle Socket.IO acknowledgment"""
        _log.debug(f"Socket.IO acknowledgment received: {args}")

    async def _connection_refresh_loop(self) -> None:
        """Periodically refresh connections for long-lived sessions"""
        try:
            while self._is_connected and not self._shutdown_event.is_set():
                await asyncio.sleep(self.connection_refresh_interval)

                if self._is_connected and self.sio:
                    _log.info("Refreshing Socket.IO connection...")

                    try:
                        # Disconnect and reconnect to refresh
                        await self.sio.disconnect()
                        await asyncio.sleep(1)  # Brief pause
                        await self.sio.connect(self.url)

                        self._stats["connection_refreshes"] += 1
                        self._last_connection_refresh = time.time()
                        _log.info("Socket.IO connection refreshed successfully")

                    except Exception as e:
                        _log.error(f"Failed to refresh Socket.IO connection: {e}")
                        self._queue_signal("error", f"Connection refresh failed: {e}")

        except asyncio.CancelledError:
            _log.debug("Connection refresh loop cancelled")

    def _handle_connection_error(self, error_msg: str) -> None:
        """Handle connection errors and update state"""
        self._is_connected = False
        self.sio = None

        if self._connection_start_time:
            self._stats["total_uptime"] += time.time() - self._connection_start_time
            self._connection_start_time = None

        self.reconnect_attempts += 1

        # Emit disconnection signal
        self._queue_signal("disconnected")

        # Call disconnection handlers
        for handler in self._disconnection_handlers:
            try:
                handler()
            except Exception as e:
                _log.error(f"Disconnection handler error: {e}")

        # Check max reconnection attempts
        if (
            self.max_reconnect_attempts > 0
            and self.reconnect_attempts >= self.max_reconnect_attempts
        ):
            _log.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached")
            self._queue_signal("error", f"Max reconnection attempts reached: {error_msg}")
            self.is_running = False
        else:
            _log.info(
                f"Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}"
            )


# Check if socketio is available and log a warning if not
if not SOCKETIO_AVAILABLE:
    _log.warning(
        "python-socketio library not found. Live broadcasting will not be available. "
        "Install with: pip install python-socketio"
    )
