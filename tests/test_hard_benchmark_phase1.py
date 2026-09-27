import json
from pathlib import Path

from agents.evaluator import Evaluator

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "benchmarks" / "generated" / "hard"
GROUND = ROOT / "benchmarks" / "ground-truth" / "hard"
MANIFEST = ROOT / "benchmarks" / "manifests" / "hard" / "hard-benchmark-manifest.json"


def test_hard_phase1_public_payloads_are_separated_from_hidden_truth():
    challenge_ids = sorted(p.stem for p in PUBLIC.glob("*.json"))
    assert len(challenge_ids) == 3, challenge_ids
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["challenge_count"] == 3

    for challenge_id in challenge_ids:
        public = json.loads((PUBLIC / f"{challenge_id}.json").read_text(encoding="utf-8"))
        hidden = json.loads((GROUND / f"{challenge_id}.json").read_text(encoding="utf-8"))

        assert challenge_id == public["challenge_id"]
        assert "ground_truth" not in public
        assert "mechanism" in hidden
        assert hidden["mechanism_fingerprint"] == public["mechanism_fingerprint"]
        assert public["deployment_configuration"]["local"] is True


def test_hard_phase1_evaluator_rejects_non_evidence_and_transaction_failures():
    challenge = {
        "challenge_id": "HB-001",
        "ground_truth": {"mechanism": "sequence-dependent loop amplification", "root_cause": "stored state used as loop bound"},
    }
    evaluator = Evaluator()

    no_evidence = {"identified_mechanism": "transaction reverted", "correct_root_cause": False, "reproducible": False}
    assert evaluator.evaluate(challenge, no_evidence)["pass"] is False

    strong = {"identified_mechanism": "sequence-dependent loop amplification", "correct_root_cause": True, "reproducible": True}
    assert evaluator.evaluate(challenge, strong)["pass"] is True


def test_hard_phase1_challenge_families_cover_three_required_dimensions():
    challenge_ids = sorted(p.stem for p in PUBLIC.glob("*.json"))
    families = [json.loads((PUBLIC / f"{cid}.json").read_text(encoding="utf-8"))["family"] for cid in challenge_ids]
    assert "sequence-dependent-loop-amplification" in families
    assert "queue-growth-gas-amplifier" in families
    assert "packed-storage-drift" in families
