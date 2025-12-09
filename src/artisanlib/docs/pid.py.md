# Artisan PID Controller Module Documentation

## File: `src/artisanlib/pid.py`

### Overview
This module implements the **core PID (Proportional-Integral-Derivative) controller algorithm** for the Artisan coffee roasting application. At 346 lines, it provides a sophisticated, production-ready PID control implementation with advanced features including derivative filtering, input/output smoothing, and thread-safe operation.

### Purpose and Architecture
The `pid.py` module serves as the **mathematical foundation** for Artisan's temperature control system, implementing:
- **Classical PID Control**: Proportional, Integral, and Derivative control terms
- **Advanced Filtering**: Derivative noise reduction and input/output smoothing
- **Thread Safety**: Semaphore-protected operations for multi-threaded environments
- **Anti-Windup Protection**: Integral term clamping to prevent control saturation
- **Derivative Kick Prevention**: Measurement-based derivative calculation

### Core Components

#### **Main PID Controller Class (`PID`)**
- **Control Function Interface**: Callback-based output control
- **Parameter Configuration**: Tunable P, I, D gains
- **State Management**: Active/inactive state control
- **Output Limiting**: Configurable duty cycle ranges

#### **Advanced Filtering System**
```python
# Derivative filtering using IIR Butterworth filter
def derivativeFilter() -> LiveSosFilter:
    return LiveSosFilter(
        iirfilter(1,                    # 1st order filter
        Wn=0.2,                        # Cutoff frequency (0.2 Hz)
        fs=1,                          # Sampling rate (1 Hz)
        btype='low',                   # Low-pass filter
        ftype='butter',                # Butterworth response
        output='sos'))                 # Second-order sections output
```

### Key Features

#### **1. Classical PID Control Algorithm**
```python
# PID control loop implementation
def update(self, i: Optional[float]) -> None:
    # Calculate error
    err = self.target - i
    
    # Proportional term
    self.Pterm = self.Kp * err
    
    # Integral term with anti-windup
    self.Iterm += self.Ki * err * dt
    self.Iterm = max(self.outMin, min(self.outMax, self.Iterm))
    
    # Derivative term (measurement-based to avoid derivative kick)
    if self.derivative_on_error:
        D = self.Kd * derr
    else:
        D = -self.Kd * dtinput
    
    # Combine terms
    output = self.Pterm + self.Iterm + D
```

#### **2. Derivative Kick Prevention**
```python
# Derivative on Measurement implementation
# Avoids control spikes when setpoint changes
if self.lastInput:
    dinput = i - self.lastInput
    dtinput = dinput / dt
else:
    dinput = 0
    dtinput = 0

# Use rate of change of input instead of error
D = -self.Kd * dtinput  # Negative sign for stability
```

#### **3. Advanced Smoothing Algorithms**
```python
def _smooth_output(self, output: float) -> float:
    # Weighted moving average with decay weights
    if self.output_smoothing_factor != 0:
        # Create decay weights: [1, 2, 3, ..., n]
        self.output_decay_weights = list(numpy.arange(1, self.output_smoothing_factor + 1))
        
        # Add new value and maintain window size
        self.previous_outputs.append(output)
        self.previous_outputs = self.previous_outputs[-self.output_smoothing_factor:]
        
        # Weighted average with decay weights
        if len(self.previous_outputs) >= self.output_smoothing_factor:
            return float(numpy.average(self.previous_outputs, weights=self.output_decay_weights))
    return output
```

#### **4. Thread-Safe Operation**
```python
# Semaphore-protected critical sections
def update(self, i: Optional[float]) -> None:
    try:
        self.pidSemaphore.acquire(1)
        # Critical PID calculation section
        # ... PID algorithm implementation
    finally:
        if self.pidSemaphore.available() < 1:
            self.pidSemaphore.release(1)
```

### Technical Architecture

#### **State Management System**
```python
# Comprehensive state tracking
self.Pterm: float = 0.0           # Current proportional term
self.errSum: float = 0.0          # Error accumulator for integral
self.Iterm: float = 0.0           # Current integral term
self.lastError: Optional[float]   # Previous error for derivative
self.lastInput: float = 0.0       # Previous input for measurement-based derivative
self.lastOutput: Optional[float]  # Previous output for initialization
self.lastTime: Optional[float]    # Previous update time
self.target: float = 0.0          # Current setpoint
self.active: bool = False         # Controller active state
```

#### **Output Control System**
```python
# Duty cycle control with step limiting
int_output = int(round(min(self.dutyMax, max(self.dutyMin, output))))

# Only send control command if:
# 1. First time (lastOutput is None)
# 2. Force duty cycle reached
# 3. Output change exceeds duty steps
if (self.lastOutput is None or 
    self.iterations_since_duty >= self.force_duty or 
    int_output >= self.lastOutput + self.dutySteps or 
    int_output <= self.lastOutput - self.dutySteps):
    
    if self.active:
        self.control(int_output)  # Call control function
        self.iterations_since_duty = 0
```

