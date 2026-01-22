# src/monitors/network_monitor.py
"""
Network monitoring with cross-platform support
"""

import subprocess
import socket
import time
import logging
import platform
from typing import Dict, Any, Optional, Tuple
from abc import ABC, abstractmethod
import random

from .base_monitor import BaseMonitor

logger = logging.getLogger(__name__)


class NetworkMonitor(BaseMonitor, ABC):
    """Abstract network monitor"""

    def __init__(self):
        super().__init__("network")
        self.cache_ttl = 60  # Network data expires faster (1 minute)

    @abstractmethod
    def _get_raw_network_info(self) -> Dict[str, Any]:
        """Get raw network information (platform-specific)"""
        pass

    def get_info(self) -> Dict[str, Any]:
        """Get network information with standardized format"""
        try:
            raw_info = self._get_raw_network_info()

            # Standardize output
            info = {
                "speed_mbps": raw_info.get("speed_mbps", 0.0),
                "latency_ms": raw_info.get("latency_ms", 0.0),
                "quality": raw_info.get("quality", 0.0),
                "connected": raw_info.get("connected", False),
                "source": raw_info.get("source", "unknown"),
                "timestamp": time.time(),
                "raw_data": raw_info
            }

            # Normalize quality to 0-1
            info["quality"] = max(0.0, min(1.0, info["quality"]))

            logger.debug(f"Network info: {info['speed_mbps']:.1f} Mbps, "
                         f"Latency: {info['latency_ms']:.0f}ms, "
                         f"Quality: {info['quality']:.2f}")

            return info

        except Exception as e:
            logger.error(f"Failed to get network info: {e}")
            return self._get_fallback_info()

    def _get_fallback_info(self) -> Dict[str, Any]:
        """Get fallback network information"""
        return {
            "speed_mbps": 10.0,
            "latency_ms": 100.0,
            "quality": 0.5,
            "connected": True,
            "source": "fallback",
            "timestamp": time.time(),
            "note": "Using fallback network data"
        }

    def _calculate_quality(self, speed_mbps: float, latency_ms: float) -> float:
        """Calculate network quality score (0-1)"""
        # Normalize speed (0-200 Mbps -> 0-1)
        speed_score = min(1.0, speed_mbps / 200.0)

        # Normalize latency (0-500ms -> 1-0, inverted)
        latency_score = max(0.0, 1.0 - (latency_ms / 500.0))

        # Weighted combination (70% speed, 30% latency)
        quality = (0.7 * speed_score) + (0.3 * latency_score)

        return max(0.0, min(1.0, quality))


class SpeedTestMonitor(NetworkMonitor):
    """Network monitor using speedtest-cli"""

    def __init__(self):
        super().__init__()
        self.speedtest_available = False
        self._check_speedtest_availability()

    def _check_speedtest_availability(self):
        """Check if speedtest-cli is available"""
        try:
            import speedtest
            self.speedtest_available = True
        except ImportError:
            logger.warning("speedtest-cli not installed")
            self.speedtest_available = False

    def is_available(self) -> bool:
        return self.speedtest_available

    def _get_raw_network_info(self) -> Dict[str, Any]:
        if not self.speedtest_available:
            raise RuntimeError("speedtest-cli not available")

        try:
            import speedtest

            logger.info("Running speed test...")
            st = speedtest.Speedtest()
            st.get_best_server()

            # Test download speed
            download_speed = st.download() / 1_000_000  # Convert to Mbps

            # Test upload speed (optional)
            upload_speed = st.upload() / 1_000_000  # Convert to Mbps

            # Get latency from server
            latency = st.results.ping

            # Check connectivity
            connected = download_speed > 0.1  # At least 0.1 Mbps

            # Calculate quality
            quality = self._calculate_quality(download_speed, latency)

            return {
                "speed_mbps": round(download_speed, 1),
                "upload_mbps": round(upload_speed, 1),
                "latency_ms": round(latency, 1),
                "quality": round(quality, 3),
                "connected": connected,
                "source": "speedtest",
                "server": st.results.server.get("name", "unknown"),
                "server_country": st.results.server.get("country", "unknown")
            }

        except Exception as e:
            logger.error(f"Speed test failed: {e}")
            raise


