import asyncio
import json
import logging
import time
import weakref
from typing import Optional, Callable, List, Dict, Any
from threading import Thread, Lock
from contextlib import asynccontextmanager

try:
    import websockets

    WEBSOCKETS_AVAILABLE = True
except ImportError:
    websockets = None
    WEBSOCKETS_AVAILABLE = False

# PyQt imports
try:
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer
except ImportError:
    from PyQt5.QtCore import QObject, pyqtSignal, QTimer

_log = logging.getLogger(__name__)


class WebSocketBroadcaster(QObject):
    """Production-ready WebSocket client for broadcasting roast data"""

    # PyQt signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)
    message_received = pyqtSignal(dict)

    def __init__(
        self,
        host: str = "localhost",
        port: int = 3000,
        path: str = "/ws/roast",
        reconnect_interval: float = 5.0,
        max_reconnect_attempts: int = 10,
        connection_timeout: float = 10.0,
        ping_interval: float = 30.0,
    ):
        super().__init__()

        # Validate parameters
        if not isinstance(host, str) or not host.strip():
            raise ValueError("Host must be a non-empty string")
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise ValueError("Port must be an integer between 1 and 65535")
        if not isinstance(path, str):
            raise ValueError("Path must be a string")
        if reconnect_interval < 0.1:
            raise ValueError("Reconnect interval must be at least 0.1 seconds")
        if max_reconnect_attempts < 0:
            raise ValueError("Max reconnect attempts must be non-negative")

        self.host = host.strip()
        self.port = port
        self.path = path if path.startswith("/") else f"/{path}"
        self.url = f"ws://{self.host}:{self.port}{self.path}"

        # Connection settings
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.connection_timeout = connection_timeout
        self.ping_interval = ping_interval
        self.reconnect_attempts = 0

        # Connection state
        self.websocket: Optional["websockets.WebSocketClientProtocol"] = None
        self._is_connected = False
        self.is_running = False
        self._connection_start_time: Optional[float] = None

        # Threading and async
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[Thread] = None
        self._shutdown_event: Optional[asyncio.Event] = None
        self._ping_task: Optional[asyncio.Task] = None

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
        self._signal_timer.start(50)  # Check every 50ms for better responsiveness

        # Statistics
        self._stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "connection_attempts": 0,
            "last_connection_time": None,
            "total_uptime": 0.0,
        }

        _log.debug(f"WebSocketBroadcaster initialized for {self.url}")

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

    def start(self) -> None:
        """Start the WebSocket client"""
        if self.is_running:
            _log.warning("WebSocket broadcaster is already running")
            return

        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets library is required for live broadcasting. "
                "Install with: pip install websockets"
            )

        with self._lock:
            self.is_running = True
            self.reconnect_attempts = 0
            self._stats["connection_attempts"] += 1

        self._thread = Thread(target=self._run_loop, daemon=True, name="WebSocketBroadcaster")
        self._thread.start()

        _log.info(f"Started WebSocket broadcaster to {self.url}")

    def stop(self) -> None:
        """Stop the WebSocket client gracefully"""
        if not self.is_running:
            return

        _log.info("Requesting WebSocket broadcaster to stop...")

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
                _log.warning("WebSocket thread did not stop within timeout")

        # Clean up
        self._is_connected = False
        self.websocket = None
        self._connection_start_time = None

        # Update stats
        if self._connection_start_time:
            self._stats["total_uptime"] += time.time() - self._connection_start_time

        _log.info("Stopped WebSocket broadcaster")

    def broadcast(self, message: str) -> bool:
        """Broadcast a message to connected clients. Returns True if sent successfully."""
        if not isinstance(message, str):
            _log.error("Message must be a string")
            return False

        if not self._is_connected or not self.websocket or not self._loop:
            _log.debug("Cannot broadcast: not connected")
            return False

        try:
            # Validate JSON if it looks like JSON
            if message.strip().startswith("{"):
                json.loads(message)  # Validate JSON format

            asyncio.run_coroutine_threadsafe(self._send_message(message), self._loop)
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
        return self._is_connected and self.websocket is not None

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
            _log.error(f"WebSocket loop error: {e}")
            self._queue_signal("error", f"Event loop error: {e}")
        finally:
            _log.info("Closing WebSocket event loop")
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

    async def _connect_and_run(self) -> None:
        """Connect to WebSocket server and handle messages"""
        while self.is_running:
            try:
                # Connection timeout
                connect_task = websockets.connect(
                    self.url, ping_interval=self.ping_interval, ping_timeout=10.0, close_timeout=5.0
                )

                async with asyncio.timeout(self.connection_timeout):
                    async with connect_task as websocket:
                        await self._handle_connection(websocket)

            except asyncio.TimeoutError:
                _log.warning(f"Connection timeout to {self.url}")
                self._handle_connection_error("Connection timeout")
            except (
                websockets.exceptions.ConnectionClosed,
                websockets.exceptions.InvalidURI,
                asyncio.CancelledError,
            ):
                _log.info("Connection closed or cancelled")
                self._handle_connection_error("Connection closed")
            except ConnectionRefusedError:
                _log.warning(f"Connection refused to {self.url}")
                self._handle_connection_error("Connection refused")
            except Exception as e:
                _log.error(f"Unexpected connection error: {e}")
                self._handle_connection_error(f"Connection error: {e}")

            # Wait before reconnecting
            if self.is_running:
                await asyncio.sleep(self.reconnect_interval)

    async def _handle_connection(self, websocket: "websockets.WebSocketClientProtocol") -> None:
        """Handle an active WebSocket connection"""
        self.websocket = websocket
        self._is_connected = True
        self._connection_start_time = time.time()
        self.reconnect_attempts = 0

        # Emit connection signal
        self._queue_signal("connected")

        # Call connection handlers
        for handler in self._connection_handlers:
            try:
                handler()
            except Exception as e:
                _log.error(f"Connection handler error: {e}")

        _log.info(f"Connected to WebSocket server at {self.url}")

        # Send identification
        try:
            await websocket.send(json.dumps({"type": "artisan_client_identification"}))
            _log.debug("Sent identification to server")
        except Exception as e:
            _log.error(f"Failed to send identification: {e}")

        # Start ping task
        self._ping_task = asyncio.create_task(self._ping_loop())

        # Handle messages and shutdown
        consumer_task = asyncio.create_task(self._consumer_handler(websocket))
        shutdown_task = asyncio.create_task(self._shutdown_event.wait())

        try:
            done, pending = await asyncio.wait(
                {consumer_task, shutdown_task}, return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

        except asyncio.CancelledError:
            _log.info("Connection tasks cancelled")
        finally:
            if self._ping_task and not self._ping_task.done():
                self._ping_task.cancel()

    def _handle_connection_error(self, error_msg: str) -> None:
        """Handle connection errors and update state"""
        self._is_connected = False
        self.websocket = None

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

    async def _ping_loop(self) -> None:
        """Send periodic ping messages to keep connection alive"""
        try:
            while self._is_connected and not self._shutdown_event.is_set():
                await asyncio.sleep(self.ping_interval)
                if self._is_connected and self.websocket:
                    try:
                        await self.websocket.ping()
                        _log.debug("Sent ping")
                    except Exception as e:
                        _log.warning(f"Ping failed: {e}")
                        break
        except asyncio.CancelledError:
            _log.debug("Ping loop cancelled")

    async def _send_message(self, message: str) -> None:
        """Send a message to the WebSocket server"""
        if not self.websocket or not self._is_connected:
            return

        try:
            await self.websocket.send(message)
            _log.debug(f"Sent message: {message[:100]}...")
        except websockets.exceptions.ConnectionClosed:
            _log.warning("Connection closed while sending message")
            self._is_connected = False
        except Exception as e:
            _log.error(f"Failed to send message: {e}")
            self._is_connected = False
            self._queue_signal("error", f"Send error: {e}")

    async def _consumer_handler(self, websocket: "websockets.WebSocketClientProtocol") -> None:
        """Handle incoming messages"""
        try:
            async for message in websocket:
                await self._handle_message(message)
        except websockets.exceptions.ConnectionClosed:
            _log.info("Connection closed by server")
        except asyncio.CancelledError:
            _log.info("Consumer task cancelled")
        finally:
            if self._is_connected:
                self._is_connected = False
                self._queue_signal("disconnected")

    async def _handle_message(self, message: str) -> None:
        """Handle incoming messages from the server"""
        try:
            data = json.loads(message)
            _log.debug(f"Received message: {data}")

            with self._lock:
                self._stats["messages_received"] += 1

            # Emit message signal
            self._queue_signal("message", data)

            # Call message callbacks
            for callback in self._message_callbacks:
                try:
                    callback(data)
                except Exception as e:
                    _log.error(f"Message callback error: {e}")

            # Handle ping/pong
            if data.get("type") == "ping":
                await self._send_message(json.dumps({"type": "pong"}))

        except json.JSONDecodeError:
            _log.warning(f"Received non-JSON message: {message[:100]}...")
        except Exception as e:
            _log.error(f"Error handling message: {e}")


# Check if websockets is available and log a warning if not
if not WEBSOCKETS_AVAILABLE:
    _log.warning(
        "websockets library not found. Live broadcasting will not be available. "
        "Install with: pip install websockets"
    )
