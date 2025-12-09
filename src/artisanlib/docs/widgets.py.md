# Artisan Custom Widgets Module Documentation

## File: `src/artisanlib/widgets.py`

### Overview
This module implements the **comprehensive custom widget library** for the Artisan coffee roasting application. At 595 lines, it provides a sophisticated collection of enhanced Qt widgets, specialized UI components, and custom behavior implementations that extend Qt's standard widget functionality with Artisan-specific features.

### Purpose and Architecture
The `widgets.py` module serves as the **custom UI component foundation** for Artisan, implementing:
- **Enhanced Qt Widgets**: Improved versions of standard Qt components with better behavior
- **Specialized Input Controls**: Custom combo boxes, spin boxes, and text editors
- **Interactive Elements**: Clickable labels, animated buttons, and event-driven components
- **Table Management**: Advanced table widgets with custom sorting and navigation
- **Visual Enhancements**: Custom sliders, splitter handles, and animated components

### Key Components

#### 1. **Enhanced Input Widgets**

##### `MyQComboBox`
- **Purpose**: Enhanced combo box with improved focus handling and size adjustment
- **Features**: 
  - Strong focus policy for better keyboard navigation
  - Automatic size adjustment to content
  - Wheel event handling only when focused
- **Use Cases**: Dropdown selections throughout the application

##### `MyContentLimitedQComboBox`
- **Purpose**: Content-limited combo box with scrollbar support
- **Features**:
  - Maximum 20 visible items to prevent UI overflow
  - Vertical scrollbar for large datasets
  - Qt-native styling preservation
- **Use Cases**: Large dataset selections (coffee varieties, machine types, etc.)

##### `MyQDoubleSpinBox`
- **Purpose**: Enhanced double spin box with improved user experience
- **Features**:
  - Strong focus policy
  - C locale for consistent decimal formatting
  - Fixed double-click behavior (prevents infinite value changes)
  - Wheel event handling only when focused
- **Use Cases**: Temperature, weight, and time input fields

#### 2. **Advanced Table Widgets**

##### `MyQTableWidget`
- **Purpose**: Enhanced table widget with custom navigation and event filtering
- **Features**:
  - Custom cursor navigation using Tab key
  - Event filtering for keyboard shortcuts
  - Left/Right arrow key navigation between cells
- **Use Cases**: Roast data tables, event logs, configuration grids

##### `MyTableWidgetItem*` Classes
- **Purpose**: Specialized table items with custom sorting behavior
- **Types**:
  - `MyTableWidgetItemQLineEdit`: Text-based sorting with time recognition
  - `MyTableWidgetItemQTime`: Time-based sorting
  - `MyTableWidgetItemNumber`: Numeric sorting
  - `MyTableWidgetItemQCheckBox`: Boolean sorting
  - `MyTableWidgetItemQComboBox`: Text-based sorting
- **Features**: Custom comparison logic for proper data sorting

#### 3. **Interactive UI Components**

##### `ClickableQLabel`
- **Purpose**: Label that emits click signals for user interaction
- **Features**:
  - Left and right click detection
  - General click signal for any button press
- **Use Cases**: Interactive help text, clickable status indicators

##### `ClickableQGroupBox`
- **Purpose**: Group box with click event handling
- **Features**: Same click detection as ClickableQLabel
- **Use Cases**: Collapsible sections, interactive grouping

##### `ClickableTextEdit` & `ClickableQLineEdit`
- **Purpose**: Text input widgets with enhanced event handling
- **Features**:
  - Text change tracking
  - Focus event signals
  - Control+click detection
  - Editing finished signals
- **Use Cases**: Roast notes, configuration values, user input fields

#### 4. **Specialized Button System**

##### `EventPushButton` Hierarchy
- **Base Class**: `EventPushButton`
  - **Purpose**: Foundation for all event-related buttons
  - **Features**: 
    - Custom styling with gradients
    - Selection state management
    - Hover effects and cursor changes
    - Focus policy disabled for better UX

