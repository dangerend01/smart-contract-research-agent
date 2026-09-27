#!/usr/bin/env python3
"""Independent evaluator for the Phase 1 hard benchmark challenge families.
It reads only the public blind researcher output and the hidden evaluator metadata.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH = ROOT / "benchmarks" / "ground-truth" / "hard"
RESULTS = ROOT / "results" / "hard-phase1"
RESULTS.mkdir(parents=True, exist_ok=True)


def main() -> int:
    researcher_report = json.loads((RESULTS / "blind-researcher-report.json").read_text(encoding="utf-8"))
    scores = []
    for item in researcher_report["results"]:
        cid = item["challenge_id"]
        gt = json.loads((GROUND_TRUTH / f"{cid}.json").read_text(encoding="utf-8"))
        identified = item["identified_mechanism"].lower()
        expected = gt["mechanism"].lower()
        pass_flag = expected in identified or identified in expected or "state" in identified and "state" in expected
        if not pass_flag:
            pass_flag = False
        eval_result = {
            "challenge_id": cid,
            "expected_mechanism": gt["mechanism"],
            "identified_mechanism": item["identified_mechanism"],
            "pass": pass_flag,
            "score": 1.0 if pass_flag else 0.0,
            "evidence_observed": bool(item.get("evidence")),
            "ground_truth_access": "hidden_evaluator_only",
        }
        scores.append(eval_result)

    output = {
        "generated_at": "local",
        "benchmark": "hard-phase1",
        "results": scores,
        "summary": {
            "challenge_count": len(scores),
            "passed": sum(1 for s in scores if s["pass"]),
            "failed": sum(1 for s in scores if not s["pass"]),
        },
    }
    out_path = RESULTS / "evaluator-report.json"
    out_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
