#!/usr/bin/env python3
"""Generate the local adversarial benchmark suite and persist the blind bundle plus evaluator data."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.benchmark_generator import BenchmarkGenerator


def main() -> int:
    generator = BenchmarkGenerator(root=ROOT)
    suite = generator.generate_suite(levels=["LEVEL_1", "LEVEL_3", "LEVEL_4", "LEVEL_6", "LEVEL_7"], seed=42)
    report = generator.generate_report(suite, title="local adversarial benchmark report")
    print(json.dumps({"status": "ok", "challenge_count": len(suite), "report": report}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
