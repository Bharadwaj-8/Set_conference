"""
Scoring functions for the Green AI Orchestrator
"""

import math
from typing import Dict, Any
from .models import SystemContext


def calculate_sustainability_score(monitor_values: Dict[str, float], weights: Dict[str, float]) -> float:
    """
    Calculate overall sustainability score based on monitor readings and weights.

    Args:
        monitor_values: Dictionary with monitor readings (battery, network, carbon)
        weights: Dictionary with weights for each factor

    Returns:
        float: Sustainability score between 0 and 1
    """
    # Normalize values (assuming they're already in 0-1 range)
    battery = monitor_values.get("battery", 0.5)
    network = monitor_values.get("network", 0.5)
    carbon = monitor_values.get("carbon", 0.5)

    # Invert carbon (lower carbon intensity is better)
    # Higher carbon intensity should give lower score
    carbon_score = 1.0 - carbon

    # Calculate weighted sum
    score = (
            battery * weights.get("battery", 0.4) +
            network * weights.get("network", 0.3) +
            carbon_score * weights.get("carbon", 0.3)
    )

    # Ensure score is between 0 and 1
    return max(0.0, min(1.0, score))


def calculate_confidence(score: float, context: SystemContext) -> float:
    """
    Calculate confidence in the decision based on score and context.

    Args:
        score: Sustainability score
        context: System context information

    Returns:
        float: Confidence level between 0 and 1
    """
    # Base confidence on score (extreme scores have higher confidence)
    score_confidence = 1.0 - abs(score - 0.5) * 2

    # Consider battery level confidence
    # Very high or very low battery levels are more certain
    battery_confidence = 1.0 - abs(context.battery - 0.5) * 2

    # Consider network stability (higher network quality = more confidence)
    network_confidence = context.network

    # Carbon confidence (closer to extremes = more confidence)
    carbon_confidence = 1.0 - abs(context.carbon - 0.5) * 2

    # Combine confidences
    confidence = (score_confidence + battery_confidence + network_confidence + carbon_confidence) / 4

    # Apply some nonlinear scaling
    confidence = confidence ** 0.5  # Square root for more conservative confidence

    return max(0.0, min(1.0, confidence))


def analyze_tradeoffs(battery: float, network: float, carbon: float) -> Dict[str, float]:
    """
    Analyze tradeoffs between different factors.

    Args:
        battery: Battery level (0-1)
        network: Network quality (0-1)
        carbon: Carbon intensity (0-1)

    Returns:
        Dict[str, float]: Tradeoff metrics
    """
    return {
        "battery_vs_performance": battery * 0.7 + (1 - battery) * 0.3,
        "network_vs_latency": network * 0.6 + (1 - network) * 0.4,
        "carbon_vs_speed": (1 - carbon) * 0.8 + carbon * 0.2,
        "overall_tradeoff": (battery + network + (1 - carbon)) / 3
    }