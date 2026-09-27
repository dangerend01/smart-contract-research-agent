# Research Log: Foundry setup and validation

## Timestamp
2026-09-27

## Experiment or hypothesis ID
Hypothesis 01: local lab baseline

## Command(s) run

```bash
curl -L https://foundry.paradigm.xyz | bash
export PATH="$HOME/.foundry/bin:$PATH"
foundryup
forge --version
forge install foundry-rs/forge-std --no-commit
forge build
forge test
```

## Environment
- OS: Ubuntu 24.04.5 LTS
- Foundry version: 1.8.3
- Solidity version: 0.8.25
- Contract revision: local baseline `src/Counter.sol`

## Observations
- Foundry was initially missing from PATH.
- The initial test failed because `src/Counter.sol` did not exist yet.
- After defining the minimal contract, compilation succeeded and the 2-test suite passed.

## Follow-up actions
- Use this repository as the local baseline for DoS and gas-griefing experiments.
- Preserve all research state in Git-tracked files only.
