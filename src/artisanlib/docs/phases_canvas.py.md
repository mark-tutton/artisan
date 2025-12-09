# Artisan Phases Canvas Module Documentation

## File: `src/artisanlib/phases_canvas.py`

### Overview
This module implements the **specialized phases visualization canvas** for the Artisan coffee roasting application. At 251 lines, it provides a sophisticated horizontal bar chart system for displaying roasting phase timing and percentages across multiple profiles, with intelligent data visualization and user interaction capabilities.

### Purpose and Architecture
The `phases_canvas.py` module serves as the **roasting phase analysis interface** for Artisan, implementing:
- **Phase Visualization**: Horizontal bar charts showing drying, maillard, and finishing phases
- **Multi-profile Comparison**: Side-by-side comparison of multiple roasting profiles
- **Intelligent Layout**: Dynamic sizing and spacing based on data content
- **Visual State Management**: Active/inactive profile differentiation and alignment indicators
- **Interactive Display**: Matplotlib-based canvas with Qt integration

### Core Classes

#### **`tphasescanvas` (Phases Canvas Class)**
The main canvas class that extends matplotlib's FigureCanvas for Qt integration:

```python
class tphasescanvas(FigureCanvas):
    __slots__ = [
        'aw', 'dpi_offset', 'barheight', 'm', 'g', 'data', 'fig', 'ax', 
        'tight_layout_params'
    ]
```

**Key Attributes:**
- **`aw`**: Reference to main ApplicationWindow
- **`dpi_offset`**: DPI adjustment for optimal display (-30%)
- **`barheight`**: Height of individual phase bars (0.88 of row height)
- **`m`**: Width of batch number and drop time fields (10 units)
- **`g`**: Gap width between fields and phase bars (2 units)
- **`data`**: Phases data structure for visualization
- **`fig`**: Matplotlib Figure object
- **`ax`**: Matplotlib Axes object for plotting

### Data Structure and Format

#### **Phases Data Format**
The module expects data in a specific tuple format:

```python
# data format: List[Tuple[str, float, Tuple[float,float,float], bool, bool, str]]
# Each tuple contains:
# - label: Profile name/identifier
# - total_time: Total roasting time in seconds
# - phases_times: Tuple of (phase1_time, phase2_time, phase3_time) in seconds
# - active: Boolean indicating if profile is currently active
# - aligned: Boolean indicating if profile is aligned to current target
# - color: Color string (e.g., '#00b950') for profile identification
```

**Phase Definitions:**
- **Phase 1**: Drying Phase (from charge to end of drying)
- **Phase 2**: Maillard Phase (from end of drying to first crack)
- **Phase 3**: Finishing Phase (from first crack to drop)

### Canvas Initialization and Configuration

#### **DPI and Layout Management**
```python
def __init__(self, dpi: int, aw: 'ApplicationWindow') -> None:
    self.dpi_offset = -30  # Reduce DPI by 30% for optimal display
    self.fig = Figure(figsize=(1, 1), frameon=False, dpi=dpi + self.dpi_offset)
    
    # Layout configuration for optimal spacing
    self.tight_layout_params: Final[Dict[str, float]] = {
        'pad': .3, 'h_pad': 0.0, 'w_pad': 0.0
    }
    self.fig.set_layout_engine('tight', **self.tight_layout_params)
```

#### **Canvas Clearing and Setup**
```python
def clear_phases(self) -> None:
    """Initializes or clears the phases canvas"""
    if self.ax is None:
        self.ax = self.fig.add_subplot(111, frameon=False)
    if self.ax is not None:
        self.ax.clear()
        self.ax.axis('off')
        self.ax.grid(False)
        # Set x-axis limits to accommodate all elements
        self.ax.set_xlim(0, 100 + 2*self.m + 2*self.g)
```

### Dynamic DPI Management

#### **DPI Adjustment System**
```python
def setdpi(self, dpi: int, moveWindow: bool = True) -> None:
    """Dynamically adjusts canvas DPI and updates display"""
    if self.aw is not None and self.fig and dpi >= 40:
        try:
            # Apply DPI offset and device pixel ratio
            self.fig.set_dpi((dpi + self.dpi_offset) * self.aw.devicePixelRatio())
            if moveWindow:
                with warnings.catch_warnings():
                    warnings.simplefilter('ignore')
                    self.fig.canvas.draw()
                FigureCanvas.updateGeometry(self)
            # Update scroller height to match new canvas size
            self.aw.scroller.setMaximumHeight(self.sizeHint().height())
        except Exception as e:
            _log.exception(e)
```

### Data Management and Updates

