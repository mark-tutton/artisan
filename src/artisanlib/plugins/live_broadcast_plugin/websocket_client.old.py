import asyncio
import json
import logging
import time
from typing import Optional, Callable, List
from threading import Thread

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
    """WebSocket client for broadcasting roast data"""
    
    # PyQt signals
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, host: str = "localhost", port: int = 3000, path: str = "/ws/roast", 
                 reconnect_interval: float = 5.0, max_reconnect_attempts: int = 10):
        super().__init__()
        
        self.host = host
        self.port = port
        self.path = path
        self.url = f"ws://{host}:{port}{path}"
        
        # Connection settings
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_attempts = 0
        
        # self.websocket = None
        self.websocket: Optional['websockets.WebSocketClientProtocol'] = None
        self._is_connected = False 
        self.is_running = False
        
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[Thread] = None
        self._message_queue: List[str] = []
        self._queue_lock: asyncio.Lock()
        self._shutdown_event: Optional[asyncio.Event] = None
        
        self._connection_handlers: List[Callable[[], None]] = []
        self._disconnection_handlers: List[Callable[[], None]] = []
        
        # Thread-safe signal emission
        self._signal_timer = QTimer()
        self._signal_timer.timeout.connect(self._emit_pending_signals)
        self._signal_timer.start(100)  # Check every 100ms
        self._pending_signals = []

        # handle post messages from server
        self._message_callbacks = []
        
    def add_connection_handler(self, handler: Callable[[], None]) -> None:
        """Add handler for connection events"""
        self._connection_handlers.append(handler)
    
    def add_disconnection_handler(self, handler: Callable[[], None]) -> None:
        """Add handler for disconnection events"""
        self._disconnection_handlers.append(handler)
    
    def start(self) -> None:
        """Start the WebSocket client"""
        if self.is_running:
            return
            
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError(
                "websockets library is required for live broadcasting. "
                "Install with: pip install websockets"
            )
        
        self.is_running = True
        self.reconnect_attempts = 0
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        _log.info(f"Started WebSocket broadcaster to {self.url}")
    
    def stop(self) -> None:
        """Stop the WebSocket client"""
        if not self.is_running:
            return
        
        _log.info("Requesting WebSocket broadcaster to stop...")
        self.is_running = False
        
        # if self._loop:
        #     self._loop.call_soon_threadsafe(self._loop.stop)
        if self._loop and self._loop.is_running() and self._shutdown_event:
            self._loop.call_soon_threadsafe(self._shutdown_event.set)
        
        if self._thread:
            self._thread.join(timeout=5)
        
        # if self.websocket:
        #     asyncio.create_task(self.websocket.close())
        
        self._is_connected = False
        _log.info("Stopped WebSocket broadcaster")
    
    def broadcast(self, message: str) -> None:
        """Broadcast a message to connected clients"""
        if self._is_connected and self.websocket:
            asyncio.run_coroutine_threadsafe(
                self._send_message(message), 
                self._loop
            )
    
    def is_connected(self) -> bool:
        """Check if connected to server"""
        return self._is_connected
    
    # def _emit_pending_signals(self) -> None:
    #     """Emit pending signals from the main thread"""
    #     while self._pending_signals:
    #         signal_type, *args = self._pending_signals.pop(0)
    #         if signal_type == 'connected':
    #             self.connected.emit()
    #         elif signal_type == 'disconnected':
    #             self.disconnected.emit()
    #         elif signal_type == 'error':
    #             self.error.emit(args[0])
    def _emit_pending_signals(self) -> None:
        """Emit pending signals from the main thread"""
        try:
            while self._pending_signals:
                signal_type, *args = self._pending_signals.pop(0)
                if signal_type == 'connected':
                    self.connected.emit()
                elif signal_type == 'disconnected':
                    self.disconnected.emit()
                elif signal_type == 'error':
                    self.error.emit(args[0])
        except Exception as e:
            _log.error(f"Error emitting signals: {e}")
    
    def _queue_signal(self, signal_type: str, *args) -> None:
        """Queue a signal to be emitted from the main thread"""
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
            # Queue error signal
            self._queue_signal('error', str(e))
        # finally:
        #     _log.info("Closing WebSocket loop")
        #     self._loop.close()
        finally:
            _log.info("Closing WebSocket event loop.")
            tasks = asyncio.all_tasks(loop=self._loop)
            for task in tasks:
                task.cancel()
            
            async def gather_tasks():
                await asyncio.gather(*tasks, return_exceptions=True)

            if self._loop.is_running():
                self._loop.run_until_complete(gather_tasks())

            self._loop.close()
    
    
    async def _connect_and_run(self) -> None:
        """Connect to WebSocket server and handle messages"""
        while self.is_running:
            try:
                async with websockets.connect(self.url) as websocket:
                    self.websocket = websocket
                    self._is_connected = True 
                    self.reconnect_attempts = 0
                    
                    self._queue_signal('connected')
                    for handler in self._connection_handlers:
                        try:
                            handler()
                        except Exception as e:
                            _log.error(f"Connection handler error: {e}")
                    
                    _log.info(f"Connected to WebSocket server at {self.url}")

                    await websocket.send(json.dumps({ "type": "artisan_client_identification" }))
                    _log.info("Sent identification to server.")

                    consumer_task = asyncio.create_task(self._consumer_handler(websocket))
                    shutdown_task = asyncio.create_task(self._shutdown_event.wait())

                    done, pending = await asyncio.wait(
                        {consumer_task, shutdown_task},
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    for task in pending:
                        task.cancel()
                        
            except (websockets.exceptions.ConnectionClosed, asyncio.CancelledError, ConnectionRefusedError):
                _log.info("Connection task stopped or connection refused.")
            except Exception as e:
                self._is_connected = False  
                self.websocket = None
                self.reconnect_attempts += 1
                
                self._queue_signal('disconnected')
                for handler in self._disconnection_handlers:
                    try:
                        handler()
                    except Exception as handler_error:
                        _log.error(f"Disconnection handler error: {handler_error}")
                
                _log.error(f"WebSocket connection error: {e}")
                
                if self.max_reconnect_attempts > 0 and self.reconnect_attempts >= self.max_reconnect_attempts:
                    _log.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached. Stopping.")
                    self._queue_signal('error', f"Max reconnection attempts ({self.max_reconnect_attempts}) reached")
                    self.is_running = False
                    break
                
            if self.is_running:
                await asyncio.sleep(self.reconnect_interval)
    
    async def _send_message(self, message: str) -> None:
        """Send a message to the WebSocket server"""
        if self.websocket and self._is_connected:  
            try:
                await self.websocket.send(message)
            except Exception as e:
                _log.error(f"Failed to send message: {e}")
                self._is_connected = False  
                self._queue_signal('error', f"Failed to send message: {e}")

    async def _consumer_handler(self, websocket: "websockets.WebSocketClientProtocol"):
            """Handle incoming messages in a loop."""
            try:
                async for message in websocket:
                    await self._handle_message(message)
            except websockets.exceptions.ConnectionClosed:
                _log.info("Connection closed by server.")
            except asyncio.CancelledError:
                _log.info("Consumer task cancelled.")
            finally:
                if self._is_connected:
                    self._is_connected = False
                    self._queue_signal('disconnected')
                    for handler in self._disconnection_handlers:
                        try:
                            handler()
                        except Exception as handler_error:
                            _log.error(f"Disconnection handler error: {handler_error}")


    def add_message_callback(self, callback):
        self._message_callbacks.append(callback)
    
    async def _handle_message(self, message: str) -> None:
        """Handle incoming messages from the server"""
        print("WebSocketBroadcaster: Raw message received:", message)
        try:
            data = json.loads(message)
            _log.debug(f"Received message: {data}")

            for cb in self._message_callbacks:
                try:
                    cb(data)
                except Exception as e:
                    _log.error(f"Message callback error: {e}")
            
            # Handle different message types
            if data.get("type") == "ping":
                await self._send_message(json.dumps({"type": "pong"}))
                
        except json.JSONDecodeError:
            _log.warning(f"Received non-JSON message: {message}")
        except Exception as e:
            _log.error(f"Error handling message: {e}")

# Check if websockets is available and log a warning if not
if not WEBSOCKETS_AVAILABLE:
    _log.warning(
        "websockets library not found. Live broadcasting will not be available. "
        "Install with: pip install websockets"
    )


# import asyncio
# import json
# import logging
# import time
# import socket
# from typing import Optional, Callable, List
# from threading import Thread

# try:
#     import websockets
#     WEBSOCKETS_AVAILABLE = True
# except ImportError:
#     websockets = None
#     WEBSOCKETS_AVAILABLE = False

# # PyQt imports
# try:
#     from PyQt6.QtCore import QObject, pyqtSignal, QTimer
# except ImportError:
#     from PyQt5.QtCore import QObject, pyqtSignal, QTimer

# _log = logging.getLogger(__name__)

# class WebSocketBroadcaster(QObject):
#     """WebSocket client for broadcasting roast data with improved stability"""
    
#     # PyQt signals
#     connected = pyqtSignal()
#     disconnected = pyqtSignal()
#     error = pyqtSignal(str)
    
#     def __init__(self, host: str = "localhost", port: int = 3000, path: str = "/ws/roast", 
#                  reconnect_interval: float = 5.0, max_reconnect_attempts: int = 10,
#                  connection_timeout: float = 10.0):
#         super().__init__()
        
#         # Validate and normalize host
#         self.host = host.strip()
#         self.port = port
#         self.path = path if path.startswith("/") else f"/{path}"
#         self.url = f"ws://{self.host}:{self.port}{self.path}"
        
#         # Connection settings
#         self.reconnect_interval = reconnect_interval
#         self.max_reconnect_attempts = max_reconnect_attempts
#         self.connection_timeout = connection_timeout
#         self.reconnect_attempts = 0
        
#         # Connection state
#         self.websocket: Optional['websockets.WebSocketClientProtocol'] = None
#         self._is_connected = False 
#         self.is_running = False
        
#         # Threading and async
#         self._loop: Optional[asyncio.AbstractEventLoop] = None
#         self._thread: Optional[Thread] = None
#         self._shutdown_event: Optional[asyncio.Event] = None
        
#         # Event handlers
#         self._connection_handlers: List[Callable[[], None]] = []
#         self._disconnection_handlers: List[Callable[[], None]] = []
#         self._message_callbacks: List[Callable] = []
        
#         # Thread-safe signal emission
#         self._signal_timer = QTimer()
#         self._signal_timer.timeout.connect(self._emit_pending_signals)
#         self._signal_timer.start(100)  # Check every 100ms
#         self._pending_signals = []
        
#         # Statistics
#         self._connection_start_time: Optional[float] = None
#         self._total_connection_attempts = 0
        
#         _log.info(f"WebSocketBroadcaster initialized for {self.url}")
        
#     def add_connection_handler(self, handler: Callable[[], None]) -> None:
#         """Add handler for connection events"""
#         self._connection_handlers.append(handler)
    
#     def add_disconnection_handler(self, handler: Callable[[], None]) -> None:
#         """Add handler for disconnection events"""
#         self._disconnection_handlers.append(handler)
    
#     def add_message_callback(self, callback):
#         """Add callback for incoming messages"""
#         self._message_callbacks.append(callback)
    
#     def start(self) -> None:
#         """Start the WebSocket client"""
#         if self.is_running:
#             _log.warning("WebSocket broadcaster is already running")
#             return
            
#         if not WEBSOCKETS_AVAILABLE:
#             raise ImportError(
#                 "websockets library is required for live broadcasting. "
#                 "Install with: pip install websockets"
#             )
        
#         self.is_running = True
#         self.reconnect_attempts = 0
#         self._total_connection_attempts += 1
#         self._thread = Thread(target=self._run_loop, daemon=True, name="WebSocketBroadcaster")
#         self._thread.start()
        
#         _log.info(f"Started WebSocket broadcaster to {self.url}")
    
#     def stop(self) -> None:
#         """Stop the WebSocket client"""
#         if not self.is_running:
#             return
        
#         _log.info("Requesting WebSocket broadcaster to stop...")
#         self.is_running = False
        
#         if self._loop and self._loop.is_running() and self._shutdown_event:
#             self._loop.call_soon_threadsafe(self._shutdown_event.set)
        
#         if self._thread:
#             self._thread.join(timeout=5)
        
#         self._is_connected = False
#         _log.info("Stopped WebSocket broadcaster")
    
#     def broadcast(self, message: str) -> None:
#         """Broadcast a message to connected clients"""
#         if self._is_connected and self.websocket and self._loop:
#             try:
#                 asyncio.run_coroutine_threadsafe(
#                     self._send_message(message), 
#                     self._loop
#                 )
#             except Exception as e:
#                 _log.error(f"Failed to queue message for broadcast: {e}")
    
#     def is_connected(self) -> bool:
#         """Check if connected to server"""
#         return self._is_connected
    
#     def get_connection_stats(self) -> dict:
#         """Get connection statistics"""
#         uptime = 0
#         if self._connection_start_time:
#             uptime = time.time() - self._connection_start_time
            
#         return {
#             "connected": self._is_connected,
#             "running": self.is_running,
#             "reconnect_attempts": self.reconnect_attempts,
#             "total_connection_attempts": self._total_connection_attempts,
#             "uptime": uptime,
#             "url": self.url
#         }
    
#     def _emit_pending_signals(self) -> None:
#         """Emit pending signals from the main thread"""
#         try:
#             while self._pending_signals:
#                 signal_type, *args = self._pending_signals.pop(0)
#                 if signal_type == 'connected':
#                     self.connected.emit()
#                 elif signal_type == 'disconnected':
#                     self.disconnected.emit()
#                 elif signal_type == 'error':
#                     self.error.emit(args[0])
#         except Exception as e:
#             _log.error(f"Error emitting signals: {e}")
    
#     def _queue_signal(self, signal_type: str, *args) -> None:
#         """Queue a signal to be emitted from the main thread"""
#         self._pending_signals.append((signal_type, *args))
    
#     def _run_loop(self) -> None:
#         """Run the asyncio event loop in a separate thread"""
#         self._loop = asyncio.new_event_loop()
#         asyncio.set_event_loop(self._loop)

#         self._shutdown_event = asyncio.Event()
#         try:
#             self._loop.run_until_complete(self._connect_and_run())
#         except Exception as e:
#             _log.error(f"WebSocket loop error: {e}")
#             self._queue_signal('error', str(e))
#         finally:
#             _log.info("Closing WebSocket event loop.")
#             try:
#                 tasks = asyncio.all_tasks(loop=self._loop)
#                 for task in tasks:
#                     task.cancel()
                
#                 async def gather_tasks():
#                     await asyncio.gather(*tasks, return_exceptions=True)

#                 if self._loop.is_running():
#                     self._loop.run_until_complete(gather_tasks())
#             except Exception as e:
#                 _log.error(f"Error during loop cleanup: {e}")
#             finally:
#                 self._loop.close()
    
#     async def _test_connectivity(self) -> bool:
#         """Test basic connectivity to the host before attempting WebSocket connection"""
#         try:
#             # Test TCP connectivity first
#             reader, writer = await asyncio.wait_for(
#                 asyncio.open_connection(self.host, self.port),
#                 timeout=self.connection_timeout
#             )
#             writer.close()
#             await writer.wait_closed()
#             _log.info(f"TCP connectivity test passed for {self.host}:{self.port}")
#             return True
#         except asyncio.TimeoutError:
#             _log.error(f"TCP connectivity test timeout for {self.host}:{self.port}")
#             return False
#         except Exception as e:
#             _log.error(f"TCP connectivity test failed for {self.host}:{self.port}: {e}")
#             return False
    
#     async def _connect_and_run(self) -> None:
#         """Connect to WebSocket server and handle messages with improved error handling"""
#         while self.is_running:
#             try:
#                 # Test connectivity first
#                 if not await self._test_connectivity():
#                     raise ConnectionRefusedError(f"Cannot reach {self.host}:{self.port}")
                
#                 # Attempt WebSocket connection with timeout
#                 _log.info(f"Attempting WebSocket connection to {self.url}")
                
#                 async with asyncio.timeout(self.connection_timeout):
#                     async with websockets.connect(
#                         self.url,
#                         ping_interval=30.0,
#                         ping_timeout=10.0,
#                         close_timeout=5.0
#                     ) as websocket:
#                         await self._handle_connection(websocket)
                        
#             except asyncio.TimeoutError:
#                 error_msg = f"Connection timeout to {self.url}"
#                 _log.error(error_msg)
#                 self._handle_connection_error(error_msg)
#             except websockets.exceptions.ConnectionClosed:
#                 _log.info("WebSocket connection closed by server")
#                 self._handle_connection_error("Connection closed by server")
#             except websockets.exceptions.InvalidURI:
#                 error_msg = f"Invalid WebSocket URI: {self.url}"
#                 _log.error(error_msg)
#                 self._handle_connection_error(error_msg)
#             except ConnectionRefusedError as e:
#                 error_msg = f"Connection refused to {self.host}:{self.port} - {e}"
#                 _log.error(error_msg)
#                 self._handle_connection_error(error_msg)
#             except asyncio.CancelledError:
#                 _log.info("WebSocket connection task cancelled")
#                 break
#             except Exception as e:
#                 error_msg = f"Unexpected connection error: {e}"
#                 _log.error(error_msg)
#                 self._handle_connection_error(error_msg)
            
#             # Wait before reconnecting
#             if self.is_running:
#                 await asyncio.sleep(self.reconnect_interval)
    
#     async def _handle_connection(self, websocket: 'websockets.WebSocketClientProtocol') -> None:
#         """Handle an active WebSocket connection"""
#         self.websocket = websocket
#         self._is_connected = True 
#         self.reconnect_attempts = 0
#         self._connection_start_time = time.time()
        
#         self._queue_signal('connected')
#         for handler in self._connection_handlers:
#             try:
#                 handler()
#             except Exception as e:
#                 _log.error(f"Connection handler error: {e}")
        
#         _log.info(f"Connected to WebSocket server at {self.url}")

#         # Send identification
#         try:
#             await websocket.send(json.dumps({"type": "artisan_client_identification"}))
#             _log.info("Sent identification to server.")
#         except Exception as e:
#             _log.error(f"Failed to send identification: {e}")

#         # Handle messages
#         consumer_task = asyncio.create_task(self._consumer_handler(websocket))
#         shutdown_task = asyncio.create_task(self._shutdown_event.wait())

#         try:
#             done, pending = await asyncio.wait(
#                 {consumer_task, shutdown_task},
#                 return_when=asyncio.FIRST_COMPLETED
#             )

#             for task in pending:
#                 task.cancel()
#         except Exception as e:
#             _log.error(f"Error in connection handling: {e}")
#         finally:
#             self._is_connected = False
#             self.websocket = None
#             self._connection_start_time = None
    
#     def _handle_connection_error(self, error_msg: str) -> None:
#         """Handle connection errors with proper state management"""
#         self._is_connected = False  
#         self.websocket = None
#         self._connection_start_time = None
#         self.reconnect_attempts += 1
        
#         self._queue_signal('disconnected')
#         for handler in self._disconnection_handlers:
#             try:
#                 handler()
#             except Exception as handler_error:
#                 _log.error(f"Disconnection handler error: {handler_error}")
        
#         if self.max_reconnect_attempts > 0 and self.reconnect_attempts >= self.max_reconnect_attempts:
#             final_error = f"Max reconnection attempts ({self.max_reconnect_attempts}) reached. Last error: {error_msg}"
#             _log.error(final_error)
#             self._queue_signal('error', final_error)
#             self.is_running = False
    
#     async def _send_message(self, message: str) -> None:
#         """Send a message to the WebSocket server"""
#         if self.websocket and self._is_connected:  
#             try:
#                 await self.websocket.send(message)
#             except Exception as e:
#                 _log.error(f"Failed to send message: {e}")
#                 self._is_connected = False  
#                 self._queue_signal('error', f"Failed to send message: {e}")

#     async def _consumer_handler(self, websocket: "websockets.WebSocketClientProtocol"):
#         """Handle incoming messages in a loop."""
#         try:
#             async for message in websocket:
#                 await self._handle_message(message)
#         except websockets.exceptions.ConnectionClosed:
#             _log.info("Connection closed by server.")
#         except asyncio.CancelledError:
#             _log.info("Consumer task cancelled.")
#         finally:
#             if self._is_connected:
#                 self._is_connected = False
#                 self._queue_signal('disconnected')
#                 for handler in self._disconnection_handlers:
#                     try:
#                         handler()
#                     except Exception as handler_error:
#                         _log.error(f"Disconnection handler error: {handler_error}")

#     async def _handle_message(self, message: str) -> None:
#         """Handle incoming messages from the server"""
#         _log.debug(f"WebSocketBroadcaster: Raw message received: {message}")
#         try:
#             data = json.loads(message)
#             _log.debug(f"Received message: {data}")

#             for cb in self._message_callbacks:
#                 try:
#                     cb(data)
#                 except Exception as e:
#                     _log.error(f"Message callback error: {e}")
            
#             # Handle different message types
#             if data.get("type") == "ping":
#                 await self._send_message(json.dumps({"type": "pong"}))
                
#         except json.JSONDecodeError:
#             _log.warning(f"Received non-JSON message: {message}")
#         except Exception as e:
#             _log.error(f"Error handling message: {e}")

# # Check if websockets is available and log a warning if not
# if not WEBSOCKETS_AVAILABLE:
#     _log.warning(
#         "websockets library not found. Live broadcasting will not be available. "
#         "Install with: pip install websockets"
#     )