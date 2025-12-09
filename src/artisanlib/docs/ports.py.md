# Artisan Communication Ports Dialog Module Documentation

## File: `src/artisanlib/ports.py`

### Overview
This module implements the **comprehensive Communication Ports Configuration Dialog** for the Artisan coffee roasting application. At 1,934 lines, it provides sophisticated interfaces for configuring all communication protocols including serial ports, MODBUS, S7, WebSocket, scales, and color meters through a unified tabbed interface system.

### Purpose and Architecture
The `ports.py` module serves as the **central communication configuration hub** for Artisan, implementing:
- **Multi-Protocol Support**: Serial, MODBUS, S7, WebSocket, and device-specific protocols
- **Unified Configuration Interface**: Tabbed dialog for all communication settings
- **Device Management**: Configuration for temperature sensors, scales, color meters, and extra devices
- **Protocol Scanning**: Built-in tools for discovering and testing device communication
- **Advanced Settings**: PID control integration, optimization options, and error handling

### Core Components

#### **1. Main Ports Configuration Dialog (`comportDlg`)**
- **Tabbed Interface**: 7 tabs for different communication protocols
- **Resizable Dialog**: Flexible layout with geometry persistence
- **Settings Management**: QSettings integration for configuration storage
- **Help System**: Context-sensitive help for different protocols

#### **2. MODBUS Scanner Dialog (`scanModbusDlg`)**
- **Register Scanning**: Function code 3 and 4 register discovery
- **Slave Configuration**: Configurable slave ID and register ranges
- **Real-Time Results**: Live HTML display of scan results
- **Interruptible Operation**: Keyboard interrupt support for long scans

#### **3. S7 Scanner Dialog (`scanS7Dlg`)**
- **Area Scanning**: PE, PA, MK, CT, TM, DB area exploration
- **Data Type Support**: Integer and float data type detection
- **Network Configuration**: Host, port, rack, and slot settings
- **Progressive Results**: Real-time scan result display

### Key Features

#### **1. Multi-Protocol Communication Support**
```python
# Tabbed interface for different protocols
self.TabWidget = QTabWidget()
self.TabWidget.addTab(C1Widget, 'ET/BT')           # Serial communication
self.TabWidget.addTab(C2Widget, 'Extra')           # Extra devices
self.TabWidget.addTab(C3Widget, 'Modbus')          # MODBUS protocol
self.TabWidget.addTab(C4Widget, 'S7')              # Siemens S7 protocol
self.TabWidget.addTab(C5Widget, 'Scale')           # Scale devices
self.TabWidget.addTab(C6Widget, 'Color')           # Color meters
self.TabWidget.addTab(C7Widget, 'WebSocket')       # WebSocket protocol
```

#### **2. Advanced Serial Port Configuration**
```python
# Comprehensive serial settings
self.bauds = ['1200', '2400', '4800', '9600', '19200', '38400', '57600', '57800', '115200']
self.bytesizes = ['7', '8']
self.parity = ['O', 'E', 'N']  # Odd, Even, None
self.stopbits = ['1', '2']
self.timeoutEdit.setValidator(self.aw.createCLocaleDoubleValidator(0, 5, 1, self.timeoutEdit))
```

#### **3. MODBUS Protocol Configuration**
```python
# MODBUS input channel configuration
for i in range(self.aw.modbus.channels):
    # Slave ID, Register, Function Code, Divider, Mode, Decode
    modbus_inputSlaveEdit = QLineEdit(str(self.aw.modbus.inputSlaves[i]))
    modbus_inputRegisterEdit = QLineEdit(str(self.aw.modbus.inputRegisters[i]))
    modbus_inputCode = QComboBox()  # Function codes 1,2,3,4
    modbus_inputDiv = QComboBox()   # Dividers: '', '1/10', '1/100'
    modbus_inputMode = QComboBox()  # Modes: '', 'C', 'F'
    modbus_inputDecode = QComboBox() # Decode: uInt16, uInt32, sInt16, sInt32, BCD16, BCD32, Float32
```

#### **4. S7 Protocol Support**
```python
# S7 area and data type configuration
s7_areas = [' ', 'PE', 'PA', 'MK', 'CT', 'TM', 'DB']
s7_types = ['Int', 'Float', 'IntFloat', 'Bool(0)', 'Bool(1)', 'Bool(2)', 'Bool(3)', 'Bool(4)', 'Bool(5)', 'Bool(6)', 'Bool(7)']

for i in range(self.aw.s7.channels):
    area = QComboBox()      # Area selection
    dbEdit = QLineEdit()    # DB number (1-16000)
    startEdit = QLineEdit() # Start address (0-65536)
    tp = QComboBox()        # Data type
    div = QComboBox()       # Divisor
    mode = QComboBox()      # Mode (Celsius/Fahrenheit)
```