#### **Data Setting and Updates**
```python
def set_phases(self, data: Optional[List[Tuple[str, float, Tuple[float,float,float], bool, bool, str]]]) -> None:
    """Sets the phases data for visualization"""
    self.data = data

def update_phases(self, data: Optional[List[Tuple[str, float, Tuple[float,float,float], bool, bool, str]]]) -> None:
    """Updates phases data and triggers redraw"""
    self.set_phases(data)
    self.redraw_phases()
```

### Core Visualization Engine

#### **Phase Bar Generation**
The `redraw_phases()` method implements sophisticated phase visualization logic:

```python
def redraw_phases(self) -> None:
    """Main visualization method that renders all phase bars"""
    if self.ax is None:
        return
    
    self.clear_phases()
    if self.data is not None and len(self.data):
        self.aw.scroller.setVisible(True)
        
        # Set background color from palette
        background_color = self.aw.qmc.palette['background']
        self.setStyleSheet(f'background-color: {background_color[:7]}')
        
        # Calculate maximum total time for scaling
        max_total_time = max(p[1] for p in self.data)
        
        # Configure font properties
        if self.aw:
            prop = self.aw.mpl_fontproperties
        else:
            prop = FontProperties().copy()
        prop.set_family(mpl.rcParams['font.family'])
        prop.set_size('medium')
        
        # Get decimal places for LCD display
        digits = (1 if self.aw.qmc.LCDdecimalplaces else 0)
        
        # Create dimmed colors for inactive profiles
        rect1dim = toDim(self.aw.qmc.palette['rect1'])
        rect2dim = toDim(self.aw.qmc.palette['rect2'])
        rect3dim = toDim(self.aw.qmc.palette['rect3'])
```

#### **Phase Bar Rendering Logic**
The method handles three different phase scenarios:

**1. Complete Phase Data:**
```python
if all(phases_times):
    # All three phases are defined
    if int(round(total_time)) == int(round(sum(phases_times))):
        # Calculate phase percentages
        phases_percentages = [(phase_time/total_time) * 100. for phase_time in phases_times]
        
        # Create extended layout with labels and gaps
        extended_phases_percentages = [
            self.m, self.g,  # Batch number field and gap
            *phases_percentages,  # Phase percentages
            self.g,  # Gap
            self.m * total_time / max_total_time  # Scaled drop time field
        ]
        
        # Generate bar widths and starting positions
        widths = numpy.array(extended_phases_percentages)
        starts = widths.cumsum() - widths
        
        # Create labels with percentages and times
        if active:
            labels = [
                f"{str(round(percent,digits)).rstrip('0').rstrip('.')}%  {stringfromseconds(tx,leadingzero=False)}" 
                if percent > 20 else (
                    f"{str(round(percent,digits)).rstrip('0').rstrip('.')}%" 
                    if percent > 10 else ''
                )
                for (percent, tx) in zip(phases_percentages, phases_times)
            ]
        else:
            labels = [''] * 3
        
        # Complete label array
        labels = [label, ''] + labels + ['', stringfromseconds(total_time,leadingzero=False)]
        
        # Set colors based on active state
        if active:
            patch_colors = [
                color, background_color,  # Profile color, background
                self.aw.qmc.palette['rect1'],  # Drying phase
                self.aw.qmc.palette['rect2'],  # Maillard phase  
                self.aw.qmc.palette['rect3'],  # Finishing phase
                background_color, color  # Background, profile color
            ]
        else:
            patch_colors = [
                color, background_color, rect1dim, rect2dim, rect3dim, 
                background_color, color
            ]
```

**2. Drying Phase Only:**
```python
elif phases_times[0] and not phases_times[1] and not phases_times[2]:
    # Only Drying Phase is defined
    phase1_percentage = (phases_times[0]/total_time) * 100.
    phases_percentages = [phase1_percentage, 100-phase1_percentage]
    
    # Create layout with missing phase indicators
    extended_phases_percentages = [
        self.m, self.g, phases_percentages, self.g, 
        self.m * total_time / max_total_time
    ]
    
    # Generate labels
    if active:
        label1 = (
            f"{str(round(phase1_percentage,digits)).rstrip('0').rstrip('.')}%  {stringfromseconds(phases_times[0],leadingzero=False)}" 
            if phase1_percentage > 20 else (
                f"{str(round(phase1_percentage,digits)).rstrip('0').rstrip('.')}%" 
                if phase1_percentage > 10 else ''
            )
        )
    else:
        label1 = ''
    
    labels = [label, '', label1, '', '', stringfromseconds(total_time,leadingzero=False)]
```

**3. Finishing Phase Only:**
```python
elif not phases_times[0] and not phases_times[1] and phases_times[2]:
    # Only Finishing Phase is defined
    phase3_percentage = (phases_times[2]/total_time) * 100.
    phases_percentages = [100-phase3_percentage, phase3_percentage]
    
    # Similar layout logic for finishing phase only
    # ... implementation details
```

