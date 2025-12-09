# Artisan Autosave Dialog Module Documentation

## File: `src/artisanlib/autosave.py`

### Overview
This module implements the **Autosave Configuration Dialog** for the Artisan coffee roasting application. It provides a comprehensive user interface for configuring automatic file saving behavior, including multiple file format support, path management, and external server upload capabilities.

### Purpose and Architecture
The `autosave.py` module serves as the **configuration interface** for Artisan's autosave functionality, allowing users to:
- **Configure automatic saving** triggered by keyboard shortcuts
- **Set file naming conventions** with customizable prefixes
- **Manage multiple output formats** (ALOG, PDF, images) simultaneously
- **Configure save paths** for different file types
- **Enable external server uploads** for cloud-based storage

### Core Components

#### **Main Dialog Class: `autosaveDlg`**
- **Inheritance**: Extends `ArtisanDialog` (custom dialog base class)
- **Modal Behavior**: Blocks interaction with parent window during configuration
- **Geometry Persistence**: Remembers dialog size/position across sessions

#### **Key UI Elements**
1. **Autosave Toggle**: Checkbox to enable/disable autosave functionality
2. **File Prefix Configuration**: Text input for custom filename generation
3. **Path Management**: Directory selection for different file types
4. **Format Selection**: Dropdown menus for multiple output formats
5. **Server Upload**: External server configuration for cloud storage

### Configuration Features

#### **1. Basic Autosave Settings**
```python
# Core autosave functionality
self.autocheckbox.setChecked(bool(self.aw.qmc.autosaveflag))
self.prefixEdit.setText(self.aw.qmc.autosaveprefix)
self.pathEdit.setText(self.aw.qmc.autosavepath)
```

#### **2. Multi-Format Support**
The dialog supports **three simultaneous output formats**:
- **Primary Format**: Main autosave format (ALOG + optional image)
- **Secondary Format**: Additional image/PDF output
- **Tertiary Format**: Third image/PDF output

Each format has:
- **Format Selection**: Dropdown for file type (PNG, JPG, PDF Report)
- **Path Configuration**: Separate directory for each format
- **Independent Toggle**: Enable/disable each format separately

#### **3. External Server Integration**
```python
# Server upload configuration
self.uploadToServerCheckbox = QCheckBox('Upload to external server')
self.serverUrlEdit = QLineEdit(getattr(self.aw.qmc, 'autosave_server_url', ''))
self.serverUrlEdit.setPlaceholderText("http://localhost:4000/upload")
```

#### **4. Recent Files Integration**
```python
# Add to recent files list
self.addtorecentfiles = QCheckBox()
self.addtorecentfiles.setChecked(self.aw.qmc.autosaveaddtorecentfilesflag)
```

### Data Flow and State Management

#### **Configuration Loading**
```python
# Load current settings from QMC (Artisan's main configuration)
settings = QSettings()
self.prefixEdit.setText(self.aw.qmc.autosaveprefix)
self.pathEdit.setText(self.aw.qmc.autosavepath)
```

#### **Configuration Saving**
```python
def autoChanged(self) -> None:
    # Update QMC configuration
    self.aw.qmc.autosavepath = self.pathEdit.text()
    self.aw.qmc.autosaveflag = 1 if self.autocheckbox.isChecked() else 0
    self.aw.qmc.autosaveprefix = self.prefixEdit.text()
    
    # Update multiple format settings
    self.aw.qmc.autosaveimage2 = self.autopdfcheckbox2.isChecked()
    self.aw.qmc.autosaveimageformat2 = self.imageTypesComboBox2.currentText()
    
    # Update server upload settings
    self.aw.qmc.autosave_upload_to_server = self.uploadToServerCheckbox.isChecked()
    self.aw.qmc.autosave_server_url = self.serverUrlEdit.text()
```

### UI Layout Architecture

#### **Grid-Based Layout System**
The dialog uses a sophisticated grid layout (`QGridLayout`) to organize controls:

```python
autolayout = QGridLayout()
# Row 0: Autosave toggle + add to recent files
autolayout.addWidget(self.autocheckbox, 0, 0, Qt.AlignmentFlag.AlignRight)
autolayout.addLayout(autochecklabelplus, 0, 1)

# Row 1-3: File prefix configuration with preview
autolayout.addWidget(prefixlabel, 1, 0)
autolayout.addWidget(self.prefixEdit, 1, 1, 1, 2)
autolayout.addWidget(prefixpreviewLabel, 2, 0)
autolayout.addWidget(self.prefixPreview, 2, 1)

# Row 4: Main save path
autolayout.addWidget(pathButton, 4, 0)
autolayout.addWidget(self.pathEdit, 4, 1, 1, 2)

# Row 5-10: Multiple format configurations
autolayout.addWidget(self.autopdfcheckbox, 5, 0, Qt.AlignmentFlag.AlignRight)
autolayout.addWidget(autopdflabel, 5, 1)
autolayout.addWidget(self.imageTypesComboBox, 5, 2)
```

#### **Column Stretching Strategy**
```python
# Column 0: Right-aligned labels and checkboxes (fixed width)
autolayout.setColumnStretch(0, 0)
# Column 1: Main input fields (expandable)
autolayout.setColumnStretch(1, 10)
# Column 2: Secondary controls (fixed width)
autolayout.setColumnStretch(2, 0)
```

### Integration Points

