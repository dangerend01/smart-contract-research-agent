// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import {Test, console2} from "forge-std/Test.sol";
import {LocalDoSGasDemo} from "../src/LocalDoSGasDemo.sol";

contract DoSGasGriefingDemoTest is Test {
    LocalDoSGasDemo internal demo;

    function setUp() public {
        demo = new LocalDoSGasDemo();
    }

    function testGasUsageScalesWithAttackerControlledEntries() public {
        for (uint256 i = 0; i < 50; i++) {
            demo.addParticipant(address(uint160(1000 + i)));
        }

        uint256 smallGas = _measureProcessGas();

        for (uint256 i = 0; i < 200; i++) {
            demo.addParticipant(address(uint160(2000 + i)));
        }

        uint256 largeGas = _measureProcessGas();

        console2.log("smallGas", smallGas);
        console2.log("largeGas", largeGas);

        assertGt(largeGas, smallGas, "gas did not increase with a larger attacker-controlled set");
        assertGt(largeGas / smallGas, 2, "gas growth should be noticeably larger for the large case");
    }

    function _measureProcessGas() internal returns (uint256) {
        uint256 gasBefore = gasleft();
        demo.processAll();
        return gasBefore - gasleft();
    }
}
