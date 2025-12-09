# Artisan Bluetooth Low Energy (BLE) Port Module Documentation

## File: `src/artisanlib/ble_port.py`

### Overview
This module implements the **comprehensive Bluetooth Low Energy (BLE) communication system** for the Artisan coffee roasting application. At 523 lines, it provides a sophisticated BLE client framework that enables wireless communication with temperature sensors, scales, and other BLE-enabled devices through a robust, thread-safe architecture.

### Purpose and Architecture
The `ble_port.py` module serves as the **BLE communication backbone** for Artisan, implementing:
- **BLE Device Management**: Device discovery, connection, and management
- **Thread-Safe Communication**: Asynchronous BLE operations in dedicated threads
- **Automatic Reconnection**: Robust connection management with automatic recovery
- **Service Discovery**: Intelligent device matching and service validation
- **Data Communication**: Read, write, and notification handling

### Key Components

#### 1. **Core BLE Interface Class: `BLE`**

##### **Thread Safety and Resource Management**
```python
class BLE:
    _scan_and_connect_lock:asyncio.Lock = asyncio.Lock()
    _terminate_scan_event = asyncio.Event()
    _asyncLoopThread:Optional[AsyncLoopThread] = None
```

- **Resource Protection**: Prevents overlapping scan/connect operations
- **Thread Isolation**: Dedicated asyncio event loop for BLE operations
- **Resource Cleanup**: Proper cleanup on application termination
- **Scan Control**: Ability to terminate ongoing scan operations

##### **Device Discovery and Matching**
```python
@staticmethod
def name_match(bd:'BLEDevice', ad:'AdvertisementData', device_name:str, case_sensitive:bool, service_uuid:Optional[str]) -> bool:
```

- **Multi-Criteria Matching**: Device name, local name, and service UUID matching
- **Case Sensitivity**: Configurable case-sensitive matching
- **Service Validation**: Service UUID-based device filtering
- **Flexible Matching**: Multiple matching strategies for device identification

##### **Scanning and Connection Management**
```python
async def _scan_and_connect(self, device_descriptions:Dict[Optional[str],Optional[Set[str]]], 
                           blacklist:Set[str], case_sensitive:bool, 
                           disconnected_callback:Optional[Callable[[BleakClient], None]], 
                           scan_timeout:float, connect_timeout:float, 
                           address:Optional[str] = None) -> Tuple[Optional[BleakClient], Optional[str]]:
```

- **Atomic Operations**: Lock-protected scan and connect operations
- **Timeout Management**: Configurable scan and connect timeouts
- **Address Filtering**: Optional device address-based filtering
- **Service Validation**: Automatic service availability verification

#### 2. **BLE Client Framework: `ClientBLE`**

##### **Client State Management**
```python
class ClientBLE(QObject):
    def __init__(self) -> None:
        self._running:bool = False
        self._ble_client:Optional[BleakClient] = None
        self._connected_service_uuid:Optional[str] = None
        self._disconnected_event:asyncio.Event = asyncio.Event()
```

- **Connection State**: Comprehensive connection state tracking
- **Service Management**: Service UUID tracking and validation
- **Event Handling**: Disconnection event management
- **Notification Tracking**: Active notification UUID management

##### **Automatic Reconnection System**
```python
async def _connect(self, case_sensitive:bool=True, scan_timeout:float=6, 
                  connect_timeout:float=6, address:Optional[str] = None) -> None:
```

- **Persistent Connection**: Continuous reconnection attempts while running
- **Blacklist Management**: Device blacklisting for failed connections
- **Service Validation**: Automatic service availability verification
- **Exponential Backoff**: Intelligent reconnection timing

##### **Data Communication Interface**
```python
def send(self, message:bytes, response:bool = False, write_characteristic:Optional[str] = None) -> None:
def read(self, read_characteristic:Optional[str] = None) -> Optional[bytes]:
```

- **Write Operations**: BLE characteristic writing with response control
- **Read Operations**: BLE characteristic reading
- **Characteristic Selection**: Automatic or manual characteristic selection
- **Error Handling**: Comprehensive error handling and logging

#### 3. **Notification System**

##### **Notification Management**
```python
def start_notifications(self) -> None:
def stop_notifications(self) -> None:
```

- **Automatic Start**: Notifications start automatically on connection
- **Characteristic Validation**: Automatic characteristic availability checking
- **State Tracking**: Active notification UUID tracking
- **Cleanup**: Proper notification cleanup on disconnection

##### **Notification Callbacks**
```python
def add_notify(self, notify_uuid:str, callback:'Callable[[BleakGATTCharacteristic, bytearray], None]') -> None:
```

- **Callback Registration**: Flexible notification callback registration
- **UUID Management**: Multiple notification characteristic support
- **Data Processing**: Real-time notification data handling
- **Error Resilience**: Robust notification error handling

#### 4. **Device Description System**

##### **Device Matching Configuration**
```python
def add_device_description(self, service_uuid:Optional[str] = None, device_name:Optional[str] = None) -> None:
```

- **Flexible Matching**: Multiple device matching strategies
- **Service UUID Matching**: Service-based device filtering
- **Name Matching**: Device name-based filtering
- **Wildcard Support**: Universal matching with None values

##### **Matching Strategies**
- **Exact Match**: Service UUID + device name combination
- **Service Only**: Service UUID matching regardless of name
- **Name Only**: Device name matching regardless of service
- **Universal Match**: Match any device (both parameters None)

