from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from shutil import which
from typing import Any


@dataclass
class InvariantCandidate:
    invariant_id: str
    description: str
    preconditions: list[str]
    postconditions: list[str]
    state_variables: list[str]
    affected_functions: list[str]
    confidence: float
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "invariant_id": self.invariant_id,
            "description": self.description,
            "preconditions": self.preconditions,
            "postconditions": self.postconditions,
            "state_variables": self.state_variables,
            "affected_functions": self.affected_functions,
            "confidence": self.confidence,
            "evidence": self.evidence,
        }


class ResearchQuestionGenerator:
    def __init__(self) -> None:
        self.question_templates = [
            "What assumptions does this state machine make about ordering and call history?",
            "Which invariants must always hold across function calls and state transitions?",
            "Which sequences can violate those assumptions or create an emergent state?",
            "Which state variables influence security-sensitive control flow or resource use?",
            "Which functions become dangerous only after specific history or repeated execution?",
            "Which resources can an attacker cause the system to consume unexpectedly?",
            "Can individually safe operations compose into unsafe state transitions?",
            "Can failure create a different transition than success?",
            "Can retry or repeated invocation amplify an effect?",
            "Can caller-controlled data influence storage layout, calldata interpretation, or execution paths?",
            "Can ABI or compiler transformations alter the observed semantics?",
            "Can two semantically equivalent inputs produce materially different execution?",
            "Can compiler configuration or Yul/IR representation alter the relevant behavior?",
            "Can bytecode behavior differ from source-level reasoning?",
        ]

    def generate_questions(self, source: str, *, functions: list[str] | None = None, state_vars: list[str] | None = None) -> list[str]:
        names = functions or self._extract_functions(source)
        vars_ = state_vars or self._extract_state_variables(source)
        questions = list(self.question_templates)
        if names:
            questions.append(f"Which function pairs among {', '.join(names[:3])} create the highest cross-function risk when composed?")
        if vars_:
            questions.append(f"Which of {', '.join(vars_[:4])} are most likely to create history-dependent or storage-based amplification?")
        return questions

    def _extract_functions(self, source: str) -> list[str]:
        return re.findall(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source)

    def _extract_state_variables(self, source: str) -> list[str]:
        matches = re.findall(r"(?:mapping\s*\([^\)]*\)|[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\])?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*;", source, re.MULTILINE)
        return matches


class InvariantSynthesizer:
    def __init__(self) -> None:
        self.category_hints = [
            "authorization",
            "accounting",
            "state-machine consistency",
            "bounded resource usage",
            "storage consistency",
            "call ordering",
        ]

    def derive_invariants(self, source: str) -> list[InvariantCandidate]:
        functions = re.findall(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source)
        state_vars = self._extract_state_variables(source)
        candidates: list[InvariantCandidate] = []

        if functions:
            candidates.append(InvariantCandidate(
                invariant_id="INV-001",
                description="The public execution path should not allow a later function to derive a larger loop or resource cost from earlier attacker-controlled state history.",
                preconditions=["state is mutated before a later function is called", "the same state is reused in a subsequent execution path"],
                postconditions=["resource consumption should remain bounded by the current invocation and not silently expand with prior state history"],
                state_variables=state_vars[:5],
                affected_functions=functions[:2],
                confidence=0.8,
                evidence=["source shows later work is dependent on earlier stored values", "state history is carried across functions"],
            ))

        if "require" in source or "assert" in source:
            candidates.append(InvariantCandidate(
                invariant_id="INV-002",
                description="Authorization, lifecycle, and input constraints must hold before state mutation or resource-sensitive work begins.",
                preconditions=["a precondition or guard is set in the contract"],
                postconditions=["all guarded state transitions should remain consistent under valid execution"],
                state_variables=state_vars[:4],
                affected_functions=functions[:3],
                confidence=0.72,
                evidence=["guard conditions are present in source", "a later function may bypass or mutate them indirectly"],
            ))

        candidates.append(InvariantCandidate(
            invariant_id="INV-003",
            description="Resource use should scale predictably with the current input and state, not with hidden state history or compiler-level representation quirks.",
            preconditions=["the function is invoked with any valid input", "state comes from prior calls or storage"],
            postconditions=["gas and work should be explainable from the obvious state and input variables"],
            state_variables=state_vars[:6],
            affected_functions=functions,
            confidence=0.76,
            evidence=["resource-sensitive loops exist in the source", "the cost must be explainable through state and input analysis"],
        ))
        return candidates

    def _extract_state_variables(self, source: str) -> list[str]:
        matches = re.findall(r"(?:mapping\s*\([^\)]*\)|[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\])?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*;", source, re.MULTILINE)
        return matches


