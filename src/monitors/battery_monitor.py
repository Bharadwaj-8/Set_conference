# src/monitors/battery_monitor.py
"""
Cross-platform battery monitoring
"""

import os
import re
import subprocess
import logging
import time
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import platform
import random

from .base_monitor import BaseMonitor

logger = logging.getLogger(__name__)


class BatteryMonitor(BaseMonitor, ABC):
    """Abstract battery monitor"""

    def __init__(self):
        super().__init__("battery")

    @abstractmethod
    def _get_raw_battery_info(self) -> Dict[str, Any]:
        """Get raw battery information (platform-specific)"""
        pass

    def get_info(self) -> Dict[str, Any]:
        """Get battery information with standardized format"""
        try:
            raw_info = self._get_raw_battery_info()

            # Standardize output
            info = {
                "percentage": raw_info.get("percentage", 0.0),
                "is_charging": raw_info.get("is_charging", False),
                "status": raw_info.get("status", "unknown"),
                "source": raw_info.get("source", "unknown"),
                "timestamp": time.time(),
                "raw_data": raw_info
            }

            # Ensure percentage is float between 0-100
            info["percentage"] = max(0.0, min(100.0, float(info["percentage"])))

            logger.debug(f"Battery info: {info['percentage']}% "
                         f"(Charging: {info['is_charging']})")

            return info

        except Exception as e:
            logger.error(f"Failed to get battery info: {e}")
            return self._get_fallback_info()

    def _get_fallback_info(self) -> Dict[str, Any]:
        """Get fallback battery information"""
        return {
            "percentage": 85.0,
            "is_charging": True,
            "status": "fallback",
            "source": "fallback",
            "timestamp": time.time(),
            "note": "Using fallback battery data"
        }


