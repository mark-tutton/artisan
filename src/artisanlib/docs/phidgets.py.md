# Artisan Phidgets Support Module Documentation

## File: `src/artisanlib/phidgets.py`

### Overview
This module implements the **comprehensive Phidget hardware support system** for the Artisan coffee roasting application. At 349 lines, it provides a sophisticated device management layer that handles Phidget device discovery, connection management, and resource allocation through a centralized manager system.

### Purpose and Architecture
The `phidgets.py` module serves as the **hardware abstraction layer** for Phidget devices in Artisan, implementing:
- **Device Discovery**: Automatic detection and enumeration of connected Phidget hardware
- **Resource Management**: Intelligent allocation and reservation of Phidget channels
- **Hub Port Management**: Sophisticated handling of VINT hub devices and port conflicts
- **Thread Safety**: Semaphore-protected operations for multi-threaded environments

### Core Components

#### **Main Manager Class: `PhidgetManager`**
- **Singleton Pattern**: Centralized management of all Phidget devices
- **Event-Driven Architecture**: Automatic device attachment/detachment handling
- **Resource Pooling**: Efficient channel allocation and deallocation
- **Conflict Resolution**: Intelligent handling of hub port conflicts

#### **Device State Management**
```python
# Device availability states
self.attachedPhidgetChannels: Dict[Phidget, bool]
# True: Available for attachment
# False: Reserved/occupied by software channel
```

### Key Features

#### **1. Automatic Device Discovery**
- **Hot-Plug Support**: Real-time detection of device connections/disconnections
- **Device Classification**: Automatic categorization by device type and class
- **Serial Number Tracking**: Unique identification of each device instance
- **Hub Port Detection**: Intelligent handling of multi-port hub devices

#### **2. Hub Port Conflict Resolution**
- **VINT Device Priority**: VINT devices automatically reserve hub port channels
- **Port Reservation**: Prevents conflicts between direct hub ports and VINT devices
- **Automatic Cleanup**: Proper resource release when devices disconnect

#### **3. Resource Allocation System**
- **Channel Reservation**: Software channels can reserve hardware channels
- **Port-Level Management**: Hub ports are managed as atomic units
- **Conflict Prevention**: Automatic detection and resolution of resource conflicts

#### **4. Remote Device Support**
- **Network Phidgets**: Support for remote Phidget devices over network
- **Local/Remote Filtering**: Selective device discovery based on location
- **Connection State Management**: Tracking of device connectivity status

### Technical Architecture

#### **Thread Safety Implementation**
```python
# Semaphore-protected operations
self.managersemaphore: QSemaphore = QSemaphore(1)

def addChannel(self, channel: 'Phidget') -> None:
    try:
        self.managersemaphore.acquire(1)
        # Critical section operations
    finally:
        if self.managersemaphore.available() < 1:
            self.managersemaphore.release(1)
```

#### **Event Handler System**
```python
# Device attachment/detachment handlers
self.manager.setOnAttachHandler(self.attachHandler)
self.manager.setOnDetachHandler(self.detachHandler)

def attachHandler(self, _: Manager, attachedChannel: 'Phidget') -> None:
    # Automatic device registration and state management
```

#### **Device Classification Logic**
```python
# Hub vs. USB device detection
if attachedChannel.getParent().getDeviceClass() != DeviceClass.PHIDCLASS_HUB:
    # Process non-hub devices
    self.addChannel(attachedChannel)
```

### Device Management Workflow

#### **Device Attachment Process**
1. **Event Trigger**: Phidget device connects to system
2. **Device Analysis**: Determine device type, class, and capabilities
3. **State Initialization**: Set initial availability state
4. **Conflict Resolution**: Handle hub port conflicts if necessary
5. **Resource Allocation**: Make device available for software channels