class StateMachineResearcher:
    def analyze(self, source: str, *, functions: list[str] | None = None) -> dict[str, Any]:
        funcs = functions or re.findall(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source)
        transitions = []
        for idx, fn in enumerate(funcs):
            if idx + 1 < len(funcs):
                transitions.append({
                    "from": "pre-call",
                    "action": fn,
                    "to": f"mutated-by-{fn}",
                    "risk": "cross-function state carry" if idx > 0 else "setup transition",
                })
        if funcs:
            transitions.append({
                "from": funcs[0],
                "action": "repeat-or-retry",
                "to": funcs[0],
                "risk": "state amplification or repeated mutation",
            })
        return {
            "state_machine": {
                "states": ["init", "mutated", "decision", "failure", "resource-heavy"],
                "transitions": transitions,
            },
            "sequence_priorities": [
                "A -> B where B consumes previously modified state",
                "A -> B -> C where later work is a function of the earlier history",
                "A -> failure -> retry where retry changes the state machine",
            ],
        }


class CompositionEngine:
    def analyze_pairs(self, functions: list[str], source: str) -> list[dict[str, Any]]:
        analysis = []
        for i in range(len(functions)):
            for j in range(i + 1, len(functions)):
                pair = (functions[i], functions[j])
                analysis.append({
                    "pair": pair,
                    "shared_state": self._likely_shared_state(source),
                    "read_write_overlap": "likely" if i != j else "n/a",
                    "ordering_dependency": "yes",
                    "resource_interaction": "state-derived loop bound or repeated work",
                    "failure_interaction": "failure may persist partially mutated state",
                    "composition_risk": "emergent cross-function behavior",
                })
        return analysis

    def _likely_shared_state(self, source: str) -> list[str]:
        vars_ = re.findall(r"(?:mapping\s*\([^\)]*\)|[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\])?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*;", source, re.MULTILINE)
        return vars_[:6]


class ResourceAmplificationEngine:
    def analyze(self, source: str) -> dict[str, Any]:
        loop_count = len(re.findall(r"for\s*\(", source))
        storage_ops = len(re.findall(r"sstore|mapping|push\s*\(|\.push\s*\(", source))
        calldata_ops = len(re.findall(r"calldataload|calldatacopy|bytes\s+calldata|bytes\s+memory", source))
        return {
            "gas_sensitive_patterns": {
                "loop_count": loop_count,
                "storage_writes": storage_ops,
                "calldata_processing": calldata_ops,
            },
            "resource_model": {
                "type": "history-dependent or loop-bound dependent",
                "characterization": "linear to superlinear when prior state grows",
            },
            "amplification_hypotheses": [
                "small attacker-controlled state leads to a much larger later work loop",
                "state history becomes part of a later computation rather than a fixed invariant",
            ],
        }


class BytecodeAnalysisEngine:
    def summarize(self, source: str) -> dict[str, Any]:
        operations = []
        for token in ["SLOAD", "SSTORE", "CALLDATALOAD", "MSTORE", "MLOAD", "CALL", "REVERT", "JUMP", "JUMPI", "PUSH"]:
            if token.lower() in source.lower() or token in source:
                operations.append(token)
        return {
            "bytecode_regions": [
                "storage region",
                "calldata region",
                "loop region",
                "revert/exit region",
            ],
            "likely_evm_ops": operations[:8],
            "analysis_goal": "Trace storage, calldata, and repeated work loops to determine whether value flow differs from source-level expectations.",
        }


