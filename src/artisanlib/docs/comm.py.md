# Artisan Communication Module Documentation

## File: `src/artisanlib/comm.py`

### Overview
This module implements the **comprehensive device communication system** for the Artisan coffee roasting application. At 7,234 lines, it serves as the central hub for all hardware interactions, supporting an extensive range of temperature sensors, scales, color meters, and control devices through various communication protocols.

### Purpose and Architecture
The `comm.py` module serves as the **hardware abstraction layer** for Artisan, implementing:
- **Multi-protocol communication** (Serial, USB, Network, Bluetooth)
- **Device driver management** for 100+ different hardware types
- **Real-time data acquisition** from temperature sensors and scales
- **Control signal generation** for heaters, fans, and other actuators
- **Protocol translation** between different device standards

### Core Components

#### **Main Communication Class: `serialport`**
- **Purpose**: Primary communication handler for all device types
- **Inheritance**: Custom class with extensive device support
- **Capabilities**: Serial, USB, network, and Bluetooth communication

#### **Supporting Classes**
1. **`YoctoThread`**: Background thread for Yoctopuce device management
2. **`nonedevDlg`**: Dialog for manual temperature input when no device is connected
3. **`extraserialport`**: Extended serial port functionality for additional devices
4. **`scaleport`**: Specialized communication for digital scales
5. **`colorport`**: Specialized communication for color measurement devices

### Device Support Matrix

#### **1. Temperature Sensors (Primary Devices)**
```python
# Thermocouple-based devices
def PHIDGET1045(self) -> Tuple[float,float,float]:      # Phidget 1045 Thermocouple
def PHIDGET1048(self) -> Tuple[float,float,float]:      # Phidget 1048 8x Thermocouple
def PHIDGET1046(self) -> Tuple[float,float,float]:      # Phidget 1046 RTD
def YOCTO_thermo(self) -> Tuple[float,float,float]:     # Yoctopuce Thermocouple
def YOCTO_pt100(self) -> Tuple[float,float,float]:      # Yoctopuce PT100 RTD
def YOCTO_IR(self) -> Tuple[float,float,float]:         # Yoctopuce Infrared Sensor
```

#### **2. Industrial Control Systems**
```python
# Programmable Logic Controllers
def S7(self, force:bool=False) -> Tuple[float,float,float]:           # Siemens S7
def MODBUS(self, force:bool=False) -> Tuple[float,float,float]:       # MODBUS RTU/TCP
def ARC_BTET(self) -> Tuple[float,float,float]:                       # Arc Roaster Control
def R1_DTBT(self) -> Tuple[float,float,float]:                        # Aillio R1 Roaster
```

#### **3. Consumer Roasting Equipment**
```python
# Home and small commercial roasters
def BEHMOR_BTET(self) -> Tuple[float,float,float]:      # Behmor Roaster
def HOTTOP_BTET(self) -> Tuple[float,float,float]:      # Hottop Roaster
def Ikawa(self) -> Tuple[float,float,float]:             # Ikawa Pro Roaster
def Kaleido_BTET(self) -> Tuple[float,float,float]:      # Kaleido Roaster
```

#### **4. Laboratory and Measurement Equipment**
```python
# Precision measurement devices
def CENTER309(self) -> Tuple[float,float,float]:         # Center 309 Thermometer
def VOLTCRAFTK204(self) -> Tuple[float,float,float]:     # Voltcraft K204 Thermometer
def HH506RA(self) -> Tuple[float,float,float]:           # Omega HH506RA
def EXTECH421509(self) -> Tuple[float,float,float]:      # Extech 421509
```

### Communication Protocols

#### **1. Serial Communication**
```python
def openport(self) -> None:
    # Opens serial port with configured parameters
    self.SP = serial.Serial(
        port=self.comport,
        baudrate=self.baudrate,
        bytesize=self.bytesize,
        parity=self.parity,
        stopbits=self.stopbits,
        timeout=self.timeout
    )

def confport(self) -> None:
    # Configures serial port parameters
    if self.SP is not None:
        self.SP.baudrate = self.baudrate
        self.SP.bytesize = self.bytesize
        self.SP.parity = self.parity
        self.SP.stopbits = self.stopbits
        self.SP.timeout = self.timeout
```

