import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "benchmarks" / "generated" / "hard-phase4"
GROUND = ROOT / "benchmarks" / "ground-truth" / "hard-phase4"
MANIFEST = ROOT / "benchmarks" / "manifests" / "hard" / "hard-phase4-manifest.json"


def test_phase4_public_payloads_are_separated_from_hidden_truth():
    challenge_ids = sorted(p.stem for p in PUBLIC.glob("*.json"))
    assert len(challenge_ids) >= 4, challenge_ids
    assert MANIFEST.exists(), "Phase 4 manifest must exist"

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["difficulty_band"] == "phase-4-deep-evm-research"
    assert manifest["challenge_count"] >= 4

    for challenge_id in challenge_ids:
        public = json.loads((PUBLIC / f"{challenge_id}.json").read_text(encoding="utf-8"))
        hidden = json.loads((GROUND / f"{challenge_id}.json").read_text(encoding="utf-8"))

        assert challenge_id == public["challenge_id"]
        assert "ground_truth" not in public
        assert "mechanism" in hidden
        assert public["deployment_configuration"]["local"] is True
        assert public["difficulty"] in {"LEVEL_8", "LEVEL_9", "LEVEL_10", "LEVEL_11"}


def test_phase4_challenges_require_deep_evm_analysis_layers():
    challenge_ids = sorted(p.stem for p in PUBLIC.glob("*.json"))
    layers = []
    for challenge_id in challenge_ids:
        public = json.loads((PUBLIC / f"{challenge_id}.json").read_text(encoding="utf-8"))
        layers.extend(public["analysis_layers"])

    required = {
        "source-analysis",
        "state-control-data-flow",
        "sequence-search",
        "gas-resource-analysis",
        "yul-ir-analysis",
        "bytecode-opcode-analysis",
        "trace-differential-analysis",
    }
    missing = required - set(layers)
    assert not missing, missing


def test_phase4_challenge_families_cover_cross_layer_mechanisms():
    challenge_ids = sorted(p.stem for p in PUBLIC.glob("*.json"))
    families = [json.loads((PUBLIC / f"{cid}.json").read_text(encoding="utf-8"))["family"] for cid in challenge_ids]
    assert "cross-function-emergent-behavior" in families
    assert "state-history-dependent-behavior" in families
    assert "resource-amplification" in families
    assert "abi-storage-edge-cases" in families
