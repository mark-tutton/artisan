# Artisan Notification System Module Documentation

## File: `src/artisanlib/notifications.py`

### Overview
This module implements the **comprehensive notification and system tray management system** for the Artisan coffee roasting application. At 384 lines, it provides a sophisticated interface for managing user notifications, system tray integration, and cross-platform notification delivery through a unified notification manager.

### Purpose and Architecture
The `notifications.py` module serves as the **user communication hub** for Artisan, implementing:
- **Multi-type Notifications**: System, user, and external service notifications
- **System Tray Integration**: Cross-platform system tray icon and menu management
- **Notification Queuing**: Intelligent notification management with aging and cleanup
- **External Service Integration**: Artisan.plus service notification handling
- **User Interaction**: Click handling and notification acknowledgment

### Core Classes and Enums

#### **`NotificationType` (Enumeration)**
Defines the classification system for different notification types:

```python
@unique
class NotificationType(Enum):
    ARTISAN_SYSTEM = 1    # Internal Artisan activity notifications
    ARTISAN_USER = 2      # User-issued notifications via notify() command
    PLUS_SYSTEM = 3       # Artisan.plus system notifications
    PLUS_REMINDER = 4     # Artisan.plus reminder notifications
    PLUS_ADMIN = 5        # Artisan.plus administrative messages
    PLUS_ADVERT = 6       # Artisan.plus advertisement notifications
```

#### **`Notification` (Data Class)**
Represents individual notification instances with comprehensive metadata:

```python
class Notification:
    def __init__(self, title: str, message: str, notification_type: NotificationType, 
                 created: Optional[float] = None, hr_id: Optional[str] = None, 
                 link: Optional[str] = None) -> None:
        self._title: str = title
        self._message: str = message
        self._type: NotificationType = notification_type
        self._created: float = created or time.time()
        self._id: Optional[str] = hr_id
        self._link: Optional[str] = link
```

**Key Properties:**
- **Title**: Notification headline text
- **Message**: Detailed notification content
- **Type**: Classification from NotificationType enum
- **Created**: Timestamp of notification creation
- **ID**: External service identifier (hr_id)
- **Link**: Optional URL for external service notifications

**Smart Title Formatting:**
```python
def formatedTitle(self) -> str:
    seconds_to = time.time() - self._created
    if seconds_to < 24*60*60:
        # Within last 24h: show title only
        return self._title
    elif seconds_to < 7*24*60*60:
        # Within past 7 days: show day name
        dt = QDateTime.fromSecsSinceEpoch(int(round(self._created)))
        day_name = QLocale().standaloneDayName(dt.date().dayOfWeek(), QLocale.FormatType.LongFormat)
        return f'{self._title} ({day_name})'
    else:
        # More than 7 days ago: show short date
        ll = QLocale()
        dt = QDateTime.fromSecsSinceEpoch(int(round(self._created)))
        short_date = ll.toString(dt.date(), ll.dateFormat(QLocale.FormatType.NarrowFormat))
        return f'{self._title} ({short_date})'
```

#### **`NotificationManager` (Main Controller Class)**
The central notification management system that handles all notification operations:

```python
class NotificationManager(QObject):
    __slots__ = [
        'notification_timeout', 'notification_queue_max_length', 'notification_queue_max_age',
        'tray_menu', 'tray_icon', 'notifications_available', 'notifications_enabled', 
        'notifications_visible', 'notifications_queue', 'active_notification', 
        'notification_menu_actions'
    ]
```

### Configuration and Constants

#### **Timing and Queue Management**
```python
# Display duration for notifications
self.notification_timeout: Final = 12000  # 12 seconds in milliseconds

# Maximum notifications in tray menu
self.notification_queue_max_length: Final = 5

# Automatic cleanup age for old notifications
self.notification_queue_max_age: Final = 30*24*60*60  # 30 days in seconds
```

#### **System Tray Configuration**
```python
# System tray icon and menu
self.tray_icon = QSystemTrayIcon(self)
self.tray_menu = QMenu()

# Notification support detection
self.notifications_available = (
    self.tray_icon.isSystemTrayAvailable() and 
    self.tray_icon.supportsMessages()
)
```

### Icon Management System

#### **Platform-Specific Icon Selection**
```python
@staticmethod
def artisanTrayIcon() -> QIcon:
    basedir = os.path.join(getResourcePath(), 'Icons')
    if sys.platform.startswith('darwin'):
        p = os.path.join(basedir, 'artisan-trayicon.svg')
    else:
        p = os.path.join(basedir, 'artisan-trayicon-large.svg')
    icon = QIcon(p)
    icon.setIsMask(True)
    return icon

@staticmethod
def notificationPlusIcon() -> QIcon:
    basedir = os.path.join(getResourcePath(), 'Icons')
    if sys.platform.startswith('darwin'):
        p = os.path.join(basedir, 'plus-notification.png')
    else:
        p = os.path.join(basedir, 'plus-notification.svg')
    return QIcon(p)
```

### Notification Queue Management

