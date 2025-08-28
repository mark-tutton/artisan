import requests
import json
import logging
import time
from typing import Dict, List, Optional, Any
from threading import Lock

_log = logging.getLogger(__name__)

class InventoryFetcher:
    """Fetches beans data from external server with JWT authentication and thread safety"""
    
    def __init__(self, server_url: str, api_key: Optional[str] = None, timeout: int = 30,
        auth_type: str = "none", jwt_token: Optional[str] = None,
    use_ssl: bool = False, validate_ssl_cert: bool = True):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.auth_type = auth_type
        self.jwt_token = jwt_token
        self.use_ssl = use_ssl
        self.validate_ssl_cert = validate_ssl_cert
        
        # Create session with proper SSL configuration
        self.session = requests.Session()
        if not self.validate_ssl_cert:
            self.session.verify = False
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Thread safety
        self._lock = Lock()
        self._last_request_time = 0
        self._min_request_interval = 0.1  # Minimum 100ms between requests
        
        # Set up headers
        self._setup_headers()

    def _setup_headers(self):
        """Setup authentication headers based on config"""
        headers = {'Content-Type': 'application/json'}
        
        if self.auth_type == "api_token" and self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.auth_type in ["jwt", "bearer"] and self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token}"
        
        self.session.headers.update(headers)
        _log.debug(f"Setup headers for auth type: {self.auth_type}")

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for requests"""
        headers = {}
        
        # Check if we have a JWT token first
        if self.jwt_token and self.jwt_token.strip():
            # JWT token
            headers["Authorization"] = f"Bearer {self.jwt_token.strip()}"
            _log.debug("Using JWT Bearer authentication")
        elif self.auth_type == "api_token" and self.api_key:
            headers["X-API-Key"] = self.api_key.strip()
            _log.debug("Using API key authentication")
        elif self.auth_type in ["jwt", "bearer"] and self.jwt_token:
            headers["Authorization"] = f"Bearer {self.jwt_token.strip()}"
            _log.debug("Using JWT Bearer authentication")
        elif self.auth_type == "none" and self.api_key and not self.jwt_token:
            # Legacy mode - only use API key if no JWT token is present
            headers["X-API-Key"] = self.api_key.strip()
            _log.debug("Using legacy API key authentication")
        
        return headers

    def _rate_limit(self):
        """Rate limiting to prevent overwhelming the server"""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            time.sleep(self._min_request_interval - time_since_last)
        self._last_request_time = time.time()

    def _build_url(self, endpoint: str) -> str:
        """Build full URL with proper protocol"""
        # Check if server_url already has a protocol
        if self.server_url.startswith(('http://', 'https://')):
            # Server URL already has protocol, just add endpoint
            return f"{self.server_url.rstrip('/')}{endpoint}"
        else:
            # No protocol specified, add default
            protocol = "https" if self.use_ssl else "http"
            return f"{protocol}://{self.server_url.rstrip('/')}{endpoint}"

    def fetch_beans(self, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        """Fetch beans from server with pagination support and thread safety"""
        with self._lock:
            try:
                self._rate_limit()
                
                # Build URL with pagination parameters
                url = self._build_url("/api/inventory")
                params = {
                    'limit': limit,
                    'offset': offset
                }
                
                # Only add API key as query parameter for legacy auth when no JWT token
                if (self.auth_type == "none" and self.api_key and 
                    not self.jwt_token and not self.jwt_token.strip()):
                    params['api_key'] = self.api_key.strip()
                    _log.debug("Added API key to URL parameters (legacy mode)")
                
                _log.info(f"Fetching beans from: {url} (limit: {limit}, offset: {offset})")
                _log.debug(f"Auth type: {self.auth_type}, JWT token: {bool(self.jwt_token)}, API key: {bool(self.api_key)}")
                
                headers = self._get_auth_headers()
                response = self.session.get(url, params=params, timeout=self.timeout, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                beans = data.get('data', [])
                total_count = data.get('total', len(beans))
                
                _log.info(f"Successfully fetched {len(beans)} beans (total available: {total_count})")
                return {
                    'data': beans,
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                }
                
            except requests.exceptions.RequestException as e:
                _log.error(f"Failed to fetch beans: {e}")
                raise Exception(f"Failed to fetch beans: {e}")

    def fetch_all_beans(self, batch_size: int = 1000) -> List[Dict[str, Any]]:
        """Fetch all beans using pagination with progress tracking"""
        all_beans = []
        offset = 0
        
        try:
            # Get first batch to determine total count
            first_result = self.fetch_beans(limit=batch_size, offset=0)
            total_count = first_result['total']
            all_beans.extend(first_result['data'])
            
            _log.info(f"Starting batch fetch: {total_count} total beans, batch size: {batch_size}")
            
            # Continue fetching remaining batches
            while first_result['has_more']:
                offset += batch_size
                result = self.fetch_beans(limit=batch_size, offset=offset)
                beans = result['data']
                all_beans.extend(beans)
                
                _log.info(f"Fetched batch {len(beans)} beans, total so far: {len(all_beans)}/{total_count}")
                
                if not result['has_more']:
                    break
            
            _log.info(f"Completed batch fetch: {len(all_beans)} beans from server")
            return all_beans
            
        except Exception as e:
            _log.error(f"Error during batch fetch: {e}")
            raise
    
    def fetch_bean_details(self, bean_id: str) -> Dict[str, Any]:
        """Fetch specific bean details with thread safety"""
        with self._lock:
            try:
                self._rate_limit()
                
                # Build URL with API key as query parameter
                url = self._build_url(f"/api/inventory/{bean_id}")
                params = {}
                
                # Only add API key as query parameter for legacy auth when no JWT token
                if (self.auth_type == "none" and self.api_key and 
                    not self.jwt_token and not self.jwt_token.strip()):
                    params['api_key'] = self.api_key.strip()
                    _log.debug("Added API key to URL parameters (legacy mode)")
                
                headers = self._get_auth_headers()
                response = self.session.get(url, params=params, timeout=self.timeout, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                return data.get('data', {})
                
            except requests.exceptions.RequestException as e:
                _log.error(f"Failed to fetch bean details: {e}")
                raise Exception(f"Failed to fetch bean details: {e}")
    
    def test_connection(self) -> bool:
        """Test connection to server with thread safety"""
        with self._lock:
            try:
                self._rate_limit()
                url = self._build_url("/api/health")
                headers = self._get_auth_headers()
                
                response = self.session.get(url, timeout=self.timeout, headers=headers)
                return response.status_code == 200
            except Exception as e:
                _log.debug(f"Connection test failed: {e}")
                return False
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information and status"""
        with self._lock:
            try:
                self._rate_limit()
                url = self._build_url("/api/info")
                headers = self._get_auth_headers()
                
                response = self.session.get(url, timeout=self.timeout, headers=headers)
                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Server returned status {response.status_code}"}
            except Exception as e:
                return {"error": f"Failed to get server info: {e}"}
    
    def validate_jwt_token(self) -> Dict[str, Any]:
        """Validate JWT token if configured"""
        if not self.jwt_token or self.auth_type not in ["jwt", "bearer"]:
            return {"valid": False, "error": "No JWT token configured"}
        
        try:
            self._rate_limit()
            url = self._build_url("/api/auth/validate")
            headers = self._get_auth_headers()
            
            response = self.session.post(url, timeout=self.timeout, headers=headers)
            if response.status_code == 200:
                return {"valid": True, "data": response.json()}
            else:
                return {"valid": False, "error": f"Validation failed: {response.status_code}"}
        except Exception as e:
            return {"valid": False, "error": f"Validation error: {e}"}
    
    def refresh_jwt_token(self) -> bool:
        """Attempt to refresh JWT token"""
        if not self.jwt_token or self.auth_type not in ["jwt", "bearer"]:
            return False
        
        try:
            self._rate_limit()
            url = self._build_url("/api/auth/refresh")
            headers = self._get_auth_headers()
            
            response = self.session.post(url, timeout=self.timeout, headers=headers)
            if response.status_code == 200:
                data = response.json()
                if 'token' in data:
                    self.jwt_token = data['token']
                    self._setup_headers()
                    _log.info("JWT token refreshed successfully")
                    return True
            return False
        except Exception as e:
            _log.error(f"Failed to refresh JWT token: {e}")
            return False
    
    def close(self):
        """Close the session and cleanup resources"""
        try:
            if self.session:
                self.session.close()
                _log.debug("Inventory fetcher session closed")
        except Exception as e:
            _log.error(f"Error closing inventory fetcher session: {e}")