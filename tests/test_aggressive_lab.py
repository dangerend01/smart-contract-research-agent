import json
from pathlib import Path

from agents.aggressive_lab import AggressiveResearchLab
from agents.self_improvement import SelfImprovementEngine

ROOT = Path(__file__).resolve().parents[1]


def test_success_learning_generates_follow_up_hypotheses():
    engine = SelfImprovementEngine(ROOT)
    result = {
        "classification": "confirmed_mechanism",
        "hypothesis_id": "H-001",
        "experiment_id": "EXP-100",
        "measurements": {"small_state": 50, "medium_state": 140, "large_state": 220},
        "feedback": {"classification": "confirmed_mechanism"},
    }
    learning = engine.learn_success({"id": "H-001", "title": "state-growth demo", "mechanism": "loop over dynamic state"}, result)
    assert learning["important_preconditions"]
    assert learning["follow_up_hypotheses"]


def test_failure_taxonomy_and_disproven_learning():
    engine = SelfImprovementEngine(ROOT)
    result = {
        "classification": "disproven",
        "hypothesis_id": "H-002",
        "experiment_id": "EXP-101",
        "measurements": {"small_state": 10, "medium_state": 11, "large_state": 12},
        "feedback": {"disproven_assumptions": ["gas did not scale as assumed"]},
    }
    failure = engine.learn_failure({"id": "H-002", "title": "failed demo"}, result)
    assert failure["failure_taxonomy"] == "GAS_NOT_SCALING"
    assert failure["modified_hypotheses"]


def test_strategy_selection_uses_prior_history():
    engine = SelfImprovementEngine(ROOT)
    historical_state = {
        "cycles": [
            {"strategies_used": [{"name": "state-growth strategy", "score": 8.0}]},
            {"strategies_used": [{"name": "boundary-value strategy", "score": 1.5}]},
        ]
    }
    assert engine.choose_strategy(0.35, historical_state) == "state-growth strategy"


def test_mutations_are_deduplicated_and_variant_specific():
    engine = SelfImprovementEngine(ROOT)
    base = {
        "id": "H-010",
        "title": "state-growth experiment",
        "mechanism": "loop over dynamic state",
        "attack_sequence": ["grow state"],
        "parameters": {"small_state": 15},
    }
    mutations = engine.generate_mutations(base, {"classification": "confirmed_mechanism"})
    titles = [item["title"] for item in mutations]
    assert len(titles) == len(set(titles))
    assert any("nested iteration" in title.lower() for title in titles)
    assert any("state-history" in title.lower() for title in titles)


def test_counterexample_minimization_reduces_parameter_size():
    engine = SelfImprovementEngine(ROOT)
    candidate = {
        "parameters": {"small_state": 100, "medium_state": 200, "large_state": 500},
        "attack_sequence": ["a", "b", "c", "d", "e"],
    }
    minimized = engine.minimize_counterexample(candidate)
    assert minimized["parameters"]["small_state"] < 100
    assert len(minimized["attack_sequence"]) < len(candidate["attack_sequence"])


def test_aggressive_lab_cycle_persists_record():
    lab = AggressiveResearchLab(ROOT, max_hypotheses=2, max_experiments=2)
    cycle = lab.run_cycle(1)
    assert cycle["cycle_id"] == "research-cycle-001"
    assert cycle["executed_experiments"]
    assert (ROOT / "research_memory" / "research-cycle-001.json").exists()


def test_cycle_evaluation_metrics_are_present():
    engine = SelfImprovementEngine(ROOT)
    cycle = {
        "hypotheses_generated": 4,
        "executed_experiments": [
            {"hypothesis_id": "H-001", "classification": "confirmed_mechanism"},
            {"hypothesis_id": "H-002", "classification": "disproven"},
            {"hypothesis_id": "H-001", "classification": "confirmed_mechanism"},
        ],
        "minimized_counterexamples": 1,
        "strategy_effectiveness": 0.75,
        "repeated_failure_rate": 0.12,
        "unexplored_areas": ["state-history strategy"],
        "coverage": {"functions": ["addParticipant"], "invariants": ["gas scaling"]},
    }
    metrics = engine.evaluate_cycle(cycle)
    assert metrics["experiments_executed"] == 3
    assert metrics["confirmed_mechanisms"] == 2
    assert metrics["disproven_hypotheses"] == 1
