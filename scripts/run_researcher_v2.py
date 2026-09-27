#!/usr/bin/env python3
"""Execute the evidence-driven deep researcher v2 against the existing Phase 1 hard benchmark public artifacts."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.researcher_v2 import run_phase1_researcher_v2


if __name__ == "__main__":
    result = run_phase1_researcher_v2(ROOT)
    print(f"researcher v2 results: {len(result['findings'])} findings")
    raise SystemExit(0)