#### **1. Main Application Window (`ApplicationWindow`)**
- **Configuration Access**: Reads/writes to `self.aw.qmc` (Artisan's main configuration)
- **File Operations**: Uses `self.aw.generateFilename()` for filename preview
- **Directory Dialogs**: Leverages `self.aw.ArtisanExistingDirectoryDialog()`
- **Message System**: Sends user feedback via `self.aw.sendmessage()`

#### **2. Help System Integration**
```python
def showautosavehelp(self, _:bool = False) -> None:
    from help import autosave_help
    self.helpdialog = self.aw.showHelpDialog(
        self, self.helpdialog,
        QApplication.translate('Form Caption','Autosave Fields Help'),
        autosave_help.content())
```

#### **3. Settings Persistence**
```python
def closeEvent(self, _:Optional['QCloseEvent'] = None) -> None:
    settings = QSettings()
    # Save window geometry
    settings.setValue('autosaveGeometry', self.saveGeometry())
```

### Error Handling and Validation

#### **QtWebEngine Compatibility**
```python
try:
    if not self.aw.QtWebEngineSupport:
        # Disable "PDF Report" item if QtWebEngine Support is not available
        model = self.imageTypesComboBox.model()
        if model is not None:
            item: Optional[QStandardItem] = cast(QStandardItemModel, model).item(
                self.aw.qmc.autoasaveimageformat_types.index('PDF Report'))
            if item is not None:
                item.setEnabled(False)
except Exception:  # pylint: disable=broad-except
    pass
```

#### **Type Safety and Import Handling**
```python
# PyQt6/PyQt5 compatibility layer
try:
    from PyQt6.QtCore import Qt, pyqtSlot, QSettings
    from PyQt6.QtWidgets import QApplication, QLabel, QPushButton, QDialogButtonBox
except ImportError:
    from PyQt5.QtCore import Qt, pyqtSlot, QSettings  # type: ignore
    from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QDialogButtonBox
```

### Key Methods

#### **`__init__(self, parent, aw)`**
- **Purpose**: Initialize dialog with current configuration
- **Parameters**: 
  - `parent`: Parent widget for modal behavior
  - `aw`: ApplicationWindow instance for configuration access
- **Key Operations**: Load settings, create UI elements, connect signals

#### **`prefixChanged(self)`**
- **Purpose**: Update filename preview in real-time
- **Trigger**: Text changes in prefix input field
- **Output**: Updates preview labels showing generated filenames

#### **`autoChanged(self)`**
- **Purpose**: Save configuration changes and close dialog
- **Operations**: Update QMC settings, send user feedback, close dialog

#### **`getpath(self, _)` and `getalsopath(self, _)`**
- **Purpose**: Open directory selection dialogs
- **Integration**: Uses Artisan's custom directory dialog system

### Technical Implementation Details

#### **Signal-Slot Architecture**
```python
# Connect UI elements to handlers
self.prefixEdit.textChanged.connect(self.prefixChanged)
self.autocheckbox.setChecked(bool(self.aw.qmc.autosaveflag))
self.dialogbuttons.accepted.connect(self.autoChanged)
```

#### **Dynamic UI Updates**
```python
# Real-time filename preview
def prefixChanged(self) -> None:
    preview = self.aw.generateFilename(self.prefixEdit.text(), previewmode=2)
    self.prefixPreview.setText(preview)
    previewrecording = self.aw.generateFilename(self.prefixEdit.text(), previewmode=1)
    # Show different preview for recording vs. normal mode
```

#### **Configuration Inheritance**
```python
# Fallback to primary settings for secondary formats
self.imageTypesComboBox2.setCurrentIndex(
    self.aw.qmc.autoasaveimageformat_types.index(
        getattr(self.aw.qmc, 'autosaveimageformat2', self.aw.qmc.autosaveimageformat)))
```

### Usage Patterns

#### **1. Configuration Workflow**
1. User opens autosave dialog
2. Dialog loads current settings from QMC
3. User modifies configuration
4. Real-time preview updates show filename generation
5. User accepts changes, configuration saves to QMC
6. Dialog closes, settings take effect immediately

#### **2. Multi-Format Scenarios**
- **Basic**: ALOG file only
- **Standard**: ALOG + one image format
- **Advanced**: ALOG + multiple image formats + external upload
- **Cloud**: ALOG + images + server upload

#### **3. Integration with Main Application**
- **Keyboard Shortcuts**: `[a]` key triggers autosave
- **File Management**: Integrates with Artisan's file system
- **Recent Files**: Optional integration with main application's recent files list
- **Help System**: Context-sensitive help integration

### Performance Considerations

#### **UI Responsiveness**
- **Real-time Updates**: Filename preview updates on every keystroke
- **Modal Behavior**: Prevents UI blocking during configuration
- **Geometry Persistence**: Fast dialog restoration on subsequent opens

#### **Memory Management**
- **Widget Cleanup**: Proper signal disconnection in closeEvent
- **Help Dialog Management**: Reuses help dialog instances
- **Settings Caching**: Efficient QSettings access

### Security and Validation

#### **Input Validation**
- **Path Validation**: Uses Artisan's directory dialog for safe path selection
- **URL Validation**: Server URL input with placeholder guidance
- **File Extension**: Dropdown-based format selection prevents invalid extensions

#### **Configuration Safety**
- **Default Values**: Fallback to safe defaults for missing settings
- **Type Safety**: Strong typing with TYPE_CHECKING support
- **Exception Handling**: Graceful degradation for missing QtWebEngine support

### Future Enhancement Considerations

#### **Extensibility Points**
- **Additional Formats**: Easy to add more output formats
- **Server Protocols**: Expandable server upload capabilities
- **Custom Validators**: Pluggable validation for paths and URLs
- **Template System**: Advanced filename generation patterns

#### **Integration Opportunities**
- **Plugin System**: Could integrate with Artisan's plugin architecture
- **Cloud Services**: Expand external server capabilities
- **Automation**: Integration with scheduling and automation systems

This module represents a sophisticated configuration management system that balances user experience with technical complexity, providing a robust foundation for Artisan's autosave functionality while maintaining extensibility for future enhancements.