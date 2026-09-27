from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = ROOT / "benchmarks"
GENERATED_DIR = BENCHMARK_ROOT / "generated"
GROUND_TRUTH_DIR = BENCHMARK_ROOT / "ground-truth"
MANIFEST_DIR = BENCHMARK_ROOT / "manifests"
REPORTS_DIR = BENCHMARK_ROOT / "reports"
PUBLIC_DIR = BENCHMARK_ROOT / "public"


LEVELS = {
    "LEVEL_1": "obvious",
    "LEVEL_2": "composed",
    "LEVEL_3": "stateful",
    "LEVEL_4": "resource/gas",
    "LEVEL_5": "adversarial",
    "LEVEL_6": "research",
    "LEVEL_7": "deep implementation",
}


@dataclass
class ChallengeDefinition:
    challenge_id: str
    difficulty: str
    contract_source: str
    deployment_configuration: dict[str, Any]
    initial_state: dict[str, Any]
    available_functions: list[str]
    intended_invariants: list[str]
    resource_model: dict[str, Any]
    hidden_ground_truth: dict[str, Any]
    generation_seed: int

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["difficulty_label"] = LEVELS.get(self.difficulty, self.difficulty)
        return data


@dataclass
class BlindResearchBundle:
    challenge_id: str
    difficulty: str
    contract_source: str
    deployment_configuration: dict[str, Any]
    initial_state: dict[str, Any]
    available_functions: list[str]
    intended_invariants: list[str]
    resource_model: dict[str, Any]
    generation_seed: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def create_blind_bundle(challenge: ChallengeDefinition | dict[str, Any]) -> dict[str, Any]:
    if isinstance(challenge, dict):
        challenge_obj = ChallengeDefinition(
            challenge_id=str(challenge.get("challenge_id", "C-UNKNOWN")),
            difficulty=str(challenge.get("difficulty", "LEVEL_1")),
            contract_source=str(challenge.get("contract_source", "")),
            deployment_configuration=dict(challenge.get("deployment_configuration", {})),
            initial_state=dict(challenge.get("initial_state", {})),
            available_functions=list(challenge.get("available_functions", [])),
            intended_invariants=list(challenge.get("intended_invariants", [])),
            resource_model=dict(challenge.get("resource_model", {})),
            hidden_ground_truth=dict(challenge.get("hidden_ground_truth", {})),
            generation_seed=int(challenge.get("generation_seed", 0)),
        )
    else:
        challenge_obj = challenge

    return BlindResearchBundle(
        challenge_id=challenge_obj.challenge_id,
        difficulty=challenge_obj.difficulty,
        contract_source=challenge_obj.contract_source,
        deployment_configuration=challenge_obj.deployment_configuration,
        initial_state=challenge_obj.initial_state,
        available_functions=challenge_obj.available_functions,
        intended_invariants=challenge_obj.intended_invariants,
        resource_model=challenge_obj.resource_model,
        generation_seed=challenge_obj.generation_seed,
    ).to_dict()


