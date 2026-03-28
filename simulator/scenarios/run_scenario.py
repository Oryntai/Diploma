"""Run predefined demo scenarios against the backend ingest endpoint.

Usage:
    python simulator/scenarios/run_scenario.py --scenario flood --ingest-url http://127.0.0.1:8000/api/ingest/telemetry
    python simulator/scenarios/run_scenario.py --scenario all --ingest-url http://127.0.0.1:8000/api/ingest/telemetry
"""
from __future__ import annotations

import argparse
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SCENARIOS = [
    "flood",
    "impossible_value",
    "unknown_device",
    "firmware_mismatch",
    "ml_anomaly",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run demo threat scenarios.")
    parser.add_argument(
        "--scenario",
        choices=SCENARIOS + ["all"],
        required=True,
        help="Scenario to run, or 'all' to run every scenario sequentially.",
    )
    parser.add_argument(
        "--ingest-url",
        required=True,
        help="Backend ingest endpoint URL.",
    )
    args = parser.parse_args()

    targets = SCENARIOS if args.scenario == "all" else [args.scenario]

    for name in targets:
        print(f"\n{'='*60}")
        print(f"  SCENARIO: {name}")
        print(f"{'='*60}")
        module = importlib.import_module(f"scenarios.{name}")
        try:
            module.run(args.ingest_url)
        except Exception as exc:
            print(f"  [ERROR] {exc}", file=sys.stderr)
            return 1
        print(f"  [OK] Scenario '{name}' completed.\n")

    print("All scenarios finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
