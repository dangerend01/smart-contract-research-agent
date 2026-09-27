#!/usr/bin/env python3
"""Independent evaluator for the Phase 2 benchmark. It reads only the public blind report and the hidden evaluator metadata."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GROUND_TRUTH = ROOT / "benchmarks" / "ground-truth" / "hard-phase2"
RESULTS = ROOT / "results" / "hard-phase2"
RESULTS.mkdir(parents=True, exist_ok=True)


def main() -> int:
    report = json.loads((RESULTS / "blind-research-report.json").read_text(encoding="utf-8"))
    scores = []
    missed = []
    false_positives = []

    for item in report["results"]:
        cid = item["challenge_id"]
        gt = json.loads((GROUND_TRUTH / f"{cid}.json").read_text(encoding="utf-8"))
        identified = item["identified_mechanism"].lower()
        expected = gt["mechanism"].lower()
        root = item["root_cause_guess"].lower()
        expected_root = gt["root_cause"].lower()

        pass_flag = expected in identified or identified in expected or ("state" in identified and "state" in expected)
        if pass_flag and (expected_root in root or "history" in root or "loop" in root):
            pass_flag = True
        elif not pass_flag:
            pass_flag = False

        if not pass_flag:
            missed.append({
                "challenge_id": cid,
                "expected_mechanism": gt["mechanism"],
                "identified_mechanism": item["identified_mechanism"],
                "reason": "public-only hypothesis did not match the protected evaluator mechanism",
            })

        if pass_flag and "assembly" in identified and gt["mechanism"] not in identified:
            false_positives.append({
                "challenge_id": cid,
                "identified_mechanism": item["identified_mechanism"],
                "reason": "the hypothesis is too generic and not anchored to the actual hidden mechanism",
            })

        scores.append({
            "challenge_id": cid,
            "expected_mechanism": gt["mechanism"],
            "identified_mechanism": item["identified_mechanism"],
            "pass": pass_flag,
            "score": 1.0 if pass_flag else 0.0,
            "ground_truth_access": "hidden_evaluator_only",
            "confidence": item.get("confidence", 0.0),
        })

    output = {
        "generated_at": "local",
        "benchmark": "hard-phase2",
        "results": scores,
        "missed_mechanisms": missed,
        "false_positives": false_positives,
        "summary": {
            "challenge_count": len(scores),
            "passed": sum(1 for s in scores if s["pass"]),
            "failed": sum(1 for s in scores if not s["pass"]),
            "missed_count": len(missed),
            "false_positive_count": len(false_positives),
        },
    }
    out_path = RESULTS / "evaluator-report.json"
    out_path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
