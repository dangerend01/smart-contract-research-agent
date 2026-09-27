pragma solidity ^0.8.24;

contract BlindStateHistory {
    uint256 public totalContributed;
    uint256 public rewardPool;
    uint256 public lastSnapshot;
    uint256 public round;

    mapping(address => uint256) public contributed;
    mapping(address => uint256) public rewardsClaimed;

    function contribute(uint256 amount) external {
        require(amount > 0, "amount must be > 0");
        totalContributed += amount;
        contributed[msg.sender] += amount;
    }

    function checkpoint() external {
        if (lastSnapshot == 0) {
            lastSnapshot = totalContributed;
            round += 1;
            return;
        }

        // Sequence-sensitive state bug: reopening a round before the previous settlement is
        // fully consumed reuses the stale previous snapshot instead of the current stable one.
        // The intended behavior is to snapshot the current total only once per cycle; this
        // resets the baseline back to the previous total and allows the next settlement to
        // count the same growth twice.
        lastSnapshot = totalContributed - 1;
        round += 1;
    }

    function settle(uint256 bonus) external {
        uint256 delta = totalContributed - lastSnapshot;
        require(delta > 0, "nothing to settle");
        rewardPool += delta * bonus;
        lastSnapshot = totalContributed;
    }

    function claim() external {
        uint256 owed = (contributed[msg.sender] * rewardPool) / totalContributed - rewardsClaimed[msg.sender];
        require(owed > 0, "nothing to claim");
        rewardsClaimed[msg.sender] += owed;
    }
}
