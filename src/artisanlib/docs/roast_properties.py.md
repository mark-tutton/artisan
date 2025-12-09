# Artisan Roast Properties Module Documentation

## File: `src/artisanlib/roast_properties.py`

### Overview
This module implements the **comprehensive Roast Properties Dialog** for the Artisan coffee roasting application. At 6,000+ lines, it provides an extensive interface for managing all aspects of roast metadata, weight calculations, energy analysis, inventory management, and roast quality assessment through a sophisticated tabbed interface system.

### Purpose and Architecture
The `roast_properties.py` module serves as the **central roast data management hub** for Artisan, implementing:
- **Roast Metadata Management**: Comprehensive roast information tracking and editing
- **Weight and Volume Calculations**: Sophisticated density and moisture calculations
- **Energy Analysis**: Detailed energy consumption and efficiency metrics
- **Inventory Integration**: Coffee bean and blend management with stock tracking
- **Quality Assessment**: Roast defect tracking and quality metrics
- **Data Export**: Clipboard and file export capabilities

### Key Components

#### **Main Dialog: `editGraphDlg`**
```python
class editGraphDlg(ArtisanResizeablDialog):
    scaleWeightUpdated = pyqtSignal(float)      # Scale weight updates
    connectScaleSignal = pyqtSignal()          # Scale connection requests
    readScaleSignal = pyqtSignal()             # Scale reading requests
```

**Core Features:**
- **Tabbed Interface**: Multiple specialized tabs for different data categories
- **Real-time Updates**: Live data synchronization with main application
- **Scale Integration**: Direct connection to digital scales and weight sensors
- **Data Validation**: Comprehensive input validation and error checking

#### **Volume Calculator: `volumeCalculatorDlg`**
```python
class volumeCalculatorDlg(ArtisanDialog):
    def __init__(self, parent, aw, weightIn, weightOut, weightunit, volumeunit, 
                 inlineedit, outlineedit, tare):
```

**Calculation Features:**
- **Density Calculations**: Automatic density computation from weight/volume
- **Moisture Adjustments**: Moisture content compensation
- **Unit Conversions**: Support for multiple weight and volume units
- **Tare Management**: Automatic tare weight handling

#### **Specialized Combo Boxes**

**`RoastsComboBox`**: Recent roast selection with search functionality
**`StockComboBox`**: Inventory item selection with unit awareness
**`CoffeesComboBox`**: Coffee bean selection from inventory
**`BlendsComboBox`**: Blend selection with component tracking

### Technical Implementation

#### **Scale Integration System**
```python
@pyqtSlot()
def readScale(self):
    # Initiates scale reading process
    # Connects to various scale types (Acaia, BLE, etc.)

@pyqtSlot(float)
def acaia_weight_changed(self, w: float):
    # Handles Acaia scale weight updates
    # Updates UI and calculations in real-time

@pyqtSlot(int)
def acaia_battery_changed(self, b: int):
    # Monitors scale battery status
    # Provides user feedback on scale condition
```

**Scale Features:**
- **Multi-Protocol Support**: Acaia, Bluetooth LE, USB, and serial scales
- **Real-time Monitoring**: Continuous weight updates during roasting
- **Battery Management**: Scale battery level monitoring
- **Connection Management**: Automatic scale detection and connection

#### **Weight Calculation Engine**
```python
@staticmethod
def calc_volume(density: float, weight: float) -> float:
    # Calculates volume from weight and density
    return weight / density if density > 0 else 0.0

def calc_density(self) -> Tuple[float, float]:
    # Calculates density from weight and volume measurements
    # Returns (density_in, density_out) tuple
```

**Calculation Capabilities:**
- **Density Computation**: Automatic density calculation from measurements
- **Moisture Compensation**: Adjusts for moisture content variations
- **Volume Estimation**: Calculates volume from weight and density
- **Loss Calculations**: Tracks weight loss during roasting process

#### **Energy Analysis System**
```python
def initEnergyTab(self):
    # Initializes energy analysis interface
    # Sets up load configurations and protocols

def updateEnergyTab(self):
    # Updates energy calculations and displays
    # Processes energy consumption data

def createEnergyDataTable(self):
    # Creates comprehensive energy data tables
    # Organizes energy consumption by load type
```

**Energy Features:**
- **Load Management**: Multiple energy load configuration
- **Protocol Tracking**: Energy measurement protocols
- **Efficiency Metrics**: Energy consumption analysis
- **CO2 Calculations**: Environmental impact assessment

### Data Management

#### **Roast Metadata System**
```python
def updateTitle(self, prev_coffee_label, prev_blend_label):
    # Updates roast title and labels
    # Manages coffee and blend information

def fillCoffeeData(self, coffee, prev_coffee_label, prev_blend_label):
    # Populates coffee-specific data fields
    # Handles origin, variety, and processing information

def fillBlendData(self, blend, prev_coffee_label, prev_blend_label):
    # Populates blend composition data
    # Manages component ratios and descriptions
```

**Metadata Features:**
- **Origin Tracking**: Coffee origin and farm information
- **Variety Management**: Coffee variety and cultivar data
- **Processing Details**: Processing method and certification
- **Blend Composition**: Multi-component blend management

#### **Inventory Integration**
```python
def populatePlusCoffeeBlendCombos(self, storeIndex=None):
    # Populates coffee and blend selection dropdowns
    # Integrates with Artisan Plus inventory system

def storeSelectionChanged(self, n: int):
    # Handles store selection changes
    # Updates available coffee and blend options

def coffeeSelectionChanged(self, n: int):
    # Handles coffee selection changes
    # Updates blend options and metadata
```

