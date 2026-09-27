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
