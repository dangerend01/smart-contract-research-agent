from agents.benchmark_generator import (
    BenchmarkGenerator,
    BlindResearchBundle,
    ChallengeDefinition,
    create_blind_bundle,
    generate_challenge_suite,
)
from agents.evaluator import Evaluator


def test_generate_challenge_suite_has_levels_and_hidden_ground_truth():
    generator = BenchmarkGenerator(root="/workspaces/smart-contract-research-agent")
    suite = generator.generate_suite(levels=["LEVEL_1", "LEVEL_4"], seed=7)
    assert len(suite) >= 2
    assert suite[0]["challenge_id"].startswith("C-")
    assert "hidden_ground_truth" in suite[0]["ground_truth"]
    assert "hidden_ground_truth" not in suite[0]["blind_bundle"]


def test_blind_bundle_hides_solution_data():
    challenge = ChallengeDefinition(
        challenge_id="C-TEST-1",
        difficulty="LEVEL_3",
        contract_source="pragma solidity ^0.8.25; contract Demo { uint256 x; function f() external { x++; } }",
        deployment_configuration={"rpc": "local"},
        initial_state={"x": 0},
        available_functions=["f"],
        intended_invariants=["x should not be unbounded"],
        resource_model={"gas": "low"},
        hidden_ground_truth={"mechanism": "state-growth"},
        generation_seed=123,
    )
    blind = create_blind_bundle(challenge)
    assert "hidden_ground_truth" not in blind
    assert blind["contract_source"]


def test_evaluator_accepts_correct_mechanism_and_rejects_false_positive():
    evaluator = Evaluator()
    challenge = {
        "challenge_id": "C-TEST-2",
        "difficulty": "LEVEL_4",
        "ground_truth": {"mechanism": "state growth increases gas", "invariant": "gas should not scale with attacker-controlled state"},
    }
    correct = {"identified_mechanism": "state growth increases gas", "correct_root_cause": True, "reproducible": True}
    wrong = {"identified_mechanism": "reentrancy", "correct_root_cause": False, "reproducible": False}
    assert evaluator.evaluate(challenge, correct)["pass"] is True
    assert evaluator.evaluate(challenge, wrong)["pass"] is False


def test_deep_analysis_engine_tracks_layers_and_policy():
    from agents.deep_analysis import DeepAnalysisEngine
    engine = DeepAnalysisEngine()
    analysis = engine.analyze_source("contract Demo { uint256 x; function f() external { x++; } }", "Demo")
    assert "solidity_source" in analysis
    assert analysis["recommended_layers"]
    assert analysis["layer_policy"] == "escalate_to_lower_layers_only_when_needed"
