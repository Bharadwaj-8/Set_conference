# src/api/client.py
"""
Client library for the Green AI Orchestrator API
"""

import requests
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
import time


class OrchestratorClient:
    """Client for interacting with the Green AI Orchestrator API"""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        """
        Initialize the client

        Args:
            base_url: Base URL of the API server
            api_key: Optional API key for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()

        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def health(self) -> Dict[str, Any]:
        """Check API health"""
        response = self.session.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

    def get_context(self, use_real_data: bool = True) -> Dict[str, Any]:
        """Get current system context"""
        params = {"use_real_data": use_real_data}
        response = self.session.get(f"{self.base_url}/context", params=params)
        response.raise_for_status()
        return response.json()

    def make_decision(
            self,
            context: Optional[Dict[str, Any]] = None,
            weights: Optional[Dict[str, float]] = None,
            threshold: Optional[float] = None
    ) -> Dict[str, Any]:
        """Make a routing decision"""
        request_data = {}

        if context:
            request_data["context"] = context

        if weights:
            request_data["weights"] = weights

        if threshold:
            request_data["threshold"] = threshold

        response = self.session.post(
            f"{self.base_url}/decision",
            json=request_data
        )
        response.raise_for_status()
        return response.json()

    def get_decisions(self, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """Get decision history"""
        params = {"limit": limit, "offset": offset}
        response = self.session.get(f"{self.base_url}/decisions", params=params)
        response.raise_for_status()
        return response.json()

    def get_decision(self, decision_id: str) -> Dict[str, Any]:
        """Get specific decision by ID"""
        response = self.session.get(f"{self.base_url}/decisions/{decision_id}")
        response.raise_for_status()
        return response.json()

    def get_statistics(self) -> Dict[str, Any]:
        """Get decision statistics"""
        response = self.session.get(f"{self.base_url}/stats")
        response.raise_for_status()
        return response.json()

    def batch_decisions(
            self,
            requests: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Make multiple decisions in batch"""
        response = self.session.post(
            f"{self.base_url}/batch",
            json=requests
        )
        response.raise_for_status()
        return response.json()

    def get_platform_info(self) -> Dict[str, Any]:
        """Get platform information"""
        response = self.session.get(f"{self.base_url}/platform")
        response.raise_for_status()
        return response.json()

    def update_configuration(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update orchestrator configuration"""
        response = self.session.post(
            f"{self.base_url}/config",
            json=config
        )
        response.raise_for_status()
        return response.json()

    def monitor_continuous(
            self,
            interval: int = 60,
            iterations: int = 10,
            callback: Optional[callable] = None
    ):
        """
        Monitor continuously and make decisions

        Args:
            interval: Time between decisions in seconds
            iterations: Number of iterations (0 for infinite)
            callback: Optional callback function for each decision
        """
        iteration = 0

        try:
            while iterations == 0 or iteration < iterations:
                iteration += 1
                print(f"\n--- Iteration {iteration} ---")

                # Make decision
                decision = self.make_decision()

                # Display decision
                self._print_decision(decision)

                # Call callback if provided
                if callback:
                    callback(decision)

                # Wait for next iteration
                if iterations == 0 or iteration < iterations:
                    time.sleep(interval)

        except KeyboardInterrupt:
            print("\nMonitoring stopped by user")
        except Exception as e:
            print(f"Monitoring failed: {e}")
            raise

    def _print_decision(self, decision: Dict[str, Any]):
        """Print decision in a readable format"""
        ctx = decision.get("context", {})

        print("\n" + "=" * 60)
        print("GREEN AI ORCHESTRATOR - DECISION (API)")
        print("=" * 60)
        print(f"Decision ID: {decision.get('decision_id', 'N/A')}")
        print(f"Time: {decision.get('timestamp', 'N/A')}")
        print("\n--- CONTEXT ---")
        print(f"Battery: {ctx.get('battery_percentage', 'N/A')}%")
        print(f"Grid: {'GREEN' if ctx.get('carbon_flag') == 1 else 'DIRTY'}")
        print(f"Network: {ctx.get('network_speed_mbps', 'N/A')} Mbps")
        print("\n--- DECISION ---")
        print(f"Mode: {decision.get('execution_mode', 'N/A')}")
        print(f"Score: {decision.get('score', 0):.3f}")
        print(f"Confidence: {decision.get('confidence', 0):.2f}")
        print(f"Reason: {decision.get('reasoning', 'N/A')}")
        print("=" * 60)

    def test_connection(self) -> bool:
        """Test connection to API server"""
        try:
            self.health()
            return True
        except Exception:
            return False


# Example usage
if __name__ == "__main__":
    # Create client
    client = OrchestratorClient("http://localhost:8000")

    # Test connection
    if client.test_connection():
        print("Connected to API server")

        # Get health
        health = client.health()
        print(f"API Health: {health.get('status')}")

        # Make a decision
        decision = client.make_decision()
        print(f"Decision: {decision.get('execution_mode')}")

        # Get statistics
        stats = client.get_statistics()
        print(f"Total decisions: {stats.get('total_decisions')}")

    else:
        print("Failed to connect to API server")