class PingMonitor(NetworkMonitor):
    """Network monitor using ping"""

    def __init__(self):
        super().__init__()
        self.ping_hosts = [
            "8.8.8.8",  # Google DNS
            "1.1.1.1",  # Cloudflare DNS
            "208.67.222.222"  # OpenDNS
        ]

    def is_available(self) -> bool:
        # Ping should be available on all platforms
        return True

    def _get_raw_network_info(self) -> Dict[str, Any]:
        # Try multiple hosts
        for host in self.ping_hosts:
            try:
                latency = self._ping_host(host)
                if latency > 0:
                    # Estimate speed based on latency (rough approximation)
                    # Good latency (<50ms) -> good speed (>50 Mbps)
                    # Poor latency (>200ms) -> poor speed (<10 Mbps)
                    if latency < 50:
                        estimated_speed = 50 + random.uniform(0, 50)  # 50-100 Mbps
                    elif latency < 100:
                        estimated_speed = 20 + random.uniform(0, 30)  # 20-50 Mbps
                    elif latency < 200:
                        estimated_speed = 5 + random.uniform(0, 15)  # 5-20 Mbps
                    else:
                        estimated_speed = 1 + random.uniform(0, 4)  # 1-5 Mbps

                    quality = self._calculate_quality(estimated_speed, latency)

                    return {
                        "speed_mbps": round(estimated_speed, 1),
                        "latency_ms": round(latency, 1),
                        "quality": round(quality, 3),
                        "connected": True,
                        "source": f"ping_{host}",
                        "ping_host": host,
                        "note": "Speed estimated from latency"
                    }

            except Exception as e:
                logger.debug(f"Ping to {host} failed: {e}")
                continue

        # All pings failed
        raise RuntimeError("All ping attempts failed")

    def _ping_host(self, host: str) -> float:
        """Ping a host and return latency in milliseconds"""
        system = platform.system().lower()

        # Build ping command
        if system == "windows":
            cmd = ["ping", "-n", "4", "-w", "1000", host]
        else:  # Linux, macOS, etc.
            cmd = ["ping", "-c", "4", "-W", "1", host]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )

            output = result.stdout

            # Parse ping output for latency
            if system == "windows":
                # Windows output: "Minimum = 15ms, Maximum = 20ms, Average = 17ms"
                match = re.search(r'Average = (\d+)ms', output)
            else:
                # Linux/macOS output: "rtt min/avg/max/mdev = 15.123/17.456/20.789/2.123 ms"
                match = re.search(r'= [\d.]+\/([\d.]+)\/', output)

            if match:
                latency = float(match.group(1))
                return latency
            else:
                raise RuntimeError("Could not parse ping output")

        except (subprocess.SubprocessError, TimeoutError, ValueError) as e:
            logger.debug(f"Ping command failed: {e}")
            raise


class SimulatedNetworkMonitor(NetworkMonitor):
    """Simulated network monitor for testing"""

    def __init__(self):
        super().__init__()
        self.base_speed = 50.0
        self.base_latency = 30.0
        self.last_update = time.time()

    def is_available(self) -> bool:
        return True

    def _get_raw_network_info(self) -> Dict[str, Any]:
        current_time = time.time()
        time_delta = current_time - self.last_update

        # Simulate network variations
        # Add some random variation
        speed_variation = random.uniform(-10, 10)
        latency_variation = random.uniform(-5, 5)

        # Simulate periodic slowdowns (every ~5 minutes in simulation time)
        if int(current_time) % 300 < 30:  # 30 seconds out of every 300
            speed_variation -= 30
            latency_variation += 50

        speed = max(0.1, self.base_speed + speed_variation)
        latency = max(1.0, self.base_latency + latency_variation)

        # Occasionally simulate disconnection (5% chance)
        connected = random.random() > 0.05

        if not connected:
            speed = 0.0
            latency = 1000.0

        quality = self._calculate_quality(speed, latency)

        self.last_update = current_time

        return {
            "speed_mbps": round(speed, 1),
            "latency_ms": round(latency, 1),
            "quality": round(quality, 3),
            "connected": connected,
            "source": "simulation",
            "note": "Using simulated network data for demonstration",
            "simulation_params": {
                "base_speed": self.base_speed,
                "base_latency": self.base_latency
            }
        }