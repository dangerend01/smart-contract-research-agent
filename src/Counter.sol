// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

contract Counter {
    uint256 private number;

    function increment() external {
        number += 1;
    }

    function decrement() external {
        require(number > 0, "Counter: underflow");
        number -= 1;
    }

    function setNumber(uint256 newNumber) external {
        number = newNumber;
    }

    function getNumber() external view returns (uint256) {
        return number;
    }
}
