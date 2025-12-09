# Artisan Main Application Module Documentation

## File: `src/artisanlib/main.py`

### Overview
This is the **core application module** for Artisan, a professional coffee roasting application. At 27,602 lines, it represents the largest and most complex file in the codebase, containing the main application window, event handling, device communication, and the complete roasting workflow management system.

### Purpose and Architecture
The `main.py` file serves as the **central nervous system** of the Artisan application, implementing:
- **Main Application Window** (`ApplicationWindow` class)
- **Device Communication Layer** (serial, MODBUS, WebSocket, etc.)
- **Roasting Workflow Management**
- **Plugin System Integration**
- **Settings and Configuration Management**
- **Event Handling and Signal Processing**

### File Structure and Organization

#### **Header Section (Lines 1-100)**
```python
# ABOUT
# This program shows how to plot the temperature and its rate of change from a
# Fuji PID or a thermocouple meter.

# LICENSE
# GNU General Public License v2/v3
# MAINTAINER: Marko Luther, 2023
```

**Key Imports:**
- **Core Libraries**: `numpy`, `PyQt6/PyQt5`, `asyncio`, `threading`
- **Specialized**: `arabic_reshaper`, `bidi` (bidirectional text support)
- **Hardware**: `requests`, `zlib`, `logging`
- **Platform Support**: `platform`, `signal`, `appnope` (macOS)

#### **Class Definitions (Lines 281-1444)**

**1. `Artisan` Class (Line 281)**
- **Purpose**: Main application instance management
- **Responsibilities**: Single instance enforcement, message handling
- **Key Methods**: `isRunning()`, `sendMessage()`, `open_url()`

**2. `EventActionThread` Class (Line 687)**
- **Purpose**: Background thread for event processing
- **Responsibilities**: Asynchronous event execution, thread safety
- **Key Methods**: `run()`, `execute_action()`

**3. `EventButton` Class (Line 804)**
- **Purpose**: Custom event button widget
- **Responsibilities**: Event triggering, visual feedback
- **Key Methods**: `mousePressEvent()`, `updateStyle()`

**4. `EventAction` Class (Line 1402)**
- **Purpose**: Event action definition and execution
- **Responsibilities**: Action parameters, execution logic
- **Key Methods**: `execute()`, `validate()`

**5. `RangeValidator` Class (Line 1420)**
- **Purpose**: Input validation for numeric ranges
- **Responsibilities**: Range checking, user feedback
- **Key Methods**: `validate()`, `fixup()`

#### **Main Application Window (Lines 1449-27602)**

**`ApplicationWindow` Class - The Heart of Artisan**

**Class Hierarchy:**
```python
class ApplicationWindow(QMainWindow):
    # Inherits from PyQt's QMainWindow
    # Implements custom roasting application logic
```

**Key Attributes (__slots__):**
```python
__slots__ = [
    # Core Application State
    'locale_str', 'app', 'superusermode', 'sample_loop_running',
    
    # Plus Account Management
    'plus_account', 'plus_subscription', 'plus_paidUntil',
    
    # UI Components
    'main_widget', 'redrawTimer', 'helpdialog',
    
    # Device Communication
    'ser', 'modbus', 's7', 'ws', 'scale', 'color',
    
    # Roasting Data
    'qmc', 'eventsbuttonflag', 'minieventsflags',
    
    # Configuration
    'settingspath', 'profilepath', 'userprofilepath',
    
    # Plugin System
    'plugin_manager', 'live_broadcast_plugin'
]
```

### Core Functionality

#### **1. Application Initialization**

**Constructor (`__init__` method):**
```python
def __init__(self, parent:Optional[QWidget] = None, *, 
             locale:str, WebEngineSupport:bool, 
             artisanviewerFirstStart:bool) -> None:
```

**Initialization Sequence:**
1. **Default Settings**: Initialize configuration defaults
2. **Locale Setup**: Set application language and regional settings
3. **Plus Account**: Initialize premium features
4. **UI Components**: Create main interface elements
5. **Device Managers**: Initialize communication layers
6. **Plugin System**: Load and register plugins

#### **2. Device Communication Layer**

**Serial Communication:**
```python
self.ser = serialport(self)  # Main serial device
self.extraser = []           # Additional serial ports
```

**Protocol Support:**
- **MODBUS**: Industrial automation protocol
- **S7**: Siemens PLC communication
- **WebSocket**: Real-time data streaming
- **Custom Protocols**: Device-specific implementations

**Scale Integration:**
```python
self.scale_manager = ScaleManager(self.scale_connected_handler, 
                                 self.scale_disconnected_handler)
```

#### **3. Roasting Workflow Management**

**State Management:**
```python
self.sample_loop_running: bool = True
self.time_stopped: float = 0
```

**Event System:**
```python
# Event buttons and actions
self.buttonCHARGE = QPushButton()
self.buttonDROP = QPushButton()
self.buttonFCs = QPushButton()  # First Crack Start
self.buttonFCe = QPushButton()  # First Crack End
```

**Data Collection:**
```python
# LCD displays for real-time data
self.lcd1 = QLCDNumber()  # Main temperature
self.lcd2 = QLCDNumber()  # Secondary temperature
self.lcd3 = QLCDNumber()  # Rate of rise
```

