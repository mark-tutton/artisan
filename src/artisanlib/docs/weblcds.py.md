# Artisan WebLCDs Module Documentation

## File: `src/artisanlib/weblcds.py`

### Overview
This module implements the **Web-based LCD Display System** for the Artisan coffee roasting application. At 283 lines, it provides a sophisticated web server framework that enables remote monitoring and display of roasting data through web browsers, WebSocket connections, and custom web interfaces.

### Purpose and Architecture
The `weblcds.py` module serves as the **web interface layer** for Artisan, implementing:
- **Remote Monitoring**: Web-based access to roasting data from any device
- **Real-time Updates**: WebSocket-based live data streaming
- **Multiple Display Types**: LCD-style displays, scale widgets, and custom interfaces
- **Asynchronous Architecture**: High-performance async web server implementation
- **Template System**: Jinja2-based HTML template rendering
- **Cross-platform Access**: Browser-based access from any operating system

### Key Components

#### **Base Web View: `WebView`**
```python
class WebView:
    __slots__ = ['_loop', '_thread', '_app', '_port', '_last_send', '_last_message', 
                  '_min_send_interval', '_resource_path', '_index_path', '_websocket_path', '_runner']
    
    def __init__(self, port: int, resource_path: str, index_path: str, websocket_path: str):
        # Base web server implementation
        # Asynchronous event loop management
        # WebSocket connection handling
```

**Core Features:**
- **Asynchronous Server**: Built on aiohttp for high performance
- **WebSocket Support**: Real-time bidirectional communication
- **Template Engine**: Jinja2 integration for dynamic HTML generation
- **Resource Management**: Static file serving and dynamic routing
- **Thread Safety**: Background thread management for async operations

### Technical Implementation

#### **Asynchronous Event Loop Management**
```python
def startWeb(self) -> bool:
    self._loop = asyncio.new_event_loop()
    self._thread = Thread(target=self.start_background_loop, args=(self._loop,), daemon=True)
    self._thread.start()
    
    # run web task in async loop
    future = asyncio.run_coroutine_threadsafe(self.startup(), self._loop)
    future.result()
    return True

@staticmethod
def start_background_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    try:
        # run_forever() returns after calling loop.stop()
        loop.run_forever()
        # clean up tasks
        for task in asyncio.all_tasks(loop):
            task.cancel()
        for t in [t for t in asyncio.all_tasks(loop) if not (t.done() or t.cancelled())]:
            with suppress(asyncio.CancelledError):
                loop.run_until_complete(t)
    except Exception as e:
        _log.exception(e)
    finally:
        loop.close()
```

**Event Loop Features:**
- **Background Threading**: Dedicated thread for async operations
- **Daemon Threads**: Automatic cleanup on application shutdown
- **Task Management**: Proper task cancellation and cleanup
- **Error Handling**: Graceful handling of loop exceptions

#### **Web Application Setup**
```python
def __init__(self, port: int, resource_path: str, index_path: str, websocket_path: str):
    self._app = web.Application(debug=True)
    self._app['websockets'] = weakref.WeakSet()
    self._app.on_shutdown.append(self.on_shutdown)
    
    aiohttp_jinja2.setup(self._app, loader=jinja2.FileSystemLoader(resource_path))
    
    self._app.add_routes([
        web.get(f'/{self._index_path}', self.index),
        web.get(f'/{self._websocket_path}', self.websocket_handler),
        web.static('/', resource_path, append_version=True)
    ])
```

**Application Features:**
- **Debug Mode**: Development-friendly debugging enabled
- **Weak References**: Automatic cleanup of disconnected WebSockets
- **Shutdown Handling**: Proper cleanup on server shutdown
- **Static File Serving**: Efficient static resource delivery
- **Version Appending**: Cache-busting for static resources

#### **WebSocket Connection Management**
```python
async def websocket_handler(self, request: 'Request') -> web.WebSocketResponse:
    ws: web.WebSocketResponse = web.WebSocketResponse()
    await ws.prepare(request)
    request.app['websockets'].add(ws)
    
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                if msg.data == '' and self._last_message is not None:
                    # send last message to new client
                    await self.send_msg_to_ws(ws, self._last_message)
            elif msg.type == WSMsgType.ERROR:
                _log.error('ws connection closed with exception %s', ws.exception())
    finally:
        request.app['websockets'].discard(ws)
    return ws
```

**WebSocket Features:**
- **Connection Tracking**: Maintains set of active connections
- **Message Broadcasting**: Sends messages to all connected clients
- **Error Handling**: Logs connection errors and exceptions
- **Auto-cleanup**: Removes disconnected clients automatically
- **Last Message Caching**: Sends last message to new connections

