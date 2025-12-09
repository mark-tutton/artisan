# Artisan Async Communication Module Documentation

## File: `src/artisanlib/async_comm.py`

### Overview
This module provides **generic asyncio-based communication infrastructure** for the Artisan coffee roasting application. It implements a sophisticated asynchronous communication layer that supports both serial and network-based device communication, with thread-safe operations and robust error handling.

### Purpose and Architecture
The `async_comm.py` module serves as the **foundational communication framework** that enables Artisan to:
- **Communicate asynchronously** with various hardware devices
- **Handle multiple communication protocols** (serial, TCP/IP)
- **Maintain thread safety** between UI and communication layers
- **Provide robust error handling** and reconnection logic
- **Support both blocking and non-blocking** communication patterns

### Core Components

#### **1. AsyncLoopThread Class**

**Purpose**: Manages a dedicated thread with its own asyncio event loop for communication operations.

**Key Features**:
```python
class AsyncLoopThread:
    __slots__ = [ '__loop', '__thread' ]
```

**Thread Management**:
- **Background Loop**: Runs asyncio event loop in separate thread
- **Daemon Thread**: Automatically terminates when main application exits
- **Resource Cleanup**: Properly closes loop and cancels pending tasks

**Implementation Details**:
```python
def start_background_loop(loop: asyncio.AbstractEventLoop) -> None:
    asyncio.set_event_loop(loop)
    try:
        loop.run_forever()  # Run until explicitly stopped
        # Clean up all pending tasks
        for task in asyncio.all_tasks(loop):
            task.cancel()
    finally:
        loop.close()
```

**Lifecycle Management**:
- **Creation**: New event loop and thread on instantiation
- **Destruction**: Automatic cleanup on object deletion
- **Warning**: Deliberate non-joining to prevent hangs

#### **2. AsyncIterable Class**

**Purpose**: Wraps asyncio Queue to provide async iteration interface for data streaming.

**Interface**:
```python
class AsyncIterable:
    def __aiter__(self) -> 'AsyncIterable':
        return self

    async def __anext__(self) -> bytes:
        return await self._queue.get()
```

**Usage Pattern**:
- **Data Streaming**: Continuous data flow from communication channels
- **Queue Integration**: Seamless integration with asyncio Queue
- **Async Iteration**: Support for `async for` loops

#### **3. IteratorReader Class**

**Purpose**: Provides buffered reading capabilities for async data streams with backlog management.

**Key Methods**:

**`readexactly(size: int)`**:
```python
async def readexactly(self, size: int = -1) -> bytes:
    if size > 0:
        return await self._read_chunk(size)
    if size == -1:
        return await self._read_until_end()
    return b''
```

**`readuntil(separator: bytes)`**:
```python
async def readuntil(self, separator: bytes = b'\n') -> bytes:
    if len(separator) != 0:
        while True:
            next_char = await self.readexactly(len(separator))
            if next_char == separator:
                break
    return separator
```

**Backlog Management**:
- **Data Buffering**: Maintains unprocessed data between reads
- **Efficient Reading**: Minimizes data copying and reallocation
- **Boundary Handling**: Proper handling of partial messages

#### **4. AsyncComm Class - The Main Communication Engine**

**Purpose**: Core communication class that orchestrates all async communication operations.

**Class Structure**:
```python
class AsyncComm:
    __slots__ = [ 
        '_asyncLoopThread', '_write_queue', '_running', 
        '_host', '_port', '_serial', '_connected_handler', 
        '_disconnected_handler', '_verify_crc', '_logging' 
    ]
```

### Communication Architecture

#### **Connection Management**

**Connection Types**:
1. **Serial Communication**: Direct serial port access
2. **Network Communication**: TCP/IP socket connections
3. **Hybrid Mode**: Serial with network fallback

**Connection Flow**:
```python
async def connect(self, connect_timeout: float = 5) -> None:
    while self._running:
        try:
            if self._serial is not None:
                # Serial connection
                connect = self.open_serial_connection(...)
            else:
                # Network connection
                connect = asyncio.open_connection(self._host, self._port)
            
            reader, writer = await asyncio.wait_for(connect, timeout=connect_timeout)
            # Handle connection success
        except Exception as e:
            # Handle connection failure
        finally:
            # Cleanup and reconnection logic
```

