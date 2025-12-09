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

    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalAuthManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        super().__init__()
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.current_token: Optional[TokenInfo] = None
        self.api_key: Optional[str] = None
        self.auth_method: str = "none"  # "oauth", "api_key", or "none"

        self.auth_base_url = self._load_auth_config()
        self._load_stored_tokens()
        self._load_stored_api_key()


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
                self.login_failed.emit("Invalid API key format. API keys must start with 'ccr_'")
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
                    self.api_key_validated.emit(api_key)
                    self.login_successful.emit(api_key, "")  # Empty refresh token for API keys
                    _log.info("API key authentication successful")
                    return True
                else:
                    error_msg = data.get('error', 'API key validation failed')
                    self.login_failed.emit(error_msg)
                    return False
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get('error', f'HTTP {response.status_code}')
                self.login_failed.emit(error_msg)
                return False
                
        except requests.exceptions.RequestException as e:
            _log.error(f"API key authentication error: {e}")
            self.login_failed.emit(f"Network error: {str(e)}")
            return False
        except Exception as e:
            _log.error(f"API key authentication error: {e}")
            self.login_failed.emit(f"Authentication error: {str(e)}")
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
                access_token = server.tokens['accessToken']
                refresh_token = server.tokens['refreshToken']

                 # Get actual expiration from server response
                expires_in = server.tokens.get('expiresIn', 3600)  # Default 1 hour if not provided
                
                # expires_in = 3600  # Default 1 hour
                
                self._set_tokens(access_token, refresh_token, expires_in)
                self.login_successful.emit(access_token, refresh_token)
                return True
            else:
                self.login_failed.emit("OAuth timeout or failed")
                return False
                
        except Exception as e:
            _log.error(f"Google OAuth error: {e}")
            self.login_failed.emit(str(e))
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
                
                self._set_tokens(access_token, refresh_token, expires_in)
                self.token_refreshed.emit(access_token, refresh_token)
                return True
                
        except Exception as e:
            _log.error(f"Token refresh error: {e}")
            
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
                    
                # Check if tokens are still valid
                expires_at = data.get('expires_at', 0)
                if expires_at > time.time():
                    self.current_token = TokenInfo(
                        access_token=data['access_token'],
                        refresh_token=data['refresh_token'],
                        expires_at=expires_at,
                        token_type=data.get('token_type', 'Bearer')
                    )
                    self.auth_method = "oauth"
                    _log.info("Loaded valid tokens from storage")
                else:
                    _log.info("Stored tokens have expired")
                    # Try to refresh if there is a refresh token
                    if data.get('refresh_token'):
                        _log.info("Attempting to refresh expired tokens")
                        if self.refresh_token():
                            _log.info("Successfully refreshed tokens")
                        else:
                            _log.warning("Failed to refresh tokens")
                            self.clear_tokens()
            else:
                _log.debug("No stored tokens found")
        except Exception as e:
            _log.error(f"Failed to load stored tokens: {e}")
            self.clear_tokens()

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
    
    def get_token_info(self) -> Optional[Dict[str, Any]]:
        """Get current token information for debugging"""
        if self.auth_method == "api_key" and self.api_key:
            return {
                'api_key': self.api_key[:12] + '...' if len(self.api_key) > 12 else self.api_key,
                'auth_method': 'api_key',
                'is_expired': False
            }
        elif self.auth_method == "oauth" and self.current_token:
            return {
                'access_token': self.current_token.access_token[:20] + '...',
                'refresh_token': self.current_token.refresh_token[:20] + '...',
                'expires_at': self.current_token.expires_at,
                'expires_in': max(0, self.current_token.expires_at - int(time.time())),
                'is_expired': self.is_token_expired(),
                'auth_method': 'oauth'
            }
        return None
