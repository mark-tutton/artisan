# Artisan Wheels Dialog Module Documentation

## File: `src/artisanlib/wheels.py`

### Overview
This module implements the **comprehensive Wheel Graph Editor Dialog** for the Artisan coffee roasting application. At 671 lines, it provides sophisticated tools for creating, editing, and managing hierarchical wheel graphs that visualize complex data relationships, roasting profiles, and coffee characteristics through an intuitive circular visualization system.

### Purpose and Architecture
The `wheels.py` module serves as the **wheel graph creation and management interface** for Artisan, implementing:
- **Wheel Graph Editor**: Visual editor for circular data visualization
- **Hierarchical Relationships**: Parent-child connections between wheel segments
- **Dynamic Configuration**: Real-time editing of wheel properties and appearance
- **Data Visualization**: Circular charts for roasting data and coffee characteristics
- **Export/Import**: Save and load wheel graph configurations
- **Interactive Design**: Drag-and-drop style editing with immediate visual feedback

### Key Components

#### **Main Dialog: `WheelDlg`**
```python
class WheelDlg(ArtisanDialog):
    def __init__(self, parent: 'QWidget', aw: 'ApplicationWindow'):
        # Comprehensive wheel graph editor
        # Real-time visualization and editing
        # Hierarchical data relationship management
```

**Core Features:**
- **Modal Operation**: Blocks interaction during wheel editing
- **Real-time Updates**: Immediate visual feedback on changes
- **Dual Table System**: Main wheel table and label properties table
- **Comprehensive Controls**: Full range of wheel customization options

### Technical Implementation

#### **Dual Table Architecture**

**Main Data Table (`datatable`)**
```python
def createdatatable(self) -> None:
    self.datatable.setColumnCount(10)
    self.datatable.setHorizontalHeaderLabels([
        'Delete Wheel', 'Edit Labels', 'Update Labels', 'Properties',
        'Radius', 'Starting angle', 'Projection', 'Text Size',
        'Color', 'Color Pattern'
    ])
```

**Main Table Features:**
- **Wheel Management**: Add, delete, and configure wheels
- **Property Editing**: Radius, angle, projection, and text size
- **Color Control**: Individual and pattern-based color management
- **Label Management**: Edit and update wheel segment labels

**Label Properties Table (`labeltable`)**
```python
def createlabeltablex(self, x: int) -> None:
    self.labeltable.setColumnCount(5)
    self.labeltable.setHorizontalHeaderLabels([
        'Label', 'Parent', 'Width', 'Color', 'Opaqueness'
    ])
```

**Label Table Features:**
- **Segment Properties**: Individual segment configuration
- **Parent Relationships**: Hierarchical connections between wheels
- **Width Control**: Segment size and proportion management
- **Visual Properties**: Color and transparency settings

#### **Wheel Configuration System**

**Radius Management**
```python
@pyqtSlot(float)
def setwidth(self, _: float) -> None:
    x = self.aw.findWidgetsRow(self.datatable, self.sender(), 4)
    if x is not None:
        widthSpinBox = cast(QDoubleSpinBox, self.datatable.cellWidget(x, 4))
        newwidth = widthSpinBox.value()
        oldwidth = self.aw.qmc.wradii[x]
        diff = newwidth - oldwidth
        
        # Adjust other wheels proportionally
        ll = len(self.aw.qmc.wradii)
        for i in range(ll):
            if i != x:
                if diff > 0:
                    self.aw.qmc.wradii[i] -= abs(float(diff))/(ll-1)
                else:
                    self.aw.qmc.wradii[i] += abs(float(diff))/(ll-1)
        
        self.aw.qmc.wradii[x] = newwidth
        
        # Correct for numerical floating point rounding errors
        count = 0.
        for wrad in self.aw.qmc.wradii:
            count += wrad
        diff = 100. - count
        if diff != 0.:
            if diff > 0.000:  # if count smaller
                self.aw.qmc.wradii[x] += abs(diff)
            else:
                self.aw.qmc.wradii[x] -= abs(diff)
        
        self.aw.qmc.drawWheel()
```

**Radius Features:**
- **Proportional Adjustment**: Other wheels adjust automatically
- **100% Coverage**: Ensures total radius equals 100%
- **Precision Correction**: Handles floating-point rounding errors
- **Real-time Updates**: Immediate visual feedback

