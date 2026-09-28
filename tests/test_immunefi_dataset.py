import os
import json
import pytest
from pathlib import Path

ROOT = Path(__file__).parent.parent
IMMUNEFI_DIR = ROOT / "datasets" / "immunefi"


def test_immunefi_dataset_directory_structure():
    assert IMMUNEFI_DIR.exists(), "datasets/immunefi directory missing"
    assert (IMMUNEFI_DIR / "raw").exists(), "datasets/immunefi/raw missing"
    assert (IMMUNEFI_DIR / "raw" / "Past-Audit-Competitions").exists(), "raw repo missing"
    assert (IMMUNEFI_DIR / "index.jsonl").exists(), "index.jsonl missing"
    assert (IMMUNEFI_DIR / "manifest.json").exists(), "manifest.json missing"
    assert (IMMUNEFI_DIR / "knowledge_schema.json").exists(), "knowledge_schema.json missing"
    assert (IMMUNEFI_DIR / "knowledge").exists(), "knowledge/ directory missing"
    assert (IMMUNEFI_DIR / "ground_truth").exists(), "ground_truth/ directory missing"
    assert (IMMUNEFI_DIR / "blind").exists(), "blind/ directory missing"


def test_immunefi_manifest_validity():
    manifest_path = IMMUNEFI_DIR / "manifest.json"
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert manifest["source_type"] == "public_github_repository"
    assert manifest["repository"] == "immunefi-team/Past-Audit-Competitions"
    assert manifest["commit"] == "8ae02ec4c4b2cc549305cc7915e6c89f6bb41c6d"
    assert manifest["competition_count"] == 33
    assert manifest["report_file_count"] == 1001
    assert manifest["status"] == "preserved"


def test_immunefi_index_jsonl_integrity():
    index_path = IMMUNEFI_DIR / "index.jsonl"
    lines = index_path.read_text(encoding="utf-8").strip().splitlines()

    assert len(lines) == 1001, f"Expected 1001 indexed reports, found {len(lines)}"

    seen_hashes = set()
    seen_report_ids = set()

    for idx, line in enumerate(lines):
        record = json.loads(line)

        assert "report_id" in record
        assert "competition" in record
        assert "source_file" in record
        assert "raw_text_hash" in record

        raw_hash = record["raw_text_hash"]
        assert raw_hash not in seen_hashes, f"Duplicate raw text hash found: {raw_hash} at line {idx}"
        seen_hashes.add(raw_hash)

        report_id = record["report_id"]
        if report_id:
            assert report_id not in seen_report_ids, f"Duplicate report ID found: {report_id} at line {idx}"
            seen_report_ids.add(report_id)

        source_path = ROOT / "datasets" / record["source_file"]
        assert source_path.exists(), f"Source file does not exist: {source_path}"


def test_immunefi_knowledge_schema_validity():
    schema_path = IMMUNEFI_DIR / "knowledge_schema.json"
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    assert schema["title"] == "ImmunefiSecurityKnowledgeSchema"
    props = schema.get("properties", {})

    required_schema_fields = [
        "vulnerability_mechanism",
        "root_cause",
        "affected_state_variables",
        "affected_functions",
        "attacker_capabilities",
        "trust_assumptions",
        "preconditions",
        "state_dependencies",
        "cross_function_dependencies",
        "cross_contract_dependencies",
        "external_calls",
        "callbacks",
        "authorization_flow",
        "accounting_relationships",
        "oracle_dependencies",
        "token_interactions",
        "storage_dependencies",
        "temporal_ordering_dependencies",
        "required_transaction_sequence",
        "minimal_reproducible_sequence",
        "security_consequence",
        "exploitability_conditions",
        "compiler_solidity_version",
        "evm_related_conditions",
        "related_mechanisms",
        "mechanism_combinations",
        "invariant_violated",
        "evidence",
        "uncertainty",
        "source_report",
        "source_code",
        "remediation",
        "generalized_security_reasoning_pattern"
    ]

    for field in required_schema_fields:
        assert field in props, f"Field '{field}' missing from knowledge_schema.json"


def test_ground_truth_blind_separation():
    ground_truth_dir = IMMUNEFI_DIR / "ground_truth"
    blind_dir = IMMUNEFI_DIR / "blind"
    knowledge_dir = IMMUNEFI_DIR / "knowledge"

    assert ground_truth_dir.exists()
    assert blind_dir.exists()
    assert knowledge_dir.exists()

    assert ground_truth_dir.resolve() != blind_dir.resolve()