#### **2. USB Device Management**
```python
# Phidget device management
def phidget1045attached(self, serial:int, port:Optional[int], deviceType:int, alternative_conf:bool = False) -> None:
    # Handles Phidget 1045 device attachment
    self.phidgetDevices[serial] = {
        'type': deviceType,
        'port': port,
        'device': None,
        'configured': False
    }

def phidget1045detached(self, serial:int, port:Optional[int], deviceType:int) -> None:
    # Handles Phidget 1045 device detachment
    if serial in self.phidgetDevices:
        del self.phidgetDevices[serial]
```

#### **3. Network Communication**
```python
# Yoctopuce network device management
def yoctoVOUTattach(self, c:int, module_id:Optional[str]) -> Optional['YVoltageOutput']:
    # Attaches to Yoctopuce voltage output module over network
    try:
        if module_id is not None:
            module = YVoltageOutput.FindVoltageOutput(f"{module_id}.voltageOutput{c}")
        else:
            module = YVoltageOutput.FirstVoltageOutput()
        if module is not None:
            module.set_voltage(0)
            return module
    except Exception as e:
        _log.error(f"Error attaching Yoctopuce VOUT: {e}")
    return None
```

### Data Acquisition and Processing

#### **1. Temperature Reading Methods**
```python
def PHIDGET1045temperature(self, deviceType:int=DeviceID.PHIDID_1045, retry:bool = True, alternative_conf:bool = False) -> Tuple[float, float]:
    # Reads temperature from Phidget 1045 thermocouple interface
    try:
        if self.phidgetManager is not None:
            # Get temperature readings from configured channels
            temp1 = self.phidgetManager.getTemperature(0, deviceType)
            temp2 = self.phidgetManager.getTemperature(1, deviceType)
            return temp1, temp2, 0.0
    except Exception as e:
        _log.error(f"Error reading Phidget 1045: {e}")
    return 0.0, 0.0, 0.0
```

#### **2. Data Validation and Filtering**
```python
def processChannelData(self, x:Optional[float], d:int, m:str) -> float:
    # Processes and validates channel data
    if x is None or numpy.isnan(x) or x == -1:
        return 0.0
    
    # Apply unit conversion if needed
    if m == 'F' and self.aw.qmc.mode == 'C':
        x = fromFtoC(x)
    elif m == 'C' and self.aw.qmc.mode == 'F':
        x = fromCtoF(x)
    
    return x
```

#### **3. Error Handling and Retry Logic**
```python
def MS6514temperature(self, retry:int=2) -> Tuple[float, float]:
    # Reads temperature with retry logic for reliability
    for attempt in range(retry):
        try:
            # Send temperature request command
            self.sendTXcommand(b'\x01\x03\x00\x00\x00\x01\x84\x0A')
            response = self.readline_terminated(b'\r')
            
            if len(response) >= 7:
                # Parse temperature data from response
                temp1 = int.from_bytes(response[3:5], byteorder='big') / 10.0
                temp2 = int.from_bytes(response[5:7], byteorder='big') / 10.0
                return temp1, temp2
            
        except Exception as e:
            _log.error(f"MS6514 read attempt {attempt + 1} failed: {e}")
            if attempt < retry - 1:
                libtime.sleep(0.1)
    
    return 0.0, 0.0
```

### Control Signal Generation

#### **1. PWM Output Control**
```python
def phidgetOUTsetPWM(self, channel:int, value:float, serial:Optional[str]=None) -> None:
    # Sets PWM duty cycle for control signals
    try:
        if serial is not None:
            device = self.phidgetDevices.get(serial)
        else:
            device = next(iter(self.phidgetDevices.values()), None)
        
        if device and device.get('pwm_channel'):
            device['pwm_channel'].setDutyCycle(value / 100.0)
            
    except Exception as e:
        _log.error(f"Error setting PWM: {e}")
```

#### **2. Digital Output Control**
```python
def phidgetBinaryOUTset(self, channel:int, value:bool, serial:Optional[str]=None) -> bool:
    # Sets digital output state
    try:
        if serial is not None:
            device = self.phidgetDevices.get(serial)
        else:
            device = next(iter(self.phidgetDevices.values()), None)
        
        if device and device.get('digital_channel'):
            device['digital_channel'].setState(value)
            return True
            
    except Exception as e:
        _log.error(f"Error setting digital output: {e}")
    
    return False
```

