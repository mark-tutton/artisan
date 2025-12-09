# Artisan Qt Single Application Module Documentation

## File: `src/artisanlib/qtsingleapplication.py`

### Overview
This module implements a **custom Qt application class** for the Artisan coffee roasting application that ensures only a single instance can run at any time. At 172 lines, it provides a sophisticated single-instance application framework with inter-process communication capabilities, preventing multiple Artisan instances from conflicting with each other.

### Purpose and Architecture
The `qtsingleapplication.py` module serves as the **application lifecycle manager** for Artisan, implementing:
- **Single Instance Enforcement**: Prevents multiple Artisan applications from running simultaneously
- **Inter-Process Communication**: Enables communication between different Artisan instances
- **Instance Activation**: Brings existing instances to foreground when new ones are launched
- **Dual-Mode Support**: Handles both main application and viewer-only instances

### Key Components

#### **Main Class: `QtSingleApplication`**
```python
class QtSingleApplication(QApplication):
    messageReceived = pyqtSignal(str)           # Emits received messages
    activateWindowSignal = pyqtSignal()         # Emits window activation requests
```

**Core Features:**
- **Single Instance Detection**: Automatically detects if another instance is running
- **Local Socket Communication**: Uses QLocalSocket for inter-process messaging
- **Window Management**: Handles window activation and focus management
- **Cross-Platform Compatibility**: PyQt5/PyQt6 dual support

### Technical Implementation

#### **Instance Detection System**
```python
def __init__(self, _id: str, _viewer_id: str, *argv: Any):
    # Attempts to connect to existing instance
    self._outSocket = QLocalSocket()
    self._outSocket.connectToServer(self._id)
    self._isRunning = self._outSocket.waitForConnected(-1)
```

**Detection Logic:**
- **Primary Instance Check**: Attempts to connect to existing application server
- **Viewer Instance Check**: Detects if viewer-only instance is running
- **Server Cleanup**: Removes stale server instances from previous runs
- **Fallback Creation**: Creates new server if no existing instance found

#### **Communication Architecture**

**Server-Side (First Instance):**
```python
# Creates local server for incoming connections
self._server = QLocalServer()
self._server.listen(self._id)
self._server.newConnection.connect(self._onNewConnection)
```

**Client-Side (Subsequent Instances):**
```python
# Connects to existing server for outgoing messages
self._outStream = QTextStream(self._outSocket)
self._outStream << msg << '\n'
```

#### **Message Handling System**
```python
@pyqtSlot()
def _onReadyRead(self):
    while True:
        msg = self._inStream.readLine()
        if not msg:
            break
        self.messageReceived.emit(msg)
```

**Message Flow:**
- **Incoming Messages**: Received through local socket connections
- **Text Stream Processing**: UTF-8 encoded message handling
- **Signal Emission**: Messages emitted via `messageReceived` signal
- **Queue Management**: Handles multiple messages in sequence

### Instance Management

#### **Running State Detection**
```python
def isRunning(self) -> bool:
    return self._isRunning

def isRunningViewer(self) -> bool:
    return self._isRunningViewer
```

**State Management:**
- **Primary Instance**: Main Artisan application instance
- **Viewer Instance**: Secondary instance for viewing/analysis only
- **State Persistence**: Maintains running state throughout application lifecycle

#### **Window Activation System**
```python
def setActivationWindow(self, activationWindow: 'ApplicationWindow', activateOnMessage: bool = True):
    self._activationWindow = activationWindow
    self._activateOnMessage = activateOnMessage

@pyqtSlot()
def activateWindow(self):
    if not self._activationWindow:
        return
    
    self._activationWindow.show()
    self._activationWindow.setWindowState(
        self._activationWindow.windowState() & ~Qt.WindowState.WindowMinimized)
    self._activationWindow.raise_()
    self._activationWindow.activateWindow()
```

**Activation Features:**
- **Window Reference**: Stores reference to main application window
- **State Restoration**: Unminimizes and brings window to foreground
- **Focus Management**: Ensures window receives keyboard focus
- **Queue Connection**: Uses queued connection for thread safety

### Platform-Specific Handling

#### **macOS Background Process Support**
```python
if sys.platform.startswith('darwin') and mp.current_process().name == 'WebLCDs':
    import AppKit
    info = AppKit.NSBundle.mainBundle().infoDictionary()
    info['LSBackgroundOnly'] = '1'
```

