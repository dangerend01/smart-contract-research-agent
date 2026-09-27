
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
