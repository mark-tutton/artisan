
# Artisan PID Dialogs Module Documentation

## File: `src/artisanlib/pid_dialogs.py`

### Overview
This module implements the **comprehensive PID control dialog system** for the Artisan coffee roasting application. At 4,367+ lines, it provides sophisticated user interfaces for configuring and controlling various PID controllers including Fuji PXG/PXR/PXF, Arduino TC4, MODBUS devices, and DTA controllers through a unified dialog framework.

### Purpose and Architecture
The `pid_dialogs.py` module serves as the **user interface layer** for Artisan's PID control system, implementing:
- **Unified Dialog Framework**: Consistent interface across all PID controller types
- **Advanced Configuration**: Comprehensive parameter setup and management
- **Real-Time Control**: Live monitoring and adjustment capabilities
- **Profile Management**: Ramp/soak profile creation and execution
- **Hardware Integration**: Direct communication with physical controllers

### Core Components

#### **1. Main PID Control Dialog (`PID_DlgControl`)**
- **Tabbed Interface**: Organized control sections for different aspects
- **Mode Management**: Manual, Ramp/Soak, and Follow Background modes
- **SV Slider Control**: Real-time setpoint adjustment interface
- **Ramp/Soak Management**: Multi-segment profile configuration
- **Import/Export**: JSON-based profile data exchange

#### **2. Fuji PXG4 PID Dialog (`PXG4pidDlgControl`)**
- **Advanced Configuration**: 7 independent PID parameter sets
- **Segment Management**: Up to 16 ramp/soak segments
- **Memory Operations**: Read/write all controller parameters
- **Time Unit Support**: HH:MM and MM:SS time formats
- **JSON Configuration**: Complete profile import/export

#### **3. Fuji PXR PID Dialog (`PXRpidDlgControl`)**
- **Simplified Interface**: 8-segment ramp/soak control
- **Thermocouple Configuration**: Sensor type and range setup
- **Autotune Support**: Automatic PID parameter optimization
- **Standby Control**: Run/standby mode management

#### **4. DTA PID Dialog (`DTApidDlgControl`)**
- **Delta Electronics Support**: DTA series controller interface
- **ASCII Protocol**: Proprietary communication implementation
- **Basic Control**: Essential PID parameter configuration

### Key Features

#### **1. Multi-Mode PID Control**
```python
# Three primary control modes
self.svMode: int = 0  # 0: manual, 1: Ramp/Soak, 2: Follow Background

def updatePidMode(self, i: int) -> None:
    # Mode switching with automatic UI updates
    if i == 0:  # Manual mode
        self.activateSVSlider(1)
    elif i == 1:  # Ramp/Soak mode
        self.activateSVSlider(0)
    elif i == 2:  # Follow Background mode
        self.activateSVSlider(0)
```

#### **2. Advanced Ramp/Soak Profiles**
```python
# Multi-segment temperature profiles
self.svLen: Final[int] = 8  # 8 temperature channels
self.svValues: List[float] = [0]*self.svLen      # Target temperatures
self.svRamps: List[int] = [0]*self.svLen         # Ramp times (seconds)
self.svSoaks: List[int] = [0]*self.svLen         # Soak times (seconds)
self.svActions: List[int] = [-1]*self.svLen      # Alarm actions
self.svBeeps: List[bool] = [False]*self.svLen    # Audio notifications
```

#### **3. Profile Import/Export System**
```python
def importrampsoaksJSON(self, filename: str) -> None:
    # Import ramp/soak profiles from JSON files
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # Parse and validate profile data
        # Update UI controls with imported values

def exportrampsoaksJSON(self, filename: str) -> bool:
    # Export current profiles to JSON format
    data = {
        'svValues': self.svValues,
        'svRamps': self.svRamps,
        'svSoaks': self.svSoaks,
        # ... complete profile data
    }
    return self.saveJSON(data, filename)
```

