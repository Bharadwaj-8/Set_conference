# src/monitors/carbon_monitor.py
"""
Carbon intensity monitoring
"""

import os
import time
import logging
import random
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from .base_monitor import BaseMonitor

logger = logging.getLogger(__name__)


class CarbonMonitor(BaseMonitor, ABC):
    """Abstract carbon monitor"""

    def __init__(self):
        super().__init__("carbon")
        self.cache_ttl = 300  # Carbon data expires in 5 minutes

    @abstractmethod
    def _get_raw_carbon_info(self, zone: str = "IN") -> Dict[str, Any]:
        """Get raw carbon information"""
        pass

    def get_info(self, zone: str = "IN") -> Dict[str, Any]:
        """Get carbon information with standardized format"""
        try:
            raw_info = self._get_raw_carbon_info(zone)

            # Standardize output
            info = {
                "intensity": raw_info.get("intensity", 0.0),
                "is_green": raw_info.get("is_green", False),
                "zone": raw_info.get("zone", zone),
                "source": raw_info.get("source", "unknown"),
                "timestamp": time.time(),
                "raw_data": raw_info
            }

            logger.debug(f"Carbon info: {info['intensity']} gCO2/kWh, "
                         f"Green: {info['is_green']}, Zone: {info['zone']}")

            return info

        except Exception as e:
            logger.error(f"Failed to get carbon info: {e}")
            return self._get_fallback_info(zone)

    def _get_fallback_info(self, zone: str = "IN") -> Dict[str, Any]:
        """Get fallback carbon information"""
        return {
            "intensity": 400.0,
            "is_green": False,
            "zone": zone,
            "source": "fallback",
            "timestamp": time.time(),
            "note": "Using fallback carbon data"
        }

    def _is_green_grid(self, intensity: float, threshold: float = 300.0) -> bool:
        """Determine if grid is green based on intensity threshold"""
        return intensity <= threshold


class ElectricityMapsMonitor(CarbonMonitor):
    """Carbon monitor using Electricity Maps API"""

    def __init__(self, api_key: Optional[str] = None):
        super().__init__()
        self.api_key = api_key or os.getenv("ELECTRICITY_MAPS_API_KEY")
        self.base_url = "https://api.electricitymap.org/v3"

    def is_available(self) -> bool:
        return self.api_key is not None

    def _get_raw_carbon_info(self, zone: str = "IN") -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("No Electricity Maps API key provided")

        try:
            import requests

            url = f"{self.base_url}/carbon-intensity/latest"
            headers = {"auth-token": self.api_key}
            params = {"zone": zone}

            logger.info(f"Fetching carbon intensity for zone {zone}...")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            intensity = data.get("carbonIntensity", 0)
            is_green = self._is_green_grid(intensity)

            return {
                "intensity": intensity,
                "is_green": is_green,
                "zone": zone,
                "source": "electricity_maps",
                "api_response": data
            }

        except Exception as e:
            logger.error(f"Electricity Maps API request failed: {e}")
            raise


class SimulatedCarbonMonitor(CarbonMonitor):
    """Simulated carbon monitor for testing"""

    def __init__(self):
        super().__init__()
        self.zone_intensities = {
            # Realistic carbon intensities by zone (gCO2/kWh)
            "IN": 650,  # India - high carbon
            "US-CAL": 250,  # California - relatively green
            "DE": 350,  # Germany
            "FR": 50,  # France (nuclear)
            "SE": 30,  # Sweden (renewables)
            "CN": 700,  # China
            "GB": 200,  # UK
        }
        self.last_update = time.time()

    def is_available(self) -> bool:
        return True

    def _get_raw_carbon_info(self, zone: str = "IN") -> Dict[str, Any]:
        current_time = time.time()

        # Get base intensity for zone
        base_intensity = self.zone_intensities.get(zone, 400)

        # Simulate daily variation (lower at night, higher during day)
        hour_of_day = (current_time % 86400) / 3600  # 0-23

        # Peak around 2 PM, low around 4 AM
        daily_variation = 0.3 * base_intensity * (1 - abs(hour_of_day - 14) / 14)
        if hour_of_day < 4 or hour_of_day > 20:
            daily_variation *= -0.5  # Lower at night

        # Add random variation
        random_variation = random.uniform(-0.1, 0.1) * base_intensity

        # Calculate final intensity
        intensity = base_intensity + daily_variation + random_variation
        intensity = max(10, intensity)  # Never below 10

        is_green = self._is_green_grid(intensity)

        return {
            "intensity": round(intensity, 1),
            "is_green": is_green,
            "zone": zone,
            "source": "simulation",
            "note": "Using simulated carbon data for demonstration",
            "simulation_params": {
                "base_intensity": base_intensity,
                "daily_variation": round(daily_variation, 1),
                "hour_of_day": round(hour_of_day, 1)
            }
        }