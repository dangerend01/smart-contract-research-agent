#!/usr/bin/env python3
"""Run the aggressive LAB/CTF research mode with a self-improvement loop."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.aggressive_lab import AggressiveResearchLab


def main() -> int:
    lab = AggressiveResearchLab(ROOT, exploration_ratio=0.45, max_hypotheses=4, max_experiments=3)
    history = lab.run(cycles=2)
    print(json.dumps({"status": "ok", "cycles": history}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
