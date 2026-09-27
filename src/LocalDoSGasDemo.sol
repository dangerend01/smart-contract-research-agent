// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract LocalDoSGasDemo {
    address[] public participants;
    mapping(address => bool) public seen;
    uint256 public processed;

    function addParticipant(address account) external {
        require(account != address(0), "zero-address not allowed");
        if (!seen[account]) {
            seen[account] = true;
            participants.push(account);
        }
    }

    function processAll() external {
        uint256 count = participants.length;

        for (uint256 i = 0; i < count; ++i) {
            address participant = participants[i];
            if (participant == address(0)) {
                continue;
            }
            processed += 1;
        }
    }
}
