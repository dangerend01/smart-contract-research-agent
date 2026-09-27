#!/usr/bin/env python3
"""Run the diversity and frontier exploration engine over the local research memory."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.diversity_engine import ResearchDiversityEngine


def main() -> int:
    engine = ResearchDiversityEngine(ROOT)
    coverage = {
        "functions": {"addParticipant": "PARTIALLY_TESTED", "processAll": "TESTED"},
        "state_variables": {"participants": "UNTESTED", "processed": "TESTED"},
        "attacker_inputs": {"participants length": "UNTESTED"},
        "loops": {"for": "TESTED"},
        "external_calls": {"transfer": "UNTESTED"},
        "revert_paths": {"require(address != 0)": "TESTED"},
        "state_transitions": {"participants push": "PARTIALLY_TESTED"},
    }
    frontier = engine.compute_frontier_from_coverage(coverage, {"contract": "LocalDoSGasDemo"})
    print(json.dumps({"status": "ok", "frontier": frontier}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
