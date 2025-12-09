# Artisan Utilities Module Documentation

## File: `src/artisanlib/util.py`

### Overview
This module implements the **comprehensive utility functions library** for the Artisan coffee roasting application. At 835 lines, it provides essential helper functions, data conversion utilities, file path management, color manipulation, and mathematical operations that form the foundation for the entire Artisan application.

### Purpose and Architecture
The `util.py` module serves as the **utility foundation layer** for Artisan, implementing:
- **Data Conversion**: Temperature, weight, volume, and time unit conversions
- **File Path Management**: Cross-platform path handling and data directory management
- **Color Manipulation**: Advanced color processing and gradient generation
- **String Processing**: Text manipulation and formatting utilities
- **Mathematical Operations**: Data interpolation, gap filling, and numerical processing
- **Platform Detection**: Operating system and application state detection

### Key Components

#### **Application Constants**
```python
application_name: Final[str] = 'Artisan'
application_viewer_name: Final[str] = 'ArtisanViewer'
application_organization_name: Final[str] = 'artisan-scope'
application_organization_domain: Final[str] = 'artisan-scope.org'
application_desktop_file_name: Final[str] = 'org.artisan_scope.artisan'
```

**Identity Management:**
- **Application Names**: Primary and viewer application identifiers
- **Organization Details**: Application organization and domain information
- **Desktop Integration**: Desktop file naming for system integration

#### **Delta Label Constants**
```python
deltaLabelPrefix: Final[str] = '<html>&Delta;&thinsp;</html>'
deltaLabelUTF8: Final[str] = 'Delta' if platform.system() == 'Linux' else '\u0394\u2009'
deltaLabelBigPrefix: Final[str] = '<big><b>&Delta;</b></big>&thinsp;<big><b>'
deltaLabelMathPrefix: Final[str] = r'$\Delta\/$'
```

**Label System:**
- **HTML Formatting**: Rich text delta labels for UI components
- **Platform Adaptation**: Different representations for different operating systems
- **Mathematical Notation**: LaTeX-style delta symbols for graphs
- **Typography Support**: Various font weights and sizes

### Platform Detection and Application State

#### **Frozen Application Detection**
```python
def appFrozen() -> bool:
    ib = False
    try:
        platf = str(platform.system())
        if platf == 'Darwin':
            # macOS: sys.frozen set by py2app and pyinstaller
            if getattr(sys, 'frozen', False):
                ib = True
        elif platf == 'Windows':
            ib = hasattr(sys, 'frozen')
        elif platf == 'Linux' and getattr(sys, 'frozen', False):
            ib = True
    except Exception as e:
        _log.exception(e)
    return ib
```

**Detection Features:**
- **macOS Support**: Detects py2app and pyinstaller packaging
- **Windows Support**: Identifies frozen Windows applications
- **Linux Support**: Detects Linux frozen applications
- **Error Handling**: Graceful fallback on detection failures

### Data Conversion Utilities

#### **Temperature Conversion System**
```python
def fromFtoCstrict(Ffloat: float) -> float:
    if Ffloat == -1:
        return Ffloat
    return (Ffloat - 32.0) * (5.0 / 9.0)

def fromCtoF(Cfloat: Optional[float]) -> Optional[float]:
    if Cfloat is None or Cfloat == -1 or numpy.isnan(Cfloat):
        return Cfloat
    return fromCtoFstrict(Cfloat)

def convertTemp(t: float, source_unit: str, target_unit: str) -> float:
    if source_unit in ('', target_unit) or target_unit == '':
        return t
    if source_unit == 'C':
        res = fromCtoF(t)
        if res is None:
            return t
        return res
    res = fromFtoC(t)
    if res is None:
        return t
    return res
```

**Temperature Features:**
- **Unit Conversion**: Fahrenheit to Celsius and vice versa
- **Error Value Handling**: Preserves -1 error values
- **NaN Protection**: Handles Not-a-Number values gracefully
- **Bidirectional Conversion**: Automatic source/target unit detection

#### **Rate of Rise (RoR) Conversion**
```python
def RoRfromCtoFstrict(CRoR: float) -> float:
    if CRoR == -1:
        return CRoR
    return CRoR * 9.0 / 5.0

def convertRoR(r: Optional[float], source_unit: str, target_unit: str) -> Optional[float]:
    if source_unit == target_unit:
        return r
    if source_unit == 'C':
        return RoRfromCtoF(r)
    return RoRfromFtoC(r)
```

