# Artisan MODBUS Port Module Documentation

## File: `src/artisanlib/modbusport.py`

### Overview
This module implements the **comprehensive MODBUS communication system** for the Artisan coffee roasting application. At 1,173 lines, it provides a sophisticated interface for communicating with industrial automation devices, temperature controllers, and PID systems through multiple MODBUS protocols and transport layers.

### Purpose and Architecture
The `modbusport.py` module serves as the **industrial communication backbone** for Artisan, implementing:
- **Multi-protocol Support**: RTU, ASCII, TCP, and UDP MODBUS variants
- **Advanced Data Conversion**: BCD, float, integer, and custom data type handling
- **Intelligent Optimization**: Register batching and caching for performance
- **Robust Error Handling**: Comprehensive error recovery and connection management
- **Asynchronous Communication**: Non-blocking I/O with proper thread safety

### Core Classes

#### **`modbusport` (Main MODBUS Communication Class)**
The primary interface for all MODBUS device communication with extensive configuration options.

**Key Attributes:**
```python
__slots__ = [
    'aw', 'legacy_pymodbus', 'modbus_serial_read_delay', 'modbus_serial_connect_delay',
    'modbus_serial_write_delay', 'maxCount', 'readRetries', 'default_comport', 'comport',
    'baudrate', 'bytesize', 'parity', 'stopbits', 'timeout', 'IP_timeout', 'IP_retries',
    'serial_readRetries', 'PID_slave_ID', 'PID_SV_register', 'PID_p_register',
    'PID_i_register', 'PID_d_register', 'PID_ON_action', 'PID_OFF_action',
    'channels', 'inputSlaves', 'inputRegisters', 'inputFloats', 'inputBCDs',
    'inputFloatsAsInt', 'inputBCDsAsInt', 'inputSigned', 'inputCodes', 'inputDivs',
    'inputModes', 'optimizer', 'fetch_max_blocks', 'fail_on_cache_miss',
    'disconnect_on_error', 'acceptable_errors', 'activeRegisters', 'readingsCache',
    'SVmultiplier', 'PIDmultiplier', 'SVwriteLong', 'SVwriteFloat', 'wordorderLittle',
    '_asyncLoopThread', '_client', 'COMsemaphore', 'default_host', 'host', 'port',
    'type', 'lastReadResult', 'commError'
]
```

### Communication Protocols

#### **Transport Layer Support**
```python
# type values:
# 0: Serial RTU (default)
# 1: Serial ASCII  
# 2: Serial Binary (deprecated)
# 3: TCP
# 4: UDP
```

#### **Serial Configuration**
```python
self.default_comport: Final[str] = 'COM5'
self.baudrate: int = 115200
self.bytesize: int = 8
self.parity: str = 'N'  # Literal['O','E','N']
self.stopbits: int = 1
self.timeout: float = 0.4  # serial MODBUS timeout
```

#### **Network Configuration**
```python
self.default_host: Final[str] = '127.0.0.1'
self.host: str = self.default_host
self.port: int = 502  # standard MODBUS port
self.IP_timeout: float = 0.2  # UDP/TCP MODBUS timeout
self.IP_retries: int = 1  # UDP/TCP MODBUS retries
```

### Data Type Conversion System

#### **BCD (Binary Coded Decimal) Support**
```python
def convert_to_bcd(value: int) -> int:
    """Converts decimal value to BCD format"""
    place, bcd = 0, 0
    while value > 0:
        nibble = value % 10
        bcd += nibble << place
        value = value // 10
        place += 4
    return bcd

def convert_from_bcd(value: int) -> int:
    """Converts BCD value to decimal format"""
    place, decimal = 1, 0
    while value > 0:
        nibble = value & 0xf
        decimal += nibble * place
        value >>= 4
        place *= 10
    return decimal
```

#### **Register Data Conversion**
```python
def convert_16bit_uint_to_registers(self, value: int) -> List[int]:
    return ModbusClientMixin.convert_to_registers(
        value, ModbusClientMixin.DATATYPE.UINT16, 
        word_order=self.word_order()
    )

def convert_32bit_int_to_registers(self, value: int) -> List[int]:
    if self.legacy_pymodbus:
        return ModbusClientMixin.convert_to_registers(
            value, ModbusClientMixin.DATATYPE.INT32
        )[::-1]
    return ModbusClientMixin.convert_to_registers(
        value, ModbusClientMixin.DATATYPE.INT32, 
        word_order=self.word_order()
    )

def convert_float_to_registers(self, value: float) -> List[int]:
    if self.legacy_pymodbus:
        return ModbusClientMixin.convert_to_registers(
            value, ModbusClientMixin.DATATYPE.FLOAT32
        )[::-1]
    return ModbusClientMixin.convert_to_registers(
        value, ModbusClientMixin.DATATYPE.FLOAT32, 
        word_order=self.word_order()
    )
```

