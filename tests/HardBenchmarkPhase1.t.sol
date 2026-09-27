// SPDX-License-Identifier: MIT
pragma solidity ^0.8.25;

import {Test, console2} from "forge-std/Test.sol";
import {SequenceAmplifier, QueueAmplifier, PackedStorageDrift} from "../src/hard/Phase1HardChallenges.sol";

contract HardBenchmarkPhase1Test is Test {
    SequenceAmplifier internal sequence;
    QueueAmplifier internal queue;
    PackedStorageDrift internal packed;

    function setUp() public {
        sequence = new SequenceAmplifier();
        queue = new QueueAmplifier();
        packed = new PackedStorageDrift();
    }

    function testSequenceStateHistoryAmplifiesProcessing() public {
        sequence.prepare(10);
        uint256 smallGas = _measureRunGas();

        sequence.prepare(500);
        uint256 largeGas = _measureRunGas();

        assertGt(largeGas, smallGas, "state history should increase execution cost");
    }

    function testQueueGrowthIncreasesSettlementCost() public {
        for (uint256 i = 0; i < 25; ++i) {
            queue.enroll(address(uint160(1000 + i)));
        }
        uint256 smallGas = _measureSettleGas();

        for (uint256 i = 0; i < 150; ++i) {
            queue.enroll(address(uint160(2000 + i)));
        }
        uint256 largeGas = _measureSettleGas();

        assertGt(largeGas, smallGas, "larger queue should increase settlement cost");
    }

    function testPackedStateValuesDriveLaterProcessing() public {
        packed.seed(12, 7, 4);
        uint256 beforeValue = packed.processed();

        packed.sweep();
        uint256 afterValue = packed.processed();

        assertGt(afterValue, beforeValue, "derived packed-state data should drive later processing");
    }

    function _measureRunGas() internal returns (uint256) {
        uint256 before = gasleft();
        sequence.run();
        return before - gasleft();
    }

    function _measureSettleGas() internal returns (uint256) {
        uint256 before = gasleft();
        queue.settle();
        return before - gasleft();
    }
}
