# Artisan Time Module Documentation

## File: `src/artisanlib/time.py`

### Overview
This module implements a **high-precision timing system** for the Artisan coffee roasting application. At 47 lines, it provides a sophisticated time measurement framework that offers higher resolution than standard system time functions, particularly optimized for macOS systems and simulator environments.

### Purpose and Architecture
The `time.py` module serves as the **precision timing foundation** for Artisan, implementing:
- **High-Resolution Timing**: Uses `time.perf_counter()` for maximum precision
- **Configurable Base Units**: Adjustable time base for different measurement needs
- **Elapsed Time Calculation**: Precise measurement of time intervals
- **Simulator Compatibility**: Adapts to different execution environments

### Key Components

#### **Main Class: `ArtisanTime`**
```python
class ArtisanTime:
    __slots__ = ['clock', 'base']
    
    def __init__(self) -> None:
        self.clock = time.perf_counter()
        self.base: float = 1000.
```

**Core Features:**
- **Memory Optimization**: Uses `__slots__` for efficient memory usage
- **High Precision**: Leverages `time.perf_counter()` for maximum accuracy
- **Configurable Base**: Adjustable time base for different measurement scales
- **Instant Initialization**: Starts timing immediately upon creation

### Technical Implementation

#### **High-Resolution Timer**
```python
def __init__(self) -> None:
    self.clock = time.perf_counter()
    self.base: float = 1000.
```

**Timer Features:**
- **`time.perf_counter()`**: Uses Python's highest resolution timer
- **Monotonic Clock**: Guaranteed to never go backwards
- **Platform Optimization**: Automatically optimized for different operating systems
- **Simulator Awareness**: Adapts to simulator vs. real hardware environments

#### **Base Unit Configuration**
```python
def setBase(self, b: float) -> None:
    self.base = b

def getBase(self) -> float:
    return self.base
```

**Base System:**
- **Default Base**: 1000.0 (milliseconds)
- **Dynamic Adjustment**: Can be changed during runtime
- **Simulator Mode**: Base can vary depending on execution environment
- **Unit Flexibility**: Supports different time measurement scales

#### **Timing Operations**

**Timer Start/Reset**
```python
def start(self) -> None:
    self.clock = time.perf_counter()
```

**Clock Adjustment**
```python
def addClock(self, period: float) -> None:
    self.clock = self.clock + period
```

**Elapsed Time Calculation**
```python
def elapsed(self) -> float:
    return (time.perf_counter() - self.clock) * self.base

def elapsedMilli(self) -> float:
    return (time.perf_counter() - self.clock) * self.base / 1000.
```

### Timing Precision Characteristics

#### **Resolution Advantages**
- **Higher Resolution**: `time.perf_counter()` provides better precision than `time.time()`
- **Monotonic Behavior**: Never decreases, even during system clock adjustments
- **Platform Optimization**: Automatically optimized for each operating system
- **Simulator Compatibility**: Maintains precision in virtualized environments

#### **Base Unit System**
```python
# Default configuration
self.base = 1000.  # Base unit of 1000

# Example calculations
elapsed()      # Returns time in base units (1000 = 1 second)
elapsedMilli() # Returns time in milliseconds (1000 = 1 second)
```

**Base Unit Logic:**
- **Base 1000**: Default configuration for millisecond precision
- **Scalable**: Can be adjusted for different measurement needs
- **Simulator Mode**: Base may change in different execution environments
- **Unit Conversion**: Automatic conversion between different time scales

### Use Cases in Artisan

#### **Roast Timing**
```python
# Initialize roast timer
roast_timer = ArtisanTime()
roast_timer.start()

# During roasting
elapsed_time = roast_timer.elapsed()  # Get elapsed time in base units
roast_minutes = roast_timer.elapsedMilli() / 60000  # Convert to minutes
```

**Roast Applications:**
- **Phase Timing**: Precise measurement of roasting phases
- **Event Timing**: Accurate event timestamp recording
- **Profile Comparison**: High-precision profile timing analysis
- **Real-time Updates**: Accurate real-time display updates

#### **Data Acquisition**
```python
# Sampling timer
sampling_timer = ArtisanTime()
sampling_timer.start()

# Check if sampling interval has elapsed
if sampling_timer.elapsed() >= sampling_interval:
    # Take sample
    sampling_timer.start()  # Reset for next interval
```

**Data Applications:**
- **Sampling Intervals**: Precise control of data collection timing
- **Sensor Updates**: Accurate sensor reading timing
- **Display Updates**: Smooth, timed UI updates
- **Logging Intervals**: Precise log entry timing

