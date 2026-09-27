#!/usr/bin/env python3
"""Run the independent execution + evidence gate against the existing Phase 1 public benchmark."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.independent_execution_gate import run_phase1_validations


if __name__ == "__main__":
    report = run_phase1_validations(ROOT)
    summary = report["summary"]
    print(json.dumps(summary, indent=2, sort_keys=True))
    raise SystemExit(0)
