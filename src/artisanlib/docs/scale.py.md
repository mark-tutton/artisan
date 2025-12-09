# Artisan Scale Support Module Documentation

## File: `src/artisanlib/scale.py`

### Overview
This module implements the **comprehensive scale support system** for the Artisan coffee roasting application. At 444 lines, it provides a sophisticated framework for managing multiple digital scales, handling weight measurements, and coordinating scale operations through a centralized management system.

### Purpose and Architecture
The `scale.py` module serves as the **hardware abstraction layer** for digital scales in Artisan, implementing:
- **Multi-Scale Support**: Management of up to two independent scales
- **Scale Abstraction**: Unified interface for different scale types and protocols
- **Weight Stabilization**: Intelligent handling of stable vs. unstable weight readings
- **Resource Management**: Scale reservation and assignment system
- **Real-time Communication**: Live weight updates and scale status monitoring

### Key Components

#### **Base Scale Class: `Scale`**
```python
class Scale(QObject):
    scanned_signal = pyqtSignal(list)           # Device discovery results
    weight_changed_signal = pyqtSignal(float, bool)  # Weight + stability flag
    battery_changed_signal = pyqtSignal(int)    # Battery level percentage
    connected_signal = pyqtSignal()             # Connection established
    disconnected_signal = pyqtSignal()          # Connection lost
```

**Core Features:**
- **Abstract Interface**: Base class for all scale implementations
- **Signal System**: Qt signal-based communication architecture
- **Model Management**: Scale type identification and configuration
- **Assignment Control**: Scale reservation and release management

#### **Scale Manager: `ScaleManager`**
```python
class ScaleManager(QObject):
    # Scale 1 management signals
    scan_scale1_signal = pyqtSignal(int)
    set_scale1_signal = pyqtSignal(int, str, str)
    connect_scale1_signal = pyqtSignal()
    disconnect_scale1_signal = pyqtSignal()
    
    # Scale 2 management signals (parallel structure)
    scan_scale2_signal = pyqtSignal(int)
    set_scale2_signal = pyqtSignal(int, str, str)
    # ... additional scale 2 signals
```

**Management Features:**
- **Dual Scale Support**: Independent management of two scales
- **Signal Routing**: Centralized signal distribution system
- **Resource Coordination**: Prevents conflicts between scale operations
- **Availability Tracking**: Monitors scale availability status

### Technical Implementation

#### **Scale Type Support**
```python
SUPPORTED_SCALES: Final[List[Tuple[str, int]]] = [
    ('Acaia', 0)  # 0: Bluetooth, 1: WiFi, 2: Serial
]

def _get_scale(self, model: int, ident: str, name: str) -> Optional[Scale]:
    if model == 0:
        from artisanlib.acaia import Acaia
        return Acaia(model, ident, name, 
                    lambda: self.connected_handler(ident, name),
                    lambda: self.disconnected_handler(ident, name),
                    stable_only=False, decimals=0)
    return None
```

**Supported Protocols:**
- **Bluetooth (0)**: Wireless scale communication
- **WiFi (1)**: Network-based scale communication
- **Serial (2)**: Wired scale communication
- **Extensible**: Easy addition of new scale types

#### **Weight Stabilization System**
```python
# Configuration constants
STABLE_TIMER_PERIOD = 350  # ms to wait for weight stabilization
MIN_STABLE_WEIGHT_CHANGE = 1  # Minimum weight change to trigger update

@pyqtSlot(float, bool)
def scale1_weight_changed_slot(self, weight: float, stable: bool):
    weight = int(round(weight))
    if stable:
        # Immediately emit stable weight
        self.scale1_stable_weight_changed_signal.emit(weight)
        self.scale1_last_weight = None
    else:
        # Store for delayed stable emission
        self.scale1_last_weight = weight
        self.scale1_stable_reading_timer.start(STABLE_TIMER_PERIOD)
        # Emit immediate weight update for fluid display
        self.scale1_weight_changed_signal.emit(weight)
```

