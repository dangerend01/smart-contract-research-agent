import json
from pathlib import Path

from agents.experiment_engine import (
    classify_measurements,
    generate_experiment_from_hypothesis,
    generate_foundry_test,
    generate_feedback,
    load_hypotheses,
    run_experiment,
    select_hypothesis_for_experiment,
)
from agents.experiment_schema import validate_experiment_schema


ROOT = Path(__file__).resolve().parents[1]


def test_experiment_schema_validation():
    record = {
        "experiment_id": "EXP-001",
        "hypothesis_id": "H-006",
        "target_contract": "src/LocalDoSGasDemo.sol",
        "setup": "Deploy local demo.",
        "attacker_actions": ["grow list"],
        "victim_actions": ["processAll()"],
        "parameters": {"small_state": 10},
        "measurements": {"small_state": 1},
        "expected_behavior": "higher gas with bigger size",
        "falsification_condition": "flat behavior indicates falsified hypothesis",
        "test_strategy": "gas measurement",
        "status": "generated",
    }
    assert validate_experiment_schema(record) is True


def test_experiment_generation_from_hypothesis():
    hypotheses = load_hypotheses()
    selected = select_hypothesis_for_experiment(hypotheses)
    assert selected is not None
    experiment = generate_experiment_from_hypothesis(selected)
    assert experiment.experiment_id.startswith("EXP-")
    assert experiment.hypothesis_id == selected.get("id")
    assert "processAll" in "\n".join(experiment.victim_actions)


def test_generated_forge_test_contains_measurement_and_fuzz():
    hypothesis = load_hypotheses()[0]
    experiment = generate_experiment_from_hypothesis(hypothesis)
    source = generate_foundry_test(experiment)
    assert "test_state_growth_gas_measurement" in source
    assert "test_fuzz_state_growth" in source
    assert "vm.assume" in source


def test_measurement_classification():
    measurements = {"small_state": 10, "medium_state": 40, "large_state": 100}
    assert classify_measurements(measurements) == "confirmed_mechanism"

    flat = {"small_state": 10, "medium_state": 11, "large_state": 12}
    assert classify_measurements(flat) == "disproven"


def test_feedback_generation():
    hypothesis = load_hypotheses()[0]
    experiment = generate_experiment_from_hypothesis(hypothesis)
    feedback = generate_feedback(experiment, "confirmed_mechanism")
    assert feedback["classification"] == "confirmed_mechanism"
    assert "possible_follow_up_hypotheses" in feedback
    assert feedback["human_review_required"] is True


def test_experiment_execution_persists_result():
    hypotheses = load_hypotheses()
    selected = select_hypothesis_for_experiment(hypotheses)
    result = run_experiment(selected)
    assert result["classification"] == "confirmed_mechanism"
    assert result["measurements"]["large_state"] > result["measurements"]["small_state"]