#### **3. Motor and Servo Control**
```python
def phidgetDCMotorSetVelocity(self, channel:int, value:float, serial:Optional[str]=None) -> None:
    # Sets DC motor velocity
    try:
        if serial is not None:
            device = self.phidgetDevices.get(serial)
        else:
            device = next(iter(self.phidgetDevices.values()), None)
        
        if device and device.get('motor_channel'):
            device['motor_channel'].setVelocity(value)
            
    except Exception as e:
        _log.error(f"Error setting motor velocity: {e}")
```

### Scale and Weight Communication

#### **1. Digital Scale Support**
```python
class scaleport(extraserialport):
    def readWeight(self, scale_weight:Optional[float]=None) -> Tuple[float,float,float]:
        # Reads weight from connected digital scale
        try:
            if self.device == 'Acaia':
                return self.readAcaia()
            elif self.device == 'KERN_NDE':
                return self.readKERN_NDE()
            elif self.device == 'Shore930':
                return self.readShore930()
            else:
                # Generic scale reading
                weight_str = self.readLine()
                weight = float(weight_str.strip())
                return weight, 0.0, 0.0
                
        except Exception as e:
            _log.error(f"Error reading scale: {e}")
            return 0.0, 0.0, 0.0
```

#### **2. Scale Protocol Implementation**
```python
@staticmethod
def readAcaia() -> Tuple[float,float,float]:
    # Reads from Acaia digital scale
    try:
        # Acaia uses specific communication protocol
        # Implementation handles weight, tare, and unit conversion
        pass
    except Exception as e:
        _log.error(f"Error reading Acaia scale: {e}")
        return 0.0, 0.0, 0.0
```

### Color Measurement Support

#### **1. Color Meter Communication**
```python
class colorport(extraserialport):
    def readColor(self) -> int:
        # Reads color measurement from connected color meter
        try:
            if self.device == 'Tonino':
                return self.readTonino()
            else:
                # Generic color reading
                color_data = self.readLine()
                return int(color_data.strip())
                
        except Exception as e:
            _log.error(f"Error reading color meter: {e}")
            return 0
```

#### **2. Tonino Color Meter Support**
```python
def readTonino(self, retry:int = 2) -> Tuple[float,float,float]:
    # Reads from Tonino color meter
    for attempt in range(retry):
        try:
            # Send measurement command
            self.sendTXcommand(b'MEASURE\r\n')
            response = self.readline_terminated(b'\r\n')
            
            if response.startswith(b'COLOR:'):
                # Parse color value
                color_value = float(response.split(b':')[1])
                return color_value, 0.0, 0.0
                
        except Exception as e:
            _log.error(f"Tonino read attempt {attempt + 1} failed: {e}")
            if attempt < retry - 1:
                libtime.sleep(0.1)
    
    return 0.0, 0.0, 0.0
```

### Device Configuration and Management

#### **1. Phidget Device Configuration**
```python
def configure1045(self) -> None:
    # Configures Phidget 1045 thermocouple interface
    try:
        if self.phidgetManager is not None:
            # Set thermocouple types for each channel
            for channel in range(4):
                thermocouple_type = self.aw.qmc.phidget1048_types[channel]
                self.phidgetManager.setThermocoupleType(channel, thermocouple_type)
                
            # Set data rate
            data_rate = self.aw.qmc.phidget1045_dataRate
            self.phidgetManager.setDataRate(data_rate)
            
    except Exception as e:
        _log.error(f"Error configuring Phidget 1045: {e}")
```

#### **2. Yoctopuce Device Configuration**
```python
def YOCTOimportLIB(self) -> None:
    # Imports and initializes Yoctopuce library
    try:
        from yoctopuce.yocto_api import YAPI
        from yoctopuce.yocto_temperature import YTemperature
        from yoctopuce.yocto_voltage import YVoltageOutput
        
        # Initialize Yoctopuce API
        YAPI.RegisterHub("usb")
        
    except ImportError as e:
        _log.error(f"Yoctopuce library not available: {e}")
        self.yoctoRemoteFlag = False
```