**Angle and Rotation Control**
```python
@pyqtSlot(int)
def setangle(self, _: int) -> None:
    x = self.aw.findWidgetsRow(self.datatable, self.sender(), 5)
    if x is not None:
        angleSpinBox = cast(QSpinBox, self.datatable.cellWidget(x, 5))
        self.aw.qmc.startangle[x] = angleSpinBox.value()
        self.aw.qmc.drawWheel()

@pyqtSlot(bool)
def rotatewheels1(self, _: bool = False) -> None:
    for i, __ in enumerate(self.aw.qmc.startangle):
        self.aw.qmc.startangle[i] += 1
    self.aw.qmc.drawWheel()

@pyqtSlot(bool)
def rotatewheels0(self, _: bool = False) -> None:
    for i, __ in enumerate(self.aw.qmc.startangle):
        self.aw.qmc.startangle[i] -= 1
    self.aw.qmc.drawWheel()
```

**Rotation Features:**
- **Individual Control**: Set starting angle for each wheel
- **Global Rotation**: Rotate entire graph clockwise/counterclockwise
- **Degree Precision**: 1-degree rotation increments
- **Wrapping Support**: Handles angles beyond 360 degrees

#### **Projection System**
```python
projectionComboBox.addItems([
    QApplication.translate('ComboBox', 'Flat'),
    QApplication.translate('ComboBox', 'Perpendicular'),
    QApplication.translate('ComboBox', 'Radial')
])

@pyqtSlot(int)
def setprojection(self, _: int) -> None:
    x = self.aw.findWidgetsRow(self.datatable, self.sender(), 6)
    if x is not None:
        projectionComboBox = cast(QComboBox, self.datatable.cellWidget(x, 6))
        self.aw.qmc.projection[x] = projectionComboBox.currentIndex()
        self.aw.qmc.drawWheel()
```

**Projection Types:**
- **Flat**: Standard 2D circular projection
- **Perpendicular**: 3D perpendicular projection
- **Radial**: Radial projection for depth effect

### Hierarchical Relationship Management

#### **Parent-Child Connections**
```python
@pyqtSlot(int)
def setwheelchild(self, z: int) -> None:
    i = self.aw.findWidgetsRow(self.labeltable, self.sender(), 1)
    if i is not None:
        self.aw.qmc.setwheelchild(z, self.labelwheelx, i)
        self.aw.qmc.drawWheel()
        self.createdatatable()  # update data table

@pyqtSlot(bool)
def resetlabelparents(self, _: bool = False) -> None:
    x = self.labelwheelx
    nsegments = len(self.aw.qmc.wheellabelparent[x])
    for i in range(nsegments):
        self.aw.qmc.wheellabelparent[x][i] = 0
        self.aw.qmc.segmentlengths[x][i] = 100./nsegments
    self.aw.qmc.drawWheel()
    self.createlabeltablex(x)
```

**Relationship Features:**
- **Dynamic Connections**: Create parent-child relationships between segments
- **Automatic Updates**: Visual updates when relationships change
- **Reset Functionality**: Clear all relationships and restore defaults
- **Proportional Adjustment**: Segment widths adjust automatically

#### **Segment Width Management**
```python
@pyqtSlot(float)
def setlabelwidth(self, z: float) -> None:
    u = self.aw.findWidgetsRow(self.labeltable, self.sender(), 2)
    if u is not None:
        x = self.labelwheelx
        newwidth = z
        oldwidth = self.aw.qmc.segmentlengths[x][u]
        diff = newwidth - oldwidth
        ll = len(self.aw.qmc.segmentlengths[x])
        
        # Adjust other segments proportionally
        for i in range(ll):
            if i != u:
                if diff > 0:
                    self.aw.qmc.segmentlengths[x][i] -= abs(float(diff))/(ll-1)
                else:
                    self.aw.qmc.segmentlengths[x][i] += abs(float(diff))/(ll-1)
        
        self.aw.qmc.segmentlengths[x][u] = newwidth
        self.aw.qmc.drawWheel()
```

