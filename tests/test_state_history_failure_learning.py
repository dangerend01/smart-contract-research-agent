from agents.deep_evm_research_engine import DeepEVMResearchEngine


SOURCE = '''
pragma solidity ^0.8.24;

contract Example {
    uint256 public total;
    uint256 public lastSnapshot;
    uint256 public rewardPool;

    function contribute(uint256 amount) external {
        total += amount;
    }

    function checkpoint() external {
        lastSnapshot = total;
    }

    function settle() external {
        rewardPool += total - lastSnapshot;
        lastSnapshot = total;
    }
}
'''


def test_identifies_snapshot_and_baseline_variables():
    engine = DeepEVMResearchEngine()
    snapshot = engine.track_state_snapshots(SOURCE)

    assert snapshot["snapshot_variables"]
    assert "lastSnapshot" in snapshot["snapshot_variables"]
    assert any(item["role"] == "baseline" for item in snapshot["state_observations"])


def test_constructs_cross_function_state_dependencies():
    engine = DeepEVMResearchEngine()
    graph = engine.build_cross_function_graph(SOURCE)

    assert graph["edges"]
    assert any(edge["source"] == "contribute" and edge["target"] == "checkpoint" for edge in graph["edges"])
    assert any(edge["source"] == "checkpoint" and edge["target"] == "settle" for edge in graph["edges"])


def test_generates_stale_state_hypotheses_and_sequence_mutations():
    engine = DeepEVMResearchEngine()
    stale = engine.generate_stale_state_hypotheses(SOURCE)
    sequence_mutations = engine.generate_sequence_mutations(SOURCE)

    assert stale
    assert any("baseline" in item["title"].lower() or "snapshot" in item["title"].lower() for item in stale)
    assert any('A -> B -> C' in mutation["label"] or 'A -> B -> C -> D' in mutation["label"] for mutation in sequence_mutations)


def test_minimizes_counterexample_for_state_history_sequence():
    engine = DeepEVMResearchEngine()
    candidate = {
        "sequence": ["contribute", "checkpoint", "contribute", "checkpoint", "settle"],
        "inputs": {"amount": 100, "bonus": 1},
        "state": {"total": 200, "lastSnapshot": 100},
        "observed_invariant_violation": "growth counted twice",
    }

    minimized = engine.minimize_counterexample(candidate)

    assert minimized["sequence"]
    assert len(minimized["sequence"]) <= len(candidate["sequence"])
    assert "observed_invariant_violation" in minimized
