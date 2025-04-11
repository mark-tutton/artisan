import logging
import requests
from typing import Dict, Any, Optional
from plus.roast import getTemplate

_log = logging.getLogger("artisan")

class RESTClient:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        _log.info("[REST Plugin] Initialized with base_url: %s", base_url)
    
    def get_headers(self) -> Dict[str, str]:
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Artisan'
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers
    
    def send_roast_data(self, profile_data: Dict[str, Any]) -> bool:
        try:
            roast_data = getTemplate(profile_data)
            
            if 'computed' in profile_data:
                computed = profile_data['computed']
                roast_data['computed'] = {
                    'total_time': computed.get('totaltime', 0),
                    'development_time': computed.get('developmenttime', 0),
                    'development_ratio': computed.get('developmentTimeRatio', 0),
                }
            
            if 'timex' in profile_data and 'temp1' in profile_data:
                roast_data['temperature_curve'] = {
                    'time': profile_data['timex'],
                    'bean_temp': profile_data['temp1'],
                    'environmental_temp': profile_data.get('temp2', [])
                }
            
            response = requests.post(
                f"{self.base_url}/roasts",
                headers=self.get_headers(),
                json=roast_data
            )
            
            return response.status_code in (200, 201)
                
        except Exception as e:
            _log.exception("[REST Plugin] Error sending roast data: %s", str(e))
            return False
            
    def test_connection(self) -> bool:
        try:
            response = requests.get(
                f"{self.base_url}/health",
                headers=self.get_headers()
            )
            return response.status_code == 200
        except Exception as e:
            _log.exception("[REST Plugin] Connection test failed: %s", str(e))
            return False