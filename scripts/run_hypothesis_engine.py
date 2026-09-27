#!/usr/bin/env python3
"""Generate local security hypotheses for the contract under analysis."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agents.hypothesis_engine import run_local_hypothesis_engine


def main() -> int:
    contract = ROOT / "src" / "LocalDoSGasDemo.sol"
    records = run_local_hypothesis_engine(contract)
    print(json.dumps({"generated": len(records), "records": records}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
