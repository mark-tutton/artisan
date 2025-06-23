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
    
    def _emit_pending_signals(self) -> None:
        """Emit pending signals from the main thread"""
        while self._pending_signals:
            signal_type, *args = self._pending_signals.pop(0)
            if signal_type == 'connected':
                self.connected.emit()
            elif signal_type == 'disconnected':
                self.disconnected.emit()
            elif signal_type == 'error':
                self.error.emit(args[0])
    
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
    
    # async def _connect_and_run(self) -> None:
    #     """Connect to WebSocket server and handle messages"""
    #     while self.is_running:
    #         try:
    #             async with websockets.connect(self.url) as websocket:
    #                 self.websocket = websocket
    #                 self._is_connected = True 
    #                 self.reconnect_attempts = 0  # Reset on successful connection
                    
    #                 # Queue connected signal
    #                 self._queue_signal('connected')
                    
    #                 # Notify connection handlers
    #                 for handler in self._connection_handlers:
    #                     try:
    #                         handler()
    #                     except Exception as e:
    #                         _log.error(f"Connection handler error: {e}")
                    
                    
    #                 _log.info(f"Connected to WebSocket server at {self.url}")


    #                 # Send identification message to the server
    #                 await websocket.send(json.dumps({
    #                     "type": "artisan_client_identification"
    #                 }))
    #                 _log.info("Sent identification to server.")

                    
    #                 # Handle incoming messages
    #                 async for message in websocket:
    #                     await self._handle_message(message)
                        
    #         except Exception as e:
    #             self._is_connected = False  
    #             self.websocket = None
    #             self.reconnect_attempts += 1
                
    #             # Queue disconnected signal
    #             self._queue_signal('disconnected')
                
    #             # Notify disconnection handlers
    #             for handler in self._disconnection_handlers:
    #                 try:
    #                     handler()
    #                 except Exception as handler_error:
    #                     _log.error(f"Disconnection handler error: {handler_error}")
                
    #             _log.error(f"WebSocket connection error: {e}")
                
    #             # Check if we should stop trying to reconnect
    #             if self.max_reconnect_attempts > 0 and self.reconnect_attempts >= self.max_reconnect_attempts:
    #                 _log.error(f"Max reconnection attempts ({self.max_reconnect_attempts}) reached. Stopping.")
    #                 self._queue_signal('error', f"Max reconnection attempts ({self.max_reconnect_attempts}) reached")
    #                 self.is_running = False
    #                 break
                
    #             # Wait before reconnecting
    #             if self.is_running:
    #                 await asyncio.sleep(self.reconnect_interval)
    
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