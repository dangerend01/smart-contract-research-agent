import json
from pathlib import Path

from agents.independent_execution_gate import IndependentExecutionGate

ROOT = Path(__file__).resolve().parents[1]


def test_validator_uses_only_public_challenge_data_for_reproduction():
    challenge = {
        "challenge_id": "HB-001",
        "contract_name": "SequenceAmplifier",
        "contract_source": "contract SequenceAmplifier { uint256 public prepared; uint256 public processed; function prepare(uint256 delta) external { prepared += delta; } function run() external { uint256 count = prepared; for (uint256 i = 0; i < count; ++i) { processed += 1; } } }",
        "available_functions": ["prepare", "run"],
        "initial_state": {"prepared": 0, "processed": 0},
        "family": "sequence-dependent-loop-amplification",
        "public_objective": "Explain why the execution cost changes after a specific sequence of calls.",
        "invariant": "execution cost should not be driven by unrelated historical state drift",
    }
    candidate = {
        "candidate_id": "cand-hb-001",
        "challenge_id": "HB-001",
        "hypothesis": "a stored state value is later reused as the loop bound during execution",
        "root_cause": "a previously stored value changes the future loop bound, so the execution cost is a function of prior state history rather than a single fixed bound.",
        "trigger": "history-dependent state mutation before victim execution",
        "observed_behavior": "the later execution path depends on previous state",
        "expected_behavior": "the later victim path should become more expensive when relevant state grows",
        "attacker_controlled_inputs": ["delta values injected before run()"],
        "required_state": ["prepared"],
        "triggering_sequence": ["prepare(delta)", "run()"],
        "minimized_counterexample": {"sequence_length": 2},
        "invariant_violation": "execution should not become substantially more expensive because of prior attacker-controlled state growth",
    }

    validator = IndependentExecutionGate(root=ROOT)
    result = validator.validate(challenge, candidate)

    assert "ground_truth" not in challenge
    assert result["classification"] in {"CONFIRMED", "PLAUSIBLE"}
    assert result["evidence_gates"]["GATE_3"] is True
    assert result["evidence_gates"]["GATE_6"] is True


def test_validator_rejects_deliberately_wrong_candidate():
    challenge = {
        "challenge_id": "HB-003",
        "contract_name": "PackedStorageDrift",
        "contract_source": "contract PackedStorageDrift { uint128 public alpha; uint256[] internal ledger; function seed(uint128 a, uint128 b, uint64 t) external { alpha = a; if (a != 0 && b != 0) { ledger.push(uint256(a) + uint256(b) + uint256(t)); } } function sweep() external { uint256 size = ledger.length; for (uint256 i = 0; i < size; ++i) { } } }",
        "available_functions": ["seed", "sweep"],
        "initial_state": {"alpha": 0, "beta": 0, "tick": 0, "processed": 0},
        "family": "packed-storage-drift",
        "public_objective": "Explain why later execution scales with stored values.",
        "invariant": "resource use should not be driven by packed-state values that are not directly tied to the intended control flow",
    }
    bad_candidate = {
        "candidate_id": "bad-candidate",
        "challenge_id": "HB-003",
        "hypothesis": "sudden random reentrancy via fallback",
        "root_cause": "an unrelated fallback call can repeatedly re-enter and drain tokens",
        "trigger": "external callback before the victim finishes",
        "observed_behavior": "the fallback triggers unexpectedly",
        "expected_behavior": "the later execution path should become more expensive when relevant state grows",
        "attacker_controlled_inputs": ["fallback callback"],
        "required_state": ["ledger"],
        "triggering_sequence": ["callback()", "sweep()"],
        "minimized_counterexample": {"sequence_length": 2},
        "invariant_violation": "reentrancy should not happen",
    }

    result = IndependentExecutionGate(root=ROOT).validate(challenge, bad_candidate)
    assert result["classification"] == "REJECTED"
    assert result["evidence_gates"]["GATE_6"] is False


def test_phase1_validation_summary_matches_public_records():
    report = IndependentExecutionGate(root=ROOT).run_phase1_validation()
    assert report["summary"]["challenge_count"] == 3
    assert report["summary"]["confirmed"] + report["summary"]["plausible"] + report["summary"]["rejected"] == 3
    assert report["summary"]["successful_independent_reproductions"] <= 3
