# Smart-Contract Security Research Lab

This repository is a reproducible local smart-contract security laboratory focused on authorized DoS, gas-griefing, and CTF-style local research. The goal is a clean, evidence-first workflow for local analysis without interacting with arbitrary public systems.

## Architecture

The repository is organized around a local research loop and an aggressive lab mode:

- `agents/`: Python utilities for contract understanding, invariant extraction, hypothesis generation, experiment execution, self-improvement, and learning persistence.
- `contracts/`: local examples and intentionally vulnerable or research-oriented contracts used only in lab scenarios.
- `src/`: Solidity source files, including safe demo contracts and local CTF-style targets.
- `tests/`: Foundry tests for build validation, regression checks, local DoS/gas-griefing demonstrations, and experiment generation.
- `hypotheses/`: hypothesis records, templates, and local deduplication state.
- `experiments/`: experiment definitions and evidence collection records.
- `results/`: measurement and summary data from local executions.
- `findings/`: evidence-backed conclusions and review summaries.
- `rejected-hypotheses/`: disproven or deprioritized ideas.
- `research-logs/`: chronological logs for each run.
- `research_memory/`: persistent learning artifacts, strategy versions, and memory snapshots.
- `prompts/`: operational research guidance and prompt material.
- `datasets/`: local benchmark or supporting data.

## Research lifecycle

The standard pipeline is:

1. Contract analysis
2. Invariant extraction
3. Hypothesis generation
4. Prioritization
5. Experiment generation
6. Local fuzzing and measurement
7. Falsification attempts
8. Counterexample minimization
9. Classification
10. Evidence storage
11. Learning and strategy adjustment
12. New hypothesis generation
13. Repeat

This is intentionally iterative and does not stop after the first successful hypothesis.

## LAB/CTF mode

The repository supports an aggressive local LAB/CTF research mode. This mode is limited to:

- local Foundry contracts
- local Anvil execution
- intentionally vulnerable contracts we create and store locally
- local fork snapshots supplied explicitly for research
- CTF-style local scenarios

It does not automatically:

- scan arbitrary public networks
- discover internet targets
- send broadcast transactions
- connect to unknown RPC endpoints
- target unapproved infrastructure

The aggressive behavior applies to local reasoning and experimentation, not to hostile or unsupported live interaction.

## Aggressive exploration goals

The aggressive engine attempts to explore:

- state transitions
- attacker-controlled state
- loops and nested iteration
- arrays and mappings
- storage growth
- external calls and payment paths
- callbacks and reentrancy-like patterns
- revert paths and error amplification
- gas-sensitive operations
- repeated interactions and call ordering
- boundary values and unusual sequences
- multi-function interactions
- state-history-dependent behavior

The system focuses on mechanisms and invariant violations instead of only seeking named CVEs or vulnerability labels.

## Self-improvement engine

The self-improvement component is implemented in [agents/self_improvement.py](agents/self_improvement.py) and [agents/aggressive_lab.py](agents/aggressive_lab.py).

It learns from both successful and failed experiments. Each experiment tracks:

- hypothesis characteristics
- contract characteristics
- involved functions
- attack sequence
- input/state characteristics
- invariant targeted
- test strategy
- fuzz strategy
- measurements
- result
- reason for success or failure
- useful mutations
- unused possibilities

This means "self-improvement" is defined as improving research strategy from experimentally observed evidence. It does not mean claiming the system is universally smarter or that every generated hypothesis is correct.

## Learning model

### Success learning

When an experiment confirms a mechanism, the engine identifies:

- what made the hypothesis successful
- important preconditions
- useful input and state patterns
- the successful function sequence
- related functions that may produce similar behavior
- mutations of the successful mechanism
- nearby follow-up hypotheses

Example success patterns include:

- state growth → nested iteration
- state growth → external-call amplification
- state growth → failure-path amplification
- state growth → state-transition blocking

These are treated as follow-up hypotheses that must still be tested experimentally.

### Failure learning

When a hypothesis is disproven, the engine records:

- the reason it failed
- the wrong assumption
- the missing precondition
- whether the sequence was invalid
- whether the measurement was insufficient
- a modified hypothesis
- a strategy change to avoid repeated unproductive tests

Failure taxonomy includes:

- WRONG_PRECONDITION
- UNREACHABLE_STATE
- INSUFFICIENT_AMPLIFICATION
- NO_VICTIM_IMPACT
- GAS_NOT_SCALING
- ATTACK_SEQUENCE_INVALID
- INVARIANT_NOT_APPLICABLE
- IMPLEMENTATION_ERROR
- INSUFFICIENT_EVIDENCE
- OTHER

## Strategy learning

The system tracks strategies such as:

- state-growth strategy
- sequence-mutation strategy
- boundary-value strategy
- gas-amplification strategy
- failure-path strategy
- external-call strategy
- invariant-breaking strategy
- cross-function interaction strategy
- state-history strategy

