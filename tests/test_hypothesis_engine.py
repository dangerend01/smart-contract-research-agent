import json
from pathlib import Path

from agents.contract_understander import extract_contract_profile
from agents.hypothesis_engine import generate_hypotheses, persist_hypotheses, _build_hypotheses_for_profile
from agents.hypothesis_schema import HYPOTHESIS_CATEGORIES, validate_hypothesis_schema


ROOT = Path(__file__).resolve().parents[1]


def test_hypothesis_schema_validation():
    payload = {
        "id": "H-001",
        "title": "Local gas amplification",
        "mechanism": "Attacker grows state before a victim processes it.",
        "category": "gas amplification",
        "affected_functions": ["processAll"],
        "attacker_controlled_inputs": ["array length"],
        "attacker_capabilities": ["append entries"],
        "required_state": ["participants array"],
        "target_invariant": "Operations should remain callable under attacker pressure.",
        "attack_sequence": ["grow input", "call victim"],
        "predicted_failure": "Victim gas rises beyond practical bounds.",
        "expected_observation": "gas rises with input size",
        "experiment_plan": {"setup": "local"},
        "priority": 70,
        "novelty_status": "new",
        "confidence": 0.8,
        "status": "unverified",
    }
    assert validate_hypothesis_schema(payload) is True
    assert payload["category"] in HYPOTHESIS_CATEGORIES


def test_generate_hypotheses_for_local_demo():
    profile = extract_contract_profile(ROOT / "src" / "LocalDoSGasDemo.sol")
    hypotheses = _build_hypotheses_for_profile(profile)
    assert len(hypotheses) >= 1
    assert any("state growth" in h.category.lower() or "gas" in h.title.lower() for h in hypotheses)
    assert all(h.status == "unverified" for h in hypotheses)


def test_prioritization_is_deterministic():
    profile = extract_contract_profile(ROOT / "src" / "LocalDoSGasDemo.sol")
    hypotheses = generate_hypotheses(profile, existing_records=[])
    scores = [h.priority for h in hypotheses]
    assert scores == sorted(scores, reverse=True)


def test_deduplication_logic():
    profile = extract_contract_profile(ROOT / "src" / "LocalDoSGasDemo.sol")
    hypotheses = generate_hypotheses(profile, existing_records=[])
    assert any(h.novelty_status in {"new", "similar", "duplicate", "requires_review"} for h in hypotheses)


def test_persistence_writes_json_file(tmp_path):
    profile = extract_contract_profile(ROOT / "src" / "LocalDoSGasDemo.sol")
    hypotheses = generate_hypotheses(profile, existing_records=[])
    saved = persist_hypotheses(hypotheses, tmp_path)
    assert len(saved) >= 1
    assert (tmp_path / "index.json").exists()
    persisted = json.loads((tmp_path / "index.json").read_text(encoding="utf-8"))
    assert len(persisted) >= len(hypotheses)


def test_local_demo_hypothesis_exists():
    profile = extract_contract_profile(ROOT / "src" / "LocalDoSGasDemo.sol")
    hypotheses = generate_hypotheses(profile, existing_records=[])
    texts = [h.title.lower() for h in hypotheses]
    assert any("state" in text and ("grow" in text or "gas" in text or "cost" in text) for text in texts)
