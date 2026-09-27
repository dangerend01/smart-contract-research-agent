import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase5_differential_campaign_uses_existing_frontier_and_records_builds():
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from agents.deep_evm_research_engine import DeepEVMResearchEngine

    campaign = DeepEVMResearchEngine()
    challenge = json.loads((ROOT / "benchmarks" / "generated" / "hard-phase4" / "PH4-011.json").read_text(encoding="utf-8"))

    result = campaign.run_phase5(challenge)

    assert result["challenge_id"] == "PH4-011"
    assert result["experiments"]
    assert result["compiler_differences"]
    assert result["deepest_layer_reached"] in {"bytecode-analysis", "trace-differential-analysis", "compiler-differential-analysis"}
    assert "optimiser" in result["compiler_differences"][0]["note"].lower() or "optimizer" in result["compiler_differences"][0]["note"].lower()


def test_phase5_minimizer_preserves_smallest_reproducer_for_state_history_case():
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from agents.deep_evm_research_engine import CounterexampleMinimizer

    minimizer = CounterexampleMinimizer()
    candidate = {
        "input_values": {"seed": 8, "delta": 4, "bias": 64},
        "state_size": 8,
        "sequence": ["prime", "settle"],
        "calldata_size": 96,
        "notes": "state-history reproduction with repeated growth",
    }

    reduced = minimizer.minimize(candidate)

    assert reduced["state_size"] <= candidate["state_size"]
    assert reduced["sequence"] in (["prime", "settle"], ["settle"], ["prime"])
    assert reduced["calldata_size"] <= candidate["calldata_size"]
