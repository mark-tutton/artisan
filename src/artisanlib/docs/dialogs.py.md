# Artisan Dialogs Module Documentation

## File: `src/artisanlib/dialogs.py`

### Overview
This module implements the **foundational dialog system** for the Artisan coffee roasting application. At 751 lines, it provides a comprehensive set of base dialog classes, specialized input dialogs, and utility components that form the backbone of Artisan's user interface system.

### Purpose and Architecture
The `dialogs.py` module serves as the **UI foundation layer** for Artisan, implementing:
- **Base Dialog Classes**: Standardized dialog behavior and styling
- **Specialized Input Dialogs**: Port selection, text input, and combo box dialogs
- **Help System**: Comprehensive help dialog with search functionality
- **Port Management**: Serial port detection and selection utilities
- **Container Management**: Tare weight and container configuration dialogs

### Core Classes

#### `ArtisanDialog` Class
**Purpose**: Base dialog class that provides standardized behavior for all Artisan dialogs.

**Key Features**:
- **Standard Button Layout**: Consistent OK/Cancel button configuration
- **Keyboard Shortcuts**: ESC key and CMD-W (macOS) support for closing
- **Memory Management**: Automatic cleanup with `WA_DeleteOnClose` attribute
- **Cross-Platform Compatibility**: Platform-specific window flag handling

**Key Methods**:
- `setButtonTranslations()`: Apply localized button text
- `cancelDialog()`: Handle dialog cancellation
- `closeEvent()`: Standardized close event handling
- `keyPressEvent()`: Keyboard shortcut processing

**Technical Implementation**:
```python
# Standard button configuration
self.dialogbuttons = QDialogButtonBox(
    QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
    Qt.Orientation.Horizontal
)

# Platform-specific window flags
if str(platform.system()) == 'Windows':
    windowFlags |= Qt.WindowType.WindowMinMaxButtonsHint
```

#### `ArtisanResizeablDialog` Class
**Purpose**: Extends `ArtisanDialog` with resizable window capabilities.

**Key Features**:
- **Windows Optimization**: Enables minimize/maximize buttons on Windows
- **Responsive Layout**: Supports dynamic window resizing
- **Platform Adaptation**: Tailored behavior for different operating systems

#### `ArtisanMessageBox` Class
**Purpose**: Custom message box with timeout functionality.

**Key Features**:
- **Auto-dismiss**: Configurable timeout for automatic closure
- **Modal Control**: Optional modal behavior for user interaction
- **Timer Integration**: Built-in countdown timer for timeout management

**Technical Implementation**:
```python
def timerEvent(self, _:Optional['QTimerEvent']) -> None:
    self.currentTime = self.currentTime + 1
    if self.currentTime >= self.timeout:
        self.done(0)
```

#### `HelpDlg` Class
**Purpose**: Comprehensive help dialog with advanced search and navigation capabilities.

**Key Features**:
- **HTML Content Support**: Rich text formatting and display
- **Search Functionality**: Real-time text search with highlighting
- **Navigation**: Keyboard shortcuts and result cycling
- **Geometry Persistence**: Remembers window position and size

**Search Implementation**:
- **Case-Insensitive Search**: Regular expression-based text matching
- **Result Highlighting**: Current match and additional matches differentiation
- **Keyboard Navigation**: Ctrl+F focus, Enter navigation, ESC closure
- **Visual Feedback**: Color-coded search results with dark mode support

**Technical Implementation**:
```python
# Search result highlighting
for i, matchCursor in enumerate(self.matches):
    selection = QTextEdit.ExtraSelection()
    selection.cursor = matchCursor
    fmt = QTextCharFormat()
    if i == self.current_match_index:
        fmt.setBackground(QColor(current_match_highlight))
    else:
        fmt.setBackground(QColor(extra_matches_highlight))
```

#### `ArtisanInputDialog` Class
**Purpose**: Simple text input dialog with drag-and-drop support.

