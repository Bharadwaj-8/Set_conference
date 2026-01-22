"""
Utility modules for the Green AI Orchestrator
"""

# Only import what actually exists in your code
try:
    from .platform import get_platform_info, PlatformType, detect_platform, get_platform_capabilities
except ImportError:
    # Define fallbacks if platform.py doesn't have these
    pass

from .config import load_config
from .logger import setup_logging

# Try to import optional modules
try:
    from .validation import validate_config, validate_monitor_data
except ImportError:
    # These might not exist yet, that's ok
    pass

try:
    from .metrics import calculate_metrics, format_metrics
except ImportError:
    pass

__all__ = [
    "get_platform_info",
    "PlatformType",
    "detect_platform",
    "get_platform_capabilities",
    "load_config",
    "setup_logging",
]