### Advanced Optimization System

#### **Register Batching and Caching**
```python
def updateActiveRegisters(self) -> None:
    """Optimizes register reads by grouping consecutive addresses"""
    self.activeRegisters = {}
    for c in range(self.channels):
        slave = self.inputSlaves[c]
        if slave != 0:
            register = self.inputRegisters[c]
            code = self.inputCodes[c]
            if code not in {1, 2}:  # MODBUS functions 1 and 2 are not optimized
                registers = [register]
                if self.inputFloats[c] or self.inputBCDs[c] or self.inputFloatsAsInt[c]:
                    registers.append(register + 1)
                # Group registers by slave and function code
```

#### **Intelligent Read Optimization**
```python
def readActiveRegisters(self) -> None:
    """Reads all active registers in optimized batches"""
    if not self.optimizer:
        return
    try:
        self.COMsemaphore.acquire(1)
        self.connect()
        if self._asyncLoopThread is not None and self.isConnected():
            asyncio.run_coroutine_threadsafe(
                self.read_active_registers_async(), 
                self._asyncLoopThread.loop
            ).result()
    finally:
        if self.COMsemaphore.available() < 1:
            self.COMsemaphore.release(1)
```

### Reading Operations

#### **Single Register Reading**
```python
def readSingleRegister(self, slave: int, register: int, code: int = 3, 
                      force: bool = False, signed: bool = False) -> Optional[int]:
    """Reads single register with caching and error handling"""
    if slave == 0:
        return None
    
    res_registers, res_bits, res_error_disconnect = self.read_registers(
        slave, register, 1, code, force
    )
    
    if code in {1, 2} and res_bits is not None:
        res = sum(x[1] << x[0] for x in enumerate(res_bits)) if len(res_bits) > 0 else 0
    elif res_registers is not None:
        if signed:
            res = self.convert_16bit_int_from_registers(res_registers)
        else:
            res = self.convert_16bit_uint_from_registers(res_registers)
    
    return res
```

#### **Float and BCD Reading**
```python
def readFloat(self, slave: int, register: int, code: int = 3, force: bool = False) -> Optional[float]:
    """Reads 32-bit float from two consecutive registers"""
    res_registers, _, res_error_disconnect = self.read_registers(slave, register, 2, code, force)
    if res_registers is not None:
        res = self.convert_float_from_registers(res_registers)
        self.clearCommError()
        return res
    return None

def readBCD(self, slave: int, register: int, code: int = 3, force: bool = False) -> Optional[int]:
    """Reads BCD-encoded value from registers"""
    res_registers, _, res_error_disconnect = self.read_registers(slave, register, 2, code, force)
    if res_registers is not None:
        res = convert_from_bcd(self.convert_32bit_uint_from_registers(res_registers))
        self.clearCommError()
        return res
    return None
```

### Writing Operations

#### **Single Register Writing**
```python
def writeSingleRegister(self, slave: int, register: int, value: float) -> None:
    """Writes single register (MODBUS function 6)"""
    if slave == 0:
        return
    try:
        self.COMsemaphore.acquire(1)
        self.connect()
        if self._asyncLoopThread is not None and self.isConnected():
            async def write_register_wrapper(client, register, value, slave):
                return await client.write_register(register, value, slave=slave)
            
            asyncio.run_coroutine_threadsafe(
                write_register_wrapper(self._client, int(register), int(round(value)), int(slave)),
                self._asyncLoopThread.loop
            ).result()
    finally:
        if self.COMsemaphore.available() < 1:
            self.COMsemaphore.release(1)
```

#### **Advanced Writing Functions**
```python
def writeWord(self, slave: int, register: int, value: float) -> None:
    """Writes 32-bit float to two consecutive registers"""
    payload: List[int] = self.convert_float_to_registers(value)
    # Write multiple registers (function 16)

def writeLong(self, slave: int, register: int, value: float) -> None:
    """Writes 32-bit integer to two consecutive registers"""
    payload: List[int] = self.convert_32bit_int_to_registers(int(round(value)))

def writeBCD(self, slave: int, register: int, value: float) -> None:
    """Writes BCD-encoded value to register"""
    r = convert_to_bcd(int(round(value)))
    payload: List[int] = self.convert_16bit_uint_to_registers(r)
```

