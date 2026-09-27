# Current State

## Project purpose
This repository is a local-only smart-contract security research workspace. It imports local Solidity targets, preserves them under the repo, runs blind analyses, records hypotheses and evidence, and keeps the research process separate from hidden benchmark truth.

## Current architecture
- Local target ingestion in `agents/target_ingestion.py`
- Public/private challenge and benchmark handling under `benchmarks/` and `targets/`
- Research analysis in `agents/deep_evm_research_engine.py`
- Strategy memory under `research_memory/strategies/`
- Evidence and result persistence under `results/` and `research-logs/`
- Python validation under `tests/`
- Foundry project configuration in the repository root

## Current research capabilities
- Import local Solidity single-file, directory, repository and public-source targets
- Normalize plain Solidity into a local Foundry wrapper when required
- Preserve imported targets for reuse and comparison
- Run blind, evidence-first local analyses
- Maintain hypothesis, experiment, and strategy histories
- Evaluate research quality against hidden or local benchmark truth without exposing it to the blind researcher

## Latest strategy version
The actual latest strategy record found in the repository is:

- `research_memory/strategies/strategy-v054.json`

## Latest synthetic benchmark
The repository contains several generated synthetic benchmark bundles under `benchmarks/generated/` and the hard benchmarks under `benchmarks/generated/hard/` and related phase directories.

## Latest real public CTF benchmark
The preserved public benchmark is the Dam Vulnerable DeFi Truster challenge:

- repository: https://github.com/tinchoabbate/damn-vulnerable-defi
- source preserved under `datasets/public_ctfs/damn-vulnerable-defi/`
- imported target: `targets/directory-damn-vulnerable-defi-124d0aff6c7d/`
- benchmark report: `research_memory/benchmarks/2026-09-27-damn-vulnerable-defi-truster.md`

## Current test status
- Project Python validation: run via the existing repository test suite
- Public challenge validation: Truster challenge remains intentionally unsolved; the local challenge test fails at the expected unsolved condition rather than at import/build failure

## Known research limitations
- The blind engine can produce generic state-ordering or stale-history hypotheses without independently proving the concrete exploit chain.
- The Truster challenge remains a known regression benchmark demonstrating the gap between generic suspicion and actual exploit discovery.
- The researcher must still connect behavior → mechanism → reproducible sequence/input → security consequence.

## Exact next recommended research step
The next recommended research step is to test the existing blind workflow against a new public benchmark only after preserving all current evidence and before any architecture change, but this step is intentionally not performed here.

## Agent usage status
The project has been preserved and validated using the existing local tooling and repository structure. No architecture redesign or challenge solution work was introduced during preservation.

## Important files and directories
- `agents/`
- `benchmarks/`
- `datasets/`
- `findings/`
- `hypotheses/`
- `prompts/`
- `research_memory/`
- `results/`
- `scripts/`
- `src/`
- `targets/`
- `tests/`
- `.gitignore`

## Commands needed to reproduce the current state

From the workspace root:

```bash
cd /workspaces/smart-contract-research-agent
PYTHONPATH="$PWD" /home/codespace/.python/current/bin/pytest -q tests
cd /workspaces/smart-contract-research-agent
~/.foundry/bin/forge test -q
python3 scripts/import_target.py --dir datasets/public_ctfs/damn-vulnerable-defi
```

These commands represent the repository’s current local validation and import workflow as preserved in this checkpoint.
