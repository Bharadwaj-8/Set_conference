"""
Validation utilities
"""

from typing import Dict, Any, List, Tuple
from ..orchestrator.models import OrchestratorConfig


def validate_config(config_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate configuration data"""
    errors = []

    # Check required sections
    required_sections = ["orchestrator", "monitors"]
    for section in required_sections:
        if section not in config_data:
            errors.append(f"Missing required section: {section}")

    # Check orchestrator section
    if "orchestrator" in config_data:
        orch = config_data["orchestrator"]

        # Check weights
        if "weights" in orch:
            weights = orch["weights"]
            required_weights = ["battery", "network", "carbon"]
            for weight in required_weights:
                if weight not in weights:
                    errors.append(f"Missing weight: {weight}")

            # Check weight sum
            total = sum(weights.values())
            if abs(total - 1.0) > 0.001:
                errors.append(f"Weights must sum to 1.0, got {total}")

    return len(errors) == 0, errors


def validate_monitor_data(monitor_values: Dict[str, float]) -> bool:
    """Validate monitor readings"""
    required_monitors = ["battery", "network", "carbon"]

    for monitor in required_monitors:
        if monitor not in monitor_values:
            return False

        value = monitor_values[monitor]
        if not isinstance(value, (int, float)):
            return False

        # Check value range
        if value < 0 or value > 1:
            return False

    return True