class MacOSBatteryMonitor(BatteryMonitor):
    """macOS battery monitor using pmset"""

    def is_available(self) -> bool:
        return platform.system() == "Darwin"

    def _get_raw_battery_info(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["pmset", "-g", "batt"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )

            output = result.stdout

            # Parse macOS pmset output
            percentage = 100.0
            is_charging = False
            status = "unknown"

            for line in output.split('\n'):
                if 'InternalBattery' in line or 'Battery' in line:
                    # Example: " -InternalBattery-0 (id=1234567)	67%; charging;"
                    parts = line.split('\t')
                    if len(parts) > 1:
                        battery_str = parts[1]

                        # Extract percentage
                        match = re.search(r'(\d+)%', battery_str)
                        if match:
                            percentage = float(match.group(1))

                        # Check charging status
                        if 'charging' in battery_str.lower():
                            is_charging = True
                            status = "charging"
                        elif 'discharging' in battery_str.lower():
                            is_charging = False
                            status = "discharging"
                        elif 'charged' in battery_str.lower() or 'full' in battery_str.lower():
                            is_charging = True
                            status = "full"
                        else:
                            status = "unknown"

            return {
                "percentage": percentage,
                "is_charging": is_charging,
                "status": status,
                "source": "macos_pmset",
                "raw_output": output.strip()
            }

        except (subprocess.SubprocessError, TimeoutError, ValueError) as e:
            logger.error(f"Failed to parse macOS battery info: {e}")
            raise


class LinuxBatteryMonitor(BatteryMonitor):
    """Linux battery monitor using sysfs/proc"""

    def is_available(self) -> bool:
        if platform.system() != "Linux":
            return False

        # Check for battery in sysfs
        battery_paths = [
            "/sys/class/power_supply/BAT0",
            "/sys/class/power_supply/BAT1",
            "/sys/class/power_supply/BAT2",
            "/proc/acpi/battery/BAT0",
            "/proc/acpi/battery/BAT1"
        ]

        for path in battery_paths:
            if os.path.exists(path):
                return True

        return False

    def _get_raw_battery_info(self) -> Dict[str, Any]:
        # Try sysfs first
        info = self._read_from_sysfs()
        if info["percentage"] >= 0:
            return info

        # Try /proc/acpi
        info = self._read_from_proc_acpi()
        if info["percentage"] >= 0:
            return info

        raise RuntimeError("Could not read Linux battery info from any source")

    def _read_from_sysfs(self) -> Dict[str, Any]:
        """Read battery info from sysfs"""
        base_paths = [
            "/sys/class/power_supply/BAT0",
            "/sys/class/power_supply/BAT1",
            "/sys/class/power_supply/BAT2"
        ]

        for base_path in base_paths:
            if not os.path.exists(base_path):
                continue

            try:
                capacity_file = os.path.join(base_path, "capacity")
                status_file = os.path.join(base_path, "status")
                present_file = os.path.join(base_path, "present")

                # Check if battery is present
                if os.path.exists(present_file):
                    with open(present_file, "r") as f:
                        if f.read().strip() != "1":
                            continue

                if os.path.exists(capacity_file):
                    with open(capacity_file, "r") as f:
                        percentage = float(f.read().strip())

                    status = "unknown"
                    if os.path.exists(status_file):
                        with open(status_file, "r") as f:
                            raw_status = f.read().strip().lower()
                            status = raw_status
                            is_charging = raw_status in ["charging", "full"]

                    return {
                        "percentage": percentage,
                        "is_charging": is_charging,
                        "status": status,
                        "source": f"sysfs_{os.path.basename(base_path)}",
                        "path": base_path
                    }

            except (IOError, ValueError) as e:
                logger.debug(f"Failed to read sysfs battery info from {base_path}: {e}")
                continue

        return {"percentage": -1, "is_charging": False}

    def _read_from_proc_acpi(self) -> Dict[str, Any]:
        """Read battery info from /proc/acpi"""
        base_paths = [
            "/proc/acpi/battery/BAT0",
            "/proc/acpi/battery/BAT1"
        ]

        for base_path in base_paths:
            if not os.path.exists(base_path):
                continue

            try:
                state_file = os.path.join(base_path, "state")
                info_file = os.path.join(base_path, "info")

                if os.path.exists(state_file) and os.path.exists(info_file):
                    # Read state file
                    with open(state_file, "r") as f:
                        state_content = f.read()

                    # Extract percentage
                    percentage_match = re.search(r'remaining capacity:\s*(\d+)', state_content, re.IGNORECASE)
                    percentage = float(percentage_match.group(1)) if percentage_match else 0

                    # Extract status
                    status_match = re.search(r'charging state:\s*(\w+)', state_content, re.IGNORECASE)
                    status = status_match.group(1).lower() if status_match else "unknown"
                    is_charging = status in ["charging", "charged", "full"]

                    return {
                        "percentage": percentage,
                        "is_charging": is_charging,
                        "status": status,
                        "source": f"proc_acpi_{os.path.basename(base_path)}",
                        "path": base_path
                    }

            except (IOError, ValueError, AttributeError) as e:
                logger.debug(f"Failed to read proc acpi battery info from {base_path}: {e}")
                continue

        return {"percentage": -1, "is_charging": False}


class WindowsBatteryMonitor(BatteryMonitor):
    """Windows battery monitor using WMI"""

    def is_available(self) -> bool:
        return platform.system() == "Windows"

    def _get_raw_battery_info(self) -> Dict[str, Any]:
        try:
            # Use WMI through PowerShell
            cmd = [
                "powershell",
                "-Command",
                "$battery = Get-WmiObject -Class Win32_Battery; "
                "if ($battery) { "
                "  $battery | Select-Object -Property "
                "  @{Name='Percentage';Expression={$_.EstimatedChargeRemaining}}, "
                "  @{Name='Status';Expression={$_.BatteryStatus}}, "
                "  DeviceID, "
                "  @{Name='IsCharging';Expression={$_.BatteryStatus -in @(2,3)}} | "
                "  ConvertTo-Json -Compress"
                "} else { 'null' }"
            ]

            creation_flags = 0
            if hasattr(subprocess, 'CREATE_NO_WINDOW'):
                creation_flags = subprocess.CREATE_NO_WINDOW

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
                creationflags=creation_flags
            )

            output = result.stdout.strip()

            if output == "null" or not output:
                logger.warning("No battery found on Windows")
                raise RuntimeError("No battery detected")

            # Parse JSON output
            import json
            data = json.loads(output)

            if isinstance(data, list) and len(data) > 0:
                battery = data[0]
            else:
                battery = data

            percentage = battery.get("Percentage", 0)
            status_code = battery.get("Status", 1)

            # BatteryStatus codes:
            # 1=Discharging, 2=AC Power, 3=Fully Charged, 4=Low, 5=Critical, 6=Charging
            status_map = {
                1: "discharging",
                2: "ac_power",
                3: "fully_charged",
                4: "low",
                5: "critical",
                6: "charging"
            }

            status = status_map.get(status_code, "unknown")
            is_charging = status_code in [2, 3, 6]  # AC Power, Fully Charged, or Charging

            return {
                "percentage": float(percentage),
                "is_charging": is_charging,
                "status": status,
                "status_code": status_code,
                "source": "windows_wmi",
                "device_id": battery.get("DeviceID", "unknown")
            }

        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError, TimeoutError) as e:
            logger.error(f"Failed to get Windows battery info: {e}")
            raise


