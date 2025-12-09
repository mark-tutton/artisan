# Artisan Events Dialog Module Documentation

## File: `src/artisanlib/events.py`

### Overview
This module implements the **comprehensive Events Configuration Dialog** for the Artisan coffee roasting application. At 3,805 lines, it provides an extensive interface for configuring all aspects of roasting events, custom buttons, sliders, quantifiers, and event annotations through a sophisticated tabbed interface system.

### Purpose and Architecture
The `events.py` module serves as the **central event management system** for Artisan, implementing:
- **Event Type Configuration**: Custom event types, labels, and visual representations
- **Custom Button Management**: User-defined event buttons with actions and styling
- **Slider Control System**: Real-time control sliders with mathematical transformations
- **Event Quantifiers**: Automated event detection based on temperature thresholds
- **Event Annotations**: Custom text annotations and visual markers
- **Palette Management**: Configurable button and slider palettes for different roasting scenarios

### Core Classes

#### **`EventsDlg` (Main Dialog Class)**
The primary events configuration dialog with 7 specialized tabs:

**Tab 1: Config**
- Event button visibility and display options
- Automatic event detection (CHARGE, DROP, TP, MET)
- Event type labels and color schemes
- Time guide and annotation settings

**Tab 2: Buttons**
- Custom event button creation and management
- Button layout configuration (rows, sizes, colors)
- Button action types (Serial, Modbus, DTA, etc.)
- Drag-and-drop button reordering

**Tab 3: Palettes**
- Button palette management and switching
- Palette backup/restore functionality
- Keyboard shortcuts for palette switching

**Tab 4: Style**
- Event visualization styling (colors, markers, thickness)
- Opacity and marker size controls
- Text color customization

**Tab 5: Sliders**
- Real-time control slider configuration
- Mathematical transformations (factor/offset)
- Bernoulli gas law calculations
- Temperature interpretation and units

**Tab 6: Quantifiers**
- Automated event detection based on temperature curves
- Source curve selection (ET, BT, extra devices)
- Threshold-based event triggering
- Slider action integration

**Tab 7: Annotations**
- Custom event annotation text
- Pre/post first crack annotation handling
- Annotation overlap management

### Key Features

#### **Event Button System**
```python
# Custom button configuration
self.extraeventslabels: List[str] = []
self.extraeventsdescriptions: List[str] = []
self.extraeventstypes: List[int] = []
self.extraeventsvalues: List[float] = []
self.extraeventsactions: List[int] = []
```

#### **Slider Control System**
```python
# Slider mathematical transformations
self.eventsliderfactors: List[float] = [1.0, 1.0, 1.0, 1.0]
self.eventslideroffsets: List[float] = [0., 0., 0., 0.]
self.eventsliderBernoulli: List[int] = [0, 0, 0, 0]  # Gas law calculations
```

#### **Event Quantifiers**
```python
# Automated event detection
self.eventquantifieractive: List[int] = [0, 0, 0, 0]
self.eventquantifiersource: List[int] = [0, 0, 0, 0]
self.eventquantifiermin: List[int] = [0, 0, 0, 0]
self.eventquantifiermax: List[int] = [100, 100, 100, 100]
```

#### **Palette Management**
```python
# Configurable button palettes
self.buttonpalette: List[Palette] = []
self.buttonpalettemaxlen: List[int] = [self.aw.buttonpalettemaxlen_default] * self.aw.max_palettes
self.buttonpalette_buttonsize: List[int] = [self.aw.buttonsize_default] * self.aw.max_palettes
```

### Advanced Functionality

#### **Mathematical Transformations**
- **Factor/Offset Calculations**: Linear transformations for slider values
- **Bernoulli Gas Law**: Pressure-based calculations for gas flow control
- **Slider Calculator**: Built-in tool for computing transformation parameters

#### **Event Detection Algorithms**
- **Temperature Threshold Monitoring**: Real-time curve analysis
- **Change Detection**: Prevents duplicate events from noise
- **Curve Source Selection**: Multiple temperature curve inputs

#### **Visual Customization**
- **Marker Styles**: Circle, square, pentagon, diamond, star, hexagon
- **Color Schemes**: HSV-based color generation with contrast optimization
- **Layout Options**: Alternative slider layouts and keyboard controls

