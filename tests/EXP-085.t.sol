// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import {Test, console2} from "forge-std/Test.sol";
import {LocalDoSGasDemo} from "../src/LocalDoSGasDemo.sol";

contract EXP_085Test is Test {
    LocalDoSGasDemo internal demo;

    function setUp() public {
        demo = new LocalDoSGasDemo();
    }

    function _measureGas(uint256 count) internal returns (uint256) {
        for (uint256 i = 0; i < count; ++i) {
            demo.addParticipant(address(uint160(0x1000 + i)));
        }
        uint256 before = gasleft();
        demo.processAll();
        return before - gasleft();
    }

    function test_state_growth_gas_measurement() public {
        uint256 small = _measureGas(10);
        uint256 medium = _measureGas(100);
        uint256 large = _measureGas(250);

        console2.log("small", small);
        console2.log("medium", medium);
        console2.log("large", large);

        assertGt(medium, small, "medium state should cost more than small state");
        assertGt(large, medium, "large state should cost more than medium state");
    }

    function test_fuzz_state_growth(uint256 size) public {
        vm.assume(size > 0 && size <= 400);
        for (uint256 i = 0; i < size; ++i) {
            demo.addParticipant(address(uint160(0x2000 + i)));
        }

        uint256 before = gasleft();
        demo.processAll();
        uint256 gasUsed = before - gasleft();

        assertGt(gasUsed, 0, "processing workload should consume gas");
    }
}