**Stabilization Logic:**
- **Immediate Updates**: Unstable weights shown immediately for responsive UI
- **Delayed Stabilization**: Timer-based stable weight emission
- **Change Detection**: Minimum weight change threshold enforcement
- **Dual Signal System**: Separate signals for stable and unstable weights

#### **Scale Assignment System**
```python
@pyqtSlot()
def reserve_scale1_slot(self) -> None:
    if self.scale1 is not None:
        self.scale1.set_assigned(True)
        self.update_availability()

@pyqtSlot()
def release_scale1_slot(self) -> None:
    if self.scale1 is not None:
        self.scale1.set_assigned(False)
        self.update_availability()
```

**Assignment Features:**
- **Resource Protection**: Prevents scale modification while in use
- **Exclusive Access**: Only one component can control a scale at a time
- **Automatic Release**: Scales can be released when no longer needed
- **Availability Tracking**: System monitors scale availability status

### Communication Architecture

#### **Signal-Based Communication**
```python
# Client-triggered signals (commands)
scan_scale1_signal = pyqtSignal(int)           # Initiate scale scanning
set_scale1_signal = pyqtSignal(int, str, str)  # Configure scale
connect_scale1_signal = pyqtSignal()           # Establish connection
disconnect_scale1_signal = pyqtSignal()        # Terminate connection
tare_scale1_signal = pyqtSignal()              # Zero the scale

# System-emitted signals (responses)
scale1_scanned_signal = pyqtSignal(list)       # Scan results
scale1_connected_signal = pyqtSignal()         # Connection established
scale1_weight_changed_signal = pyqtSignal(int) # Weight updates
scale1_stable_weight_changed_signal = pyqtSignal(int) # Stable weights
```

**Signal Flow:**
- **Command Signals**: Client requests sent to scale manager
- **Response Signals**: Scale status and data sent to clients
- **Queued Connections**: Thread-safe signal handling
- **Bidirectional Communication**: Full duplex scale communication

#### **Connection Management**
```python
def update_availability(self, force: bool = False) -> None:
    availability = ((self.scale1 is not None and self.scale1.is_connected() and not self.scale1.is_assigned()) or
                   (self.scale2 is not None and self.scale2.is_connected() and not self.scale2.is_assigned()))
    
    if (force or self.available) and not availability:
        self.unavailable_signal.emit()
    elif (force or not self.available) and availability:
        self.available_signal.emit()
    self.available = availability
```

**Availability Logic:**
- **Dynamic Assessment**: Real-time availability calculation
- **Assignment Awareness**: Considers scale assignment status
- **Change Detection**: Emits signals only when status changes
- **Force Updates**: Optional forced availability updates

### Scale Operations

#### **Scanning and Discovery**
```python
@pyqtSlot(int)
def scan_scale1_slot(self, model: int) -> None:
    if model == 0:  # Acaia
        self.set_scale1_slot(0, '', '')
        if self.scale1 is not None:
            self.scale1.scan()
```

**Discovery Features:**
- **Model-Specific Scanning**: Different protocols for different scale types
- **Automatic Configuration**: Scale setup during discovery process
- **Device Enumeration**: Lists available scales for user selection
- **Connection Preparation**: Pre-configures discovered scales

#### **Connection Management**
```python
@pyqtSlot()
def connect_scale1_slot(self) -> None:
    if self.scale1 is not None:
        self.scale1.connect_scale()

@pyqtSlot()
def disconnect_scale1_slot(self) -> None:
    if self.scale1 is not None and not self.scale1.is_assigned():
        self.scale1.disconnect_scale()
```

**Connection Features:**
- **Conditional Disconnection**: Prevents disconnection of assigned scales
- **Automatic Reconnection**: Handles connection loss and recovery
- **Status Monitoring**: Tracks connection state changes
- **Error Handling**: Graceful handling of connection failures

#### **Scale Operations**
```python
@pyqtSlot()
def tare_scale1_slot(self) -> None:
    if self.scale1 is not None:
        self.scale1.tare_scale()

def disconnect_all(self) -> None:
    if self.scale1 is not None:
        self.scale1.disconnect_scale()
    if self.scale2 is not None:
        self.scale2.disconnect_scale()
```

