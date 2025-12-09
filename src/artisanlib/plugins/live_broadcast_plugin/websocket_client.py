import asyncio
import json
import logging
import time
import weakref
import uuid
import os
import sys
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
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex
except ImportError:
    from PyQt5.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex

_log = logging.getLogger(__name__)

class SocketIOBroadcaster(QObject):
    """Socket.IO client for broadcasting roast data with proper PyQt threading"""

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
        refresh_token: Optional[str] = None,
        reconnect_interval: float = 5.0,
        max_reconnect_attempts: int = 10,
        connection_timeout: float = 10.0,
        ping_interval: float = 30.0,
        connection_refresh_interval: float = 3600.0,  # 1 hour refresh
        roaster_id: Optional[str] = None, 
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
        self.refresh_token = refresh_token

        # roaster id 
        self.roaster_id = roaster_id.strip() if roaster_id and roaster_id.strip() else self._generate_stable_client_id()
        

        # # Build URL with proper protocol
        # protocol = "https" if secure else "http"
        # self.url = f"{protocol}://{self.host}:{self.port}"
        
        # # Extract the Socket.IO path from the full path
        # self.socketio_path = self.path.strip("/")

        # Build URL with proper protocol - clean host of any existing protocol
        clean_host = self.host.replace("https://", "").replace("http://", "")
        protocol = "https" if secure else "http"
        self.url = f"{protocol}://{clean_host}:{self.port}"
        
        # Extract the Socket.IO path from the full path
        self.socketio_path = self.path.strip("/")

        
        # Connection settings
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.connection_timeout = connection_timeout
        self.ping_interval = ping_interval
        self.connection_refresh_interval = connection_refresh_interval
        self.reconnect_attempts = 0

        # Generate stable unique client identifier
        self.client_id = self._generate_stable_client_id()
        
        # Client identification data
        self.client_info = self._generate_client_info()

        # Connection state
        self.sio: Optional[socketio.AsyncClient] = None
        self._is_connected = False
        self.is_running = False
        self._connection_start_time: Optional[float] = None
        self._last_connection_refresh = 0

        # PyQt threading support
        self._worker_thread: Optional[QThread] = None
        self._mutex = QMutex()
        
        # Threading and async
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[Thread] = None
        self._shutdown_event: Optional[asyncio.Event] = None

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
            "auth_failures": 0,
        }

        _log.debug(f"SocketIOBroadcaster initialized for {self.url}")

    def _generate_stable_client_id(self) -> str:
        """Generate a stable unique client identifier"""
        try:
            pid = os.getpid()
            python_version = f"{sys.version_info.major}.{sys.version_info.minor}"

            stable_id = f"artisan_{pid}_{python_version}_{uuid.uuid4().hex[:12]}"
            return stable_id
            
        except Exception as e:
            _log.warning(f"Could not generate stable client ID: {e}")
            # Fallback to simple UUID
            return f"artisan_{uuid.uuid4().hex[:16]}"

    def _generate_client_info(self) -> Dict[str, Any]:
        """Generate client identification information"""
        try:
            return {
                "clientId": self.client_id,
                "clientType": "artisan",
                "clientVersion": "2.0.0",
                "clientBuild": "artisan-live-broadcast-plugin",
                "platform": "unknown",  
                "platformVersion": "unknown",
                "architecture": "unknown",
                "hostname": "unknown",  
                "deviceName": "artisan-client",
                "deviceModel": "unknown",
                "connectionType": "artisan_broadcast",
                "capabilities": [
                    "roast_data_broadcast",
                    "roast_event_broadcast", 
                    "monitoring_data_broadcast",
                    "custom_event_broadcast",
                    "roast_control_receive"
                ],
                "metadata": {
                    "pythonVersion": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                    "socketioVersion": getattr(socketio, '__version__', 'unknown') if socketio else 'not_available',
                    "connectionTime": time.time(),
                    "processId": os.getpid()
                }
            }
                
        except Exception as e:
            _log.warning(f"Could not generate complete client info: {e}")
            return {
                "clientId": self.client_id,
                "clientType": "artisan",
                "clientVersion": "2.0.0",
                "platform": "unknown",
                "hostname": "unknown"
            }

    def get_client_id(self) -> str:
        """Get the stable client identifier"""
        return self.client_id

    def get_client_info(self) -> Dict[str, Any]:
        """Get client identification information"""
        return self.client_info.copy()

    def update_auth_tokens(self, auth_token: str, refresh_token: str):
        """Update authentication tokens"""
        self.auth_token = auth_token
        self.refresh_token = refresh_token
        
        # If connected, might need to reconnect with new tokens
        if self.is_connected():
            _log.info("Updating auth tokens - reconnecting with new credentials")
            self.disconnect()
            # The reconnection logic will use the new tokens
            
        self.token_refreshed.emit()

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
        self._mutex.lock()
        try:
            stats = self._stats.copy()
            if self._connection_start_time:
                stats["current_uptime"] = time.time() - self._connection_start_time
            return stats
        finally:
            self._mutex.unlock()
        
    def start(self) -> bool:
        """Start the Socket.IO client using PyQt threading"""
        if self.is_running:
            _log.warning("Socket.IO broadcaster is already running")
            return True

        if not SOCKETIO_AVAILABLE:
            _log.debug("python-socketio library is required for live broadcasting")
            return False

        try:
            self._mutex.lock()
            self.is_running = True
            self.reconnect_attempts = 0
            self._stats["connection_attempts"] += 1
            self._mutex.unlock()

            _log.debug(f"Starting Socket.IO broadcaster to {self.url} with path {self.socketio_path}")
            
            # Use PyQt threading approach
            self._thread = Thread(target=self._run_loop, daemon=True, name="SocketIOBroadcaster")
            self._thread.start()

            _log.debug(f"Started Socket.IO broadcaster to {self.url}")
            return True

        except Exception as e:
            _log.debug(f"Failed to start Socket.IO broadcaster: {e}")
            self._mutex.lock()
            try:
                self.is_running = False
            finally:
                self._mutex.unlock()
            return False

    def stop(self) -> bool:
        """Stop the Socket.IO client gracefully using PyQt threading"""
        if not self.is_running:
            return True

        try:
            _log.debug("Requesting Socket.IO broadcaster to stop...")

            self._mutex.lock()
            try:
                self.is_running = False
            finally:
                self._mutex.unlock()

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
            self._mutex.lock()
            try:
                self._is_connected = False
                self.sio = None
                self._connection_start_time = None

                # Update stats
                if self._connection_start_time:
                    self._stats["total_uptime"] += time.time() - self._connection_start_time
            finally:
                self._mutex.unlock()

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
                    # Check if it's an API key (starts with 'ccr_') or OAuth token
                    if self.auth_token.startswith('ccr_'):
                        # API key authentication
                        headers = {"X-API-Key": self.auth_token}
                        connect_kwargs["auth"] = {"apiKey": self.auth_token}
                    else:
                        # OAuth JWT token authentication
                        connect_kwargs["auth"] = {"token": self.auth_token}
                        headers = {"Authorization": f"Bearer {self.auth_token}"}
                        if self.refresh_token:
                            headers["x-refresh-token"] = self.refresh_token
                    
                    connect_kwargs["headers"] = headers
                    self.sio.auth = connect_kwargs.get("auth", {})
                    
                    _log.debug(f"Connecting with authentication: {self.auth_token[:20]}...")
                    _log.debug(f"Auth parameter: {connect_kwargs['auth']}")
                    _log.debug(f"Headers: {connect_kwargs['headers']}")
                    _log.debug(f"Client auth: {self.sio.auth}")

                _log.debug(f"Attempting to connect to {self.url} with path {self.socketio_path}")
                _log.debug(f"Full connection kwargs: {connect_kwargs}")
                
                await self.sio.connect(self.url, **connect_kwargs)

                _log.debug("Socket.IO connection established successfully")

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

                # Add client ID to message for server-side filtering
                if isinstance(data, dict):
                    data["senderClientId"] = self.client_id
                    data["roaster_id"] = self.roaster_id 


                asyncio.run_coroutine_threadsafe(self._emit_with_ack(event_type, data), self._loop)
            else:
                message_data = {
                    "data": message,
                    "senderClientId": self.client_id,
                    "roaster_id": self.roaster_id
                }
                asyncio.run_coroutine_threadsafe(
                    self._emit_with_ack("message", message_data), self._loop
                )

            self._mutex.lock()
            try:
                self._stats["messages_sent"] += 1
            finally:
                self._mutex.unlock()
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
            self._mutex.lock()
            try:
                signals_to_emit = self._pending_signals.copy()
                self._pending_signals.clear()
            finally:
                self._mutex.unlock()

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
        self._mutex.lock()
        try:
            self._pending_signals.append((signal_type, *args))
        finally:
            self._mutex.unlock()

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
                self._mutex.lock()
                try:
                    self._is_connected = True
                    self._connection_start_time = time.time()
                    self.reconnect_attempts = 0
                    self._stats["successful_connections"] += 1
                finally:
                    self._mutex.unlock()
                
                # Emit connection signal
                self._queue_signal("connected")
                
                # Call connection handlers
                for handler in self._connection_handlers:
                    try:
                        handler()
                    except Exception as e:
                        _log.debug(f"Connection handler error: {e}")

                # Send client identification
                await self._send_client_identification()

                _log.debug("Socket.IO connection fully established")

            @self.sio.event
            async def disconnect():
                _log.debug("Socket.IO disconnected")
                self._mutex.lock()
                try:
                    self._is_connected = False
                    if self._connection_start_time:
                        self._stats["total_uptime"] += time.time() - self._connection_start_time
                        self._connection_start_time = None
                finally:
                    self._mutex.unlock()
                
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
                        self._mutex.lock()
                        try:
                            self._stats["auth_failures"] += 1
                        finally:
                            self._mutex.unlock()
                        self._queue_signal("auth_failed", f"Authentication failed: {error_msg}")
                    else:
                        self._queue_signal("error", f"Connection error: {error_msg}")
                else:
                    self._queue_signal("error", f"Connection error: {data}")

            # Handle connection established response
            @self.sio.event
            async def connection_established(data):
                _log.debug(f"Received connection_established: {data}")
                if isinstance(data, dict):
                    server_client_id = data.get("clientId")
                    if server_client_id:
                        _log.info(f"Server assigned client ID: {server_client_id}")
                        # Update our client ID if server assigned a different one
                        if server_client_id != self.client_id:
                            _log.info(f"Updating client ID from {self.client_id} to {server_client_id}")
                            self.client_id = server_client_id
                            self.client_info["clientId"] = server_client_id

            # Handle artisan identification response
            @self.sio.event
            async def artisan_identified(data):
                _log.debug(f"Received artisan_identified: {data}")
                if isinstance(data, dict):
                    _log.info(f"Artisan client successfully identified: {data.get('message', 'OK')}")

            # JWT token refresh response
            @self.sio.event
            async def tokens_refreshed(data):
                _log.debug("Received JWT token refresh response")
                try:
                    if isinstance(data, dict) and "accessToken" in data:
                        new_token = data["accessToken"]
                        new_refresh_token = data.get("refreshToken")
                        self.update_auth_tokens(new_token, new_refresh_token)
                        _log.debug("JWT tokens refreshed successfully")
                        self._queue_signal("token_refreshed")
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

    async def _send_client_identification(self) -> None:
        """Send client identification to server"""
        try:
            if not self.sio or not self._is_connected:
                _log.warning("Cannot send client identification: not connected")
                return

            identification_data = {
                "clientId": self.client_id,
                "clientInfo": self.client_info,
                "timestamp": time.time(),
                "capabilities": self.client_info.get("capabilities", []),
                "metadata": self.client_info.get("metadata", {})
            }

            _log.debug(f"Sending client identification: {identification_data}")
            await self.sio.emit("artisan_client_identification", identification_data)
            _log.info(f"Client identification sent with ID: {self.client_id}")

        except Exception as e:
            _log.error(f"Failed to send client identification: {e}")

    # async def _handle_socketio_message(self, event: str, data: Any) -> None:
    #     """Handle incoming Socket.IO messages"""
    #     try:
    #         # Filter out data messages for Artisan clients - they should only receive control messages
    #         if event in ["monitoring_data", "roast_event", "roast_data"]:
    #             _log.debug(f"Ignoring {event} message - Artisan client should not receive data messages")
    #             return
            
    #         message_data = {"type": event, "data": data, "timestamp": time.time()}

    #         _log.debug(f"Received Socket.IO event: {event} with data: {data}")

    #         self._mutex.lock()
    #         try:
    #             self._stats["messages_received"] += 1
    #         finally:
    #             self._mutex.unlock()

    #         # Emit message signal
    #         self._queue_signal("message", message_data)

    #         # Call message callbacks
    #         for callback in self._message_callbacks:
    #             try:
    #                 callback(message_data)
    #             except Exception as e:
    #                 _log.debug(f"Message callback error: {e}")

    #     except Exception as e:
    #         _log.debug(f"Error handling Socket.IO message: {e}")

    async def _handle_socketio_message(self, event: str, data: Any) -> None:
        """Handle incoming Socket.IO messages with filtering for Artisan clients"""
        try:
            # Artisan clients should only receive roast_control messages
            if event in ['monitoring_data', 'roast_data', 'roast_event']:
                self.logger.debug(f"Ignoring {event} message - Artisan client should not receive data messages")
                return
                
            # Only process roast_control messages
            if event == 'roast_control':
                self.logger.debug(f"Processing roast_control message: {data}")
                # Process the control message
                if self.message_callbacks:
                    for callback in self.message_callbacks:
                        try:
                            callback(data)
                        except Exception as e:
                            self.logger.error(f"Error in message callback: {e}")
            else:
                self.logger.debug(f"Ignoring unknown event: {event}")
                
        except Exception as e:
            self.logger.error(f"Error handling Socket.IO message: {e}")

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

    def _handle_connection_error(self, error_msg: str) -> None:
        """Handle connection errors and update state"""
        self._mutex.lock()
        try:
            self._is_connected = False
            self.sio = None

            if self._connection_start_time:
                self._stats["total_uptime"] += time.time() - self._connection_start_time
                self._connection_start_time = None

            self.reconnect_attempts += 1
        finally:
            self._mutex.unlock()

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
            self._mutex.lock()
            try:
                self.is_running = False
            finally:
                self._mutex.unlock()
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