#### **4. Real-Time Control Interface**
```python
# SV slider with range limits
def activateSVSlider(self, flag: bool) -> None:
    if flag:
        self.aw.sliderGrpBoxSV.setVisible(True)
        self.aw.sliderSV.setMinimum(self.svSliderMin)
        self.aw.sliderSV.setMaximum(self.svSliderMax)
        # Set current SV value and enable control
    else:
        self.aw.sliderGrpBoxSV.setVisible(False)
        # Disable slider control
```

### Technical Architecture

#### **Dialog Inheritance Hierarchy**
```python
class PID_DlgControl(ArtisanDialog):
    # Base PID control dialog with common functionality
    
class PXpidDlgControl(PID_DlgControl):
    # Fuji PX series base functionality
    
class PXRpidDlgControl(PXpidDlgControl):
    # Fuji PXR specific features
    
class PXG4pidDlgControl(PXpidDlgControl):
    # Fuji PXG4 advanced features
    
class DTApidDlgControl(ArtisanDialog):
    # DTA controller specific interface
```

#### **Event-Driven Architecture**
```python
# PyQt signal/slot connections for real-time updates
@pyqtSlot(int)
def sliderMinValueChangedSlot(self, i: int) -> None:
    self.svSliderMin = i
    self.aw.sliderSV.setMinimum(self.svSliderMin)

@pyqtSlot(int)
def sliderMaxValueChangedSlot(self, i: int) -> None:
    self.svSliderMax = i
    self.aw.sliderSV.setMaximum(self.svSliderMax)
```

#### **Configuration Management**
```python
# Comprehensive parameter storage and retrieval
def savePIDJSON(self, filename: str) -> bool:
    data = {
        'pidKp': self.pidKp,
        'pidKi': self.pidKi,
        'pidKd': self.pidKd,
        'pidSource': self.pidSource,
        'pidCycle': self.pidCycle,
        'svValues': self.svValues,
        'svRamps': self.svRamps,
        'svSoaks': self.svSoaks,
        # ... extensive parameter set
    }
    return self.saveJSON(data, filename)
```

### Advanced Features

#### **1. Multi-PID Configuration (PXG4)**
```python
# Support for 7 independent PID parameter sets
def setNpidSlot(self, _: bool = False) -> None:
    # Configure PID parameters for specific set
    pidn = self.pidComboBox.currentIndex() + 1
    self.setNpid(pidn)

def setNpid(self, pidn: int) -> None:
    # Set PID parameters for set N
    pkey = 'p' + str(pidn)
    ikey = 'i' + str(pidn)
    dkey = 'd' + str(pidn)
    # Send commands to controller
```

#### **2. Segment Table Management**
```python
def createsegmenttable(self) -> None:
    # Dynamic table creation for ramp/soak segments
    self.segmentTable = QTableWidget()
    self.segmentTable.setRowCount(self.svLen)
    self.segmentTable.setColumnCount(4)
    # Configure table headers and data binding
    
def setsegment_i(self, i: int) -> None:
    # Individual segment parameter updates
    sv = self.segmentTable.item(i, 0).text()
    ramp = self.segmentTable.item(i, 1).text()
    soak = self.segmentTable.item(i, 2).text()
    # Validate and send to controller
```

#### **3. Background Profile Following**
```python
def changeFollowBackground(self, _: int) -> None:
    # Enable/disable background profile following
    if self.followBackgroundCheckBox.isChecked():
        self.aw.pidcontrol.loadpidfrombackground = True
        # Load PID parameters from background profile
    else:
        self.aw.pidcontrol.loadpidfrombackground = False
```

#### **4. Advanced Control Features**
- **Autotune Support**: Automatic PID parameter optimization
- **Standby Management**: Run/standby mode control
- **Thermocouple Configuration**: Sensor type and range setup
- **Time Unit Selection**: HH:MM vs MM:SS format support
- **Lookahead Control**: Predictive temperature adjustment

### User Interface Architecture

