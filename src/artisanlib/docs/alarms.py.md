# Artisan Alarms Dialog Module Documentation

## File: `src/artisanlib/alarms.py`

### Overview
This module implements the **comprehensive Alarms Configuration Dialog** for the Artisan coffee roasting application. At 1,161 lines, it provides an extensive interface for managing sophisticated alarm systems, including conditional alarms, alarm sets, and complex triggering mechanisms that enable precise control over roasting processes.

### Purpose and Architecture
The `alarms.py` module serves as the **central alarm management system** for Artisan, implementing:
- **Conditional Alarm System**: Complex alarm logic with guards and dependencies
- **Alarm Set Management**: Multiple configurable alarm configurations
- **Event-Based Triggering**: Time and condition-based alarm activation
- **Multi-Action Support**: Various alarm responses and actions
- **Import/Export Functionality**: Alarm configuration persistence and sharing

### Key Components

#### 1. **Main Dialog Class: `AlarmDlg`**

##### **Initialization and Layout**
```python
def __init__(self, parent:QWidget, aw:'ApplicationWindow', activeTab:int = 0) -> None:
```
- **Purpose**: Initialize the comprehensive alarm configuration dialog
- **Features**: 
  - Tabbed interface (Alarm Table, Alarm Sets)
  - Modal dialog with persistent geometry
  - Integration with main application window
  - Help system integration

##### **Tab Structure**
- **Tab 1: Alarm Table**: Main alarm configuration interface
- **Tab 2: Alarm Sets**: Alarm set management and storage

#### 2. **Alarm Table System**

##### **Table Structure**
The alarm table contains 12 columns with sophisticated functionality:

1. **Nr**: Row number (auto-generated)
2. **Status**: Enable/disable checkbox
3. **If Alarm**: Guard alarm reference (conditional logic)
4. **But Not**: Negative guard alarm reference
5. **From**: Trigger event selection
6. **Time**: Time offset after trigger event
7. **Source**: Temperature source selection
8. **Condition**: Comparison operator (<, >, =, ≠)
9. **Value**: Temperature threshold
10. **Action**: Alarm response action
11. **Beep**: Audio notification toggle
12. **Description**: User-defined alarm description

##### **Alarm Table Management**
```python
def createalarmtable(self) -> None:
def setalarmtablerow(self, i:int) -> None:
def savealarms(self) -> None:
```

- **Dynamic Row Creation**: Automatic table population from alarm data
- **Widget Integration**: Complex cell widgets for different data types
- **Data Persistence**: Automatic saving of table state
- **Column Management**: Configurable column widths and sorting

#### 3. **Conditional Alarm Logic**

##### **Guard System**
The alarm system implements sophisticated conditional logic:

- **If Alarm**: Primary guard condition - alarm only fires if this alarm is active
- **But Not**: Negative guard condition - alarm is blocked if this alarm is active
- **Dependency Management**: Automatic reference adjustment on insert/delete operations

##### **Trigger Events**
Alarms can be triggered by various roasting events:

- **ON**: Always active
- **START**: Roast start
- **CHARGE**: Bean charge
- **TP**: Turning point
- **DRY END**: Drying phase end
- **FC START**: First crack start
- **FC END**: First crack end
- **SC START**: Second crack start
- **SC END**: Second crack end
- **DROP**: Bean drop
- **COOL**: Cooling phase
- **If Alarm**: Conditional on another alarm

#### 4. **Alarm Actions**

##### **Action Types**
The system supports 30+ different alarm actions:

- **Notifications**: Pop-up dialogs, audio beeps
- **Control Actions**: START, STOP, PID control, ramp/soak
- **Event Marking**: Automatic phase marking
- **Program Control**: External program execution
- **UI Actions**: Canvas color changes, slider control
- **Playback Control**: Profile playback management

##### **Action Implementation**
```python
# Examples of alarm actions
'Pop Up', 'Call Program', 'Event Button', 'Slider BT', 'Slider ET',
'START', 'DRY', 'FCs', 'FCe', 'SCs', 'SCe', 'DROP', 'COOL END',
'OFF', 'CHARGE', 'RampSoak ON/OFF', 'PID ON/OFF', 'SV', 'Playback ON/OFF'
```

#### 5. **Alarm Set Management**

##### **Alarm Set System**
```python
def setAlarmSet(self, _:bool = False) -> None:
def setAlarmTable(self, _:bool = False) -> None:
```

- **Multiple Configurations**: Store and retrieve different alarm setups
- **Profile Integration**: Load alarms from roasting profiles
- **Background Integration**: Load alarms from background profiles
- **Label Management**: User-defined alarm set names

##### **Alarm Set Operations**
- **Store Current**: Save current alarm configuration to selected set
- **Activate Set**: Load selected alarm set into current configuration
- **Profile Loading**: Automatic alarm loading from profiles
- **Background Loading**: Alarm loading from background curves

#### 6. **Data Import/Export**

##### **File Format Support**
```python
def importalarmsJSON(self, filename:str) -> None:
def exportalarmsJSON(self, filename:str) -> bool:
```