**macOS Features:**
- **Background Process Detection**: Identifies WebLCD processes
- **AppKit Integration**: Uses native macOS frameworks
- **Background Mode**: Configures processes for background operation

#### **Cross-Platform Compatibility**
```python
try:
    from PyQt6.QtCore import pyqtSignal, QTextStream, Qt, pyqtSlot
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtNetwork import QLocalSocket, QLocalServer
except ImportError:
    from PyQt5.QtCore import pyqtSignal, QTextStream, Qt, pyqtSlot
    from PyQt5.QtWidgets import QApplication
    from PyQt5.QtNetwork import QLocalSocket, QLocalServer
```

**Compatibility Features:**
- **PyQt6 Support**: Primary target with modern Qt features
- **PyQt5 Fallback**: Maintains compatibility with older installations
- **Import Error Handling**: Graceful degradation on missing modules

### Communication Protocols

#### **Message Sending**
```python
def sendMessage(self, msg: str) -> bool:
    if self._outStream is None or self._outSocket is None:
        return False
    self._outStream << msg << '\n'
    self._outStream.flush()
    return self._outSocket.waitForBytesWritten()
```

**Message Features:**
- **Text-Based Protocol**: Simple string message format
- **Newline Termination**: Messages end with newline character
- **Flush Guarantee**: Ensures immediate message transmission
- **Success Verification**: Confirms message was written to socket

#### **Connection Management**
```python
@pyqtSlot()
def _onNewConnection(self):
    if self._inSocket is not None:
        self._inSocket.readyRead.disconnect(self._onReadyRead)
    
    self._inSocket = self._server.nextPendingConnection()
    self._inStream = QTextStream(self._inSocket)
    
    if self._inSocket is not None:
        self._inSocket.readyRead.connect(self._onReadyRead)
    
    if self._activateOnMessage and self._isRunning:
        self.activateWindow()
```

**Connection Features:**
- **Dynamic Connection Handling**: Manages incoming connections
- **Event Disconnection**: Prevents multiple signal connections
- **Stream Setup**: Initializes text streams for new connections
- **Auto-Activation**: Automatically activates window on new connections

### Integration with Artisan

#### **Application Lifecycle**
This module is critical for Artisan's startup process:
- **Instance Validation**: Ensures only one Artisan instance runs
- **Resource Protection**: Prevents conflicts between multiple instances
- **User Experience**: Brings existing instance to foreground
- **Communication Bridge**: Enables inter-instance messaging

#### **Use Cases in Artisan**
Common scenarios where this module is used:
- **File Association**: Opening roast files from file manager
- **Command Line Arguments**: Processing command line parameters
- **Instance Coordination**: Managing multiple Artisan windows
- **Plugin Communication**: Enabling plugin-to-plugin messaging

### Error Handling and Robustness

#### **Socket Management**
- **Stale Server Cleanup**: Removes abandoned server instances
- **Connection Validation**: Verifies socket connections before use
- **Resource Cleanup**: Proper disposal of socket resources
- **Exception Handling**: Graceful handling of communication errors

#### **State Consistency**
- **Running State Validation**: Ensures consistent instance state
- **Window Reference Management**: Maintains valid window references
- **Signal Connection Safety**: Prevents duplicate signal connections
- **Resource Lifecycle**: Proper cleanup of Qt resources

### Performance Characteristics

#### **Efficiency Features**
- **Local Socket Communication**: Fast inter-process communication
- **Minimal Resource Usage**: Lightweight socket management
- **Efficient Message Processing**: Stream-based message handling
- **Quick Instance Detection**: Fast startup time validation

#### **Scalability Considerations**
- **Single Instance Limitation**: Designed for single-user scenarios
- **Message Queue Management**: Handles message bursts efficiently
- **Connection Pooling**: Manages multiple incoming connections
- **Memory Footprint**: Minimal memory overhead per instance

### Security and Isolation

#### **Local Communication**
- **Unix Domain Sockets**: Secure local-only communication
- **Process Isolation**: No network exposure or external access
- **User-Scoped**: Communication limited to user's processes
- **No Authentication**: Relies on OS-level process isolation

#### **Resource Protection**
- **Socket Cleanup**: Prevents resource leaks
- **Process Validation**: Ensures legitimate Artisan instances
- **Message Validation**: Handles malformed messages gracefully
- **State Protection**: Maintains application integrity

This module represents a sophisticated solution to the common problem of single-instance applications, providing Artisan with robust instance management, inter-process communication, and seamless user experience when multiple instances are attempted.