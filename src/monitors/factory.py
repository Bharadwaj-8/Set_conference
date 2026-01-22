# src/monitors/factory.py
"""
Factory for creating platform-appropriate monitors
"""

import platform
import logging
from typing import Dict, Any, Optional

from .battery_monitor import (
    BatteryMonitor,
    MacOSBatteryMonitor,
    LinuxBatteryMonitor,
    WindowsBatteryMonitor,
    UniversalBatteryMonitor,
    SimulatedBatteryMonitor
)
from .network_monitor import (
    NetworkMonitor,
    SpeedTestMonitor,
    PingMonitor,
    SimulatedNetworkMonitor
)
from .carbon_monitor import (
    CarbonMonitor,
    ElectricityMapsMonitor,
    SimulatedCarbonMonitor
)

logger = logging.getLogger(__name__)


class MonitorFactory:
    """Factory for creating platform-appropriate monitors"""

    @staticmethod
    def create_battery_monitor(
            use_universal: bool = True,
            use_simulation: bool = False
    ) -> BatteryMonitor:
        """
        Create a battery monitor for the current platform

        Args:
            use_universal: Use UniversalBatteryMonitor which auto-detects
            use_simulation: Force use of simulation (for testing)

        Returns:
            BatteryMonitor instance
        """
        if use_simulation:
            logger.info("Creating simulated battery monitor")
            return SimulatedBatteryMonitor()

        if use_universal:
            logger.info("Creating universal battery monitor")
            return UniversalBatteryMonitor()

        system = platform.system()

        if system == "Darwin":
            logger.info("Creating macOS battery monitor")
            return MacOSBatteryMonitor()
        elif system == "Linux":
            logger.info("Creating Linux battery monitor")
            return LinuxBatteryMonitor()
        elif system == "Windows":
            logger.info("Creating Windows battery monitor")
            return WindowsBatteryMonitor()
        else:
            logger.warning(f"Unknown platform {system}, using simulation")
            return SimulatedBatteryMonitor()

    @staticmethod
    def create_network_monitor(
            use_speedtest: bool = True,
            fallback_to_ping: bool = True,
            use_simulation: bool = False
    ) -> NetworkMonitor:
        """
        Create a network monitor

        Args:
            use_speedtest: Use speedtest-cli if available
            fallback_to_ping: Fall back to ping if speedtest fails
            use_simulation: Force use of simulation (for testing)

        Returns:
            NetworkMonitor instance
        """
        if use_simulation:
            logger.info("Creating simulated network monitor")
            return SimulatedNetworkMonitor()

        if use_speedtest:
            try:
                monitor = SpeedTestMonitor()
                if monitor.is_available():
                    logger.info("Creating speedtest network monitor")
                    return monitor
                else:
                    logger.warning("speedtest-cli not available")
            except Exception as e:
                logger.warning(f"Failed to create speedtest monitor: {e}")

        if fallback_to_ping:
            try:
                monitor = PingMonitor()
                logger.info("Creating ping network monitor")
                return monitor
            except Exception as e:
                logger.warning(f"Failed to create ping monitor: {e}")

        logger.warning("No real network monitor available, using simulation")
        return SimulatedNetworkMonitor()

    @staticmethod
    def create_carbon_monitor(
            api_key: Optional[str] = None,
            use_simulation_if_no_key: bool = True,
            zone: str = "IN",
            use_simulation: bool = False
    ) -> CarbonMonitor:
        """
        Create a carbon monitor

        Args:
            api_key: Electricity Maps API key
            use_simulation_if_no_key: Use simulation if no API key
            zone: Carbon zone
            use_simulation: Force use of simulation (for testing)

        Returns:
            CarbonMonitor instance
        """
        if use_simulation:
            logger.info("Creating simulated carbon monitor")
            return SimulatedCarbonMonitor()

        if api_key:
            try:
                monitor = ElectricityMapsMonitor(api_key=api_key)
                if monitor.is_available():
                    logger.info(f"Creating Electricity Maps carbon monitor for zone {zone}")
                    return monitor
                else:
                    logger.warning("Electricity Maps API key invalid")
            except Exception as e:
                logger.warning(f"Failed to create Electricity Maps monitor: {e}")

        if use_simulation_if_no_key:
            logger.info(f"Creating simulated carbon monitor for zone {zone}")
            return SimulatedCarbonMonitor()

        raise ValueError("No API key provided and simulation disabled")

    @staticmethod
    def create_all_monitors(config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create all monitors based on configuration

        Args:
            config: Configuration dictionary

        Returns:
            Dictionary of monitors
        """
        monitors = {}

        # Get API key from environment if not in config
        api_key = config.get("api_keys", {}).get("electricity_maps")
        if not api_key:
            import os
            api_key = os.getenv("ELECTRICITY_MAPS_API_KEY")

        # Battery monitor
        battery_config = config.get("monitors", {}).get("battery", {})
        if battery_config.get("enabled", True):
            monitors["battery"] = MonitorFactory.create_battery_monitor(
                use_universal=battery_config.get("use_universal", True),
                use_simulation=battery_config.get("use_simulation", False)
            )

        # Network monitor
        network_config = config.get("monitors", {}).get("network", {})
        if network_config.get("enabled", True):
            monitors["network"] = MonitorFactory.create_network_monitor(
                use_speedtest=network_config.get("use_speedtest", True),
                fallback_to_ping=network_config.get("fallback_to_ping", True),
                use_simulation=network_config.get("use_simulation", False)
            )

        # Carbon monitor
        carbon_config = config.get("monitors", {}).get("carbon", {})
        if carbon_config.get("enabled", True):
            zone = carbon_config.get("zone", "IN")
            monitors["carbon"] = MonitorFactory.create_carbon_monitor(
                api_key=api_key,
                use_simulation_if_no_key=carbon_config.get("use_simulation", True),
                zone=zone,
                use_simulation=carbon_config.get("use_simulation", False)
            )

        logger.info(f"Created {len(monitors)} monitors: {list(monitors.keys())}")
        return monitors