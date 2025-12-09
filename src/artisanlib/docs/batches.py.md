# Artisan Batch Management Dialog Module Documentation

## File: `src/artisanlib/batches.py`

### Overview
This module implements the **Batch Management Dialog** for the Artisan coffee roasting application. It provides a simple but essential interface for configuring batch numbering systems, enabling roasters to maintain organized records of their roasting sessions with sequential numbering and customizable prefixes.

### Purpose and Architecture
The `batches.py` module serves as the **batch counter configuration system**, allowing users to:
- **Enable/disable batch counting** for roasting sessions
- **Set custom prefixes** for batch identification
- **Configure sequential counters** for automatic numbering
- **Protect batch counters** from being overwritten by settings files
- **Maintain roasting session organization** through systematic naming

### Core Components

#### **Main Dialog Class: `batchDlg`**
- **Inheritance**: Extends `ArtisanDialog` (custom dialog base class)
- **Modal Behavior**: Blocks interaction with parent window during configuration
- **Fixed Size**: Dialog size is constrained to prevent resizing
- **Position Persistence**: Remembers dialog position across sessions

#### **Key UI Elements**
1. **Batch Counter Toggle**: Checkbox to enable/disable batch counting
2. **Prefix Configuration**: Text input for custom batch naming
3. **Counter Management**: Spinbox for sequential numbering
4. **Protection Settings**: Checkbox to prevent counter overwrites
5. **Descriptive Labels**: User guidance and information display

### Configuration Features

#### **1. Batch Counter System**
```python
# Core batch functionality
self.batchcheckbox = QCheckBox()
self.batchcheckbox.setToolTip('ON/OFF batch counter')
if self.aw.qmc.batchcounter > -1:
    self.batchcheckbox.setChecked(True)
else:
    self.batchcheckbox.setChecked(False)
```

#### **2. Prefix Management**
```python
# Custom batch naming
self.prefixEdit = QLineEdit(self.aw.qmc.batchprefix)
self.prefixEdit.setToolTip('Batch prefix')
```

#### **3. Sequential Counter**
```python
# Numeric sequence management
self.counterSpinBox = QSpinBox()
self.counterSpinBox.setRange(0, 999999)
self.counterSpinBox.setSingleStep(1)
self.counterSpinBox.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)
```

#### **4. Counter Protection**
```python
# Prevent accidental overwrites
self.neverOverwriteCheckbox = QCheckBox()
self.neverOverwriteCheckbox.setToolTip('If ticked, the batch counter is never modified by loading a settings file')
if self.aw.qmc.neverUpdateBatchCounter:
    self.neverOverwriteCheckbox.setChecked(True)
```

### Data Flow and State Management

#### **1. Configuration Loading**
```python
# Load current settings from QMC
self.prefixEdit.setText(self.aw.qmc.batchprefix)
if self.aw.qmc.batchcounter > -1:
    self.counterSpinBox.setValue(int(round(self.aw.qmc.batchcounter)))
    self.counterSpinBox.setEnabled(True)
    self.prefixEdit.setEnabled(True)
    self.neverOverwriteCheckbox.setEnabled(True)
```

#### **2. Configuration Saving**
```python
def batchChanged(self) -> None:
    self.aw.qmc.batchprefix = self.prefixEdit.text()
    if self.batchcheckbox.isChecked():
        self.aw.qmc.batchcounter = self.counterSpinBox.value()
    else:
        self.aw.qmc.batchcounter = -1
        self.aw.qmc.batchsequence = 1
    self.aw.qmc.neverUpdateBatchCounter = bool(self.neverOverwriteCheckbox.isChecked())
```

#### **3. Dynamic UI State Management**
```python
@pyqtSlot(int)
def toggleCounterFlag(self, _: int) -> None:
    if self.batchcheckbox.isChecked():
        self.prefixEdit.setEnabled(True)
        self.counterSpinBox.setEnabled(True)
        self.neverOverwriteCheckbox.setEnabled(True)
    else:
        self.prefixEdit.setEnabled(False)
        self.counterSpinBox.setEnabled(False)
        self.neverOverwriteCheckbox.setEnabled(False)
```

### UI Layout Architecture

