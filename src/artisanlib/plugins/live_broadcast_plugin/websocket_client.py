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
    auth_failed = pyqtSignal(str)
    token_refreshed = pyqtSignal()

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

        # # Build URL with proper protocol
        # protocol = "wss" if secure else "ws"
        # self.url = f"{protocol}://{self.host}:{self.port}{self.path}"

        protocol = "https" if secure else "http"
        self.url = f"{protocol}://{self.host}:{self.port}"
        
        # Extract the Socket.IO path from the full path
        self.socketio_path = self.path.strip("/")


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

        # JWT token management
        self._token_expiry: Optional[float] = None
        self._token_refresh_attempts = 0
        self._max_token_refresh_attempts = 3

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
            "bytes_sent": 0,
            "bytes_received": 0,
            "connection_attempts": 0,
            "successful_connections": 0,
            "failed_connections": 0,
            "total_uptime": 0.0,
            "connection_refreshes": 0,
            "token_refreshes": 0,
            "auth_failures": 0,
        }

        _log.debug(f"SocketIOBroadcaster initialized for {self.url}")

    def update_auth_token(self, new_token: str) -> None:
        """Update the JWT authentication token"""
        try:
            old_token = self.auth_token
            self.auth_token = new_token
            self._token_refresh_attempts = 0  # Reset refresh attempts
            
            _log.debug("JWT token updated successfully")
            
            # If connected, try to refresh the connection with new token
            if self._is_connected and self.sio:
                asyncio.run_coroutine_threadsafe(self._refresh_connection_with_new_token(), self._loop)
                
        except Exception as e:
            _log.debug(f"Error updating auth token: {e}")

    async def _refresh_connection_with_new_token(self) -> None:
        """Refresh connection with new JWT token"""
        try:
            if not self.sio or not self._is_connected:
                return

            _log.debug("Refreshing connection with new JWT token...")

            # Disconnect and reconnect with new token
            await self.sio.disconnect()
            await asyncio.sleep(1)  

            # Reconnect with new token
            connect_kwargs = {
                "wait_timeout": self.connection_timeout,
                "socketio_path": self.socketio_path  
            }
            if self.auth_token:
                connect_kwargs["auth"] = {"token": self.auth_token}
                connect_kwargs["headers"] = {"Authorization": f"Bearer {self.auth_token}"}

            await self.sio.connect(self.url, **connect_kwargs)
            
            self._stats["token_refreshes"] += 1
            self._queue_signal("token_refreshed")
            _log.debug("Connection refreshed with new JWT token successfully")

        except Exception as e:
            _log.debug(f"Failed to refresh connection with new token: {e}")
            self._queue_signal("error", f"Token refresh failed: {e}")

    async def _connect_with_auth(self) -> None:
        """Connect to Socket.IO server with JWT authentication"""
        try:
            _log.debug(f"Starting connection to {self.url} with path {self.socketio_path}")
            
            # Validate JWT token if provided
            if self.auth_token:
                _log.debug("Validating JWT token...")
                if not self._validate_jwt_token():
                    raise ValueError("Invalid or expired JWT token")
                _log.debug("JWT token validation passed")

            # Setup client with authentication
            client_kwargs = {
                "logger": _log,
                "engineio_logger": _log if hasattr(self, 'config') and getattr(self.config, "enable_debug_logging", False) else None,
                "ping_timeout": self.connection_timeout,
                "ping_interval": self.ping_interval,
                "reconnection": True,
                "reconnection_attempts": self.max_reconnect_attempts,
                "reconnection_delay": self.reconnect_interval,
                "reconnection_delay_max": 30.0,
            }

            _log.debug(f"Creating Socket.IO client with kwargs: {client_kwargs}")
            self.sio = socketio.AsyncClient(**client_kwargs)

            _log.debug("Setting up Socket.IO event handlers...")
            self._setup_socketio_handlers()

            # Connect with authentication
            connect_kwargs = {
                "wait_timeout": self.connection_timeout,
                "socketio_path": self.socketio_path
            }

            if self.auth_token:
                connect_kwargs["auth"] = {"token": self.auth_token}
                connect_kwargs["headers"] = {"Authorization": f"Bearer {self.auth_token}"}
                
                _log.debug(f"Connecting with JWT authentication: {self.auth_token[:20]}...")
                _log.debug(f"Auth parameter: {connect_kwargs['auth']}")
                _log.debug(f"Headers: {connect_kwargs['headers']}")
            else:
                _log.debug("Connecting without authentication...")

            _log.debug(f"Connection kwargs: {connect_kwargs}")
            _log.debug(f"Attempting connection to {self.url}")

            await self.sio.connect(self.url, **connect_kwargs)

            _log.debug("Socket.IO connect() call completed successfully")

            # Start connection refresh timer
            self._refresh_timer = asyncio.create_task(self._connection_refresh_loop())

            # Wait for shutdown or disconnection
            await self._shutdown_event.wait()

        except Exception as e:
            _log.debug(f"Socket.IO connection error: {e}")
            _log.debug(f"Error type: {type(e)}")
            _log.debug(f"Error details: {str(e)}")
            
            # Check if it's an authentication error
            if "unauthorized" in str(e).lower() or "401" in str(e):
                self._stats["auth_failures"] += 1
                self._queue_signal("auth_failed", f"Authentication failed: {e}")
            else:
                self._handle_connection_error(f"Connection error: {e}")

            # Wait before reconnecting
            if self.is_running:
                await asyncio.sleep(self.reconnect_interval)
    
    def _validate_jwt_token(self) -> bool:
        """Enhanced JWT token validation with issuer/audience support"""
        try:
            if not self.auth_token or not isinstance(self.auth_token, str):
                return False

            # Check if token has JWT structure
            parts = self.auth_token.split('.')
            if len(parts) != 3:
                return False

            # length validation
            if len(self.auth_token) < 50:
                return False

            # Check for expiration and claims
            try:
                import base64
                import json
                
                # Decode payload
                payload = parts[1]
                # Add padding
                payload += '=' * (4 - len(payload) % 4)
                decoded = base64.b64decode(payload)
                payload_data = json.loads(decoded.decode('utf-8'))
                
                # Check expiration
                if 'exp' in payload_data:
                    exp_time = payload_data['exp']
                    current_time = time.time()
                    
                    if current_time >= exp_time:
                        _log.warning("JWT token has expired")
                        return False
                    
                    # Set token expiry
                    self._token_expiry = exp_time
                
                # Check issuer if configured
                if hasattr(self, 'config') and hasattr(self.config, 'jwt_issuer'):
                    expected_issuer = self.config.jwt_issuer
                    if expected_issuer and payload_data.get('iss') != expected_issuer:
                        _log.warning(f"JWT issuer mismatch: expected {expected_issuer}, got {payload_data.get('iss')}")
                        return False
                
                # Check audience if configured
                if hasattr(self, 'config') and hasattr(self.config, 'jwt_audience'):
                    expected_audience = self.config.jwt_audience
                    if expected_audience:
                        token_audience = payload_data.get('aud')
                        if isinstance(token_audience, list):
                            if expected_audience not in token_audience:
                                _log.warning(f"JWT audience not in allowed list: expected {expected_audience}, got {token_audience}")
                                return False
                        elif token_audience != expected_audience:
                            _log.warning(f"JWT audience mismatch: expected {expected_audience}, got {token_audience}")
                            return False
                
                _log.debug(f"JWT token validated successfully - exp: {payload_data.get('exp')}, iss: {payload_data.get('iss')}, aud: {payload_data.get('aud')}")
                    
            except Exception as e:
                _log.debug(f"Could not decode JWT payload for validation: {e}")

            return True

        except Exception as e:
            _log.debug(f"Error validating JWT token: {e}")
            return False

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
            _log.debug("python-socketio library is required for live broadcasting")
            return False

        try:
            with self._lock:
                self.is_running = True
                self.reconnect_attempts = 0
                self._stats["connection_attempts"] += 1

            _log.debug(f"Starting Socket.IO broadcaster to {self.url} with path {self.socketio_path}")
            
            self._thread = Thread(target=self._run_loop, daemon=True, name="SocketIOBroadcaster")
            self._thread.start()

            _log.debug(f"Started Socket.IO broadcaster to {self.url}")
            return True

        except Exception as e:
            _log.debug(f"Failed to start Socket.IO broadcaster: {e}")
            with self._lock:
                self.is_running = False
            return False

    def stop(self) -> bool:
        """Stop the Socket.IO client gracefully"""
        if not self.is_running:
            return True

        try:
            _log.debug("Requesting Socket.IO broadcaster to stop...")

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

            _log.debug("Stopped Socket.IO broadcaster")
            return True

        except Exception as e:
            _log.debug(f"Error stopping Socket.IO broadcaster: {e}")
            return False

    async def _connect_and_run(self) -> None:
        """Connect to Socket.IO server and handle messages"""
        while self.is_running:
            try:
                # Create Socket.IO client
                client_kwargs = {
                    "logger": True,
                    "engineio_logger": True,
                    "reconnection": True,
                    "reconnection_attempts": self.max_reconnect_attempts,
                    "reconnection_delay": self.reconnect_interval,
                    "reconnection_delay_max": 30.0,
                }

                self.sio = socketio.AsyncClient(**client_kwargs)

                self._setup_socketio_handlers()

                connect_kwargs = {
                    "wait_timeout": self.connection_timeout,
                    "socketio_path": self.socketio_path  
                }

                if self.auth_token:
                    connect_kwargs["auth"] = {"token": self.auth_token}
                    connect_kwargs["headers"] = {"Authorization": f"Bearer {self.auth_token}"}
                    
                    self.sio.auth = {"token": self.auth_token}
                    
                    _log.debug(f"Connecting with JWT authentication: {self.auth_token[:20]}...")
                    _log.debug(f"Auth parameter: {connect_kwargs['auth']}")
                    _log.debug(f"Headers: {connect_kwargs['headers']}")
                    _log.debug(f"Client auth: {self.sio.auth}")

                _log.debug(f"Attempting to connect to {self.url} with path {self.socketio_path}")
                _log.debug(f"Full connection kwargs: {connect_kwargs}")
                
                await self.sio.connect(self.url, **connect_kwargs)

                _log.debug("Socket.IO connection established successfully")

                # Start connection refresh timer
                self._refresh_timer = asyncio.create_task(self._connection_refresh_loop())

                # Wait for shutdown or disconnection
                await self._shutdown_event.wait()

            except Exception as e:
                _log.debug(f"Socket.IO connection error: {e}")
                _log.debug(f"Error type: {type(e)}")
                _log.debug(f"Error details: {str(e)}")
                self._handle_connection_error(f"Connection error: {e}")

            # Wait before reconnecting
            if self.is_running:
                await asyncio.sleep(self.reconnect_interval)
    
    def broadcast(self, message: str) -> bool:
        """Broadcast a message to connected clients. Returns True if sent successfully."""
        if not isinstance(message, str):
            _log.debug("Message must be a string")
            return False

        if not self._is_connected or not self.sio or not self._loop:
            _log.debug("Cannot broadcast: not connected")
            return False

        try:
            # Validate JSON
            if message.strip().startswith("{"):
                data = json.loads(message)  
                event_type = data.get("type", "roast_data")

                asyncio.run_coroutine_threadsafe(self._emit_with_ack(event_type, data), self._loop)
            else:
                asyncio.run_coroutine_threadsafe(
                    self._emit_with_ack("message", {"data": message}), self._loop
                )

            with self._lock:
                self._stats["messages_sent"] += 1
            return True

        except json.JSONDecodeError:
            _log.debug("Invalid JSON message")
            return False
        except Exception as e:
            _log.debug(f"Failed to queue message for broadcast: {e}")
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
                    _log.debug(f"Error emitting {signal_type} signal: {e}")
        except Exception as e:
            _log.debug(f"Error in signal emission: {e}")

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
            _log.debug(f"Socket.IO loop error: {e}")
            self._queue_signal("error", f"Event loop error: {e}")
        finally:
            _log.debug("Closing Socket.IO event loop")
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
                _log.debug(f"Error during loop cleanup: {e}")

    def _setup_socketio_handlers(self) -> None:
        """Setup Socket.IO event handlers"""
        try:
            if not self.sio:
                _log.warning("Cannot setup handlers: Socket.IO client not initialized")
                return

            _log.debug("Setting up Socket.IO event handlers...")

            # Connection events
            @self.sio.event
            async def connect():
                _log.debug("Socket.IO connected successfully")
                self._is_connected = True
                self._connection_start_time = time.time()
                self.reconnect_attempts = 0
                self._stats["successful_connections"] += 1
                
                # Emit connection signal
                self._queue_signal("connected")
                
                # Call connection handlers
                for handler in self._connection_handlers:
                    try:
                        handler()
                    except Exception as e:
                        _log.debug(f"Connection handler error: {e}")

                _log.debug("Socket.IO connection fully established")

            @self.sio.event
            async def disconnect():
                _log.debug("Socket.IO disconnected")
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
                        _log.debug(f"Disconnection handler error: {e}")

            @self.sio.event
            async def connect_error(data):
                _log.debug(f"Socket.IO connection error: {data}")
                
                # Check for authentication errors
                if isinstance(data, dict):
                    error_msg = str(data.get("message", data))
                    if "unauthorized" in error_msg.lower() or "401" in error_msg:
                        self._stats["auth_failures"] += 1
                        self._queue_signal("auth_failed", f"Authentication failed: {error_msg}")
                    else:
                        self._queue_signal("error", f"Connection error: {error_msg}")
                else:
                    self._queue_signal("error", f"Connection error: {data}")

            # JWT token refresh response
            @self.sio.event
            async def token_refresh_response(data):
                _log.debug("Received JWT token refresh response")
                try:
                    if isinstance(data, dict) and "new_token" in data:
                        new_token = data["new_token"]
                        self.update_auth_token(new_token)
                        _log.debug("JWT token refreshed successfully")
                    else:
                        _log.warning("Invalid token refresh response format")
                        
                except Exception as e:
                    _log.debug(f"Error handling token refresh response: {e}")

            # Catch all other events
            @self.sio.event
            async def catch_all(event, data):
                _log.debug(f"Socket.IO event received: {event}")
                await self._handle_socketio_message(event, data)

            _log.debug("Socket.IO event handlers setup completed")

        except Exception as e:
            _log.debug(f"Error setting up Socket.IO handlers: {e}")

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
                    _log.debug(f"Message callback error: {e}")

        except Exception as e:
            _log.debug(f"Error handling Socket.IO message: {e}")

    async def _emit_with_ack(self, event: str, data: Any) -> None:
        """Emit Socket.IO event with acknowledgment"""
        if not self.sio or not self._is_connected:
            return

        try:
            # Use emit with acknowledgment for reliability
            await self.sio.emit(event, data, callback=self._ack_callback)
            _log.debug(f"Emitted Socket.IO event: {event}")
        except Exception as e:
            _log.debug(f"Failed to emit Socket.IO event {event}: {e}")
            self._queue_signal("error", f"Emit error: {e}")

    def _ack_callback(self, *args):
        """Handle Socket.IO acknowledgment"""
        _log.debug(f"Socket.IO acknowledgment received: {args}")

    async def _connection_refresh_loop(self) -> None:
        """Periodically refresh connections and JWT tokens for long-lived sessions"""
        try:
            while self._is_connected and not self._shutdown_event.is_set():
                await asyncio.sleep(self.connection_refresh_interval)

                if self._is_connected and self.sio:
                    _log.debug("Refreshing Socket.IO connection...")

                    try:
                        # Check if JWT token needs refresh
                        if self.auth_token and self._token_expiry:
                            current_time = time.time()
                            time_until_expiry = self._token_expiry - current_time
                            
                            # Refresh if token expires within 5 minutes
                            if time_until_expiry < 300:
                                _log.debug("JWT token expiring soon, attempting refresh...")
                                await self._attempt_token_refresh()

                        # Disconnect and reconnect to refresh connection
                        await self.sio.disconnect()
                        await asyncio.sleep(1)  # Brief pause
                        
                        # Reconnect with current token
                        connect_kwargs = {
                            "wait_timeout": self.connection_timeout,
                            "socketio_path": self.socketio_path 
                        }
                        if self.auth_token:
                            connect_kwargs["auth"] = {"token": self.auth_token}
                            connect_kwargs["headers"] = {"Authorization": f"Bearer {self.auth_token}"}

                        await self.sio.connect(self.url, **connect_kwargs)

                        self._stats["connection_refreshes"] += 1
                        self._last_connection_refresh = time.time()
                        _log.debug("Socket.IO connection refreshed successfully")

                    except Exception as e:
                        _log.debug(f"Failed to refresh Socket.IO connection: {e}")
                        self._queue_signal("error", f"Connection refresh failed: {e}")

        except asyncio.CancelledError:
            _log.debug("Connection refresh loop cancelled")


    async def _attempt_token_refresh(self) -> None:
        """Attempt to refresh the JWT token"""
        try:
            if self._token_refresh_attempts >= self._max_token_refresh_attempts:
                _log.debug("Max JWT token refresh attempts reached")
                self._queue_signal("auth_failed", "Max token refresh attempts reached")
                return

            self._token_refresh_attempts += 1
            _log.debug(f"Attempting JWT token refresh (attempt {self._token_refresh_attempts})")

            # Emit token refresh request to server
            if self.sio:
                await self.sio.emit("token_refresh_request", {
                    "current_token": self.auth_token,
                    "timestamp": time.time()
                })

            # TODO: buld out token refresh logic

        except Exception as e:
            _log.debug(f"Failed to attempt token refresh: {e}")
            self._queue_signal("error", f"Token refresh attempt failed: {e}")

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
                _log.debug(f"Disconnection handler error: {e}")

        # Check max reconnection attempts
        if (
            self.max_reconnect_attempts > 0
            and self.reconnect_attempts >= self.max_reconnect_attempts
        ):
            _log.debug(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached")
            self._queue_signal("error", f"Max reconnection attempts reached: {error_msg}")
            self.is_running = False
        else:
            _log.debug(
                f"Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}"
            )


# Check if socketio is available and log a warning if not
if not SOCKETIO_AVAILABLE:
    _log.warning(
        "python-socketio library not found. Live broadcasting will not be available. "
        "Install with: pip install python-socketio"
    )
