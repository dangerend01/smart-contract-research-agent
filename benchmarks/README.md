# Local Adversarial Benchmark Suite

This directory contains local, offline benchmark challenges for the smart-contract research lab.

Boundaries:
- only local contracts, local Foundry projects, and explicitly authorized challenge artifacts
- no arbitrary internet discovery or public RPC interaction
- no live exploitation against external systems

Contents:
- generated/: blind benchmark bundles for the researcher
- ground-truth/: evaluator-only hidden metadata and challenge explanations
- manifests/: deterministic challenge manifest records
- reports/: benchmark summaries and metrics
- public/: later adapter location for legally permitted public CTF source used locally only

The research agent receives only the blind bundle; the evaluator reads the ground-truth archive.
