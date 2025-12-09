# Artisan Profile Transposer Module Documentation

## File: `src/artisanlib/transposer.py`

### Overview
This module implements the **comprehensive Profile Transposer Dialog** for the Artisan coffee roasting application. At 1,252 lines, it provides sophisticated mathematical tools for transforming roasting profiles through time and temperature mapping, enabling roasters to adapt existing profiles to new target specifications.

### Purpose and Architecture
The `transposer.py` module serves as the **mathematical transformation engine** for Artisan, implementing:
- **Profile Transformation**: Mathematical mapping between source and target roasting profiles
- **Multiple Mapping Modes**: Discrete, linear, and quadratic transformation algorithms
- **Phase-Based Analysis**: Roasting phase timing and percentage calculations
- **Temperature Scaling**: Bean temperature curve transformation
- **Real-time Preview**: Live calculation and display of transformation results

### Key Components

#### **Main Dialog: `profileTransformatorDlg`**
```python
class profileTransformatorDlg(ArtisanDialog):
    def __init__(self, parent: 'QWidget', aw: 'ApplicationWindow'):
        # Comprehensive profile transformation interface
        # Mathematical mapping between source and target profiles
```

**Core Features:**
- **Modal Operation**: Blocks interaction during profile transformation
- **State Preservation**: Maintains original profile data for restoration
- **Real-time Calculation**: Live preview of transformation results
- **Multiple Tables**: Phases, time, and temperature transformation views

#### **Custom Validator: `MyQRegularExpressionValidator`**
```python
class MyQRegularExpressionValidator(QRegularExpressionValidator):
    @staticmethod
    def fixup(value: Optional[str]) -> str:
        # Fixes partial time input like '12' => '12:00', '12:' => '12:00'
```

**Validation Features:**
- **Time Format Fixing**: Automatically completes partial time entries
- **Input Validation**: Ensures proper time format (MM:SS)
- **User Experience**: Reduces input errors and improves usability

### Technical Implementation

#### **Data Structure Management**
```python
# Original data preservation
self.org_transMappingMode = self.aw.qmc.transMappingMode
self.org_timex = self.aw.qmc.timex[:]
self.org_temp2 = self.aw.qmc.temp2[:]
self.org_extratimex = copy.deepcopy(self.aw.qmc.extratimex)
self.org_curFile = self.aw.curFile
self.org_UUID = self.aw.qmc.roastUUID
```

**Data Preservation:**
- **Deep Copying**: Prevents modification of original data
- **State Restoration**: Enables complete rollback of changes
- **Metadata Protection**: Preserves roast identification and timestamps
- **File Management**: Maintains original file associations

#### **Mapping Mode System**
```python
self.mappingModeComboBox.addItems([
    QApplication.translate('ComboBox', 'discrete'),
    QApplication.translate('ComboBox', 'linear'),
    QApplication.translate('ComboBox', 'quadratic')
])
```

**Mapping Algorithms:**
- **Discrete (0)**: Segment-wise linear mapping between specific points
- **Linear (1)**: Global linear transformation across entire profile
- **Quadratic (2)**: Global quadratic transformation for curved profiles

### Mathematical Transformation Engine

#### **Time Transformation System**
```python
def calcTimeResults(self) -> List[float]:
    if self.aw.qmc.transMappingMode == 0:
        # Discrete mapping
        fits = self.calcDiscretefits([0] + self.profileTimes, [0] + self.targetTimes)
        for i in range(4):
            fit = fits[i+1]
            profileTime = self.profileTimes[i]
            if fit is not None and profileTime is not None:
                res.append(numpy.poly1d(fit)(profileTime))
    else:
        # Linear/Quadratic mapping
        fit_func = self.calcTimePolyfit()
        for i in range(4):
            profileTime = self.profileTimes[i]
            if fit_func is not None and profileTime is not None:
                res.append(fit_func(profileTime))
```