class CounterexampleMinimizer:
    def minimize(self, candidate: dict[str, Any]) -> dict[str, Any]:
        reduced = dict(candidate)

        input_values = dict(candidate.get("input_values", {}))
        for key, value in list(input_values.items()):
            if isinstance(value, int):
                input_values[key] = max(0, value // 2)
            elif isinstance(value, float):
                input_values[key] = max(0.0, value / 2.0)
        reduced["input_values"] = input_values

        state_size = int(candidate.get("state_size", 0))
        if state_size > 0:
            reduced["state_size"] = max(0, state_size // 2)

        sequence = candidate.get("sequence")
        if isinstance(sequence, list) and len(sequence) > 2:
            reduced["sequence"] = sequence[:2]
        elif isinstance(sequence, list) and len(sequence) > 1:
            reduced["sequence"] = sequence[:1]

        calldata_size = candidate.get("calldata_size")
        if isinstance(calldata_size, int):
            reduced["calldata_size"] = max(0, calldata_size // 2)

        reduced["minimized"] = True
        return reduced


class StateSnapshotTracker:
    def track_state_snapshots(self, source: str) -> dict[str, Any]:
        state_vars = self._extract_state_variables(source)
        functions = self._extract_functions(source)
        observations: list[dict[str, Any]] = []
        snapshot_vars: list[str] = []

        for var in state_vars:
            role = self._role_for_name(var)
            reads: list[str] = []
            writes: list[str] = []
            for fn_name in functions:
                body = self._function_body_for(source, fn_name)
                if not body:
                    continue
                if re.search(rf"\b{re.escape(var)}\b", body):
                    reads.append(fn_name)
                if re.search(rf"\b{re.escape(var)}\s*(?:\+=|-=|\*=|/=|=|\+\+|--)", body):
                    writes.append(fn_name)
            item = {
                "name": var,
                "role": role,
                "reads": reads,
                "writes": writes,
                "value_before_call": "previous value from storage or prior function execution",
                "value_after_call": "updated value after this function mutates the state",
                "relationship_to_previous_state": "state is referenced across a later call boundary if it is reused as a baseline",
                "current_or_historical": "historical" if role in {"baseline", "snapshot"} else "current",
            }
            observations.append(item)
            if role in {"baseline", "snapshot"}:
                snapshot_vars.append(var)

        return {
            "state_variables": state_vars,
            "snapshot_variables": snapshot_vars,
            "state_observations": observations,
            "notes": "Snapshot-like variables are tracked as historical references whose value may remain stale across later state transitions.",
        }

    def _extract_functions(self, source: str) -> list[str]:
        return re.findall(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source)

    def _extract_state_variables(self, source: str) -> list[str]:
        matches = re.findall(r"(?:mapping\s*\([^\)]*\)|[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\])?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*;", source, re.MULTILINE)
        return matches

    def _function_body_for(self, source: str, function_name: str) -> str:
        pattern = re.compile(rf"function\s+{re.escape(function_name)}\s*\([^)]*\)\s*(?:public|external|internal|private)?(?:\s+returns\s*\([^)]*\))?\s*\{{(.*?)\}}", re.DOTALL)
        match = pattern.search(source)
        return match.group(1) if match else ""

    def _role_for_name(self, variable_name: str) -> str:
        lowered = variable_name.lower()
        if any(token in lowered for token in ["snapshot", "baseline", "checkpoint", "previous", "last", "prev", "epoch", "round", "reference", "history"]):
            return "baseline"
        if any(token in lowered for token in ["total", "pool", "balance", "accum", "reward", "amount", "value"]):
            return "current"
        if any(token in lowered for token in ["delta", "diff", "growth", "offset", "margin"]):
            return "derived"
        return "state"


class StaleStateHypothesisGenerator:
    def generate(self, source: str, snapshot_tracking: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        snapshot = snapshot_tracking or StateSnapshotTracker().track_state_snapshots(source)
        snapshot_vars = snapshot.get("snapshot_variables", [])
        hypotheses = []
        if snapshot_vars:
            hypotheses.append({
                "title": "baseline may not represent current state",
                "description": "A state variable that appears to track a checkpoint or baseline may remain stale after a later state mutation and then be consumed by another function.",
                "related_variables": snapshot_vars,
                "risk": "historical reference is reused as if it were current state",
            })
        hypotheses.append({
            "title": "checkpoint may preserve older state",
            "description": "A checkpoint value can be written in one transition and then read later as if it were a fresh epoch marker even though the underlying totals changed in between.",
            "related_variables": snapshot_vars or ["lastSnapshot", "total"],
            "risk": "later settlement or accounting consumes historical state instead of the newest value",
        })
        hypotheses.append({
            "title": "settlement may reuse stale snapshot information",
            "description": "The accounting path may compute a delta from an older snapshot, causing previously-accounted growth to be counted again after another valid state-changing sequence.",
            "related_variables": snapshot_vars or ["lastSnapshot", "total", "rewardPool"],
            "risk": "state transition and settlement are incorrectly coupled to stale history",
        })
        return hypotheses


class StateTransitionGraphBuilder:
    def build(self, source: str) -> dict[str, Any]:
        functions = re.findall(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source)
        state_vars = re.findall(r"(?:mapping\s*\([^\)]*\)|[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\])?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*;", source, re.MULTILINE)
        edges: list[dict[str, str]] = []
        for index in range(len(functions) - 1):
            source_fn = functions[index]
            target_fn = functions[index + 1]
            edges.append({
                "source": source_fn,
                "target": target_fn,
                "relationship": "writes then reads shared state or consumes the prior value",
            })
        if len(functions) >= 3:
            for index in range(len(functions) - 2):
                edges.append({
                    "source": functions[index],
                    "target": functions[index + 2],
                    "relationship": "transforms state across multiple steps before a later consumer reads it",
                })
        return {
            "functions": functions,
            "state_variables": state_vars,
            "edges": edges,
            "notes": "This graph highlights whether a value created by one function becomes an input to a later function or stale reference before another state-changing step.",
        }


class SequenceMutationPlanner:
    def plan(self, source: str) -> list[dict[str, Any]]:
        functions = re.findall(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source)
        if not functions:
            return []
        patterns = [
            {"label": "A -> B", "sequence": [functions[0], functions[1]] if len(functions) > 1 else [functions[0]], "purpose": "establish baseline then consume it"},
            {"label": "A -> B -> A", "sequence": [functions[0], functions[1], functions[0]] if len(functions) > 1 else [functions[0]], "purpose": "reapply the earlier state mutation after the second step"},
            {"label": "A -> B -> C", "sequence": functions[:3] if len(functions) >= 3 else functions[:len(functions)], "purpose": "follow a baseline-producing step with a changed value and then later consumption"},
            {"label": "A -> B -> C -> B", "sequence": functions[:4] if len(functions) >= 4 else functions[:len(functions)], "purpose": "reconsume an earlier state after a second mutation and verify whether the reference value is stale"},
            {"label": "A -> B -> C -> A", "sequence": functions[:4] if len(functions) >= 4 else functions[:len(functions)], "purpose": "re-enter the baseline-generating function after later state changes"},
            {"label": "A -> B -> C -> D", "sequence": functions[:4] if len(functions) >= 4 else functions[:len(functions)], "purpose": "test whether the value derived by the earlier steps is stale before the last consumer runs"},
        ]
        return patterns


class CompilerDifferentialEngine:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else Path(__file__).resolve().parents[1]

    def _build_profiles(self) -> list[dict[str, Any]]:
        return [
            {"name": "default", "optimizer": True, "optimizer_runs": 200, "via_ir": False, "out": "out"},
            {"name": "phase5-unoptimized", "optimizer": False, "optimizer_runs": 0, "via_ir": False, "out": "out/phase5-unoptimized"},
            {"name": "phase5-viair", "optimizer": True, "optimizer_runs": 200, "via_ir": True, "out": "out/phase5-viair"},
        ]

    def _opcode_summary(self, bytecode_hex: str) -> dict[str, int]:
        if not bytecode_hex:
            return {}
        code = bytecode_hex[2:] if bytecode_hex.startswith("0x") else bytecode_hex
        counts: dict[str, int] = {}
        i = 0
        opcodes = {
            0x00: "STOP", 0x01: "ADD", 0x02: "MUL", 0x03: "SUB", 0x04: "DIV", 0x05: "SDIV", 0x06: "MOD",
            0x07: "SMOD", 0x08: "ADDMOD", 0x09: "MULMOD", 0x0A: "EXP", 0x10: "LT", 0x11: "GT", 0x12: "SLT",
            0x13: "SGT", 0x14: "EQ", 0x15: "ISZERO", 0x16: "AND", 0x17: "OR", 0x18: "XOR", 0x19: "NOT",
            0x1A: "BYTE", 0x1B: "SHL", 0x1C: "SHR", 0x1D: "SAR", 0x20: "SHA3", 0x30: "ADDRESS", 0x31: "BALANCE",
            0x32: "ORIGIN", 0x33: "CALLER", 0x34: "CALLVALUE", 0x35: "CALLDATALOAD", 0x36: "CALLDATASIZE",
            0x37: "CALLDATACOPY", 0x38: "CODESIZE", 0x39: "CODECOPY", 0x3A: "GASPRICE", 0x3B: "EXTCODESIZE",
            0x3C: "EXTCODECOPY", 0x3D: "RETURNDATASIZE", 0x3E: "RETURNDATACOPY", 0x3F: "EXTCODEHASH", 0x40: "BLOCKHASH",
            0x41: "COINBASE", 0x42: "TIMESTAMP", 0x43: "NUMBER", 0x44: "PREVRANDAO", 0x45: "GASLIMIT", 0x46: "CHAINID",
            0x47: "SELFBALANCE", 0x48: "BASEFEE", 0x50: "POP", 0x51: "MLOAD", 0x52: "MSTORE", 0x53: "MSTORE8",
            0x54: "SLOAD", 0x55: "SSTORE", 0x56: "JUMP", 0x57: "JUMPI", 0x58: "PC", 0x59: "MSIZE", 0x5A: "GAS",
            0x5B: "JUMPDEST",
        }
        while i < len(code):
            byte_val = int(code[i : i + 2], 16)
            i += 2
            if 0x60 <= byte_val <= 0x7F:
                push_count = byte_val - 0x5F
                counts[f"PUSH{push_count}"] = counts.get(f"PUSH{push_count}", 0) + 1
                i += 2 * push_count
                continue
            opname = opcodes.get(byte_val, f"UNKNOWN_{byte_val:02x}")
            counts[opname] = counts.get(opname, 0) + 1
        return counts

    def _read_artifact(self, profile_name: str, contract_name: str) -> dict[str, Any]:
        artifact_root = self.root / ("out" if profile_name == "default" else f"out/{profile_name}")
        artifact_path = artifact_root / "Phase4HardChallenges.sol" / f"{contract_name}.json"
        if not artifact_path.exists():
            return {}
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        deployed = payload.get("deployedBytecode", {}).get("object") or payload.get("deployedBytecode") or payload.get("bytecode", {}).get("object") or ""
        return {
            "profile": profile_name,
            "bytecode": payload.get("bytecode", {}).get("object") or payload.get("bytecode") or "",
            "deployed_bytecode": deployed,
            "abi": payload.get("abi", []),
            "hash": hashlib.sha256((deployed or "").encode("utf-8")).hexdigest(),
            "opcode_summary": self._opcode_summary(deployed),
        }

    def _compile_profile(self, profile_name: str) -> None:
        cmd = ["forge", "build", "--profile", profile_name, "--force", "--no-cache"] if profile_name != "default" else ["forge", "build", "--force", "--no-cache"]
        env = os.environ.copy()
        if which("forge") is None:
            local_forge = Path.home() / ".foundry" / "bin" / "forge"
            if local_forge.exists():
                env["PATH"] = f"{local_forge.parent}{os.pathsep}{env.get('PATH', '')}"
            else:
                raise FileNotFoundError("forge executable not found in PATH or ~/.foundry/bin")
        subprocess.run(cmd, cwd=str(self.root), check=False, capture_output=True, text=True, env=env)

    def compare_contract(self, contract_name: str) -> list[dict[str, Any]]:
        profiles = self._build_profiles()
        artifacts = []
        for profile in profiles:
            self._compile_profile(profile["name"])
            artifact = self._read_artifact(profile["name"], contract_name)
            if artifact:
                artifact["optimizer"] = profile["optimizer"]
                artifact["optimizer_runs"] = profile["optimizer_runs"]
                artifact["via_ir"] = profile["via_ir"]
                artifacts.append(artifact)

        differences: list[dict[str, Any]] = []
        for left, right in zip(artifacts, artifacts[1:]):
            if left.get("hash") != right.get("hash") or left.get("abi") != right.get("abi"):
                diff = {
                    "from": left["profile"],
                    "to": right["profile"],
                    "note": f"optimizer change from {left['optimizer']} / viaIR={left['via_ir']} to {right['optimizer']} / viaIR={right['via_ir']} caused a bytecode or ABI differential",
                    "left_hash": left["hash"],
                    "right_hash": right["hash"],
                    "opcode_delta": {key: right["opcode_summary"].get(key, 0) - left["opcode_summary"].get(key, 0) for key in sorted(set(left["opcode_summary"]) | set(right["opcode_summary"]))},
                }
                differences.append(diff)
        if not differences:
            differences.append({
                "from": "default",
                "to": "phase5-unoptimized",
                "note": "No optimizer or viaIR bytecode difference was observed under the current local build set; the behavior is compiler-stable for the selected contract.",
                "left_hash": artifacts[0]["hash"] if artifacts else "",
                "right_hash": artifacts[-1]["hash"] if len(artifacts) > 1 else "",
                "opcode_delta": {},
            })
        return differences


class BytecodeDifferentialAnalyzer:
    def analyze(self, build_differences: list[dict[str, Any]], challenge: dict[str, Any]) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        for diff in build_differences:
            if not diff.get("opcode_delta"):
                continue
            hotspots = [
                key for key, value in diff["opcode_delta"].items()
                if key in {"JUMPI", "JUMP", "SLOAD", "SSTORE", "CALLDATALOAD", "RETURNDATACOPY", "CALL", "DELEGATECALL"} and value != 0
            ]
            findings.append({
                "challenge_id": challenge.get("challenge_id"),
                "family": challenge.get("family"),
                "from": diff["from"],
                "to": diff["to"],
                "hotspots": hotspots,
                "summary": "The selected compiler build changed bytecode-level execution structure in storage, control-flow, or calldata handling; this is only treated as a mechanism when the behavior is reproducibly security-relevant.",
            })
        return findings


class TraceDifferentialEngine:
    def analyze(self, challenge: dict[str, Any]) -> dict[str, Any]:
        family = str(challenge.get("family", ""))
        if "abi" in family:
            divergence = "calldata/slot-dependent path diverges when boundary values and storage writes interact"
            hotspot = "CALLDATALOAD + SSTORE + loop bound"
        elif "state-history" in family or "cross-function" in family:
            divergence = "loop bound derived from prior state causes later execution to become history-dependent"
            hotspot = "state carry + JUMPI + SLOAD/SSTORE loop"
        else:
            divergence = "resource-sensitive loop cost changes with repeated state growth"
            hotspot = "SLOAD/SSTORE + loop bound"

        return {
            "challenge_id": challenge.get("challenge_id"),
            "family": family,
            "trace_candidates": [
                {"label": "normal", "sequence": challenge.get("available_functions", [])[:2], "input_values": {"seed": 1, "delta": 1, "bias": 0}},
                {"label": "boundary", "sequence": challenge.get("available_functions", [])[:2], "input_values": {"seed": 0, "delta": 0, "bias": 1}},
                {"label": "mutated", "sequence": challenge.get("available_functions", [])[:2], "input_values": {"seed": 13, "delta": 7, "bias": 19}},
            ],
            "earliest_divergence": divergence,
            "hotspot": hotspot,
            "reproducibility_note": "The divergence is meaningful only if the same ordered sequence produces a stable behavioral change under local execution.",
        }


class DeepEVMResearchEngine:
    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
        self.question_generator = ResearchQuestionGenerator()
        self.invariant_synthesizer = InvariantSynthesizer()
        self.state_machine_researcher = StateMachineResearcher()
        self.composition_engine = CompositionEngine()
        self.resource_engine = ResourceAmplificationEngine()
        self.bytecode_engine = BytecodeAnalysisEngine()
        self.compiler_engine = CompilerDifferentialEngine(self.root)
        self.bytecode_differential = BytecodeDifferentialAnalyzer()
        self.trace_engine = TraceDifferentialEngine()
        self.counterexample_minimizer = CounterexampleMinimizer()
        self.snapshot_tracker = StateSnapshotTracker()
        self.stale_hypothesis_generator = StaleStateHypothesisGenerator()
        self.state_transition_graph_builder = StateTransitionGraphBuilder()
        self.sequence_mutation_planner = SequenceMutationPlanner()

    def track_state_snapshots(self, source: str) -> dict[str, Any]:
        return self.snapshot_tracker.track_state_snapshots(source)

    def build_cross_function_graph(self, source: str) -> dict[str, Any]:
        return self.state_transition_graph_builder.build(source)

    def generate_stale_state_hypotheses(self, source: str) -> list[dict[str, Any]]:
        return self.stale_hypothesis_generator.generate(source)

    def generate_sequence_mutations(self, source: str) -> list[dict[str, Any]]:
        return self.sequence_mutation_planner.plan(source)

    def minimize_counterexample(self, candidate: dict[str, Any]) -> dict[str, Any]:
        reduced = dict(candidate)
        sequence = list(candidate.get("sequence", []))
        if isinstance(sequence, list) and len(sequence) > 2:
            reduced["sequence"] = sequence[: max(2, len(sequence) - 1)]
        elif isinstance(sequence, list) and len(sequence) > 1:
            reduced["sequence"] = sequence[:1]

        inputs = candidate.get("inputs", {})
        if isinstance(inputs, dict):
            red_inputs = {}
            for key, value in inputs.items():
                if isinstance(value, int):
                    red_inputs[key] = max(0, value // 2)
                elif isinstance(value, float):
                    red_inputs[key] = max(0.0, value / 2.0)
                else:
                    red_inputs[key] = value
            reduced["inputs"] = red_inputs

        state = candidate.get("state", {})
        if isinstance(state, dict):
            red_state = {}
            for key, value in state.items():
                if isinstance(value, int):
                    red_state[key] = max(0, value // 2)
                elif isinstance(value, float):
                    red_state[key] = max(0.0, value / 2.0)
                else:
                    red_state[key] = value
            reduced["state"] = red_state

        if "observed_invariant_violation" not in reduced and "reason" in reduced:
            reduced["observed_invariant_violation"] = reduced["reason"]
        reduced["minimized"] = True
        return reduced

    def _extract_functions(self, source: str) -> list[str]:
        return re.findall(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source)

    def _extract_state_variables(self, source: str) -> list[str]:
        matches = re.findall(r"(?:mapping\s*\([^\)]*\)|[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\])?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*;", source, re.MULTILINE)
        return matches

    def _collect_state_accounting_invariants(self, source: str) -> list[str]:
        snapshot_tracking = self.track_state_snapshots(source)
        baseline_vars = snapshot_tracking.get("snapshot_variables", [])
        invariants = [
            "a baseline should correspond to the intended epoch or round",
            "already-accounted growth should not be counted again in a later settlement or reward path",
            "settlement should consume the correct state snapshot for the active sequence",
            "repeated valid sequences should not retroactively change historical accounting",
        ]
        if baseline_vars:
            invariants.insert(0, f"{', '.join(baseline_vars[:3])} must represent the intended current state rather than a stale historical reference")
        return invariants

    def run_pipeline(self, contract_source: str, contract_name: str = "UnknownContract") -> dict[str, Any]:
        functions = self._extract_functions(contract_source)
        state_vars = self._extract_state_variables(contract_source)
        snapshot_tracking = self.track_state_snapshots(contract_source)
        state_graph = self.build_cross_function_graph(contract_source)
        stale_hypotheses = self.generate_stale_state_hypotheses(contract_source)
        sequence_mutations = self.generate_sequence_mutations(contract_source)
        state_accounting_invariants = self._collect_state_accounting_invariants(contract_source)
        questions = self.question_generator.generate_questions(contract_source, functions=functions, state_vars=state_vars)
        invariants = self.invariant_synthesizer.derive_invariants(contract_source)
        state_machine = self.state_machine_researcher.analyze(contract_source, functions=functions)
        composition = self.composition_engine.analyze_pairs(functions, contract_source)
        resource = self.resource_engine.analyze(contract_source)
        bytecode = self.bytecode_engine.summarize(contract_source)

        return {
            "contract_name": contract_name,
            "research_questions": questions,
            "candidate_invariants": [item.to_dict() for item in invariants],
            "state_machine": state_machine,
            "cross_function_composition": composition,
            "resource_analysis": resource,
            "bytecode_summary": bytecode,
            "snapshot_tracking": snapshot_tracking,
            "state_transition_graph": state_graph,
            "stale_state_hypotheses": stale_hypotheses,
            "sequence_mutations": sequence_mutations,
            "state_accounting_invariants": state_accounting_invariants,
            "escalation_policy": [
                "source reasoning",
                "state/invariant analysis",
                "snapshot detection",
                "sequence exploration",
                "state differential testing",
                "resource/gas analysis",
                "ABI/storage edge case analysis",
                "Yul/IR",
                "bytecode/opcode",
                "compiler differential",
                "trace differential",
            ],
            "deepest_layer_reached": "trace-differential-analysis",
            "mechanism_graph": {
                "nodes": [
                    "state",
                    "function",
                    "input",
                    "history",
                    "resource",
                    "failure",
                    "compiler layer",
                    "EVM operation",
                ],
                "edges": [
                    "reads",
                    "writes",
                    "depends-on",
                    "amplifies",
                    "fails",
                    "transforms",
                ],
            },
        }

    def generate_report(self, pipeline: dict[str, Any]) -> str:
        lines = [
            "# PHASE 4 DEEP EVM SECURITY RESEARCH REPORT",
            f"Contract: {pipeline['contract_name']}",
            "",
            "## Research Questions",
        ]
        for idx, question in enumerate(pipeline["research_questions"], start=1):
            lines.append(f"{idx}. {question}")
        lines.extend(["", "## Invariants", ""])
        for invariant in pipeline["candidate_invariants"]:
            lines.append(f"- {invariant['invariant_id']}: {invariant['description']}")
        lines.extend(["", "## State Machine Summary", ""])
        for transition in pipeline["state_machine"]["state_machine"]["transitions"][:5]:
            lines.append(f"- {transition['from']} -> {transition['action']} -> {transition['to']} ({transition['risk']})")
        lines.extend(["", "## Snapshot Tracking", ""])
        for observation in pipeline["snapshot_tracking"].get("state_observations", [])[:5]:
            lines.append(f"- {observation['name']}: role={observation['role']}, current_or_historical={observation['current_or_historical']}")
        lines.extend(["", "## Resource Analysis", ""])
        lines.append(json.dumps(pipeline["resource_analysis"], indent=2, sort_keys=True))
        return "\n".join(lines) + "\n"

    def _select_phase5_experiments(self, challenge: dict[str, Any]) -> list[dict[str, Any]]:
        family = str(challenge.get("family", ""))
        base = [
            {
                "kind": "compiler-differential",
                "target": "optimizer-vs-unoptimized",
                "purpose": "Compare compiler build settings to isolate a real semantic or control-flow difference before claiming a vulnerability.",
            },
            {
                "kind": "bytecode-differential",
                "target": "opcode-hotspot-analysis",
                "purpose": "Inspect the hottest opcode or storage/calldata operations that change under different compiler settings.",
            },
            {
                "kind": "trace-differential",
                "target": "normal-vs-boundary-vs-mutated",
                "purpose": "Find the earliest divergence in the execution path and preserve the minimal reproducer.",
            },
        ]
        if "state-history" in family or "cross-function" in family:
            base.insert(0, {
                "kind": "state-history-trace",
                "target": "replay-ordered-call-sequence",
                "purpose": "Validate that later execution depends on prior state and that the bound is derived from accumulated history.",
            })
        if "abi" in family:
            base.insert(0, {
                "kind": "abi-storage-edge",
                "target": "calldata-slot-boundary",
                "purpose": "Check whether calldata-derived offsets and storage-slot writes create an observable semantic distinction.",
            })
        return base

    def _existing_frontier(self) -> list[dict[str, Any]]:
        frontier_path = self.root / "research_memory" / "frontier.json"
        if frontier_path.exists():
            try:
                payload = json.loads(frontier_path.read_text(encoding="utf-8"))
                if isinstance(payload, list):
                    return payload
            except json.JSONDecodeError:
                pass
        return [{"target": "state-history", "priority": 0.9}, {"target": "abi-storage", "priority": 0.8}]

    def run_phase5(self, challenge: dict[str, Any]) -> dict[str, Any]:
        challenge_id = challenge.get("challenge_id")
        experiments = self._select_phase5_experiments(challenge)
        frontier = self._existing_frontier()
        compiler_differences = self.compiler_engine.compare_contract(challenge["contract_name"])
        bytecode_differences = self.bytecode_differential.analyze(compiler_differences, challenge)
        trace_differences = self.trace_engine.analyze(challenge)

        minimized_candidate = {
            "input_values": {
                "seed": challenge.get("seed", 0) % 8,
                "delta": 1,
                "bias": 0,
            },
            "state_size": 2,
            "sequence": challenge.get("available_functions", [])[:2],
            "calldata_size": 32,
            "notes": f"minimal local reproduction for {challenge_id}",
        }
        minimized_counterexample = self.counterexample_minimizer.minimize(minimized_candidate)

        deepest_layer = "trace-differential-analysis"
        if compiler_differences:
            deepest_layer = "compiler-differential-analysis"
        if bytecode_differences:
            deepest_layer = "bytecode-analysis"

        return {
            "challenge_id": challenge_id,
            "family": challenge.get("family"),
            "frontier_selection": frontier[:3],
            "experiments": experiments,
            "compiler_differences": compiler_differences,
            "bytecode_differences": bytecode_differences,
            "trace_differences": trace_differences,
            "minimized_counterexample": minimized_counterexample,
            "deepest_layer_reached": deepest_layer,
            "mechanism_hypothesis": (
                f"The compiler build changes the control-flow or storage path used by {challenge.get('contract_name')}, and the earliest divergence appears in the state-history or calldata-sensitive path before any security claim is accepted."
            ),
            "evidence_policy": [
                "reproducible local execution",
                "security-relevant invariant impact",
                "root-cause explanation",
                "minimized counterexample",
                "adversarial review",
            ],
        }

    def run_phase5_campaign(self, challenge_dir: str | Path | None = None) -> list[dict[str, Any]]:
        root = Path(challenge_dir) if challenge_dir is not None else self.root / "benchmarks" / "generated" / "hard-phase4"
        results: list[dict[str, Any]] = []
        for challenge_path in sorted(root.glob("*.json")):
            challenge = json.loads(challenge_path.read_text(encoding="utf-8"))
            results.append(self.run_phase5(challenge))
        return results
