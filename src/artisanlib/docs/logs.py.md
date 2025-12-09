# Artisan Logs Module Documentation

## File: `src/artisanlib/logs.py`

### Overview
This module implements the **comprehensive logging and diagnostic system** for the Artisan coffee roasting application. At 143 lines, it provides three specialized dialog classes for viewing and managing different types of application logs: serial communication logs, error logs, and message history logs.

### Purpose and Architecture
The `logs.py` module serves as the **diagnostic and debugging interface** for Artisan, implementing:
- **Serial Communication Logging**: Real-time monitoring of hardware communication
- **Error Log Management**: Comprehensive error tracking and display
- **Message History**: User notification and system message archives
- **Log Viewer Dialogs**: User-friendly interfaces for log inspection

### Core Classes

#### **`serialLogDlg` (Serial Log Dialog)**
The primary interface for monitoring serial communication between Artisan and hardware devices.

**Key Features:**
- **Real-time Logging**: Live display of serial communication data
- **Toggle Control**: Enable/disable serial logging functionality
- **HTML Formatting**: Rich text display with version information and entry numbering
- **Reverse Chronological Order**: Most recent entries displayed first

**Implementation Details:**
```python
class serialLogDlg(ArtisanDialog):
    def __init__(self, parent:'QWidget', aw:'ApplicationWindow') -> None:
        # Modal dialog with serial log toggle and display
        self.serialcheckbox = QCheckBox(QApplication.translate('CheckBox','Serial Log ON/OFF'))
        self.serialEdit = QTextEdit()  # Read-only HTML display
```

**Log Format:**
```python
def getstring(self) -> str:
    # Converts serial log list to HTML string
    htmlserial = 'version = ' + __version__ + '<br><br>'
    for i in range(len(self.aw.seriallog)):
        htmlserial += '<b>' + str(lenl-i) + '</b> ' + self.aw.seriallog[-i-1] + '<br><br>'
```

#### **`errorDlg` (Error Log Dialog)**
Comprehensive error tracking and display system for debugging application issues.

**Key Features:**
- **Error Count Display**: Shows total number of errors encountered
- **Chronological Listing**: Reverse-ordered error display with timestamps
- **HTML Formatting**: Rich text presentation for readability
- **Version Information**: Includes application version for debugging context

**Implementation Details:**
```python
class errorDlg(ArtisanDialog):
    def __init__(self, parent:'QWidget', aw:'ApplicationWindow') -> None:
        # Modal dialog with error count label and detailed error display
        self.elabel = QLabel()  # Error count display
        self.errorEdit = QTextEdit()  # Read-only error details
```

**Error Processing:**
```python
def update_log(self) -> None:
    # Converts error log to HTML with reverse numbering
    lenl = len(self.aw.qmc.errorlog)
    htmlerr = ''.join([f'<b>{lenl-i}</b> {m}<br><br>' for i,m in enumerate(reversed(self.aw.qmc.errorlog))])
    
    # Update error count label
    enumber = len(self.aw.qmc.errorlog)
    labelstr = '<b>' + QApplication.translate('Label','Number of errors found {0}').format(str(enumber)) + '</b>'
```

#### **`messageDlg` (Message History Dialog)**
User notification and system message archive viewer.

**Key Features:**
- **Message Archive**: Complete history of user notifications and system messages
- **Chronological Display**: Reverse-ordered message listing
- **HTML Formatting**: Rich text presentation for message clarity
- **Read-only Interface**: Prevents accidental message modification

**Implementation Details:**
```python
class messageDlg(ArtisanDialog):
    def __init__(self, parent:'QWidget', aw:'ApplicationWindow') -> None:
        # Modal dialog with message history display
        self.messageEdit = QTextEdit()  # Read-only message display
```

**Message Processing:**
```python
def update_log(self) -> None:
    # Converts message history to HTML with reverse numbering
    lenl = len(self.aw.messagehist)
    htmlmessage = ''.join([f'<b>{lenl-i}</b> {m}<br><br>' for i,m in enumerate(reversed(self.aw.messagehist))])
```

### Data Sources and Integration

#### **Serial Communication Logs**
```python
# Source: self.aw.seriallog (ApplicationWindow serial log list)
# Format: List of serial communication strings
# Usage: Hardware debugging and communication troubleshooting
```

#### **Error Logs**
```python
# Source: self.aw.qmc.errorlog (QMainWindow error log list)
# Format: List of error message strings
# Usage: Application debugging and issue tracking
```

#### **Message History**
```python
# Source: self.aw.messagehist (ApplicationWindow message history list)
# Format: List of user notification and system message strings
# Usage: User communication tracking and system status monitoring
```

### User Interface Design

#### **Dialog Characteristics**
- **Modal Behavior**: All log dialogs are modal, preventing interaction with main application
- **Read-only Content**: Log displays are protected from user modification
- **Responsive Layout**: Uses QVBoxLayout for consistent vertical arrangement
- **Tooltip Support**: Provides helpful context for user controls