#### **Message Broadcasting System**
```python
async def send_msg_to_all(self, message: str) -> None:
    if 'websockets' in self._app and self._app['websockets'] is not None:
        ws_set = set(self._app['websockets'])
        for ws in ws_set:
            await self.send_msg_to_ws(ws, message)

def send_msg(self, message: str, timeout: Optional[float] = 0.2) -> None:
    self._last_message = message
    now: float = time.time()
    if self._loop is not None and (now - self._min_send_interval) > self._last_send:
        self._last_send = now
        future = asyncio.run_coroutine_threadsafe(self.send_msg_to_all(message), self._loop)
        try:
            future.result(timeout)
        except TimeoutError:
            future.cancel()
        except Exception as ex:
            _log.error(ex)
```

**Broadcasting Features:**
- **Rate Limiting**: Configurable minimum send intervals
- **Thread Safety**: Cross-thread message sending
- **Timeout Protection**: Prevents blocking on slow operations
- **Error Recovery**: Graceful handling of send failures
- **Message Caching**: Stores last message for new clients

### Specialized Display Classes

#### **WebLCDs: Main LCD Display**
```python
class WebLCDs(WebView):
    __slots__ = ['_nonesymbol', '_timecolor', '_timebackground', '_btcolor', '_btbackground', 
                  '_etcolor', '_etbackground', '_showetflag', '_showbtflag']
    
    def __init__(self, port: int, resource_path: str, index_path: str, websocket_path: str,
                 nonesymbol: str, timecolor: str, timebackground: str, btcolor: str,
                 btbackground: str, etcolor: str, etbackground: str, 
                 showetflag: bool, showbtflag: bool):
        # Main LCD-style display for roasting data
        # Configurable colors and display options
        # Bean temperature and environmental temperature display
```

**LCD Features:**
- **Color Customization**: Configurable text and background colors
- **Display Flags**: Control visibility of different temperature readings
- **Symbol Handling**: Custom symbols for missing data
- **Template Rendering**: Uses 'artisan.tpl' for HTML generation
- **Port Configuration**: Configurable network port

#### **WebGreen: Green Coffee Scale Widget**
```python
class WebGreen(WebView):
    __slots__ = ['_title']
    
    template_name = 'scale_widget.tpl'
    index_path = 'green'
    ws_path = 'websocket'
    
    def __init__(self, title: str, port: int, resource_path: str):
        super().__init__(port, resource_path, WebGreen.index_path, f'{WebGreen.ws_path}')
        self._title = title
        self._min_send_interval = 0  # send all updates
```

**Green Coffee Features:**
- **Scale Integration**: Displays green coffee weight data
- **Real-time Updates**: No rate limiting for immediate feedback
- **Custom Templates**: Uses 'scale_widget.tpl' for rendering
- **Title Configuration**: Customizable widget title
- **Dedicated Path**: '/green' endpoint for green coffee data

#### **WebRoasted: Roasted Coffee Scale Widget**
```python
class WebRoasted(WebView):
    __slots__ = ['_title']
    
    template_name = 'scale_widget.tpl'
    index_path = 'roasted'
    ws_path = 'websocket'
    
    def __init__(self, title: str, port: int, resource_path: str):
        super().__init__(port, resource_path, WebRoasted.index_path, f'{WebRoasted.ws_path}')
        self._title = title
        self._min_send_interval = 0  # send all updates
```

**Roasted Coffee Features:**
- **Scale Integration**: Displays roasted coffee weight data
- **Real-time Updates**: No rate limiting for immediate feedback
- **Custom Templates**: Uses 'scale_widget.tpl' for rendering
- **Title Configuration**: Customizable widget title
- **Dedicated Path**: '/roasted' endpoint for roasted coffee data

### Server Management and Lifecycle

#### **Startup Process**
```python
async def startup(self) -> None:
    self._runner = web.AppRunner(self._app)
    await self._runner.setup()
    site = web.TCPSite(self._runner, '0.0.0.0', self._port)
    await asyncio.wait_for(site.start(), 0.7)
```

**Startup Features:**
- **App Runner Setup**: Configures aiohttp application runner
- **TCP Site Binding**: Binds to all network interfaces
- **Port Configuration**: Uses specified port number
- **Timeout Protection**: 0.7 second startup timeout
- **Network Binding**: Binds to 0.0.0.0 for external access

#### **Shutdown Process**
```python
def stopWeb(self) -> None:
    if self._loop is not None:
        if self._runner is not None:
            future = asyncio.run_coroutine_threadsafe(self._runner.cleanup(), self._loop)
            future.result()
        self._loop.call_soon_threadsafe(self._loop.stop)
        self._loop = None
    
    if self._thread is not None:
        self._thread.join()
        self._thread = None

@staticmethod
async def on_shutdown(app: web.Application) -> None:
    for ws in set(app['websockets']):
        await ws.close(code=WSCloseCode.GOING_AWAY, message='Server shutdown')
```