class UniversalBatteryMonitor(BatteryMonitor):
    """
    Universal battery monitor that tries all platform-specific monitors
    Falls back to simulation if none work
    """

    def __init__(self):
        super().__init__()
        self.platform_monitors = []
        self.current_monitor = None
        self._initialize_monitors()

    def _initialize_monitors(self):
        """Initialize platform-specific monitors"""
        system = platform.system()

        if system == "Darwin":
            self.platform_monitors.append(MacOSBatteryMonitor())
        elif system == "Linux":
            self.platform_monitors.append(LinuxBatteryMonitor())
        elif system == "Windows":
            self.platform_monitors.append(WindowsBatteryMonitor())

        # Always try simulation as last resort
        self.platform_monitors.append(SimulatedBatteryMonitor())

    def is_available(self) -> bool:
        """Check if any monitor is available"""
        for monitor in self.platform_monitors:
            if monitor.is_available():
                self.current_monitor = monitor
                return True
        return False

    def _get_raw_battery_info(self) -> Dict[str, Any]:
        """Get battery info from the first available monitor"""
        if not self.current_monitor:
            if not self.is_available():
                return SimulatedBatteryMonitor()._get_raw_battery_info()

        try:
            return self.current_monitor._get_raw_battery_info()
        except Exception as e:
            logger.error(f"Current monitor failed: {e}")

            # Try other monitors
            for monitor in self.platform_monitors:
                if monitor != self.current_monitor and monitor.is_available():
                    try:
                        self.current_monitor = monitor
                        return monitor._get_raw_battery_info()
                    except Exception:
                        continue

            # All monitors failed, use simulation
            return SimulatedBatteryMonitor()._get_raw_battery_info()


class SimulatedBatteryMonitor(BatteryMonitor):
    """Simulated battery monitor for testing and fallback"""

    def __init__(self, initial_percentage: float = 85.0):
        super().__init__()
        self.percentage = initial_percentage
        self.is_charging = True
        self.discharge_rate = 0.05  # Percentage per call when discharging
        self.charge_rate = 0.5  # Percentage per call when charging
        self.last_update = time.time()

    def is_available(self) -> bool:
        return True  # Always available

    def _get_raw_battery_info(self) -> Dict[str, Any]:
        current_time = time.time()
        time_delta = current_time - self.last_update

        # Simulate battery drain/charge over time
        if self.is_charging:
            charge_amount = self.charge_rate * (time_delta / 60)  # Per minute
            self.percentage = min(100, self.percentage + charge_amount)

            # Stop charging when full
            if self.percentage >= 99.9:
                self.is_charging = False
                self.percentage = 100.0
        else:
            discharge_amount = self.discharge_rate * (time_delta / 60)  # Per minute
            self.percentage = max(0, self.percentage - discharge_amount)

            # Start charging when low
            if self.percentage <= 20:
                self.is_charging = True

        # Randomly change charging status for simulation (5% chance)
        if random.random() < 0.05:
            self.is_charging = not self.is_charging

        self.last_update = current_time

        status = "charging" if self.is_charging else "discharging"
        if self.percentage >= 99.9:
            status = "full"
        elif self.percentage <= 5:
            status = "critical"

        return {
            "percentage": round(self.percentage, 1),
            "is_charging": self.is_charging,
            "status": status,
            "source": "simulation",
            "note": "Using simulated battery data for demonstration",
            "simulation_params": {
                "discharge_rate": self.discharge_rate,
                "charge_rate": self.charge_rate
            }
        }