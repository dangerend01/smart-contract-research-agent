import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "benchmarks" / "generated" / "hard-phase3"
GROUND = ROOT / "benchmarks" / "ground-truth" / "hard-phase3"
MANIFEST = ROOT / "benchmarks" / "manifests" / "hard" / "hard-phase3-manifest.json"


def test_phase3_public_payloads_are_separated_from_hidden_truth():
    challenge_ids = sorted(p.stem for p in PUBLIC.glob("*.json"))
    assert len(challenge_ids) == 3, challenge_ids
    assert MANIFEST.exists(), "Phase 3 manifest must exist"

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["challenge_count"] == 3
    assert manifest["difficulty_band"] == "phase-3-hard"

    for challenge_id in challenge_ids:
        public = json.loads((PUBLIC / f"{challenge_id}.json").read_text(encoding="utf-8"))
        hidden = json.loads((GROUND / f"{challenge_id}.json").read_text(encoding="utf-8"))

        assert challenge_id == public["challenge_id"]
        assert "ground_truth" not in public
        assert "mechanism" in hidden
        assert public["deployment_configuration"]["local"] is True
        assert public["difficulty"] in {"LEVEL_8", "LEVEL_9", "LEVEL_10"}


def test_phase3_challenges_require_deeper_or_bytecode_analysis():
    challenge_ids = sorted(p.stem for p in PUBLIC.glob("*.json"))
    layers = []
    for challenge_id in challenge_ids:
        public = json.loads((PUBLIC / f"{challenge_id}.json").read_text(encoding="utf-8"))
        layers.extend(public["analysis_layers"])

    assert "source-analysis" in layers
    assert "state-control-data-flow" in layers
    assert "sequence-search" in layers
    assert "gas-resource-analysis" in layers
    assert "yul-ir-analysis" in layers
    assert "bytecode-opcode-analysis" in layers


def test_phase3_challenge_families_cover_deeper_local_mechanisms():
    challenge_ids = sorted(p.stem for p in PUBLIC.glob("*.json"))
    families = [json.loads((PUBLIC / f"{cid}.json").read_text(encoding="utf-8"))["family"] for cid in challenge_ids]
    assert "cross-function-state-entropy-drift" in families
    assert "state-history-miner-gas-drift" in families
    assert "abi-yul-slot-ambiguity" in families
