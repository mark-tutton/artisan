# Artisan Axis Configuration Dialog Module Documentation

## File: `src/artisanlib/axis.py`

### Overview
This module implements the **comprehensive Axis Configuration Dialog** for the Artisan coffee roasting application. At 978 lines, it provides an extensive interface for configuring all aspects of chart axes, grid systems, and visualization parameters that control how roasting data is displayed and analyzed.

### Purpose and Architecture
The `axis.py` module serves as the **central visualization configuration hub** for Artisan, implementing:
- **Multi-Axis Management**: Time (X), Temperature (Y), and Delta (Z) axis configuration
- **Grid System Control**: Comprehensive grid styling and behavior management
- **Automatic Scaling**: Intelligent axis scaling based on profile data
- **Visual Customization**: Extensive visual parameter configuration
- **Profile Integration**: Axis settings integration with roasting profiles

### Key Components

#### 1. **Main Dialog Class: `WindowsDlg`**

##### **Initialization and State Management**
```python
def __init__(self, parent:'QWidget', aw:'ApplicationWindow') -> None:
```
- **Purpose**: Initialize the comprehensive axis configuration dialog
- **Features**: 
  - State preservation for undo/restore functionality
  - Modal dialog with persistent positioning
  - Integration with main application window
  - Comprehensive parameter tracking

##### **State Preservation System**
The dialog maintains original values for all configurable parameters:
```python
self.time_grid_org = self.aw.qmc.time_grid
self.temp_grid_org = self.aw.qmc.temp_grid
self.gridlinestyle_org = self.aw.qmc.gridlinestyle
# ... extensive state tracking for all parameters
```

#### 2. **Time Axis (X-Axis) Configuration**

##### **Time Range Control**
- **Maximum Time**: Configurable end time for time axis
- **Minimum Time**: Configurable start time for time axis
- **Time Format**: MM:SS format with validation
- **Relative Positioning**: Time values relative to CHARGE event

##### **Automatic Time Management**
```python
def autoAxis(self, _:bool = False) -> None:
```
- **Auto Scaling**: Automatic time axis calculation based on profile data
- **Mode Selection**: 
  - **Roast**: Time axis covers only roasting period
  - **BBP+Roast**: Includes before/after roasting period
  - **BBP**: Only before/after roasting period
- **Profile Integration**: Automatic calculation from background profiles

##### **Time Axis Features**
- **Grid Steps**: Configurable time grid intervals (1min, 2min, 3min, 4min, 5min, 10min, 30min, 1hour)
- **Recording Control**: Minimum recording time configuration
- **Reset Behavior**: Maximum time on recording start
- **Expansion Control**: Automatic time axis extension when needed

#### 3. **Temperature Axis (Y-Axis) Configuration**

##### **Temperature Range Control**
- **Maximum Temperature**: Upper temperature limit
- **Minimum Temperature**: Lower temperature limit
- **Validation**: Ensures max > min temperature
- **Unit Support**: Celsius and Fahrenheit support

##### **Temperature Grid System**
- **Grid Steps**: Configurable temperature grid intervals (0-500°C/°F)
- **Grid Display**: Toggle temperature grid visibility
- **Step Mode**: 100% event step alignment configuration
- **Profile Integration**: Automatic loading from profiles

##### **Step Mode Configuration**
```python
def step100Changed(self) -> None:
```
- **100% Event Alignment**: Aligns 100% event values with specified Y-axis value
- **Phase Limit Integration**: Uses lowest phase limit if no value specified
- **Dynamic Adjustment**: Real-time step mode configuration

#### 4. **Delta Axis (Z-Axis) Configuration**

##### **Delta Range Control**
- **Maximum Delta**: Upper delta temperature limit
- **Minimum Delta**: Lower delta temperature limit
- **Validation**: Ensures max > min delta
- **Auto Scaling**: Automatic delta axis calculation

##### **Automatic Delta Management**
```python
def autoDeltaAxis(self, _:bool = False) -> None:
```
- **ET Auto Scaling**: Automatic scaling based on DeltaET values
- **BT Auto Scaling**: Automatic scaling based on DeltaBT values
- **Background Integration**: Delta calculation from background profiles
- **Grid Optimization**: Automatic grid step calculation

##### **Delta Grid System**
- **Grid Steps**: Configurable delta grid intervals (0-100°C/°F)
- **Auto Grid Calculation**: Intelligent grid step sizing
- **Profile Integration**: Background profile delta calculation

#### 5. **Grid System Configuration**

##### **Grid Display Control**
- **Time Grid**: Toggle time grid visibility
- **Temperature Grid**: Toggle temperature grid visibility
- **Grid Style**: Line style selection (solid, dashed, dashed-dot, dotted)
- **Grid Width**: Configurable line thickness (1-5 pixels)
- **Grid Opacity**: Configurable transparency (0.1-1.0)

##### **Grid Styling**
```python
def changegridstyle(self, _:int) -> None:
def changegridwidth(self, _:int) -> None:
def changegridalpha(self, _:int) -> None:
```
- **Style Selection**: Multiple grid line styles
- **Width Control**: Adjustable line thickness
- **Opacity Control**: Configurable transparency levels
- **Real-time Updates**: Immediate visual feedback

