# Artisan Canvas Module Documentation

## File: `src/artisanlib/canvas.py`

### Overview
This module implements the **core visualization and plotting system** for the Artisan coffee roasting application. At 19,091 lines, it represents one of the largest and most complex modules in the codebase, containing the main plotting canvas, data visualization, event handling, and real-time chart rendering capabilities.

### Purpose and Architecture
The `canvas.py` module serves as the **visualization engine** for Artisan, implementing:
- **Real-time plotting** of temperature curves and roasting data
- **Interactive chart management** with zoom, pan, and selection capabilities
- **Event visualization** and annotation system
- **Background profile management** and comparison
- **Advanced chart features** including projections, statistics, and flavor wheels

### Core Components

#### **Main Canvas Class: `tgraphcanvas`**
- **Inheritance**: Extends `matplotlib.backends.backend_qtagg.FigureCanvasQTAgg`
- **Purpose**: Primary plotting canvas for all roasting data visualization
- **Integration**: Combines matplotlib plotting with PyQt6/PyQt5 GUI framework

#### **Supporting Classes**
1. **`AmbientWorker`**: Background thread for ambient data collection
2. **`tgraphcanvas`**: Main plotting canvas with extensive functionality
3. **Additional utility classes** for specialized plotting operations

### Key Features and Capabilities

#### **1. Real-Time Data Visualization**
```python
# Temperature curve plotting
self.temp1 = []  # ET (Environmental Temperature) data
self.temp2 = []  # BT (Bean Temperature) data
self.timex = []  # Time axis data
self.delta1 = [] # ET Rate of Rise (RoR)
self.delta2 = [] # BT Rate of Rise (RoR)
```

#### **2. Advanced Plotting System**
- **Multi-axis support**: Primary temperature axis + secondary RoR axis
- **Curve management**: Configurable line styles, colors, and markers
- **Background profiles**: Overlay comparison with reference roasts
- **Projection lines**: Future temperature predictions based on current trends

#### **3. Event Visualization**
```python
# Event type management
self.etypes = []  # Event type definitions
self.specialevents = []  # Special event data
self.eventsGraphflag = True  # Show events on graph
self.annotationsflag = True  # Show event annotations
```

#### **4. Interactive Features**
- **Mouse interaction**: Click, drag, and selection capabilities
- **Zoom and pan**: Chart navigation and view management
- **Event editing**: Click-to-add/modify roasting events
- **Context menus**: Right-click actions for various chart elements

### Data Management and Processing

#### **1. Temperature Data Handling**
```python
# Real-time data arrays
self.temp1 = []      # ET temperature readings
self.temp2 = []      # BT temperature readings
self.stemp1 = []     # Smoothed ET data
self.stemp2 = []     # Smoothed BT data
self.ctemp1 = []     # Current ET values
self.ctemp2 = []     # Current BT values
```

#### **2. Rate of Rise Calculations**
```python
# Delta (RoR) computation
self.delta1 = []     # ET Rate of Rise
self.delta2 = []     # BT Rate of Rise
self.unfiltereddelta1 = []  # Raw ET RoR
self.unfiltereddelta2 = []  # Raw BT RoR
```

#### **3. Background Profile Management**
```python
# Background profile data
self.backgroundprofile = None
self.temp1B = []     # Background ET data
self.temp2B = []     # Background BT data
self.timeB = []      # Background time data
self.backgroundEvents = []  # Background event markers
```

### Plotting and Rendering System

#### **1. Core Rendering Method**
```python
def redraw(self, recomputeAllDeltas:bool = True, re_smooth_foreground:bool = True, 
           takelock:bool = True, forceRenewAxis:bool = False, re_smooth_background:bool = False) -> None:
    # Main redraw method with extensive optimization and caching
    # Handles axis recreation, curve plotting, and visual updates
```

#### **2. Chart Configuration**
```python
# Visual styling and configuration
self.palette = {
    'background': '#ffffff',
    'grid': '#e5e5e5',
    'et': '#cc0f50',      # ET curve color
    'bt': '#0a5c90',      # BT curve color
    'deltaet': '#cc0f50', # ET RoR color
    'deltabt': '#0a5c90'  # BT RoR color
}
```

#### **3. Axis Management**
```python
# Dual-axis system
self.ax = None        # Primary temperature axis
self.delta_ax = None  # Secondary RoR axis
self.fig = None       # Matplotlib figure object
```

### Event System and Annotations

#### **1. Event Management**
```python
# Event recording and display
def EventRecord(self, extraevent:Optional[int] = None, takeLock:bool = True) -> None:
    # Records roasting events with timestamps and values

def addEvent(self, event_time_idx:int, event_type:int, event_description:str, event_value:float) -> None:
    # Adds new event to the chart

def deleteEvent(self, event_time_idx:int) -> None:
    # Removes event from the chart
```

#### **2. Event Visualization**
```python
# Event display configuration
self.eventslabelschars = 20  # Maximum characters for event labels
self.showeventsonbt = True   # Show events on BT curve
self.EvalueColor = []        # Event value colors
self.EvalueMarker = []       # Event marker styles
```

#### **3. Interactive Event Editing**
```python
# Mouse interaction for events
def onclick(self, event:'MouseEvent') -> None:
    # Handles mouse clicks for event creation/editing

def onpick(self, event:'PickEvent') -> None:
    # Handles event selection and editing
```

### Background Profile System

#### **1. Profile Loading and Management**
```python
# Background profile operations
def loadbackground(self, filename:str) -> None:
    # Loads background profile for comparison

def deleteBackground(self) -> None:
    # Removes current background profile

def movebackground(self, direction:str, step:int) -> None:
    # Moves background profile for alignment
```

