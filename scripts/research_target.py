#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from agents.research_pipeline import analyze_contract
from agents.target_ingestion import TargetImporter


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local research flow against an imported target.")
    parser.add_argument("--target", required=True, help="Target ID to research.")
    parser.add_argument("--target-root", default=str(ROOT / "targets"), help="Root directory containing imported targets.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    target_root = Path(args.target_root).resolve()
    target_dir = target_root / args.target
    metadata_path = target_dir / "metadata.json"
    if not metadata_path.exists():
        raise SystemExit(f"Target not found: {target_dir}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata.get("network_policy") != "LOCAL_ONLY":
        raise SystemExit("This target is not marked as local-only; the local research pipeline is blocked.")

    importer = TargetImporter(target_root=target_root)
    contract_path = importer.resolve_primary_contract(target_dir)
    if contract_path is None:
        raise SystemExit(f"No Solidity contract file was found for target {args.target}")

    analysis = analyze_contract(contract_path)
    report_path = target_dir / "report.md"
    report_path.write_text(
        f"# Local Research Report for {args.target}\n\n"
        f"Generated: {datetime.now(timezone.utc).isoformat()}\n\n"
        f"- target_id: {args.target}\n"
        f"- source_type: {metadata['source_type']}\n"
        f"- network_policy: {metadata['network_policy']}\n"
        f"- hypothesis_count: {len(analysis.get('hypotheses', []))}\n"
        f"- invariant_count: {len(analysis.get('invariants', []))}\n\n"
        "The target remains in a local-only, evidence-first workflow and is not allowed to reach arbitrary live infrastructure.\n",
        encoding="utf-8",
    )

    print(f"TARGET IMPORTED: {args.target} (LOCAL_ONLY)")
    print(f"Research status: READY")
    print(f"Local analysis generated {len(analysis.get('hypotheses', []))} hypotheses for {contract_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