#### **Filtering Architecture**
```python
# Multi-level filtering system
class PID:
    def __init__(self, ...):
        # Input smoothing
        self.input_smoothing_factor: int = 0
        self.input_decay_weights: Optional[List[float]] = None
        self.previous_inputs: List[float] = []
        
        # Output smoothing
        self.output_smoothing_factor: int = 0
        self.output_decay_weights: Optional[List[float]] = None
        self.previous_outputs: List[float] = []
        
        # Derivative filtering
        self.derivative_filter_level: int = 0
        self.derivative_filter: LiveSosFilter = self.derivativeFilter()
```

### Advanced Features

#### **1. Anti-Windup Protection**
```python
# Integral term clamping prevents control saturation
self.Iterm += self.Ki * err * dt

# Clamp Iterm to output limits
self.Iterm = max(self.outMin, min(self.outMax, self.Iterm))

# Output clamping
if output > self.outMax:
    output = self.outMax
elif output < self.outMin:
    output = self.outMin
```

#### **2. Duty Cycle Optimization**
```python
# Configurable duty cycle parameters
self.dutySteps: int = 1           # Minimum change to trigger control
self.dutyMin: int = 0             # Minimum duty cycle
self.dutyMax: int = 100           # Maximum duty cycle
self.force_duty: int = 3          # Force control update every N cycles

# Prevents excessive control updates
if self.iterations_since_duty >= self.force_duty:
    # Force control update even if no change
    self.control(int_output)
    self.iterations_since_duty = 0
```

#### **3. Measurement-Based Derivative**
```python
# Two derivative calculation modes
self.derivative_on_error = False  # False = measurement-based

if self.derivative_on_error:
    # Traditional derivative on error (can cause derivative kick)
    D = self.Kd * derr
else:
    # Derivative on measurement (avoids derivative kick)
    D = -self.Kd * dtinput
```

### Performance Considerations

#### **Efficient Calculations**
- **Minimal Memory Allocation**: Pre-allocated data structures
- **Conditional Smoothing**: Only compute smoothing when enabled
- **Efficient Filtering**: IIR filter with minimal computational overhead
- **Smart Updates**: Only send control commands when necessary

#### **Thread Safety Optimization**
- **Minimal Critical Sections**: Only protect essential operations
- **Efficient Semaphore Usage**: Single semaphore for all operations
- **Exception Safety**: Guaranteed semaphore release in finally blocks
- **Non-blocking Reads**: Separate methods for state queries

### Integration Points

#### **Main Application Integration**
- **Control Function Interface**: Callback-based output control
- **Parameter Configuration**: Real-time PID tuning
- **State Monitoring**: Active state and output querying
- **Event Integration**: Automatic control updates

#### **Hardware Controller Integration**
- **Duty Cycle Control**: Direct heater control integration
- **Temperature Feedback**: Real-time temperature input processing
- **Output Limiting**: Hardware-specific output constraints
- **Timing Control**: Configurable update frequencies

### Error Handling and Validation

#### **Input Validation**
```python
def update(self, i: Optional[float]) -> None:
    if i == -1 or i is None:
        # Reject error values
        return
    
    # Process valid input
    i = self._smooth_input(i)
    # ... PID calculation
```

#### **Exception Safety**
```python
# Guaranteed resource cleanup
try:
    self.pidSemaphore.acquire(1)
    # Critical operations
except Exception as e:
    _log.exception(e)
finally:
    if self.pidSemaphore.available() < 1:
        self.pidSemaphore.release(1)
```

### Mathematical Foundation

#### **PID Transfer Function**
The controller implements the standard PID transfer function:

```
G(s) = Kp + Ki/s + Kd*s
```

Where:
- **Kp**: Proportional gain (immediate response to error)
- **Ki**: Integral gain (eliminates steady-state error)
- **Kd**: Derivative gain (improves transient response)

#### **Anti-Windup Implementation**
```python
# Integral windup prevention
self.Iterm += self.Ki * err * dt
self.Iterm = max(self.outMin, min(self.outMax, self.Iterm))
```

#### **Derivative Filtering**
```python
# IIR Butterworth low-pass filter
# Cutoff frequency: 0.2 Hz
# Sampling rate: 1 Hz
# Order: 1st order
if self.derivative_filter_level > 0:
    D = self.derivative_filter(D)
```

### Future Enhancement Opportunities

#### **Potential Improvements**
- **Adaptive Tuning**: Automatic PID parameter optimization
- **Advanced Filtering**: Kalman filtering for noise reduction
- **Predictive Control**: Model-based predictive control
- **Fuzzy Logic**: Fuzzy PID control for non-linear systems

#### **Integration Extensions**
- **Machine Learning**: AI-based parameter tuning
- **Cloud Integration**: Remote monitoring and optimization
- **Advanced Protocols**: Support for industrial control protocols
- **Real-Time Optimization**: Online performance optimization

This module represents the mathematical core of Artisan's temperature control system, providing a robust, efficient, and feature-rich PID implementation that serves as the foundation for precise temperature control in coffee roasting applications.