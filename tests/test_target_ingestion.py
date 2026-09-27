from pathlib import Path

import pytest

from agents.target_ingestion import TargetImportError, TargetImporter


def _write_contract(path: Path, source: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def test_import_from_file_creates_target_manifest(tmp_path):
    contract_path = _write_contract(
        tmp_path / "src" / "Simple.sol",
        """
        pragma solidity ^0.8.24;

        contract Simple {
            function ping() external pure returns (uint256) {
                return 42;
            }
        }
        """,
    )

    importer = TargetImporter(target_root=tmp_path / "targets")
    result = importer.import_from_file(contract_path)

    assert result["target_id"]
    assert result["metadata"]["source_type"] == "file"
    assert result["network_policy"] == "LOCAL_ONLY"
    assert (tmp_path / "targets" / result["target_id"] / "metadata.json").exists()
    assert (tmp_path / "targets" / result["target_id"] / "inventory.json").exists()
    assert (tmp_path / "targets" / result["target_id"] / "source").exists()


def test_import_from_repo_accepts_local_git_style_path(tmp_path):
    repo_root = tmp_path / "repo"
    _write_contract(
        repo_root / "src" / "Vault.sol",
        """
        pragma solidity ^0.8.24;

        contract Vault {
            uint256 public value;
            function set(uint256 v) external { value = v; }
        }
        """,
    )

    importer = TargetImporter(target_root=tmp_path / "targets")
    result = importer.import_from_repo(str(repo_root))

    assert result["metadata"]["source_type"] == "repository"
    assert result["inventory"]["solidity_files"]
    assert result["target_id"]


def test_import_from_code_creates_local_target(tmp_path):
    importer = TargetImporter(target_root=tmp_path / "targets")
    result = importer.import_from_code(
        """
        pragma solidity ^0.8.24;

        contract PastedTarget {
            function get() external pure returns (uint256) {
                return 7;
            }
        }
        """
    )

    assert result["metadata"]["source_type"] == "code"
    assert result["target_id"]
    assert result["research_status"] in {"READY", "PENDING"}


def test_invalid_or_empty_inputs_raise_error(tmp_path):
    importer = TargetImporter(target_root=tmp_path / "targets")

    with pytest.raises(TargetImportError):
        importer.import_target(source="")

    with pytest.raises(TargetImportError):
        importer.import_from_url("not-a-valid-url")


def test_missing_compiler_is_reported(tmp_path, monkeypatch):
    source = tmp_path / "MissingCompiler.sol"
    source.write_text(
        """
        pragma solidity ^0.9.0;

        contract MissingCompiler {
            function demo() external pure returns (uint256) { return 1; }
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr("agents.target_ingestion.shutil.which", lambda _name: None)

    importer = TargetImporter(target_root=tmp_path / "targets")
    result = importer.import_from_file(source)

    assert result["build_status"] == "MISSING_COMPILER"


def test_build_failure_is_recorded(tmp_path, monkeypatch):
    source = _write_contract(
        tmp_path / "Bad.sol",
        """
        pragma solidity ^0.8.24;

        contract Bad {
            function broken( returns (uint256) {
                return 1;
            }
        }
        """,
    )

    def fake_run(*args, **kwargs):
        return type("Completed", (), {"returncode": 1, "stdout": "", "stderr": "compile failed"})()

    monkeypatch.setattr("agents.target_ingestion.subprocess.run", fake_run)
    monkeypatch.setattr("agents.target_ingestion.shutil.which", lambda _name: "/usr/bin/forge")

    importer = TargetImporter(target_root=tmp_path / "targets")
    result = importer.import_from_file(source)

    assert result["build_status"] == "BUILD_FAILED"


def test_multi_contract_repository_is_inventoried(tmp_path):
    repo = tmp_path / "multi"
    _write_contract(
        repo / "src" / "A.sol",
        """
        pragma solidity ^0.8.24;
        contract A {}
        """,
    )
    _write_contract(
        repo / "src" / "B.sol",
        """
        pragma solidity ^0.8.24;
        import "./A.sol";
        contract B is A {}
        """,
    )

    importer = TargetImporter(target_root=tmp_path / "targets")
    result = importer.import_from_directory(repo)

    assert len(result["inventory"]["solidity_files"]) >= 2
    assert "A.sol" in result["inventory"]["solidity_files"][0] or len(result["inventory"]["solidity_files"]) >= 2
    assert result["metadata"]["source_type"] == "directory"


def test_target_isolation_and_local_only_policy(tmp_path):
    repo = tmp_path / "lab"
    _write_contract(
        repo / "src" / "Only.sol",
        """
        pragma solidity ^0.8.24;
        contract Only {
            function ok() external pure returns (bool) { return true; }
        }
        """,
    )

    importer = TargetImporter(target_root=tmp_path / "targets")
    result = importer.import_from_directory(repo)

    target_dir = tmp_path / "targets" / result["target_id"]
    assert target_dir.exists()
    assert (target_dir / "source").exists()
    assert result["network_policy"] == "LOCAL_ONLY"
    assert result["metadata"]["live_transaction_allowed"] is False
