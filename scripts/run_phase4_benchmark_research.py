#!/usr/bin/env python3
"""Run the blind public-only Phase 4 research pass and persist findings and a markdown report."""

from __future__ import annotations

import json
from pathlib import Path

from agents.deep_evm_research_engine import DeepEVMResearchEngine

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "benchmarks" / "generated" / "hard-phase4"
RESULTS = ROOT / "results" / "hard-phase4"
RESULTS.mkdir(parents=True, exist_ok=True)

engine = DeepEVMResearchEngine()


def main() -> int:
    output = []
    for public_path in sorted(PUBLIC.glob("*.json")):
        challenge = json.loads(public_path.read_text(encoding="utf-8"))
        pipeline = engine.run_pipeline(challenge["contract_source"], challenge["contract_name"])
        report = engine.generate_report(pipeline)
        (RESULTS / f"{challenge['challenge_id']}-analysis.json").write_text(json.dumps(pipeline, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (RESULTS / f"{challenge['challenge_id']}-report.md").write_text(report, encoding="utf-8")
        output.append({
            "challenge_id": challenge["challenge_id"],
            "family": challenge["family"],
            "depth": pipeline["deepest_layer_reached"],
            "questions": len(pipeline["research_questions"]),
            "invariants": len(pipeline["candidate_invariants"]),
        })

    report_path = RESULTS / "PHASE4_RESEARCH_REPORT.md"
    report_path.write_text(
        "# PHASE 4 RESEARCH REPORT\n\n"
        + "\n".join(f"- {item['challenge_id']}: {item['family']} | deepest layer: {item['depth']} | questions: {item['questions']} | invariants: {item['invariants']}" for item in output)
        + "\n",
        encoding="utf-8",
    )

    payload = {"benchmark": "hard-phase4", "researcher_mode": "blind-public-only", "results": output}
    (RESULTS / "blind-research-report.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