#### **1. Grid-Based Layout System**
```python
batchlayout = QGridLayout()
batchlayout.addWidget(self.batchcheckbox, 0, 0, Qt.AlignmentFlag.AlignRight)
batchlayout.addWidget(batchchecklabel, 0, 1)
batchlayout.addWidget(prefixlabel, 1, 0)
batchlayout.addWidget(self.prefixEdit, 1, 1)
batchlayout.addWidget(counterlabel, 2, 0)
batchlayout.addWidget(self.counterSpinBox, 2, 1)
batchlayout.addWidget(descrLabel, 3, 0, 1, 3)
batchlayout.addWidget(self.neverOverwriteCheckbox, 4, 0, Qt.AlignmentFlag.AlignRight)
batchlayout.addWidget(neverOverwriteCounterlabel, 4, 1)
```

#### **2. Layout Constraints**
```python
mainLayout.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
```

#### **3. Button Layout**
```python
buttonLayout = QHBoxLayout()
buttonLayout.addStretch()
buttonLayout.addWidget(self.dialogbuttons)
```

### Integration Points

#### **1. Main Application Window (`ApplicationWindow`)**
- **Configuration Access**: Reads/writes to `self.aw.qmc` (Artisan's main configuration)
- **Settings Management**: Integrates with Artisan's configuration system

#### **2. Quick Mill Control (`QMC`)**
```python
# Batch configuration properties
self.aw.qmc.batchprefix      # Custom prefix for batch names
self.aw.qmc.batchcounter     # Current batch number (-1 if disabled)
self.aw.qmc.batchsequence    # Sequence number for batch tracking
self.aw.qmc.neverUpdateBatchCounter  # Protection flag
```

#### **3. Settings Persistence**
```python
# Dialog position persistence
settings = QSettings()
if settings.contains('BatchPosition'):
    self.move(settings.value('BatchPosition'))

# Position saving on close
def close(self) -> bool:
    settings = QSettings()
    settings.setValue('BatchPosition', self.frameGeometry().topLeft())
    return super().close()
```

### Key Methods

#### **`__init__(self, parent, aw)`**
- **Purpose**: Initialize dialog with current batch configuration
- **Parameters**: 
  - `parent`: Parent widget for modal behavior
  - `aw`: ApplicationWindow instance for configuration access
- **Key Operations**: Load settings, create UI elements, connect signals, set initial state

#### **`toggleCounterFlag(self, _)`**
- **Purpose**: Enable/disable batch counter controls based on checkbox state
- **Trigger**: Checkbox state change
- **Operations**: Dynamically enable/disable prefix, counter, and protection controls

#### **`batchChanged(self)`**
- **Purpose**: Save configuration changes and close dialog
- **Operations**: Update QMC settings, handle counter state, close dialog
- **Integration**: Updates main application's batch configuration

#### **`close(self)`**
- **Purpose**: Save dialog position and close
- **Operations**: Persist position to settings, call parent close method
- **Return**: Boolean indicating close success

### State Management Logic

#### **1. Counter State Logic**
```python
# Counter enabled state
if self.aw.qmc.batchcounter > -1:
    # Counter is active
    self.counterSpinBox.setValue(int(round(self.aw.qmc.batchcounter)))
    self.counterSpinBox.setEnabled(True)
    self.prefixEdit.setEnabled(True)
    self.neverOverwriteCheckbox.setEnabled(True)
else:
    # Counter is disabled
    self.counterSpinBox.setValue(0)
    self.counterSpinBox.setEnabled(False)
    self.prefixEdit.setEnabled(False)
    self.neverOverwriteCheckbox.setEnabled(False)
```

#### **2. Configuration Persistence Logic**
```python
def batchChanged(self) -> None:
    # Always save prefix
    self.aw.qmc.batchprefix = self.prefixEdit.text()
    
    if self.batchcheckbox.isChecked():
        # Enable counter mode
        self.aw.qmc.batchcounter = self.counterSpinBox.value()
    else:
        # Disable counter mode
        self.aw.qmc.batchcounter = -1
        self.aw.qmc.batchsequence = 1
    
    # Save protection setting
    self.aw.qmc.neverUpdateBatchCounter = bool(self.neverOverwriteCheckbox.isChecked())
```

### User Experience Features

#### **1. Visual Feedback**
- **Tooltips**: Comprehensive help text for all controls
- **Descriptive Labels**: Clear indication of what each control does
- **Status Information**: Shows next batch number information

#### **2. Input Validation**
- **Counter Range**: Limits counter to 0-999,999
- **Step Increments**: Single-step counter increments
- **Alignment**: Right-aligned numeric input for better readability

#### **3. Accessibility**
- **Keyboard Navigation**: Tab order follows logical flow
- **Focus Management**: OK button receives initial focus
- **Modal Behavior**: Prevents accidental interaction with background

### Integration with Roasting Workflow

#### **1. Batch Naming Convention**
- **Prefix + Counter**: Generates names like "Batch001", "Roast2024-001"
- **Sequential Tracking**: Maintains order across multiple roasting sessions
- **File Naming**: Integrates with Artisan's file saving system

#### **2. Settings Protection**
- **Counter Preservation**: Prevents accidental reset when loading settings
- **Workflow Continuity**: Maintains batch sequence across sessions
- **Data Integrity**: Protects against configuration corruption

#### **3. Session Management**
- **Automatic Incrementing**: Counter increases with each new batch
- **Reset Capability**: Can reset counter when needed
- **Flexible Naming**: Custom prefixes for different roast types or origins

### Technical Implementation Details

#### **1. Signal-Slot Architecture**
```python
# Connect UI elements to handlers
self.dialogbuttons.accepted.connect(self.batchChanged)
self.dialogbuttons.rejected.connect(self.close)
self.batchcheckbox.stateChanged.connect(self.toggleCounterFlag)
```

#### **2. State Synchronization**
```python
# Real-time UI state updates
def toggleCounterFlag(self, _: int) -> None:
    enabled = self.batchcheckbox.isChecked()
    self.prefixEdit.setEnabled(enabled)
    self.counterSpinBox.setEnabled(enabled)
    self.neverOverwriteCheckbox.setEnabled(enabled)
```

#### **3. Settings Integration**
```python
# QSettings for persistent storage
settings = QSettings()
if settings.contains('BatchPosition'):
    self.move(settings.value('BatchPosition'))

# Position saving
settings.setValue('BatchPosition', self.frameGeometry().topLeft())
```

### Error Handling and Validation

#### **1. Input Validation**
- **Range Checking**: Counter limited to reasonable range (0-999,999)
- **Type Safety**: Strong typing with TYPE_CHECKING support
- **State Validation**: Ensures UI state consistency

#### **2. Exception Safety**
- **Graceful Degradation**: Handles missing settings gracefully
- **Default Values**: Provides sensible defaults for missing configuration
- **State Recovery**: Maintains consistent state across configuration changes

### Performance Considerations

#### **1. Minimal Resource Usage**
- **Fixed Size**: Prevents unnecessary layout recalculations
- **Efficient Updates**: Only updates changed configuration values
- **Lazy Loading**: Loads settings only when needed

#### **2. Responsive UI**
- **Immediate Feedback**: UI updates happen in real-time
- **Non-blocking Operations**: All operations are synchronous and fast
- **Optimized Layout**: Grid layout provides efficient widget positioning

### Future Enhancement Considerations

#### **1. Extensibility Points**
- **Custom Naming Patterns**: Support for more complex naming schemes
- **Batch Categories**: Different counter sets for different roast types
- **Import/Export**: Batch configuration sharing between installations

#### **2. Advanced Features**
- **Auto-increment Rules**: Automatic counter advancement based on conditions
- **Batch History**: Track and display previous batch information
- **Template System**: Predefined batch naming templates

#### **3. Integration Opportunities**
- **Database Integration**: Store batch information in external databases
- **Cloud Sync**: Synchronize batch counters across multiple devices
- **Reporting System**: Generate batch reports and analytics

### Usage Patterns

#### **1. Typical Workflow**
1. User opens batch dialog
2. Enables batch counter if needed
3. Sets custom prefix (e.g., "Roast2024-")
4. Sets starting counter number
5. Optionally enables counter protection
6. Saves configuration and closes dialog

#### **2. Configuration Scenarios**
- **New Installation**: Start with counter 1 and custom prefix
- **Existing Setup**: Load current counter and continue sequence
- **Reset Scenario**: Reset counter to 1 for new year/season
- **Protection Mode**: Enable protection to prevent accidental resets

#### **3. Integration with Main Application**
- **File Naming**: Batch numbers automatically included in saved files
- **Session Tracking**: Each roasting session gets unique batch identifier
- **Record Keeping**: Maintains organized history of roasting sessions

This module represents a focused, efficient batch management system that provides essential functionality for organizing roasting sessions while maintaining simplicity and reliability. It serves as a foundation for more advanced batch tracking and reporting features that could be added in future versions.