# Artisan Colors Configuration Dialog Module Documentation

## File: `src/artisanlib/colors.py`

### Overview
This module implements the **comprehensive Colors Configuration Dialog** for the Artisan coffee roasting application. At 970 lines, it provides an extensive interface for customizing all visual aspects of the application including chart colors, LCD displays, background elements, and comprehensive theming capabilities through a sophisticated tabbed interface system.

### Purpose and Architecture
The `colors.py` module serves as the **central visual customization hub** for Artisan, implementing:
- **Multi-Tab Interface**: Curves, Graph, and LCDs configuration tabs
- **Comprehensive Color Management**: All application color customization
- **Real-time Preview**: Immediate visual feedback on color changes
- **Theme Management**: Built-in themes and custom color schemes
- **Opacity Control**: Advanced transparency and opacity settings

### Key Components

#### 1. **Main Dialog Class: `graphColorDlg`**

##### **Initialization and Tab Structure**
```python
def __init__(self, parent:QWidget, aw:'ApplicationWindow', activeTab:int = 0) -> None:
```
- **Purpose**: Initialize the comprehensive color configuration dialog
- **Features**: 
  - Three main configuration tabs
  - Modal dialog with persistent tab state
  - Integration with main application window
  - Real-time color preview system

##### **Tab Organization**
- **Tab 0: Curves**: Profile and background curve colors
- **Tab 1: Graph**: Chart elements and UI colors
- **Tab 2: LCDs**: Digital display color configuration

#### 2. **Tab 0: Curves Configuration**

##### **Profile Colors**
```python
self.metButton = QPushButton()        # ET (Environment Temperature)
self.btButton = QPushButton()         # BT (Bean Temperature)
self.deltametButton = QPushButton()   # Delta ET
self.deltabtButton = QPushButton()    # Delta BT
```

- **Primary Temperature Curves**: ET and BT main curve colors
- **Delta Temperature Curves**: Rate of change curve colors
- **Color Buttons**: Interactive color selection with preview
- **Real-time Updates**: Immediate color application

##### **Background Profile Colors**
```python
self.bgmetButton = QPushButton()      # Background ET
self.bgbtButton = QPushButton()       # Background BT
self.bgdeltametButton = QPushButton() # Background Delta ET
self.bgdeltabtButton = QPushButton()  # Background Delta BT
self.bgextraButton = QPushButton()    # Background Extra 1
self.bgextra2Button = QPushButton()   # Background Extra 2
```

- **Background Curve Colors**: Colors for reference/background profiles
- **Extra Device Colors**: Additional temperature source colors
- **Opacity Control**: Background curve transparency settings
- **Visual Separation**: Clear distinction from foreground curves

##### **Opacity and Transparency**
```python
self.opaqbgSpinBox = QSpinBox()
self.opaqbgSpinBox.setRange(1,10)
self.opaqbgSpinBox.setValue(int(round(self.aw.qmc.backgroundalpha * 10)))
```

- **Background Opacity**: 0-10 scale (transparent to opaque)
- **Real-time Adjustment**: Immediate opacity changes
- **Visual Feedback**: Live preview of transparency effects
- **Consistent Scaling**: Standardized opacity values

#### 3. **Tab 1: Graph Configuration**

##### **Chart Element Colors**
```python
self.canvasButton = QPushButton()           # Chart canvas
self.backgroundButton = QPushButton()       # Chart background
self.titleButton = QPushButton()            # Chart title
self.gridButton = QPushButton()             # Grid lines
self.yButton = QPushButton()                # Y-axis labels
self.xButton = QPushButton()                # X-axis labels
```

- **Core Chart Elements**: Fundamental chart appearance
- **Grid System**: Grid line color and visibility
- **Axis Labels**: X and Y axis text colors
- **Background Elements**: Chart background and canvas colors

##### **Phase and Event Colors**
```python
self.rect1Button = QPushButton()            # Drying Phase
self.rect2Button = QPushButton()            # Maillard Phase
self.rect3Button = QPushButton()            # Finishing Phase
self.rect4Button = QPushButton()            # Cooling Phase
self.rect5Button = QPushButton()            # Bars Background
```

- **Roasting Phases**: Color coding for different roasting phases
- **Visual Organization**: Clear phase identification
- **Professional Appearance**: Consistent color scheme
- **User Customization**: Individual phase color control

