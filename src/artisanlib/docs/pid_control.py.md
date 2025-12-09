# Artisan PID Control Module Documentation

## File: `src/artisanlib/pid_control.py`

### Overview
This module implements the **comprehensive PID control system** for the Artisan coffee roasting application. At 1,904 lines, it provides sophisticated temperature control capabilities supporting multiple hardware platforms including Fuji PID controllers, Arduino TC4, MODBUS devices, and software-based PID control.

### Purpose and Architecture
The `pid_control.py` module serves as the **central temperature control hub** for Artisan, implementing:
- **Multi-Platform PID Support**: Fuji PXG/PXR/PXF, Arduino TC4, MODBUS, S7, Kaleido
- **Advanced Control Algorithms**: Proportional-Integral-Derivative control with filtering
- **Ramp/Soak Profiles**: Complex temperature profiles with automatic execution
- **Background Profile Following**: Automatic temperature control based on reference curves
- **Hardware Abstraction**: Unified interface for diverse control hardware

### Core Components

#### **1. Fuji PID Controller Class (`FujiPID`)**
- **Device Support**: PXG4, PXR, PXF series controllers
- **Communication Protocols**: Serial and MODBUS communication
- **Memory Mapping**: Complete register mapping for all controller parameters
- **Thermocouple Support**: Extensive sensor type compatibility

#### **2. Arduino TC4 PID Class (`PIDcontrol`)**
- **Software PID**: Internal PID algorithm implementation
- **Hardware Integration**: Direct Arduino communication
- **Ramp/Soak Management**: Multi-segment temperature profiles
- **Event Integration**: Automatic event triggering and alarm management

#### **3. DTA PID Controller Class (`DtaPID`)**
- **Delta Electronics Support**: DTA series temperature controllers
- **ASCII Protocol**: Proprietary communication protocol implementation
- **Checksum Validation**: Robust error detection and correction

### Key Features

#### **1. Multi-Protocol Communication**
```python
# Support for multiple communication methods
if self.aw.ser.useModbusPort:
    # MODBUS protocol implementation
    reg = self.aw.modbus.address2register(register, 6)
    self.aw.modbus.writeSingleRegister(station, reg, value)
else:
    # Serial protocol implementation
    command = self.message2send(station, 6, register, value)
    response = self.aw.ser.sendFUJIcommand(command, 8)
```

#### **2. Advanced PID Control**
- **Proportional Control**: Configurable proportional band (P)
- **Integral Control**: Adjustable integration time (I)
- **Derivative Control**: Configurable derivative time (D)
- **Derivative Filtering**: Noise reduction for derivative term
- **Duty Cycle Control**: Configurable output limits and steps

#### **3. Ramp/Soak Profile System**
```python
# Multi-segment temperature profiles
self.svValues: List[float] = [0]*self.svLen      # Target temperatures
self.svRamps: List[int] = [0]*self.svLen         # Ramp times (seconds)
self.svSoaks: List[int] = [0]*self.svLen         # Soak times (seconds)
self.svActions: List[int] = [-1]*self.svLen      # Alarm actions
self.svBeeps: List[bool] = [False]*self.svLen    # Audio notifications
```

#### **4. Background Profile Following**
- **Automatic SV Calculation**: Real-time setpoint adjustment
- **Lookahead Support**: Predictive temperature control
- **Smoothing Algorithms**: Noise reduction for stable control
- **Multi-Curve Support**: BT, ET, and extra temperature curves

### Technical Architecture

#### **Device Communication Layer**
```python
# Unified communication interface
def externalPIDControl(self) -> int:
    # Returns control type:
    # 0: internal PID, 1: MODBUS, 2: S7, 3: TC4, 4: Kaleido
    if self.aw.modbus.PID_slave_ID != 0:
        return 1  # MODBUS
    if self.aw.s7.PID_area != 0:
        return 2  # S7
    if (self.aw.qmc.device == 19 and self.aw.qmc.PIDbuttonflag):
        return 3  # TC4
    return 0  # Internal
```

#### **Memory Mapping System**
```python
# Fuji PXG4 register mapping
self.PXG4: Dict[str, List[Union[float, int]]] = {
    'manual': [0, 41121],           # Manual mode control
    'runstandby': [0, 41004],       # Run/standby control
    'p': [5, 41006],                # Proportional band
    'i': [240, 41007],              # Integration time
    'd': [60, 41008],               # Derivative time
    'sv1': [300.0, 41241],          # Setpoint 1
    # ... extensive parameter mapping
}
```