### Integration Points

#### **Main Application**
- **Event Registration**: Integrates with main roasting workflow
- **Button Visibility**: Controls button display during roasting sessions
- **Action Execution**: Triggers hardware commands and external actions

#### **Canvas System**
- **Event Rendering**: Displays events on temperature curves
- **Annotation Positioning**: Manages text and marker placement
- **Visual Updates**: Triggers chart redraws when events change

#### **Communication Layer**
- **Hardware Control**: Executes device commands via sliders
- **External Actions**: Triggers programs, serial commands, and network actions
- **Real-time Updates**: Maintains synchronization with hardware state

### Configuration Management

#### **Settings Persistence**
```python
def storeState(self) -> None:
    # Stores current configuration for potential restoration
    self.eventsbuttonflagstored = self.aw.eventsbuttonflag
    self.extraeventslabels = self.aw.extraeventslabels[:]
    # ... extensive state storage
```

#### **Palette Operations**
```python
def transferbuttonsto(self, pindex: Optional[int] = None) -> None:
    # Saves current configuration to selected palette
    copy: Palette = (
        self.extraeventstypes[:],
        self.extraeventsvalues[:],
        # ... comprehensive palette data
    )
```

### Error Handling and Validation

#### **Input Validation**
- **Range Checking**: Ensures slider values are within valid bounds
- **Type Safety**: Validates event types and action parameters
- **Data Integrity**: Prevents invalid configurations from being saved

#### **State Management**
- **Configuration Backup**: Stores original settings for restoration
- **Change Tracking**: Monitors modifications across all tabs
- **Rollback Support**: Allows cancellation of unsaved changes

### Performance Considerations

#### **Efficient Updates**
- **Selective Redraws**: Only redraws affected chart areas
- **Batch Operations**: Groups multiple configuration changes
- **Lazy Loading**: Defers expensive operations until needed

#### **Memory Management**
- **List Slicing**: Uses copy operations for state management
- **Widget Recycling**: Reuses UI components where possible
- **Event Disconnection**: Properly manages signal connections

### Internationalization

#### **Multi-language Support**
```python
# Translation support for all UI elements
QApplication.translate('Label', 'Event')
QApplication.translate('ComboBox', 'Serial Command')
QApplication.translate('Tooltip', 'Action type to fire when the button is clicked')
```

#### **Locale Handling**
- **Number Formatting**: Supports different decimal separators
- **Text Direction**: Handles right-to-left languages
- **Cultural Adaptations**: Adjusts UI for different regions

### Security and Safety

#### **Input Sanitization**
- **Command Validation**: Prevents injection attacks in action strings
- **Range Limits**: Enforces safe operating parameters
- **Type Checking**: Validates all user inputs

#### **Hardware Protection**
- **Command Filtering**: Sanitizes device control commands
- **Safety Limits**: Prevents dangerous hardware configurations
- **Error Recovery**: Graceful handling of communication failures

### Extension Points

#### **Plugin Integration**
- **Action Types**: Extensible action system for custom behaviors
- **Event Sources**: Support for additional temperature sensors
- **Custom Commands**: User-defined action implementations

#### **Customization Options**
- **Button Layouts**: Configurable grid arrangements
- **Color Schemes**: User-defined visual themes
- **Event Types**: Extensible event classification system

### Testing and Debugging

#### **Development Tools**
- **State Inspection**: Comprehensive configuration debugging
- **Event Logging**: Detailed event execution tracking
- **Validation Tools**: Built-in configuration verification

#### **Error Reporting**
- **Exception Handling**: Comprehensive error capture and reporting
- **User Feedback**: Clear error messages and recovery suggestions
- **Debug Information**: Detailed logging for troubleshooting

### Future Enhancements

#### **Planned Features**
- **Advanced Event Patterns**: Complex event detection algorithms
- **Machine Learning**: AI-powered event prediction
- **Cloud Integration**: Remote event monitoring and control
- **Mobile Support**: Touch-optimized interface elements

This module represents the most sophisticated event management system in Artisan, providing professional roasters with unparalleled control over their roasting workflow through a combination of manual controls, automated detection, and extensive customization options.