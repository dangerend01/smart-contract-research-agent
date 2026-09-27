// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import {Test, console2} from "forge-std/Test.sol";
import {
    CrossFunctionStateEntropy,
    SequenceHistoryGasDrift,
    AbiAssemblySlotAmbiguity
} from "../src/hard/Phase2HardChallenges.sol";

contract HardBenchmarkPhase2Test is Test {
    CrossFunctionStateEntropy internal entropy;
    SequenceHistoryGasDrift internal drift;
    AbiAssemblySlotAmbiguity internal assemblyAmbiguity;

    function setUp() public {
        entropy = new CrossFunctionStateEntropy();
        drift = new SequenceHistoryGasDrift();
        assemblyAmbiguity = new AbiAssemblySlotAmbiguity();
    }

    function testCrossFunctionStateEntropyAmplifiesAfterStateCarry() public {
        entropy.arm(2, 3);
        uint256 before = gasleft();
        entropy.trigger();
        uint256 smallCost = before - gasleft();

        entropy.arm(20, 30);
        before = gasleft();
        entropy.trigger();
        uint256 largeCost = before - gasleft();

        assertGt(largeCost, smallCost, "state carry across functions should amplify later work");
    }

    function testSequenceHistoryGasDriftAmplifiesWithStateHistory() public {
        drift.record(3);
        drift.record(9);
        uint256 before = gasleft();
        drift.sweep(0);
        uint256 smallCost = before - gasleft();

        drift.record(18);
        drift.record(24);
        before = gasleft();
        drift.sweep(7);
        uint256 largeCost = before - gasleft();

        assertGt(largeCost, smallCost, "historical state should raise later sweep cost");
    }

    function testAbiAssemblySlotAmbiguityDependsOnCalldataAndStorage() public {
        assemblyAmbiguity.seed(5, 7);
        bytes memory first = hex"01";
        uint256 before = gasleft();
        assemblyAmbiguity.execute(first);
        uint256 smallCost = before - gasleft();

        assemblyAmbiguity.seed(17, 21);
        bytes memory second = hex"ff";
        before = gasleft();
        assemblyAmbiguity.execute(second);
        uint256 largeCost = before - gasleft();

        assertGt(largeCost, smallCost, "hidden calldata and storage state should change loop size");
    }
}
