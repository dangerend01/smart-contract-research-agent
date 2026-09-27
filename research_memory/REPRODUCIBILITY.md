# Reproducibility Checklist

## 1. Repository setup

```bash
cd /workspaces/smart-contract-research-agent
```

## 2. Python environment

This workspace uses the local Python environment already configured for the project.

```bash
PYTHONPATH=/workspaces/smart-contract-research-agent /home/codespace/.python/current/bin/pytest -q /workspaces/smart-contract-research-agent/tests
```

## 3. Foundry requirement

Foundry is required for local project builds and challenge tests.

```bash
~/.foundry/bin/forge --version
```

## 4. Target ingestion command

Use the existing import pipeline exactly as implemented:

```bash
cd /workspaces/smart-contract-research-agent
PYTHONPATH=/workspaces/smart-contract-research-agent python3 /workspaces/smart-contract-research-agent/scripts/import_target.py --dir datasets/public_ctfs/damn-vulnerable-defi
```

## 5. Research command

The project’s direct local research flow remains:

```bash
cd /workspaces/smart-contract-research-agent
PYTHONPATH=/workspaces/smart-contract-research-agent python3 /workspaces/smart-contract-research-agent/scripts/research_target.py --target <target-id> --target-root /workspaces/smart-contract-research-agent/targets
```

## 6. Benchmark location

- public CTF source: `datasets/public_ctfs/damn-vulnerable-defi/`
- imported target: `targets/directory-damn-vulnerable-defi-124d0aff6c7d/`
- benchmark report: `research_memory/benchmarks/2026-09-27-damn-vulnerable-defi-truster.md`

## 7. Test commands

```bash
cd /workspaces/smart-contract-research-agent
PYTHONPATH="$PWD" /home/codespace/.python/current/bin/pytest -q tests

cd /workspaces/smart-contract-research-agent
~/.foundry/bin/forge test -q
```

## 8. Result locations

- Python validation output: terminal output from `pytest`
- local benchmark evidence: `results/blind-discovery/20260927T182211Z/blind-research-output.json`
- imported target metadata: `targets/directory-damn-vulnerable-defi-124d0aff6c7d/metadata.json`
- local challenge test output: terminal logs from the challenge run

## 9. Git commit required

```bash
cd /workspaces/smart-contract-research-agent
git add -A
git commit -m "checkpoint: preserve public CTF research benchmark"
```

## 10. GitHub push required

```bash
git push
```

This checklist records the actual commands and result paths already used for preservation in this repository snapshot.
