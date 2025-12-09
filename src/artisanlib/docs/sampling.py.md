# Artisan Sampling Dialog Module Documentation

## File: `src/artisanlib/sampling.py`

### Overview
This module implements the **Sampling Configuration Dialog** for the Artisan coffee roasting application. At 127 lines, it provides a focused interface for configuring data sampling parameters, roast completion behavior, and monitoring preferences through a simple, modal dialog system.

### Purpose and Architecture
The `sampling.py` module serves as the **data acquisition configuration interface** for Artisan, implementing:
- **Sampling Rate Configuration**: Adjustable data collection intervals
- **Roast Completion Behavior**: Control over post-roast actions
- **Monitoring Preferences**: Continuous monitoring configuration
- **Settings Persistence**: User preference storage and restoration

### Key Components

#### **Main Dialog: `SamplingDlg`**
```python
class SamplingDlg(ArtisanDialog):
    def __init__(self, parent: 'QWidget', aw: 'ApplicationWindow'):
        # Integrates with main application window
        # Provides sampling configuration interface
```

**Core Features:**
- **Modal Operation**: Blocks interaction with main application during configuration
- **Settings Integration**: Direct access to main application configuration
- **Layout Management**: Organized, user-friendly interface layout
- **Cross-Platform Compatibility**: PyQt5/PyQt6 dual support

### Technical Implementation

#### **Configuration Controls**

**Keep ON Flag**
```python
self.keepOnFlag = QCheckBox(QApplication.translate('Label','Keep ON'))
self.keepOnFlag.setChecked(bool(self.aw.qmc.flagKeepON))
```
- **Purpose**: Controls continuous monitoring after roast completion
- **Integration**: Directly modifies main application flag
- **Behavior**: Determines if monitoring continues post-roast

**Open Completed Roast Flag**
```python
self.openCompletedFlag = QCheckBox(QApplication.translate('Label','Open Completed Roast in Viewer'))
self.openCompletedFlag.setChecked(bool(self.aw.qmc.flagOpenCompleted))
```
- **Purpose**: Controls automatic roast viewer opening
- **Integration**: Manages post-roast workflow
- **User Experience**: Streamlines roast analysis process

**Sampling Interval Control**
```python
self.interval = MyQDoubleSpinBox()
self.interval.setSingleStep(1)
self.interval.setValue(self.aw.qmc.delay/1000.)
self.interval.setRange(self.aw.qmc.min_delay/1000., 40.)
self.interval.setDecimals(2)
self.interval.setSuffix('s')
```
- **Range**: Configurable from minimum delay to 40 seconds
- **Precision**: 2 decimal place accuracy
- **Units**: Seconds (converted from milliseconds internally)
- **Validation**: Enforces minimum and maximum boundaries

#### **Layout Management System**
```python
# Interval layout with centered control
intervalLayout = QHBoxLayout()
intervalLayout.addStretch()
intervalLayout.addWidget(self.interval)
intervalLayout.addStretch()

# Flag layout with grid organization
flagGrid = QGridLayout()
flagGrid.addWidget(self.keepOnFlag, 0, 0)
flagGrid.addWidget(self.openCompletedFlag, 1, 0)

# Main layout composition
layout = QVBoxLayout()
layout.addLayout(intervalLayout)
layout.addLayout(flagLayout)
layout.addStretch()
layout.addLayout(buttonsLayout)
```

**Layout Features:**
- **Centered Controls**: Professional appearance with balanced spacing
- **Grid Organization**: Logical grouping of related controls
- **Flexible Spacing**: Dynamic spacing for different screen sizes
- **Fixed Size Constraint**: Prevents window resizing for consistency

### Configuration Management

#### **Settings Persistence**
```python
def storeSettings(self) -> None:
    # Save window position (only; not size!)
    settings = QSettings()
    settings.setValue('SamplingPosition', self.frameGeometry().topLeft())
```

**Persistence Features:**
- **Position Memory**: Remembers dialog location between sessions
- **Size Consistency**: Maintains fixed dialog size
- **User Preference**: Preserves user's preferred dialog position
- **Cross-Session**: Settings maintained across application restarts

#### **Configuration Application**
```python
@pyqtSlot()
def ok(self) -> None:
    self.aw.qmc.flagKeepON = bool(self.keepOnFlag.isChecked())
    self.aw.qmc.flagOpenCompleted = bool(self.openCompletedFlag.isChecked())
    self.aw.setSamplingRate(int(self.interval.value()*1000.))
    
    # Warning for tight sampling intervals
    if self.aw.qmc.delay < self.aw.qmc.default_delay:
        QMessageBox.warning(None,
            QApplication.translate('Message', 'Warning', None),
            QMessageBox.warning(None,
                QApplication.translate('Message', 'A tight sampling interval might lead to instability on some machines. We suggest a minimum of 1s.'))
```

