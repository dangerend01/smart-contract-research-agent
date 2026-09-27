# Target Report: directory-damn-vulnerable-defi-124d0aff6c7d

This target is imported and stored locally for authorized, offline, evidence-driven smart-contract research.

- Source type: directory
- Source location: /tmp/damn-vulnerable-defi
- Network policy: LOCAL_ONLY
- Build status: OK
- Research status: READY
- Project kind: foundry
- UI port: 8000 (kept separate from the local Anvil JSON-RPC endpoint at 8545)

## Solidity inventory

- src/DamnValuableNFT.sol
- src/DamnValuableStaking.sol
- src/DamnValuableToken.sol
- src/DamnValuableVotes.sol
- src/abi-smuggling/AuthorizedExecutor.sol
- src/abi-smuggling/SelfAuthorizedVault.sol
- src/backdoor/WalletRegistry.sol
- src/climber/ClimberConstants.sol
- src/climber/ClimberErrors.sol
- src/climber/ClimberTimelock.sol
- src/climber/ClimberTimelockBase.sol
- src/climber/ClimberVault.sol
- src/compromised/Exchange.sol
- src/compromised/TrustfulOracle.sol
- src/compromised/TrustfulOracleInitializer.sol
- src/curvy-puppet/CurvyPuppetLending.sol
- src/curvy-puppet/CurvyPuppetOracle.sol
- src/curvy-puppet/ICryptoSwapFactory.sol
- src/curvy-puppet/ICryptoSwapPool.sol
- src/curvy-puppet/IStableSwap.sol
- src/free-rider/FreeRiderNFTMarketplace.sol
- src/free-rider/FreeRiderRecoveryManager.sol
- src/naive-receiver/BasicForwarder.sol
- src/naive-receiver/FlashLoanReceiver.sol
- src/naive-receiver/Multicall.sol
- src/naive-receiver/NaiveReceiverPool.sol
- src/puppet-v2/PuppetV2Pool.sol
- src/puppet-v2/UniswapV2Library.sol
- src/puppet-v3/INonfungiblePositionManager.sol
- src/puppet-v3/PuppetV3Pool.sol
- src/puppet/IUniswapV1Exchange.sol
- src/puppet/IUniswapV1Factory.sol
- src/puppet/PuppetPool.sol
- src/selfie/ISimpleGovernance.sol
- src/selfie/SelfiePool.sol
- src/selfie/SimpleGovernance.sol
- src/shards/IShardsNFTMarketplace.sol
- src/shards/ShardsFeeVault.sol
- src/shards/ShardsNFTMarketplace.sol
- src/side-entrance/SideEntranceLenderPool.sol
- src/the-rewarder/TheRewarderDistributor.sol
- src/truster/TrusterLenderPool.sol
- src/unstoppable/UnstoppableMonitor.sol
- src/unstoppable/UnstoppableVault.sol
- src/wallet-mining/AuthorizerFactory.sol
- src/wallet-mining/AuthorizerUpgradeable.sol
- src/wallet-mining/TransparentProxy.sol
- src/wallet-mining/WalletDeployer.sol
- src/withdrawal/L1Forwarder.sol
- src/withdrawal/L1Gateway.sol
- src/withdrawal/L2Handler.sol
- src/withdrawal/L2MessageStore.sol
- src/withdrawal/TokenBridge.sol
- test/abi-smuggling/ABISmuggling.t.sol
- test/backdoor/Backdoor.t.sol
- test/climber/Climber.t.sol
- test/compromised/Compromised.t.sol
- test/curvy-puppet/CurvyPuppet.t.sol
- test/free-rider/FreeRider.t.sol
- test/naive-receiver/NaiveReceiver.t.sol
- test/puppet-v2/PuppetV2.t.sol
- test/puppet-v3/PuppetV3.t.sol
- test/puppet/Puppet.t.sol
- test/selfie/Selfie.t.sol
- test/shards/Shards.t.sol
- test/side-entrance/SideEntrance.t.sol
- test/the-rewarder/TheRewarder.t.sol
- test/truster/Truster.t.sol
- test/unstoppable/Unstoppable.t.sol
- test/wallet-mining/CreateX.sol
- test/wallet-mining/SafeSingletonFactory.sol
- test/wallet-mining/WalletMining.t.sol
- test/withdrawal/Withdrawal.t.sol

## Notes

- No live blockchain or arbitrary external transaction system is used.
- The imported target remains isolated under the local target directory.
- Research execution should proceed only with local compilation, replay, and evidence collection.