#### 6. **Legend and Visual Configuration**

##### **Legend Positioning**
```python
def changelegendloc(self, _:int) -> None:
```
- **Location Options**: 12 different legend positions
- **Dynamic Positioning**: Real-time legend location changes
- **Profile Integration**: Legend settings from profiles
- **Comparator Support**: Legend management for comparison views

##### **Visual Customization**
- **Chart Redraw**: Automatic chart updates on parameter changes
- **Cross Marker Support**: Cross-line marker adjustment
- **Navigation History**: Matplotlib navigation reset
- **Profile Integration**: Background profile support

#### 7. **Advanced Features**

##### **Locking and Automation**
- **Time Axis Locking**: Prevent automatic time axis adjustment
- **Auto Time Scaling**: Automatic time axis calculation
- **Auto Delta Scaling**: Automatic delta axis calculation
- **Profile Loading**: Automatic axis settings from profiles

##### **Profile Integration**
```python
def updatewindow(self) -> None:
```
- **Background Profiles**: Axis calculation from background curves
- **Foreground Profiles**: Axis calculation from active profiles
- **Profile Loading**: Automatic axis settings on profile load
- **Settings Persistence**: Axis configuration persistence

##### **Validation and Error Handling**
- **Input Validation**: Comprehensive input validation for all fields
- **Range Checking**: Ensures logical parameter relationships
- **Error Recovery**: Graceful handling of invalid inputs
- **State Restoration**: Complete state restoration on cancel

### Technical Implementation Details

#### **Input Validation System**
- **Regular Expressions**: Time format validation (MM:SS)
- **Range Validators**: Numeric range validation for all parameters
- **Type Conversion**: Robust string-to-value conversion
- **Error Handling**: Comprehensive exception handling

#### **Real-time Updates**
- **Signal Handling**: Qt signal-based parameter updates
- **Chart Redraw**: Automatic chart updates on parameter changes
- **State Synchronization**: Real-time state synchronization
- **Performance Optimization**: Efficient update mechanisms

#### **State Management**
- **Original Value Tracking**: Complete state preservation
- **Undo/Restore**: Full state restoration capability
- **Settings Persistence**: QSettings-based configuration storage
- **Window Positioning**: Persistent dialog positioning

### Integration Points

#### **Main Application**
- **Chart System**: Direct integration with main chart display
- **Profile Management**: Axis settings from roasting profiles
- **Settings System**: Configuration persistence and management
- **Error Reporting**: Centralized error handling

#### **Roasting Workflow**
- **Event System**: Time axis based on roasting events
- **Phase Detection**: Automatic phase-based scaling
- **Profile Loading**: Axis settings from loaded profiles
- **Background Integration**: Background curve axis calculation

#### **Visualization System**
- **Matplotlib Integration**: Direct chart redraw control
- **Grid Management**: Comprehensive grid system control
- **Legend System**: Legend positioning and management
- **Navigation Control**: Chart navigation history management

### Configuration and Customization

#### **Axis Parameters**
- **Time Ranges**: Configurable start and end times
- **Temperature Ranges**: Configurable temperature limits
- **Delta Ranges**: Configurable delta temperature limits
- **Grid Intervals**: Configurable grid step sizes

#### **Visual Parameters**
- **Grid Styling**: Line styles, widths, and opacity
- **Grid Visibility**: Individual grid system control
- **Legend Positioning**: 12 different legend locations
- **Chart Updates**: Real-time visual feedback

#### **Behavioral Parameters**
- **Auto Scaling**: Automatic axis calculation modes
- **Locking**: Manual vs. automatic axis control
- **Profile Integration**: Automatic settings from profiles
- **Expansion Control**: Dynamic axis extension

### Best Practices and Usage

#### **Axis Configuration**
- **Logical Ranges**: Ensure min < max for all axes
- **Grid Optimization**: Choose appropriate grid step sizes
- **Auto Scaling**: Use automatic scaling for optimal display
- **Profile Integration**: Leverage profile-based settings

#### **Performance Considerations**
- **Grid Density**: Avoid overly dense grid systems
- **Update Frequency**: Balance responsiveness with performance
- **Profile Loading**: Efficient profile integration
- **Memory Management**: Proper resource cleanup

#### **User Experience**
- **Visual Feedback**: Immediate updates on parameter changes
- **State Preservation**: Complete undo/restore capability
- **Validation**: Clear input validation and error messages
- **Persistence**: Automatic configuration saving

### Future Enhancements

#### **Planned Improvements**
- **Advanced Scaling**: More sophisticated auto-scaling algorithms
- **Grid Templates**: Predefined grid configuration templates
- **Profile Comparison**: Enhanced multi-profile axis management
- **Export/Import**: Axis configuration sharing

#### **Extensibility Features**
- **Plugin Integration**: Plugin-defined axis behaviors
- **Custom Grids**: User-defined grid patterns
- **Advanced Validation**: Enhanced parameter validation
- **Performance Optimization**: Improved update mechanisms

This module represents Artisan's comprehensive axis configuration system, providing professional-grade chart customization capabilities that enable precise control over data visualization while maintaining ease of use and comprehensive configuration options.