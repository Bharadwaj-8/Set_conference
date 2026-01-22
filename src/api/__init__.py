# src/api/__init__.py
"""
REST API for the Green AI Orchestrator
"""

from .server import app
from .client import OrchestratorClient

__all__ = ["app", "OrchestratorClient"]