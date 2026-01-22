# src/monitors/__init__.py
"""
Platform-agnostic monitoring system for the Green AI Orchestrator
"""

from .base_monitor import BaseMonitor
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
from .factory import MonitorFactory

__all__ = [
    "BaseMonitor",
    "BatteryMonitor",
    "MacOSBatteryMonitor",
    "LinuxBatteryMonitor",
    "WindowsBatteryMonitor",
    "UniversalBatteryMonitor",
    "SimulatedBatteryMonitor",
    "NetworkMonitor",
    "SpeedTestMonitor",
    "PingMonitor",
    "SimulatedNetworkMonitor",
    "CarbonMonitor",
    "ElectricityMapsMonitor",
    "SimulatedCarbonMonitor",
    "MonitorFactory",
]