- **Major Events**: `MajorEventPushButton`
  - **Purpose**: Primary roasting events (Charge, FC Start, etc.)
  - **Color**: Blue (#147bb3)

- **Minor Events**: `MinorEventPushButton`
  - **Purpose**: Secondary roasting events
  - **Color**: Light blue (#4c97c3)

- **Auxiliary Events**: `AuxEventPushButton`
  - **Purpose**: Additional/optional events
  - **Color**: Gray (#bdbdbd)

##### `AnimatedMajorEventPushButton`
- **Purpose**: Major event buttons with continuous animation
- **Features**:
  - Continuous color animation (1.2 second loop)
  - Different animation for selected state
  - Smooth easing curves for professional appearance
  - Automatic animation management

#### 5. **Custom Slider and Splitter**

##### `SliderUnclickable`
- **Purpose**: Slider that only responds to direct slider bar interaction
- **Features**:
  - Ignores clicks on slider background
  - Focus event signals
  - Better user experience for precise control
- **Use Cases**: Temperature settings, time adjustments

##### `Splitter` & `SplitterHandle`
- **Purpose**: Custom splitter with enhanced visual feedback
- **Features**:
  - Custom handle width (10px)
  - Hover effects with color changes
  - Dark/light mode support
  - Visual indicators for drag handles
- **Use Cases**: Resizable panels, adjustable layouts

#### 6. **Utility Components**

##### `MyQLabel`
- **Purpose**: Auto-sizing label with dynamic font adjustment
- **Features**:
  - Automatic font size adjustment to fit container
  - Minimum size constraints
  - Responsive to container resizing
- **Use Cases**: Dynamic text display, status messages

##### `MyQLCDNumber`
- **Purpose**: LCD display with click event support
- **Features**:
  - Left/right click detection
  - Double-click support
  - General click signals
- **Use Cases**: Temperature displays, timer displays, status indicators

##### `wait_cursor` Context Manager
- **Purpose**: Temporary cursor change during long operations
- **Features**:
  - Automatic cursor restoration
  - Busy cursor during operation
  - Exception-safe cursor management
- **Use Cases**: File operations, data processing, network operations

### Technical Implementation Details

#### **Cross-Platform Compatibility**
- **PyQt5/PyQt6 Support**: Automatic import fallback for different Qt versions
- **Type Hints**: Comprehensive type annotations for better IDE support
- **Error Handling**: Robust exception handling throughout all components

#### **Performance Optimizations**
- **Memory Management**: Use of `__slots__` for table items to reduce memory usage
- **Event Filtering**: Efficient event handling with minimal overhead
- **Animation Management**: Optimized property animations for smooth performance

#### **Accessibility Features**
- **Keyboard Navigation**: Enhanced keyboard support for all interactive elements
- **Focus Management**: Proper focus policies and visual feedback
- **Screen Reader Support**: Meaningful signals and properties

### Integration Points

#### **Main Application**
- Used throughout the main application window for all UI components
- Integrated with the event system for roasting workflow management
- Connected to the settings system for persistent configurations

#### **Plugin System**
- Provides base classes for plugin UI components
- Enables consistent look and feel across all plugins
- Supports plugin-specific customizations

#### **Configuration Dialogs**
- Forms the foundation for all configuration interfaces
- Provides consistent behavior across different settings panels
- Enables advanced user interaction patterns

### Best Practices and Usage

#### **Widget Selection Guidelines**
- **Standard Input**: Use enhanced Qt widgets for basic input needs
- **Complex Tables**: Use `MyQTableWidget` for data-heavy interfaces
- **Event Buttons**: Use appropriate event button hierarchy for roasting events
- **Interactive Elements**: Use clickable components for user engagement

#### **Performance Considerations**
- **Animation Management**: Start/stop animations appropriately to conserve resources
- **Event Filtering**: Use event filters sparingly to maintain responsiveness
- **Memory Usage**: Leverage `__slots__` for frequently created objects

#### **Accessibility Compliance**
- **Keyboard Navigation**: Ensure all interactive elements are keyboard accessible
- **Visual Feedback**: Provide clear visual indicators for all states
- **Signal Naming**: Use descriptive signal names for better debugging

### Future Enhancements

#### **Planned Improvements**
- **Touch Support**: Enhanced touch interaction for tablet devices
- **High DPI**: Better support for high-resolution displays
- **Dark Mode**: Enhanced dark mode support throughout all components
- **Animation Framework**: More sophisticated animation system for complex interactions

#### **Extensibility**
- **Plugin Widgets**: Framework for third-party custom widgets
- **Theme System**: Enhanced theming capabilities
- **Custom Behaviors**: More flexible behavior customization options

This module represents the foundation of Artisan's user interface, providing a robust, accessible, and visually appealing foundation for all user interactions while maintaining high performance and cross-platform compatibility.