#### **4. Plugin System Integration**

**Plugin Initialization:**
```python
def initialize_plugins(self):
    """Initialize and register plugins"""
    from artisanlib.plugins.live_broadcast_plugin import LiveBroadcastPlugin
    from artisanlib.plugins.inventory_fetcher import InventoryFetcherPlugin
    
    # Register plugins
    self.plugin_manager.register_plugin(LiveBroadcastPlugin)
    self.plugin_manager.register_plugin(InventoryFetcherPlugin)
```

**Plugin Management:**
- **Dynamic Loading**: Plugins loaded at runtime
- **Interface Standardization**: Common plugin interface
- **Configuration Integration**: Plugin settings in main app

#### **5. Settings and Configuration**

**Settings Loading:**
```python
def settingsLoad(self, filename:Optional[str] = None, 
                theme:bool = False, machine:bool = False, 
                redraw:bool = True) -> bool:
```

**Configuration Categories:**
- **Application Settings**: General app behavior
- **Machine Profiles**: Roaster-specific configurations
- **Theme Settings**: Visual appearance and styling
- **Device Settings**: Communication and hardware parameters

### Signal and Slot Architecture

#### **Custom Signals**
```python
# Device communication signals
singleShotPhidgetsPulseOFF = pyqtSignal(int, int, str)
updatePlusStatusSignal = pyqtSignal()

# UI update signals
setTitleSignal = pyqtSignal(str, bool)
sendmessageSignal = pyqtSignal(str, bool, str)

# Roasting control signals
pidOnSignal = pyqtSignal()
pidOffSignal = pyqtSignal()
addEventSignal = pyqtSignal(int, int, bool, bool, bool)
```

#### **Signal Flow**
1. **Device Events** → **Signal Emission** → **UI Updates**
2. **User Actions** → **Signal Emission** → **Device Control**
3. **Plugin Events** → **Signal Emission** → **Application Response**

### Event Handling System

#### **Event Types**
- **Roasting Events**: CHARGE, DRY END, FC START, FC END, SC START, SC END, DROP, COOL END
- **Custom Events**: User-defined event types
- **System Events**: Application lifecycle, device state changes

#### **Event Processing**
```python
def addEvent(self, event_type: int, event_time: int, 
             is_manual: bool, is_auto: bool, is_custom: bool):
    # Event recording and processing logic
```

### Performance and Optimization

#### **Memory Management**
- **__slots__**: Optimized attribute storage
- **Signal Queuing**: Efficient event propagation
- **Timer Management**: Controlled update frequency

#### **Threading Model**
- **Main Thread**: UI and user interaction
- **Device Threads**: Asynchronous communication
- **Event Threads**: Background event processing

### Platform Support

#### **Cross-Platform Features**
- **Windows**: High DPI support, Fusion style
- **macOS**: App nap prevention, native integration
- **Linux**: Platform-specific optimizations

#### **Hardware Abstraction**
- **Device Drivers**: Platform-independent communication
- **Scale Integration**: Universal scale support
- **Protocol Support**: Multiple communication standards

### Integration Points

#### **External Systems**
- **Artisan Plus**: Cloud-based features and collaboration
- **Plugin Ecosystem**: Extensible functionality
- **Import/Export**: Multiple file format support

#### **File Formats**
- **.alog**: Artisan log files
- **.alrm**: Alarm configurations
- **.apal**: Palette definitions
- **.aset**: Application settings
- **.athm**: Theme configurations

### Error Handling and Logging

#### **Exception Management**
```python
try:
    # Critical operations
except Exception as e:
    _log.error(f"Operation failed: {e}")
    # Graceful degradation
```

#### **Logging System**
- **Structured Logging**: Categorized log messages
- **Debug Support**: Configurable log levels
- **Performance Monitoring**: Operation timing

### Security Considerations

#### **User Permissions**
- **Superuser Mode**: Administrative functions
- **Account Management**: Plus account security
- **Plugin Security**: Sandboxed plugin execution

#### **Data Protection**
- **Credential Storage**: System keychain integration
- **File Access**: Controlled file operations
- **Network Security**: Secure communication protocols

### Development and Maintenance

#### **Code Organization**
- **Modular Structure**: Logical separation of concerns
- **Documentation**: Comprehensive inline comments
- **Type Hints**: Python type annotation support

#### **Testing Support**
- **Unit Testing**: Individual component testing
- **Integration Testing**: End-to-end workflow testing
- **Performance Testing**: Resource usage monitoring

### Conclusion

The `main.py` file represents the **architectural foundation** of the Artisan application. It demonstrates a sophisticated, production-ready coffee roasting application with:

- **Comprehensive device support** for various roasting equipment
- **Robust event handling** for complex roasting workflows
- **Extensible plugin architecture** for feature expansion
- **Cross-platform compatibility** for diverse user environments
- **Professional-grade error handling** and user experience

This module serves as a **reference implementation** for complex, real-time applications that require hardware integration, user interface management, and extensible architecture. The combination of PyQt for the UI, comprehensive device communication, and plugin-based extensibility creates a powerful platform for coffee roasting professionals.