#### 5. **Advanced Features**

##### **Heartbeat System**
```python
async def _keep_alive(self) -> None:
def set_heartbeat(self, frequency:float) -> None:
```

- **Connection Monitoring**: Periodic connection health checks
- **Configurable Frequency**: Adjustable heartbeat intervals
- **Automatic Management**: Background heartbeat operation
- **Connection Recovery**: Heartbeat-based connection monitoring

##### **Scan Management**
```python
def scan(self, scan_timeout:float = 3.0) -> 'List[Tuple[BLEDevice, AdvertisementData]]':
```

- **Device Discovery**: Comprehensive BLE device scanning
- **Advertisement Data**: Rich device information collection
- **Timeout Control**: Configurable scan duration
- **Result Processing**: Structured scan result handling

### Technical Implementation Details

#### **Asynchronous Architecture**
- **Event Loop Management**: Dedicated asyncio event loop for BLE operations
- **Thread Safety**: Proper synchronization between UI and BLE threads
- **Non-blocking Operations**: All BLE operations are asynchronous
- **Resource Management**: Proper cleanup of asyncio resources

#### **BLE Protocol Handling**
- **GATT Services**: Comprehensive GATT service management
- **Characteristic Operations**: Read, write, and notification handling
- **Service Discovery**: Automatic service availability detection
- **Connection Management**: Robust connection lifecycle management

#### **Error Handling and Recovery**
- **Exception Safety**: Comprehensive exception handling throughout
- **Connection Recovery**: Automatic reconnection on failures
- **Timeout Management**: Configurable timeouts for all operations
- **Resource Cleanup**: Proper cleanup of failed connections

### Integration Points

#### **Main Application**
- **Device Communication**: Integration with Artisan's device system
- **Settings System**: BLE configuration persistence
- **Error Reporting**: Centralized error handling and logging
- **Device Management**: BLE device lifecycle management

#### **Device Drivers**
- **Temperature Sensors**: BLE temperature sensor integration
- **Scales**: BLE scale integration
- **Control Devices**: BLE control device integration
- **Custom Devices**: Plugin-defined BLE device support

#### **Communication System**
- **Async Communication**: Integration with Artisan's async communication framework
- **Thread Management**: Proper thread lifecycle management
- **Event Handling**: Integration with Qt event system
- **Signal Management**: Qt signal-based communication

### Configuration and Customization

#### **BLE Parameters**
- **Scan Timeouts**: Configurable device discovery timeouts
- **Connect Timeouts**: Configurable connection establishment timeouts
- **Reconnection Delays**: Intelligent reconnection timing
- **Heartbeat Frequency**: Configurable connection monitoring

#### **Device Matching**
- **Service UUIDs**: Service-based device filtering
- **Device Names**: Name-based device identification
- **Case Sensitivity**: Configurable name matching behavior
- **Wildcard Support**: Flexible matching strategies

#### **Communication Settings**
- **Characteristic Selection**: Manual or automatic characteristic selection
- **Response Handling**: Configurable write response handling
- **Notification Management**: Flexible notification configuration
- **Error Logging**: Comprehensive communication logging

### Best Practices and Usage

#### **BLE Device Integration**
- **Service Validation**: Always validate required services
- **Characteristic Management**: Proper characteristic registration
- **Error Handling**: Implement comprehensive error handling
- **Resource Cleanup**: Proper cleanup on disconnection

#### **Performance Optimization**
- **Connection Management**: Efficient connection lifecycle management
- **Notification Handling**: Optimize notification processing
- **Resource Usage**: Monitor system resource consumption
- **Timeout Configuration**: Balance responsiveness with reliability

#### **Error Recovery**
- **Reconnection Logic**: Implement robust reconnection strategies
- **Service Validation**: Verify service availability on reconnection
- **State Management**: Maintain consistent connection state
- **User Feedback**: Provide clear connection status information

### Future Enhancements

#### **Planned Improvements**
- **Advanced Security**: Enhanced BLE security features
- **Power Management**: Improved power consumption optimization
- **Multi-Device Support**: Enhanced multi-device management
- **Protocol Extensions**: Support for additional BLE protocols

#### **Extensibility Features**
- **Plugin Support**: Enhanced plugin BLE device support
- **Custom Protocols**: User-defined BLE communication protocols
- **Advanced Matching**: More sophisticated device matching algorithms
- **Performance Monitoring**: BLE performance metrics and optimization

### Use Cases and Applications

#### **Temperature Sensors**
- **Wireless Monitoring**: BLE temperature sensor integration
- **Real-time Data**: Continuous temperature data streaming
- **Multi-sensor Support**: Multiple BLE temperature sensors
- **Battery Management**: Battery-powered sensor support

#### **Digital Scales**
- **Weight Monitoring**: BLE scale integration
- **Real-time Weighing**: Continuous weight data streaming
- **Multi-scale Support**: Multiple BLE scale support
- **Calibration Support**: Scale calibration and management

#### **Control Devices**
- **Remote Control**: BLE control device integration
- **Parameter Adjustment**: Remote parameter modification
- **Status Monitoring**: Device status monitoring
- **Configuration Management**: Remote device configuration

This module represents Artisan's comprehensive BLE communication system, providing professional-grade wireless device integration capabilities that enable seamless communication with modern BLE-enabled roasting equipment while maintaining high performance, reliability, and ease of use.