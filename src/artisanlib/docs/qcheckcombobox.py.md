
# Artisan Check Combo Box Module Documentation

## File: `src/artisanlib/qcheckcombobox.py`

### Overview
This module implements a **custom QComboBox subclass** for the Artisan coffee roasting application that enables multiple item selection through checkboxes. At 434 lines, it provides a sophisticated multi-selection interface that maintains Qt's native look and feel while extending functionality beyond standard combo box limitations.

### Purpose and Architecture
The `qcheckcombobox.py` module serves as a **custom UI component** for Artisan, implementing:
- **Multi-Selection Interface**: Checkbox-based selection allowing multiple items to be chosen simultaneously
- **Cross-Platform Compatibility**: PyQt5/PyQt6 dual support with automatic detection
- **Native Styling**: Maintains platform-specific visual appearance (Windows list-style, macOS menu-style)
- **Enhanced User Experience**: Keyboard navigation, mouse interaction, and visual feedback

### Key Components

#### **Main Class: `CheckComboBox`**
```python
class CheckComboBox(QComboBox):
    flagChanged = pyqtSignal(int, bool)  # Emits (index, checked_state)
```

**Core Features:**
- **Multiple Selection**: Users can check/uncheck multiple items independently
- **Placeholder Text**: Customizable text when no items are selected
- **Separator Configuration**: Configurable delimiter for displaying selected items
- **Event Filtering**: Sophisticated mouse and keyboard event handling

#### **Delegates for Styling**

**`ComboItemDelegate` (List-Style)**
- Used for Windows-style appearance
- Renders items as list view entries
- Handles separators and visual styling

**`ComboMenuDelegate` (Menu-Style)**
- Used for macOS Aqua-style appearance
- Renders items as menu entries
- Maintains native menu look and feel

### Technical Implementation

#### **Event Handling System**
```python
def eventFilter(self, obj, event):
    # Handles mouse clicks, keyboard navigation, and selection changes
    # Manages checkbox state toggling
    # Prevents unwanted popup dismissal
```

**Key Event Features:**
- **Mouse Click Handling**: Toggles checkbox states on item clicks
- **Keyboard Navigation**: Space bar toggles current item selection
- **Popup Management**: Prevents accidental dismissal during selection
- **Focus Management**: Maintains proper focus states

#### **Visual Rendering**
```python
def paintEvent(self, event):
    # Custom painting for selected items display
    # Shows checked items with separator
    # Displays placeholder text when nothing selected
```

**Display Logic:**
- **Selected Items**: Shows checked items joined by separator
- **Placeholder**: Displays custom text when no selection
- **Icon Support**: Maintains icon display capabilities
- **State Awareness**: Adapts to enabled/disabled states

### Configuration Options

#### **Initialization Parameters**
```python
def __init__(self, parent=None, placeholderText='', separator=', ', **kwargs):
    # parent: Parent widget
    # placeholderText: Text shown when no items selected
    # separator: Delimiter between selected items
```

#### **Customizable Properties**
- **Placeholder Text**: Configurable default display text
- **Separator Character**: Customizable delimiter (default: ", ")
- **Focus Policy**: Strong focus for keyboard navigation
- **Item Delegates**: Automatic style-based delegate selection

### Usage Patterns

#### **Basic Setup**
```python
# Create multi-selection combo box
cb = CheckComboBox(placeholderText='Select items...', separator=' | ')

# Add checkable items
cb.addItem('Temperature Sensor')
cb.addItem('Pressure Sensor')
cb.addItem('Humidity Sensor')

# Make items checkable
model = cb.model()
for i in range(cb.count()):
    item = model.item(i)
    if item:
        item.setCheckable(True)
```

#### **Event Handling**
```python
# Connect to selection changes
cb.flagChanged.connect(lambda index, checked: print(f"Item {index}: {checked}"))

# Get selected indices
selected = cb.checkedIndices()  # Returns [0, 2] if items 0 and 2 are checked
```

### Integration with Artisan

#### **Plugin System Usage**
This component is likely used throughout Artisan's plugin system for:
- **Device Selection**: Multiple sensor/device configuration
- **Feature Toggles**: Enabling/disabling multiple features simultaneously
- **Export Options**: Selecting multiple file formats or destinations
- **Notification Settings**: Configuring multiple notification types

#### **Configuration Dialogs**
Common usage in:
- **Port Configuration**: Selecting multiple communication ports
- **Event Management**: Choosing multiple event types to monitor
- **Data Export**: Selecting multiple export formats
- **Plugin Settings**: Enabling multiple plugin features

### Technical Considerations

#### **Performance Characteristics**
- **Event Filtering**: Efficient event handling with minimal overhead
- **Model Updates**: Direct model manipulation for checkbox states
- **Visual Updates**: Optimized painting and redraw operations
- **Memory Management**: Proper cleanup of event filters and timers

#### **Compatibility Features**
- **PyQt Version Detection**: Automatic PyQt5/PyQt6 compatibility
- **Style Adaptation**: Platform-specific visual rendering
- **Event System**: Maintains Qt's event handling architecture
- **Widget Hierarchy**: Proper parent-child relationships

### Error Handling and Edge Cases

#### **Robustness Features**
- **Null Checks**: Comprehensive null pointer protection
- **Exception Handling**: Graceful degradation on errors
- **State Validation**: Ensures consistent internal states
- **Resource Cleanup**: Proper cleanup of event filters and timers

#### **User Experience Safeguards**
- **Double-Click Protection**: Prevents accidental selection changes
- **Focus Management**: Maintains proper focus during interactions
- **Visual Feedback**: Clear indication of selection states
- **Keyboard Navigation**: Intuitive keyboard interaction patterns

### Future Enhancement Possibilities

#### **Potential Improvements**
- **Drag and Drop**: Multi-item reordering capabilities
- **Search/Filter**: Text-based item filtering
- **Grouping**: Hierarchical item organization
- **Custom Rendering**: Enhanced visual customization options
- **Accessibility**: Improved screen reader and keyboard navigation support

This module represents a sophisticated extension of Qt's standard combo box functionality, providing Artisan with a powerful multi-selection interface that maintains native platform appearance while significantly enhancing user interaction capabilities.