#### **Temperature Unit Conversion**
```python
def conv2celsius(self) -> None:
    # Convert Fahrenheit values to Celsius
    self.svValue = fromFtoCstrict(self.svValue)
    self.pidKp = self.pidKp * (9/5.)  # Scale PID parameters
    self.pidKi = self.pidKi * (9/5.)
    self.pidKd = self.pidKd * (9/5.)
```

### Control Modes

#### **1. Manual Mode**
- **Direct SV Control**: User-defined setpoint values
- **Slider Interface**: Real-time temperature adjustment
- **Incremental Control**: Fine-tuning with +/- buttons

#### **2. Ramp/Soak Mode**
- **Profile Execution**: Automatic temperature progression
- **Segment Management**: Up to 8 temperature segments
- **Time-Based Control**: Precise timing for each phase
- **Alarm Integration**: Automatic event triggering

#### **3. Follow Background Mode**
- **Profile Replication**: Automatic curve following
- **Lookahead Control**: Predictive temperature adjustment
- **Smoothing**: Noise reduction for stable control
- **Multi-Curve Support**: BT, ET, and extra curves

### Advanced Features

#### **1. PID Parameter Optimization**
```python
# Automatic PID tuning support
def setpidPXG(self, k: int, newPvalue: float, newIvalue: float, newDvalue: float) -> None:
    # Configure PID parameters for specific setpoint
    pkey = 'p' + str(k)
    ikey = 'i' + str(k)
    dkey = 'd' + str(k)
    # Send commands to controller
```

#### **2. Duty Cycle Control**
```python
# Energy output control
def setEnergy(self, v: float) -> None:
    # Map PID output to slider positions
    if self.pidPositiveTarget:
        slidernr = self.pidPositiveTarget - 1
        heat = numpy.interp(vx, [0, 100], [heat_min, heat_max])
        self.aw.addRawEventSignal.emit(heat, raw_heat, slidernr, ...)
```

#### **3. Event Integration**
- **Automatic Alarms**: Temperature-based event triggering
- **Slider Control**: Automatic slider movement
- **Event Recording**: Command history for replay
- **Audio Notifications**: Configurable beep sounds

### Error Handling and Validation

#### **Communication Error Handling**
```python
# Robust error detection
if len(p) == 8 and len(i) == 8 and len(d) == 8:
    # Success - update local state
    self.aw.fujipid.PXG4[pkey][0] = float(newPvalue)
    message = f'pid #{k} successfully set to ({newPvalue},{newIvalue},{newDvalue})'
else:
    # Error - report failure
    message = f'pid command failed. Bad data at pid{k} (8,8,8): ({len(p)},{len(i)},{len(d)})'
    self.aw.qmc.adderror(message)
```

#### **Data Validation**
- **Range Checking**: Temperature and time limits
- **Type Validation**: Data type verification
- **Protocol Compliance**: Communication protocol validation
- **Checksum Verification**: Data integrity checking

### Performance Considerations

#### **Efficient Communication**
- **Command Batching**: Grouped parameter updates
- **Timing Optimization**: Strategic delays between commands
- **Resource Locking**: Semaphore-protected operations
- **Buffer Management**: Input/output buffer optimization

#### **Memory Management**
- **Register Caching**: Local parameter storage
- **State Synchronization**: Real-time parameter updates
- **Profile Storage**: Efficient ramp/soak data structures
- **Event Queuing**: Optimized event processing

### Integration Points

#### **Main Application Integration**
- **Device Management**: Integration with device detection system
- **Event System**: Automatic event triggering and recording
- **UI Updates**: Real-time interface updates
- **Settings Persistence**: Configuration storage and retrieval

#### **Plugin System Compatibility**
- **Hardware Abstraction**: Unified interface for all controllers
- **Protocol Support**: Multiple communication standards
- **Configuration Management**: Centralized parameter control
- **Error Reporting**: Integrated error handling system

### Future Enhancement Opportunities

#### **Potential Improvements**
- **Machine Learning**: AI-based PID parameter optimization
- **Advanced Filtering**: Kalman filtering for noise reduction
- **Predictive Control**: Model-based predictive control
- **Cloud Integration**: Remote monitoring and control

#### **Integration Extensions**
- **IoT Support**: Internet of Things device integration
- **Mobile Control**: Smartphone/tablet control interfaces
- **Data Analytics**: Advanced performance analysis
- **Automation**: Fully automated roasting sequences

This module represents the core of Artisan's temperature control capabilities, providing professional-grade PID control across multiple hardware platforms while maintaining the flexibility and reliability required for precision coffee roasting applications.