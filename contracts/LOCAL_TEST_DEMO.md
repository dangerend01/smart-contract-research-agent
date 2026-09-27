# Local DoS / Gas-Griefing Demo

This contract is intentionally tiny and designed only for local research. It demonstrates how an unbounded loop over user-controlled state creates a gas-cost amplification pattern.

## Why it is a relevant local research example

- The contract stores participant addresses in a dynamic array.
- An attacker can grow that list with many addresses.
- A later `processAll()` call iterates over the entire array.
- As the array grows, the gas used by the victim action also grows.

## Invariant that fails

> An operation should remain callable even when another actor can grow attacker-controlled state.

The local failure is not a real-world exploit against a live target; it is a safe, local demonstration of a gas-griefing pattern that should be treated as a signal to inspect other contracts for similar loops.

## Test scenario

The Foundry test in `tests/DoSGasGriefingDemo.t.sol` measures gas for two cases:

1. a smaller participant set
2. a much larger participant set

The test verifies that the larger set produces a materially higher gas cost.