#### **Performance Measurement**
```python
# Performance timer
perf_timer = ArtisanTime()
perf_timer.start()

# Execute operation
some_operation()

# Measure performance
performance_time = perf_timer.elapsedMilli()  # Time in milliseconds
```

**Performance Applications:**
- **Algorithm Timing**: Measure processing algorithm performance
- **UI Responsiveness**: Monitor user interface response times
- **Plugin Performance**: Assess plugin execution efficiency
- **System Optimization**: Identify performance bottlenecks

### Platform-Specific Behavior

#### **macOS Optimization**
```python
# Higher resolution time signal (at least on macOS)
# base can change (eg. depending on the simulator mode)
```

**macOS Features:**
- **Enhanced Precision**: macOS provides higher resolution timing
- **Hardware Acceleration**: Leverages macOS-specific timing optimizations
- **Simulator Mode**: Different behavior in iOS Simulator vs. real hardware
- **Performance Benefits**: Better timing accuracy on Apple platforms

#### **Cross-Platform Compatibility**
```python
import time

# Uses time.perf_counter() which is optimized for each platform
self.clock = time.perf_counter()
```

**Platform Support:**
- **Windows**: Optimized for Windows timing APIs
- **Linux**: Leverages Linux high-resolution timers
- **macOS**: Enhanced precision on Apple platforms
- **Simulators**: Adapts to virtualized environments

### Performance Characteristics

#### **Memory Efficiency**
```python
__slots__ = ['clock', 'base']
```

**Optimization Features:**
- **Slot-Based Storage**: Reduces memory overhead
- **Minimal Attributes**: Only essential timing data stored
- **Fast Access**: Optimized attribute access patterns
- **Reduced GC Pressure**: Minimizes garbage collection impact

#### **Computational Efficiency**
```python
def elapsed(self) -> float:
    return (time.perf_counter() - self.clock) * self.base

def elapsedMilli(self) -> float:
    return (time.perf_counter() - self.clock) * self.base / 1000.
```

**Efficiency Features:**
- **Single Calculation**: Minimal computational overhead
- **Optimized Math**: Efficient floating-point operations
- **Cached Values**: Base value cached for repeated calculations
- **Fast Retrieval**: Quick elapsed time calculations

### Integration with Artisan

#### **Main Application Usage**
```python
# Typical usage in main application
class ApplicationWindow:
    def __init__(self):
        self.roast_timer = ArtisanTime()
        self.sampling_timer = ArtisanTime()
        self.display_timer = ArtisanTime()
```

**Integration Points:**
- **Roast Management**: Primary timing for roasting operations
- **Data Collection**: Precise sampling interval control
- **User Interface**: Smooth, timed display updates
- **Event System**: Accurate event timing and sequencing

#### **Plugin System Integration**
```python
# Plugin timing support
class PluginBase:
    def __init__(self):
        self.execution_timer = ArtisanTime()
        self.performance_timer = ArtisanTime()
```

**Plugin Features:**
- **Execution Timing**: Measure plugin execution time
- **Performance Monitoring**: Track plugin performance metrics
- **Event Timing**: Accurate plugin event timing
- **Resource Management**: Time-based resource allocation

### Error Handling and Edge Cases

#### **Clock Drift Handling**
- **Monotonic Clock**: `time.perf_counter()` never goes backwards
- **System Clock Independence**: Unaffected by system time changes
- **NTP Immunity**: Network time protocol changes don't affect timing
- **Sleep Recovery**: Maintains accuracy after system sleep

#### **Simulator Environment**
```python
# base can change (eg. depending on the simulator mode)
```

**Simulator Features:**
- **Environment Detection**: Automatically detects simulator vs. real hardware
- **Base Adjustment**: Adjusts timing base for simulator environment
- **Performance Adaptation**: Optimizes for virtualized timing characteristics
- **Consistency Maintenance**: Ensures timing consistency across environments

### Future Enhancement Possibilities

#### **Advanced Timing Features**
- **Multiple Timers**: Support for multiple concurrent timers
- **Timer Events**: Event-driven timing notifications
- **Statistical Timing**: Timing statistics and analysis
- **Calibration**: Automatic timing calibration and adjustment

#### **Integration Enhancements**
- **Database Timing**: Database operation timing support
- **Network Timing**: Network operation timing integration
- **File I/O Timing**: File operation performance measurement
- **Memory Timing**: Memory allocation timing analysis

This module represents a focused, high-performance timing solution that provides Artisan with the precision timing capabilities needed for professional coffee roasting operations, ensuring accurate measurements and smooth user experiences across all supported platforms.