**RoR Features:**
- **Temperature Rate Conversion**: Converts temperature change rates
- **Unit Consistency**: Maintains proper units for rate calculations
- **Error Preservation**: Handles error values appropriately
- **Automatic Detection**: Identifies source and target units

#### **Weight and Volume Conversion**
```python
def convertWeight(v: float, i: int, o: int) -> float:
    # i/o: 0:g, 1:Kg, 2:lb (pound), 3:oz (ounce)
    convtable = [
        [1., 0.001, 0.00220462262, 0.035274],      # g
        [1000, 1., 2.205, 35.274],                 # Kg
        [453.591999, 0.45359237, 1., 16.],         # lb
        [28.3495, 0.0283495, 0.0625, 1.]          # oz
    ]
    return v * convtable[i][o]

def convertVolume(v: float, i: int, o: int) -> float:
    # i/o: 0:l (liter), 1:gal (gallons US), 2:qt, 3:pt, 4:cup, 5:cm^3/ml
    convtable = [
        [1., 0.26417205, 1.05668821, 2.11337643, 4.22675284, 1000.],           # liter
        [3.78541181, 1., 4., 8., 16, 3785.4117884],                            # gallon
        [0.94635294, 0.25, 1., 2., 4., 946.352946],                            # quart
        [0.47317647, 0.125, 0.5, 1., 2., 473.176473],                          # pint
        [0.23658823, 0.0625, 0.25, 0.5, 1., 236.5882365],                      # cup
        [0.001, 2.6417205e-4, 1.05668821e-3, 2.11337641e-3, 4.2267528e-3, 1.] # cm^3
    ]
    return v * convtable[i][o]
```

**Conversion Features:**
- **Comprehensive Units**: Supports all common weight and volume units
- **Precise Conversion**: Uses exact conversion factors
- **Bidirectional**: Converts between any two units
- **Table-based**: Efficient lookup-based conversion

### Time and String Processing

#### **Time Format Conversion**
```python
def stringfromseconds(seconds_raw: float, leadingzero: bool = True) -> str:
    seconds = int(math.floor(seconds_raw + 0.5))
    if seconds >= 0:
        d, m = divmod(seconds, 60)
        if leadingzero:
            return f'{d:02d}:{m:02d}'
        return f'{d:d}:{m:02d}'
    negtime = abs(seconds)
    d, m = divmod(negtime, 60)
    if leadingzero:
        return f'-{d:02d}:{m:02d}'
    return f'-{d:d}:{m:02d}'

def stringtoseconds(string: str) -> int:
    timeparts = string.split(':')
    if len(timeparts) != 2:
        return -1
    if timeparts[0][0] != '-':  # positive number
        seconds = int(timeparts[1])
        seconds += int(timeparts[0]) * 60
        return seconds
    seconds = int(timeparts[0]) * 60
    seconds -= int(timeparts[1])
    return seconds  # negative number
```

**Time Features:**
- **MM:SS Format**: Standard time display format
- **Negative Time Support**: Handles negative time values
- **Leading Zero Control**: Optional leading zero padding
- **Input Validation**: Robust parsing of time strings

#### **String Processing Utilities**
```python
def abbrevString(s: str, ll: int) -> str:
    if len(s) > ll:
        return f'{s[:ll-1]}...'
    return s

def comma2dot(s: str) -> str:
    s = s.strip()
    last_dot = s.rfind('.')
    if last_dot > -1:
        if last_dot + 1 == len(s):
            return s.replace(',', '').replace('.', '')
        return s[:last_dot].replace(',', '').replace('.', '') + s[last_dot:].replace(',', '').rstrip('0').rstrip('.')
    last_pos = s.rfind(',')
    if last_pos > -1:
        if last_pos + 1 == len(s):
            return s.replace(',', '').replace('.', '')
        return s[:last_pos].replace(',', '') + '.' + s[last_pos+1:].rstrip('0').rstrip('.')
    return s
```

**String Features:**
- **Abbreviation**: Truncates long strings with ellipsis
- **Decimal Separator**: Converts comma to dot decimal notation
- **Trailing Zero Removal**: Cleans up unnecessary decimal places
- **International Support**: Handles different decimal separator conventions