Strategy performance is updated from historical experimental outcomes, and the engine balances:

- exploitation: focus on strategies with prior useful results
- exploration: deliberately test under-tested or unusual combinations

The balance is configurable with `EXPLORATION_RATIO` and the research budget settings.

## Hypothesis mutation and deduplication

After each experiment, the engine produces mutated candidate hypotheses by varying:

- parameters
- attacker actions
- victim actions
- sequence order
- state initialization
- repetition count
- input sizes
- invariant targets
- involved functions

Mutations are deduplicated against the repository memory to reduce repeated experiments and maintain research continuity.

## Counterexample minimization

When a fuzzing or boundary-case run suggests an interesting effect, the engine attempts to minimize:

- input size
- sequence length
- state size
- function call count

The minimized testcase becomes a reusable local research artifact and is stored with the relevant experiment evidence.

## Persistent research memory

Everything is persisted to local JSON/Markdown artifacts. This includes:

- hypotheses
- experiments
- successful mechanisms
- rejected hypotheses
- failure reasons
- counterexamples
- minimized testcases
- gas measurements
- state parameters
- call sequences
- strategy performance
- learning patterns
- follow-up hypotheses
- research logs
- versioned strategies and learning artifacts

Historical results are never silently overwritten. Each important learning step remains traceable to the experiments that produced it.

## Versioned self-improvement

The project stores strategy versions as artifacts such as:

- strategy-v001
- strategy-v002
- strategy-v003

Each version records:

- previous strategy
- observed evidence
- proposed change
- reason
- expected benefit
- tests performed
- resulting performance
- timestamp
- run ID

The system may propose improvements automatically, but it only applies changes that pass the project’s automated validation tests.

## Self-evaluation

The engine conducts periodic evaluations of the research process using metrics such as:

- hypotheses generated
- unique hypotheses
- duplicate rate
- experiments executed
- useful experiments
- disproven hypotheses
- confirmed mechanisms
- minimized counterexamples
- strategy effectiveness
- repeated-failure rate
- unexplored areas
- coverage of contract functions and invariants

## Research budget and resume

The aggressive mode supports configurable limits such as:

- MAX_HYPOTHESES
- MAX_EXPERIMENTS
- MAX_FUZZ_CASES
- MAX_SEQUENCE_LENGTH
- MAX_RUNTIME
- EXPLORATION_RATIO

The system can resume from previous research memory instead of restarting from zero.

## Research diversity and exploration engine

The repository also includes a diversity and frontier engine in [agents/diversity_engine.py](agents/diversity_engine.py). It tracks:

- a machine-readable mechanism graph for contracts, functions, state variables, inputs, invariants, attack surfaces, hypotheses, experiments, and observed mechanisms
- coverage classification for TESTED, PARTIALLY_TESTED, and UNTESTED dimensions
- duplicate detection and mechanism fingerprinting for known, variant, potentially distinct, and unknown patterns
- combination generation for function sequences and state-history variants
- frontier generation for under-tested regions of the local contract search space
- exploration selection that prefers frontier items over rediscovered duplicates while preserving the historical research trail

This keeps the lab from repeatedly spending its full budget on the same mechanism while still preserving the learnings that produced it.

## Hypothesis and experiment engines

The repository includes:

- [agents/hypothesis_engine.py](agents/hypothesis_engine.py): local hypothesis generation, prioritization, and deduplication
- [agents/experiment_engine.py](agents/experiment_engine.py): experiment generation and evidence persistence
- [agents/aggressive_lab.py](agents/aggressive_lab.py): aggressive local experimentation and self-improvement orchestration
- [agents/self_improvement.py](agents/self_improvement.py): strategy learning, mutation, and versioning
- [agents/diversity_engine.py](agents/diversity_engine.py): anti-rediscovery, frontier generation, and coverage tracking

## Local demo

A safe local DoS/gas-griefing demo is provided in:

- [src/LocalDoSGasDemo.sol](src/LocalDoSGasDemo.sol)
- [tests/DoSGasGriefingDemo.t.sol](tests/DoSGasGriefingDemo.t.sol)

This example is used as the initial research target for the self-improvement loop.

## Running the aggressive lab mode

```bash
export PATH="$HOME/.foundry/bin:$PATH"
python3 scripts/run_aggressive_lab.py
```

This executes two local research cycles using the stored evidence from the first cycle to inform strategy mutation in the second.

## Safety boundaries

This lab is intentionally limited to local, explicitly authorized research. It does not claim vulnerabilities without reproducible local evidence and it does not perform arbitrary live exploitation.

## Notes

The aggressive research mode is designed to explore local mechanisms, test hypotheses, learn from both success and failure, and improve the way the laboratory asks questions. It is an evidence-driven research system, not a claim engine.
