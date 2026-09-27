#!/usr/bin/env python3
"""Generate the first three hard benchmark family artifacts without modifying existing benchmark data."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "benchmarks"
GENERATED = BASE / "generated" / "hard"
GROUND_TRUTH = BASE / "ground-truth" / "hard"
MANIFESTS = BASE / "manifests" / "hard"

GENERATED.mkdir(parents=True, exist_ok=True)
GROUND_TRUTH.mkdir(parents=True, exist_ok=True)
MANIFESTS.mkdir(parents=True, exist_ok=True)

CHALLENGE_SOURCE = {
    "HB-001": '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract SequenceAmplifier {
    uint256 public prepared;
    uint256 public processed;

    function prepare(uint256 delta) external {
        require(delta < 1_000_000, "delta out of range");
        prepared += delta;
    }

    function run() external {
        uint256 count = prepared;
        for (uint256 i = 0; i < count; ++i) {
            processed += 1;
        }
    }
}
''',
    "HB-002": '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract QueueAmplifier {
    address[] internal waiting;
    uint256 public settled;

    function enroll(address account) external {
        if (account != address(0)) {
            waiting.push(account);
        }
    }

    function settle() external {
        uint256 count = waiting.length;
        for (uint256 i = 0; i < count; ++i) {
            address account = waiting[i];
            if (account != address(0)) {
                settled += 1;
            }
        }
    }
}
''',
    "HB-003": '''
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract PackedStorageDrift {
    uint128 public alpha;
    uint128 public beta;
    uint64 public tick;
    uint256[] internal ledger;
    uint256 public processed;

    function seed(uint128 a, uint128 b, uint64 t) external {
        alpha = a;
        beta = b;
        tick = t;
        if (a != 0 && b != 0) {
            ledger.push(uint256(a) + uint256(b) + uint256(t));
        }
    }

    function sweep() external {
        uint256 size = ledger.length;
        for (uint256 i = 0; i < size; ++i) {
            processed += ledger[i];
        }
    }
}
''',
}

PUBLIC_CHALLENGES = {
    "HB-001": {
        "challenge_id": "HB-001",
        "family": "sequence-dependent-loop-amplification",
        "difficulty": "INTERMEDIATE",
        "difficulty_classification": "multi-function/state-history",
        "mechanism_fingerprint": "state-history->loop-bound-coupling",
        "seed": 1101,
        "contract_name": "SequenceAmplifier",
        "contract_source": CHALLENGE_SOURCE["HB-001"],
        "deployment_configuration": {"local": True, "deterministic": True, "solc": "0.8.25"},
        "available_functions": ["prepare", "run"],
        "initial_state": {"prepared": 0, "processed": 0},
        "invariant": "execution cost should not be driven by unrelated historical state drift",
        "resource_model": {"gas": "state_history_dependent", "notes": "the loop bound derives from prior state"},
        "public_objective": "Explain why the execution cost changes after a specific sequence of calls.",
        "expected_evidence_requirements": [
            "ordered call trace",
            "state before/after snapshot",
            "invariant statement",
            "explanation of loop-bound dependency"
        ],
        "compiler_configuration": {"optimizer": False, "via_ir": False},
    },
    "HB-002": {
        "challenge_id": "HB-002",
        "family": "queue-growth-gas-amplifier",
        "difficulty": "INTERMEDIATE",
        "difficulty_classification": "resource/gas/state-growth",
        "mechanism_fingerprint": "state-growth->loop-amplification",
        "seed": 1102,
        "contract_name": "QueueAmplifier",
        "contract_source": CHALLENGE_SOURCE["HB-002"],
        "deployment_configuration": {"local": True, "deterministic": True, "solc": "0.8.25"},
        "available_functions": ["enroll", "settle"],
        "initial_state": {"waiting": [], "settled": 0},
        "invariant": "processing cost should not scale with the number of previously accepted entries",
        "resource_model": {"gas": "linear_in_queue_length", "notes": "the settle loop grows with stored entries"},
        "public_objective": "Determine why the processing path becomes more expensive as the queue grows.",
        "expected_evidence_requirements": [
            "queue-growth measurement",
            "state delta explanation",
            "function-ordering analysis",
            "resource/timing evidence"
        ],
        "compiler_configuration": {"optimizer": False, "via_ir": False},
    },
    "HB-003": {
        "challenge_id": "HB-003",
        "family": "packed-storage-drift",
        "difficulty": "ADVANCED",
        "difficulty_classification": "deeper program analysis / storage-layout reasoning",
        "mechanism_fingerprint": "storage-layout->state-derived-loop-bound",
        "seed": 1103,
        "contract_name": "PackedStorageDrift",
        "contract_source": CHALLENGE_SOURCE["HB-003"],
        "deployment_configuration": {"local": True, "deterministic": True, "solc": "0.8.25"},
        "available_functions": ["seed", "sweep"],
        "initial_state": {"alpha": 0, "beta": 0, "tick": 0, "processed": 0},
        "invariant": "resource use should not be driven by packed-state values that are not directly tied to the intended control flow",
        "resource_model": {"gas": "state_layout_and_loop_bound_dependent", "notes": "packed values are written and later used to size a loop"},
        "public_objective": "Explain the origin of the execution cost growth and why it is tied to specific state values.",
        "expected_evidence_requirements": [
            "state transition trace",
            "storage interpretation evidence",
            "invariant explanation",
            "compiled-layout or slot reasoning"
        ],
        "compiler_configuration": {"optimizer": False, "via_ir": False, "storage_layout_focus": True},
    },
}

HIDDEN_TRUTH = {
    "HB-001": {
        "challenge_id": "HB-001",
        "difficulty": "INTERMEDIATE",
        "mechanism": "sequence-dependent loop amplification",
        "root_cause": "the prepare() function stores a value in prepared, and the later run() function uses that stored value as its loop bound. The cost therefore depends on historical state evolution rather than the current control-flow alone.",
        "invariant": "processing cost should not be tied to unrelated historical state drift",
        "evidence_requirements": [
            "call sequence: prepare(x) then run()",
            "state snapshot showing prepared increases before loop execution",
            "gas increase as prepared increases",
            "clear statement that the execution loop bound is derived from historical state"
        ],
        "reproducible_proof": {
            "steps": [
                "prepare(10)",
                "run()",
                "prepare(200)",
                "run()",
                "compare gas or loop count"
            ],
            "expected_result": "run() with larger prepared state consumes more gas and increases processed by a larger amount"
        },
        "mechanism_fingerprint": "state-history->loop-bound-coupling",
        "difficulty_classification": "multi-function/state-history",
    },
    "HB-002": {
        "challenge_id": "HB-002",
        "difficulty": "INTERMEDIATE",
        "mechanism": "queue-growth gas amplifier",
        "root_cause": "the settle() function iterates over every previously accepted entry in waiting. Each new enrollment expands the future processing cost of settle(), creating a direct queue-growth amplification path.",
        "invariant": "state expansion should not imply unbounded future processing cost for unrelated users",
        "evidence_requirements": [
            "enqueue several values and observe settle() cost growth",
            "state delta showing waiting.length changes before settlement",
            "explanation that settlement cost scales with queued entries"
        ],
        "reproducible_proof": {
            "steps": [
                "enroll() several entries",
                "measure settle() gas",
                "enroll() more entries",
                "measure settle() gas again",
                "confirm larger cost"
            ],
            "expected_result": "the larger queue leads to significantly larger gas use for settle()"
        },
        "mechanism_fingerprint": "state-growth->loop-amplification",
        "difficulty_classification": "resource/gas/state-growth",
    },
    "HB-003": {
        "challenge_id": "HB-003",
        "difficulty": "ADVANCED",
        "mechanism": "packed-state-driven loop bound",
        "root_cause": "alpha, beta, and tick are packed and later used to derive the sweep loop bound through ledger entries. The challenge is not a textbook bug label; it requires understanding the merged storage behavior and how those values feed a later expensive loop.",
        "invariant": "the resource cost should not be driven by compact storage values that only later become a loop bound",
        "evidence_requirements": [
            "analyze the state transition from seed() to sweep()",
            "show how values in packed storage feed the loop bound",
            "show that the loop is state-derived rather than fixed",
            "optionally inspect storage layout or compiler output to explain the packed layout"
        ],
        "reproducible_proof": {
            "steps": [
                "seed() with different values",
                "observe both storage and processed state",
                "invoke sweep() and measure larger gas or processed growth",
                "confirm the cost scales with the derived value rather than a trivial constant"
            ],
            "expected_result": "sweep() cost and processing amount track the sum of the stored packed values"
        },
        "mechanism_fingerprint": "storage-layout->state-derived-loop-bound",
        "difficulty_classification": "deeper program analysis / storage-layout reasoning",
    },
}

for cid, payload in PUBLIC_CHALLENGES.items():
    path = GENERATED / f"{cid}.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    gt_path = GROUND_TRUTH / f"{cid}.json"
    gt_payload = {
        "challenge_id": cid,
        "difficulty": payload["difficulty"],
        "difficulty_classification": payload["difficulty_classification"],
        "mechanism_fingerprint": payload["mechanism_fingerprint"],
        **HIDDEN_TRUTH[cid],
    }
    gt_path.write_text(json.dumps(gt_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

manifest = {
    "challenge_count": len(PUBLIC_CHALLENGES),
    "difficulty_band": "phase-1-hard",
    "generated_at": "local",
    "challenges": [
        {
            "challenge_id": cid,
            "difficulty": payload["difficulty"],
            "family": payload["family"],
            "seed": payload["seed"],
            "mechanism_fingerprint": payload["mechanism_fingerprint"],
        }
        for cid, payload in sorted(PUBLIC_CHALLENGES.items())
    ],
}
(MANIFESTS / "hard-benchmark-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

print(json.dumps({"status": "ok", "challenge_count": len(PUBLIC_CHALLENGES), "generated": sorted(PUBLIC_CHALLENGES.keys())}, indent=2, sort_keys=True))
