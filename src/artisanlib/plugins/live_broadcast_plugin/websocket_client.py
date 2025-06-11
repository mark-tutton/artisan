import asyncio
import json
import logging
import time
from typing import Optional, Callable, List
from threading import Thread

# Try to import websockets, but make it optional
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    websockets = None
    WEBSOCKETS_AVAILABLE = False

_log = logging.getLogger(__name__)

class WebSocketBroadcaster:
    """WebSocket client for broadcasting roast data"""
    
    def __init__(self, host: str = "localhost", port: int = 3000, path: str = "/ws/roast"):
        self.host = host
        self.port = port
        self.path = path
        self.url = f"ws://{host}:{port}{path}"
        
        self.websocket = None
        self.is_connected = False
        self.is_running = False
        
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[Thread] = None
        self._message_queue: List[str] = []
        self._queue_lock = asyncio.Lock()
        
        self._connection_handlers: List[Callable[[], None]] = []
        self._disconnection_handlers: List[Callable[[], None]] = []
        
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
        self._thread = Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        _log.info(f"Started WebSocket broadcaster to {self.url}")
    
    def stop(self) -> None:
        """Stop the WebSocket client"""
        self.is_running = False
        
        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        if self._thread:
            self._thread.join(timeout=5)
        
        if self.websocket:
            asyncio.create_task(self.websocket.close())
        
        self.is_connected = False
        _log.info("Stopped WebSocket broadcaster")
    
    def broadcast(self, message: str) -> None:
        """Broadcast a message to connected clients"""
        if self.is_connected and self.websocket:
            asyncio.run_coroutine_threadsafe(
                self._send_message(message), 
                self._loop
            )
    
    def _run_loop(self) -> None:
        """Run the asyncio event loop in a separate thread"""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._connect_and_run())
        except Exception as e:
            _log.error(f"WebSocket loop error: {e}")
        finally:
            self._loop.close()
    
    async def _connect_and_run(self) -> None:
        """Connect to WebSocket server and handle messages"""
        while self.is_running:
            try:
                async with websockets.connect(self.url) as websocket:
                    self.websocket = websocket
                    self.is_connected = True
                    
                    # Notify connection handlers
                    for handler in self._connection_handlers:
                        try:
                            handler()
                        except Exception as e:
                            _log.error(f"Connection handler error: {e}")
                    
                    _log.info(f"Connected to WebSocket server at {self.url}")
                    
                    # Handle incoming messages
                    async for message in websocket:
                        await self._handle_message(message)
                        
            except Exception as e:
                self.is_connected = False
                self.websocket = None
                
                # Notify disconnection handlers
                for handler in self._disconnection_handlers:
                    try:
                        handler()
                    except Exception as handler_error:
                        _log.error(f"Disconnection handler error: {handler_error}")
                
                _log.error(f"WebSocket connection error: {e}")
                
                # Wait before reconnecting
                if self.is_running:
                    await asyncio.sleep(5)
    
    async def _send_message(self, message: str) -> None:
        """Send a message to the WebSocket server"""
        if self.websocket and self.is_connected:
            try:
                await self.websocket.send(message)
            except Exception as e:
                _log.error(f"Failed to send message: {e}")
                self.is_connected = False
    
    async def _handle_message(self, message: str) -> None:
        """Handle incoming messages from the server"""
        try:
            data = json.loads(message)
            _log.debug(f"Received message: {data}")
            
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