### Data Processing and Interpolation

#### **Gap Filling Algorithm**
```python
def fill_gaps(ll: Union[Sequence[Union[float, int]], 'npt.NDArray[numpy.floating[Any]]'], 
              interpolate_max: int = 3) -> List[float]:
    res: List[float] = []
    last_val: float = -1
    skip: int = -1
    
    for i, e in enumerate(ll):
        if i >= skip:
            if i == 0 and e == -1 and last_val == -1:  # prefix handling
                s: float = -1
                for ee in ll[:5]:
                    if ee != -1:
                        s = ee
                        break
                res.append(s)
                last_val = s
            elif e == -1 and last_val != -1:  # gap interpolation
                next_val = None
                next_idx = None
                for j in range(i+1, len(ll)):
                    if ll[j] != -1:
                        next_val = ll[j]
                        next_idx = j
                        break
                
                if next_val is None or next_idx is None:
                    res.extend(ll[i:])
                    return res
                
                if interpolate_max is not None and interpolate_max < (next_idx - i):
                    res.extend(ll[i:next_idx])  # gap too big
                else:
                    # interpolate intermediate values
                    step = (next_val - last_val) / (next_idx - i + 1.)
                    for _ in range(next_idx - i):
                        last_val = last_val + step
                        res.append(last_val)
                skip = next_idx
            else:
                res.append(e)
                last_val = e
    
    return res
```

**Interpolation Features:**
- **Gap Detection**: Identifies missing data points (-1 values)
- **Configurable Limits**: Controls maximum gap size for interpolation
- **Linear Interpolation**: Smooth data filling between valid points
- **Prefix Handling**: Special handling for leading missing values

#### **Duplicate Removal**
```python
def replace_duplicates(data: List[float]) -> List[float]:
    lv: float = -1
    data_core: List[float] = []
    
    for v in data:
        if v == lv:
            data_core.append(-1)  # mark duplicates as missing
        else:
            data_core.append(v)
            lv = v
    
    # reconstruct first and last reading
    if len(data) > 0:
        data_core[-1] = data[-1]
    
    return fill_gaps(data_core, interpolate_max=100)
```

**Duplicate Features:**
- **Duplicate Detection**: Identifies consecutive identical values
- **Missing Value Marking**: Converts duplicates to -1 for interpolation
- **Boundary Preservation**: Maintains first and last data points
- **Gap Filling Integration**: Uses interpolation to fill duplicate gaps

### File Path Management

#### **Data Directory Management**
```python
@functools.lru_cache(maxsize=None)
def _getAppDataDirectory(app: 'Artisan') -> Optional[str]:
    # temporarily switch app name to Artisan
    appName = app.applicationName()
    app.setApplicationName(application_name)
    data_dir = QStandardPaths.standardLocations(
        QStandardPaths.StandardLocation.AppLocalDataLocation
    )[0]
    app.setApplicationName(appName)
    
    try:
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        return data_dir
    except Exception:
        return None

def getDataDirectory() -> Optional[str]:
    app = QCoreApplication.instance()
    return _getAppDataDirectory(app)
```

**Directory Features:**
- **Cross-platform Paths**: Uses Qt standard paths for consistency
- **Automatic Creation**: Creates directories if they don't exist
- **Caching**: LRU cache for performance optimization
- **Error Handling**: Graceful fallback on directory creation failures

#### **Resource Path Management**
```python
@functools.lru_cache(maxsize=None)
def getResourcePath() -> str:
    platf = platform.system()
    if platf == 'Darwin':  # macOS
        if appFrozen():
            return QCoreApplication.applicationDirPath() + '/../Resources/'
        return os.path.dirname(os.path.realpath(__file__)) + '/../includes/'
    elif platf == 'Linux':
        if appFrozen():
            return QCoreApplication.applicationDirPath() + '/'
        return os.path.dirname(os.path.realpath(__file__)) + '/../includes/'
    elif platf == 'Windows':
        if appFrozen():
            return os.path.dirname(sys.executable) + '\\'
        return os.path.dirname(os.path.realpath(__file__)) + '\\..\\includes\\'
    return QCoreApplication.applicationDirPath() + '/'
```