class BenchmarkGenerator:
    def __init__(self, root: str | Path = ROOT):
        self.root = Path(root)
        self.benchmark_root = self.root / "benchmarks"
        for directory in [GENERATED_DIR, GROUND_TRUTH_DIR, MANIFEST_DIR, REPORTS_DIR, PUBLIC_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

    def _template_contract(self, challenge_id: str, difficulty: str, seed: int) -> ChallengeDefinition:
        if difficulty == "LEVEL_1":
            contract = '''
            // SPDX-License-Identifier: MIT
            pragma solidity ^0.8.25;
            contract {name} {{
                address[] public participants;
                mapping(address => bool) public seen;
                uint256 public processed;
                function addParticipant(address account) external {{
                    require(account != address(0));
                    if (!seen[account]) {{ seen[account] = true; participants.push(account); }}
                }}
                function processAll() external {{
                    for (uint256 i = 0; i < participants.length; ++i) {{
                        if (participants[i] != address(0)) processed += 1;
                    }}
                }}
            }}
            '''.replace("{name}", challenge_id.replace("-", "_"))
            ground_truth = {
                "mechanism": "state growth increases gas",
                "root_cause": "iteration over attacker-controlled storage grows with participants array length",
                "difficulty_reason": "The issue is local, measurable, and depends on state growth rather than a textbook exploit signature.",
                "invariant": "gas should not scale with attacker-controlled state",
                "resource_affected": "gas",
                "affected_functions": ["addParticipant", "processAll"],
                "failure_mode": "resource amplification",
                "layer": "solidity-source",
            }
            return ChallengeDefinition(
                challenge_id=challenge_id,
                difficulty=difficulty,
                contract_source=contract,
                deployment_configuration={"address_count": 10, "local": True},
                initial_state={"participants": [], "processed": 0},
                available_functions=["addParticipant", "processAll"],
                intended_invariants=["gas should not scale with attacker-controlled state"],
                resource_model={"gas": "linear_in_state_size"},
                hidden_ground_truth=ground_truth,
                generation_seed=seed,
            )

        if difficulty == "LEVEL_4":
            contract = '''
            // SPDX-License-Identifier: MIT
            pragma solidity ^0.8.25;
            contract {name} {{
                address[] private queue;
                uint256 public total;
                uint256 public epoch;
                function push(address account) external {{
                    if (account != address(0)) {{ queue.push(account); }}
                }}
                function settle() external {{
                    uint256 count = queue.length;
                    for (uint256 i = 0; i < count; ++i) {{
                        total += 1;
                        if (i % 2 == 0) {{ epoch += 1; }}
                    }}
                }}
            }}
            '''.replace("{name}", challenge_id.replace("-", "_"))
            ground_truth = {
                "mechanism": "state growth increases gas through repeated loop work",
                "root_cause": "settle iterates on queue length and expands additional state writes as the queue grows",
                "difficulty_reason": "The mechanism depends on state growth and repeated resource amplification rather than a textbook well-known bug.",
                "invariant": "processing cost should not grow with attacker-controlled queue size",
                "resource_affected": "gas",
                "affected_functions": ["push", "settle"],
                "failure_mode": "resource amplification",
                "layer": "source-and-measurement",
            }
            return ChallengeDefinition(
                challenge_id=challenge_id,
                difficulty=difficulty,
                contract_source=contract,
                deployment_configuration={"local": True, "state_reset": True},
                initial_state={"queue": [], "total": 0, "epoch": 0},
                available_functions=["push", "settle"],
                intended_invariants=["processing cost should not grow with attacker-controlled queue size"],
                resource_model={"gas": "linear_with_queue_length_and_state_writes"},
                hidden_ground_truth=ground_truth,
                generation_seed=seed,
            )

        contract = '''
        // SPDX-License-Identifier: MIT
        pragma solidity ^0.8.25;
        contract {name} {{
            uint256 public state;
            uint256 public step;
            function first(uint256 x) external {{
                state += x;
                step += 1;
            }}
            function second() external {{
                if (state > 0) {{
                    uint256 loopCount = state;
                    for (uint256 i = 0; i < loopCount; ++i) {{
                        step += 1;
                    }}
                }}
            }}
        }}
        '''.replace("{name}", challenge_id.replace("-", "_"))
        ground_truth = {
            "mechanism": "cross-function state dependency",
            "root_cause": "state from one function modifies the loop bounds of another function and turns a bounded operation into a state-dependent amplification path",
            "difficulty_reason": "The issue relies on ordered function interaction and state history rather than a classic isolated bug.",
            "invariant": "sequence of operations should not create unexpected resource amplification",
            "resource_affected": "gas",
            "affected_functions": ["first", "second"],
            "failure_mode": "stateful cross-function amplification",
            "layer": "source-and-sequence",
        }
        return ChallengeDefinition(
            challenge_id=challenge_id,
            difficulty=difficulty,
            contract_source=contract,
            deployment_configuration={"local": True, "sequence_enabled": True},
            initial_state={"state": 0, "step": 0},
            available_functions=["first", "second"],
            intended_invariants=["sequence of operations should not create unexpected resource amplification"],
            resource_model={"gas": "depends_on_state_history"},
            hidden_ground_truth=ground_truth,
            generation_seed=seed,
        )

    def generate_suite(self, *, levels: Iterable[str] | None = None, seed: int = 1) -> list[dict[str, Any]]:
        selected_levels = list(levels or ["LEVEL_1", "LEVEL_3", "LEVEL_4", "LEVEL_6", "LEVEL_7"])
        suite: list[dict[str, Any]] = []
        for index, level in enumerate(selected_levels, start=1):
            challenge_id = f"C-{level}-{index:03d}"
            challenge = self._template_contract(challenge_id, level, seed + index)
            blind_bundle = create_blind_bundle(challenge)
            payload = {
                "challenge_id": challenge.challenge_id,
                "difficulty": challenge.difficulty,
                "blind_bundle": blind_bundle,
                "ground_truth": {
                    "hidden_ground_truth": challenge.hidden_ground_truth,
                    "mechanism": challenge.hidden_ground_truth.get("mechanism"),
                    "root_cause": challenge.hidden_ground_truth.get("root_cause"),
                    "invariant": challenge.hidden_ground_truth.get("invariant"),
                },
                "contract_source": challenge.contract_source,
                "deployment_configuration": challenge.deployment_configuration,
                "initial_state": challenge.initial_state,
                "available_functions": challenge.available_functions,
                "intended_invariants": challenge.intended_invariants,
                "resource_model": challenge.resource_model,
                "generation_seed": challenge.generation_seed,
            }
            suite.append(payload)
            self._persist_challenge(challenge, blind_bundle)
        self._persist_manifest(suite)
        return suite

    def _persist_challenge(self, challenge: ChallengeDefinition, blind_bundle: dict[str, Any]) -> None:
        generated_path = GENERATED_DIR / f"{challenge.challenge_id}.json"
        generated_path.write_text(json.dumps({
            "challenge_id": challenge.challenge_id,
            "difficulty": challenge.difficulty,
            "blind_bundle": blind_bundle,
            "contract_source": challenge.contract_source,
            "deployment_configuration": challenge.deployment_configuration,
            "initial_state": challenge.initial_state,
            "available_functions": challenge.available_functions,
            "intended_invariants": challenge.intended_invariants,
            "resource_model": challenge.resource_model,
            "generation_seed": challenge.generation_seed,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        gt_path = GROUND_TRUTH_DIR / f"{challenge.challenge_id}.json"
        gt_path.write_text(json.dumps({
            "challenge_id": challenge.challenge_id,
            "difficulty": challenge.difficulty,
            "ground_truth": challenge.hidden_ground_truth,
            "generation_seed": challenge.generation_seed,
        }, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _persist_manifest(self, suite: list[dict[str, Any]]) -> None:
        manifest = {
            "generated_at": "local",
            "challenge_count": len(suite),
            "challenges": [
                {
                    "challenge_id": item["challenge_id"],
                    "difficulty": item["difficulty"],
                    "generation_seed": item["generation_seed"],
                }
                for item in suite
            ],
        }
        (MANIFEST_DIR / "benchmark-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def generate_report(self, suite: list[dict[str, Any]], *, title: str = "benchmark report") -> dict[str, Any]:
        report = {
            "title": title,
            "total_challenges": len(suite),
            "difficulties": sorted({item["difficulty"] for item in suite}),
            "challenge_ids": [item["challenge_id"] for item in suite],
        }
        (REPORTS_DIR / "benchmark-report.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return report


def generate_challenge_suite(*, levels: Iterable[str] | None = None, seed: int = 1, root: str | Path = ROOT) -> list[dict[str, Any]]:
    return BenchmarkGenerator(root=root).generate_suite(levels=levels, seed=seed)