**Transformation Features:**
- **Polynomial Fitting**: Uses numpy.polyfit for mathematical mapping
- **Segment Analysis**: Breaks profile into logical roasting phases
- **Offset Handling**: Manages time offsets and reference points
- **Error Handling**: Graceful degradation on mathematical failures

#### **Temperature Transformation System**
```python
def calcTempResults(self) -> Tuple[List[Optional[float]], Optional[str]]:
    if self.aw.qmc.transMappingMode == 0:
        # Discrete mapping
        fits = self.calcDiscretefits(self.profileTemps, self.targetTemps)
        for i in range(5):
            fit = fits[i]
            profileTemp = self.profileTemps[i]
            if profileTemp is not None and fit is not None:
                res.append(numpy.poly1d(fit)(profileTemp))
    else:
        # Linear/Quadratic mapping
        fit_func = self.calcTempPolyfit()
        if fit_func is not None:
            p = numpy.poly1d(fit_func)
            for i in range(5):
                profileTemp = self.profileTemps[i]
                if profileTemp is not None:
                    res.append(p(profileTemp))
```

**Temperature Features:**
- **Multi-point Mapping**: Maps temperatures at key roasting events
- **Formula Generation**: Creates mathematical formulas for transformations
- **Phase-aware Processing**: Different transformations for different roasting phases
- **Validation**: Ensures temperature transformations are physically reasonable

#### **Discrete Fitting Algorithm**
```python
@staticmethod
def calcDiscretefits(sources: List[Optional[float]], targets: List[Optional[float]]) -> List[Optional['npt.NDArray[numpy.float64]']]:
    fits = [None] * len(sources)
    last_fit = None
    
    for i, _ in enumerate(sources):
        if sources[i] is not None:
            if targets[i] is None:
                fits[i] = last_fit  # Use previous fit
            else:
                # Calculate new fit between current and next valid points
                next_idx = None
                for j in range(i+1, len(sources)):
                    if sources[j] is not None and targets[j] is not None:
                        next_idx = j
                        break
                
                if next_idx is None:
                    if last_fit is not None:
                        fits[i] = last_fit
                    else:
                        # Simple offset transformation
                        fits[i] = numpy.array([1, targets[i] - sources[i]])
                else:
                    # Linear fit between two points
                    fits[i] = numpy.polyfit([sources[i], sources[next_idx]], 
                                          [targets[i], targets[next_idx]], 1)
                
                last_fit = fits[i]
    
    return fits
```

**Algorithm Features:**
- **Segment-wise Processing**: Handles missing data points gracefully
- **Fit Propagation**: Extends fits to adjacent segments
- **Fallback Strategies**: Provides default transformations when needed
- **Mathematical Robustness**: Handles edge cases and numerical issues

### User Interface Components

#### **Phases Table**
```python
def createPhasesTable(self) -> None:
    self.phasestable.setHorizontalHeaderLabels([
        QApplication.translate('Label', 'Drying'),
        QApplication.translate('Label', 'Maillard'),
        QApplication.translate('Label', 'Finishing')
    ])
    self.phasestable.setVerticalHeaderLabels([
        QApplication.translate('Table', 'Profile'),
        QApplication.translate('Table', 'Target'),
        QApplication.translate('Table', 'Result')
    ])
```

**Phases Features:**
- **Three Roasting Phases**: Drying, Maillard, Finishing
- **Time and Percentage**: Dual input methods for phase targets
- **Real-time Calculation**: Live phase timing and percentage updates
- **Background Integration**: Uses background profiles for target suggestions

#### **Time Table**
```python
def createTimeTable(self) -> None:
    self.timetable.setHorizontalHeaderLabels([
        QApplication.translate('Label', 'DRY END'),
        QApplication.translate('Label', 'FC START'),
        QApplication.translate('Label', 'SC START'),
        QApplication.translate('Label', 'DROP')
    ])
```

**Time Features:**
- **Key Roasting Events**: DRY, FCs, SCs, DROP timing
- **Target Specification**: User-defined target times
- **Result Preview**: Calculated transformation results
- **Background Profile**: Suggests targets from background profiles

