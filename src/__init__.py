# src/__init__.py
"""
Green AI Orchestrator - A dynamic, carbon-aware orchestrator for edge-cloud AI systems
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .orchestrator.decision_engine import DynamicGreenOrchestrator
from .utils.platform import get_platform_info, detect_platform

__all__ = [
    "DynamicGreenOrchestrator",
    "get_platform_info",
    "detect_platform",
]