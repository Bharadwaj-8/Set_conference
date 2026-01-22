# tests/test_orchestrator.py
"""
Unit tests for the orchestrator
"""

import pytest
from src.orchestrator.decision_engine import DynamicGreenOrchestrator
from src.orchestrator.models import SystemContext, ExecutionMode


class TestDynamicGreenOrchestrator:
    """Test suite for DynamicGreenOrchestrator"""

    def test_initialization(self):
        """Test orchestrator initialization"""
        orchestrator = DynamicGreenOrchestrator()
        assert orchestrator is not None
        assert hasattr(orchestrator, 'monitors')
        assert 'battery' in orchestrator.monitors
        assert 'network' in orchestrator.monitors
        assert 'carbon' in orchestrator.monitors

    def test_decision_making(self):
        """Test basic decision making"""
        orchestrator = DynamicGreenOrchestrator()

        # Create test context
        context = SystemContext(
            battery_percentage=50.0,
            is_charging=False,
            carbon_flag=1,  # Green grid
            network_quality=0.8
        )

        decision = orchestrator.make_decision(context)

        assert decision is not None
        assert decision.execution_mode in [ExecutionMode.EDGE, ExecutionMode.CLOUD]
        assert 0 <= decision.score <= 1
        assert 0 <= decision.confidence <= 1
        assert decision.reasoning is not None

    def test_hard_constraints(self):
        """Test hard constraint rules"""
        orchestrator = DynamicGreenOrchestrator()

        # Test critical battery
        context = SystemContext(
            battery_percentage=5.0,
            is_charging=False,
            carbon_flag=1,
            network_quality=0.9
        )

        decision = orchestrator.make_decision(context)
        assert decision.execution_mode == ExecutionMode.EDGE
        assert "critical battery" in decision.reasoning.lower() or "hard constraint" in decision.reasoning.lower()

    def test_score_calculation(self):
        """Test sustainability score calculation"""
        orchestrator = DynamicGreenOrchestrator()

        # Test with high battery, green grid, good network
        context = SystemContext(
            battery_percentage=90.0,
            carbon_flag=1,
            network_quality=0.9
        )

        decision = orchestrator.make_decision(context)
        assert decision.score > 0.5  # Should be high

        # Test with low battery, dirty grid, poor network
        context = SystemContext(
            battery_percentage=20.0,
            carbon_flag=0,
            network_quality=0.2
        )

        decision = orchestrator.make_decision(context)
        assert decision.score < 0.5  # Should be low