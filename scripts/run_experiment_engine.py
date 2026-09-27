#!/usr/bin/env python3
"""Generate and execute a local experiment for a stored hypothesis."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.experiment_engine import load_hypotheses, run_experiment, select_hypothesis_for_experiment


def main() -> int:
    hypotheses = load_hypotheses()
    hypothesis = select_hypothesis_for_experiment(hypotheses)
    if hypothesis is None:
        raise ValueError("No local hypotheses were found in the repository memory.")
    result = run_experiment(hypothesis)
    print(json.dumps({"result": result}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
