#!/usr/bin/env python3
"""Generate the Phase 2 harder blind benchmark while leaving Phase 1 artifacts untouched."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks"
GENERATED = BASE / "generated" / "hard-phase2"
GROUND_TRUTH = BASE / "ground-truth" / "hard-phase2"
MANIFESTS = BASE / "manifests" / "hard"

GENERATED.mkdir(parents=True, exist_ok=True)
GROUND_TRUTH.mkdir(parents=True, exist_ok=True)
MANIFESTS.mkdir(parents=True, exist_ok=True)

CHALLENGE_SOURCE = {
    "PH2-005": '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract CrossFunctionStateEntropy {
    uint256 public epoch;
    uint256 public total;
    uint256[] internal backlog;
    bool public armed;

    function arm(uint256 seed, uint256 delta) external {
        armed = true;
        epoch = seed + delta;
        backlog.push(seed);
        backlog.push(delta);
    }

    function trigger() external {
        if (!armed) {
            return;
        }

        uint256 limit = epoch;
        uint256 length = backlog.length;
        for (uint256 i = 0; i < limit; ++i) {
            total += backlog[i % length];
        }
    }
}
''',
    "PH2-006": '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract SequenceHistoryGasDrift {
    uint256 public score;
    uint256 public window;
    uint256[] internal history;

    function record(uint256 value) external {
        history.push(value);
        window += value;
    }

    function sweep(uint256 bias) external {
        uint256 bound = window + bias;
        for (uint256 i = 0; i < history.length; ++i) {
            bound += history[i] % 17;
        }

        for (uint256 i = 0; i < bound; ++i) {
            score += 1;
        }
    }
}
''',
    "PH2-007": '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract AbiAssemblySlotAmbiguity {
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
    "PH2-005": {
        "challenge_id": "PH2-005",
        "family": "cross-function-state-entropy",
        "difficulty": "LEVEL_5",
        "difficulty_classification": "cross-function/state-history",
        "mechanism_fingerprint": "cross-function-state->loop-bound",
        "seed": 2005,
        "contract_name": "CrossFunctionStateEntropy",
        "contract_source": CHALLENGE_SOURCE["PH2-005"],
        "deployment_configuration": {"local": True, "deterministic": True, "solc": "0.8.25"},
        "available_functions": ["arm", "trigger"],
        "initial_state": {"epoch": 0, "total": 0, "armed": False},
        "invariant": "resource cost should not be driven by repeated state carries between functions under a single call chain",
        "resource_model": {"gas": "state_history_and_loop_bound_dependent", "notes": "the trigger loop bound derives from a prior arm() value and a stored queue"},
        "public_objective": "Explain why the cost of trigger() changes after a specific state-history sequence and why the resulting loop is tied to earlier function state.",
        "expected_evidence_requirements": [
            "ordered call trace",
            "state history before and after arm()/trigger()",
            "control/data-flow explanation",
            "measurement of the loop bound's dependence on historical values"
        ],
        "analysis_layers": [
            "source-analysis",
            "state-control-data-flow",
            "sequence-search",
            "gas-resource-analysis"
        ],
        "compiler_configuration": {"optimizer": True, "optimizer_runs": 200, "via_ir": False},
    },
    "PH2-006": {
        "challenge_id": "PH2-006",
        "family": "sequence-history-gas-drift",
        "difficulty": "LEVEL_6",
        "difficulty_classification": "sequence/search/history+gas",
        "mechanism_fingerprint": "state-history->nonlinear-loop-growth",
        "seed": 2006,
        "contract_name": "SequenceHistoryGasDrift",
        "contract_source": CHALLENGE_SOURCE["PH2-006"],
        "deployment_configuration": {"local": True, "deterministic": True, "solc": "0.8.25"},
        "available_functions": ["record", "sweep"],
        "initial_state": {"score": 0, "window": 0},
        "invariant": "execution should not become disproportionately expensive simply because the history of prior user calls increased the later loop bound",
        "resource_model": {"gas": "history_driven_and_sequence_sensitive", "notes": "history values are accumulated and then folded into the sweep loop bound"},
        "public_objective": "Find the sequence/state interaction that turns the later sweep() cost into a function of prior recorded values and ordering.",
        "expected_evidence_requirements": [
            "state-history trace",
            "sequence mutation evidence",
            "gas scaling proof across different prior call orders",
            "call-order sensitivity explanation"
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
    "PH2-007": {
        "challenge_id": "PH2-007",
        "family": "abi-assembly-slot-ambiguity",
        "difficulty": "LEVEL_7",
        "difficulty_classification": "abi/evm/yul/bytecode depth",
        "mechanism_fingerprint": "calldata+assembly+slot_aliasing->resource-amplification",
        "seed": 2007,
        "contract_name": "AbiAssemblySlotAmbiguity",
        "contract_source": CHALLENGE_SOURCE["PH2-007"],
        "deployment_configuration": {"local": True, "deterministic": True, "solc": "0.8.25"},
        "available_functions": ["seed", "execute"],
        "initial_state": {"slotA": 0, "slotB": 0, "processed": 0},
        "invariant": "execution cost should not silently depend on opaque ABI and storage aliasing that is hidden behind assembly-level data interpretation",
        "resource_model": {"gas": "assembly_and_calldata_dependent", "notes": "the bound is derived from a partially hidden ABI/calldata offset plus packed storage values"},
        "public_objective": "Explain why a function that looks like a simple ABI wrapper becomes disproportionately expensive under certain calldata and state combinations, and why source-level reasoning alone is incomplete.",
        "expected_evidence_requirements": [
            "state-plus-calldata trace",
            "assembly or Yul interpretation",
            "storage aliasing or slot reasoning",
            "bytecode-level explanation when source reasoning is insufficient"
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
    "PH2-005": {
        "challenge_id": "PH2-005",
        "difficulty": "LEVEL_5",
        "mechanism": "cross-function state entropy",
        "root_cause": "arm() stores a seed and delta that later determine the trigger() loop bound. The state history across functions produces a loop whose length is tied to prior attacker-controlled values instead of an independent bounded operation.",
        "invariant": "state should not carry a hidden loop bound from one function into a later unrelated function call",
        "evidence_requirements": [
            "compare arm(seed, delta) followed by trigger()",
            "show the loop bound equals epoch from prior state",
            "demonstrate that the cost scales with the historical drift introduced by arm()"
        ],
        "reproducible_proof": {
            "steps": [
                "arm(3, 5)",
                "trigger()",
                "arm(9, 18)",
                "trigger()",
                "compare gas and total"
            ],
            "expected_result": "trigger() consumes notably more gas as the historical arm() state grows"
        },
        "mechanism_fingerprint": "cross-function-state->loop-bound",
        "difficulty_classification": "cross-function/state-history",
    },
    "PH2-006": {
        "challenge_id": "PH2-006",
        "difficulty": "LEVEL_6",
        "mechanism": "sequence-history gas drift",
        "root_cause": "record() accumulates values into history and window. sweep() adds both the cumulative window and each stored value modulo 17 into its bound, so the later work scales superlinearly with the exact prior call sequence and history of values.",
        "invariant": "a later loop should not become a function of arbitrarily accumulated historical inputs from prior user actions",
        "evidence_requirements": [
            "measure gas after different record() sequences",
            "show the sweep() loop bound depends on window and stored history",
            "confirm reverse ordering or different values shift the bound"
        ],
        "reproducible_proof": {
            "steps": [
                "record(5)",
                "record(10)",
                "sweep(0)",
                "record(15)",
                "sweep(4)",
                "compare the gas profile"
            ],
            "expected_result": "different call order or sequence lengths produce different sweep() costs and loop bounds"
        },
        "mechanism_fingerprint": "state-history->nonlinear-loop-growth",
        "difficulty_classification": "sequence/search/history+gas",
    },
    "PH2-007": {
        "challenge_id": "PH2-007",
        "difficulty": "LEVEL_7",
        "mechanism": "ABI/assembly slot-ambiguity amplification",
        "root_cause": "execute() uses assembly to read calldata and also writes storage through an explicit slot alias (0x40 / 0x41), causing a later loop bound to depend on both slot values and calldata-derived offset data. The source-level contract shape hides the real amplification because it is distributed across ABI decoding, raw calldata access, and storage aliasing.",
        "invariant": "data-dependent execution should not be hidden behind opaque ABI and EVM-level storage aliasing that only appears when inspecting assembly or bytecode",
        "evidence_requirements": [
            "inspect the `execute(bytes)` path and raw calldata interpretation",
            "explain the assembly-level read of calldata and storage writes",
            "show how the loop bound is derived from slotA, slotB, and offset/data input",
            "verify with Yul/IR or bytecode/opcode evidence when source is insufficient"
        ],
        "reproducible_proof": {
            "steps": [
                "seed(left, right)",
                "execute(data) with a payload that changes the raw calldataload offset or leading byte",
                "compare gas and processed count",
                "validate the bound is derived from both state and calldata"
            ],
            "expected_result": "small changes in hidden calldata or storage values lead to materially different loop counts and gas usage"
        },
        "mechanism_fingerprint": "calldata+assembly+slot_aliasing->resource-amplification",
        "difficulty_classification": "abi/evm/yul/bytecode depth",
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
    "benchmark": "hard-phase2",
    "challenge_count": len(PUBLIC_CHALLENGES),
    "difficulty_band": "phase-2-hard",
    "challenge_ids": sorted(PUBLIC_CHALLENGES),
    "difficulty_levels": ["LEVEL_5", "LEVEL_6", "LEVEL_7"],
    "public_only": True,
    "notes": "Phase 2 is a harder blind benchmark focused on deeper exploration, state-history, ABI/EVM edge cases, and assembly-level influences.",
}

MANIFESTS.joinpath("hard-phase2-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps({"status": "ok", "benchmark": "hard-phase2", "challenge_count": len(PUBLIC_CHALLENGES)}, indent=2, sort_keys=True))
