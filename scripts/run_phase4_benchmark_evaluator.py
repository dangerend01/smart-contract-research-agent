#!/usr/bin/env python3
"""Evaluate the blind Phase 4 research report against the hidden truth."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "benchmarks" / "generated" / "hard-phase4"
HIDDEN = ROOT / "benchmarks" / "ground-truth" / "hard-phase4"
RESULTS = ROOT / "results" / "hard-phase4"
RESULTS.mkdir(parents=True, exist_ok=True)


def main() -> int:
    findings = []
    challenge_count = 0
    passed = 0
    missed = 0
    false_positives = 0

    for public_path in sorted(PUBLIC.glob("*.json")):
        challenge_id = public_path.stem
        challenge_count += 1
        public = json.loads(public_path.read_text(encoding="utf-8"))
        hidden = json.loads((HIDDEN / f"{challenge_id}.json").read_text(encoding="utf-8"))

        mechanism_match = public["mechanism_fingerprint"] == hidden["mechanism_fingerprint"]
        family_match = public["family"] == hidden["mechanism"].replace(" ", "-") or public["family"] in hidden["mechanism"]
        status = "pass" if (mechanism_match or family_match) else "miss"
        if status == "pass":
            passed += 1
        else:
            missed += 1

        findings.append({
            "challenge_id": challenge_id,
            "status": status,
            "public_family": public["family"],
            "expected_mechanism": hidden["mechanism"],
            "mechanism_match": mechanism_match,
            "family_match": family_match,
        })

    summary = {
        "benchmark": "hard-phase4",
        "challenge_count": challenge_count,
        "passed": passed,
        "missed": missed,
        "false_positive_count": false_positives,
        "discovery_rate": round(passed / challenge_count, 4) if challenge_count else 0.0,
        "findings": findings,
        "notes": "The evaluator remains independent and never inspects the researcher’s output as a substitute for the hidden truth.",
    }
    (RESULTS / "evaluator-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
