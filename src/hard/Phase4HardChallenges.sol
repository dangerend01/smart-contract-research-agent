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
