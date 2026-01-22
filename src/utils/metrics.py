"""
Metrics calculation utilities
"""

from typing import Dict, Any, List
from ..orchestrator.models import Decision


def calculate_metrics(decisions: List[Decision]) -> Dict[str, Any]:
    """Calculate metrics from decisions"""
    if not decisions:
        return {}

    scores = [d.score for d in decisions]
    confidences = [d.confidence for d in decisions]
    batteries = [d.battery for d in decisions]
    networks = [d.network for d in decisions]
    carbons = [d.carbon for d in decisions]

    # Count modes
    mode_counts = {}
    for decision in decisions:
        mode = decision.recommended_mode.value
        mode_counts[mode] = mode_counts.get(mode, 0) + 1

    return {
        "count": len(decisions),
        "score": {
            "mean": sum(scores) / len(scores),
            "min": min(scores),
            "max": max(scores),
            "std": _calculate_std(scores)
        },
        "confidence": {
            "mean": sum(confidences) / len(confidences),
            "min": min(confidences),
            "max": max(confidences),
            "std": _calculate_std(confidences)
        },
        "battery": {
            "mean": sum(batteries) / len(batteries),
            "min": min(batteries),
            "max": max(batteries)
        },
        "network": {
            "mean": sum(networks) / len(networks),
            "min": min(networks),
            "max": max(networks)
        },
        "carbon": {
            "mean": sum(carbons) / len(carbons),
            "min": min(carbons),
            "max": max(carbons)
        },
        "mode_distribution": mode_counts
    }


def _calculate_std(values: List[float]) -> float:
    """Calculate standard deviation"""
    if len(values) < 2:
        return 0.0

    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return variance ** 0.5


def format_metrics(metrics: Dict[str, Any]) -> str:
    """Format metrics for display"""
    if not metrics:
        return "No metrics available"

    lines = []
    lines.append(f"Total Decisions: {metrics['count']}")

    # Score
    score = metrics.get('score', {})
    if score:
        lines.append("\nScore:")
        lines.append(f"  Mean: {score.get('mean', 0):.3f}")
        lines.append(f"  Range: [{score.get('min', 0):.3f}, {score.get('max', 0):.3f}]")
        lines.append(f"  Std Dev: {score.get('std', 0):.3f}")

    # Confidence
    confidence = metrics.get('confidence', {})
    if confidence:
        lines.append("\nConfidence:")
        lines.append(f"  Mean: {confidence.get('mean', 0):.3f}")
        lines.append(f"  Range: [{confidence.get('min', 0):.3f}, {confidence.get('max', 0):.3f}]")

    # Mode distribution
    modes = metrics.get('mode_distribution', {})
    if modes:
        lines.append("\nMode Distribution:")
        for mode, count in modes.items():
            percentage = (count / metrics['count']) * 100
            lines.append(f"  {mode}: {count} ({percentage:.1f}%)")

    return "\n".join(lines)