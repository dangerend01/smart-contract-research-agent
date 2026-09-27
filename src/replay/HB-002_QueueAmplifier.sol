
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
