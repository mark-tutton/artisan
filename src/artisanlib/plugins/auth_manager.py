import os
import logging
import time
import requests
import webbrowser
import threading
from typing import Optional, Dict, Any
from dataclasses import dataclass
from PyQt6.QtCore import QObject, pyqtSignal
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
from pathlib import Path
import sys



_log = logging.getLogger(__name__)

@dataclass
class TokenInfo:
    access_token: str
    refresh_token: str
    expires_at: int
    token_type: str = "Bearer"

class GoogleOAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/callback'):
            # Parse the callback URL
            parsed_url = urllib.parse.urlparse(self.path)
            query_params = urllib.parse.parse_qs(parsed_url.query)
            
            # Check for direct tokens first 
            access_token = query_params.get('accessToken', [None])[0]
            refresh_token = query_params.get('refreshToken', [None])[0]
            
            if access_token and refresh_token:
                # Store tokens directly
                self.server.tokens = {
                    'accessToken': access_token,
                    'refreshToken': refresh_token
                }
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'''
                <html>
                <body>
                    <h1>Authentication Successful!</h1>
                    <p>You can close this window and return to Artisan.</p>
                </body>
                </html>
                ''')
                return
            
            # Fallback to authorization code flow 
            auth_code = query_params.get('code', [None])[0]
            state = query_params.get('state', [None])[0]
            
            if auth_code and state == 'artisan':
                # Exchange authorization code for tokens
                try:
                    response = requests.post(
                        f"{self.server.auth_base_url}/google/callback",
                        json={"code": auth_code, "state": state},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            # Store tokens
                            self.server.tokens = {
                                'accessToken': data['accessToken'],
                                'refreshToken': data['refreshToken']
                            }
                            
                            # Send success response
                            self.send_response(200)
                            self.send_header('Content-type', 'text/html')
                            self.end_headers()
                            self.wfile.write(b'''
                            <html>
                            <body>
                                <h1>Authentication Successful!</h1>
                                <p>You can close this window and return to Artisan.</p>
                            </body>
                            </html>
                            ''')
                        else:
                            raise Exception("Authentication failed")
                    else:
                        raise Exception(f"HTTP {response.status_code}")
                        
                except Exception as e:
                    _log.error(f"Token exchange error: {e}")
                    self.send_response(400)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(f'''
                    <html>
                    <body>
                        <h1>Authentication Failed</h1>
                        <p>Error: {str(e)}</p>
                    </body>
                    </html>
                    '''.encode())
            else:
                # Send error response
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                self.wfile.write(b'''
                <html>
                <body>
                    <h1>Authentication Failed</h1>
                    <p>Invalid callback parameters.</p>
                </body>
                </html>
                ''')
    
    def log_message(self, format, *args):
        # Suppress default logging
        pass

class GlobalAuthManager(QObject):
    """Centralized JWT token management for all plugins"""
    
    # Signals for token events
    token_refreshed = pyqtSignal(str, str)  # access_token, refresh_token
    token_expired = pyqtSignal()
    login_successful = pyqtSignal(str, str)  # access_token, refresh_token
    login_failed = pyqtSignal(str)  # error message
    api_key_validated = pyqtSignal(str)  # api_key
    
    def __init__(self):
        super().__init__()
        
        _log.info("DEBUG: GlobalAuthManager.__init__ called")
        
        # prevent re-initialization of instance variables if already initialized
        if getattr(self, '_initialized', False):
            _log.info("DEBUG: GlobalAuthManager already initialized, skipping instance variable setup")
            return
        
        # Initialize instance variables
        try:
            self.current_token: Optional[TokenInfo] = None
            self.api_key: Optional[str] = None
            self.auth_method: str = "none"
            
            self.auth_base_url = self._load_auth_config()
            self._load_stored_tokens()
            self._load_stored_api_key()
            
            _log.info("DEBUG: GlobalAuthManager instance variables initialized successfully")
        except Exception as e:
            _log.error(f"DEBUG: Error initializing instance variables: {e}", exc_info=True)
            import traceback
            _log.error(traceback.format_exc())
            # Continue - set defaults even if loading fails
            if not hasattr(self, 'current_token'):
                self.current_token = None
            if not hasattr(self, 'api_key'):
                self.api_key = None
            if not hasattr(self, 'auth_method'):
                self.auth_method = "none"
            if not hasattr(self, 'auth_base_url'):
                self.auth_base_url = None
        
        self._initialized = True
        _log.info("DEBUG: GlobalAuthManager marked as initialized")


    def _load_auth_config(self) -> str:
        """Load auth configuration from file"""
        try:
            config_path = Path.home() / ".artisan" / "auth" / "auth_config.json"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                auth_url = config.get('auth_base_url', 'http://localhost:5101/auth')
                _log.info(f"Loaded auth URL from config: {auth_url}")
                return auth_url
        except Exception as e:
            _log.warning(f"Could not load auth config: {e}")
        
        # Fallback to env var or default
        fallback_url = os.getenv('ARTISAN_AUTH_BASE_URL', 'http://localhost:5101/auth')
        _log.info(f"Using fallback auth URL: {fallback_url}")
        return fallback_url
    
    def _save_auth_config(self) -> None:
        """Save auth configuration to file"""
        try:
            config_path = Path.home() / ".artisan" / "auth" / "auth_config.json"
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            config = {
                'auth_base_url': self.auth_base_url,
                'updated_at': time.time()
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
                
            _log.debug(f"Auth config saved to: {config_path}")
        except Exception as e:
            _log.error(f"Failed to save auth config: {e}")
    
    def set_auth_base_url(self, url: str) -> None:
        """Set the authentication base URL and save to config"""
        if not url.endswith('/auth'):
            url = url.rstrip('/') + '/auth'
        self.auth_base_url = url
        _log.info(f"Auth base URL set to: {self.auth_base_url}")
        
        # Save to config file
        self._save_auth_config()

    
    def get_auth_base_url(self) -> str:
        """Get the current authentication base URL"""
        return self.auth_base_url

    def login_with_api_key(self, api_key: str) -> bool:
        """Authenticate using an API key"""
        try:
            if not api_key or not api_key.startswith('ccr_'):
                error_msg = "Invalid API key format. API keys must start with 'ccr_'"
                self._safe_emit(self.login_failed, error_msg)
                return False
            
            # Get gateway base URL (remove /auth suffix if present)
            gateway_url = self.auth_base_url.replace('/auth', '')
            
            # Verify API key with backend
            response = requests.post(
                f"{gateway_url}/api/api-keys/verify",
                headers={"X-API-Key": api_key},
                json={"apiKey": api_key},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('valid'):
                    # Store API key
                    self.api_key = api_key
                    self.auth_method = "api_key"
                    self._save_api_key()
                    self._safe_emit(self.api_key_validated, api_key)
                    self._safe_emit(self.login_successful, api_key, "")
                    _log.info("API key authentication successful")
                    return True
                else:
                    error_msg = data.get('error', 'API key validation failed')
                    self._safe_emit(self.login_failed, error_msg)
                    return False
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', f'HTTP {response.status_code}')
                self._safe_emit(self.login_failed, error_msg)
                return False
                
        except requests.exceptions.RequestException as e:
            _log.error(f"API key authentication error: {e}")
            self._safe_emit(self.login_failed, f"Network error: {str(e)}")
            return False
        except Exception as e:
            _log.error(f"API key authentication error: {e}", exc_info=True)
            self._safe_emit(self.login_failed, f"Authentication error: {str(e)}")
            return False
    
    def login_with_google(self) -> bool:
        """Perform Google OAuth login"""
        try:
            # Start local server to handle OAuth callback
            server = HTTPServer(('localhost', 8080), GoogleOAuthHandler)
            server.tokens = None
            server.auth_base_url = self.auth_base_url  
            
            # Start server in a thread
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            # Open Google OAuth URL
            oauth_url = f"{self.auth_base_url}/google/artisan"
            webbrowser.open(oauth_url)
            
            # Wait for OAuth callback
            timeout = 60  # 60 seconds timeout
            start_time = time.time()
            
            while server.tokens is None and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            server.shutdown()
            
            if server.tokens:
                access_token = server.tokens.get('accessToken')
                refresh_token = server.tokens.get('refreshToken')
                
                if not access_token or not refresh_token:
                    self._safe_emit(self.login_failed, "Invalid token response from server")
                    return False

                # Get actual expiration from server response
                expires_in = server.tokens.get('expiresIn', 3600)  # Default 1 hour if not provided
                
                self._set_tokens(access_token, refresh_token, expires_in)
                self._safe_emit(self.login_successful, access_token, refresh_token)
                return True
            else:
                self._safe_emit(self.login_failed, "OAuth timeout or failed")
                return False
                
        except Exception as e:
            _log.error(f"Google OAuth error: {e}", exc_info=True)
            self._safe_emit(self.login_failed, str(e))
            return False
    
    def refresh_token(self) -> bool:
        """Refresh the JWT token"""
        if self.auth_method != "oauth":
            return False

        if not self.current_token or not self.current_token.refresh_token:
            return False
            
        try:
            response = requests.post(
                f"{self.auth_base_url}/refresh",
                json={"refreshToken": self.current_token.refresh_token},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get('accessToken')
                refresh_token = data.get('refreshToken', self.current_token.refresh_token)
                expires_in = data.get('expiresIn', 3600)
                
                if not access_token:
                    _log.error("No access token in refresh response")
                    return False
                
                self._set_tokens(access_token, refresh_token, expires_in)
                
                # Safely emit signal - check if QApplication is ready
                try:
                    from PyQt6.QtWidgets import QApplication
                    app = QApplication.instance()
                    if app is not None:
                        self.token_refreshed.emit(access_token, refresh_token)
                    else:
                        _log.warning("QApplication not ready, skipping signal emission")
                except Exception as e:
                    _log.warning(f"Could not emit token_refreshed signal: {e}")
                
                return True
            else:
                _log.error(f"Token refresh failed with status {response.status_code}")
                
        except Exception as e:
            _log.error(f"Token refresh error: {e}", exc_info=True)
            
        return False

    
    def get_valid_token(self) -> Optional[str]:
        """Get a valid access token or API key, refreshing if necessary"""
        if self.auth_method == "api_key":
            return self.api_key
        elif self.auth_method == "oauth":
            if not self.current_token:
                return None
                
            if self.is_token_expired():
                if not self.refresh_token():
                    self.token_expired.emit()
                    return None
                    
            return self.current_token.access_token
        
        return None
    
    def is_token_expired(self) -> bool:
        """Check if token is expired (only for OAuth tokens)"""
        if self.auth_method != "oauth" or not self.current_token:
            return False
        return time.time() >= self.current_token.expires_at

    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests"""
        headers = {}
        
        if self.auth_method == "api_key" and self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.auth_method == "oauth":
            token = self.get_valid_token()
            if token:
                headers["Authorization"] = f"Bearer {token}"
        
        return headers

    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        if self.auth_method == "api_key": 
            return self.api_key is not None
        elif self.auth_method == "oauth":
            return self.get_valid_token() is not None
        return False
    
    
    def _set_tokens(self, access_token: str, refresh_token: str, expires_in: int):
        """Set new tokens"""
        expires_at = int(time.time()) + expires_in
        self.current_token = TokenInfo(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )
        self._save_tokens()
    
    def _get_token_storage_path(self) -> Path:
        """Get the path for storing tokens"""
        token_dir = Path.home() / ".artisan" / "auth"
        token_dir.mkdir(parents=True, exist_ok=True)
        return token_dir / "tokens.json"

    def _get_api_key_storage_path(self) -> Path:
        """Get the path for storing API key"""
        token_dir = Path.home() / ".artisan" / "auth"
        token_dir.mkdir(parents=True, exist_ok=True)
        return token_dir / "api_key.json"
    
    def _load_stored_tokens(self):
        """Load tokens from persistent storage"""
        try:
            token_path = self._get_token_storage_path()
            if token_path.exists():
                with open(token_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Validate data structure
                if not isinstance(data, dict):
                    _log.warning("Invalid token data format")
                    return
                    
                # Check if tokens are still valid
                expires_at = data.get('expires_at', 0)
                if not isinstance(expires_at, (int, float)):
                    _log.warning("Invalid expires_at value in token data")
                    return
                
                if expires_at > time.time():
                    # Validate required fields
                    access_token = data.get('access_token')
                    refresh_token = data.get('refresh_token')
                    
                    if not access_token or not refresh_token:
                        _log.warning("Missing required token fields")
                        return
                    
                    self.current_token = TokenInfo(
                        access_token=access_token,
                        refresh_token=refresh_token,
                        expires_at=expires_at,
                        token_type=data.get('token_type', 'Bearer')
                    )
                    self.auth_method = "oauth"
                    _log.info("Loaded valid tokens from storage")
                else:
                    _log.info("Stored tokens have expired")
                    # Don't try to refresh during initialization - defer it
                    # Refresh will happen when token is actually needed
                    if data.get('refresh_token'):
                        _log.info("Tokens expired, will refresh when needed")
                        # Store refresh token for later use
                        self.current_token = TokenInfo(
                            access_token="",  # Will be refreshed
                            refresh_token=data.get('refresh_token'),
                            expires_at=0,
                            token_type='Bearer'
                        )
                        self.auth_method = "oauth"
            else:
                _log.debug("No stored tokens found")
        except json.JSONDecodeError as e:
            _log.error(f"Failed to parse token file (corrupted): {e}")
            # Try to backup corrupted file
            try:
                backup_path = token_path.with_suffix('.json.bak')
                token_path.rename(backup_path)
                _log.info(f"Backed up corrupted token file to {backup_path}")
            except:
                pass
        except Exception as e:
            _log.error(f"Failed to load stored tokens: {e}", exc_info=True)
            # Don't clear tokens on error - might be a temporary issue


    def _load_stored_api_key(self):
        """Load API key from persistent storage"""
        try:
            api_key_path = self._get_api_key_storage_path()
            if api_key_path.exists():
                with open(api_key_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                api_key = data.get('api_key')
                if api_key and api_key.startswith('ccr_'):
                    self.api_key = api_key
                    self.auth_method = "api_key"
                    _log.info("Loaded API key from storage")
        except Exception as e:
            _log.error(f"Failed to load stored API key: {e}")
    
    def _save_tokens(self):
        """Save tokens to persistent storage"""
        try:
            if not self.current_token:
                return
                
            token_path = self._get_token_storage_path()
            data = {
                'access_token': self.current_token.access_token,
                'refresh_token': self.current_token.refresh_token,
                'expires_at': self.current_token.expires_at,
                'token_type': self.current_token.token_type,
                'saved_at': time.time()
            }
            
            with open(token_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            _log.debug("Tokens saved to storage")
        except Exception as e:
            _log.error(f"Failed to save tokens: {e}")
    
    def _save_api_key(self):
        """Save API key to persistent storage"""
        try:
            if not self.api_key:
                return
                
            api_key_path = self._get_api_key_storage_path()
            data = {
                'api_key': self.api_key,
                'saved_at': time.time()
            }
            
            with open(api_key_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            _log.debug("API key saved to storage")
        except Exception as e:
            _log.error(f"Failed to save API key: {e}")
    
    def clear_tokens(self):
        """Clear all tokens and API keys"""
        self.current_token = None
        self.api_key = None
        self.auth_method = "none"
        try:
            token_path = self._get_token_storage_path()
            if token_path.exists():
                token_path.unlink()
                _log.info("Cleared stored tokens")
            
            api_key_path = self._get_api_key_storage_path()
            if api_key_path.exists():
                api_key_path.unlink()
                _log.info("Cleared stored API key")
        except Exception as e:
            _log.error(f"Failed to clear stored credentials: {e}")
    
    def _safe_emit(self, signal, *args):
        """Safely emit a signal, checking if QApplication is ready"""
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
            if app is not None:
                signal.emit(*args)
            else:
                _log.warning(f"QApplication not ready, skipping signal emission: {signal}")
        except Exception as e:
            _log.warning(f"Could not emit signal {signal}: {e}")

    def get_token_info(self) -> Optional[Dict[str, Any]]:
        """Get current token information for debugging"""
        try:
            if self.auth_method == "api_key" and self.api_key:
                return {
                    'api_key': self.api_key[:12] + '...' if len(self.api_key) > 12 else self.api_key,
                    'auth_method': 'api_key',
                    'is_expired': False
                }
            elif self.auth_method == "oauth" and self.current_token:
                expires_in = max(0, self.current_token.expires_at - int(time.time())) if self.current_token.expires_at > 0 else 0
                return {
                    'access_token': (self.current_token.access_token[:20] + '...') if self.current_token.access_token else 'N/A',
                    'refresh_token': (self.current_token.refresh_token[:20] + '...') if self.current_token.refresh_token else 'N/A',
                    'expires_at': self.current_token.expires_at,
                    'expires_in': expires_in,
                    'is_expired': self.is_token_expired(),
                    'auth_method': 'oauth'
                }
        except Exception as e:
            _log.error(f"Error getting token info: {e}", exc_info=True)
        return None


_auth_manager_instance: Optional[GlobalAuthManager] = None

def get_auth_manager() -> Optional[GlobalAuthManager]:
    """
    Factory function to get or create the GlobalAuthManager singleton.
    Ensures QApplication is ready before creating the QObject.
    """
    global _auth_manager_instance
    
    if _auth_manager_instance is not None:
        return _auth_manager_instance
    
    # Check if QApplication is ready
    try:
        try:
            from PyQt6.QtWidgets import QApplication
            app = QApplication.instance()
        except ImportError:
            try:
                from PyQt5.QtWidgets import QApplication  # type: ignore
                app = QApplication.instance()
            except ImportError:
                _log.error("Neither PyQt6 nor PyQt5 available - cannot create GlobalAuthManager")
                return None
        
        if app is None:
            _log.warning("QApplication.instance() is None - QApplication not ready yet")
            try:
                from PyQt6.QtCore import QTimer
                def delayed_create():
                    global _auth_manager_instance
                    if _auth_manager_instance is None:
                        try:
                            _auth_manager_instance = GlobalAuthManager()
                            _log.info("GlobalAuthManager created (delayed)")
                        except Exception as e:
                            _log.error(f"Failed to create GlobalAuthManager (delayed): {e}", exc_info=True)
                QTimer.singleShot(100, delayed_create)
                return None
            except ImportError:
                try:
                    from PyQt5.QtCore import QTimer  # type: ignore
                    def delayed_create():
                        global _auth_manager_instance
                        if _auth_manager_instance is None:
                            try:
                                _auth_manager_instance = GlobalAuthManager()
                                _log.info("GlobalAuthManager created (delayed)")
                            except Exception as e:
                                _log.error(f"Failed to create GlobalAuthManager (delayed): {e}", exc_info=True)
                    QTimer.singleShot(100, delayed_create)
                    return None
                except ImportError:
                    pass
            return None
    
    except Exception as e:
        _log.error(f"Error checking QApplication: {e}", exc_info=True)
        return None
    
    # QApplication is ready, create the instance
    try:
        _auth_manager_instance = GlobalAuthManager()
        _log.info("GlobalAuthManager created successfully")
        return _auth_manager_instance
    except Exception as e:
        _log.error(f"Failed to create GlobalAuthManager: {e}", exc_info=True)
        import traceback
        _log.error(traceback.format_exc())
        return None