- **`.alrm` Files**: Native Artisan alarm format (JSON)
- **`.alog` Files**: Profile-based alarm loading
- **JSON Structure**: Comprehensive alarm data serialization
- **UTF-8 Support**: International character support

##### **Import/Export Features**
- **Complete Data Transfer**: All alarm parameters preserved
- **Format Validation**: Automatic file format detection
- **Error Handling**: Comprehensive error reporting and recovery
- **Data Migration**: Seamless format conversion

#### 7. **Advanced Features**

##### **Table Operations**
```python
def addalarm(self, _:bool = False) -> None:
def insertalarm(self, _:bool = False) -> None:
def deletealarm(self, _:bool = False) -> None:
def clearalarms(self, _:bool = False) -> None:
```

- **Row Management**: Add, insert, delete, clear operations
- **Bulk Operations**: All on/off functionality
- **Selection Handling**: Smart row selection and management
- **Reference Correction**: Automatic guard reference adjustment

##### **Clipboard Integration**
```python
def copyAlarmTabletoClipboard(self, _:bool=False) -> None:
```

- **Tabular Export**: Tab-separated values for spreadsheet import
- **Formatted Export**: Pretty table format for documentation
- **Modifier Key Support**: Alt-click for formatted output
- **System Integration**: Native clipboard support

##### **Configuration Persistence**
- **Column Widths**: Automatic column width preservation
- **Window Geometry**: Dialog position and size persistence
- **Settings Integration**: QSettings-based configuration storage
- **Profile Integration**: Alarm loading from roasting profiles

### Technical Implementation Details

#### **Widget Integration**
- **Custom Table Items**: Specialized table items for different data types
- **Cell Widgets**: Complex input controls embedded in table cells
- **Validation**: Input validation for numeric and time fields
- **Sorting**: Custom sorting algorithms for different data types

#### **Data Management**
- **State Tracking**: Comprehensive alarm state management
- **Reference Management**: Automatic guard reference adjustment
- **Data Synchronization**: Real-time table-data synchronization
- **Error Recovery**: Robust error handling and recovery

#### **Performance Optimizations**
- **Lazy Loading**: Table population only when needed
- **Efficient Updates**: Minimal table redraws
- **Memory Management**: Proper cleanup of table resources
- **Sorting Optimization**: Efficient table sorting algorithms

### Integration Points

#### **Main Application**
- **Event System**: Integration with roasting event system
- **Profile Management**: Alarm loading from roasting profiles
- **Settings System**: Configuration persistence
- **Error Reporting**: Centralized error handling

#### **Roasting Workflow**
- **Phase Detection**: Automatic phase-based alarm triggering
- **Temperature Monitoring**: Real-time temperature-based alarms
- **Event Marking**: Automatic event marking from alarms
- **Process Control**: Alarm-based roasting process control

#### **Plugin System**
- **Action Extensions**: Plugin-defined alarm actions
- **Data Sources**: Plugin-provided temperature sources
- **Event Integration**: Plugin event integration
- **Configuration Sharing**: Plugin configuration persistence

### Configuration and Customization

#### **Alarm Parameters**
- **Temperature Thresholds**: Configurable temperature values
- **Time Offsets**: Flexible time-based triggering
- **Guard Conditions**: Complex conditional logic
- **Action Selection**: Comprehensive action options

#### **User Interface**
- **Column Customization**: Adjustable column widths
- **Sorting Options**: Multiple sorting criteria
- **Selection Behavior**: Configurable selection modes
- **Visual Feedback**: Status-based visual indicators

#### **System Integration**
- **Profile Loading**: Automatic alarm loading from profiles
- **Background Integration**: Background curve alarm loading
- **File Management**: Comprehensive file import/export
- **Settings Persistence**: Automatic configuration saving

### Best Practices and Usage

#### **Alarm Design**
- **Logical Structure**: Use guard conditions for complex logic
- **Event Selection**: Choose appropriate trigger events
- **Action Planning**: Plan alarm responses carefully
- **Testing**: Test alarm configurations thoroughly

#### **Performance Considerations**
- **Alarm Count**: Limit total number of active alarms
- **Complexity**: Avoid overly complex guard conditions
- **Resource Usage**: Monitor system resource consumption
- **Testing**: Validate alarm configurations

#### **Maintenance**
- **Regular Review**: Periodically review alarm configurations
- **Documentation**: Document complex alarm logic
- **Backup**: Regular backup of alarm configurations
- **Updates**: Keep alarm configurations current

### Future Enhancements

#### **Planned Improvements**
- **Advanced Logic**: More complex conditional expressions
- **Scheduling**: Time-based alarm scheduling
- **Notifications**: Enhanced notification system
- **Integration**: Better external system integration

#### **Extensibility Features**
- **Plugin Actions**: Plugin-defined alarm actions
- **Custom Conditions**: User-defined alarm conditions
- **Advanced Triggers**: Complex trigger combinations
- **Reporting**: Comprehensive alarm reporting

This module represents Artisan's sophisticated alarm management system, providing professional-grade alarm capabilities that enable precise control over roasting processes while maintaining ease of use and comprehensive configuration options.