#### **Coil and Discrete Input Control**
```python
def writeCoil(self, slave: int, register: int, value: bool) -> None:
    """Writes single coil (MODBUS function 5)"""
    
def writeCoils(self, slave: int, register: int, values: List[bool]) -> None:
    """Writes multiple coils (MODBUS function 15)"""
    
def maskWriteRegister(self, slave: int, register: int, and_mask: int, or_mask: int) -> None:
    """Writes register with bit masking (MODBUS function 22)"""
```

### PID Control Integration

#### **Setpoint Control**
```python
def setTarget(self, sv: float) -> None:
    """Sets PID controller setpoint value"""
    if self.PID_slave_ID:
        multiplier = 1.
        if self.SVmultiplier == 1:
            multiplier = 10.
        elif self.SVmultiplier == 2:
            multiplier = 100.
        
        if self.SVwriteFloat:
            self.writeWord(self.PID_slave_ID, self.PID_SV_register, float(sv * multiplier))
        elif self.SVwriteLong:
            self.writeLong(self.PID_slave_ID, self.PID_SV_register, int(round(sv * multiplier)))
        else:
            self.writeSingleRegister(self.PID_slave_ID, self.PID_SV_register, int(round(sv * multiplier)))
```

#### **PID Parameter Configuration**
```python
def setPID(self, p: float, i: float, d: float) -> None:
    """Sets PID controller parameters"""
    if self.PID_slave_ID and not self.PID_p_register == self.PID_i_register == self.PID_d_register == 0:
        multiplier = 1.
        if self.PIDmultiplier == 1:
            multiplier = 10.
        elif self.PIDmultiplier == 2:
            multiplier = 100.
        
        self.writeSingleRegister(self.PID_slave_ID, self.PID_p_register, p * multiplier)
        self.writeSingleRegister(self.PID_slave_ID, self.PID_i_register, i * multiplier)
        self.writeSingleRegister(self.PID_slave_ID, self.PID_d_register, d * multiplier)
```

### Connection Management

#### **Asynchronous Connection Handling**
```python
async def connect_async(self) -> None:
    """Establishes MODBUS connection with appropriate client type"""
    if not self.isConnected():
        self.commError = 0
        try:
            if self.type == 1:  # Serial ASCII
                self._client = AsyncModbusSerialClient(
                    framer=FramerType.ASCII,
                    port=self.comport,
                    baudrate=self.baudrate,
                    bytesize=self.bytesize,
                    parity=self.parity,
                    stopbits=self.stopbits,
                    retries=self.serial_readRetries,
                    timeout=min((self.aw.qmc.delay/2000), self.timeout)
                )
            elif self.type == 3:  # TCP
                self._client = AsyncModbusTcpClient(
                    host=self.host,
                    port=self.port,
                    retries=self.IP_retries,
                    timeout=min((self.aw.qmc.delay/2000), self.IP_timeout)
                )
            # ... other connection types
            
            if self._client is not None:
                await self._client.connect()
            
            if self.isConnected():
                self.updateActiveRegisters()
                self.clearReadingsCache()
                # Respect user-defined connect delay for serial connections
                if self.type in {0, 1}:  # RTU/ASCII
                    await asyncio.sleep(self.modbus_serial_connect_delay)
                else:
                    await asyncio.sleep(.3)  # Avoid hiccups on startup
```

#### **Error Handling and Recovery**
```python
def disconnectOnError(self) -> None:
    """Disconnects on communication errors if mechanism is active"""
    if self.disconnect_on_error and (self.commError > self.acceptable_errors or not self.isConnected()):
        _log.info('MODBUS disconnectOnError: %s', self.commError)
        self.disconnect()

def clearCommError(self) -> None:
    """Clears communication error count and notifies user"""
    if self.commError > 0:
        self.aw.qmc.adderror(QApplication.translate('Error Message', 'Modbus Communication Resumed'))
    self.commError = 0
```

### Performance Optimization Features

#### **Register Caching System**
```python
def cacheReadings(self, code: int, slave: int, register: int, results: List[int]) -> None:
    """Caches register readings for optimizer"""
    if code not in self.readingsCache:
        self.readingsCache[code] = {}
    if slave not in self.readingsCache[code]:
        self.readingsCache[code][slave] = {}
    for i, v in enumerate(results):
        self.readingsCache[code][slave][register + i] = v
        if self.aw.seriallogflag:
            ser_str = f'cache reading : Slave = {slave} || Register = {register+i} || Rx = {v}'
            self.aw.addserial(ser_str)
```

