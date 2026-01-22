"""
Platform utilities
"""

import platform
import sys
import socket
import psutil
from typing import Dict, Any
from enum import Enum


class PlatformType(Enum):
    """Platform types"""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    UNKNOWN = "unknown"


def detect_platform() -> PlatformType:
    """Detect the current platform"""
    system = platform.system().lower()

    if system == "windows":
        return PlatformType.WINDOWS
    elif system == "darwin":
        return PlatformType.MACOS
    elif system == "linux":
        return PlatformType.LINUX
    else:
        return PlatformType.UNKNOWN


def get_platform_info() -> Dict[str, Any]:
    """Get platform information"""
    platform_type = detect_platform()

    info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_version": platform.python_version(),
        "hostname": socket.gethostname(),
        "platform_type": platform_type.value,
    }

    # Add CPU info
    try:
        info["cpu_count"] = psutil.cpu_count()
        info["cpu_percent"] = psutil.cpu_percent(interval=0.1)
    except:
        info["cpu_count"] = 1
        info["cpu_percent"] = 0

    # Add memory info
    try:
        mem = psutil.virtual_memory()
        info["memory_total"] = mem.total
        info["memory_available"] = mem.available
        info["memory_percent"] = mem.percent
    except:
        info["memory_total"] = 0
        info["memory_available"] = 0
        info["memory_percent"] = 0

    # Platform-specific info
    if platform_type == PlatformType.MACOS:
        try:
            import subprocess
            result = subprocess.run(["sw_vers", "-productVersion"],
                                  capture_output=True, text=True)
            if result.returncode == 0:
                info["macos_version"] = result.stdout.strip()
        except:
            pass

    return info


def is_mobile() -> bool:
    """Check if running on mobile platform"""
    # This is a placeholder - mobile detection would be more complex
    return False


def get_platform_capabilities() -> Dict[str, bool]:
    """Get platform capabilities"""
    plat = detect_platform()

    return {
        "has_battery": plat in [PlatformType.MACOS, PlatformType.LINUX, PlatformType.WINDOWS],
        "has_network": True,
        "supports_gpu": plat in [PlatformType.MACOS, PlatformType.WINDOWS, PlatformType.LINUX],
        "is_mobile": is_mobile(),
        "is_server": plat == PlatformType.LINUX and "server" in platform.release().lower()
    }