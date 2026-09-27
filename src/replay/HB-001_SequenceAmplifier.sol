
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
