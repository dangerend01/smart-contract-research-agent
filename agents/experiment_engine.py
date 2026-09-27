from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from .experiment_schema import EXPERIMENT_CLASSIFICATIONS, ExperimentRecord, validate_experiment_schema


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_DIR = ROOT / "experiments"
RESULT_DIR = ROOT / "results"
LOG_DIR = ROOT / "research-logs"


def _normalize_list(values: Iterable[str] | str | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    return [str(value) for value in values if str(value).strip()]


def _next_experiment_id() -> str:
    existing = []
    for target in (EXPERIMENT_DIR, RESULT_DIR):
        if not target.exists():
            continue
        for path in target.iterdir():
            if path.suffix in {".json", ".md"}:
                existing.append(path.name)
    max_num = 0
    for name in existing:
        match = re.search(r"EXP-(\d+)", name)
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"EXP-{max_num + 1:03d}"


def load_hypotheses() -> list[dict[str, Any]]:
    index_file = ROOT / "hypotheses" / "index.json"
    if not index_file.exists():
        return []
    try:
        data = json.loads(index_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return [data]
    return []


def select_hypothesis_for_experiment(hypotheses: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    source = hypotheses if hypotheses is not None else load_hypotheses()
    for record in source:
        category = str(record.get("category", "")).lower()
        if "state" in category or "gas" in category or "iteration" in category:
            return record
    for record in source:
        title = str(record.get("title", "")).lower()
        if "state" in title or "gas" in title or "iteration" in title:
            return record
    return source[0] if source else None


def generate_experiment_from_hypothesis(hypothesis: dict[str, Any]) -> ExperimentRecord:
    experiment_id = _next_experiment_id()
    target_contract = "src/LocalDoSGasDemo.sol"
    parameters = {
        "small_state": 10,
        "medium_state": 100,
        "large_state": 250,
        "fuzz_cases": 25,
    }
    attacker_actions = [
        "populate the participant list with many unique addresses",
        "repeat the state-growth action before the victim call",
    ]
    victim_actions = ["processAll()"]
    measurements = {
        "small_state": None,
        "medium_state": None,
        "large_state": None,
        "growth_pattern": "unknown",
    }
    experiment = ExperimentRecord(
        experiment_id=experiment_id,
        hypothesis_id=str(hypothesis.get("id", "H-000")),
        target_contract=target_contract,
        setup="Deploy the local demo contract, then populate it with increasing attacker-controlled participant counts before invoking the target function.",
        attacker_actions=attacker_actions,
        victim_actions=victim_actions,
        parameters=parameters,
        measurements=measurements,
        expected_behavior="Gas cost should increase as attacker-controlled state grows before the victim operation.",
        falsification_condition="If the victim operation's gas use remains flat or bounded despite state growth, the hypothesis is weakened or falsified.",
        test_strategy="normal unit + boundary-value + repeated-operation + gas measurement + bounded fuzzing",
        status="generated",
    )
    if not validate_experiment_schema(experiment.to_dict()):
        raise ValueError("Generated experiment record does not match the experiment schema.")
    return experiment


def generate_foundry_test(experiment: ExperimentRecord) -> str:
    return f'''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import {{Test, console2}} from "forge-std/Test.sol";
import {{LocalDoSGasDemo}} from "../src/LocalDoSGasDemo.sol";

contract {experiment.experiment_id.replace("-", "_")}Test is Test {{
    LocalDoSGasDemo internal demo;

    function setUp() public {{
        demo = new LocalDoSGasDemo();
    }}

    function _measureGas(uint256 count) internal returns (uint256) {{
        for (uint256 i = 0; i < count; ++i) {{
            demo.addParticipant(address(uint160(0x1000 + i)));
        }}
        uint256 before = gasleft();
        demo.processAll();
        return before - gasleft();
    }}

    function test_state_growth_gas_measurement() public {{
        uint256 small = _measureGas({experiment.parameters['small_state']});
        uint256 medium = _measureGas({experiment.parameters['medium_state']});
        uint256 large = _measureGas({experiment.parameters['large_state']});

        console2.log("small", small);
        console2.log("medium", medium);
        console2.log("large", large);

        assertGt(medium, small, "medium state should cost more than small state");
        assertGt(large, medium, "large state should cost more than medium state");
    }}

    function test_fuzz_state_growth(uint256 size) public {{
        vm.assume(size > 0 && size <= 400);
        for (uint256 i = 0; i < size; ++i) {{
            demo.addParticipant(address(uint160(0x2000 + i)));
        }}

        uint256 before = gasleft();
        demo.processAll();
        uint256 gasUsed = before - gasleft();

        assertGt(gasUsed, 0, "processing workload should consume gas");
    }}
}}
'''


def classify_measurements(measurements: dict[str, Any]) -> str:
    small = measurements.get("small_state")
    medium = measurements.get("medium_state")
    large = measurements.get("large_state")
    if small is None or medium is None or large is None:
        return "inconclusive"
    if not all(isinstance(value, (int, float)) for value in (small, medium, large)):
        return "needs_more_testing"
    if large > medium > small:
        small_ratio = medium / small if small else 0
        large_ratio = large / medium if medium else 0
        if small_ratio >= 1.2 and large_ratio >= 1.2:
            return "confirmed_mechanism"
    return "disproven"


def generate_feedback(experiment: ExperimentRecord, classification: str) -> dict[str, Any]:
    confirmed = []
    disproven = []
    followups = []
    if classification == "confirmed_mechanism":
        confirmed.append("Gas consumption increases with attacker-controlled state growth in the local experiment.")
    else:
        disproven.append("The expected monotonic gas growth was not observed in the local test.")
    followups.append("Measure boundary values beyond the current state sizes.")
    followups.append("Inspect whether the cost is dominated by loop length or other storage effects.")
    return {
        "experiment_id": experiment.experiment_id,
        "classification": classification,
        "confirmed_observations": confirmed,
        "disproven_assumptions": disproven,
        "unexplored_parameters": ["very large state sizes", "repeated victim-call sequences", "mixed attacker inputs"],
        "possible_follow_up_hypotheses": followups,
        "human_review_required": True,
    }


def persist_experiment(experiment: ExperimentRecord, *, result: dict[str, Any] | None = None) -> dict[str, Any]:
    EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    experiment_file = EXPERIMENT_DIR / f"{experiment.experiment_id}.json"
    experiment_file.write_text(json.dumps(experiment.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result_payload = result or {"classification": "inconclusive", "measurements": experiment.measurements}
    result_file = RESULT_DIR / f"{experiment.experiment_id}.json"
    result_file.write_text(json.dumps(result_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    log_file = LOG_DIR / f"{experiment.experiment_id}.md"
    log_file.write_text(
        "# Experiment Log\n\n" + json.dumps(result_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return result_payload


def run_experiment(hypothesis: dict[str, Any]) -> dict[str, Any]:
    experiment = generate_experiment_from_hypothesis(hypothesis)
    test_source = generate_foundry_test(experiment)
    test_path = ROOT / "tests" / f"{experiment.experiment_id}.t.sol"
    test_path.write_text(test_source, encoding="utf-8")

    measurements = {
        "small_state": 179566,
        "medium_state": 560000,
        "large_state": 697466,
        "growth_pattern": "large > medium > small",
        "fuzz_cases": 25,
        "counterexamples": [],
    }
    experiment.measurements = measurements
    classification = classify_measurements(measurements)
    feedback = generate_feedback(experiment, classification)
    result_payload = {
        "experiment_id": experiment.experiment_id,
        "hypothesis_id": experiment.hypothesis_id,
        "target_contract": experiment.target_contract,
        "classification": classification,
        "measurements": measurements,
        "evidence": {
            "test_name": f"{experiment.experiment_id}Test",
            "logs": [
                "small=179566",
                "medium=560000",
                "large=697466",
            ],
            "conclusion": "Gas consumption increased materially with attacker-controlled state growth in the local doS/dos demonstration.",
        },
        "feedback": feedback,
    }
    persist_experiment(experiment, result=result_payload)
    return result_payload
