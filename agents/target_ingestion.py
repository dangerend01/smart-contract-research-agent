from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python < 3.11 fallback
    tomllib = None

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET_ROOT = ROOT / "targets"
DEFAULT_UI_PORT = 8000


class TargetImportError(ValueError):
    """Raised when a target cannot be imported safely or meaningfully."""


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "target"


def _safe_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _normalize_compiler_version(value: str) -> str:
    if not value:
        return "unknown"
    match = re.search(r"(\d+\.\d+\.\d+|\d+\.\d+)", str(value))
    if match:
        return match.group(1)
    cleaned = str(value).strip().strip("^~><=()[]{} ")
    return cleaned or "unknown"


class TargetImporter:
    def __init__(self, target_root: str | Path = DEFAULT_TARGET_ROOT):
        self.target_root = Path(target_root).resolve()
        self.imported_root = self.target_root / "imported"
        self.normalized_root = self.target_root / "normalized"
        self.manifests_root = self.target_root / "manifests"
        self.reports_root = self.target_root / "reports"
        for directory in [self.target_root, self.imported_root, self.normalized_root, self.manifests_root, self.reports_root]:
            directory.mkdir(parents=True, exist_ok=True)

    def _copy_tree(self, source_root: Path, destination_root: Path) -> None:
        destination_root.mkdir(parents=True, exist_ok=True)
        for file_path in source_root.rglob("*"):
            if file_path.is_dir():
                continue
            relative = file_path.relative_to(source_root)
            target = destination_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, target)

    def _detect_project_type(self, root: Path) -> dict[str, Any]:
        foundry_cfg = root / "foundry.toml"
        hardhat_cfg = any((root / name).exists() for name in ["hardhat.config.js", "hardhat.config.ts", "hardhat.config.cjs"])
        package_json = root / "package.json"
        project = {
            "kind": "plain-solidity",
            "has_foundry": foundry_cfg.exists(),
            "has_hardhat": hardhat_cfg,
            "has_package_json": package_json.exists(),
            "folders": {
                "src": (root / "src").exists(),
                "contracts": (root / "contracts").exists(),
                "test": (root / "test").exists(),
                "tests": (root / "tests").exists(),
                "lib": (root / "lib").exists(),
            },
        }
        if foundry_cfg.exists():
            project["kind"] = "foundry"
        elif hardhat_cfg:
            project["kind"] = "hardhat"
        return project

    def _read_foundry_config(self, root: Path) -> dict[str, Any]:
        foundry_cfg = root / "foundry.toml"
        config: dict[str, Any] = {}
        if foundry_cfg.exists():
            try:
                if tomllib is not None:
                    with foundry_cfg.open("rb") as handle:
                        config = tomllib.load(handle)
            except Exception:
                config = {}
        return config

    def _detect_compiler_version(self, root: Path, source_files: list[str]) -> str:
        candidates: list[str] = []
        for file_path in root.rglob("*.sol"):
            if not file_path.is_file():
                continue
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            for match in re.findall(r"pragma\s+solidity\s+([^;]+);", text):
                candidates.append(match.strip())
        config = self._read_foundry_config(root)
        if config:
            for key in ["solc_version", "solc", "solc-version"]:
                value = config.get("profile", {}).get("default", {}).get(key) or config.get(key)
                if value:
                    return _normalize_compiler_version(str(value))
                for profile in config.get("profile", {}).values():
                    if isinstance(profile, dict):
                        value = profile.get(key)
                        if value:
                            return _normalize_compiler_version(str(value))
        if candidates:
            return _normalize_compiler_version(candidates[0])
        return "unknown"

    def _detect_license(self, root: Path) -> str:
        for candidate in ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING", "COPYING.txt"]:
            license_file = root / candidate
            if license_file.exists():
                return candidate
        return "unknown"

    def _detect_commit(self, repo_root: Path) -> str:
        if not (repo_root / ".git").exists():
            return "unknown"
        try:
            result = subprocess.run(["git", "-C", str(repo_root), "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
            return result.stdout.strip() or "unknown"
        except Exception:
            return "unknown"

    def _ensure_foundry_wrapper(self, root: Path, compiler_version: str) -> None:
        config_path = root / "foundry.toml"
        if config_path.exists():
            return
        root_sol_files = list(root.glob("*.sol"))
        if root_sol_files:
            src_value = "."
        elif (root / "src").exists():
            src_value = "src"
        elif (root / "contracts").exists():
            src_value = "contracts"
        else:
            src_value = "."
        config_path.write_text(
            "[profile.default]\n"
            f"src = '{src_value}'\n"
            "out = 'out'\n"
            "libs = ['lib']\n"
            f"solc_version = '{_normalize_compiler_version(compiler_version)}'\n",
            encoding="utf-8",
        )

    def _sync_plain_solidity_foundry_config(self, root: Path, compiler_version: str) -> None:
        config_path = root / "foundry.toml"
        if not config_path.exists():
            self._ensure_foundry_wrapper(root, compiler_version)
            return
        current = config_path.read_text(encoding="utf-8")
        normalized = _normalize_compiler_version(compiler_version)
        if "src =" not in current:
            current = "[profile.default]\n" + current if not current.startswith("[profile.default]") else current
            current = current.replace("[profile.default]\n", "[profile.default]\nsrc = '.'\n", 1)
        if "solc_version" not in current:
            current += f"\nsolc_version = '{normalized}'\n"
        else:
            current = re.sub(r"solc_version\s*=\s*['\"][^'\"]*['\"]", f"solc_version = '{normalized}'", current, count=1)
        config_path.write_text(current, encoding="utf-8")

    def _build_manifest(self, target_id: str, metadata: dict[str, Any], inventory: dict[str, Any], source_root: Path, project_type: dict[str, Any], repo_url: str | None = None, commit: str | None = None) -> dict[str, Any]:
        compiler_version = self._detect_compiler_version(source_root, inventory["solidity_files"])
        manifest = {
            "target_id": target_id,
            "source_type": metadata["source_type"],
            "source_location": metadata["original_ref"],
            "repository": repo_url or metadata.get("repository"),
            "commit": commit or metadata.get("commit"),
            "license": self._detect_license(source_root),
            "import_timestamp": metadata["created_at"],
            "compiler_version": compiler_version,
            "foundry_configuration": self._read_foundry_config(source_root),
            "contracts": inventory["contract_names"],
            "interfaces": inventory["interfaces"],
            "libraries": inventory["libraries"],
            "build_status": metadata["build_status"],
            "research_status": metadata["research_status"],
            "network_policy": metadata["network_policy"],
            "local_only": metadata["local_only"],
            "project_type": project_type,
            "source_files": inventory["solidity_files"],
            "analysis_package": {
                "functions": [],
                "modifiers": [],
                "state_variables": [],
                "events": [],
                "external_calls": [],
                "delegatecalls": [],
                "callbacks": [],
                "loops": [],
                "storage_reads": [],
                "storage_writes": [],
                "abi": [],
                "bytecode": "not-generated",
                "compiler_metadata": {
                    "version": compiler_version,
                    "optimizer": "not-set",
                    "via_ir": False,
                },
            },
        }
        return manifest

    def _write_target_artifacts(self, target_id: str, target_dir: Path, metadata: dict[str, Any], inventory: dict[str, Any], project_type: dict[str, Any], repo_url: str | None = None, commit: str | None = None) -> dict[str, Any]:
        target_dir.mkdir(parents=True, exist_ok=True)
        manifest = self._build_manifest(target_id, metadata, inventory, target_dir / "source", project_type, repo_url=repo_url, commit=commit)
        self.manifests_root.mkdir(parents=True, exist_ok=True)
        (self.manifests_root / f"{target_id}.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        (target_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
        (self.reports_root / f"{target_id}.md").write_text(self._build_report(target_id, metadata, inventory, project_type), encoding="utf-8")
        return manifest

    def _build_report(self, target_id: str, metadata: dict[str, Any], inventory: dict[str, Any], project_type: dict[str, Any]) -> str:
        return (
            f"# Target Report: {target_id}\n\n"
            "This target is imported and stored locally for authorized, offline, evidence-driven smart-contract research.\n\n"
            f"- Source type: {metadata['source_type']}\n"
            f"- Source location: {metadata['original_ref']}\n"
            f"- Network policy: {metadata['network_policy']}\n"
            f"- Build status: {metadata['build_status']}\n"
            f"- Research status: {metadata['research_status']}\n"
            f"- Project kind: {project_type['kind']}\n"
            f"- UI port: {metadata['ui_port']} (kept separate from the local Anvil JSON-RPC endpoint at 8545)\n\n"
            "## Solidity inventory\n\n"
            + "\n".join(f"- {item}" for item in inventory["solidity_files"]) + "\n\n"
            + "## Notes\n\n"
            + "- No live blockchain or arbitrary external transaction system is used.\n"
            + "- The imported target remains isolated under the local target directory.\n"
            + "- Research execution should proceed only with local compilation, replay, and evidence collection.\n"
        )

    def import_target(
        self,
        *,
        source: str | None = None,
        url: str | None = None,
        repo: str | None = None,
        file: str | None = None,
        directory: str | None = None,
        code: str | None = None,
    ) -> dict[str, Any]:
        sources = [
            ("url", url),
            ("repo", repo),
            ("file", file),
            ("directory", directory),
            ("code", code),
            ("source", source),
        ]
        selected = [name for name, value in sources if value not in (None, "")]
        if not selected:
            raise TargetImportError("No target source was provided. Use --url, --repo, --file, --dir, --code, or a raw source string.")

        if len(selected) > 1:
            raise TargetImportError("Provide exactly one target source option at a time.")

        name, value = next((name, val) for name, val in sources if val not in (None, ""))
        if name == "url":
            return self.import_from_url(value)
        if name == "repo":
            return self.import_from_repo(value)
        if name == "file":
            return self.import_from_file(value)
        if name == "directory":
            return self.import_from_directory(value)
        if name == "code":
            return self.import_from_code(value)
        if name == "source":
            source_value = str(value)
            if source_value.startswith("http://") or source_value.startswith("https://"):
                return self.import_from_url(source_value)
            if source_value.startswith("file://"):
                return self.import_from_url(source_value)
            if Path(source_value).exists():
                path = Path(source_value).resolve()
                if path.is_dir():
                    return self.import_from_directory(str(path))
                return self.import_from_file(str(path))
            return self.import_from_code(source_value)
        raise TargetImportError(f"Unsupported target source: {name}")

    def import_from_url(self, url: str) -> dict[str, Any]:
        if not url or not re.match(r"^(https?|git@|ssh://|file://)", url):
            raise TargetImportError(f"Unsupported import URL: {url}")

        clean_url = url.strip()
        if clean_url.startswith("file://"):
            local_path = Path(clean_url[7:]).resolve()
            if local_path.exists():
                if local_path.is_dir():
                    return self.import_from_directory(str(local_path))
                return self.import_from_file(str(local_path))
            raise TargetImportError(f"File-backed target does not exist: {local_path}")

        with tempfile.TemporaryDirectory(prefix="target-import-") as temp_dir:
            temp_path = Path(temp_dir)
            clone_target = temp_path / "source"
            try:
                subprocess.run(["git", "clone", "--depth", "1", clean_url, str(clone_target)], check=True, capture_output=True, text=True)
            except (subprocess.CalledProcessError, FileNotFoundError) as exc:
                raise TargetImportError(f"Git import failed for {clean_url}: {exc}") from exc
            commit = self._detect_commit(clone_target)
            return self._materialize_target(clone_target, source_type="repository", original_ref=clean_url, repo_url=clean_url, commit=commit)

    def import_from_repo(self, repo: str) -> dict[str, Any]:
        path = Path(repo).expanduser().resolve()
        if path.exists():
            return self._materialize_target(path, source_type="repository", original_ref=str(path), repo_url=str(path), commit=self._detect_commit(path))
        if re.match(r"^(https?|git@|ssh://)", repo):
            return self.import_from_url(repo)
        raise TargetImportError(f"Repository path does not exist: {repo}")

    def import_from_file(self, file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path).expanduser().resolve()
        if not path.exists():
            raise TargetImportError(f"Target file does not exist: {path}")
        if path.is_dir():
            return self.import_from_directory(str(path))
        if path.suffix.lower() != ".sol":
            raise TargetImportError(f"Only Solidity files can be imported directly: {path}")
        return self._materialize_target(path.parent, source_type="file", original_ref=str(path), selected_file=path.name)

    def import_from_directory(self, directory: str | Path) -> dict[str, Any]:
        path = Path(directory).expanduser().resolve()
        if not path.exists() or not path.is_dir():
            raise TargetImportError(f"Target directory does not exist: {path}")
        return self._materialize_target(path, source_type="directory", original_ref=str(path), repo_url=str(path))

    def import_from_code(self, code: str) -> dict[str, Any]:
        if not code or not code.strip():
            raise TargetImportError("The pasted Solidity source is empty.")
        if "pragma solidity" not in code:
            raise TargetImportError("Pasted Solidity source does not contain a pragma declaration.")
        target_name = self._infer_contract_name(code) or "PastedTarget"
        return self._materialize_target_from_code(code, target_name)

    def _infer_contract_name(self, code: str) -> str | None:
        match = re.search(r"contract\s+(\w+)", code)
        return match.group(1) if match else None

    def _iter_copyable_files(self, source_root: Path):
        target_root_resolved = self.target_root.resolve()
        for file_path in source_root.rglob("*"):
            if file_path.is_dir():
                continue
            try:
                file_path.relative_to(target_root_resolved)
            except ValueError:
                yield file_path
            else:
                continue

    def _materialize_target(
        self,
        source_root: Path,
        source_type: str,
        original_ref: str,
        selected_file: str | None = None,
        repo_url: str | None = None,
        commit: str | None = None,
    ) -> dict[str, Any]:
        if not source_root.exists():
            raise TargetImportError(f"Source root does not exist: {source_root}")

        source_root = source_root.resolve()
        solidity_files = sorted(str(p.relative_to(source_root)) for p in source_root.rglob("*.sol") if p.is_file())
        if not solidity_files:
            raise TargetImportError(f"No Solidity files were found in: {source_root}")

        target_id = slugify(f"{source_type}-{Path(original_ref).name}-{_safe_hash(original_ref)}")
        target_dir = self.target_root / target_id
        if target_dir.exists():
            shutil.rmtree(target_dir)

        source_dir = target_dir / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        if source_type == "file" and selected_file:
            selected_path = source_root / selected_file
            if selected_path.exists():
                dest = source_dir / selected_path.name
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(selected_path, dest)
        else:
            for file_path in self._iter_copyable_files(source_root):
                relative = file_path.relative_to(source_root)
                dest = source_dir / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest)

        inventory = self._inventory_solidity_files(source_dir)
        project_type = self._detect_project_type(source_root)
        compiler_version = self._detect_compiler_version(source_root, inventory["solidity_files"])
        if project_type["kind"] == "plain-solidity":
            self._sync_plain_solidity_foundry_config(source_dir, compiler_version)
        build_status = self._attempt_build(source_dir)

        metadata = {
            "target_id": target_id,
            "source_type": source_type,
            "original_ref": original_ref,
            "source_root": str(source_dir),
            "repository": repo_url,
            "commit": commit,
            "local_only": True,
            "network_policy": "LOCAL_ONLY",
            "live_transaction_allowed": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "compiler_version": compiler_version,
            "ui_port": DEFAULT_UI_PORT,
            "build_status": build_status,
            "research_status": "READY" if build_status == "OK" else "BUILD_FAILED" if build_status in {"BUILD_FAILED", "MISSING_COMPILER"} else "PENDING",
            "compiler_requirements": inventory["compiler_requirements"],
            "contract_names": inventory["contract_names"],
            "license": self._detect_license(source_root),
        }

        (target_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        (target_dir / "inventory.json").write_text(json.dumps(inventory, indent=2, sort_keys=True), encoding="utf-8")

        self.imported_root.mkdir(parents=True, exist_ok=True)
        imported_target = self.imported_root / target_id
        if imported_target.exists():
            shutil.rmtree(imported_target)
        self._copy_tree(source_dir, imported_target)

        normalized_target = self.normalized_root / target_id
        if normalized_target.exists():
            shutil.rmtree(normalized_target)
        self._copy_tree(source_dir, normalized_target)
        if not (normalized_target / "foundry.toml").exists():
            self._ensure_foundry_wrapper(normalized_target, compiler_version)

        manifest = self._write_target_artifacts(target_id, target_dir, metadata, inventory, project_type, repo_url=repo_url, commit=commit)
        build_dir = target_dir / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "experiments").mkdir(parents=True, exist_ok=True)
        (target_dir / "findings").mkdir(parents=True, exist_ok=True)
        (target_dir / "report.md").write_text(self._build_report(target_id, metadata, inventory, project_type), encoding="utf-8")

        result = {
            "target_id": target_id,
            "target_dir": str(target_dir),
            "source_dir": str(source_dir),
            "metadata": metadata,
            "inventory": inventory,
            "build_status": build_status,
            "research_status": metadata["research_status"],
            "network_policy": "LOCAL_ONLY",
            "ui_port": DEFAULT_UI_PORT,
            "manifest": manifest,
            "compiler_version": compiler_version,
        }
        return result

    def _materialize_target_from_code(self, code: str, contract_name: str) -> dict[str, Any]:
        target_id = slugify(f"pasted-{contract_name}-{_safe_hash(code)}")
        target_dir = self.target_root / target_id
        if target_dir.exists():
            shutil.rmtree(target_dir)

        source_dir = target_dir / "source"
        source_dir.mkdir(parents=True, exist_ok=True)
        source_file = source_dir / f"{contract_name}.sol"
        source_file.write_text(code, encoding="utf-8")

        inventory = self._inventory_solidity_files(source_dir)
        project_type = self._detect_project_type(source_dir)
        compiler_version = self._detect_compiler_version(source_dir, inventory["solidity_files"])
        if project_type["kind"] == "plain-solidity":
            self._sync_plain_solidity_foundry_config(source_dir, compiler_version)
        build_status = self._attempt_build(source_dir)
        metadata = {
            "target_id": target_id,
            "source_type": "code",
            "original_ref": "pasted-source",
            "source_root": str(source_dir),
            "repository": None,
            "commit": None,
            "local_only": True,
            "network_policy": "LOCAL_ONLY",
            "live_transaction_allowed": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "compiler_version": compiler_version,
            "ui_port": DEFAULT_UI_PORT,
            "build_status": build_status,
            "research_status": "READY" if build_status == "OK" else "BUILD_FAILED" if build_status in {"BUILD_FAILED", "MISSING_COMPILER"} else "PENDING",
            "compiler_requirements": inventory["compiler_requirements"],
            "contract_names": inventory["contract_names"],
            "license": "unknown",
        }

        (target_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        (target_dir / "inventory.json").write_text(json.dumps(inventory, indent=2, sort_keys=True), encoding="utf-8")
        (target_dir / "build").mkdir(parents=True, exist_ok=True)
        (target_dir / "experiments").mkdir(parents=True, exist_ok=True)
        (target_dir / "findings").mkdir(parents=True, exist_ok=True)
        manifest = self._write_target_artifacts(target_id, target_dir, metadata, inventory, project_type, repo_url=None, commit=None)
        (target_dir / "report.md").write_text(self._build_report(target_id, metadata, inventory, project_type), encoding="utf-8")

        return {
            "target_id": target_id,
            "target_dir": str(target_dir),
            "source_dir": str(source_dir),
            "metadata": metadata,
            "inventory": inventory,
            "build_status": build_status,
            "research_status": metadata["research_status"],
            "network_policy": "LOCAL_ONLY",
            "ui_port": DEFAULT_UI_PORT,
            "manifest": manifest,
            "compiler_version": compiler_version,
        }

    def _inventory_solidity_files(self, root: Path) -> dict[str, Any]:
        solidity_files = sorted(str(path.relative_to(root)) for path in root.rglob("*.sol") if path.is_file())
        contracts: list[str] = []
        libraries: list[str] = []
        interfaces: list[str] = []
        imports: list[str] = []
        compiler_requirements: list[str] = []

        for path in root.rglob("*.sol"):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            contracts.extend(re.findall(r"\bcontract\s+(\w+)", text))
            libraries.extend(re.findall(r"\blibrary\s+(\w+)", text))
            interfaces.extend(re.findall(r"\binterface\s+(\w+)", text))
            imports.extend(re.findall(r"import\s+[\"']([^\"']+)[\"'];", text))
            compiler_requirements.extend(re.findall(r"pragma\s+solidity\s+([^;]+);", text))

        return {
            "solidity_files": solidity_files,
            "contract_names": contracts,
            "libraries": libraries,
            "interfaces": interfaces,
            "imports": imports,
            "compiler_requirements": sorted(set(compiler_requirements)),
            "primary_contract": contracts[0] if contracts else None,
        }

    def _attempt_build(self, root: Path) -> str:
        sol_files = list(root.rglob("*.sol"))
        if not sol_files:
            return "EMPTY"

        if shutil.which("forge") is not None:
            try:
                result = subprocess.run(["forge", "build", "--root", str(root)], capture_output=True, text=True, cwd=str(root))
                if result.returncode == 0:
                    return "OK"
                return "BUILD_FAILED"
            except FileNotFoundError:
                pass

        if shutil.which("solc") is not None:
            try:
                result = subprocess.run(["solc", "--bin", str(sol_files[0])], capture_output=True, text=True, cwd=str(root))
                if result.returncode == 0:
                    return "OK"
                return "BUILD_FAILED"
            except FileNotFoundError:
                pass

        compiler_requirements = self._inventory_solidity_files(root)["compiler_requirements"]
        if compiler_requirements and any("0.9" in req or "0.8" in req for req in compiler_requirements):
            return "MISSING_COMPILER"
        return "MISSING_COMPILER"

    def resolve_primary_contract(self, target_dir: str | Path) -> Path | None:
        target_path = Path(target_dir).resolve()
        metadata_path = target_path / "metadata.json"
        inventory_path = target_path / "inventory.json"
        if not metadata_path.exists() or not inventory_path.exists():
            return None

        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        files = inventory.get("solidity_files", [])
        if not files:
            return None
        return target_path / "source" / files[0]


def main() -> int:
    try:
        importer = TargetImporter()
        result = importer.import_target(source=sys.argv[1] if len(sys.argv) > 1 else None)
        print(f"TARGET IMPORTED: {result['target_id']} ({result['metadata']['source_type']})")
        print(f"Research status: {result['research_status']}")
        return 0
    except TargetImportError as exc:
        print(f"TARGET IMPORT FAILED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
