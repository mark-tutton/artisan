# Artisan Curves Dialog Module Documentation

## File: `src/artisanlib/curves.py`

### Overview
This module implements the **comprehensive Curves Configuration Dialog** for the Artisan coffee roasting application. At 2,663 lines, it provides an extensive interface for configuring all aspects of roasting curve visualization, mathematical analysis, filtering, and display settings through a tabbed interface.

### Purpose and Architecture
The `curves.py` module serves as the **central configuration hub** for Artisan's visualization and analysis capabilities, implementing:
- **Rate of Rise (RoR) configuration** for temperature differential calculations
- **Data filtering and smoothing** for noise reduction and curve enhancement
- **Mathematical plotting tools** for custom curve generation and analysis
- **Display customization** including themes, fonts, and visual effects
- **Advanced analysis tools** including polynomial fitting and statistical analysis

### Core Classes

#### `equDataDlg` Class
**Purpose**: Displays tabular data for plotter equations and mathematical expressions.

**Key Features**:
- **Data Table**: Shows computed values for P1-P9 plotter equations
- **Precision Control**: Adjustable decimal places (1-6) for data display
- **Copy Functionality**: Clipboard export with tabular formatting options
- **Dynamic Updates**: Real-time data refresh based on current roast profile

**Key Methods**:
- `createDataTable()`: Generates the data display table
- `copyDataTabletoClipboard()`: Exports data to clipboard with formatting options
- `changeprecision()`: Adjusts decimal precision for all displayed values

#### `CurvesDlg` Class
**Purpose**: Main configuration dialog with 6 comprehensive tabs for all curve-related settings.

**Tab Structure**:
1. **RoR Tab**: Rate of Rise configuration and LCD display settings
2. **Filters Tab**: Data filtering, smoothing, and input processing
3. **Plotter Tab**: Custom mathematical plotting with 9 equation slots
4. **Math Tab**: Advanced mathematical analysis tools
5. **Analyze Tab**: Curve fitting and analysis interval configuration
6. **UI Tab**: Appearance, resolution, and display customization

### Key Configuration Areas

#### Rate of Rise (RoR) Configuration
**Delta Temperature Settings**:
- **ET/BT Delta Flags**: Enable/disable rate of rise calculations
- **Filter Sensitivity**: Adjustable smoothing filters (0-40 pads)
- **Delta Span**: Time intervals for RoR calculations (1-30 seconds)
- **LCD Display**: Show RoR values on main display with swap options
- **Projection Settings**: Linear/quadratic curve projections for ET/BT

**Mathematical Functions**:
- **Custom Formulas**: User-defined mathematical expressions for delta calculations
- **Symbolic Assignments**: Variable-based formula definitions
- **Polyfit Computation**: Polynomial fitting for improved RoR accuracy

#### Data Filtering and Processing
**Input Filters**:
- **Duplicate Handling**: Interpolate or drop duplicate temperature readings
- **Spike Detection**: Remove anomalous temperature spikes
- **Min/Max Limits**: Temperature range validation
- **ET/BT Swapping**: Exchange environmental and bean temperature roles

**Curve Smoothing**:
- **Filter Strength**: Adjustable smoothing (0-5 filter levels)
- **Drop Interpolation**: Fill gaps in temperature data
- **Optimal Smoothing**: Post-roast curve enhancement algorithms

#### Mathematical Plotting System
**Equation Slots (P1-P9)**:
- **Custom Formulas**: Mathematical expressions using roast variables
- **Color Customization**: Individual curve color selection
- **Background Integration**: Set curves as background reference profiles
- **Virtual Device Creation**: Convert plots to virtual temperature sensors

