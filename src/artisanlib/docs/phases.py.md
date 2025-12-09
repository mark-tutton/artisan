# Artisan Phases Dialog Module Documentation

## File: `src/artisanlib/phases.py`

### Overview
This module implements the **Roast Phases Configuration Dialog** for the Artisan coffee roasting application. At 367 lines, it provides a comprehensive interface for configuring roasting phase boundaries, automatic phase detection, and phase-related display settings through an intuitive grid-based layout.

### Purpose and Architecture
The `phases.py` module serves as the **roasting phase management system** for Artisan, implementing:
- **Phase Boundary Configuration**: Temperature thresholds for drying, maillard, and finishing phases
- **Automatic Phase Detection**: Event-based phase boundary adjustment
- **Phase Display Controls**: LCD modes, watermarks, and visual indicators
- **Background Profile Integration**: Phase synchronization with reference profiles

### Core Components

#### **Main Dialog Class: `phasesGraphDlg`**
- **Inheritance**: Extends `ArtisanDialog` for consistent UI behavior
- **Modal Operation**: Ensures user focus during configuration
- **State Management**: Preserves original values for cancellation support

#### **Phase Configuration System**
```python
# Phase boundaries with automatic linking
self.startdry → self.enddry → self.startmid → self.endmid → self.startfinish → self.endfinish
```

#### **Temperature Unit Support**
- **Fahrenheit Mode**: All inputs display with °F suffix
- **Celsius Mode**: All inputs display with °C suffix
- **Dynamic Range**: 0-1000° for both temperature scales

### Key Features

#### **1. Phase Boundary Management**
- **Drying Phase**: Start and end temperature configuration
- **Maillard Phase**: Middle phase temperature boundaries
- **Finishing Phase**: Final phase temperature settings
- **Automatic Linking**: Adjacent phase boundaries automatically sync

#### **2. Automatic Phase Detection**
- **Auto Adjusted Mode**: Phases automatically adjust based on roast events
- **Event Integration**: DryEnd and FCs events automatically update phase boundaries
- **Background Profile Sync**: Phase boundaries can be derived from reference profiles

#### **3. Display and Visualization**
- **Watermarks**: Visual phase indicators on the main chart
- **Phase LCDs**: Real-time phase information display
- **LCD Modes**: Time, percentage, or temperature-based phase information

#### **4. Advanced Controls**
- **From Background**: Use background profile events for phase boundaries
- **Auto DRY**: Automatic drying phase detection
- **Auto FCs**: Automatic first crack detection and phase adjustment

### User Interface Architecture

#### **Layout Structure**
```
┌─────────────────────────────────────────────────────────────┐
│                    Roast Phases                            │
├─────────────────────────────────────────────────────────────┤
│         min     max    Phases    Phases                    │
│                    LCDs Mode    LCDs All                   │
├─────────────────────────────────────────────────────────────┤
│ Drying    [start]  [end]    [Mode]     [ ]                │
│ Maillard  [start]  [end]    [Mode]                        │
│ Finishing [start]  [end]    [Mode]     [✓]                │
├─────────────────────────────────────────────────────────────┤
│ [✓] Auto Adjusted  [✓] From Background                     │
│ [✓] Auto DRY       [✓] Auto FCs                           │
│ [✓] Watermarks     [✓] Phases LCDs                        │
├─────────────────────────────────────────────────────────────┤
│                    [Restore Defaults]  [Cancel] [OK]      │
└─────────────────────────────────────────────────────────────┘
```

#### **Input Controls**
- **SpinBoxes**: Numeric input for temperature values with unit suffixes
- **CheckBoxes**: Boolean toggles for feature activation
- **ComboBoxes**: Mode selection for LCD displays
- **Button Groups**: Standard dialog buttons with custom actions

### Data Flow and State Management

#### **Initialization Process**
1. **State Capture**: Store original phase values and flags
2. **UI Population**: Set current values from application state
3. **Event Binding**: Connect UI controls to state change handlers
4. **Phase Synchronization**: Apply automatic phase adjustments

#### **State Change Handling**
```python
# Example: Auto adjustment flag change
@pyqtSlot(int)
def pushbuttonflagChanged(self, i:int) -> None:
    if i:
        self.aw.qmc.phasesbuttonflag = True
        self.events2phases()  # Apply event-based adjustments
        self.getphases()      # Update UI
        self.aw.qmc.redraw()  # Refresh display
```

#### **Settings Persistence**
- **QSettings Integration**: Automatic saving of phase boundaries
- **Position Memory**: Dialog position is preserved between sessions
- **State Validation**: Only valid configurations are saved

### Integration Points

#### **Main Application Integration**
- **Phase Data**: Direct access to `aw.qmc.phases` array
- **Event System**: Integration with roast event detection
- **Background Profiles**: Synchronization with reference profiles
- **Display Updates**: Triggers chart redraws and LCD updates

#### **Plugin System Compatibility**
- **Dialog Framework**: Extends `ArtisanDialog` for consistent behavior
- **Translation Support**: Full internationalization support
- **Settings Management**: Integrated with application settings system

### Error Handling and Validation

#### **Input Validation**
- **Temperature Ranges**: 0-1000° range for all phase inputs
- **Phase Consistency**: Automatic boundary linking prevents invalid configurations
- **State Synchronization**: UI state always reflects application state

#### **Error Recovery**
- **Cancel Operation**: Restores all original values
- **Default Restoration**: Provides factory default phase boundaries
- **State Rollback**: Automatic cleanup on dialog rejection

### Performance Considerations

#### **Efficient Updates**
- **Conditional Redraws**: Only redraw when necessary
- **State Caching**: Original values cached for quick restoration
- **Event Optimization**: Minimal UI updates during configuration

#### **Memory Management**
- **Reference Management**: Direct references to application objects
- **Cleanup Handling**: Proper state restoration on dialog closure
- **Resource Efficiency**: Minimal memory footprint for configuration dialogs

### Future Enhancement Opportunities

#### **Potential Improvements**
- **Phase Templates**: Predefined phase configurations for different roast styles
- **Advanced Validation**: Cross-phase boundary validation rules
- **Phase Analytics**: Statistical analysis of phase timing across profiles
- **Custom Phase Types**: User-defined phase categories beyond the standard three

#### **Integration Extensions**
- **Recipe System**: Phase configuration as part of roast recipes
- **Machine Learning**: Automatic phase boundary optimization
- **Cloud Sync**: Phase configurations synchronized across devices

This module represents a critical component of Artisan's roasting workflow, providing users with precise control over phase definitions while maintaining the flexibility to automatically adapt to actual roast events and reference profiles.