#### **Intelligent Register Batching**
```python
def read_active_registers_async(self) -> None:
    """Reads active registers in optimized sequences"""
    for code, slaves in self.activeRegisters.items():
        for slave, registers in slaves.items():
            registers_sorted = sorted(registers)
            if self.fetch_max_blocks:
                sequences = [(registers_sorted[0], registers_sorted[-1])]
            else:
                # Split into successive sequences, handling gaps
                gaps = [[s, er] for s, er in zip(registers_sorted, registers_sorted[1:]) if s+1 < er]
                edges = iter(registers_sorted[:1] + sum(gaps, []) + registers_sorted[-1:])
                sequences = list(zip(edges, edges))
            
            for seq in sequences:
                register = seq[0]
                count = seq[1] - seq[0] + 1
                if 0 < count <= self.maxCount:
                    # Read register sequence and cache results
```

### Thread Safety and Synchronization

#### **Semaphore-based Resource Management**
```python
self.COMsemaphore: QSemaphore = QSemaphore(1)

# Usage pattern in all communication methods:
try:
    self.COMsemaphore.acquire(1)
    # Perform MODBUS operation
finally:
    if self.COMsemaphore.available() < 1:
        self.COMsemaphore.release(1)
```

#### **Asynchronous Loop Management**
```python
self._asyncLoopThread: Optional[AsyncLoopThread] = None

# All async operations are executed in the dedicated thread:
if self._asyncLoopThread is not None and self.isConnected():
    asyncio.run_coroutine_threadsafe(
        async_operation(), 
        self._asyncLoopThread.loop
    ).result()
```

### Configuration and Flexibility

#### **Channel Configuration**
```python
self.channels: Final[int] = 10
self.inputSlaves: List[int] = [0] * self.channels
self.inputRegisters: List[int] = [0] * self.channels
self.inputFloats: List[bool] = [False] * self.channels
self.inputBCDs: List[bool] = [False] * self.channels
self.inputFloatsAsInt: List[bool] = [False] * self.channels
self.inputBCDsAsInt: List[bool] = [False] * self.channels
self.inputSigned: List[bool] = [False] * self.channels
self.inputCodes: List[int] = [3] * self.channels
self.inputDivs: List[int] = [0] * self.channels
self.inputModes: List[str] = ['C'] * self.channels
```

#### **Data Type Flexibility**
```python
# Multiple data interpretation options per channel:
# - 16-bit unsigned/signed integers
# - 32-bit unsigned/signed integers  
# - 32-bit floating point
# - BCD-encoded values
# - Custom scaling and division factors
# - Multiple MODBUS function codes (1, 2, 3, 4)
```

### Error Handling and Logging

#### **Comprehensive Error Detection**
```python
@staticmethod
def invalidResult(res: Any, count: int) -> Tuple[bool, bool]:
    """Determines if MODBUS response is valid and if disconnect is required"""
    if res is None:
        return True, False
    if isinstance(res, ExceptionResponse):
        return True, False
    if res.isError():
        return True, True
    if res.registers is None:
        return True, False
    if count > 0 and len(res.registers) != count:
        return True, False
    return False, False
```

#### **Detailed Communication Logging**
```python
# Serial logging for debugging:
if self.aw.seriallogflag:
    if self.type < 3:  # serial MODBUS
        ser_str = f'MODBUS readFloat : {self.formatMS(tx,time.time())}ms => {self.comport},{self.baudrate},{self.bytesize},{self.parity},{self.stopbits},{self.timeout} || Slave = {slave} || Register = {register} || Code = {code} || Rx = {res} || retries = {self.readRetries}'
    else:  # IP MODBUS
        ser_str = f'MODBUS readFloat : {self.formatMS(tx,time.time())}ms => {self.host}:{self.port} || Slave = {slave} || Register = {register} || Code = {code} || Rx = {res} || retries = {self.readRetries}'
    self.aw.addserial(ser_str)
```

### Integration Points

#### **Main Application Integration**
- **Temperature Reading**: Integrates with Artisan's temperature monitoring system
- **PID Control**: Provides setpoint and parameter control for temperature regulation
- **Event Actions**: Supports custom button and slider actions via MODBUS commands
- **Real-time Updates**: Maintains synchronization with hardware state

#### **Hardware Device Support**
- **Temperature Controllers**: PID controllers, thermostats, and temperature monitors
- **Industrial Equipment**: PLCs, SCADA systems, and automation equipment
- **Custom Devices**: User-configured MODBUS slaves with custom register mappings
- **Multi-device Networks**: Support for multiple slaves on single MODBUS network

This module represents the most sophisticated industrial communication system in Artisan, providing professional roasters with enterprise-grade MODBUS connectivity for industrial automation, temperature control, and data acquisition systems.