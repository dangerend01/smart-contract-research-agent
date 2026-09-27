pragma solidity ^0.8.24;

import {BlindStateHistory} from "../BlindStateHistory.sol";

contract BlindStateHistoryTest {
    BlindStateHistory vault;

    function assertEq(uint256 a, uint256 b) internal pure {
        require(a == b, "assertEq failed");
    }

    function setUp() public {
        vault = new BlindStateHistory();
    }

    function test_stale_checkpoint_reuses_old_baseline() public {
        setUp();

        vault.contribute(100);
        vault.checkpoint();

        vault.contribute(100);
        vault.checkpoint();

        vault.settle(1e18);

        // The second checkpoint reuses a stale baseline, so settlement only credits the final 1 wei
        // rather than the full 100 wei that a stable snapshot should have reflected.
        assertEq(vault.rewardPool(), 1e18);
        assertEq(vault.lastSnapshot(), 200);
    }

    function test_claim_uses_overinflated_reward_accounting() public {
        setUp();

        vault.contribute(100);
        vault.checkpoint();

        vault.contribute(100);
        vault.checkpoint();

        vault.settle(1e18);
        vault.claim();

        assertEq(vault.rewardsClaimed(address(this)), 1e18);
    }
}
