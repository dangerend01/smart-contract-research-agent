#!/usr/bin/env python3
"""Generate the Phase 4 deep EVM research benchmarks while preserving earlier benchmark artifacts."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks"
GENERATED = BASE / "generated" / "hard-phase4"
GROUND_TRUTH = BASE / "ground-truth" / "hard-phase4"
MANIFESTS = BASE / "manifests" / "hard"

GENERATED.mkdir(parents=True, exist_ok=True)
GROUND_TRUTH.mkdir(parents=True, exist_ok=True)
MANIFESTS.mkdir(parents=True, exist_ok=True)

CHALLENGE_SOURCE = {
    "PH4-011": '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract CrossFunctionEmergentBehavior {
    uint256 public epoch;
    uint256 public total;
    uint256[] internal backlog;
    bool public enabled;

    function prime(uint256 seed, uint256 delta) external {
        enabled = true;
        epoch = seed + delta;
        backlog.push(seed);
        backlog.push(delta);
    }

    function settle() external {
        if (!enabled) return;

        uint256 bound = epoch + backlog.length;
        for (uint256 i = 0; i < bound; ++i) {
            total += backlog[i % backlog.length];
        }
    }
}
''',
    "PH4-012": '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract StateHistoryDependentBehavior {
    uint256 public score;
    uint256 public window;
    uint256[] internal history;

    function record(uint256 value) external {
        history.push(value);
        window += value;
    }

    function evaluate(uint256 bias) external {
        uint256 bound = window + bias;
        for (uint256 i = 0; i < history.length; ++i) {
            bound += history[i] % 19;
        }

        for (uint256 i = 0; i < bound; ++i) {
            score += 1;
        }
    }
}
''',
    "PH4-013": '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract ResourceAmplification {
    uint256[] private tracker;
    uint256 public consumed;

    function add(uint256 value) external {
        if (value > 0) {
            tracker.push(value);
            consumed += value;
        }
    }

    function drain() external {
        uint256 bound = tracker.length;
        for (uint256 i = 0; i < bound; ++i) {
            for (uint256 j = 0; j < tracker[i] % 17; ++j) {
                consumed += 1;
            }
        }
    }
}
''',
    "PH4-014": '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract AbiStorageEdgeCases {
    uint256 public slotA;
    uint256 public slotB;
    uint256 public processed;

    function seed(uint256 left, uint256 right) external {
        slotA = left;
        slotB = right;
        assembly {
            sstore(0x40, left)
            sstore(0x41, right)
        }
    }

    function execute(bytes calldata data) external {
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
    "PH4-011": {
        "challenge_id": "PH4-011",
        "family": "cross-function-emergent-behavior",
        "difficulty": "LEVEL_8",
        "difficulty_classification": "cross-function state carry + emergent loop amplification",
        "mechanism_fingerprint": "cross-function-state->loop-bound-emergence",
        "seed": 4011,
        "contract_name": "CrossFunctionEmergentBehavior",
        "contract_source": CHALLENGE_SOURCE["PH4-011"],
        "deployment_configuration": {"local": True, "deterministic": True, "solc": "0.8.25"},
        "available_functions": ["prime", "settle"],
        "initial_state": {"epoch": 0, "total": 0, "enabled": False},
        "invariant": "resource use should not silently depend on earlier state history when the later function appears to do a simple bounded loop",
        "resource_model": {"gas": "history-dependent loop amplification", "notes": "prime() populates state, settle() derives its bound from earlier values"},
        "public_objective": "Explain why later processing becomes more expensive after a specific state-history sequence and why this is an emergent cross-function mechanism.",
        "expected_evidence_requirements": [
            "state-history trace",
            "ordered call sequence",
            "loop-bound derivation",
            "minimized reproducer"
        ],
        "analysis_layers": [
            "source-analysis",
            "state-control-data-flow",
            "sequence-search",
            "gas-resource-analysis",
            "yul-ir-analysis",
            "bytecode-opcode-analysis",
            "trace-differential-analysis",
            "compiler-differential-analysis",
            "semantic-differential-analysis",
        ],
        "compiler_configuration": {"optimizer": True, "optimizer_runs": 200, "via_ir": False},
    },
    "PH4-012": {
        "challenge_id": "PH4-012",
        "family": "state-history-dependent-behavior",
        "difficulty": "LEVEL_9",
        "difficulty_classification": "history-sensitive execution and state carry",
        "mechanism_fingerprint": "history-growth->nonlinear-bound-amplification",
        "seed": 4012,
        "contract_name": "StateHistoryDependentBehavior",
        "contract_source": CHALLENGE_SOURCE["PH4-012"],
        "deployment_configuration": {"local": True, "deterministic": True, "solc": "0.8.25"},
        "available_functions": ["record", "evaluate"],
        "initial_state": {"score": 0, "window": 0},
        "invariant": "evaluation cost should not unexpectedly become a function of the entire stored call history and a broader repeated state machine",
        "resource_model": {"gas": "sequence-sensitive state amplification", "notes": "history and window are folded into a later bound"},
        "public_objective": "Find the precise sequence-dependent amplification and explain why a later call becomes more expensive after earlier history was accumulated.",
        "expected_evidence_requirements": [
            "historical state trace",
            "sequence minimization",
            "algorithmic bound derivation",
            "runtime comparison across histories"
        ],
        "analysis_layers": [
            "source-analysis",
            "state-control-data-flow",
            "sequence-search",
            "gas-resource-analysis",
            "yul-ir-analysis",
            "bytecode-opcode-analysis",
            "trace-differential-analysis",
            "compiler-differential-analysis",
            "semantic-differential-analysis",
        ],
        "compiler_configuration": {"optimizer": True, "optimizer_runs": 200, "via_ir": False},
    },
    "PH4-013": {
        "challenge_id": "PH4-013",
        "family": "resource-amplification",
        "difficulty": "LEVEL_10",
        "difficulty_classification": "resource amplification + state growth + multi-layer observation",
        "mechanism_fingerprint": "state-growth->nested-loop-amplification",
        "seed": 4013,
        "contract_name": "ResourceAmplification",
        "contract_source": CHALLENGE_SOURCE["PH4-013"],
        "deployment_configuration": {"local": True, "deterministic": True, "solc": "0.8.25"},
        "available_functions": ["add", "drain"],
        "initial_state": {"tracker": [], "consumed": 0},
        "invariant": "small attacker-controlled inputs should not create a disproportionate later resource cost when the system processes stored state",
        "resource_model": {"gas": "superlinear growth under repeated state accumulation", "notes": "drain() multiplies each stored value by its modulo-derived loop count"},
        "public_objective": "Explain why a later drain() becomes unexpectedly expensive after repeated small additions and why the growth is state-dependent rather than constant.",
        "expected_evidence_requirements": [
            "growth trace",
            "loop-bound analysis",
            "resource comparison across different histories",
            "counterexample minimization"
        ],
        "analysis_layers": [
            "source-analysis",
            "state-control-data-flow",
            "sequence-search",
            "gas-resource-analysis",
            "yul-ir-analysis",
            "bytecode-opcode-analysis",
            "trace-differential-analysis",
            "compiler-differential-analysis",
            "semantic-differential-analysis",
        ],
        "compiler_configuration": {"optimizer": True, "optimizer_runs": 200, "via_ir": False},
    },
    "PH4-014": {
        "challenge_id": "PH4-014",
        "family": "abi-storage-edge-cases",
        "difficulty": "LEVEL_11",
        "difficulty_classification": "ABI + storage + assembly + bytecode semantics",
        "mechanism_fingerprint": "calldata+assembly-slot-aliasing->resource-amplification",
        "seed": 4014,
        "contract_name": "AbiStorageEdgeCases",
        "contract_source": CHALLENGE_SOURCE["PH4-014"],
        "deployment_configuration": {"local": True, "deterministic": True, "solc": "0.8.25"},
        "available_functions": ["seed", "execute"],
        "initial_state": {"slotA": 0, "slotB": 0, "processed": 0},
        "invariant": "execution should not silently depend on ABI-level raw calldata and hidden storage-slot behavior in a way that source-level reasoning cannot explain",
        "resource_model": {"gas": "calldata-and-storage-derived work expansion", "notes": "execute() combines raw calldataload offset with assembly-written slots and leading calldata bytes"},
        "public_objective": "Explain the hidden coupling between ABI-level input interpretation and storage representation, and show how the actual cost is determined by more than source semantics reveal.",
        "expected_evidence_requirements": [
            "calldata trace",
            "storage interaction analysis",
            "assembly or Yul explanation",
            "bytecode/opcode evidence when needed"
        ],
        "analysis_layers": [
            "source-analysis",
            "state-control-data-flow",
            "sequence-search",
            "gas-resource-analysis",
            "yul-ir-analysis",
            "bytecode-opcode-analysis",
            "trace-differential-analysis",
            "compiler-differential-analysis",
            "semantic-differential-analysis",
        ],
        "compiler_configuration": {"optimizer": True, "optimizer_runs": 200, "via_ir": True},
    },
}

HIDDEN_TRUTH = {
    "PH4-011": {
        "challenge_id": "PH4-011",
        "difficulty": "LEVEL_8",
        "mechanism": "cross-function emergent behavior",
        "root_cause": "prime() populates stored values and later settle() derives its loop bound from epoch and backlog length. The cost is not fixed by a single function; it emerges from earlier state history and later function composition.",
        "invariant": "state machine behavior must remain explainable and bounded even when the same values are reused across multiple calls",
        "evidence_requirements": [
            "compare prime() followed by settle() against settle() alone",
            "show the loop bound depends on both historical state and backlog length",
            "demonstrate the cross-function composition effect"
        ],
        "mechanism_fingerprint": "cross-function-state->loop-bound-emergence",
        "difficulty_classification": "cross-function state carry + emergent loop amplification",
    },
    "PH4-012": {
        "challenge_id": "PH4-012",
        "difficulty": "LEVEL_9",
        "mechanism": "state-history dependent behavior",
        "root_cause": "record() accumulates history and window; evaluate() later folds both values into a loop bound. The resource cost becomes a function of earlier historical state and sequence.",
        "invariant": "a later evaluation should not become a hidden function of earlier call history and stored sequence values",
        "evidence_requirements": [
            "show cost shifts with different record() histories",
            "prove the later bound is derived from old values",
            "minimize the sequence to the smallest reproducer"
        ],
        "mechanism_fingerprint": "history-growth->nonlinear-bound-amplification",
        "difficulty_classification": "history-sensitive execution and state carry",
    },
    "PH4-013": {
        "challenge_id": "PH4-013",
        "difficulty": "LEVEL_10",
        "mechanism": "resource amplification under state growth",
        "root_cause": "add() stores values and drain() multiplies each stored value by a modulo-derived loop count, turning small state growth into a disproportionate later cost explosion.",
        "invariant": "small attacker-controlled state growth should not cause a disproportionately larger operation cost later in the same lifecycle",
        "evidence_requirements": [
            "compare different tracker sizes",
            "show nested-loop amplification",
            "demonstrate the relationship between stored values and drain() cost"
        ],
        "mechanism_fingerprint": "state-growth->nested-loop-amplification",
        "difficulty_classification": "resource amplification + state growth + multi-layer observation",
    },
    "PH4-014": {
        "challenge_id": "PH4-014",
        "difficulty": "LEVEL_11",
        "mechanism": "ABI/storage edge case with assembly interaction",
        "root_cause": "seed() writes storage values in both Solidity and assembly, while execute() derives the bound from a raw calldata offset and leading byte plus those storage values. The effective behavior is hidden behind ABI and EVM representation-level semantics.",
        "invariant": "execution cost should not silently depend on a hidden ABI and storage interaction that source-level reasoning cannot see",
        "evidence_requirements": [
            "inspect assembly and calldata reading",
            "show raw-value coupling between slot data and calldata",
            "confirm with bytecode/opcode or trace evidence"
        ],
        "mechanism_fingerprint": "calldata+assembly-slot-aliasing->resource-amplification",
        "difficulty_classification": "ABI + storage + assembly + bytecode semantics",
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
    "benchmark": "hard-phase4",
    "challenge_count": len(PUBLIC_CHALLENGES),
    "difficulty_band": "phase-4-deep-evm-research",
    "challenge_ids": sorted(PUBLIC_CHALLENGES),
    "difficulty_levels": ["LEVEL_8", "LEVEL_9", "LEVEL_10", "LEVEL_11"],
    "notes": "Phase 4 is a local deep-EVM research benchmark that measures cross-function composition, state-history dependence, resource amplification, ABI/storage edge cases, and evidence-led escalation to deeper EVM layers.",
}

MANIFESTS.joinpath("hard-phase4-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"status": "ok", "benchmark": "hard-phase4", "challenge_count": len(PUBLIC_CHALLENGES)}, indent=2, sort_keys=True))