#### **Temperature Table**
```python
def createTempTable(self) -> None:
    self.temptable.setHorizontalHeaderLabels([
        QApplication.translate('Label', 'CHARGE'),
        QApplication.translate('Label', 'DRY END'),
        QApplication.translate('Label', 'FC START'),
        QApplication.translate('Label', 'SC START'),
        QApplication.translate('Label', 'DROP')
    ])
```

**Temperature Features:**
- **Bean Temperature Points**: Key temperature measurements
- **Target Temperatures**: User-specified target values
- **Transformation Results**: Calculated temperature curves
- **Formula Display**: Mathematical transformation formulas

### Interactive Features

#### **Header Click Actions**
```python
@pyqtSlot(int)
def phasesTableColumnHeaderClicked(self, i: int) -> None:
    if (self.phases_target_widgets_time[i] is not None and
            self.phases_target_widgets_percent[i] is not None):
        # Clear target values or suggest from background profile
        if self.aw.qmc.backgroundprofile is not None:
            # Suggest values from background profile
            if i == 0:  # DRYING
                s = stringfromseconds(back_dry - back_offset)
            elif i == 1:  # MAILLARD
                s = stringfromseconds(back_fcs - back_dry)
            elif i == 2:  # FINISHING
                s = stringfromseconds(back_drop - back_fcs)
```

**Interactive Features:**
- **Smart Clearing**: Click headers to clear or suggest values
- **Background Integration**: Suggests targets from background profiles
- **Context Awareness**: Different actions for different table sections
- **User Efficiency**: Reduces manual input requirements

#### **Real-time Updates**
```python
@pyqtSlot()
def updatePhasesWidget(self) -> None:
    # Clear corresponding time target if percentage target is set
    if sender.text() != '':
        try:
            time_idx = self.phases_target_widgets_time.index(sender)
            phases_target_widgets_percent = self.phases_target_widgets_percent[time_idx]
            if phases_target_widgets_percent is not None:
                phases_target_widgets_percent.setText('')
        except Exception:
            pass
    self.updateTimeResults()
```

**Update Features:**
- **Automatic Synchronization**: Updates related fields automatically
- **Conflict Prevention**: Prevents conflicting input methods
- **Live Calculation**: Real-time result updates
- **User Feedback**: Immediate visual feedback on changes

### Application and Restoration

#### **Transformation Application**
```python
@pyqtSlot(bool)
def apply(self, _: bool = False) -> None:
    applied_time = self.applyTimeTransformation()
    applied_temp = self.applyTempTransformation()
    if applied_time or applied_temp:
        # Update roast metadata
        self.aw.qmc.roastUUID = None
        self.aw.qmc.roastdate = QDateTime.currentDateTime()
        self.aw.qmc.roastepoch = self.aw.qmc.roastdate.toSecsSinceEpoch()
        # Mark file as modified
        self.aw.qmc.fileDirty()
        # Update display
        self.aw.qmc.timealign()
        self.aw.autoAdjustAxis()
        self.aw.qmc.redraw()
```

**Application Features:**
- **Metadata Update**: Generates new roast identification
- **File Management**: Marks file as modified
- **Display Update**: Refreshes charts and axes
- **State Management**: Updates application state

#### **State Restoration**
```python
@pyqtSlot(bool)
def restore(self, _: bool = False) -> None:
    # Restore original file and metadata
    self.aw.setCurrentFile(self.org_curFile, addToRecent=False)
    self.aw.qmc.roastUUID = self.org_UUID
    self.aw.qmc.roastdate = self.org_roastdate
    # Restore original data
    self.aw.qmc.timex = self.org_timex[:]
    self.aw.qmc.temp2 = self.org_temp2[:]
    # Update display
    self.aw.autoAdjustAxis()
    self.aw.qmc.redraw()
```

**Restoration Features:**
- **Complete Rollback**: Restores all original data and metadata
- **File Association**: Restores original file connections
- **Display Reset**: Returns to original visual state
- **State Consistency**: Ensures application state consistency

