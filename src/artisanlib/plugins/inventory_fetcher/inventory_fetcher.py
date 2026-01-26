import requests
import json
import logging
import time
from typing import Dict, List, Optional, Any
from threading import Lock
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_log = logging.getLogger(__name__)


class InventoryFetcher:
    """Fetches beans data from external server via Gateway with authentication and thread safety"""
    def __init__(self, config, auth_manager=None):
        self.config = config
        self.auth_manager = auth_manager
        
        # Use defaults
        self.timeout = 30
        self.use_ssl = True
        self.validate_ssl_cert = True

        self.session = requests.Session()

        adapter = HTTPAdapter(
            pool_connections=1,
            pool_maxsize=1,
            max_retries=Retry(total=3, backoff_factor=0.3, status_forcelist=[500, 502, 504]),
        )

        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        if not self.validate_ssl_cert:
            self.session.verify = False
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Thread safety
        self._lock = Lock()
        self._last_request_time = 0
        self._min_request_interval = 0.1  # Minimum 100ms between requests
        self._closed = False

        _log.debug("InventoryFetcher initialized with connection pooling")

    def _rate_limit(self):
        """Rate limiting to prevent overwhelming the server"""
        if self._closed:
            raise Exception("Fetcher is closed")

        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            time.sleep(self._min_request_interval - time_since_last)
        self._last_request_time = time.time()

    def _build_url(self, endpoint: str) -> str:
        """Build full URL with proper protocol"""
        if self._closed:
            raise Exception("Fetcher is closed")

        base_url = self.config.get_effective_url()

        # Check if base_url already has a protocol
        if base_url.startswith(("http://", "https://")):
            # Base URL already has protocol, just add endpoint
            return f"{base_url.rstrip('/')}{endpoint}"
        else:
            # No protocol specified, add default
            protocol = "https" if self.use_ssl else "http"
            return f"{protocol}://{base_url.rstrip('/')}{endpoint}"


    def fetch_beans(self, limit: int = 1000, offset: int = 0) -> Dict[str, Any]:
        """Fetch beans from server with pagination and thread safety"""
        if self._closed:
            raise Exception("Fetcher is closed")

        with self._lock:
            try:
                self._rate_limit()

                # # Build URL
                # url = self._build_url("/api/inventory/available/artisan")
                # params = {"limit": limit, "offset": offset}
                # Build URL using configurable endpoint
                inventory_endpoint = self.config.inventory_endpoint or "/api/inventory/available/artisan"
                url = self._build_url(inventory_endpoint)
                params = {"limit": limit, "offset": offset}

                _log.info(f"Fetching beans from: {url} (limit: {limit}, offset: {offset})")
                _log.debug(f"Fetching from gateway: {self.config.gateway_url}")

                headers = self._get_auth_headers()
                
                _log.info("=== INVENTORY FETCHER REQUEST DEBUG ===")
                _log.info(f"Request URL: {url}")
                _log.info(f"Request method: GET")
                _log.info(f"Request params: {params}")
                _log.info(f"Request headers: {headers}")
                _log.info(f"Auth manager available: {self.auth_manager is not None}")
                if self.auth_manager:
                    _log.info(f"Auth manager authenticated: {self.auth_manager.is_authenticated()}")
                    token_info = self.auth_manager.get_token_info()
                    _log.info(f"Token info: {token_info}")
                _log.info("=======================================")
                
                response = requests.get(url, params=params, headers=headers, timeout=self.timeout)

                _log.info("=== INVENTORY FETCHER REQUEST DEBUG ===")
                _log.info(f"Request URL: {url}")
                _log.info(f"Request method: GET")
                _log.info(f"Request params: {params}")
                _log.info(f"Request headers: {headers}")
                
                if 'Authorization' in headers:
                    auth_header = headers['Authorization']
                    _log.info(f"Authorization header being sent: {auth_header[:50]}...")
                else:
                    _log.warning("No Authorization header in request headers!")
                
                _log.info(f"Auth manager available: {self.auth_manager is not None}")
                if self.auth_manager:
                    _log.info(f"Auth manager authenticated: {self.auth_manager.is_authenticated()}")
                    token_info = self.auth_manager.get_token_info()
                    _log.info(f"Token info: {token_info}")
                _log.info("=======================================")
                
                _log.info("========================================")
                
                if response.status_code == 401:
                    _log.warning("Authentication failed - token may be expired")
                    try:
                        error_data = response.json()
                        _log.warning(f"401 Error details: {error_data}")
                    except:
                        _log.warning(f"401 Error response: {response.text}")
                    return {"error": "Authentication failed", "status_code": 401}

                response.raise_for_status()

                data = response.json()
                beans = data.get("data", [])
                total_count = data.get("total", len(beans))

                _log.info(f"Successfully fetched {len(beans)} beans (total available: {total_count})")
                return {
                    "data": beans,
                    "total": total_count,
                    "limit": limit,
                    "offset": offset,
                    "has_more": offset + limit < total_count,
                }

            except requests.exceptions.RequestException as e:
                _log.error(f"Failed to fetch beans: {e}")
                raise Exception(f"Failed to fetch beans: {e}")

    def fetch_all_beans(self, batch_size: int = 1000) -> List[Dict[str, Any]]:
        """Fetch all beans using pagination with progress tracking"""
        if self._closed:
            raise Exception("Fetcher is closed")

        all_beans = []
        offset = 0

        try:
            # Get first batch to determine total count
            first_result = self.fetch_beans(limit=batch_size, offset=0)
            total_count = first_result["total"]
            all_beans.extend(first_result["data"])

            _log.info(f"Starting batch fetch: {total_count} total beans, batch size: {batch_size}")

            # Continue fetching remaining batches
            while first_result["has_more"]:
                offset += batch_size
                result = self.fetch_beans(limit=batch_size, offset=offset)
                beans = result["data"]
                all_beans.extend(beans)

                _log.info(
                    f"Fetched batch {len(beans)} beans, total so far: {len(all_beans)}/{total_count}"
                )

                if not result["has_more"]:
                    break

            _log.info(f"Completed batch fetch: {len(all_beans)} beans from server")
            return all_beans

        except Exception as e:
            _log.error(f"Error during batch fetch: {e}")
            raise
      

    def fetch_bean_details(self, bean_id: str) -> Dict[str, Any]:
        """Fetch specific bean details with thread safety"""
        if self._closed:
            raise Exception("Fetcher is closed")

        with self._lock:
            try:
                self._rate_limit()

                # Build URL
                if self.config.use_gateway:
                    url = self._build_url(f"/api/inventory/{bean_id}")
                else:
                    url = self._build_url(f"/api/inventory/{bean_id}")

                response = self.session.get(url, timeout=self.timeout)

                response.raise_for_status()

                data = response.json()
                return data.get("data", {})

            except requests.exceptions.RequestException as e:
                _log.error(f"Failed to fetch bean details: {e}")
                raise Exception(f"Failed to fetch bean details: {e}")

    def test_connection(self) -> bool:
        """Test connection to server with thread safety"""
        if self._closed:
            return False

        with self._lock:
            try:
                self._rate_limit()

                # Use config health check URL else default
                health_url = self.config.health_check_url or "/api/inventory/health"
                url = self._build_url(health_url)

                response = self.session.get(url, timeout=self.timeout)

                # auith error handling
                if response.status_code == 401:
                    _log.warning("Authentication failed during connection test")
                    return False

                return response.status_code == 200
            except Exception as e:
                _log.debug(f"Connection test failed: {e}")
                return False

    def get_server_info(self) -> Dict[str, Any]:
        """Get server information and status"""
        if self._closed:
            return {"error": "Fetcher is closed"}

        with self._lock:
            try:
                self._rate_limit()

                if self.config.use_gateway:
                    url = self._build_url("/gateway/routes")
                else:
                    url = self._build_url("/api/info")

                response = self.session.get(url, timeout=self.timeout)

                # auth error handling
                if response.status_code == 401:
                    _log.warning("Authentication failed during connection test")
                    return False

                if response.status_code == 200:
                    return response.json()
                else:
                    return {"error": f"Server returned status {response.status_code}"}
            except Exception as e:
                return {"error": f"Failed to get server info: {e}"}

    def close(self):
        """Close the session and cleanup resources"""
        # Check if object is properly initialized
        if not hasattr(self, '_closed'):
            return
            
        if self._closed:
            return

        try:
            self._closed = True
            if hasattr(self, 'session') and self.session:
                self.session.close()
                _log.debug("Inventory fetcher session closed")
        except Exception as e:
            _log.error(f"Error closing inventory fetcher session: {e}")

    def __del__(self):
        """Destructor to ensure cleanup"""
        try:
            self.close()
        except Exception:
            pass

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    @property
    def is_closed(self) -> bool:
        """Check if fetcher is closed"""
        return self._closed

    def get_connection_info(self) -> Dict[str, Any]:
        """Get connection information without making new connections"""
        if self._closed:
            return {"status": "closed", "message": "Fetcher is closed"}

        try:
            adapter = self.session.get_adapter("http://")
            pool_info = {}
            if adapter:
                pool_info = {
                    "pool_connections": getattr(adapter, "config", {}).get(
                        "pool_connections", "unknown"
                    ),
                    "pool_maxsize": getattr(adapter, "config", {}).get("pool_maxsize", "unknown"),
                    "pool_block": getattr(adapter, "config", {}).get("pool_block", "unknown"),
                }

            return {
                "status": "active",
                "closed": self._closed,
                "session_closed": self.session.closed if hasattr(self.session, "closed") else False,
                "pool_info": pool_info,
                "server_url": self.config.get_effective_url(),
                "auth_type": (
                    self.config.gateway_auth_type
                    if self.config.use_gateway
                    else self.config.auth_type
                ),
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}



    def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers from global auth manager"""
        headers: Dict[str, str] = {}

        _log.debug("=== AUTH HEADERS DEBUG ===")
        _log.debug(f"Auth manager available: {self.auth_manager is not None}")

        if self.auth_manager:
            try:
                # Delegate to GlobalAuthManager so API key vs OAuth is handled correctly
                headers = self.auth_manager.get_auth_headers()
                _log.debug(f"Auth headers from GlobalAuthManager: {headers}")
            except Exception as e:
                _log.error(f"Error getting auth headers from GlobalAuthManager: {e}", exc_info=True)
        else:
            _log.debug("No auth manager available")

        _log.debug(f"Final headers: {headers}")
        _log.debug("==========================")

        return headers