**Width Features:**
- **Proportional Adjustment**: Other segments adjust automatically
- **100% Coverage**: Ensures total segment width equals 100%
- **Real-time Updates**: Immediate visual feedback
- **Precision Management**: Handles floating-point calculations

### Color and Visual Management

#### **Color System**
```python
@pyqtSlot(bool)
def setwheelcolor(self, _: bool = False) -> None:
    x = self.aw.findWidgetsRow(self.datatable, self.sender(), 8)
    if x is not None:
        colorf = self.aw.colordialog(QColor(self.aw.qmc.wheelcolor[x][0]))
        if colorf.isValid():
            colorname = str(colorf.name())
            for i in range(len(self.aw.qmc.wheelcolor[x])):
                self.aw.qmc.wheelcolor[x][i] = colorname
        self.createdatatable()
        self.aw.qmc.drawWheel()

@pyqtSlot(bool)
def setsegmentcolor(self, _: bool = False) -> None:
    i = self.aw.findWidgetsRow(self.labeltable, self.sender(), 3)
    if i is not None:
        x = self.labelwheelx
        colorf = self.aw.colordialog(QColor(self.aw.qmc.wheelcolor[x][i]))
        if colorf.isValid():
            colorname = str(colorf.name())
            self.aw.qmc.wheelcolor[x][i] = colorname
            self.createdatatable()
            self.aw.qmc.drawWheel()
```

**Color Features:**
- **Wheel-level Colors**: Apply uniform color to entire wheel
- **Segment-level Colors**: Individual segment color control
- **Color Dialog Integration**: Native color picker interface
- **Real-time Updates**: Immediate visual feedback

#### **Color Pattern System**
```python
@pyqtSlot(int)
def setcolorpattern(self, _: int) -> None:
    self.aw.qmc.wheelcolorpattern = self.colorSpinBox.value()
    if self.aw.qmc.wheelcolorpattern:
        for x, __ in enumerate(self.aw.qmc.wheelcolor):
            wlen = len(self.aw.qmc.wheelcolor[x])
            for i in range(wlen):
                color = QColor()
                color.setHsv(int(round((360/wlen)*i*self.aw.qmc.wheelcolorpattern)), 255, 255, 255)
                self.aw.qmc.wheelcolor[x][i] = str(color.name())
        self.aw.qmc.drawWheel()
```

**Pattern Features:**
- **HSV-based Generation**: Creates harmonious color patterns
- **Automatic Distribution**: Evenly distributes colors across segments
- **Pattern Variation**: Different patterns for different wheels
- **Global Application**: Apply patterns to entire graph

#### **Transparency and Visual Effects**
```python
@pyqtSlot(int)
def setsegmentalpha(self, z: int) -> None:
    u = self.aw.findWidgetsRow(self.labeltable, self.sender(), 4)
    if u is not None:
        x = self.labelwheelx
        self.aw.qmc.segmentsalpha[x][u] = float(z/10.)
        self.aw.qmc.drawWheel()
```

**Visual Features:**
- **Alpha Control**: Segment transparency management
- **Range Control**: 0-10 scale converted to 0.0-1.0 alpha
- **Individual Control**: Per-segment transparency settings
- **Real-time Updates**: Immediate visual feedback

### Text and Typography Management

#### **Text Size Control**
```python
@pyqtSlot(bool)
def changetext1(self, _: bool = False) -> None:
    for i, __ in enumerate(self.aw.qmc.wheeltextsize):
        self.aw.qmc.wheeltextsize[i] += 1
    self.aw.qmc.drawWheel()

@pyqtSlot(bool)
def changetext0(self, _: bool = False) -> None:
    for i, __ in enumerate(self.aw.qmc.wheeltextsize):
        self.aw.qmc.wheeltextsize[i] -= 1
    self.aw.qmc.drawWheel()

@pyqtSlot(int)
def setTextsizeX(self, _: int) -> None:
    x = self.aw.findWidgetsRow(self.datatable, self.sender(), 7)
    if x is not None:
        txtSpinBox = cast(QSpinBox, self.datatable.cellWidget(x, 7))
        self.aw.qmc.wheeltextsize[x] = txtSpinBox.value()
        self.aw.qmc.drawWheel()
```