### Mathematical Foundation

#### **Polynomial Fitting**
```python
def calcTimePolyfit(self) -> Optional[Callable[[float], float]]:
    xa = [0]  # Initialize with CHARGE time 00:00
    ya = [0]
    for i in range(4):
        profileTime = self.profileTimes[i]
        targetTime = self.targetTimes[i]
        if profileTime is not None and targetTime is not None:
            xa.append(profileTime)
            ya.append(targetTime)
    
    deg = min(len(xa) - 1, self.aw.qmc.transMappingMode)
    if len(xa) > 1:
        try:
            z = numpy.polyfit(xa, ya, deg)
            return numpy.poly1d(z)
        except Exception:
            return None
    return None
```

**Fitting Features:**
- **Degree Selection**: Automatically selects appropriate polynomial degree
- **Data Validation**: Ensures sufficient data points for fitting
- **Error Handling**: Graceful handling of mathematical failures
- **Function Generation**: Creates callable transformation functions

#### **Discrete Mapping Application**
```python
def applyDiscreteTimeMapping(self, timex: List[float], fits: List[Optional['npt.NDArray[numpy.float64]']]) -> List[float]:
    offset = self.forgroundOffset()
    res_timex = []
    
    # Calculate new offset
    if offset == 0 or fits[0] is None:
        new_offset = 0
    else:
        new_offset = numpy.poly1d(fits[0])(offset)
    
    for i, _ in enumerate(timex):
        # Determine which fit to apply based on position in profile
        j = 0
        if self.aw.qmc.timeindex[6] > 0 and i >= self.aw.qmc.timeindex[6]:
            j = 4  # After DROP
        elif self.aw.qmc.timeindex[4] > 0 and i >= self.aw.qmc.timeindex[4]:
            j = 3  # After SCs
        elif self.aw.qmc.timeindex[2] > 0 and i >= self.aw.qmc.timeindex[2]:
            j = 2  # After FCs
        elif self.aw.qmc.timeindex[1] > 0 and i >= self.aw.qmc.timeindex[1]:
            j = 1  # After DRY
        
        fitsj = fits[j]
        if fitsj is None:
            res_timex.append(timex[i] - offset + new_offset)
        else:
            fit = numpy.poly1d(fitsj)
            res_timex.append(fit(timex[i] - offset) + new_offset)
    
    return res_timex
```

**Mapping Features:**
- **Phase-aware Processing**: Applies different transformations to different roasting phases
- **Offset Management**: Handles time offsets and reference points
- **Fallback Strategies**: Provides default transformations when fits are unavailable
- **Consistent Results**: Ensures mathematical consistency across transformations

### Integration Points

#### **Main Application Integration**
```python
def __init__(self, parent: 'QWidget', aw: 'ApplicationWindow'):
    # Direct access to main application window
    # Integration with Quality Management Center (QMC)
    # Access to roast data and configuration
```

**Integration Features:**
- **Data Access**: Direct access to roast profiles and events
- **Configuration Management**: Integration with application settings
- **Display Updates**: Automatic chart and axis updates
- **File Management**: Integration with file system operations

#### **Background Profile Integration**
```python
if self.aw.qmc.backgroundprofile is not None:
    back_offset = self.backgroundOffset()
    back_dry = self.aw.qmc.timeB[self.aw.qmc.timeindexB[1]]
    back_fcs = self.aw.qmc.timeB[self.aw.qmc.timeindexB[2]]
    back_drop = self.aw.qmc.timeB[self.aw.qmc.timeindexB[6]]
```

**Background Features:**
- **Target Suggestions**: Suggests targets from background profiles
- **Reference Data**: Provides reference for transformation targets
- **Quality Assurance**: Helps ensure reasonable transformation targets
- **User Guidance**: Guides users toward realistic transformations

This module represents a sophisticated mathematical tool that enables professional roasters to adapt existing roasting profiles to new specifications through advanced mathematical transformations, providing both precision and flexibility in profile adaptation.