##### **Special Elements and Analysis**
```python
self.specialeventboxButton = QPushButton()  # Special Event Markers
self.specialeventtextButton = QPushButton() # Special Event Text
self.bgeventmarkerButton = QPushButton()    # Background Event Markers
self.bgeventtextButton = QPushButton()      # Background Event Text
self.analysismaskButton = QPushButton()     # Analysis Mask
self.statsanalysisbkgndButton = QPushButton() # Statistics Background
```

- **Event Markers**: Custom event visualization colors
- **Analysis Tools**: Analysis mask and statistics colors
- **Text Elements**: Event text and label colors
- **Background Elements**: Analysis background colors

##### **Advanced Chart Elements**
```python
self.markersButton = QPushButton()          # Data markers
self.textButton = QPushButton()             # General text
self.watermarksButton = QPushButton()       # Watermarks
self.timeguideButton = QPushButton()        # Time guides
self.aucguideButton = QPushButton()         # AUC guides
self.aucareaButton = QPushButton()          # AUC areas
```

- **Data Visualization**: Marker and text colors
- **Guides and Overlays**: Time and AUC guide colors
- **Watermarks**: Background watermark colors
- **Professional Elements**: Chart enhancement colors

##### **Legend and UI Elements**
```python
self.legendbgButton = QPushButton()         # Legend background
self.legendborderButton = QPushButton()     # Legend border
self.legendbgSpinBox = QSpinBox()           # Legend opacity
```

- **Legend System**: Legend appearance and styling
- **Opacity Control**: Legend background transparency
- **Border Styling**: Legend border colors
- **Professional Layout**: Consistent legend appearance

#### 4. **Tab 2: LCDs Configuration**

##### **LCD Display Colors**
```python
self.lcd1LEDButton = QPushButton()          # Timer LCD digits
self.lcd1backButton = QPushButton()         # Timer LCD background
self.lcd2LEDButton = QPushButton()          # ET LCD digits
self.lcd2backButton = QPushButton()         # ET LCD background
# ... additional LCD configurations
```

- **8 LCD Displays**: Comprehensive LCD color management
- **Digit Colors**: LED digit appearance
- **Background Colors**: LCD background styling
- **Individual Control**: Per-LCD color customization

##### **LCD Categories**
- **Timer LCD**: Roasting timer display
- **ET LCD**: Environment temperature display
- **BT LCD**: Bean temperature display
- **Delta ET LCD**: Delta environment temperature
- **Delta BT LCD**: Delta bean temperature
- **Extra Devices LCD**: Additional device displays
- **Ramp/Soak Timer LCD**: Ramp/soak timing display
- **Slow Cooling Timer LCD**: Cooling phase timing

##### **LCD Color Management**
```python
def setlcdColor(self, palette:Dict[str,str], disj_palette:Dict[str,str], select:str) -> None:
```

- **Color Validation**: Prevents identical digit/background colors
- **Alpha Support**: Transparency support for LCD colors
- **Real-time Updates**: Immediate LCD color changes
- **Consistency Checks**: Color contrast validation

#### 5. **Color Management System**

##### **Color Button System**
```python
def colorButton(self, s:str) -> QPushButton:
def setColorButton(self, button:QPushButton, tag:str) -> None:
```

- **Interactive Buttons**: Clickable color selection buttons
- **Color Preview**: Real-time color display
- **Text Contrast**: Automatic text color adjustment
- **Consistent Styling**: Unified button appearance

##### **Color Selection Dialog**
```python
def setColor(self, title:str, var:QPushButton, color:str) -> None:
def setbgColor(self, title:str, var:QPushButton, color:str) -> None:
```

- **Native Color Dialog**: System color picker integration
- **Alpha Support**: Transparency and opacity control
- **Real-time Application**: Immediate color changes
- **Validation**: Color value validation and error handling

##### **Color Conversion and Management**
```python
from artisanlib.util import rgba_colorname2argb_colorname, argb_colorname2rgba_colorname
```

- **Format Conversion**: RGBA/ARGB color format handling
- **Cross-platform Support**: Consistent color representation
- **Alpha Channel**: Proper transparency handling
- **Color Validation**: Robust color value validation

