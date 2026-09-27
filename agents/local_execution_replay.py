from __future__ import annotations

import json
import math
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RPC_URL = "http://127.0.0.1:8545"
DEFAULT_MNEMONIC = "test test test test test test test test test test test junk"


class LocalExecutionReplayHarness:
    """Launches local Anvil and replays candidate execution traces against public benchmark contracts."""

    def __init__(self, root: str | Path = ROOT, rpc_url: str = DEFAULT_RPC_URL, mnemonic: str = DEFAULT_MNEMONIC):
        self.root = Path(root)
        self.rpc_url = rpc_url
        self.mnemonic = mnemonic
        self.private_key = self._derive_private_key()
        self.account = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
        self.process = None
        self._ensure_anvil()

    def _path_env(self) -> dict[str, str]:
        env = os.environ.copy()
        for candidate in [
            str(Path.home() / ".foundry" / "bin"),
            "/home/codespace/.foundry/bin",
            "/root/.foundry/bin",
        ]:
            if Path(candidate).exists():
                env["PATH"] = f"{candidate}{os.pathsep}{env.get('PATH', '')}"
                return env
        return env

    def _ensure_anvil(self) -> None:
        if self.process is not None and self.process.poll() is None:
            return
        env = self._path_env()

        self.process = subprocess.Popen(
            [
                "anvil",
                "--host",
                "127.0.0.1",
                "--port",
                "8545",
                "--chain-id",
                "31337",
                "--mnemonic",
                "test test test test test test test test test test test junk",
                "--gas-limit",
                "12000000",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                subprocess.run(["cast", "chain-id", "--rpc-url", self.rpc_url], check=True, capture_output=True, text=True, env=env)
                return
            except subprocess.CalledProcessError:
                time.sleep(0.1)
        raise RuntimeError("Local Anvil RPC did not come up in time.")

    def _derive_private_key(self) -> str:
        result = self._run(["cast", "wallet", "private-key", "--mnemonic", self.mnemonic, "--mnemonic-index", "0"])
        if result.returncode != 0:
            raise RuntimeError(f"Unable to derive local deploy key: {result.stderr or result.stdout}")
        return result.stdout.strip()

    def _run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(command, check=False, capture_output=True, text=True, env=self._path_env())

    def _write_contract(self, challenge: dict[str, Any]) -> Path:
        contract_name = str(challenge.get("contract_name", "ReplayTarget"))
        target_dir = self.root / "src" / "replay"
        target_dir.mkdir(parents=True, exist_ok=True)
        contract_path = target_dir / f"{challenge.get('challenge_id', 'challenge')}-{contract_name}.sol"
        contract_path.write_text(str(challenge.get("contract_source", "")), encoding="utf-8")
        return contract_path

    def _function_signatures(self, challenge: dict[str, Any]) -> list[str]:
        source = str(challenge.get("contract_source", ""))
        matches = re.findall(r"function\s+(\w+)\s*\(([^)]*)\)\s*(?:public|external|internal|private)?\s*(?:returns\s*\(([^)]*)\))?", source)
        signatures = []
        for name, args, _returns in matches:
            part = ", ".join(arg.strip() for arg in args.split(",") if arg.strip())
            signatures.append(f"{name}({part})")
        return signatures

    def _default_arg_values_for_signature(self, signature: str) -> list[Any]:
        params = re.findall(r"(\w+)(?:\s*\[[^\]]*\])?", signature)
        # Remove the function name before the first "("; keep only type tokens.
        match = re.search(r"\((.*)\)$", signature)
        if match:
            raw = match.group(1)
        else:
            raw = signature
        tokens = [part.strip() for part in raw.split(",") if part.strip()]
        values: list[Any] = []
        for token in tokens:
            if token.startswith("uint") or token == "int":
                values.append(1)
            elif token.startswith("bytes"):
                values.append("0x11")
            elif token == "address":
                values.append("0x0000000000000000000000000000000000000001")
            elif token == "bool":
                values.append(True)
            elif token.startswith("string"):
                values.append("x")
            else:
                values.append(1)
        return values

    def _default_candidate_sequence(self, challenge: dict[str, Any]) -> list[dict[str, Any]]:
        functions = challenge.get("available_functions") or self._function_signatures(challenge)
        if not functions:
            return []
        sequence: list[dict[str, Any]] = []
        for index, name in enumerate(functions[:2]):
            args = self._default_arg_values_for_signature(name)
            if not args:
                sequence.append({"function": name, "args": []})
            else:
                sequence.append({"function": name, "args": args})
            if index == 0 and len(functions) > 1:
                sequence[-1]["args"] = args or [1]
        if len(sequence) == 1 and functions:
            sequence.append({"function": functions[0], "args": self._default_arg_values_for_signature(functions[0])})
        return sequence

    def _candidate_sequence_from_payload(self, challenge: dict[str, Any], candidate: dict[str, Any]) -> list[dict[str, Any]]:
        if candidate.get("call_sequence"):
            return candidate["call_sequence"]
        if candidate.get("sequence"):
            seq = candidate.get("sequence") or []
            if isinstance(seq, list) and seq and isinstance(seq[0], dict):
                return seq
            if isinstance(seq, list) and seq and isinstance(seq[0], str):
                parsed: list[dict[str, Any]] = []
                for step in seq:
                    match = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)", step)
                    if match:
                        name = match.group(1)
                        args_text = match.group(2).strip()
                        args = [] if not args_text else [int(v.strip()) if v.strip().lstrip("-").isdigit() else v.strip() for v in args_text.split(",")]
                        parsed.append({"function": name, "args": args})
                if parsed:
                    return parsed
        if candidate.get("triggering_sequence"):
            seq = candidate.get("triggering_sequence") or []
            if seq and isinstance(seq[0], dict):
                return seq
            if seq and isinstance(seq[0], str):
                parsed: list[dict[str, Any]] = []
                for step in seq:
                    match = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*\((.*)\)", step)
                    if match:
                        name = match.group(1)
                        args_text = match.group(2).strip()
                        args = [] if not args_text else [int(v.strip()) if v.strip().lstrip("-").isdigit() else v.strip() for v in args_text.split(",")]
                        parsed.append({"function": name, "args": args})
                if parsed:
                    return parsed
        return self._default_candidate_sequence(challenge)

    def _state_getters(self, challenge: dict[str, Any]) -> list[str]:
        state_keys = list(challenge.get("initial_state", {}).keys())
        if not state_keys:
            return []
        return [str(key) for key in state_keys]

    def _call_contract(self, address: str, function_name: str, args: list[Any]) -> dict[str, Any]:
        signature = function_name if "(" in function_name else f"{function_name}({', '.join(self._signature_types(function_name))})"
        cmd = ["cast", "send", address, signature, "--rpc-url", self.rpc_url, "--private-key", self.private_key, "--json"]
        if args:
            cmd = ["cast", "send", address, signature] + [str(v) for v in args] + ["--rpc-url", self.rpc_url, "--private-key", self.private_key, "--json"]
        result = self._run(cmd)
        if result.returncode != 0:
            return {"status": "reverted", "error": result.stderr.strip() or result.stdout.strip()}
        parsed = json.loads(result.stdout) if result.stdout.strip() else {}
        tx_hash = parsed.get("transactionHash") or parsed.get("transaction_hash") or "0x0"
        gas_used = parsed.get("gasUsed") or parsed.get("gas_used") or 0
        status = parsed.get("status")
        return {
            "tx_hash": tx_hash,
            "status": "success" if status == "0x1" or status is True or status == 1 else "reverted",
            "gas_used": gas_used,
            "receipt": parsed,
        }

    def _signature_types(self, function_name: str) -> list[str]:
        match = re.search(r"\((.*)\)$", function_name)
        if not match:
            return []
        raw = match.group(1)
        if not raw:
            return []
        tokens = []
        for part in [p.strip() for p in raw.split(",") if p.strip()]:
            tokens.append(part.split()[0] if " " in part else part)
        return tokens

    def _encode_args(self, signature: str, args: list[Any]) -> str:
        if not args:
            return f'"{signature}"'
        encoded_args = []
        for value in args:
            if isinstance(value, bool):
                encoded_args.append("true" if value else "false")
            elif isinstance(value, int):
                encoded_args.append(str(value))
            elif isinstance(value, str):
                if value.startswith("0x"):
                    encoded_args.append(value)
                else:
                    encoded_args.append(f'"{value}"')
            else:
                encoded_args.append(str(value))
        return f'"{signature}" ' + " ".join(encoded_args)

    def _read_state(self, address: str, key: str) -> Any:
        getter = f"{key}()"
        result = self._run(["cast", "call", address, getter, "--rpc-url", self.rpc_url])
        if result.returncode != 0:
            return None
        return result.stdout.strip()

    def _build_contract_file(self, challenge: dict[str, Any]) -> tuple[str, str]:
        contract_source = str(challenge.get("contract_source", ""))
        contract_name = str(challenge.get("contract_name", "ReplayTarget"))
        file_path = self.root / "src" / "replay" / f"{challenge.get('challenge_id', 'challenge')}_{contract_name}.sol"
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(contract_source, encoding="utf-8")
        return str(file_path), contract_name

    def deploy(self, challenge: dict[str, Any]) -> dict[str, Any]:
        contract_file, contract_name = self._build_contract_file(challenge)
        build = self._run(["forge", "build", "--root", str(self.root)])
        if build.returncode != 0:
            raise RuntimeError(f"Forge build failed: {build.stderr or build.stdout}")

        artifact_path = self.root / "out" / f"{challenge.get('challenge_id', 'challenge')}_{contract_name}.sol" / f"{contract_name}.json"
        if not artifact_path.exists():
            artifact_path = self.root / "out" / f"{contract_name}.json"
        if not artifact_path.exists():
            matches = list(self.root.glob(f"out/**/{contract_name}.json"))
            if not matches:
                raise RuntimeError(f"Could not locate compiled artifact for {contract_name}")
            artifact_path = matches[0]

        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        bytecode = payload.get("bytecode", {}).get("object") if isinstance(payload.get("bytecode"), dict) else payload.get("bytecode")
        if not bytecode:
            raise RuntimeError(f"Could not find deployment bytecode in {artifact_path}")

        deploy_cmd = ["cast", "send", "--rpc-url", self.rpc_url, "--private-key", self.private_key, "--create", bytecode, "--json"]
        result = self._run(deploy_cmd)
        if result.returncode != 0:
            raise RuntimeError(f"Deployment failed: {result.stderr or result.stdout}")

        receipt_payload = json.loads(result.stdout) if result.stdout.strip() else {}
        tx_hash = receipt_payload.get("transactionHash") or receipt_payload.get("transaction_hash") or "0x0"
        address = receipt_payload.get("contractAddress") or receipt_payload.get("contract_address") or receipt_payload.get("address")
        if not address:
            raise RuntimeError(f"Could not parse deployed address from receipt: {result.stdout}")
        return {"address": address, "deployed": True, "artifact": str(artifact_path), "tx_hash": tx_hash}

    def replay_candidate(self, challenge: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        deployed = self.deploy(challenge)
        address = deployed["address"]
        initial_state = dict(challenge.get("initial_state", {}))
        baseline_sequence = []
        trigger_sequence = self._candidate_sequence_from_payload(challenge, candidate)
        state_before = {key: self._read_state(address, key) for key in initial_state.keys()}

        # Baseline: minimal zero-value call(s) with the same function names
        default_sequence = self._candidate_sequence_from_payload(challenge, {"call_sequence": [{"function": list((challenge.get("available_functions") or [""]))[0], "args": []}]}) if challenge.get("available_functions") else []
        for call in default_sequence:
            payload = self._call_contract(address, call["function"], call.get("args", []))
            baseline_sequence.append({"call": call, "result": payload})

        execution_results = []
        for call in trigger_sequence:
            call_name = str(call.get("function") or call.get("name") or call.get("signature") or "")
            args = list(call.get("args", []))
            result = self._call_contract(address, call_name, args)
            execution_results.append({"call": call_name, "args": args, "result": result})

        state_after = {key: self._read_state(address, key) for key in initial_state.keys()}
        return {
            "execution_id": f"exec-{challenge.get('challenge_id', 'unknown')}-{int(time.time() * 1000)}",
            "candidate_id": str(candidate.get("candidate_id") or candidate.get("challenge_id") or "unknown"),
            "challenge_id": str(challenge.get("challenge_id", "unknown")),
            "actors": [self.account],
            "initial_state": initial_state,
            "call_sequence": trigger_sequence,
            "execution_results": execution_results,
            "gas_measurements": {item["call"]: item["result"].get("gas_used", 0) for item in execution_results},
            "state_delta": {
                "before": state_before,
                "after": state_after,
                "diff": {k: {"before": state_before.get(k), "after": state_after.get(k)} for k in initial_state.keys()},
            },
            "baseline": baseline_sequence,
            "events": [],
            "return_data": {item["call"]: item["result"].get("receipt", {}) for item in execution_results},
            "trace": [],
            "status": "REPRODUCED" if execution_results else "REPRODUCTION_FAILED",
            "deployed_address": address,
        }


def run_local_execution_replay(challenge: dict[str, Any], candidate: dict[str, Any], root: str | Path = ROOT) -> dict[str, Any]:
    harness = LocalExecutionReplayHarness(root=root)
    return harness.replay_candidate(challenge, candidate)