**Text Features:**
- **Global Control**: Increase/decrease all text sizes simultaneously
- **Individual Control**: Set text size for specific wheels
- **Range Validation**: 1-30 point size range
- **Real-time Updates**: Immediate visual feedback

#### **Text Color Management**
```python
@pyqtSlot(bool)
def settextcolor(self, _: bool = False) -> None:
    colorf = self.aw.colordialog(QColor(self.aw.qmc.wheeltextcolor))
    if colorf.isValid():
        colorname = str(colorf.name())
        self.aw.qmc.wheeltextcolor = colorname
        self.aw.qmc.drawWheel()
```

**Text Color Features:**
- **Global Text Color**: Single color for all text elements
- **Color Dialog Integration**: Native color picker interface
- **Real-time Updates**: Immediate visual feedback
- **Consistent Typography**: Unified text appearance

### Wheel Management Operations

#### **Adding New Wheels**
```python
@pyqtSlot(bool)
def insertwheel(self, _: bool = False) -> None:
    ndata = len(self.aw.qmc.wradii)
    if ndata:
        # Adjust existing wheel radii proportionally
        count = 0.
        for i in range(ndata):
            self.aw.qmc.wradii[i] = 100./(ndata+1)
            count += self.aw.qmc.wradii[i]
        self.aw.qmc.wradii.append(100.-count)
    else:
        self.aw.qmc.wradii.append(100.)
    
    # Determine number of segments based on outer wheel
    if len(self.aw.qmc.wheelnames):
        nwheels = len(self.aw.qmc.wheelnames[-1])
    else:
        nwheels = 3
    
    # Create default segments
    wn, sl, sa, wlp, co = [], [], [], [], []
    for i in range(nwheels+1):
        wn.append(f'W{len(self.aw.qmc.wheelnames)+1} {i+1}')
        sl.append(100./(nwheels+1))
        sa.append(.3)
        wlp.append(0)
        color = QColor()
        color.setHsv(int(round((360/(nwheels+1))*i)), 255, 255, 255
        co.append(str(color.name()))
    
    # Add wheel data
    self.aw.qmc.wheelnames.append(wn)
    self.aw.qmc.segmentlengths.append(sl)
    self.aw.qmc.segmentsalpha.append(sa)
    self.aw.qmc.wheellabelparent.append(wlp)
    self.aw.qmc.startangle.append(0)
    self.aw.qmc.projection.append(2)
    self.aw.qmc.wheeltextsize.append(10)
    self.aw.qmc.wheelcolor.append(co)
    
    self.createdatatable()
    self.aw.qmc.drawWheel()
```

**Add Wheel Features:**
- **Proportional Adjustment**: Existing wheels resize automatically
- **Smart Segmentation**: Number of segments based on outer wheel
- **Default Values**: Sensible defaults for new wheels
- **Color Generation**: Automatic color distribution
- **Real-time Updates**: Immediate visual feedback

#### **Deleting Wheels**
```python
@pyqtSlot(bool)
def popwheel(self, _: bool = False) -> None:
    x = self.aw.findWidgetsRow(self.datatable, self.sender(), 0)
    if x is not None:
        # Correct radius of other wheels (to use 100% coverage)
        width = self.aw.qmc.wradii[x]
        ll = len(self.aw.qmc.wradii)
        for i in range(ll):
            if i != x:
                self.aw.qmc.wradii[i] += float(width)/(ll-1)
        
        # Remove wheel data
        self.aw.qmc.wheelnames.pop(x)
        self.aw.qmc.wradii.pop(x)
        self.aw.qmc.startangle.pop(x)
        self.aw.qmc.projection.pop(x)
        self.aw.qmc.wheeltextsize.pop(x)
        self.aw.qmc.segmentlengths.pop(x)
        self.aw.qmc.segmentsalpha.pop(x)
        self.aw.qmc.wheellabelparent.pop(x)
        self.aw.qmc.wheelcolor.pop(x)
        
        self.createdatatable()
        self.aw.qmc.drawWheel()
```

**Delete Wheel Features:**
- **Proportional Adjustment**: Other wheels expand to fill space
- **100% Coverage**: Maintains total radius coverage
- **Complete Cleanup**: Removes all associated data
- **Real-time Updates**: Immediate visual feedback

### File Operations