#### **Serial Communication Support**

**Serial Connection Wrapper**:
```python
@staticmethod
async def open_serial_connection(url: str, *, loop: Optional[asyncio.AbstractEventLoop] = None,
        limit: Optional[int] = None, **kwargs: Union[int, float, str]) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
```

**Key Features**:
- **Patched pyserial-asyncio**: Custom serial transport implementation
- **StreamReader/StreamWriter**: Standard asyncio interface
- **Configurable Buffer**: Adjustable buffer limits (default: 64 KiB)
- **Loop Integration**: Seamless event loop integration

#### **Data Flow Architecture**

**Read Path**:
```
Device → StreamReader → handle_reads() → read_msg() → Application
```

**Write Path**:
```
Application → send() → _write_queue → handle_writes() → StreamWriter → Device
```

**Queue Management**:
- **Thread-Safe Operations**: `asyncio.run_coroutine_threadsafe()`
- **Bounded Queues**: Prevents memory overflow
- **Message Ordering**: FIFO message processing

### Thread Safety and Concurrency

#### **Threading Model**

**Architecture**:
```
Main Thread (UI) ←→ AsyncLoopThread (Communication)
     ↓                    ↓
PyQt Event Loop    asyncio Event Loop
     ↓                    ↓
User Interface      Device Communication
```

**Thread Safety Mechanisms**:
1. **Dedicated Communication Thread**: Isolated from UI thread
2. **Queue-Based Communication**: Thread-safe message passing
3. **Event Loop Isolation**: Separate asyncio loops per thread
4. **Atomic Operations**: Thread-safe signal emission

#### **Concurrency Control**

**Task Management**:
```python
read_handler = asyncio.create_task(self.handle_reads(reader))
write_handler = asyncio.create_task(self.handle_writes(writer, self._write_queue))
done, pending = await asyncio.wait([read_handler, write_handler], 
                                  return_when=asyncio.FIRST_COMPLETED)
```

**Resource Cleanup**:
- **Task Cancellation**: Proper cleanup of pending tasks
- **Exception Propagation**: Handling of task exceptions
- **Connection Cleanup**: Proper writer closure

### Error Handling and Resilience

#### **Exception Management**

**Comprehensive Error Handling**:
```python
try:
    # Communication operations
except asyncio.TimeoutError:
    _log.debug('connection timeout')
except Exception as e:
    _log.error(e)
finally:
    # Cleanup operations
```

**Error Recovery Strategies**:
1. **Automatic Reconnection**: Continuous retry loop
2. **Timeout Handling**: Configurable connection timeouts
3. **Resource Cleanup**: Proper cleanup on failures
4. **Handler Invocation**: Disconnection notification

#### **Reconnection Logic**

**Reconnection Strategy**:
```python
while self._running:
    try:
        # Attempt connection
        # Handle communication
    except Exception:
        # Handle failure
    finally:
        # Cleanup and wait
        await asyncio.sleep(0.5)  # Prevent rapid reconnection
```

**Benefits**:
- **Resilient Communication**: Automatic recovery from failures
- **Backoff Strategy**: Prevents connection flooding
- **State Management**: Proper state transitions

### Configuration and Customization

#### **Communication Parameters**

**Serial Settings**:
```python
self._serial: Optional[SerialSettings] = serial
# Supports: port, baudrate, bytesize, stopbits, parity, timeout
```

**Network Settings**:
```python
self._host: str = host      # Default: '127.0.0.1'
self._port: int = port      # Default: 8080
```

**Behavioral Settings**:
```python
self._verify_crc: bool = True   # CRC verification
self._logging: bool = False     # Communication logging
```

#### **Handler System**

**Event Handlers**:
```python
self._connected_handler: Optional[Callable[[], None]] = connected_handler
self._disconnected_handler: Optional[Callable[[], None]] = disconnected_handler
```

**Handler Invocation**:
- **Connection Events**: Automatic handler execution
- **Exception Safety**: Protected handler execution
- **State Synchronization**: Proper event ordering

