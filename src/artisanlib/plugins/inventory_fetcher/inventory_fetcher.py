import requests
import json
import logging
from typing import Dict, List, Optional, Any

_log = logging.getLogger(__name__)

class InventoryFetcher:
    """Fetches beans data from external server"""
    
    def __init__(self, server_url: str, api_key: Optional[str] = None, timeout: int = 30):
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.session = requests.Session()
        
        # Set up headers
        headers = {'Content-Type': 'application/json'}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        self.session.headers.update(headers)
    
    def fetch_beans(self) -> List[Dict[str, Any]]:
        """Fetch all beans from server"""
        try:
            # Build URL with API key as query parameter
            url = f"{self.server_url}/api/inventory"
            params = {}
            
            # Add API key as query parameter if provided
            if self.api_key:
                params['api_key'] = self.api_key
            
            _log.info(f"Fetching beans from: {url}")
            _log.debug(f"API key provided: {bool(self.api_key)}")
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            _log.info(f"Successfully fetched {len(data.get('data', []))} beans")
            return data.get('data', [])
            
        except requests.exceptions.RequestException as e:
            _log.error(f"Failed to fetch beans: {e}")
            raise Exception(f"Failed to fetch beans: {e}")
    
    def fetch_bean_details(self, bean_id: str) -> Dict[str, Any]:
        """Fetch specific bean details"""
        try:
            # Build URL with API key as query parameter
            url = f"{self.server_url}/api/inventory/{bean_id}"
            params = {}
            
            # Add API key as query parameter if provided
            if self.api_key:
                params['api_key'] = self.api_key
            
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            return data.get('data', {})
            
        except requests.exceptions.RequestException as e:
            _log.error(f"Failed to fetch bean details: {e}")
            raise Exception(f"Failed to fetch bean details: {e}")
    
    def test_connection(self) -> bool:
        """Test connection to server"""
        try:
            response = self.session.get(f"{self.server_url}/api/health", timeout=self.timeout)
            return response.status_code == 200
        except:
            return False