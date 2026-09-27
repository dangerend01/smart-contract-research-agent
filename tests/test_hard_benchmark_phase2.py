import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "benchmarks" / "generated" / "hard-phase2"
GROUND = ROOT / "benchmarks" / "ground-truth" / "hard-phase2"
MANIFEST = ROOT / "benchmarks" / "manifests" / "hard" / "hard-phase2-manifest.json"


def test_phase2_public_payloads_are_separated_from_hidden_truth():
    challenge_ids = sorted(p.stem for p in PUBLIC.glob("*.json"))
    assert len(challenge_ids) == 3, challenge_ids
    assert MANIFEST.exists(), "Phase 2 manifest must exist"

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["challenge_count"] == 3
    assert manifest["difficulty_band"] == "phase-2-hard"

    for challenge_id in challenge_ids:
        public = json.loads((PUBLIC / f"{challenge_id}.json").read_text(encoding="utf-8"))
        hidden = json.loads((GROUND / f"{challenge_id}.json").read_text(encoding="utf-8"))

        assert challenge_id == public["challenge_id"]
        assert "ground_truth" not in public
        assert "mechanism" in hidden
        assert public["deployment_configuration"]["local"] is True
        assert public["difficulty"] in {"LEVEL_5", "LEVEL_6", "LEVEL_7"}


def test_phase2_challenges_require_deeper_exploration_layers():
    challenge_ids = sorted(p.stem for p in PUBLIC.glob("*.json"))
    analysis_layers = []
    for challenge_id in challenge_ids:
        public = json.loads((PUBLIC / f"{challenge_id}.json").read_text(encoding="utf-8"))
        analysis_layers.extend(public["analysis_layers"])

    assert "source-analysis" in analysis_layers
    assert "state-control-data-flow" in analysis_layers
    assert "sequence-search" in analysis_layers
    assert "gas-resource-analysis" in analysis_layers
    assert "yul-ir-analysis" in analysis_layers
    assert "bytecode-opcode-analysis" in analysis_layers


def test_phase2_challenge_families_cover_advanced_mechanisms():
    challenge_ids = sorted(p.stem for p in PUBLIC.glob("*.json"))
    families = [json.loads((PUBLIC / f"{cid}.json").read_text(encoding="utf-8"))["family"] for cid in challenge_ids]
    assert "cross-function-state-entropy" in families
    assert "sequence-history-gas-drift" in families
    assert "abi-assembly-slot-ambiguity" in families