**Inventory Features:**
- **Store Management**: Multiple inventory store support
- **Stock Tracking**: Real-time stock level monitoring
- **Blend Management**: Complex blend composition tracking
- **Cost Analysis**: Inventory cost and pricing management

### Quality Assessment

#### **Roast Defect Tracking**
```python
@pyqtSlot(int)
def roastflagHeavyFCChanged(self, i: int):
    # Tracks heavy first crack defects

@pyqtSlot(int)
def roastflagLowFCChanged(self, i: int):
    # Tracks low first crack defects

@pyqtSlot(int)
def roastflagOilyChanged(self, i: int):
    # Tracks oily bean defects
```

**Quality Metrics:**
- **First Crack Issues**: Heavy, low, or irregular first crack
- **Bean Defects**: Oily, drops, light/dark cuts
- **Moisture Problems**: Excessive or insufficient moisture
- **Density Variations**: Inconsistent bean density

#### **Color Analysis Integration**
```python
@pyqtSlot(bool)
def scanWholeColor(self, _: bool = False):
    # Initiates whole bean color scanning
    # Integrates with color measurement devices

@pyqtSlot(bool)
def scanGroundColor(self, _: bool = False):
    # Initiates ground coffee color scanning
    # Provides roast level assessment
```

**Color Features:**
- **Whole Bean Analysis**: Pre-grinding color assessment
- **Ground Coffee Analysis**: Post-grinding color measurement
- **Roast Level Determination**: Automatic roast level classification
- **Quality Consistency**: Color uniformity assessment

### Data Export and Management

#### **Table Management**
```python
def createDataTable(self):
    # Creates comprehensive data tables
    # Organizes roast data for analysis

def createEventTable(self, force: bool = False):
    # Creates event tracking tables
    # Manages roast event chronology

def saveEventTable(self):
    # Saves event data to persistent storage
    # Maintains roast event history
```

**Table Features:**
- **Data Organization**: Structured data presentation
- **Event Tracking**: Chronological event management
- **Alarm Integration**: Alarm event recording
- **Data Persistence**: Automatic data saving

#### **Export Capabilities**
```python
@pyqtSlot(bool)
def copyDataTabletoClipboard(self, _: bool = False):
    # Exports data table to clipboard
    # Enables data sharing with other applications

@pyqtSlot(bool)
def copyEventTabletoClipboard(self, _: bool = False):
    # Exports event table to clipboard
    # Provides event data for external analysis
```

**Export Features:**
- **Clipboard Export**: Easy data copying to other applications
- **Format Preservation**: Maintains data structure and formatting
- **Selective Export**: Choose specific data for export
- **External Integration**: Seamless data sharing

### User Interface Features

#### **Tab Management**
```python
@pyqtSlot(int)
def tabSwitched(self, i: int):
    # Handles tab switching events
    # Updates UI state and data validation

def setActiveTab(self):
    # Sets the currently active tab
    # Manages tab-specific functionality
```

**Tab Organization:**
- **General Tab**: Basic roast information and metadata
- **Energy Tab**: Energy consumption and efficiency analysis
- **Setup Tab**: Machine configuration and settings
- **Data Tab**: Roast data tables and analysis
- **Events Tab**: Event tracking and management

#### **Input Validation**
```python
@staticmethod
def validateText2Seconds(s: str) -> int:
    # Converts text input to seconds
    # Handles various time formats

@staticmethod
def validateSeconds2Text(seconds: float) -> str:
    # Converts seconds to formatted text
    # Provides human-readable time display

def validatePctText(self, s: str) -> str:
    # Validates percentage input
    # Ensures proper percentage formatting
```

**Validation Features:**
- **Format Checking**: Ensures proper data format
- **Range Validation**: Validates data within acceptable ranges
- **Type Conversion**: Automatic data type conversion
- **Error Prevention**: Prevents invalid data entry

### Integration Points

#### **Main Application Integration**
```python
def __init__(self, parent: QWidget, aw: 'ApplicationWindow', activeTab: int = 0):
    # Integrates with main application window
    # Accesses global application state and settings
```

**Integration Features:**
- **Application Context**: Access to main application state
- **Settings Management**: Global configuration access
- **Plugin Integration**: Plugin system integration
- **Data Synchronization**: Real-time data updates

#### **Plugin System Integration**
```python
def update_inventory_combo(self, beans):
    # Updates inventory from plugin data
    # Integrates with inventory management plugins
```

**Plugin Features:**
- **Inventory Plugins**: Coffee and blend management
- **Scale Plugins**: Weight measurement integration
- **Color Plugins**: Color analysis integration
- **Export Plugins**: Data export functionality

### Performance Characteristics

#### **Efficiency Features**
- **Lazy Loading**: Data loaded only when needed
- **Caching**: Frequently accessed data cached
- **Batch Updates**: Multiple updates processed together
- **Memory Management**: Efficient memory usage

#### **Scalability Considerations**
- **Large Datasets**: Handles extensive roast data
- **Multiple Roasts**: Manages multiple roast profiles
- **Real-time Updates**: Efficient real-time data processing
- **Resource Management**: Optimized resource usage

This module represents the comprehensive data management backbone of Artisan, providing professional roasters with sophisticated tools for tracking, analyzing, and managing every aspect of their roasting process from bean selection to final quality assessment.