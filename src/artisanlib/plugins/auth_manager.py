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
        self.auth_base_url = "http://localhost:5101/auth"
        self._load_stored_tokens()
    
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
                expires_in = 3600  # Default 1 hour
                
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
        """Get a valid access token, refreshing if necessary"""
        if not self.current_token:
            return None
            
        if self.is_token_expired():
            if not self.refresh_token():
                self.token_expired.emit()
                return None
                
        return self.current_token.access_token
    
    def is_token_expired(self) -> bool:
        """Check if token is expired"""
        if not self.current_token:
            return True
        return time.time() >= self.current_token.expires_at
    
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
    
    def clear_tokens(self):
        """Clear all tokens"""
        self.current_token = None
        try:
            token_path = self._get_token_storage_path()
            if token_path.exists():
                token_path.unlink()
                _log.info("Cleared stored tokens")
        except Exception as e:
            _log.error(f"Failed to clear stored tokens: {e}")
    
    def get_token_info(self) -> Optional[Dict[str, Any]]:
        """Get current token information for debugging"""
        if not self.current_token:
            return None
            
        return {
            'access_token': self.current_token.access_token[:20] + '...',
            'refresh_token': self.current_token.refresh_token[:20] + '...',
            'expires_at': self.current_token.expires_at,
            'expires_in': max(0, self.current_token.expires_at - int(time.time())),
            'is_expired': self.is_token_expired()
        }
    
    
    def clear_tokens(self):
        """Clear all tokens"""
        self.current_token = None
        # Clear from storage
