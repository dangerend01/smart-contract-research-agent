
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