**Shutdown Features:**
- **Graceful Cleanup**: Proper cleanup of web runner
- **Thread Safety**: Safe loop stopping from any thread
- **WebSocket Cleanup**: Closes all active connections
- **Thread Joining**: Waits for background thread completion
- **Resource Cleanup**: Proper disposal of all resources

### Template System Integration

#### **Jinja2 Template Setup**
```python
aiohttp_jinja2.setup(self._app, loader=jinja2.FileSystemLoader(resource_path))
```

**Template Features:**
- **File System Loading**: Loads templates from resource directory
- **Dynamic Rendering**: Server-side template processing
- **Variable Injection**: Passes data to HTML templates
- **Template Caching**: Efficient template loading and caching

#### **Template Rendering Examples**
```python
@aiohttp_jinja2.template('artisan.tpl')
async def index(self, _request: 'Request') -> Dict[str, str]:
    showspace_str = 'inline' if not (self._showbtflag and self._showetflag) else 'none'
    showbt_str = 'inline' if self._showbtflag else 'none'
    showet_str = 'inline' if self._showetflag else 'none'
    return {
        'port': str(self._port),
        'nonesymbol': self._nonesymbol,
        'timecolor': self._timecolor,
        'timebackground': self._timebackground,
        'btcolor': self._btcolor,
        'btbackground': self._btbackground,
        'etcolor': self._etcolor,
        'etbackground': self._etbackground,
        'showbt': showbt_str,
        'showet': showet_str,
        'showspace': showspace_str
    }
```

**Rendering Features:**
- **Conditional Display**: Controls visibility of UI elements
- **Color Configuration**: Passes color settings to templates
- **Port Information**: Provides port number for client connections
- **Display Flags**: Controls which data elements are shown

### Performance and Optimization

#### **Rate Limiting System**
```python
def send_msg(self, message: str, timeout: Optional[float] = 0.2) -> None:
    self._last_message = message
    now: float = time.time()
    if self._loop is not None and (now - self._min_send_interval) > self._last_send:
        self._last_send = now
        # Send message logic
```

**Optimization Features:**
- **Configurable Intervals**: Different rate limits for different display types
- **Time-based Throttling**: Prevents excessive message sending
- **Performance Protection**: Avoids overwhelming clients with updates
- **Resource Management**: Efficient use of network and CPU resources

#### **Memory Management**
```python
self._app['websockets'] = weakref.WeakSet()
```

**Memory Features:**
- **Weak References**: Automatic cleanup of disconnected clients
- **Garbage Collection**: Prevents memory leaks from abandoned connections
- **Resource Efficiency**: Minimal memory overhead per connection
- **Automatic Cleanup**: No manual connection tracking required

### Security and Network Features

#### **Network Binding**
```python
site = web.TCPSite(self._runner, '0.0.0.0', self._port)
```

**Network Features:**
- **External Access**: Binds to all network interfaces
- **Port Configuration**: Configurable port numbers
- **TCP Protocol**: Reliable connection-oriented communication
- **Network Visibility**: Accessible from other devices on network

#### **Error Handling and Logging**
```python
async def send_msg_to_ws(self, ws: web.WebSocketResponse, message: str) -> None:
    try:
        await ws.send_str(message)
    except Exception as e:
        _log.exception(e)
        try:
            self._app['websockets'].discard(ws)
        except Exception as ex:
            _log.exception(ex)
```

**Error Handling Features:**
- **Exception Logging**: Comprehensive error logging
- **Connection Cleanup**: Automatic removal of failed connections
- **Graceful Degradation**: Continues operation despite individual failures
- **Debug Information**: Detailed logging for troubleshooting

### Integration Points

#### **Main Application Integration**
```python
# Used by main Artisan application to provide web-based monitoring
# Integrates with roasting data and scale systems
# Provides remote access to application state
```

**Integration Features:**
- **Data Access**: Receives roasting data from main application
- **Scale Integration**: Displays weight data from connected scales
- **Real-time Updates**: Provides live data streaming
- **Remote Monitoring**: Enables monitoring from any web-enabled device

#### **Template System Integration**
```python
# Templates located in resource_path directory
# artisan.tpl: Main LCD display template
# scale_widget.tpl: Scale display widget template
```

**Template Integration:**
- **HTML Generation**: Server-side HTML generation
- **Dynamic Content**: Real-time data injection into templates
- **Responsive Design**: Mobile-friendly web interfaces
- **Custom Styling**: Configurable colors and appearance

This module represents a sophisticated web interface system that transforms Artisan from a local desktop application into a network-accessible monitoring platform, enabling professional roasters to monitor their roasting process from any device with a web browser while maintaining the performance and reliability required for real-time roasting operations.