#### **Tabbed Interface Design**
```
┌─────────────────────────────────────────────────────────────┐
│                    PID Control                              │
├─────────────────────────────────────────────────────────────┤
│ [General] [Ramp/Soak] [Advanced] [Import/Export]          │
├─────────────────────────────────────────────────────────────┤
│ General Tab:                                               │
│ • PID Mode Selection (Manual/RS/Follow)                    │
│ • SV Slider Control                                        │
│ • PID ON/OFF Buttons                                       │
│ • Basic Parameters (Kp, Ki, Kd)                           │
├─────────────────────────────────────────────────────────────┤
│ Ramp/Soak Tab:                                             │
│ • Segment Table (8-16 segments)                            │
│ • Temperature, Ramp, Soak inputs                           │
│ • Action and Beep configuration                            │
│ • Pattern execution control                                │
├─────────────────────────────────────────────────────────────┤
│ Advanced Tab:                                              │
│ • Advanced PID parameters                                  │
│ • Control limits and steps                                 │
│ • Background profile settings                              │
│ • Hardware-specific options                                │
└─────────────────────────────────────────────────────────────┘
```

#### **Dynamic Control Generation**
```python
# Automatic UI generation based on controller capabilities
def paintlabels(self, _: int = 0) -> None:
    # Read current controller values and update UI
    for i in range(self.svLen):
        sv_item = self.segmentTable.item(i, 0)
        ramp_item = self.segmentTable.item(i, 1)
        soak_item = self.segmentTable.item(i, 2)
        # Update table items with current values
```

### Integration Points

#### **Main Application Integration**
- **Device Communication**: Direct integration with PID control system
- **Event System**: Automatic event triggering and recording
- **Settings Management**: Configuration persistence and retrieval
- **UI Updates**: Real-time interface synchronization

#### **Hardware Controller Integration**
- **Fuji Controllers**: PXG4, PXR, PXF series support
- **Arduino TC4**: Firmware-based PID control
- **MODBUS Devices**: Industrial automation integration
- **DTA Controllers**: Delta Electronics support

### Error Handling and Validation

#### **Input Validation**
```python
def setsegment_i(self, i: int) -> None:
    try:
        sv = float(self.segmentTable.item(i, 0).text())
        ramp = int(self.segmentTable.item(i, 1).text())
        soak = int(self.segmentTable.item(i, 2).text())
        
        # Validate ranges
        if not (0 <= sv <= 999):
            raise ValueError("SV out of range")
        if not (0 <= ramp <= 999):
            raise ValueError("Ramp time out of range")
        if not (0 <= soak <= 999):
            raise ValueError("Soak time out of range")
            
        # Send to controller
        self.aw.fujipid.setsegment(i+1, sv, ramp, soak)
    except ValueError as e:
        self.aw.sendmessage(f"Invalid input: {e}")
```

#### **Communication Error Handling**
- **Timeout Detection**: Communication failure detection
- **Retry Logic**: Automatic retry mechanisms
- **Error Reporting**: User-friendly error messages
- **Fallback Modes**: Graceful degradation on failures

### Performance Considerations

#### **Efficient UI Updates**
- **Conditional Rendering**: Only update changed elements
- **Batch Operations**: Group multiple parameter updates
- **Lazy Loading**: Defer non-critical operations
- **Memory Management**: Efficient data structure usage

#### **Communication Optimization**
- **Command Batching**: Group related commands
- **Timing Optimization**: Strategic delays between operations
- **Resource Locking**: Semaphore-protected operations
- **Buffer Management**: Optimized I/O handling

### Future Enhancement Opportunities

#### **Potential Improvements**
- **Machine Learning**: AI-based parameter optimization
- **Advanced Visualization**: Real-time control performance graphs
- **Cloud Integration**: Remote monitoring and control
- **Mobile Support**: Touch-optimized interfaces

#### **Integration Extensions**
- **IoT Support**: Internet of Things device integration
- **Advanced Protocols**: Support for emerging standards
- **Data Analytics**: Performance analysis and optimization
- **Automation**: Fully automated control sequences

This module represents the comprehensive user interface for Artisan's PID control system, providing professional-grade configuration and control capabilities across multiple hardware platforms while maintaining the intuitive usability required for both novice and expert users.`