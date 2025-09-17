import json
import logging
import time
import requests
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

_log = logging.getLogger(__name__)

from .config import AutosaveAddonConfig

@dataclass
class TokenInfo:
    access_token: str
    refresh_token: str
    expires_at: int
    token_type: str = "Bearer"

class JWTTokenManager:
    """Manages JWT token lifecycle including refresh"""
    
    def __init__(self, config: AutosaveAddonConfig):
        self.config = config
        self.current_token: Optional[TokenInfo] = None
        self._load_stored_tokens()
    
    def _load_stored_tokens(self) -> None:
        """Load tokens from config"""
        if (self.config.autosave_jwt_token and 
            self.config.autosave_refresh_token and 
            self.config.autosave_token_expires_at):
            
            self.current_token = TokenInfo(
                access_token=self.config.autosave_jwt_token,
                refresh_token=self.config.autosave_refresh_token,
                expires_at=self.config.autosave_token_expires_at
            )
            _log.info("Loaded stored JWT tokens from config")
    
    def _save_tokens_to_config(self, token_info: TokenInfo) -> None:
        """Save tokens to config"""
        self.config.autosave_jwt_token = token_info.access_token
        self.config.autosave_refresh_token = token_info.refresh_token
        self.config.autosave_token_expires_at = token_info.expires_at
        self.current_token = token_info
        _log.info("Saved JWT tokens to config")
    
    def is_token_expired(self, token_info: Optional[TokenInfo] = None) -> bool:
        """Check if token is expired or about to expire"""
        if not token_info:
            token_info = self.current_token
        
        if not token_info:
            return True
        
        current_time = int(time.time())
        threshold = self.config.autosave_refresh_threshold
        
        return token_info.expires_at <= (current_time + threshold)
    
    def get_valid_token(self) -> Optional[str]:
        """Get a valid access token, refreshing if necessary"""
        if not self.current_token:
            _log.warning("No JWT token available")
            return None
        
        if self.is_token_expired():
            _log.info("JWT token expired or about to expire, attempting refresh")
            if not self.refresh_token():
                _log.error("Failed to refresh JWT token")
                return None
        
        return self.current_token.access_token
    
    def refresh_token(self) -> bool:
        """Refresh the JWT token using refresh token"""
        if not self.current_token or not self.current_token.refresh_token:
            _log.error("No refresh token available")
            return False
        
        try:
            refresh_url = f"{self.config.autosave_server_url.replace('/api/files/upload', '')}/api/auth/refresh"
            _log.info(f"Attempting token refresh at: {refresh_url}")
            
            payload = {
                "refreshToken": self.current_token.refresh_token
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                refresh_url,
                json=payload,
                headers=headers,
                timeout=self.config.autosave_connection_timeout
            )
            
            _log.info(f"Token refresh response: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Calculate expiry time
                expires_in = data.get('expiresIn', 3600)  # Default 1 hour
                expires_at = int(time.time()) + expires_in
                
                new_token = TokenInfo(
                    access_token=data['accessToken'],
                    refresh_token=data.get('refreshToken', self.current_token.refresh_token),
                    expires_at=expires_at,
                    token_type=data.get('tokenType', 'Bearer')
                )
                
                self._save_tokens_to_config(new_token)
                _log.info("JWT token refreshed successfully")
                return True
            else:
                _log.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            _log.error(f"Token refresh request failed: {e}")
            return False
        except Exception as e:
            _log.error(f"Token refresh error: {e}")
            return False
    
    def set_tokens(self, access_token: str, refresh_token: str, expires_in: int) -> None:
        """Set new tokens (e.g., after login)"""
        expires_at = int(time.time()) + expires_in
        
        token_info = TokenInfo(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at
        )
        
        self._save_tokens_to_config(token_info)
        _log.info("New JWT tokens set")
    
    def clear_tokens(self) -> None:
        """Clear stored tokens"""
        self.config.autosave_jwt_token = ""
        self.config.autosave_refresh_token = ""
        self.config.autosave_token_expires_at = 0
        self.current_token = None
        _log.info("JWT tokens cleared")
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers with valid token"""
        if self.config.autosave_auth_type in ["jwt", "bearer"]:
            token = self.get_valid_token()
            if token:
                return {"Authorization": f"Bearer {token}"}
        
        return {}