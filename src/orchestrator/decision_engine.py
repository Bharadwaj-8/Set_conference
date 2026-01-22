"""
Main decision engine for the Green AI Orchestrator
"""

import time
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import asdict
from pathlib import Path
import os

from .models import SystemContext, Decision, ExecutionMode, OrchestratorConfig
from .scoring import calculate_sustainability_score, calculate_confidence, analyze_tradeoffs
from ..monitors.factory import MonitorFactory
from ..utils.platform import get_platform_info
from ..utils.config import load_config
from ..utils.logger import setup_logging

logger = logging.getLogger(__name__)


class DynamicGreenOrchestrator:
    """
    Production-ready dynamic green orchestrator
    Works on macOS, Windows, and Linux
    """

    def __init__(
            self,
            config_path: Optional[str] = None,
            output_dir: str = "results"
    ):
        """
        Initialize orchestrator

        Args:
            config_path: Path to configuration file
            output_dir: Directory for output files
        """
        # Load configuration
        self.config_data = load_config(config_path)

        # Create OrchestratorConfig instance with loaded data
        self.config = self._create_config_from_data()

        # Validate configuration
        self.config.validate()

        # Setup output directory
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup logging
        setup_logging(
            level=self.config.log_level,
            log_file=self.config.log_file or str(self.output_dir / "orchestrator.log")
        )

        # Get platform info
        self.platform_info = get_platform_info()

        # Initialize monitors using factory
        self.monitors = self._initialize_monitors()

        # Decision history
        self.decision_history: List[Decision] = []

        logger.info(f"Initialized Green AI Orchestrator v{self.config.version}")
        logger.info(f"Platform: {self.platform_info.get('system', 'unknown')}")
        logger.info(f"Weights: {self.config.weights}")
        logger.info(f"Threshold: {self.config.threshold}")
        logger.info(f"Output directory: {self.output_dir}")

    def _create_config_from_data(self) -> OrchestratorConfig:
        """Create OrchestratorConfig from loaded data"""
        # Start with default config
        config = OrchestratorConfig()

        # Update from loaded data if available
        if self.config_data and "orchestrator" in self.config_data:
            orch_config = self.config_data["orchestrator"]

            # Update weights
            if "weights" in orch_config:
                for key, value in orch_config["weights"].items():
                    if key in config.weights:
                        config.weights[key] = value

            # Update thresholds
            if "threshold" in orch_config:
                config.threshold = orch_config["threshold"]
            if "hard_edge_battery" in orch_config:
                config.hard_edge_battery = orch_config["hard_edge_battery"]
            if "hard_cloud_battery" in orch_config:
                config.hard_cloud_battery = orch_config["hard_cloud_battery"]

        # Update monitor settings
        if self.config_data and "monitors" in self.config_data:
            monitors_config = self.config_data["monitors"]

            if "battery" in monitors_config:
                config.use_real_battery = monitors_config["battery"].get("enabled", True)

            if "network" in monitors_config:
                config.use_real_network = monitors_config["network"].get("enabled", True)

            if "carbon" in monitors_config:
                config.use_real_carbon = monitors_config["carbon"].get("enabled", True)
                config.carbon_zone = monitors_config["carbon"].get("zone", "IN")

        # Update logging
        if self.config_data and "logging" in self.config_data:
            log_config = self.config_data["logging"]
            config.log_level = log_config.get("level", "INFO")
            if "file" in log_config:
                config.log_file = log_config["file"]

        return config

    def _initialize_monitors(self) -> Dict[str, Any]:
        """Initialize all monitors"""
        monitors = {}

        # Battery monitor
        if self.config.use_real_battery:
            try:
                monitors["battery"] = MonitorFactory.create_battery_monitor()
                if not monitors["battery"].is_available():
                    logger.warning("Battery monitor not available, using simulation")
                    monitors["battery"] = MonitorFactory.create_battery_monitor(use_universal=True)
            except Exception as e:
                logger.error(f"Failed to initialize battery monitor: {e}")
                monitors["battery"] = MonitorFactory.create_battery_monitor(use_universal=True)
        else:
            monitors["battery"] = MonitorFactory.create_battery_monitor(use_universal=False)

        # Network monitor
        if self.config.use_real_network:
            try:
                monitors["network"] = MonitorFactory.create_network_monitor(
                    use_speedtest=True,
                    fallback_to_ping=True
                )
            except Exception as e:
                logger.error(f"Failed to initialize network monitor: {e}")
                monitors["network"] = MonitorFactory.create_network_monitor(
                    use_speedtest=False,
                    fallback_to_ping=False
                )
        else:
            monitors["network"] = MonitorFactory.create_network_monitor(
                use_speedtest=False,
                fallback_to_ping=False
            )

        # Carbon monitor
        if self.config.use_real_carbon:
            api_key = os.getenv("ELECTRICITY_MAPS_API_KEY")
            try:
                monitors["carbon"] = MonitorFactory.create_carbon_monitor(
                    api_key=api_key,
                    use_simulation_if_no_key=True,
                    zone=self.config.carbon_zone
                )
            except Exception as e:
                logger.error(f"Failed to initialize carbon monitor: {e}")
                monitors["carbon"] = MonitorFactory.create_carbon_monitor(
                    api_key=None,
                    use_simulation_if_no_key=True
                )
        else:
            monitors["carbon"] = MonitorFactory.create_carbon_monitor(
                api_key=None,
                use_simulation_if_no_key=True
            )

        logger.info(f"Initialized {len(monitors)} monitors: {list(monitors.keys())}")
        return monitors

    def make_decision(self) -> Decision:
        """
        Make a single sustainability decision based on current monitor readings.
        Works with battery, network, and carbon monitors.
        """
        # --- Battery status ---
        battery_monitor = self.monitors.get("battery")
        battery_status = 0.5  # Default
        if battery_monitor:
            if hasattr(battery_monitor, "get_level"):
                battery_status = battery_monitor.get_level()
            elif hasattr(battery_monitor, "read"):
                battery_status = battery_monitor.read()
            elif hasattr(battery_monitor, "battery_level"):
                battery_status = battery_monitor.battery_level
            else:
                logger.warning("Battery monitor has no readable method, using default 0.5")
                battery_status = 0.5
        else:
            logger.warning("No battery monitor available, using default 0.5")

        # --- Network status ---
        network_monitor = self.monitors.get("network")
        network_status = 0.5  # Default
        if network_monitor:
            if hasattr(network_monitor, "get_speed"):
                network_status = network_monitor.get_speed()
            elif hasattr(network_monitor, "read"):
                network_status = network_monitor.read()
            elif hasattr(network_monitor, "network_quality"):
                network_status = network_monitor.network_quality
            else:
                logger.warning("Network monitor has no readable method, using default 0.5")
                network_status = 0.5
        else:
            logger.warning("No network monitor available, using default 0.5")

        # --- Carbon status ---
        carbon_monitor = self.monitors.get("carbon")
        carbon_status = 0.5  # Default
        if carbon_monitor:
            if hasattr(carbon_monitor, "get_carbon_intensity"):
                carbon_status = carbon_monitor.get_carbon_intensity()
            elif hasattr(carbon_monitor, "read"):
                carbon_status = carbon_monitor.read()
            elif hasattr(carbon_monitor, "carbon_intensity"):
                carbon_status = carbon_monitor.carbon_intensity
            else:
                logger.warning("Carbon monitor has no readable method, using default 0.5")
                carbon_status = 0.5
        else:
            logger.warning("No carbon monitor available, using default 0.5")

        # --- Prepare values dict ---
        monitor_values = {
            "battery": battery_status,
            "network": network_status,
            "carbon": carbon_status
        }

        # --- Compute sustainability score ---
        score = calculate_sustainability_score(monitor_values, self.config.weights)

        # --- Create system context for confidence ---
        context = SystemContext(
            battery=battery_status,
            network=network_status,
            carbon=carbon_status,
            platform=self.platform_info.get("system", "unknown")
        )

        confidence = calculate_confidence(score, context)

        # --- Determine execution mode ---
        tradeoffs = analyze_tradeoffs(battery_status, network_status, carbon_status)

        # Simple logic for execution mode (you can make this more sophisticated)
        if battery_status < self.config.hard_edge_battery:
            recommended_mode = ExecutionMode.CLOUD_ONLY
            explanation = "Battery too low for edge processing"
        elif battery_status > self.config.hard_cloud_battery and network_status > 0.7:
            recommended_mode = ExecutionMode.EDGE_ONLY
            explanation = "High battery and good network for edge processing"
        elif score > self.config.threshold:
            recommended_mode = ExecutionMode.HYBRID
            explanation = "Good conditions for hybrid processing"
        else:
            recommended_mode = ExecutionMode.DEFERRED
            explanation = "Poor conditions, defer processing"

        # --- Create Decision object ---
        decision = Decision(
            score=score,
            confidence=confidence,
            battery=battery_status,
            network=network_status,
            carbon=carbon_status,
            timestamp=time.time(),
            recommended_mode=recommended_mode,
            explanation=explanation,
            tradeoffs=tradeoffs
        )

        # --- Save decision to history ---
        self.decision_history.append(decision)

        # Limit history size
        if len(self.decision_history) > self.config.decision_history_size:
            self.decision_history = self.decision_history[-self.config.decision_history_size:]

        logger.info(f"Decision made: Score={score:.3f}, Confidence={confidence:.3f}, Mode={recommended_mode.value}")
        return decision

    def get_recent_decisions(self, count: int = 10) -> List[Decision]:
        """Get recent decisions from history"""
        return self.decision_history[-count:] if self.decision_history else []

    def save_decision_history(self, filename: Optional[str] = None):
        """Save decision history to file"""
        if not filename:
            filename = self.output_dir / f"decisions_{int(time.time())}.json"
        else:
            filename = self.output_dir / filename

        history_data = [asdict(decision) for decision in self.decision_history]

        with open(filename, 'w') as f:
            json.dump(history_data, f, indent=2, default=str)

        logger.info(f"Saved {len(history_data)} decisions to {filename}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about decisions"""
        if not self.decision_history:
            return {}

        scores = [d.score for d in self.decision_history]
        confidences = [d.confidence for d in self.decision_history]

        return {
            "total_decisions": len(self.decision_history),
            "average_score": sum(scores) / len(scores),
            "average_confidence": sum(confidences) / len(confidences),
            "min_score": min(scores),
            "max_score": max(scores),
            "mode_distribution": {
                mode.value: len([d for d in self.decision_history if d.recommended_mode == mode])
                for mode in ExecutionMode
            }
        }