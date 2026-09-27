#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from agents.target_ingestion import TargetImportError, TargetImporter


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import a local Solidity target into the offline research workspace.")
    parser.add_argument("target", nargs="?", help="Path to a Solidity file, project directory, or GitHub repository URL.")
    parser.add_argument("--url", help="Remote Git URL or file:// target to import.")
    parser.add_argument("--repo", help="Local repository path or remote Git repository URL to import.")
    parser.add_argument("--file", help="Single Solidity file to import.")
    parser.add_argument("--dir", dest="directory", help="Local directory containing a Solidity project.")
    parser.add_argument("--code", help="Raw Solidity source code or a path to a Solidity file containing source.")
    parser.add_argument("--target-root", default=str(ROOT / "targets"), help="Directory where imported targets are stored.")
    parser.add_argument("--research", action="store_true", help="Start the local research pipeline after import.")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    importer = TargetImporter(target_root=args.target_root)
    try:
        if args.target is not None and not any([args.url, args.repo, args.file, args.directory, args.code]):
            payload = importer.import_target(source=args.target)
        else:
            payload = importer.import_target(
                url=args.url,
                repo=args.repo,
                file=args.file,
                directory=args.directory,
                code=args.code,
            )
    except TargetImportError as exc:
        print(f"TARGET IMPORT FAILED: {exc}", file=sys.stderr)
        return 1

    print("TARGET IMPORTED")
    print(f"Target ID: {payload['target_id']}")
    print(f"Status: {payload['research_status']}")
    print(f"Contracts: {', '.join(payload['inventory']['contract_names']) if payload['inventory']['contract_names'] else 'n/a'}")
    print(f"Compiler: {payload['compiler_version']}")
    print(f"Build: {'PASS' if payload['build_status'] == 'OK' else 'FAIL'}")
    print(f"Research: {payload['research_status']}")
    if args.research:
        script = ROOT / "scripts" / "research_target.py"
        subprocess.run([sys.executable, str(script), "--target", payload["target_id"], "--target-root", str(args.target_root)], cwd=str(ROOT), check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
