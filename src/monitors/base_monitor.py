# src/monitors/base_monitor.py
"""
Abstract base class for all monitors
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseMonitor(ABC):
    """Abstract base class for all system monitors"""

    def __init__(self, name: str):
        self.name = name
        self.last_update_time = 0
        self.cache_ttl = 300  # 5 minutes default cache TTL
        self.cache = {}

    @abstractmethod
    def is_available(self) -> bool:
        """Check if monitor is available on this system"""
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Get monitored information"""
        pass

    def get_cached_info(self) -> Dict[str, Any]:
        """Get cached information if available and fresh"""
        import time
        current_time = time.time()

        if (self.cache and
                current_time - self.last_update_time < self.cache_ttl):
            logger.debug(f"Using cached data for {self.name}")
            return self.cache

        # Get fresh data
        info = self.get_info()
        self.cache = info
        self.last_update_time = current_time

        return info

    def refresh(self):
        """Force refresh of cached data"""
        self.cache = {}
        return self.get_info()

    def set_cache_ttl(self, ttl: int):
        """Set cache time-to-live in seconds"""
        self.cache_ttl = ttl

    def __str__(self):
        return f"{self.name}Monitor({self.__class__.__name__})"

    def __repr__(self):
        return f"<{self.__class__.__name__} name='{self.name}'>"