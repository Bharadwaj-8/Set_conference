#!/usr/bin/env python3
"""
Run script for Green AI Orchestrator
"""

import sys
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.orchestrator.decision_engine import DynamicGreenOrchestrator


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Green AI Orchestrator')

    parser.add_argument('--single', action='store_true',
                        help='Make a single decision')
    parser.add_argument('--continuous', action='store_true',
                        help='Run in continuous mode')
    parser.add_argument('--iterations', type=int, default=5,
                        help='Number of decisions to make (default: 5)')
    parser.add_argument('--interval', type=float, default=2.0,
                        help='Interval between decisions in seconds (default: 2.0)')
    parser.add_argument('--config', type=str, default=None,
                        help='Path to configuration file')
    parser.add_argument('--output', type=str, default='results',
                        help='Output directory (default: results)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--stats', action='store_true',
                        help='Show statistics after running')
    parser.add_argument('--save', action='store_true',
                        help='Save decision history to file')

    return parser.parse_args()


def main():
    """Main function"""
    args = parse_arguments()

    print("=" * 50)
    print("Green AI Orchestrator")
    print("=" * 50)

    try:
        # Initialize orchestrator
        orchestrator = DynamicGreenOrchestrator(
            config_path=args.config,
            output_dir=args.output
        )

        if args.verbose:
            print(f"Platform: {orchestrator.platform_info.get('system', 'unknown')}")
            print(f"Weights: {orchestrator.config.weights}")
            print(f"Threshold: {orchestrator.config.threshold}")
            print(f"Monitors: {list(orchestrator.monitors.keys())}")

        # Single decision mode
        if args.single:
            print("\nMaking single decision...")
            decision = orchestrator.make_decision()

            print("\n" + "=" * 50)
            print("DECISION RESULTS:")
            print("=" * 50)
            print(f"Score: {decision.score:.3f}")
            print(f"Confidence: {decision.confidence:.3f}")
            print(f"Recommended Mode: {decision.recommended_mode.value}")
            print(f"Explanation: {decision.explanation}")
            print(f"Battery: {decision.battery:.3f}")
            print(f"Network: {decision.network:.3f}")
            print(f"Carbon: {decision.carbon:.3f}")

            if args.verbose:
                print(f"Tradeoffs: {decision.tradeoffs}")
                print(f"Timestamp: {decision.timestamp}")

        # Continuous mode
        elif args.continuous or args.iterations > 1:
            print(f"\nMaking {args.iterations} decisions...")
            print("=" * 50)

            for i in range(args.iterations):
                if i > 0 and args.interval > 0:
                    import time
                    time.sleep(args.interval)

                decision = orchestrator.make_decision()
                print(f"Decision {i + 1}: "
                      f"Score={decision.score:.3f}, "
                      f"Confidence={decision.confidence:.3f}, "
                      f"Mode={decision.recommended_mode.value}, "
                      f"Battery={decision.battery:.3f}")

        # Statistics
        if args.stats or args.iterations > 1:
            stats = orchestrator.get_statistics()
            print("\n" + "=" * 50)
            print("STATISTICS:")
            print("=" * 50)

            if stats:
                print(f"Total Decisions: {stats.get('total_decisions', 0)}")
                print(f"Average Score: {stats.get('average_score', 0):.3f}")
                print(f"Average Confidence: {stats.get('average_confidence', 0):.3f}")
                print(f"Min Score: {stats.get('min_score', 0):.3f}")
                print(f"Max Score: {stats.get('max_score', 0):.3f}")

                mode_dist = stats.get('mode_distribution', {})
                if mode_dist:
                    print("\nMode Distribution:")
                    for mode, count in mode_dist.items():
                        percentage = (count / stats['total_decisions']) * 100
                        print(f"  {mode}: {count} ({percentage:.1f}%)")

        # Save history
        if args.save:
            orchestrator.save_decision_history()
            print(f"\nDecision history saved to {args.output}/")

        print("\n" + "=" * 50)
        print("Done!")
        print("=" * 50)

    except Exception as e:
        print(f"\nError: {e}")

        if args.verbose:
            import traceback
            traceback.print_exc()

        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())