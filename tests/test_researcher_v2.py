import json
from pathlib import Path

from agents.evaluator import Evaluator
from agents.researcher_v2 import EvidenceDrivenResearcherV2

ROOT = Path(__file__).resolve().parents[1]


def test_prediction_recording_and_evidence_requirements_are_present():
    challenge = json.loads((ROOT / "benchmarks" / "generated" / "hard" / "HB-001.json").read_text(encoding="utf-8"))
    researcher = EvidenceDrivenResearcherV2(root=ROOT)
    result = researcher.analyze_challenge(challenge)

    required = [
        "observed_behavior",
        "expected_behavior",
        "attacker_controlled_inputs",
        "required_state",
        "triggering_sequence",
        "predicted_outcome",
        "observed_outcome",
        "reproducible_test",
        "minimized_counterexample",
        "affected_functions",
        "affected_state_variables",
        "resource_impact",
        "root_cause",
        "invariant_violation",
    ]
    for key in required:
        assert key in result, key
    assert result["prediction"]
    assert result["finding_status"] in {"CONFIRMED", "PLAUSIBLE", "UNCONFIRMED", "FALSE_POSITIVE"}


def test_invariant_extraction_and_deep_analysis_escalation_are_recorded():
    challenge = json.loads((ROOT / "benchmarks" / "generated" / "hard" / "HB-003.json").read_text(encoding="utf-8"))
    researcher = EvidenceDrivenResearcherV2(root=ROOT)
    result = researcher.analyze_challenge(challenge)

    assert result["candidate_invariants"]
    assert "deep_analysis" in result
    assert "selected_layers" in result["deep_analysis"]
    assert result["deep_analysis"]["reason"]


def test_counterexample_minimization_keeps_smallest_reproducer():
    challenge = json.loads((ROOT / "benchmarks" / "generated" / "hard" / "HB-002.json").read_text(encoding="utf-8"))
    researcher = EvidenceDrivenResearcherV2(root=ROOT)
    result = researcher.analyze_challenge(challenge)

    minimized = result["minimized_counterexample"]
    assert minimized["sequence_length"] >= 1
    assert minimized["calls"]
    assert minimized["reason"]


def test_root_cause_structure_is_separate_from_symptom_and_invariant():
    challenge = json.loads((ROOT / "benchmarks" / "generated" / "hard" / "HB-001.json").read_text(encoding="utf-8"))
    researcher = EvidenceDrivenResearcherV2(root=ROOT)
    result = researcher.analyze_challenge(challenge)

    assert "root_cause" in result
    assert "invariant_violation" in result
    assert result["root_cause"] != result["invariant_violation"]


def test_research_memory_strategy_version_is_created():
    challenge = json.loads((ROOT / "benchmarks" / "generated" / "hard" / "HB-001.json").read_text(encoding="utf-8"))
    researcher = EvidenceDrivenResearcherV2(root=ROOT)
    findings = [researcher.analyze_challenge(challenge)]
    payload = researcher.persist_strategy_version(findings)

    assert payload["strategy_version"].startswith("strategy-v")
    version_file = ROOT / "research_memory" / "strategies" / f"{payload['strategy_version']}.json"
    assert version_file.exists()


def test_evaluator_statuses_cover_desired_set():
    evaluator = Evaluator()
    challenge = {
        "challenge_id": "HB-TEST",
        "ground_truth": {"mechanism": "state-dependent gas amplification"},
    }

    assert evaluator.classify_finding_status(challenge, {"finding_status": "CONFIRMED"}) == "CONFIRMED"
    assert evaluator.classify_finding_status(challenge, {"finding_status": "PLAUSIBLE"}) == "PLAUSIBLE"
    assert evaluator.classify_finding_status(challenge, {"finding_status": "MISSED"}) == "MISSED"
    assert evaluator.classify_finding_status(challenge, {"finding_status": "FALSE_POSITIVE"}) == "FALSE_POSITIVE"
    assert evaluator.classify_finding_status(challenge, {"finding_status": "KNOWN_PATTERN"}) == "KNOWN_PATTERN"
    assert evaluator.classify_finding_status(challenge, {"finding_status": "KNOWN_VARIANT"}) == "KNOWN_VARIANT"
    assert evaluator.classify_finding_status(challenge, {"finding_status": "POTENTIALLY_DISTINCT"}) == "POTENTIALLY_DISTINCT"