#### **5. WebSocket Configuration**
```python
# WebSocket machine and node configuration
ws_setup = QHBoxLayout()
ws_setup.addWidget(ws_hostlabel)      # Host/IP address
ws_setup.addWidget(self.ws_hostEdit)
ws_setup.addWidget(ws_portlabel)      # Port number
ws_setup.addWidget(self.ws_portEdit)
ws_setup.addWidget(ws_pathlabel)      # Path
ws_setup.addWidget(self.ws_pathEdit)
ws_setup.addWidget(ws_machineIDlabel) # Machine ID
ws_setup.addWidget(self.ws_machineIDEdit)
```

### Technical Architecture

#### **Dialog Inheritance Hierarchy**
```python
class scanModbusDlg(ArtisanDialog):
    # MODBUS scanning functionality
    
class scanS7Dlg(ArtisanDialog):
    # S7 scanning functionality
    
class comportDlg(ArtisanResizeablDialog):
    # Main ports configuration dialog
    # Extends ArtisanResizeablDialog for flexible sizing
```

#### **Dynamic UI Generation**
```python
def createserialTable(self) -> None:
    # Dynamic table creation for extra devices
    nssdevices = min(len(self.aw.extracomport), len(self.aw.qmc.extradevices))
    if nssdevices:
        self.serialtable.setRowCount(nssdevices)
        self.serialtable.setColumnCount(7)
        
        for i in range(nssdevices):
            # Create PortComboBox, QComboBox, and QLineEdit widgets
            # for each extra device dynamically
```

#### **Settings Persistence System**
```python
# QSettings integration for configuration storage
settings = QSettings()
if settings.contains('PortsGeometry'):
    self.restoreGeometry(settings.value('PortsGeometry'))

def closeEvent(self, _: Optional['QCloseEvent'] = None) -> None:
    settings = QSettings()
    settings.setValue('PortsGeometry', self.saveGeometry())
```

### Advanced Features

#### **1. PID Control Integration**
```python
# MODBUS PID configuration
modbus_pid_registers = QHBoxLayout()
modbus_pid_registers.addWidget(modbus_SVregister_label)  # Set Value register
modbus_pid_registers.addWidget(self.modbus_SVregister_Edit)
modbus_pid_registers.addWidget(modbus_Pregister_label)   # Proportional register
modbus_pid_registers.addWidget(self.modbus_Pregister_Edit)
modbus_pid_registers.addWidget(modbus_Iregister_label)   # Integral register
modbus_pid_registers.addWidget(self.modbus_Iregister_Edit)
modbus_pid_registers.addWidget(modbus_Dregister_label)   # Derivative register
modbus_pid_registers.addWidget(self.modbus_Dregister_Edit)
```

#### **2. Protocol Optimization**
```python
# MODBUS optimization settings
self.modbus_optimize = QCheckBox('optimize')
self.modbus_optimize.setChecked(self.aw.modbus.optimizer)
self.modbus_full_block = QCheckBox('fetch full blocks')
self.modbus_full_block.setChecked(self.aw.modbus.fetch_max_blocks)
self.modbus_full_block.setEnabled(bool(self.aw.modbus.optimizer))
```

#### **3. Device-Specific Configuration**
```python
# Scale device configuration
self.scale_deviceEdit = QComboBox()
self.supported_scales = list(self.aw.scale.devicefunctionlist.keys())
self.scale_deviceEdit.addItems(self.supported_scales)

# Color meter configuration
self.color_deviceEdit = QComboBox()
supported_color_meters = list(self.aw.color.devicefunctionlist.keys())
self.color_deviceEdit.addItems(supported_color_meters)
```

#### **4. Bluetooth Permission Handling**
```python
@pyqtSlot(int)
def scaleDeviceIndexChanged(self, i: int) -> None:
    if self.supported_scales[i] in self.aw.scale.bluetooth_devices:
        permission_status: Optional[bool] = self.aw.app.getBluetoothPermission(request=True)
        if permission_status is False:
            message: str = QApplication.translate('Message', 'Bluetooth access denied')
            QMessageBox.warning(None, message, message)
```

### User Interface Architecture

