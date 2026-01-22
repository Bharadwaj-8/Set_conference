#!/usr/bin/env python3
"""
Test imports to see what's broken
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

print("Testing imports...")

# Test utils imports
print("\n1. Testing utils imports:")
try:
    from src.utils.platform import get_platform_info
    print("✓ platform.get_platform_info")
except ImportError as e:
    print(f"✗ platform.get_platform_info: {e}")

try:
    from src.utils.config import load_config
    print("✓ config.load_config")
except ImportError as e:
    print(f"✗ config.load_config: {e}")

try:
    from src.utils.logger import setup_logging
    print("✓ logger.setup_logging")
except ImportError as e:
    print(f"✗ logger.setup_logging: {e}")

# Test orchestrator imports
print("\n2. Testing orchestrator imports:")
try:
    from src.orchestrator.models import SystemContext, Decision, OrchestratorConfig
    print("✓ models")
except ImportError as e:
    print(f"✗ models: {e}")

try:
    from src.orchestrator.scoring import calculate_sustainability_score
    print("✓ scoring")
except ImportError as e:
    print(f"✗ scoring: {e}")

# Test decision engine
print("\n3. Testing decision_engine import:")
try:
    from src.orchestrator.decision_engine import DynamicGreenOrchestrator
    print("✓ DynamicGreenOrchestrator")
except ImportError as e:
    print(f"✗ DynamicGreenOrchestrator: {e}")
    import traceback
    traceback.print_exc()