#### **Device Reservation Process**
1. **Channel Request**: Software requests specific Phidget channel
2. **Resource Check**: Verify channel availability and compatibility
3. **Reservation**: Mark channel as reserved/occupied
4. **Port Management**: Handle related hub port reservations
5. **State Update**: Update device availability status

#### **Device Release Process**
1. **Release Request**: Software releases Phidget channel
2. **Resource Cleanup**: Mark channel as available
3. **Port Management**: Release related hub port resources
4. **State Update**: Update device availability status
5. **Conflict Resolution**: Resolve any remaining port conflicts

### Advanced Features

#### **Hub Port Conflict Resolution**
```python
# VINT device priority handling
if hupportdevice:
    # VINT device - reserve all hub port channels
    for k, _ in self.attachedPhidgetChannels.items():
        if k.getHub() == hub and k.getHubPort() == hubport:
            if k.getIsHubPortDevice() != 0:
                self.attachedPhidgetChannels[k] = False
else:
    # Direct hub port - check for VINT device conflicts
    if k.getIsHubPortDevice() == 0:
        state = False  # Deactivate due to VINT device
```

#### **Device Matching and Selection**
```python
def getFirstMatchingPhidget(self, phidget_class_name: str, device_id: int, 
                           channel: Optional[int] = None, remote: bool = False,
                           remoteOnly: bool = False, serial: Optional[int] = None,
                           hubport: Optional[int] = None) -> Tuple[Optional[int], Optional[int]]:
    # Complex matching logic for device selection
    # Returns (serial_number, port) tuple
```

#### **Remote Device Support**
```python
# Remote device filtering
((remote and not remoteOnly) or 
 (not remote and k.getIsLocal()) or 
 (remote and remoteOnly and not k.getIsLocal()))
```

### Integration Points

#### **Main Application Integration**
- **Device Discovery**: Automatic integration with Artisan's device system
- **Channel Management**: Seamless channel allocation for temperature sensors, scales, etc.
- **Error Handling**: Integrated logging and error reporting
- **Settings Persistence**: Device configurations saved in application settings

#### **Plugin System Compatibility**
- **Standard Interface**: Consistent API for all Phidget device types
- **Resource Sharing**: Efficient sharing of limited hardware resources
- **Conflict Prevention**: Automatic resolution of device conflicts

### Error Handling and Recovery

#### **Exception Management**
- **Broad Exception Handling**: Catches all exceptions to prevent crashes
- **Graceful Degradation**: Continues operation even with device failures
- **Detailed Logging**: Comprehensive error reporting for debugging
- **Resource Cleanup**: Automatic cleanup on device failures

#### **Recovery Mechanisms**
- **Automatic Reconnection**: Handles temporary connection losses
- **State Restoration**: Maintains device state across reconnections
- **Conflict Resolution**: Automatically resolves resource conflicts

### Performance Considerations

#### **Efficient Resource Management**
- **Lazy Initialization**: Devices initialized only when needed
- **Resource Pooling**: Efficient reuse of device resources
- **Conflict Prevention**: Proactive conflict resolution
- **Memory Optimization**: Minimal memory footprint per device

#### **Scalability Features**
- **Device Limit Handling**: Efficient management of large numbers of devices
- **Port Conflict Resolution**: Intelligent handling of complex hub configurations
- **Remote Device Support**: Efficient network device management

### Future Enhancement Opportunities

#### **Potential Improvements**
- **Device Templates**: Predefined configurations for common Phidget setups
- **Advanced Diagnostics**: Enhanced device health monitoring
- **Performance Metrics**: Device performance and reliability tracking
- **Configuration Validation**: Advanced device configuration validation

#### **Integration Extensions**
- **Cloud Device Management**: Remote device configuration and monitoring
- **Device Firmware Updates**: Automatic firmware update management
- **Advanced Error Recovery**: Machine learning-based error prediction and prevention

This module represents a critical component of Artisan's hardware support system, providing robust and efficient management of Phidget devices while maintaining the flexibility and reliability required for professional coffee roasting applications.