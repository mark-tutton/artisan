# Artisan Background Profile Dialog Module Documentation

## File: `src/artisanlib/background.py`

### Overview
This module implements the **Background Profile Configuration Dialog** for the Artisan coffee roasting application. It provides a comprehensive interface for managing background profiles, which are reference roasting curves that can be overlaid on the current roast for comparison, guidance, and playback assistance.

### Purpose and Architecture
The `background.py` module serves as the **background profile management system**, enabling users to:
- **Load and display reference profiles** alongside current roasting data
- **Configure visual representation** of background curves and events
- **Set up playback assistance** for guided roasting
- **Manage profile alignment** and positioning
- **Export background data** in tabular formats

### Core Components

#### **Main Dialog Class: `backgroundDlg`**
- **Inheritance**: Extends `ArtisanResizeablDialog` (resizable dialog base class)
- **Modal Behavior**: Blocks interaction with parent window during configuration
- **Tabbed Interface**: Four specialized tabs for different aspects of background management
- **Geometry Persistence**: Remembers dialog size/position across sessions

#### **Tab Structure**
1. **Config Tab**: Core background settings and controls
2. **Events Tab**: Background profile event table
3. **Data Tab**: Background profile data table
4. **Playback Tab**: Playback assistance configuration

### Configuration Features

#### **1. Background Profile Management**
```python
# Core background functionality
self.backgroundCheck.setChecked(self.aw.qmc.background)
self.pathedit.setText(self.aw.qmc.backgroundpath)
self.filename = ''
```

#### **2. Visual Display Options**
```python
# Multiple display toggles
self.backgroundDetails.setChecked(self.aw.qmc.backgroundDetails)
self.backgroundeventsflag.setChecked(self.aw.qmc.backgroundeventsflag)
self.backgroundETflag.setChecked(self.aw.qmc.backgroundETcurve)
self.backgroundBTflag.setChecked(self.aw.qmc.backgroundBTcurve)
self.backgroundDeltaETflag.setChecked(self.aw.qmc.DeltaETBflag)
self.backgroundDeltaBTflag.setChecked(self.aw.qmc.DeltaBTBflag)
self.backgroundFullflag.setChecked(self.aw.qmc.backgroundShowFullflag)
```

#### **3. Profile Alignment System**
```python
# Alignment event selection
self.aw.qmc.alignnames = [
    'CHARGE', 'DRY', 'FCs', 'FCe', 'SCs', 'SCe', 'DROP', 'ALL'
]
self.alignComboBox.addItems(self.aw.qmc.alignnames)
self.alignComboBox.setCurrentIndex(self.aw.qmc.alignEvent)
```

#### **4. Movement Controls**
```python
# Background profile positioning
self.speedSpinBox.setRange(1, 90)
self.speedSpinBox.setValue(int(self.aw.qmc.backgroundmovespeed))
self.upButton.clicked.connect(self.moveUp)
self.downButton.clicked.connect(self.moveDown)
self.leftButton.clicked.connect(self.moveLeft)
self.rightButton.clicked.connect(self.moveRight)
```

### Playback Assistance System

#### **1. Event Playback Configuration**
```python
# Main playback controls
self.backgroundReproduce = QCheckBox('Playback Aid')
self.backgroundPlaybackEvents = QCheckBox('Playback Events')
self.backgroundPlaybackDROP = QCheckBox('Playback DROP')

# Event type selection
self.backgroundPlaybackEvent0 = QCheckBox(self.aw.qmc.etypesf(0))
self.backgroundPlaybackEvent1 = QCheckBox(self.aw.qmc.etypesf(1))
self.backgroundPlaybackEvent2 = QCheckBox(self.aw.qmc.etypesf(2))
self.backgroundPlaybackEvent3 = QCheckBox(self.aw.qmc.etypesf(3))
```

#### **2. Ramp Rate Playback**
```python
# Ramp rate indicators
self.backgroundPlaybackRampEvent0 = QCheckBox(self.aw.qmc.etypesf(0))
self.backgroundPlaybackRampEvent1 = QCheckBox(self.aw.qmc.etypesf(1))
self.backgroundPlaybackRampEvent2 = QCheckBox(self.aw.qmc.etypesf(2))
self.backgroundPlaybackRampEvent3 = QCheckBox(self.aw.qmc.etypesf(3))
```

#### **3. Timing and Warning System**
```python
# Warning time configuration
self.etimeSpinBox.setRange(1, 60)
self.etimeSpinBox.setValue(int(self.aw.qmc.detectBackgroundEventTime))
self.backgroundReproduceBeep = QCheckBox('Beep')
```

### Data Management and Display

#### **1. Event Table Generation**
```python
def createEventTable(self) -> None:
    ndata = len(self.aw.qmc.backgroundEvents)
    self.eventtable.setRowCount(ndata)
    self.eventtable.setColumnCount(6)
    self.eventtable.setHorizontalHeaderLabels([
        'Time', self.ETname, self.BTname, 'Description', 'Type', 'Value'
    ])
```

