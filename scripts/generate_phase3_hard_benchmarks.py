#!/usr/bin/env python3
"""Generate the Phase 3 blind benchmark while preserving Phase 1 and 2 artifacts."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks"
GENERATED = BASE / "generated" / "hard-phase3"
GROUND_TRUTH = BASE / "ground-truth" / "hard-phase3"
MANIFESTS = BASE / "manifests" / "hard"

GENERATED.mkdir(parents=True, exist_ok=True)
GROUND_TRUTH.mkdir(parents=True, exist_ok=True)
MANIFESTS.mkdir(parents=True, exist_ok=True)

CHALLENGE_SOURCE = {
    "PH3-008": '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract CrossFunctionStateEntropyDrift {
    uint256 public epoch;
    uint256 public total;
    uint256 public last;
    uint256[] internal backlog;
    bool public active;

    function priming(uint256 left, uint256 right) external {
        active = true;
        epoch = left + right;
        last = right;
        backlog.push(left);
        backlog.push(right);
    }

    function trigger() external {
        if (!active) {
            return;
        }

        uint256 bound = epoch + last;
        uint256 length = backlog.length;
        for (uint256 i = 0; i < bound; ++i) {
            total += backlog[i % length];
        }
    }
}
''',
    "PH3-009": '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract StateHistoryMinerGasDrift {
    uint256 public score;
    uint256 public window;
    uint256[] internal history;

    function record(uint256 value) external {
        history.push(value);
        window += value;
    }

    function mine(uint256 bias) external {
        uint256 bound = window + bias;
        for (uint256 i = 0; i < history.length; ++i) {
            bound += history[i] % 13;
        }

        for (uint256 i = 0; i < bound; ++i) {
            score += 1;
        }
    }
}
''',
    "PH3-010": '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract AbiYulSlotAmbiguity {
    uint256 public slotA;
    uint256 public slotB;
    uint256 public processed;

    function prepare(uint256 left, uint256 right) external {
        slotA = left;
        slotB = right;
        assembly {
            sstore(0x40, left)
            sstore(0x41, right)
        }
    }

    function commit(bytes calldata data) external {
        uint256 offset;
        assembly {
            offset := calldataload(4)
        }

        uint256 bound = (slotA + slotB + offset) % 257;
        if (data.length > 0) {
            bound += uint256(uint8(data[0]));
        }

        for (uint256 i = 0; i < bound; ++i) {
            processed += 1;
        }
    }
}
''',
}

PUBLIC_CHALLENGES = {
    "PH3-008": {
        "challenge_id": "PH3-008",
        "family": "cross-function-state-entropy-drift",
        "difficulty": "LEVEL_8",
        "difficulty_classification": "multi-function state drift / history-sensitive loop",
        "mechanism_fingerprint": "cross-function-state->loop-bound-with-history",
        "seed": 3008,
        "contract_name": "CrossFunctionStateEntropyDrift",
        "contract_source": CHALLENGE_SOURCE["PH3-008"],
        "deployment_configuration": {"local": True, "deterministic": True, "solc": "0.8.25"},
        "available_functions": ["priming", "trigger"],
        "initial_state": {"epoch": 0, "total": 0, "last": 0, "active": False},
        "invariant": "execution cost should not become a hidden function of a prior priming sequence if the later operation is meant to be a bounded routine",
        "resource_model": {"gas": "state_history_dependent", "notes": "later work is derived from historical state created by a prior function"},
        "public_objective": "Find the sequence-dependent cost amplification caused by historical state created on one function and consumed by another.",
        "expected_evidence_requirements": [
            "ordered call trace",
            "state history before and after priming/trigger",
            "bound analysis",
            "reproduction of larger total cost after a specific sequence"
        ],
        "analysis_layers": [
            "source-analysis",
            "state-control-data-flow",
            "sequence-search",
            "gas-resource-analysis"
        ],
        "compiler_configuration": {"optimizer": True, "optimizer_runs": 200, "via_ir": False},
    },
    "PH3-009": {
        "challenge_id": "PH3-009",
        "family": "state-history-miner-gas-drift",
        "difficulty": "LEVEL_9",
        "difficulty_classification": "state history + resource drift + minimized sequence search",
        "mechanism_fingerprint": "history-growth->nonlinear-bound-amplification",
        "seed": 3009,
        "contract_name": "StateHistoryMinerGasDrift",
        "contract_source": CHALLENGE_SOURCE["PH3-009"],
        "deployment_configuration": {"local": True, "deterministic": True, "solc": "0.8.25"},
        "available_functions": ["record", "mine"],
        "initial_state": {"score": 0, "window": 0},
        "invariant": "an attacker should not be able to create a later runtime expansion by accumulating prior state and repeatedly feeding it into a later loop bound",
        "resource_model": {"gas": "sequence_sensitive_history_drift", "notes": "window and history values are folded into a growing later bound"},
        "public_objective": "Determine what sequence of historical calls makes mine() unexpectedly expensive and why the later bound changes with the previous state.",
        "expected_evidence_requirements": [
            "ordered history trace",
            "sequence comparison",
            "gas scaling across repeated record() calls",
            "counterexample minimization"
        ],
        "analysis_layers": [
            "source-analysis",
            "state-control-data-flow",
            "sequence-search",
            "gas-resource-analysis",
            "fuzzing-analysis"
        ],
        "compiler_configuration": {"optimizer": True, "optimizer_runs": 200, "via_ir": False},
    },
    "PH3-010": {
        "challenge_id": "PH3-010",
        "family": "abi-yul-slot-ambiguity",
        "difficulty": "LEVEL_10",
        "difficulty_classification": "ABI + EVM + Yul/IR + bytecode depth",
        "mechanism_fingerprint": "raw-calldata+assembly-slot-alias->loop-bound-amplification",
        "seed": 3010,
        "contract_name": "AbiYulSlotAmbiguity",
        "contract_source": CHALLENGE_SOURCE["PH3-010"],
        "deployment_configuration": {"local": True, "deterministic": True, "solc": "0.8.25"},
        "available_functions": ["prepare", "commit"],
        "initial_state": {"slotA": 0, "slotB": 0, "processed": 0},
        "invariant": "the execution cost should not silently depend on raw calldata and storage-slot aliasing hidden behind assembly-level data interpretation",
        "resource_model": {"gas": "calldata_and_slot_derived", "notes": "the loop bound depends on calldata offset and storage aliasing hidden from source-level reasoning"},
        "public_objective": "Explain why source-level reasoning is insufficient and why calldata and storage-slot state together determine the later execution cost.",
        "expected_evidence_requirements": [
            "state plus calldata trace",
            "Yul/IR or assembly explanation",
            "bytecode or opcode evidence when necessary",
            "runtime reproduction with a minimized input"
        ],
        "analysis_layers": [
            "source-analysis",
            "state-control-data-flow",
            "sequence-search",
            "gas-resource-analysis",
            "yul-ir-analysis",
            "bytecode-opcode-analysis"
        ],
        "compiler_configuration": {"optimizer": True, "optimizer_runs": 200, "via_ir": True},
    },
}

HIDDEN_TRUTH = {
    "PH3-008": {
        "challenge_id": "PH3-008",
        "difficulty": "LEVEL_8",
        "mechanism": "cross-function historical loop entanglement",
        "root_cause": "priming() stores historical values in epoch, last, and backlog. trigger() then uses epoch + last as the loop bound and iterates over backlog, turning earlier state into hidden work that is only visible when the sequence is enforced across calls.",
        "invariant": "the later routine should not consume hidden work created by a prior call sequence",
        "evidence_requirements": [
            "compare priming() then trigger() versus trigger() alone",
            "show the bound is driven by historical state values",
            "demonstrate larger total cost after a more expensive priming sequence"
        ],
        "reproducible_proof": {
            "steps": [
                "priming(3, 5)",
                "trigger()",
                "priming(10, 20)",
                "trigger()",
                "compare gas and total"
            ],
            "expected_result": "larger historical state yields a higher loop bound and more total work"
        },
        "mechanism_fingerprint": "cross-function-state->loop-bound-with-history",
        "difficulty_classification": "multi-function state drift / history-sensitive loop",
    },
    "PH3-009": {
        "challenge_id": "PH3-009",
        "difficulty": "LEVEL_9",
        "mechanism": "history-driven mining drift",
        "root_cause": "record() accumulates a historical sequence into window and history. mine() then sets a bound from window + bias and adds each historical value modulo 13, so the cost depends on the exact accumulated sequence and ordering of prior calls.",
        "invariant": "repeated record() calls should not silently transform a later work loop into a sequence-dependent amplification path",
        "evidence_requirements": [
            "measure cost across different record() histories",
            "show the loop bound depends on both window and stored sequence values",
            "show the need for minimization around the critical historical pattern"
        ],
        "reproducible_proof": {
            "steps": [
                "record(3)",
                "record(9)",
                "mine(0)",
                "record(18)",
                "mine(7)",
                "compare gas and score"
            ],
            "expected_result": "different accumulated histories produce materially different mine() costs and score growth"
        },
        "mechanism_fingerprint": "history-growth->nonlinear-bound-amplification",
        "difficulty_classification": "state history + resource drift + minimized sequence search",
    },
    "PH3-010": {
        "challenge_id": "PH3-010",
        "difficulty": "LEVEL_10",
        "mechanism": "assembly-level slot and calldata coupling",
        "root_cause": "prepare() writes slotA and slotB while also using assembly to store explicit slots. commit() reads calldataload(4) and combines it with the slot values and a leading byte of calldata to derive the final loop bound. The problem is not visible in pure Solidity semantics alone; it requires Yul/IR or bytecode inspection to see the hidden coupling.",
        "invariant": "a function should not secretly derive its cost from raw calldata and hidden slot aliases unless the system explicitly models those behaviors",
        "evidence_requirements": [
            "inspect the assembly block in prepare() and commit()",
            "show the raw calldata offset is used in the loop bound",
            "show the payload byte influences the loop bound",
            "confirm the dependency with Yul/IR or bytecode/opcode evidence"
        ],
        "reproducible_proof": {
            "steps": [
                "prepare(left, right)",
                "commit(data) with different leading bytes or calldata offsets",
                "compare gas and processed values",
                "confirm the loop bound is assembled from both state and ABI-level data"
            ],
            "expected_result": "small value or data shifts cause noticeably different work and gas use"
        },
        "mechanism_fingerprint": "raw-calldata+assembly-slot-alias->loop-bound-amplification",
        "difficulty_classification": "ABI + EVM + Yul/IR + bytecode depth",
    },
}

for challenge_id, payload in PUBLIC_CHALLENGES.items():
    public_path = GENERATED / f"{challenge_id}.json"
    public_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    gt_path = GROUND_TRUTH / f"{challenge_id}.json"
    gt = {
        "challenge_id": challenge_id,
        "difficulty": payload["difficulty"],
        "difficulty_classification": payload["difficulty_classification"],
        "mechanism_fingerprint": payload["mechanism_fingerprint"],
        **HIDDEN_TRUTH[challenge_id],
    }
    gt_path.write_text(json.dumps(gt, indent=2, sort_keys=True) + "\n", encoding="utf-8")

manifest = {
    "benchmark": "hard-phase3",
    "challenge_count": len(PUBLIC_CHALLENGES),
    "difficulty_band": "phase-3-hard",
    "challenge_ids": sorted(PUBLIC_CHALLENGES),
    "difficulty_levels": ["LEVEL_8", "LEVEL_9", "LEVEL_10"],
    "public_only": True,
    "notes": "Phase 3 measures real blind research performance against harder mechanisms, including cross-function state drift, sequence-sensitive gas amplification, and EVM/assembly-level data coupling.",
}

MANIFESTS.joinpath("hard-phase3-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"status": "ok", "benchmark": "hard-phase3", "challenge_count": len(PUBLIC_CHALLENGES)}, indent=2, sort_keys=True))