#### **Save and Load System**
```python
@pyqtSlot(bool)
def fileSave(self, _: bool = False) -> None:
    try:
        filename = self.aw.ArtisanSaveFileDialog(
            msg=QApplication.translate('Message', 'Save Wheel graph'), 
            ext='*.wg'
        )
        if filename:
            self.aw.serialize(filename, cast(Dict[str, Any], self.aw.getWheelGraph()))
            self.aw.sendmessage(QApplication.translate('Message', 'Wheel Graph saved'))
    except OSError as e:
        self.aw.qmc.adderror(
            (QApplication.translate('Error Message', 'IO Error:') + 
             ' Wheel graph filesave(): {0}').format(str(e))
        )

@pyqtSlot(bool)
def loadWheel(self, _: bool = False) -> None:
    filename = self.aw.ArtisanOpenFileDialog(
        msg=QApplication.translate('Message', 'Open Wheel Graph'),
        path=self.aw.getDefaultPath(), 
        ext='*.wg'
    )
    if filename:
        self.aw.loadWheel(filename)
        self.aw.wheelpath = filename
        self.createdatatable()
        self.aw.qmc.drawWheel()
```

**File Features:**
- **WG Format**: Custom wheel graph file format
- **Serialization**: Complete wheel configuration storage
- **Error Handling**: Graceful handling of file operations
- **Path Management**: Integration with default file paths
- **State Restoration**: Complete wheel configuration restoration

### Advanced Configuration Options

#### **Aspect Ratio Control**
```python
@pyqtSlot(float)
def setaspect(self, _: float) -> None:
    self.aw.qmc.wheelaspect = self.aspectSpinBox.value()
    self.aw.qmc.drawWheel()
```

**Aspect Features:**
- **Range Control**: 0.0 to 2.0 aspect ratio range
- **Step Control**: 0.1 increment precision
- **Real-time Updates**: Immediate visual feedback
- **Visual Distortion**: Control wheel shape and appearance

#### **Edge and Line Management**
```python
@pyqtSlot(int)
def setedge(self, _: int) -> None:
    self.aw.qmc.wheeledge = float(self.edgeSpinBox.value())/100.
    self.aw.qmc.drawWheel()

@pyqtSlot(int)
def setlinewidth(self, _: int) -> None:
    self.aw.qmc.wheellinewidth = self.linewidthSpinBox.value()
    self.aw.qmc.drawWheel()

@pyqtSlot(bool)
def setlinecolor(self, _: bool = False) -> None:
    colorf = self.aw.colordialog(QColor(self.aw.qmc.wheellinecolor))
    if colorf.isValid():
        colorname = str(colorf.name())
        self.aw.qmc.wheellinecolor = colorname
        self.aw.qmc.drawWheel()
```

**Visual Enhancement Features:**
- **Edge Control**: Decorative edges between wheels (0-5 range)
- **Line Width**: Configurable line thickness (0-20 range)
- **Line Color**: Customizable line colors
- **Precision Control**: Fine-tuned visual appearance

### Integration and Workflow

#### **View Mode Integration**
```python
@pyqtSlot(bool)
def viewmode(self, _: bool = False) -> None:
    self.close()
    self.aw.qmc.connectWheel()
    self.aw.qmc.drawWheel()

@pyqtSlot('QCloseEvent')
def closeEvent(self, _: Optional['QCloseEvent'] = None) -> None:
    self.viewmode(False)
```

**Integration Features:**
- **Seamless Transition**: Switch between edit and view modes
- **Wheel Connection**: Integrate with main application
- **State Persistence**: Maintain wheel configuration
- **Workflow Integration**: Part of complete roasting workflow

#### **Real-time Updates**
```python
# Throughout the module, changes trigger immediate updates:
self.aw.qmc.drawWheel()  # Redraw wheel visualization
self.createdatatable()    # Update data tables
```

**Update Features:**
- **Immediate Feedback**: Changes visible instantly
- **Synchronized Updates**: All views update simultaneously
- **Performance Optimization**: Efficient redraw operations
- **User Experience**: Responsive editing interface

This module represents a sophisticated visual design tool that enables professional roasters to create complex, hierarchical data visualizations through an intuitive circular interface, providing both artistic expression and functional data representation for coffee roasting analysis and presentation.