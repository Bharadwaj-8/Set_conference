"""
Data models for the Green AI Orchestrator
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
import time


class ExecutionMode(Enum):
    """Execution mode options"""
    EDGE_ONLY = "edge_only"
    CLOUD_ONLY = "cloud_only"
    HYBRID = "hybrid"
    DEFERRED = "deferred"


@dataclass
class SystemContext:
    """System context information"""
    battery: float
    network: float
    carbon: float
    platform: str
    timestamp: float = field(default_factory=time.time)
    additional_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Decision:
    """Decision made by the orchestrator"""
    score: float
    confidence: float
    battery: float
    network: float
    carbon: float
    timestamp: float = field(default_factory=time.time)
    recommended_mode: ExecutionMode = ExecutionMode.EDGE_ONLY
    explanation: str = ""
    tradeoffs: Dict[str, float] = field(default_factory=dict)


@dataclass
class OrchestratorConfig:
    """Configuration for the orchestrator"""
    # Weights for different factors
    weights: Dict[str, float] = field(default_factory=lambda: {
        "battery": 0.4,
        "network": 0.3,
        "carbon": 0.3
    })

    # Thresholds
    threshold: float = 0.5
    hard_edge_battery: float = 0.2
    hard_cloud_battery: float = 0.8

    # Monitor settings
    use_real_battery: bool = True
    use_real_network: bool = True
    use_real_carbon: bool = True
    carbon_zone: str = "IN"  # Default to India

    # Logging
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # Other settings
    version: str = "1.0.0"
    decision_history_size: int = 1000

    def validate(self):
        """Validate configuration"""
        if not 0 <= self.threshold <= 1:
            raise ValueError(f"Threshold must be between 0 and 1, got {self.threshold}")

        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")

        if not self.weights:
            raise ValueError("Weights dictionary cannot be empty")

    def update_weights(self, new_weights: Dict[str, float]):
        """Update weights with validation"""
        total = sum(new_weights.values())
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"New weights must sum to 1.0, got {total}")
        self.weights.update(new_weights)