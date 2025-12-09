# Artisan WebSocket Port Module Documentation

## File: `src/artisanlib/wsport.py`

### Overview
This module implements the **comprehensive WebSocket communication system** for the Artisan coffee roasting application. At 413 lines, it provides a sophisticated bidirectional communication framework that enables real-time data exchange, remote control, and event synchronization between Artisan and external WebSocket servers or clients.

### Purpose and Architecture
The `wsport.py` module serves as the **WebSocket communication backbone** for Artisan, implementing:
- **Bidirectional Communication**: Real-time data exchange with external systems
- **Remote Control Integration**: External triggering of roasting events and actions
- **Event Broadcasting**: Real-time transmission of roasting data and events
- **Automatic Reconnection**: Robust connection management with automatic recovery
- **Asynchronous Operation**: Non-blocking communication using asyncio

### Key Components

#### 1. **Core WebSocket Class: `wsport`**

##### **Initialization and Configuration**
```python
def __init__(self, aw:'ApplicationWindow') -> None:
```
- **Purpose**: Initialize WebSocket communication system
- **Parameters**: `aw` - Reference to main application window
- **Features**: 
  - Default connection to `127.0.0.1:80/WebSocket`
  - Configurable host, port, and path
  - Support for up to 10 data channels
  - Compression and timeout configuration

##### **Connection Parameters**
- **Host/Port**: Configurable TCP endpoint (default: `127.0.0.1:80`)
- **Path**: WebSocket path (default: `WebSocket`)
- **Compression**: Deflate compression support (configurable)
- **Timeouts**: 
  - Connection timeout: 4 seconds (configurable)
  - Request timeout: 0.5 seconds (configurable)
  - Ping interval: 20 seconds (keepalive)
  - Ping timeout: 20 seconds

#### 2. **Communication Architecture**

##### **Asynchronous Event Loop Management**
- **Thread-Safe Operation**: Dedicated thread for asyncio event loop
- **Background Processing**: Non-blocking communication in background thread
- **Queue-Based Messaging**: Asynchronous message queue for outbound communication

##### **Producer-Consumer Pattern**
```python
async def producer(self) -> Optional[str]:
    # Retrieves messages from write queue
    
async def consumer(self, message:str) -> None:
    # Processes incoming WebSocket messages
```

- **Producer**: Manages outbound message queue
- **Consumer**: Processes incoming messages and triggers appropriate actions
- **Message Routing**: Intelligent message handling based on content type

#### 3. **Message Processing System**

##### **Request-Response Handling**
```python
async def registerRequest(self, message_id:int) -> asyncio.Event:
async def setRequestResponse(self, message_id:int, v:Dict[str, Any]) -> None:
def getRequestResponse(self, message_id:int) -> Optional[Dict[str,Any]]:
```

- **Message ID Tracking**: Unique identifier for each request
- **Event-Based Synchronization**: asyncio.Event for blocking operations
- **Response Correlation**: Automatic matching of requests and responses
- **Timeout Management**: Configurable request timeouts

##### **Push Message Processing**
The system handles several types of push messages:

###### **Roasting Control Messages**
- **`startRoasting`**: Triggers charge event and optionally starts recording
- **`endRoasting`**: Triggers drop event and optionally stops monitoring
- **`addEvent`**: Adds specific roasting phase events

###### **Event Types Supported**
- **`colorChangeEvent`**: Marks drying phase (DRY)
- **`firstCrackBeginningEvent`**: Marks first crack start (FCs)
- **`firstCrackEndEvent`**: Marks first crack end (FCe)
- **`secondCrackBeginningEvent`**: Marks second crack start (SCs)
- **`secondCrackEndEvent`**: Marks second crack end (SCe)

###### **Configuration Messages**
- **`setBurnerCapacity`**: Sets burner capacity value
- **`setRoastingProcessName`**: Sets current roast name
- **`setRoastingProcessNote`**: Sets roast notes
- **`setRoastingProcessFillWeight`**: Sets fill weight

#### 4. **Connection Management**

##### **Automatic Connection and Reconnection**
```python
async def connect(self) -> None:
```

- **Persistent Connection**: Continuous connection attempts with automatic recovery
- **Error Handling**: Graceful handling of connection failures and timeouts
- **Reconnection Logic**: Automatic reconnection with configurable delays
- **Connection State Management**: Proper cleanup and resource management

##### **Connection Lifecycle**
1. **Initial Connection**: Attempts to establish WebSocket connection
2. **Message Handling**: Sets up consumer and producer tasks
3. **Error Recovery**: Handles disconnections and connection failures
4. **Automatic Reconnection**: Restarts connection process automatically
5. **Resource Cleanup**: Proper task cancellation and cleanup

#### 5. **Data Channel Management**