**Configuration Features:**
- **Real-time Updates**: Immediate application of configuration changes
- **Unit Conversion**: Automatic conversion from seconds to milliseconds
- **Validation Warnings**: User alerts for potentially problematic settings
- **Default Protection**: Warns against overly aggressive sampling rates

### Integration Points

#### **Main Application Integration**
```python
def __init__(self, parent: 'QWidget', aw: 'ApplicationWindow'):
    # Direct access to main application window
    # Modifies global configuration state
    # Integrates with monitoring system
```

**Integration Features:**
- **Configuration Access**: Direct modification of main application flags
- **Sampling Control**: Integration with data acquisition system
- **Monitoring Management**: Control over continuous monitoring behavior
- **Workflow Integration**: Post-roast process management

#### **Quality Management Center Integration**
```python
# Access to QMC (Quality Management Center) configuration
self.aw.qmc.flagKeepON = bool(self.keepOnFlag.isChecked())
self.aw.qmc.flagOpenCompleted = bool(self.openCompletedFlag.isChecked())
self.aw.setSamplingRate(int(self.interval.value()*1000.))
```

**QMC Features:**
- **Flag Management**: Direct modification of QMC configuration flags
- **Sampling Rate Control**: Integration with data collection timing
- **Default Value Access**: Retrieval of system default values
- **Minimum Delay Enforcement**: Respects system-imposed limits

### User Experience Features

#### **Focus Management**
```python
ok_button: Optional[QPushButton] = self.dialogbuttons.button(QDialogButtonBox.StandardButton.Ok)
if ok_button is not None:
    ok_button.setFocus()
```

**Focus Features:**
- **Default Focus**: OK button receives initial focus
- **Logical Navigation**: Intuitive tab order through controls
- **Accessibility**: Proper focus management for keyboard users
- **User Efficiency**: Minimizes mouse movement for common operations

#### **Warning System**
```python
if self.aw.qmc.delay < self.aw.qmc.default_delay:
    QMessageBox.warning(None,
        QApplication.translate('Message', 'Warning', None),
        QApplication.translate('Message', 'A tight sampling interval might lead to instability on some machines. We suggest a minimum of 1s.'))
```

**Warning Features:**
- **Proactive Alerts**: Warns before potential problems occur
- **Educational Content**: Explains why certain settings might be problematic
- **Recommendations**: Provides specific guidance for optimal settings
- **User Protection**: Prevents configuration that could cause system instability

### Technical Considerations

#### **Performance Impact**
- **Sampling Rate Effects**: Higher sampling rates increase CPU usage
- **Data Volume**: Sampling frequency directly affects data storage requirements
- **System Stability**: Aggressive sampling can cause system instability
- **Memory Usage**: More frequent sampling increases memory consumption

#### **Compatibility Features**
- **Cross-Platform**: Works consistently across Windows, macOS, and Linux
- **PyQt Versions**: Supports both PyQt5 and PyQt6
- **Screen Resolutions**: Adapts to different display configurations
- **Accessibility**: Proper focus and navigation management

### Use Cases and Workflows

#### **Typical Configuration Scenarios**

**High-Frequency Monitoring**
- **Use Case**: Detailed roast analysis requiring fine-grained data
- **Configuration**: Sampling interval < 1 second
- **Considerations**: System stability and data volume

**Standard Roasting**
- **Use Case**: Normal roasting operations
- **Configuration**: 1-5 second sampling intervals
- **Benefits**: Balanced performance and data quality

**Batch Roasting**
- **Use Case**: Multiple roasts with continuous monitoring
- **Configuration**: Keep ON flag enabled
- **Workflow**: Seamless transition between roasts

#### **Post-Roast Workflow**
```python
# Automatic roast viewer opening
if self.openCompletedFlag.isChecked():
    # Roast automatically opens in viewer
    # Enables immediate analysis
    # Streamlines workflow
```

**Workflow Features:**
- **Immediate Analysis**: Automatic roast data presentation
- **Workflow Continuity**: Seamless transition from roasting to analysis
- **User Efficiency**: Reduces manual navigation steps
- **Quality Assurance**: Prompts immediate roast review

### Error Handling and Validation

#### **Input Validation**
- **Range Checking**: Enforces minimum and maximum sampling intervals
- **Type Safety**: Ensures proper data type conversion
- **Boundary Enforcement**: Respects system-imposed limits
- **User Feedback**: Clear warnings for problematic configurations

#### **System Protection**
- **Minimum Delay Enforcement**: Prevents overly aggressive sampling
- **Stability Warnings**: Alerts users to potential system issues
- **Default Fallbacks**: System maintains safe default values
- **Graceful Degradation**: System continues operation with safe settings

This module represents a focused, user-friendly interface for configuring one of Artisan's most critical functions - data sampling and monitoring behavior. It balances simplicity with comprehensive functionality, ensuring users can easily configure their roasting environment while being protected from potentially problematic settings.