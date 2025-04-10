# /src/plugins/rest_plugin/rest_plugin.py
import json
import logging
from typing import Any, Dict, Optional
import requests
from plus import util, config

# Use Artisan's logging system
_log = logging.getLogger("artisan")

class RoastRESTPlugin:
    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        _log.info("[REST Plugin] Initialized with base_url: %s", base_url)
        
    def get_headers(self) -> Dict[str, str]:
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': f'Artisan'  
        }
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
            _log.debug("[REST Plugin] Authorization header added")
        else:
            _log.warning("[REST Plugin] No API key provided")
        return headers

    def send_roast_data(self, profile_data: Dict[str, Any]) -> bool:
        """Send roast data to REST server"""
        try:
            _log.info("[REST Plugin] Preparing to send roast data")
            
            from plus.roast import getTemplate
            roast_data = getTemplate(profile_data)
            
            # Add computed values
            if 'computed' in profile_data:
                computed = profile_data['computed']
                roast_data['computed'] = {
                    'total_time': computed.get('totaltime', 0),
                    'development_time': computed.get('developmenttime', 0),
                    'development_ratio': computed.get('developmentTimeRatio', 0),
                }
                _log.debug("[REST Plugin] Added computed values: total_time=%s, dev_time=%s, dev_ratio=%s",
                          computed.get('totaltime', 0),
                          computed.get('developmenttime', 0),
                          computed.get('developmentTimeRatio', 0))

            # Add temperature data
            if 'timex' in profile_data and 'temp1' in profile_data:
                roast_data['temperature_curve'] = {
                    'time': profile_data['timex'],
                    'bean_temp': profile_data['temp1'],
                    'environmental_temp': profile_data.get('temp2', [])
                }
                _log.debug("[REST Plugin] Added temperature curve with %d time points", 
                          len(profile_data['timex']))

            endpoint = f"{self.base_url}/roasts"
            _log.info("[REST Plugin] Sending POST request to %s", endpoint)

            response = requests.post(
                endpoint,
                headers=self.get_headers(),
                json=roast_data
            )
            
            if response.status_code in (200, 201):
                _log.info("[REST Plugin] Successfully sent roast data")
                return True
            else:
                _log.error("[REST Plugin] Failed to send roast data. Status: %d, Response: %s", 
                          response.status_code, response.text)
                return False
                
        except Exception as e:
            _log.exception("[REST Plugin] Error sending roast data: %s", str(e))
            return False