##### **Channel Configuration**
- **Maximum Channels**: 10 configurable data channels
- **Channel Modes**: Temperature units (0: __, 1: Celsius, 2: Fahrenheit)
- **Channel Requests**: Customizable data request patterns
- **Channel Nodes**: JSON node names for each channel

##### **Data Structure**
```python
self.readings: List[float] = [-1]*self.channels  # Channel readings
self.channel_requests: List[str] = ['']*self.channels  # Request patterns
self.channel_nodes: List[str] = ['']*self.channels  # JSON node names
self.channel_modes: List[int] = [0]*self.channels  # Temperature modes
```

#### 6. **Integration with Main Application**

##### **Signal Integration**
- **Recording Control**: `toggleRecorderSignal` for starting/stopping data recording
- **Event Marking**: Various marking signals for roasting phases
- **Monitoring Control**: `toggleMonitorSignal` for monitoring state
- **User Feedback**: `sendmessageSignal` for connection status updates

##### **Serial Logging Integration**
- **Debug Output**: Integration with Artisan's serial logging system
- **Message Tracking**: Comprehensive logging of all WebSocket activity
- **Error Reporting**: Detailed error logging with line numbers

### Technical Implementation Details

#### **Asynchronous Architecture**
- **Event Loop Management**: Dedicated asyncio event loop in background thread
- **Thread Safety**: Proper synchronization between UI and communication threads
- **Non-Blocking Operations**: All WebSocket operations are asynchronous
- **Resource Management**: Proper cleanup of asyncio tasks and resources

#### **Message Protocol**
- **JSON Format**: All messages use JSON encoding
- **UTF-8 Encoding**: Proper handling of international characters
- **Message Separation**: Support for multi-line JSON messages
- **Compression**: Optional deflate compression for bandwidth optimization

#### **Error Handling and Recovery**
- **Exception Safety**: Comprehensive exception handling throughout
- **Connection Recovery**: Automatic reconnection on failures
- **Timeout Management**: Configurable timeouts for all operations
- **Resource Cleanup**: Proper cleanup of failed connections

### Integration Points

#### **Main Application Window**
- **Event System**: Integration with Artisan's event marking system
- **Recording Control**: Control of data recording and monitoring
- **User Interface**: Status updates and error reporting
- **Configuration**: Access to application settings and preferences

#### **Roasting Workflow**
- **Phase Marking**: Automatic marking of roasting phases
- **Event Recording**: Integration with event button system
- **Data Synchronization**: Real-time data exchange with external systems
- **Remote Control**: External triggering of roasting actions

#### **Plugin System**
- **Communication Layer**: Foundation for plugin communication
- **Event Broadcasting**: Support for plugin event transmission
- **Data Exchange**: Plugin data sharing capabilities
- **Remote Integration**: Plugin remote access support

### Configuration and Customization

#### **Connection Settings**
- **Host Configuration**: Configurable WebSocket server endpoint
- **Port Settings**: Flexible port configuration
- **Path Customization**: Customizable WebSocket path
- **Compression Options**: Enable/disable deflate compression

#### **Timeout Configuration**
- **Connection Timeout**: Time to establish initial connection
- **Request Timeout**: Time to wait for response
- **Ping Intervals**: Keepalive ping frequency
- **Reconnection Delays**: Delay between reconnection attempts

#### **Message Customization**
- **JSON Node Names**: Configurable message structure
- **Event Messages**: Customizable event message types
- **Command Patterns**: Flexible command structure
- **Data Formats**: Configurable data representation

### Best Practices and Usage

#### **Connection Management**
- **Automatic Start**: WebSocket starts automatically when needed
- **Graceful Shutdown**: Proper cleanup on application exit
- **Error Recovery**: Automatic handling of connection issues
- **Resource Conservation**: Efficient use of system resources

#### **Message Handling**
- **Asynchronous Processing**: Non-blocking message handling
- **Event Correlation**: Proper request-response matching
- **Timeout Handling**: Graceful handling of slow responses
- **Error Reporting**: Comprehensive error logging and reporting

#### **Performance Optimization**
- **Message Queuing**: Efficient outbound message handling
- **Compression**: Bandwidth optimization when enabled
- **Connection Pooling**: Efficient connection management
- **Resource Cleanup**: Proper cleanup of unused resources

### Future Enhancements

#### **Planned Improvements**
- **Secure WebSocket**: WSS (WebSocket Secure) support
- **Authentication**: Enhanced security and authentication
- **Message Validation**: Schema-based message validation
- **Performance Monitoring**: Connection quality metrics

#### **Extensibility Features**
- **Plugin Support**: Enhanced plugin communication capabilities
- **Custom Protocols**: Support for custom message formats
- **Multi-Server**: Support for multiple WebSocket endpoints
- **Load Balancing**: Intelligent connection distribution

This module represents Artisan's primary WebSocket communication system, providing robust, asynchronous, and feature-rich communication capabilities that enable seamless integration with external systems, remote monitoring, and automated roasting control while maintaining high performance and reliability.