**Key Features**:
- **Text Input**: Single-line text entry with validation
- **Drag-and-Drop**: File/URL dropping support
- **Modal Operation**: Blocking dialog behavior
- **Memory Management**: Controlled cleanup with `WA_DeleteOnClose=False`

**Drag-and-Drop Implementation**:
```python
def dropEvent(self, event:Optional['QDropEvent']) -> None:
    if event is not None:
        mimeData = event.mimeData()
        if mimeData is not None and mimeData.hasUrls():
            urls = mimeData.urls()
            if urls and len(urls)>0:
                self.inputLine.setText(urls[0].toString())
```

#### `ArtisanComboBoxDialog` Class
**Purpose**: Selection dialog with combo box interface.

**Key Features**:
- **Choice Selection**: Dropdown list of predefined options
- **Default Values**: Configurable initial selection
- **Modal Operation**: User must make selection before proceeding
- **Index Return**: Returns selected item index for processing

#### `PortComboBox` Class
**Purpose**: Specialized combo box for serial port selection with real-time port detection.

**Key Features**:
- **Port Detection**: Automatic serial port discovery
- **Device Filtering**: Platform-specific port filtering (macOS Bluetooth exclusion)
- **Editable Interface**: User can type custom port names
- **Real-time Updates**: Port list refresh on focus events

**Port Detection Implementation**:
```python
def updateMenu(self) -> None:
    import serial.tools.list_ports
    comports = [(cp.device, cp.product, 'n/a') for cp in serial.tools.list_ports.comports()]
    
    # macOS-specific filtering
    if platform.system() == 'Darwin':
        self.ports = [p for p in comports if (p[0] not in [
            '/dev/cu.Bluetooth-PDA-Sync', '/dev/cu.debug-console', 
            '/dev/cu.wlan-debug', '/dev/cu.Bluetooth-Modem'
        ])]
```

**Platform-Specific Behavior**:
- **macOS**: Excludes Bluetooth and debug ports
- **Windows/Linux**: Includes all detected serial ports
- **Port Sorting**: Alphabetical ordering for consistent display

#### `ArtisanPortsDialog` Class
**Purpose**: Dialog wrapper for port selection using `PortComboBox`.

**Key Features**:
- **Port Selection**: Integrated port combo box interface
- **Modal Operation**: Blocking dialog until port selection
- **Selection Return**: Returns selected port name for configuration

#### `ArtisanSliderLCDinputDlg` Class
**Purpose**: Numeric input dialog with validation and range constraints.

**Key Features**:
- **Value Validation**: Integer input with min/max range checking
- **Focus Management**: Automatic focus and text selection
- **Fixed Layout**: Consistent dialog sizing
- **Input Validation**: Real-time value range enforcement

#### `tareDlg` Class
**Purpose**: Container tare weight management dialog for scale calibration.

**Key Features**:
- **Container Management**: Add/remove container definitions
- **Weight Input**: Editable weight values with unit conversion
- **Scale Integration**: Real-time scale weight reading
- **Data Persistence**: Save/load container configurations

**Key Methods**:
- `addTare()`: Add new container with current scale weight
- `delTare()`: Remove selected container
- `saveTareTable()`: Persist container data to application state
- `weightEdited()`: Handle weight input validation and conversion

**Weight Unit Support**:
- **Grams (g)**: Integer input with 0-9999 range
- **Kilograms (Kg)**: Decimal input with automatic g/Kg detection
- **Pounds (lb)**: Decimal input with unit conversion
- **Automatic Conversion**: Seamless unit conversion between systems

**Technical Implementation**:
```python
def setTableRow(self, row:int, name:str, weight:float) -> None:
    # Weight unit-specific validation and display
    if self.aw.qmc.weight[2] == 'g':
        weight_widget.setText(str(int(round(weight))))
        weight_widget.setValidator(QIntValidator(0,9999, weight_widget))
    elif self.aw.qmc.weight[2] == 'Kg':
        w = convertWeight(weight,0,weight_units.index(self.aw.qmc.weight[2]))
        weight_widget.setText(f'{float2floatWeightVolume(w):g}')
```

### Technical Implementation