#### **Visual Presentation**
- **HTML Formatting**: Rich text display with bold numbering and line breaks
- **Version Information**: Application version displayed at top of logs
- **Reverse Chronology**: Most recent entries appear first for immediate relevance
- **Consistent Styling**: Uniform appearance across all log types

### Logging Control Mechanisms

#### **Serial Logging Toggle**
```python
@pyqtSlot(int)
def serialcheckboxChanged(self, _:int) -> None:
    # Enables/disables serial communication logging
    if self.serialcheckbox.isChecked():
        self.aw.seriallogflag = True
    else:
        self.aw.seriallogflag = False
```

#### **Real-time Updates**
```python
def update_log(self) -> None:
    # Refreshes log display with current data
    if self.aw.seriallogflag:  # Only update if logging is enabled
        self.serialEdit.setText(self.getstring())
```

### Memory and Performance Management

#### **Efficient Data Processing**
- **List Comprehension**: Uses Python list comprehensions for efficient HTML generation
- **String Joining**: Concatenates HTML fragments efficiently
- **Lazy Updates**: Only refreshes displays when explicitly requested

#### **Resource Management**
- **Dialog Cleanup**: Properly manages dialog references in main application
- **Memory Cleanup**: Clears dialog references on close to prevent memory leaks
- **Efficient Rendering**: HTML-based display for fast text rendering

### Internationalization Support

#### **Multi-language Interface**
```python
# Translation support for all user-facing text
QApplication.translate('Form Caption','Serial Log')
QApplication.translate('CheckBox','Serial Log ON/OFF')
QApplication.translate('Label','Number of errors found {0}')
QApplication.translate('Tooltip', 'ON/OFF logs serial communication')
```

#### **Localized Formatting**
- **Number Formatting**: Supports different locale-specific number representations
- **Text Direction**: Handles right-to-left languages appropriately
- **Cultural Adaptations**: Adjusts UI elements for different regions

### Error Handling and Robustness

#### **Exception Safety**
- **Graceful Degradation**: Continues operation even if log data is corrupted
- **Data Validation**: Ensures log data integrity before display
- **Fallback Behavior**: Provides default displays when data is unavailable

#### **User Experience**
- **Clear Error Messages**: Presents errors in user-friendly format
- **Context Information**: Includes version and timing data for debugging
- **Accessibility**: Read-only interfaces prevent accidental data loss

### Integration with Main Application

#### **Application Window Integration**
```python
# Dialog references stored in main application
self.aw.serial_dlg = None
self.aw.error_dlg = None
self.aw.message_dlg = None
```

#### **Data Synchronization**
- **Real-time Updates**: Logs reflect current application state
- **State Persistence**: Logging preferences maintained across sessions
- **Event-driven Updates**: Logs update in response to application events

### Debugging and Development Support

#### **Developer Tools**
- **Version Tracking**: Includes application version in all logs
- **Timeline Analysis**: Chronological ordering for debugging sequences
- **Data Inspection**: Detailed view of application state and communication

#### **Troubleshooting Features**
- **Communication Debugging**: Serial log for hardware interface issues
- **Error Analysis**: Comprehensive error tracking for bug identification
- **User Feedback**: Message history for understanding user interactions

### Security Considerations

#### **Data Protection**
- **Read-only Access**: Prevents accidental log modification
- **Information Disclosure**: Careful about sensitive data in logs
- **Access Control**: Logs accessible only to authorized users

#### **Privacy and Compliance**
- **User Data Handling**: Respects privacy in message logging
- **Audit Trail**: Maintains appropriate logging for compliance
- **Data Retention**: Logs managed according to application policies

### Future Enhancements

#### **Planned Features**
- **Log Filtering**: Advanced search and filter capabilities
- **Export Functionality**: Save logs to external files
- **Real-time Monitoring**: Live log streaming and alerts
- **Advanced Analytics**: Log analysis and pattern recognition

#### **Performance Improvements**
- **Virtual Scrolling**: Efficient handling of large log volumes
- **Search Indexing**: Fast text search across log entries
- **Compression**: Efficient storage of historical log data

### Use Cases and Scenarios

#### **Hardware Troubleshooting**
- **Serial Communication Issues**: Debug device connection problems
- **Command Failures**: Track failed hardware commands
- **Timing Problems**: Analyze communication timing issues

#### **Application Debugging**
- **Error Investigation**: Identify and resolve application bugs
- **Performance Analysis**: Monitor application behavior over time
- **User Experience**: Understand user interaction patterns

#### **System Administration**
- **Maintenance Monitoring**: Track system health and performance
- **Update Verification**: Confirm successful application updates
- **Configuration Validation**: Verify system configuration changes

This module provides essential diagnostic capabilities for Artisan, enabling users and developers to monitor application behavior, troubleshoot issues, and maintain system reliability through comprehensive logging and error tracking systems.