### Thread Safety and Synchronization

#### **1. Semaphore Protection**
```python
# Thread-safe device access
self.COMsemaphore = QSemaphore(1)  # Communication semaphore

def safe_device_access(self):
    # Ensures thread-safe device communication
    try:
        self.COMsemaphore.acquire(1)
        # Perform device operation
        result = self.device_operation()
    finally:
        if self.COMsemaphore.available() < 1:
            self.COMsemaphore.release(1)
    return result
```

#### **2. Background Thread Management**
```python
class YoctoThread(threading.Thread):
    def run(self) -> None:
        # Background thread for Yoctopuce device management
        try:
            while not self.stopped:
                # Poll Yoctopuce devices
                YAPI.Sleep(100)
                YAPI.UpdateDeviceList()
                
        except Exception as e:
            _log.error(f"YoctoThread error: {e}")
        finally:
            self.finished.emit()
```

### Error Handling and Recovery

#### **1. Communication Error Recovery**
```python
def handle_communication_error(self, device_type:str, error:Exception) -> None:
    # Handles communication errors with recovery strategies
    _log.error(f"Communication error with {device_type}: {error}")
    
    # Attempt to reconnect
    if self.auto_reconnect:
        self.reconnect_device(device_type)
    
    # Fallback to manual input if available
    if self.manual_input_available:
        self.enable_manual_input()
```

#### **2. Device Fallback Strategies**
```python
def get_temperature_fallback(self) -> Tuple[float,float,float]:
    # Provides fallback temperature readings when primary device fails
    try:
        # Try secondary device
        if self.secondary_device_available:
            return self.read_secondary_device()
        
        # Try cached values
        if self.temperature_cache_valid:
            return self.cached_temperatures
        
        # Manual input
        return self.get_manual_temperatures()
        
    except Exception as e:
        _log.error(f"All temperature sources failed: {e}")
        return 0.0, 0.0, 0.0
```

### Performance Optimization

#### **1. Data Rate Management**
```python
def optimize_data_rate(self, device_type:str) -> None:
    # Optimizes data acquisition rate for different devices
    if device_type == 'PHIDGET1045':
        # High-speed thermocouple reading
        self.set_data_rate(4)  # 4ms intervals
    elif device_type == 'YOCTO_thermo':
        # Network device with latency considerations
        self.set_data_rate(100)  # 100ms intervals
    else:
        # Standard serial device
        self.set_data_rate(250)  # 250ms intervals
```

#### **2. Caching and Buffering**
```python
# Temperature data caching
self.temperature_cache = {}
self.cache_validity_period = 1000  # milliseconds

def get_cached_temperature(self, device_id:str) -> Optional[float]:
    # Retrieves cached temperature if still valid
    if device_id in self.temperature_cache:
        timestamp, value = self.temperature_cache[device_id]
        if libtime.time() * 1000 - timestamp < self.cache_validity_period:
            return value
    return None
```

### Integration Points

#### **1. Main Application Integration**
```python
# Application window reference
self.aw = aw  # ApplicationWindow instance

# Quick Mill Control integration
self.aw.qmc.device = self.current_device
self.aw.qmc.device_logging = self.logging_enabled
```

#### **2. Plugin System Integration**
```python
# Plugin device support
def register_plugin_device(self, plugin_name:str, device_handler:Callable) -> None:
    # Registers custom device handlers from plugins
    self.plugin_devices[plugin_name] = device_handler
    _log.info(f"Registered plugin device: {plugin_name}")
```

### Future Enhancement Considerations

#### **1. Protocol Extensions**
- **MQTT Support**: IoT device communication
- **OPC UA**: Industrial automation standards
- **WebSocket**: Real-time web-based monitoring

#### **2. Device Discovery**
- **Auto-discovery**: Automatic device detection
- **Plug-and-play**: Hot-plug device support
- **Device profiles**: Pre-configured device templates

#### **3. Advanced Control**
- **PID Control**: Built-in temperature control algorithms
- **Recipe Management**: Automated roasting sequences
- **Remote Control**: Network-based device control

This module represents the foundation of Artisan's hardware integration capabilities, providing a robust, extensible communication layer that supports an extensive range of coffee roasting equipment while maintaining reliability and performance across different communication protocols and device types.