#### 6. **Theme Management System**

##### **Built-in Themes**
```python
@pyqtSlot(bool)
def recolor1(self, _:bool) -> None:        # Default theme
def recolor2(self, _:bool) -> None:        # Grey theme
```

- **Default Theme**: Standard Artisan color scheme
- **Grey Theme**: Monochromatic color scheme
- **Theme Switching**: Instant theme application
- **Consistent Styling**: Unified theme appearance

##### **Theme Application**
```python
def setLCD_bw(self, _:bool) -> None:       # Black/White LCD theme
```

- **LCD Themes**: Specialized LCD color schemes
- **Professional Appearance**: Clean, readable displays
- **Theme Consistency**: Unified LCD appearance
- **User Preferences**: Customizable theme options

### Technical Implementation Details

#### **Real-time Updates**
- **Immediate Application**: Color changes applied instantly
- **Canvas Updates**: Automatic chart redraw on color changes
- **LCD Updates**: Real-time LCD appearance updates
- **Performance Optimization**: Efficient update mechanisms

#### **Color Validation**
- **Contrast Checking**: Prevents unreadable color combinations
- **Alpha Validation**: Proper transparency value handling
- **Format Validation**: Color format consistency
- **Error Prevention**: Comprehensive error handling

#### **State Management**
- **Tab Persistence**: Remembers active tab across sessions
- **Color Persistence**: Automatic color setting persistence
- **Theme Persistence**: Theme selection persistence
- **User Preferences**: Comprehensive preference management

### Integration Points

#### **Main Application**
- **Chart System**: Direct integration with main chart display
- **LCD System**: Comprehensive LCD color management
- **Settings System**: Color configuration persistence
- **Theme System**: Built-in and custom theme support

#### **Visualization System**
- **Canvas Management**: Chart canvas color control
- **Grid System**: Grid appearance and styling
- **Phase Visualization**: Roasting phase color coding
- **Event System**: Event marker and text colors

#### **User Interface**
- **Button Styling**: Consistent button appearance
- **Text Colors**: Readable text color management
- **Background Elements**: UI background styling
- **Professional Appearance**: Consistent visual design

### Configuration and Customization

#### **Color Parameters**
- **Primary Colors**: Main temperature curve colors
- **Background Colors**: Reference profile colors
- **UI Colors**: Interface element colors
- **LCD Colors**: Display appearance colors

#### **Opacity Settings**
- **Background Opacity**: Background curve transparency
- **Legend Opacity**: Legend background transparency
- **Analysis Opacity**: Analysis mask transparency
- **Statistics Opacity**: Statistics background transparency

#### **Theme Options**
- **Default Theme**: Standard Artisan appearance
- **Grey Theme**: Monochromatic color scheme
- **Black/White LCD**: Clean LCD appearance
- **Custom Colors**: User-defined color schemes

### Best Practices and Usage

#### **Color Selection**
- **Contrast Considerations**: Ensure readable color combinations
- **Professional Appearance**: Maintain consistent visual design
- **Phase Identification**: Use distinct colors for different phases
- **Accessibility**: Consider color vision accessibility

#### **Theme Management**
- **Consistent Application**: Apply themes consistently across elements
- **User Preferences**: Respect user color preferences
- **Professional Standards**: Maintain professional appearance
- **Customization Balance**: Balance customization with usability

#### **Performance Considerations**
- **Update Frequency**: Minimize unnecessary color updates
- **Memory Management**: Efficient color value storage
- **Rendering Optimization**: Optimize chart redraw performance
- **User Experience**: Smooth color change application

### Future Enhancements

#### **Planned Improvements**
- **Advanced Themes**: More sophisticated theme options
- **Color Palettes**: Predefined color palette support
- **Export/Import**: Theme sharing and distribution
- **Advanced Opacity**: More granular transparency control

#### **Extensibility Features**
- **Plugin Themes**: Plugin-defined color schemes
- **Custom Palettes**: User-defined color palettes
- **Advanced Styling**: More sophisticated visual customization
- **Theme Engine**: Enhanced theme management system

This module represents Artisan's comprehensive color management system, providing professional-grade visual customization capabilities that enable users to create personalized, professional-looking roasting interfaces while maintaining consistency and usability across all application elements.