**Advanced Features**:
- **Annotation Support**: Text labels with positioning and sizing
- **Special Commands**: Beans visualization, program execution
- **Variable Support**: Access to all roast data variables (P, F, $, #)

#### Mathematical Analysis Tools
**Interpolation Methods**:
- **Linear**: Basic linear interpolation between data points
- **Cubic**: 3rd order spline interpolation for smooth curves
- **Nearest**: Use nearest neighbor values

**Statistical Analysis**:
- **Univariate Analysis**: Statistical analysis of single variables
- **Logarithmic Regression**: Natural log curve fitting
- **Exponential Fitting**: Power function analysis (x², x³)
- **Polynomial Fitting**: Custom degree polynomial regression

**Analysis Intervals**:
- **Event-Based**: Start analysis at roast milestones (DRY END, FC START)
- **Custom Timing**: User-defined time offsets from CHARGE
- **Threshold Configuration**: Significance thresholds for analysis

#### Display and Appearance
**Visual Customization**:
- **Graph Styles**: Classic and xkcd plotting styles
- **Font Selection**: Multiple font options including international support
- **Path Effects**: Visual enhancement levels (0-5)
- **Glow Effects**: Enhanced curve visibility options

**Resolution and Performance**:
- **DPI Settings**: Adjustable resolution (40-300%)
- **Performance Options**: Balance between quality and speed
- **Theme Selection**: Qt application style customization

**Web Integration**:
- **WebLCDs**: Remote monitoring via web interface
- **QR Code Generation**: Easy mobile device access
- **Port Configuration**: Customizable web server ports

### Technical Implementation

#### State Management
**Configuration Preservation**:
- **Original Values**: Store initial settings for cancellation
- **Real-time Updates**: Immediate application of most changes
- **Settings Persistence**: Save dialog position and tab state

**Validation and Error Handling**:
- **Input Validation**: Range checking and format validation
- **Error Reporting**: Comprehensive error logging and user feedback
- **Graceful Degradation**: Fallback behavior for invalid configurations

#### Performance Optimization
**Redraw Management**:
- **Selective Updates**: Minimize unnecessary chart redraws
- **Delta Recalculation**: Smart delta temperature updates
- **Background Processing**: Non-blocking UI updates

**Memory Management**:
- **Data Caching**: Store computed values to avoid recalculation
- **Efficient Updates**: Batch multiple configuration changes
- **Resource Cleanup**: Proper disposal of temporary objects

### Integration Points

#### Main Application Integration
- **Canvas Updates**: Direct communication with plotting canvas
- **LCD Management**: Integration with display systems
- **Plugin Support**: Extensible configuration system

#### Data Flow
- **Real-time Updates**: Live configuration changes during roasting
- **Profile Integration**: Settings applied to current and background profiles
- **Export Support**: Configuration persistence across sessions

### Usage Patterns

#### Roasting Workflow
1. **Pre-Roast**: Configure RoR settings and display preferences
2. **During Roast**: Adjust filters and smoothing in real-time
3. **Post-Roast**: Apply mathematical analysis and curve fitting
4. **Analysis**: Use plotting tools for detailed curve examination

#### Configuration Management
- **Tab-based Organization**: Logical grouping of related settings
- **Immediate Preview**: Most changes visible without dialog closure
- **Cancel/Restore**: Ability to revert all changes
- **Settings Persistence**: Remember user preferences across sessions

### Advanced Features

#### Mathematical Expression Engine
**Variable Support**:
- **Time Variables**: Access to roast timing data
- **Temperature Variables**: Current and historical temperature values
- **Event Variables**: Roast milestone timing
- **Custom Functions**: User-defined mathematical operations

**Expression Evaluation**:
- **Real-time Calculation**: Live computation during roasting
- **Error Handling**: Graceful handling of invalid expressions
- **Performance Optimization**: Efficient mathematical evaluation

#### Virtual Device System
**Device Creation**:
- **Mathematical Sources**: Convert formulas to virtual sensors
- **Color Management**: Customizable device colors
- **Integration**: Seamless integration with main display system

### Security and Safety

#### Code Execution Safety
- **Expression Validation**: Safe mathematical expression evaluation
- **Program Execution**: Controlled execution environment for plotter programs
- **Input Sanitization**: Validation of all user inputs

#### Error Prevention
- **Range Validation**: Prevent invalid configuration values
- **State Consistency**: Maintain application stability
- **User Feedback**: Clear error messages and validation feedback

This module represents the **core configuration interface** for Artisan's visualization and analysis capabilities, providing professional roasters with comprehensive tools for customizing their roasting experience while maintaining system stability and performance.