#### Memory Management
**Dialog Lifecycle**:
- **Automatic Cleanup**: `WA_DeleteOnClose` attribute for most dialogs
- **Controlled Cleanup**: Manual memory management for persistent dialogs
- **Signal Management**: Proper signal disconnection and cleanup

**Resource Handling**:
- **Widget Cleanup**: Automatic widget disposal
- **Signal Cleanup**: Proper signal-slot disconnection
- **Memory Leak Prevention**: Controlled object lifecycle management

#### Cross-Platform Compatibility
**Platform Detection**:
```python
if str(platform.system()) == 'Windows':
    # Windows-specific window flags
elif str(platform.system()) == 'Darwin':
    # macOS-specific port filtering
```

**UI Adaptation**:
- **Window Flags**: Platform-appropriate window behavior
- **Port Filtering**: OS-specific serial port handling
- **Keyboard Shortcuts**: Platform-appropriate key combinations

#### Input Validation
**Data Validation**:
- **Range Checking**: Min/max value enforcement
- **Type Validation**: Input type verification
- **Format Validation**: Text format and structure checking

**User Feedback**:
- **Visual Indicators**: Input state visualization
- **Error Messages**: Clear validation feedback
- **Auto-correction**: Automatic input adjustment

### Integration Points

#### Main Application Integration
- **Application Window Reference**: Direct access to main application state
- **Settings Integration**: QSettings for configuration persistence
- **Signal Communication**: Dialog result communication with main app

#### Plugin System Integration
- **Dialog Factory**: Standardized dialog creation patterns
- **Configuration Management**: Consistent settings handling
- **Event Propagation**: Proper event flow through dialog hierarchy

### Usage Patterns

#### Dialog Creation
```python
# Standard dialog creation
dialog = ArtisanDialog(parent, self.aw)
dialog.setWindowTitle("Configuration")
dialog.exec()

# Specialized dialog creation
port_dialog = ArtisanPortsDialog(self, self.aw)
selected_port = port_dialog.getSelection()
```

#### Configuration Persistence
```python
# Save dialog geometry
settings = QSettings()
settings.setValue('DialogGeometry', self.saveGeometry())

# Restore dialog geometry
if settings.contains('DialogGeometry'):
    self.restoreGeometry(settings.value('DialogGeometry'))
```

#### Event Handling
```python
# Standard close event handling
def closeEvent(self, event):
    self.dialogbuttons.rejected.emit()

# Custom event filtering
def eventFilter(self, obj, event):
    if event.type() == QEvent.Type.MouseButtonPress:
        self.updateMenu()
    return super().eventFilter(obj, event)
```

### Advanced Features

#### Search and Navigation
**Help System Features**:
- **Real-time Search**: Instant search results as you type
- **Result Highlighting**: Visual distinction of search matches
- **Navigation Shortcuts**: Keyboard-based result cycling
- **Search Persistence**: Maintains search state across interactions

#### Port Management
**Serial Port Features**:
- **Dynamic Detection**: Real-time port availability updates
- **Smart Filtering**: Platform-appropriate port exclusion
- **User Customization**: Manual port name entry
- **Device Integration**: Scale and sensor port management

#### Container Management
**Tare System Features**:
- **Multi-unit Support**: Grams, kilograms, pounds
- **Scale Integration**: Real-time weight reading
- **Container Library**: Persistent container definitions
- **Weight Validation**: Range checking and unit conversion

### Security and Safety

#### Input Validation
**Safety Measures**:
- **Range Enforcement**: Prevents invalid value entry
- **Type Checking**: Ensures data type consistency
- **Format Validation**: Maintains data integrity

#### Memory Safety
**Resource Management**:
- **Automatic Cleanup**: Prevents memory leaks
- **Signal Management**: Proper event handling
- **Widget Disposal**: Controlled object lifecycle

This module represents the **foundational UI infrastructure** for Artisan, providing a robust, cross-platform dialog system that supports the application's complex configuration and user interaction requirements while maintaining consistency, usability, and performance across different operating systems and use cases.