### Performance Characteristics

#### **Memory Management**

**Efficient Data Handling**:
- **StreamReader Buffering**: Configurable buffer limits
- **Queue Management**: Bounded message queues
- **Backlog Optimization**: Minimal data copying

**Resource Usage**:
- **Thread Isolation**: Dedicated communication thread
- **Event Loop Efficiency**: Single loop per thread
- **Memory Cleanup**: Automatic resource management

#### **Throughput Optimization**

**Async Operations**:
- **Non-blocking I/O**: Concurrent read/write operations
- **Efficient Queuing**: Minimal overhead message passing
- **Task Management**: Optimized task scheduling

### Integration Points

#### **Artisan Integration**

**Usage in Main Application**:
```python
# Device communication instances
self.ser = serialport(self)      # Serial communication
self.modbus = modbusport(self)   # MODBUS communication
self.ws = wsport(self)           # WebSocket communication
```

**Plugin System Support**:
- **Communication Abstraction**: Common interface for all devices
- **Protocol Independence**: Support for various protocols
- **Configuration Integration**: Unified settings management

#### **Hardware Device Support**

**Supported Protocols**:
1. **Serial Devices**: Thermocouples, PID controllers, scales
2. **Network Devices**: Web-based displays, remote sensors
3. **Custom Protocols**: Device-specific implementations

**Device Categories**:
- **Temperature Sensors**: Real-time temperature monitoring
- **Control Devices**: PID controllers, heaters
- **Measurement Devices**: Scales, color meters
- **Display Devices**: LCD displays, web interfaces

### Security Considerations

#### **Communication Security**

**Data Integrity**:
- **CRC Verification**: Optional message integrity checking
- **Timeout Protection**: Connection timeout limits
- **Error Handling**: Comprehensive exception management

**Access Control**:
- **Port Restrictions**: Configurable port access
- **Host Validation**: Network endpoint validation
- **Serial Port Security**: Serial port access control

### Development and Maintenance

#### **Code Quality**

**Design Patterns**:
- **Template Method**: Base class with override points
- **Strategy Pattern**: Configurable communication methods
- **Observer Pattern**: Event handler system

**Best Practices**:
- **Type Hints**: Comprehensive type annotation
- **Error Handling**: Robust exception management
- **Resource Management**: Proper cleanup and disposal

#### **Extensibility**

**Subclassing Support**:
```python
class CustomDevice(AsyncComm):
    async def read_msg(self, stream: asyncio.StreamReader) -> None:
        # Custom message handling logic
        pass
```

**Override Points**:
- **Message Reading**: Custom message parsing
- **Connection Logic**: Specialized connection handling
- **Error Recovery**: Custom error handling strategies

### Testing and Validation

#### **Testing Strategies**

**Unit Testing**:
- **Component Isolation**: Individual class testing
- **Mock Integration**: Simulated device communication
- **Error Scenarios**: Exception handling validation

**Integration Testing**:
- **Device Communication**: Real hardware testing
- **Protocol Validation**: Communication protocol verification
- **Performance Testing**: Throughput and latency measurement

### Conclusion

The `async_comm.py` module represents a **sophisticated, production-ready communication framework** that demonstrates several advanced software engineering concepts:

**Architectural Excellence**:
- **Separation of Concerns**: Clear separation between communication and business logic
- **Thread Safety**: Robust concurrent operation support
- **Error Resilience**: Comprehensive error handling and recovery

**Technical Innovation**:
- **Async/Await Integration**: Modern Python async programming
- **Protocol Abstraction**: Unified interface for diverse communication methods
- **Resource Management**: Efficient memory and thread management

**Real-World Application**:
- **Hardware Integration**: Practical device communication support
- **Performance Optimization**: Efficient data handling and processing
- **Maintainability**: Clean, well-documented code structure

This module serves as a **reference implementation** for building robust, asynchronous communication systems in Python, particularly for applications requiring hardware integration and real-time data processing. The combination of asyncio, threading, and comprehensive error handling creates a powerful foundation for reliable device communication in the Artisan coffee roasting application.