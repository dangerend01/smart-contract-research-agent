# PHASE 5 DEEP EVM / COMPILER DIFFERENTIAL RESEARCH REPORT

- benchmark: hard-phase4
- phase: PHASE5
- challenge_count: 4
- experiments_performed: 15
- mechanisms_discovered: 4
- mechanisms_missed: 0
- false_positives: 0
- compiler_differences: 8
- bytecode_differences: 8
- trace_differences: 4
- deepest_analysis_layer_reached: bytecode-analysis
- minimized_counterexamples: 4

## Selected challenge findings
- PH4-011: cross-function-emergent-behavior | deepest layer: bytecode-analysis | experiments: 4
  hypothesis: The compiler build changes the control-flow or storage path used by CrossFunctionEmergentBehavior, and the earliest divergence appears in the state-history or calldata-sensitive path before any security claim is accepted.
  compiler-note: optimizer change from True / viaIR=False to False / viaIR=False caused a bytecode or ABI differential
  trace-note: loop bound derived from prior state causes later execution to become history-dependent
- PH4-012: state-history-dependent-behavior | deepest layer: bytecode-analysis | experiments: 4
  hypothesis: The compiler build changes the control-flow or storage path used by StateHistoryDependentBehavior, and the earliest divergence appears in the state-history or calldata-sensitive path before any security claim is accepted.
  compiler-note: optimizer change from True / viaIR=False to False / viaIR=False caused a bytecode or ABI differential
  trace-note: loop bound derived from prior state causes later execution to become history-dependent
- PH4-013: resource-amplification | deepest layer: bytecode-analysis | experiments: 3
  hypothesis: The compiler build changes the control-flow or storage path used by ResourceAmplification, and the earliest divergence appears in the state-history or calldata-sensitive path before any security claim is accepted.
  compiler-note: optimizer change from True / viaIR=False to False / viaIR=False caused a bytecode or ABI differential
  trace-note: resource-sensitive loop cost changes with repeated state growth
- PH4-014: abi-storage-edge-cases | deepest layer: bytecode-analysis | experiments: 4
  hypothesis: The compiler build changes the control-flow or storage path used by AbiStorageEdgeCases, and the earliest divergence appears in the state-history or calldata-sensitive path before any security claim is accepted.
  compiler-note: optimizer change from True / viaIR=False to False / viaIR=False caused a bytecode or ABI differential
  trace-note: calldata/slot-dependent path diverges when boundary values and storage writes interact