#### **Queue Operations**
```python
def addNotificationItem(self, notification: Notification) -> None:
    """Adds notification to queue and updates menu"""
    self.notifications_queue.append(notification)
    self.updateNotificationMenu()

def removeNotificationItem(self, notification: Notification) -> None:
    """Removes notification from queue and updates menu"""
    self.notifications_queue.remove(notification)
    self.updateNotificationMenu()

def clearNotificationQueue(self) -> None:
    """Clears all queued notifications"""
    self.notifications_queue = []
```

#### **Intelligent Queue Cleanup**
```python
def cleanNotificationQueue(self) -> None:
    """Removes outdated entries and limits queue length"""
    try:
        # Remove notifications older than max_age
        age_limit = time.time() - self.notification_queue_max_age
        self.notifications_queue = [
            n for n in self.notifications_queue 
            if n.created > age_limit
        ]
        
        # Limit queue to maximum length (keep most recent)
        self.notifications_queue = self.notifications_queue[
            max(0, len(self.notifications_queue) - self.notification_queue_max_length):
        ]
    except Exception as e:
        _log.exception(e)
```

### User Interaction Handling

#### **Notification Click Processing**
```python
@pyqtSlot()
def messageClicked(self) -> None:
    """Handles user clicks on notification messages"""
    try:
        if self.active_notification:
            # Handle different notification types
            if self.active_notification.type in [NotificationType.ARTISAN_SYSTEM, NotificationType.ARTISAN_USER]:
                # Raise Artisan application window
                app = QApplication.instance()
                if app is not None:
                    assert isinstance(app, QtSingleApplication)
                    app.activateWindow()
                    
            elif self.active_notification.type in [NotificationType.PLUS_SYSTEM, NotificationType.PLUS_ADMIN, NotificationType.PLUS_ADVERT]:
                if self.active_notification.link is None:
                    # Open artisan.plus main page
                    QDesktopServices.openUrl(QUrl(plus.util.plusLink()))
                else:
                    try:
                        # Open specific link
                        QDesktopServices.openUrl(QUrl(self.active_notification.link))
                    except Exception:
                        # Fallback to artisan.plus if link is invalid
                        QDesktopServices.openUrl(QUrl(plus.util.plusLink()))
                        
            elif self.active_notification.type == NotificationType.PLUS_REMINDER:
                # Open artisan.plus reminder tab
                QDesktopServices.openUrl(QUrl(plus.util.remindersLink()))
            
            # Acknowledge notification to external service
            if self.active_notification.id:
                n = self.active_notification.id
                QTimer.singleShot(500, lambda: sendPlusNotificationSeen(n, datetime.now(timezone.utc)))
            
            # Clean up active notification
            self.removeNotificationItem(self.active_notification)
            self.active_notification = None
    except Exception as e:
        _log.exception(e)
```

#### **Menu Item Selection**
```python
@pyqtSlot(bool)
def notificationItemSelected(self, _checked: bool = False) -> None:
    """Handles selection of notification menu items"""
    action = self.sender()
    if action is not None and hasattr(action, 'data'):
        n = action.data()
        self.setNotification(n, addToQueue=False)
```

### Notification Display System

#### **Smart Notification Presentation**
```python
def showNotification(self, notification: Notification) -> None:
    """Presents notification to user with appropriate icon"""
    try:
        icon: Union[QIcon, QSystemTrayIcon.MessageIcon] = QSystemTrayIcon.MessageIcon.Information
        
        # Select appropriate icon based on notification type
        if notification.type in [NotificationType.ARTISAN_SYSTEM, NotificationType.ARTISAN_USER]:
            icon = self.notificationArtisanIcon()
        elif notification.type in [
            NotificationType.PLUS_SYSTEM,
            NotificationType.PLUS_REMINDER,
            NotificationType.PLUS_ADMIN,
            NotificationType.PLUS_ADVERT
        ]:
            icon = self.notificationPlusIcon()
        
        # Display notification with timeout
        self.tray_icon.showMessage(
            notification.formatedTitle(), 
            notification.message, 
            icon, 
            self.notification_timeout
        )
    except Exception as e:
        _log.exception(e)
```

#### **Notification Timing and Queuing**
```python
def setNotification(self, notification: Notification, addToQueue: bool = True) -> None:
    """Sets notification as active and displays it to user"""
    try:
        self.active_notification = notification
        if addToQueue:
            self.addNotificationItem(notification)
        
        # Display notification immediately
        self.showNotification(notification)
    except Exception as e:
        _log.exception(e)
```

### External Service Integration

#### **Artisan.plus Notification Handling**
```python
def sendNotificationMessage(self, title: str, message: str, 
                          notification_type: NotificationType,
                          created: Optional[float] = None,
                          hr_id: Optional[str] = None,
                          link: Optional[str] = None,
                          pos: int = 0) -> None:
    """External API for sending notifications"""
    try:
        if self.notifications_available and self.notifications_enabled:
            n = Notification(title, message, notification_type, 
                           created=created, hr_id=hr_id, link=link)
            
            # Check if notification is within age limit
            if time.time() - self.notification_queue_max_age < n.created:
                if self.active_notification is None:
                    # Display immediately if no active notification
                    self.setNotification(n)
                else:
                    # Delay presentation based on position parameter
                    QTimer.singleShot(
                        self.notification_timeout * pos, 
                        lambda: self.setNotification(n)
                    )
            else:
                _log.info('outdated notification discarded: %s', n.formatedTitle())
    except Exception as e:
        _log.exception(e)
```