**Resource Features:**
- **Platform-specific Paths**: Different paths for different operating systems
- **Frozen App Support**: Handles packaged vs. source code paths
- **Resource Location**: Locates includes and resource directories
- **Path Normalization**: Ensures proper path separators

### Color Manipulation System

#### **Color Format Conversion**
```python
def argb_colorname2rgba_colorname(c: str) -> str:
    if len(c) == 9 and c[0] == '#':
        return f'#{c[3:9]}{c[1:3]}'  # ARGB to RGBA
    return c

def rgba_colorname2argb_colorname(c: str) -> str:
    if len(c) == 9 and c[0] == '#':
        return f'#{c[7:9]}{c[1:7]}'  # RGBA to ARGB
    return c
```

**Color Features:**
- **Format Conversion**: Converts between ARGB and RGBA formats
- **Hex Support**: Handles 9-character hex color strings
- **Alpha Channel**: Preserves transparency information
- **Cross-platform**: Supports different color format requirements

#### **Color Modification**
```python
def toGrey(color: str) -> str:
    h, _s, l, a = QColor(rgba_colorname2argb_colorname(color)).getHslF()
    if h is not None and l is not None and a is not None:
        gray = QColor.fromHslF(h, 0, (1-l)/1.7+l, a)  # saturation set to 0
    else:
        gray = QColor.fromHslF(0.5, 0, 0.5, 1.0)
    
    if len(color) == 9:
        return gray.name(QColor.NameFormat.HexArgb)
    return gray.name(QColor.NameFormat.HexRgb)

def toDim(color: str) -> str:
    h, s, l, a = QColor(rgba_colorname2argb_colorname(color)).getHslF()
    if h is not None and s is not None and l is not None and a is not None:
        gray = QColor.fromHslF(h, s/4, (1-l)/1.7+l, a)  # reduced saturation
    else:
        gray = QColor.fromHslF(0.5, 0, 0.5, 1.0)
    
    if len(color) == 9:
        return gray.name(QColor.NameFormat.HexArgb)
    return gray.name(QColor.NameFormat.HexRgb)
```

**Modification Features:**
- **Grayscale Conversion**: Converts colors to grayscale
- **Dimming**: Reduces color saturation and brightness
- **HSL Manipulation**: Uses HSL color space for modifications
- **Alpha Preservation**: Maintains transparency information

#### **Gradient Generation**
```python
@functools.lru_cache(maxsize=None)
def createGradient(rgb: Union[QColor, str], tint_factor: float = 0.1, 
                   shade_factor: float = 0.1, reverse: bool = False) -> str:
    light_grad, dark_grad = createRGBGradient(rgb, tint_factor, shade_factor)
    if reverse:
        return f'QLinearGradient(x1:0,y1:0,x2:0,y2:1,stop:0 {dark_grad}, stop:1 {light_grad})'
    return f'QLinearGradient(x1:0,y1:0,x2:0,y2:1,stop:0 {light_grad}, stop:1 {dark_grad})'

def createRGBGradient(rgb: Union[QColor, str], tint_factor: float = 0.3, 
                      shade_factor: float = 0.3) -> Tuple[str, str]:
    try:
        rgb_tuple: Tuple[float, float, float]
        if isinstance(rgb, QColor):
            r, g, b, _ = rgb.getRgbF()
            if r is not None and g is not None and b is not None:
                rgb_tuple = (r, g, b)
            else:
                rgb_tuple = (0.5, 0.5, 0.5)
        elif rgb[0:1] == '#':  # hex input
            rgb_tuple = (float(int(rgb[1:3], 16)/255), 
                        float(int(rgb[3:5], 16)/255), 
                        float(int(rgb[5:7], 16)/255))
        else:  # color name
            rgb_tuple = colors.hex2color(colors.cnames[rgb])
        
        # Create darker and lighter variants
        r, g, b = tuple(int(255 * (x * (1 - shade_factor))) for x in rgb_tuple)
        darker_rgb = f'#{r:02x}{g:02x}{b:02x}'
        r, g, b = tuple(int(255 * (x + (1 - x) * tint_factor)) for x in rgb_tuple)
        lighter_rgb = f'#{r:02x}{g:02x}{b:02x}'
        
    except Exception as e:
        _log.exception(e)
        lighter_rgb = darker_rgb = '#000000'
    
    return lighter_rgb, darker_rgb
```