### Visual Enhancement Features

#### **Text Color Contrast Management**
```python
# Set text colors for optimal contrast
if active:
    text_colors = [
        'white' if self.aw.QColorBrightness(QColor(c)) < 128 else 'black' 
        for c in patch_colors
    ]
else:
    text_colors = [
        'gainsboro' if self.aw.QColorBrightness(QColor(c)) < 128 else 'dimgrey' 
        for c in patch_colors
    ]

# Apply colors to text boxes
for j, tb in enumerate(tboxes):
    tb.set_color(text_colors[j])
```

#### **Graph Style and Sketch Effects**
```python
# Apply sketch parameters for artistic rendering
if self.aw.qmc.graphstyle:
    for c in rects.get_children():
        c.set_sketch_params(scale=1, length=700, randomness=12)
```

### Dynamic Layout Management

#### **Canvas Sizing and Positioning**
```python
# Calculate optimal canvas height based on number of profiles
x, _ = self.fig.get_size_inches()
self.fig.set_size_inches(x, (i-1)*0.35 + 0.445, forward=True)

# Set y-axis limits to eliminate borders
self.ax.set_ylim((-0.5, i-0.5))

# Update scroller height to match canvas
self.aw.scroller.setMaximumHeight(self.sizeHint().height())
```

#### **Empty State Handling**
```python
else:
    # No profiles to display
    QSettings().setValue('MainSplitter', self.aw.splitter.saveState())
    if self.ax is not None:
        self.ax.set_ylim((0, 0))
    self.aw.scroller.setMaximumHeight(0)
    self.aw.scroller.setVisible(False)
```

### Integration Points

#### **Main Application Integration**
- **Application Window**: Receives reference to main application for palette and settings access
- **Scroller Management**: Integrates with scroll area for proper sizing
- **Splitter State**: Saves and restores splitter configuration
- **Font Management**: Uses application font properties for consistency

#### **Matplotlib Integration**
- **Figure Canvas**: Extends matplotlib's FigureCanvas for Qt compatibility
- **Backend Integration**: Uses QtAgg backend for optimal Qt integration
- **Layout Engine**: Leverages matplotlib's tight layout for optimal spacing
- **Rendering Pipeline**: Integrates with matplotlib's drawing system

### Performance Optimizations

#### **Efficient Data Processing**
- **NumPy Arrays**: Uses numpy for efficient array operations
- **Cumulative Sums**: Optimizes bar positioning calculations
- **Conditional Rendering**: Only renders visible elements
- **Memory Management**: Efficient use of matplotlib objects

#### **Smart Rendering**
- **Canvas Updates**: Uses `draw_idle()` for efficient redraws
- **Geometry Updates**: Only updates when necessary
- **Warning Suppression**: Handles matplotlib warnings gracefully
- **Error Handling**: Robust exception handling for rendering failures

### Visual Customization

#### **Color Scheme Integration**
- **Palette System**: Integrates with Artisan's color palette system
- **Profile Colors**: Supports custom colors per profile
- **State Colors**: Different colors for active/inactive profiles
- **Contrast Management**: Automatic text color selection for readability

#### **Layout Flexibility**
- **Dynamic Sizing**: Automatically adjusts to content
- **Gap Management**: Configurable spacing between elements
- **Field Sizing**: Adjustable batch number and time field widths
- **Responsive Design**: Adapts to different screen sizes and DPI settings

### Error Handling and Robustness

#### **Data Validation**
```python
if int(round(total_time)) == int(round(sum(phases_times))):
    # Process valid data
    # ... rendering logic
else:
    _log.error('redraw_phases(): inconsistent phases data in %s (total: %s, sum(phases): %s)', 
               label, total_time, sum(phases_times))
    # Skip inconsistent data
```

#### **Exception Handling**
- **Rendering Failures**: Graceful handling of matplotlib errors
- **Data Corruption**: Validation of phase timing consistency
- **Resource Management**: Proper cleanup of failed operations
- **User Feedback**: Clear error logging for debugging

### Future Enhancement Possibilities

#### **Planned Features**
- **Legend System**: Phase color legend (currently commented out)
- **Interactive Elements**: Clickable bars for profile selection
- **Animation Support**: Smooth transitions between states
- **Export Capabilities**: Save phase charts as images

#### **Performance Improvements**
- **Virtual Scrolling**: Handle large numbers of profiles efficiently
- **Caching**: Cache rendered elements for faster updates
- **Lazy Loading**: Load profile data on demand
- **GPU Acceleration**: Leverage hardware acceleration when available

This module represents a sophisticated visualization system that transforms complex roasting phase data into intuitive, informative charts, enabling roasters to quickly compare and analyze multiple roasting profiles through an elegant and responsive interface.