#### **2. Data Table Generation**
```python
def createDataTable(self) -> None:
    ndata = min(len(self.aw.qmc.timeB), len(self.aw.qmc.temp1B), len(self.aw.qmc.temp2B))
    headers = ['Time', self.ETname, self.BTname, 
               deltaLabelUTF8 + self.ETname, deltaLabelUTF8 + self.BTname]
```

#### **3. Extra Curve Support**
```python
# XT and YT curve selection
curvenames = ['']  # First entry is empty (no extra curve)
for i in range(min(len(self.aw.qmc.extraname1B), len(self.aw.qmc.extraname2B), len(self.aw.qmc.extratimexB))):
    cn1 = self.aw.qmc.extraname1B[i]
    cn2 = self.aw.qmc.extraname2B[i]
    curvenames.append(f'B{2*i+3}: {cn1}')
    curvenames.append(f'B{2*i+4}: {cn2}')
```

### Integration Points

#### **1. Main Application Window (`ApplicationWindow`)**
- **Configuration Access**: Reads/writes to `self.aw.qmc` (Artisan's main configuration)
- **File Operations**: Uses `self.aw.ArtisanOpenFileDialog()` for file selection
- **Background Management**: Calls `self.aw.loadbackground()` and `self.aw.deleteBackground()`
- **Redraw Operations**: Triggers `self.aw.qmc.redraw()` for UI updates

#### **2. Quick Mill Control (`QMC`)**
```python
# Background profile data
self.aw.qmc.backgroundprofile
self.aw.qmc.backgroundEvents
self.aw.qmc.timeB, self.aw.qmc.temp1B, self.aw.qmc.temp2B
self.aw.qmc.extraname1B, self.aw.qmc.extraname2B, self.aw.qmc.extratimexB
```

#### **3. Profile Data Semaphore**
```python
# Thread-safe data access
try:
    self.aw.qmc.profileDataSemaphore.acquire(1)
    # ... data table operations
finally:
    if self.aw.qmc.profileDataSemaphore.available() < 1:
        self.aw.qmc.profileDataSemaphore.release(1)
```

### UI Layout Architecture

#### **1. Tabbed Interface Design**
```python
self.TabWidget = QTabWidget()
C1Widget = QWidget()
C1Widget.setLayout(tab1layout)
self.TabWidget.addTab(C1Widget, 'Config')
C2Widget = QWidget()
C2Widget.setLayout(tab2layout)
self.TabWidget.addTab(C2Widget, 'Events')
C3Widget = QWidget()
C3Widget.setLayout(tab3layout)
self.TabWidget.addTab(C3Widget, 'Data')
```

#### **2. Grid-Based Movement Controls**
```python
movelayout = QGridLayout()
movelayout.addWidget(self.upButton, 0, 1)
movelayout.addWidget(self.leftButton, 1, 0)
movelayout.addWidget(self.speedSpinBox, 1, 1)
movelayout.addWidget(self.rightButton, 1, 2)
movelayout.addWidget(self.downButton, 2, 1)
```

#### **3. Horizontal Checkbox Layouts**
```python
checkslayout1 = QHBoxLayout()
checkslayout1.addStretch()
checkslayout1.addWidget(self.backgroundCheck)
checkslayout1.addSpacing(5)
checkslayout1.addWidget(self.backgroundDetails)
# ... additional checkboxes with spacing
checkslayout1.addStretch()
```

### Key Methods

#### **`__init__(self, parent, aw, activeTab)`**
- **Purpose**: Initialize dialog with current configuration and active tab
- **Parameters**: 
  - `parent`: Parent widget for modal behavior
  - `aw`: ApplicationWindow instance for configuration access
  - `activeTab`: Initial tab to display
- **Key Operations**: Load settings, create UI elements, connect signals, set active tab

#### **`load(self, _)`**
- **Purpose**: Load background profile from file
- **Operations**: File selection, profile loading, curve population, UI updates
- **Integration**: Calls main application's background loading system

#### **`delete(self, _)`**
- **Purpose**: Remove current background profile
- **Operations**: Clear UI, reset configuration, trigger redraw
- **Cleanup**: Resets line count caches and updates display

#### **`move_background(self, m)`**
- **Purpose**: Reposition background profile
- **Parameters**: `m` - movement direction ('up', 'down', 'left', 'right')
- **Operations**: Calculate movement step, update position, redraw

#### **`readChecks(self)`**
- **Purpose**: Update configuration based on checkbox states
- **Operations**: Sync UI state with QMC configuration, trigger redraw
- **Integration**: Updates main application's background display settings

### Data Flow and State Management

#### **1. Configuration Loading**
```python
# Load current settings from QMC
self.backgroundCheck.setChecked(self.aw.qmc.background)
self.backgroundDetails.setChecked(self.aw.qmc.backgroundDetails)
self.backgroundeventsflag.setChecked(self.aw.qmc.backgroundeventsflag)
```

#### **2. Configuration Saving**
```python
def accept(self) -> None:
    self.aw.qmc.backgroundmovespeed = self.speedSpinBox.value()
    self.aw.qmc.backgroundKeyboardControlFlag = bool(self.keyboardControlflag.isChecked())
    if self.aw.qmc.backgroundPlaybackEvents:
        self.aw.qmc.turn_playback_event_ON()
```

#### **3. Real-time Updates**
```python
# Checkbox state changes trigger immediate configuration updates
self.backgroundCheck.clicked.connect(self.readChecks)
self.backgroundDetails.clicked.connect(self.readChecks)
self.backgroundeventsflag.clicked.connect(self.readChecks)
```

### Performance Considerations

#### **1. Lazy Table Creation**
```python
@pyqtSlot(int)
def tabSwitched(self, i: int) -> None:
    if i == 1:
        self.createEventTable()
    elif i == 2:
        self.createDataTable()
```

#### **2. Signal Blocking for Batch Updates**
```python
self.xtcurveComboBox.blockSignals(True)
self.xtcurveComboBox.clear()
self.xtcurveComboBox.addItems(curvenames)
self.xtcurveComboBox.blockSignals(False)
```

#### **3. Semaphore-Protected Data Access**
```python
# Prevents data corruption during table generation
try:
    self.aw.qmc.profileDataSemaphore.acquire(1)
    # ... data operations
finally:
    if self.aw.qmc.profileDataSemaphore.available() < 1:
        self.aw.qmc.profileDataSemaphore.release(1)
```

### Error Handling and Validation

#### **1. Exception Handling in Curve Naming**
```python
try:
    cn1 = cn1.format(
        self.aw.qmc.Betypesf(0), self.aw.qmc.Betypesf(1),
        self.aw.qmc.Betypesf(2), self.aw.qmc.Betypesf(3), self.aw.qmc.mode)
except Exception as e:
    # Substitution might fail if a variable {7} is used
    _log.error(e)
```

#### **2. Safe Table Operations**
```python
# Avoid crashes on Ubuntu 16.04
# self.eventtable.clear()  # This crashes Ubuntu 16.04
# self.eventtable.clearContents()  # This crashes Ubuntu 16.04
self.eventtable.clearSelection()  # This seems to work
```

#### **3. Platform-Specific Behavior**
```python
if platform.system() != 'Windows':
    ok_button: Optional[QPushButton] = self.dialogbuttons.button(QDialogButtonBox.StandardButton.Ok)
    if ok_button is not None:
        ok_button.setFocus()
else:
    self.TabWidget.setFocus()
```

### Advanced Features

#### **1. Keyboard Control System**
```python
self.keyboardControlflag = QCheckBox('Keyboard Control')
self.keyboardControlflag.setToolTip('Move the background profile using the cursor keys')
```

#### **2. Event Type Abbreviation System**
```python
# Event type display with abbreviations
text = QApplication.translate('Table', '#{0} {1}{2}').format(
    str(index+1),
    self.aw.qmc.etypeAbbrev(self.aw.qmc.Betypesf(self.aw.qmc.backgroundEtypes[index])),
    self.aw.qmc.eventsvalues(self.aw.qmc.backgroundEvalues[index]))
```

#### **3. Color-Coded Event Display**
```python
# Color coding for different event types
if i == self.aw.qmc.timeindexB[0] != -1:
    item0.setBackground(QColor('#f07800'))  # CHARGE
elif i == self.aw.qmc.timeindexB[1]:
    item0.setBackground(QColor('orange'))   # DRY END
elif i in self.aw.qmc.backgroundEvents:
    item0.setBackground(QColor('yellow'))   # Custom events
```

### Integration with Roasting Workflow

#### **1. Profile Comparison**
- **Visual Overlay**: Background profiles displayed alongside current roast
- **Event Alignment**: Key roasting phases aligned for comparison
- **Delta Calculations**: Temperature difference curves for analysis

#### **2. Guided Roasting**
- **Playback Assistance**: Audio and visual cues for timing
- **Event Warnings**: Notifications when approaching key phases
- **Ramp Rate Monitoring**: Real-time comparison with reference curves

#### **3. Batch Size Management**
```python
self.setBatchSizeFromBackground = QCheckBox('Set batch size')
self.setBatchSizeFromBackground.setToolTip('Set batch size from background profile on load')
```

### Future Enhancement Considerations

#### **1. Extensibility Points**
- **Additional Curve Types**: Easy to add more background curve types
- **Custom Event Types**: Expandable event system
- **Advanced Alignment**: More sophisticated profile matching algorithms

#### **2. Performance Optimizations**
- **Data Caching**: Intelligent caching of frequently accessed data
- **Lazy Loading**: Load background data only when needed
- **Incremental Updates**: Update only changed portions of displays

#### **3. Integration Opportunities**
- **Cloud Profiles**: Remote background profile storage
- **Profile Sharing**: Community profile exchange system
- **Machine Learning**: AI-assisted profile matching and recommendations

This module represents a sophisticated background profile management system that provides comprehensive tools for comparing current roasts with reference profiles, enabling users to improve their roasting consistency and learn from successful profiles.