#### **2. Profile Comparison Features**
```python
# Comparison capabilities
self.backgroundETcurve = True    # Show background ET
self.backgroundBTcurve = True    # Show background BT
self.backgroundDetails = True    # Show background details
self.backgroundeventsflag = True # Show background events
```

#### **3. Alignment and Synchronization**
```python
# Profile alignment options
self.alignEvent = 0  # Alignment event (CHARGE, DRY, FCs, etc.)
self.timealign()     # Time-based alignment method
```

### Advanced Chart Features

#### **1. Temperature Projections**
```python
# Future temperature predictions
self.ETprojectFlag = True    # Enable ET projections
self.BTprojectFlag = True    # Enable BT projections
self.projectionconstant = 300  # Projection time constant
```

#### **2. Statistics and Analysis**
```python
# Statistical calculations and display
self.statisticsflags = []    # Statistics display flags
self.AUCbegin = 0            # Area Under Curve start
self.AUCtarget = 0           # AUC target value
self.statisticsheight = 100  # Statistics panel height
```

#### **3. Flavor Wheel Visualization**
```python
# Coffee flavor assessment tools
self.wheelflag = False       # Enable flavor wheel
self.wheelnames = []         # Flavor attribute names
self.segmentlengths = []     # Wheel segment lengths
self.wheelcolor = []         # Wheel color scheme
```

### Performance and Optimization

#### **1. Rendering Optimization**
```python
# Performance tuning
self.optimalSmoothing = True     # Enable optimal smoothing
self.curvefilter = True          # Enable curve filtering
self.median_filter_factor = 0.5  # Median filter strength
```

#### **2. Data Caching**
```python
# Memory management
self.curveVisibilityCache = {}   # Curve visibility cache
self.l_annotations_dict = {}     # Annotation cache
self.l_event_flags_dict = {}     # Event flag cache
```

#### **3. Thread Safety**
```python
# Multi-threading support
self.profileDataSemaphore = QSemaphore(1)  # Data access semaphore
self.updateBackgroundSemaphore = QSemaphore(1)  # Background update semaphore
```

### Integration Points

#### **1. Main Application Window**
```python
# Application integration
self.aw = aw  # ApplicationWindow reference
self.aw.qmc  # Quick Mill Control reference
self.aw.comparator  # Profile comparator
```

#### **2. Device Communication**
```python
# Hardware integration
self.device = None              # Current device
self.device_logging = False     # Device logging state
self.phidgetManager = None      # Phidget device manager
```

#### **3. Settings and Configuration**
```python
# Configuration management
self.mode = 'C'                 # Temperature mode (C/F)
self.LCDdecimalplaces = 1       # LCD decimal precision
self.graphstyle = 1             # Graph style selection
```

### Signal System

#### **1. Qt Signal Definitions**
```python
# Custom signals for UI updates
updategraphicsSignal = pyqtSignal()
updateLargeLCDsSignal = pyqtSignal(str,str,str)
showAlarmPopupSignal = pyqtSignal(str,int)
fileDirtySignal = pyqtSignal()
redrawSignal = pyqtSignal(bool,bool,bool,bool,bool)
```

#### **2. Signal Usage**
```python
# Signal emission for UI updates
def redraw(self, ...) -> None:
    # Emits signals to update various UI components
    self.updategraphicsSignal.emit()
    self.redrawSignal.emit(...)
```

### Error Handling and Validation

#### **1. Data Validation**
```python
# Input validation and sanitization
def is_proper_temp(self, temp:float) -> bool:
    # Validates temperature values

def validate_event_data(self, event_data:dict) -> bool:
    # Validates event data integrity
```

#### **2. Exception Handling**
```python
# Robust error handling
try:
    # Plotting operations
    self.ax.plot(x, y)
except Exception as e:
    _log.exception(f"Plotting error: {e}")
    # Fallback rendering
```

### Memory Management

#### **1. Garbage Collection**
```python
# Memory optimization
import gc
gc.collect()  # Force garbage collection after heavy operations
```

#### **2. Resource Cleanup**
```python
# Proper resource management
def cleanup_resources(self) -> None:
    # Cleans up matplotlib artists and cached data
    self.clear_annotations()
    self.clear_curves()
```

### Platform Compatibility

#### **1. PyQt Version Support**
```python
# Cross-version compatibility
try:
    from PyQt6.QtWidgets import QApplication, QWidget
    from PyQt6.QtCore import pyqtSignal, pyqtSlot
except ImportError:
    from PyQt5.QtWidgets import QApplication, QWidget
    from PyQt5.QtCore import pyqtSignal, pyqtSlot
```

#### **2. Operating System Adaptations**
```python
# Platform-specific behavior
if platform.system() == 'Windows':
    # Windows-specific optimizations
    self.windows_optimizations()
elif platform.system() == 'Darwin':
    # macOS-specific optimizations
    self.macos_optimizations()
```

### Future Enhancement Considerations

#### **1. Performance Improvements**
- **GPU acceleration**: OpenGL rendering for large datasets
- **Data streaming**: Real-time data streaming without full redraws
- **Caching strategies**: Advanced caching for complex visualizations

#### **2. Feature Extensions**
- **3D visualization**: Multi-dimensional roasting data display
- **Machine learning**: AI-powered curve analysis and predictions
- **Cloud integration**: Remote profile sharing and comparison

#### **3. Accessibility Features**
- **Screen reader support**: Enhanced accessibility for visually impaired users
- **Keyboard navigation**: Complete keyboard-based chart interaction
- **High contrast modes**: Enhanced visibility options

This module represents the heart of Artisan's visualization system, providing a sophisticated, real-time plotting engine that handles the complex requirements of coffee roasting data visualization while maintaining performance and usability across different platforms and use cases.