#### **Tabbed Interface Design**
```
┌─────────────────────────────────────────────────────────────┐
│                    Ports Configuration                      │
├─────────────────────────────────────────────────────────────┤
│ [ET/BT] [Extra] [Modbus] [S7] [Scale] [Color] [WebSocket] │
├─────────────────────────────────────────────────────────────┤
│ ET/BT Tab:                                                 │
│ • Communication Port Selection                             │
│ • Baud Rate Configuration                                  │
│ • Data Format Settings (Parity, Stop Bits, etc.)          │
│ • Timeout Configuration                                    │
├─────────────────────────────────────────────────────────────┤
│ Extra Tab:                                                 │
│ • Dynamic Table for Additional Devices                     │
│ • Per-Device Serial Configuration                          │
│ • Device Type Identification                               │
├─────────────────────────────────────────────────────────────┤
│ Modbus Tab:                                                │
│ • Serial/Network Configuration                             │
│ • Input Channel Setup (8 channels)                        │
│ • PID Control Integration                                  │
│ • Optimization Settings                                    │
├─────────────────────────────────────────────────────────────┤
│ S7 Tab:                                                    │
│ • Network Configuration (Host, Port, Rack, Slot)           │
│ • Area and Data Type Configuration                         │
│ • PID Control Integration                                  │
│ • Optimization Settings                                    │
├─────────────────────────────────────────────────────────────┤
│ Scale Tab:                                                 │
│ • Scale Device Selection                                   │
│ • Serial Port Configuration                                │
│ • Device-Specific Settings                                │
├─────────────────────────────────────────────────────────────┤
│ Color Tab:                                                 │
│ • Color Meter Device Selection                             │
│ • Serial Port Configuration                                │
│ • Device-Specific Settings                                │
├─────────────────────────────────────────────────────────────┤
│ WebSocket Tab:                                             │
│ • Machine Configuration (Host, Port, Path, ID)             │
│ • Node Configuration                                       │
│ • Event Message Configuration                               │
│ • Channel Configuration                                    │
└─────────────────────────────────────────────────────────────┘
```

#### **Dynamic Table Generation**
```python
# Extra devices table with embedded controls
def createserialTable(self) -> None:
    for i in range(nssdevices):
        # Device name (non-editable)
        device = QTableWidgetItem(devname)
        self.serialtable.setItem(i, 0, device)
        
        # Communication port (PortComboBox)
        comportComboBox = PortComboBox(selection=self.aw.extracomport[i])
        self.serialtable.setCellWidget(i, 1, comportComboBox)
        
        # Baud rate (QComboBox)
        baudComboBox = QComboBox()
        baudComboBox.addItems(self.bauds)
        self.serialtable.setCellWidget(i, 2, baudComboBox)
        
        # Additional serial parameters...
```

### Integration Points

#### **Main Application Integration**
- **Device Management**: Integration with device detection and configuration
- **Serial Port Management**: Unified serial port handling
- **Settings System**: QSettings integration for persistence
- **Help System**: Context-sensitive help integration

#### **Protocol System Integration**
- **MODBUS**: Full MODBUS RTU/ASCII/TCP/UDP support
- **S7**: Siemens S7 protocol integration
- **WebSocket**: WebSocket client configuration
- **Serial**: Comprehensive serial communication support

### Error Handling and Validation

#### **Input Validation**
```python
def accept(self) -> None:
    # Serial parameter validation
    class comportError(Exception):
        pass
    class timeoutError(Exception):
        pass
    
    try:
        if not comport:
            raise comportError
        if not timeout:
            raise timeoutError
        # Additional validation...
    except comportError:
        self.aw.qmc.adderror('Serial Exception: invalid comm port')
        self.comportEdit.setFocus()
        return
    except timeoutError:
        self.aw.qmc.adderror('Serial Exception: timeout')
        self.timeoutEdit.selectAll()
        self.timeoutEdit.setFocus()
        return
```

#### **Exception Handling**
```python
def createserialTable(self) -> None:
    try:
        # Table creation logic
        pass
    except Exception as e:
        _, _, exc_tb = sys.exc_info()
        self.aw.qmc.adderror(
            f'Exception: createserialTable(): {str(e)}',
            getattr(exc_tb, 'tb_lineno', '?')
        )
```

### Performance Considerations

#### **Efficient UI Updates**
- **Conditional Rendering**: Only show relevant configuration options
- **Dynamic Widget Creation**: Create controls only when needed
- **Lazy Loading**: Defer non-critical operations
- **Memory Management**: Efficient widget lifecycle management

#### **Communication Optimization**
- **Protocol Optimization**: Built-in optimization flags
- **Block Fetching**: Full block retrieval options
- **Timeout Configuration**: Configurable communication timeouts
- **Retry Logic**: Automatic retry mechanisms

### Future Enhancement Opportunities

#### **Potential Improvements**
- **Advanced Protocol Support**: Additional industrial protocols
- **Network Discovery**: Automatic device discovery
- **Configuration Templates**: Predefined configuration sets
- **Advanced Diagnostics**: Enhanced communication troubleshooting

#### **Integration Extensions**
- **Cloud Configuration**: Remote configuration management
- **Mobile Support**: Touch-optimized interfaces
- **API Integration**: REST API configuration
- **Advanced Security**: Enhanced authentication and encryption

This module represents the comprehensive communication configuration system for Artisan, providing professional-grade protocol support and device management capabilities while maintaining an intuitive and powerful user interface for complex industrial communication scenarios.