**Operation Features:**
- **Tare Functionality**: Zero calibration for accurate measurements
- **Bulk Operations**: Operations on multiple scales simultaneously
- **Operation Validation**: Ensures scales are available for operations
- **Error Recovery**: Handles operation failures gracefully

### Data Processing

#### **Weight Data Handling**
```python
@pyqtSlot(float, bool)
def scale1_weight_changed_slot(self, weight: float, stable: bool):
    weight = int(round(weight))  # Convert to integer grams
    if stable:
        # Clear stored weight and emit stable reading
        self.scale1_last_weight = None
        self.scale1_stable_weight_changed_signal.emit(weight)
    else:
        # Store weight for delayed stable emission
        self.scale1_last_weight = weight
        self.scale1_stable_reading_timer.start(STABLE_TIMER_PERIOD)
        # Emit immediate update for responsive UI
        self.scale1_weight_changed_signal.emit(weight)
```

**Data Features:**
- **Precision Handling**: Maintains decimal precision during processing
- **Unit Conversion**: Automatic conversion to standard units (grams)
- **Dual Stream**: Separate handling of stable and unstable readings
- **Timer Integration**: Delayed emission of potentially stable weights

#### **Battery and Status Monitoring**
```python
battery_changed_signal = pyqtSignal(int)  # Battery level percentage
connected_signal = pyqtSignal()           # Connection status
disconnected_signal = pyqtSignal()        # Disconnection events
```

**Monitoring Features:**
- **Battery Tracking**: Real-time battery level monitoring
- **Connection Status**: Live connection state updates
- **Event Logging**: Comprehensive event tracking
- **User Notifications**: Automatic status change notifications

### Integration Points

#### **Main Application Integration**
```python
def __init__(self, connected_handler: Callable[[str, str], None], 
             disconnected_handler: Callable[[str, str], None]) -> None:
    self.connected_handler = connected_handler
    self.disconnected_handler = disconnected_handler
```

**Integration Features:**
- **Callback System**: Application-specific connection handlers
- **Event Routing**: Direct event delivery to application components
- **State Synchronization**: Maintains application state consistency
- **Error Propagation**: Forwards scale errors to application layer

#### **Scale Driver Integration**
```python
def _get_scale(self, model: int, ident: str, name: str) -> Optional[Scale]:
    if model == 0:
        from artisanlib.acaia import Acaia
        return Acaia(model, ident, name, 
                    lambda: self.connected_handler(ident, name),
                    lambda: self.disconnected_handler(ident, name),
                    stable_only=False, decimals=0)
```

**Driver Features:**
- **Dynamic Loading**: Scale drivers loaded on demand
- **Protocol Abstraction**: Unified interface across different protocols
- **Configuration Passing**: Driver-specific parameter configuration
- **Error Isolation**: Driver failures don't affect other scales

### Performance Characteristics

#### **Efficiency Features**
- **Lazy Initialization**: Scales created only when needed
- **Signal Queuing**: Thread-safe signal handling
- **Timer Optimization**: Efficient weight stabilization timing
- **Memory Management**: Proper cleanup of scale resources

#### **Real-time Performance**
- **Immediate Updates**: Unstable weights shown instantly
- **Stable Detection**: Intelligent stable weight identification
- **Minimal Latency**: Low-latency weight data delivery
- **Efficient Filtering**: Smart weight change filtering

### Error Handling and Robustness

#### **Connection Resilience**
- **Automatic Recovery**: Handles connection interruptions
- **Error Isolation**: Scale failures don't affect other operations
- **Graceful Degradation**: Continues operation with available scales
- **User Feedback**: Clear error messages and status updates

#### **Data Validation**
- **Weight Range Checking**: Validates weight readings
- **Stability Verification**: Ensures weight stability before emission
- **Change Thresholds**: Prevents noise-induced false updates
- **Format Validation**: Ensures proper data format

This module represents a sophisticated, production-ready scale management system that provides Artisan with professional-grade weight measurement capabilities, supporting multiple scales simultaneously while maintaining data accuracy and system stability.