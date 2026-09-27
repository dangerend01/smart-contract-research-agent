
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
