// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import {Test} from "forge-std/Test.sol";
import {Counter} from "../src/Counter.sol";

contract CounterTest is Test {
    Counter internal counter;

    function setUp() public {
        counter = new Counter();
    }

    function testIncrementIncreasesCount() public {
        counter.increment();
        assertEq(counter.getNumber(), 1);
    }

    function testSetNumberUpdatesCount() public {
        counter.setNumber(42);
        assertEq(counter.getNumber(), 42);
    }
}