**Gradient Features:**
- **CSS Generation**: Creates Qt CSS gradient strings
- **Tint and Shade**: Generates lighter and darker color variants
- **Multiple Inputs**: Supports QColor, hex strings, and color names
- **Error Handling**: Graceful fallback on color processing failures

### Networking and System Utilities

#### **Network Connectivity Testing**
```python
def isOpen(ip: str, port: int) -> bool:
    import socket
    timeout = 0.3  # timeout in seconds
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(timeout)
            return s.connect_ex((ip, port)) == 0
    except Exception as e:
        _log.info(e)
    return False
```

**Network Features:**
- **Port Testing**: Tests TCP port connectivity
- **Timeout Control**: Configurable connection timeout
- **Error Handling**: Graceful handling of connection failures
- **Resource Management**: Proper socket cleanup

#### **Logging Management**
```python
@functools.lru_cache(maxsize=None)
def getLoggers() -> List[logging.Logger]:
    return [logging.getLogger(name) for name in logging.root.manager.loggerDict if '.' not in name]

def setDeviceDebugLogLevel(state: bool) -> None:
    if state:
        logging.getLogger('pymodbus.logging').setLevel(logging.DEBUG)
        logging.getLogger('pymodbus.client').setLevel(logging.DEBUG)
        _log.info('device debug logging ON')
    else:
        logging.getLogger('pymodbus.logging').setLevel(logging.ERROR)
        _log.info('device debug logging OFF')
```

**Logging Features:**
- **Logger Discovery**: Finds all application loggers
- **Device Debug Control**: Manages device communication logging
- **Level Management**: Controls logging verbosity
- **Performance Optimization**: Cached logger discovery

### Advanced Data Processing

#### **Weight Rendering System**
```python
def render_weight(amount: float, weight_unit_index: int, target_unit_idx: int,
                 right_to_left_lang: bool = False, brief: int = 0, 
                 smart_unit_upgrade: bool = True) -> str:
    w = convertWeight(amount, weight_unit_index, target_unit_idx)
    
    # Smart unit selection based on magnitude
    if w < 1 and target_unit_idx == 1:  # kg -> g for small weights
        w = convertWeight(amount, weight_unit_index, 0)
        target_unit = weight_units[0]
    elif w >= 1000000 and target_unit_idx == 0:  # g -> t for large weights
        w = w / 1000000.0
        target_unit = 't'
    elif w >= 10000 and target_unit_idx == 0:  # g -> kg for medium weights
        w = convertWeight(amount, weight_unit_index, 1)
        target_unit = weight_units[1]
    # ... additional smart unit logic
    
    decimals = 0 if w >= 100 else 1
    if target_unit not in ['g', 'oz']:
        decimals += 2
    if brief > 0:
        decimals = max(0, decimals - brief)
    
    w = float2float(w, decimals)
    return (f'{target_unit.lower()}{w:g}' if right_to_left_lang else f'{w:g}{target_unit.lower()}')
```

**Weight Features:**
- **Smart Unit Selection**: Automatically chooses appropriate units
- **Internationalization**: Supports right-to-left languages
- **Precision Control**: Configurable decimal places
- **Magnitude Awareness**: Adapts units based on weight values

#### **Type Conversion Utilities**
```python
def toInt(x: Optional[Union[int, str, float]]) -> int:
    if x is None:
        return 0
    try:
        return int(round(float(x)))
    except Exception:
        return 0

def toFloat(x: Any) -> float:
    if x is None:
        return 0.
    try:
        return float(x)
    except Exception:
        return 0.

def toBool(x: Any) -> bool:
    if isinstance(x, str):
        x_lower = x.lower()
        if x_lower in {'yes', 'true', 't', '1'}:
            return True
        if x_lower in {'no', 'false', 'f', '0'}:
            return False
        try:
            return bool(eval(x))
        except Exception:
            return False
    return bool(x)
```

**Conversion Features:**
- **Safe Conversion**: Handles conversion errors gracefully
- **Default Values**: Provides sensible defaults for failed conversions
- **String Parsing**: Intelligent boolean string parsing
- **Type Safety**: Ensures consistent return types

This module represents the comprehensive utility foundation of Artisan, providing essential functions for data processing, unit conversion, file management, and system integration that enable the application to work consistently across different platforms and handle diverse data types reliably.