#### **Notification Acknowledgment**
```python
def sendPlusNotificationSeen(hr_id: str, date: datetime) -> None:
    """Sends acknowledgment to artisan.plus service"""
    _log.debug('sendPlusNotificationSeen(%s,%s)', hr_id, date.isoformat())
    try:
        plus.connection.sendData(
            f'{plus.config.notifications_url}/seen/{hr_id}',
            {'date': date.isoformat()},
            'PUT'
        )
    except Exception as e:
        _log.exception(e)
```

### System Tray Menu Management

#### **Dynamic Menu Updates**
```python
def updateNotificationMenu(self) -> None:
    """Updates system tray menu with current notifications"""
    try:
        self.cleanNotificationQueue()
        self.tray_menu.clear()
        self.notification_menu_actions = []
        
        if len(self.notifications_queue) > 0 and self.notifications_visible:
            self.tray_icon.show()
            
            # Add menu items for each notification (most recent first)
            for n in reversed(self.notifications_queue):
                title = n.formatedTitle()
                menu_title = (title[:25] + '...') if len(title) > 25 else title
                
                action = QAction(menu_title)
                action.triggered.connect(self.notificationItemSelected)
                action.setData(n)
                self.notification_menu_actions.append(action)
                self.tray_menu.addAction(action)
        else:
            self.tray_icon.hide()
    except Exception as e:
        _log.exception(e)
```

### Visibility and State Management

#### **Notification System Control**
```python
def showNotifications(self) -> None:
    """Enables notification visibility"""
    if self.notifications_available:
        self.notifications_visible = True
        if len(self.notifications_queue) > 0:
            self.tray_icon.show()
            self.updateNotificationMenu()

def hideNotifications(self) -> None:
    """Disables notification visibility"""
    if self.notifications_available:
        self.notifications_visible = False
        self.tray_icon.hide()

def enableNotifications(self) -> None:
    """Enables notification processing"""
    self.notifications_enabled = True

def disableNotifications(self) -> None:
    """Disables notification processing"""
    self.notifications_enabled = False
```

### Cross-Platform Compatibility

#### **Platform-Specific Adaptations**
- **macOS**: Uses SVG icons and specific icon paths
- **Windows/Linux**: Uses large SVG icons for better visibility
- **System Tray Support**: Detects and adapts to platform capabilities
- **Notification APIs**: Leverages native system notification support

#### **Qt Version Compatibility**
```python
try:
    from PyQt6.QtWidgets import QSystemTrayIcon, QApplication, QMenu
    from PyQt6.QtGui import QIcon, QDesktopServices, QAction
    from PyQt6.QtCore import QTimer, pyqtSlot, QUrl, QObject, QDateTime, QLocale
except ImportError:
    from PyQt5.QtWidgets import QSystemTrayIcon, QApplication, QMenu, QAction
    from PyQt5.QtGui import QIcon, QDesktopServices
    from PyQt5.QtCore import QTimer, pyqtSlot, QUrl, QObject, QDateTime, QLocale
```

### Error Handling and Logging

#### **Comprehensive Exception Handling**
- **Graceful Degradation**: Continues operation even if notifications fail
- **Detailed Logging**: Comprehensive error tracking and debugging
- **User Feedback**: Clear error messages and fallback behaviors
- **Resource Cleanup**: Proper cleanup of failed operations

#### **Debug and Information Logging**
```python
_log: Final[logging.Logger] = logging.getLogger(__name__)

# Extensive logging throughout the system
_log.debug('addNotificationItem()')
_log.info('setNotification(%s, %s, %s, %s)', notification.type.name, 
          notification.formatedTitle(), notification.message, addToQueue)
_log.exception(e)  # For exception logging
```

### Integration Points

#### **Main Application Integration**
- **System Tray**: Provides persistent system tray presence
- **Notification Queue**: Manages all application notifications
- **User Interaction**: Handles notification clicks and acknowledgments
- **External Services**: Integrates with artisan.plus notification system

#### **External Service Integration**
- **Artisan.plus**: Receives and displays external notifications
- **URL Handling**: Opens external links and services
- **Acknowledgment**: Confirms notification processing to external services
- **Authentication**: Handles external service authentication

### Performance and Resource Management

#### **Efficient Queue Management**
- **Automatic Cleanup**: Removes old notifications automatically
- **Memory Optimization**: Limits queue size to prevent memory issues
- **Smart Aging**: Intelligent timestamp-based cleanup
- **Resource Conservation**: Efficient icon and menu management

#### **Timing Optimization**
- **Delayed Presentation**: Prevents notification spam
- **Timeout Management**: Automatic notification dismissal
- **Queue Positioning**: Intelligent notification scheduling
- **User Experience**: Smooth notification flow

This module represents the most sophisticated notification system in Artisan, providing professional roasters with enterprise-grade notification capabilities, system tray integration, and external service connectivity through a unified and intelligent notification management system.