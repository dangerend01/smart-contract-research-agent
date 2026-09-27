from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re


@dataclass
class FunctionSummary:
    name: str
    signature: str
    visibility: str
    modifiers: list[str] = field(default_factory=list)
    loops: list[str] = field(default_factory=list)
    external_calls: list[str] = field(default_factory=list)
    state_writes: list[str] = field(default_factory=list)


@dataclass
class ContractProfile:
    contract_name: str
    file_path: str
    functions: list[FunctionSummary]
    state_variables: list[str]
    modifiers: list[str]
    external_calls: list[str]
    loops: list[str]
    mappings: list[str]
    arrays: list[str]
    access_control_checks: list[str]
    eth_transfers: list[str]
    token_transfers: list[str]
    gas_sensitive_operations: list[str]
    state_transitions: list[str]


def _find_matching_brace(source: str, start_index: int) -> int:
    depth = 0
    for index in range(start_index, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    raise ValueError("unbalanced braces in contract")


def _extract_function_summaries(source: str) -> list[FunctionSummary]:
    pattern = re.compile(
        r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\)\s*(?:public|external|private|internal|view|pure|payable|\s)*\s*\{",
        re.DOTALL,
    )
    summaries: list[FunctionSummary] = []

    for match in pattern.finditer(source):
        name = match.group(1)
        signature = match.group(2).strip()
        decl = match.group(0)
        opening_brace_index = source.find("{", match.start())
        closing_brace_index = _find_matching_brace(source, opening_brace_index)
        body = source[opening_brace_index + 1 : closing_brace_index]

        visibility = "public"
        for token in ("external", "public", "internal", "private"):
            if token in decl:
                visibility = token
                break

        modifiers = re.findall(r"\b(?:only[A-Z][A-Za-z0-9_]+|only[A-Za-z_][A-Za-z0-9_]*)\b", decl)
        loops = re.findall(r"\b(?:for|while)\s*\s*\(", body)
        external_calls = re.findall(
            r"\b(?:\w+\.)?(?:call|delegatecall|staticcall|transfer|safeTransfer|safeTransferFrom|approve|transferFrom)\s*\(",
            body,
        )
        state_writes = []
        for storage_var in re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", body):
            if storage_var in {"for", "while", "if", "else", "return", "require", "emit", "revert", "assert"}:
                continue
            if re.search(rf"\b{re.escape(storage_var)}\s*=" , body):
                state_writes.append(storage_var)

        summaries.append(
            FunctionSummary(
                name=name,
                signature=signature,
                visibility=visibility,
                modifiers=sorted(set(modifiers)),
                loops=sorted(set(loops)),
                external_calls=sorted(set(external_calls)),
                state_writes=sorted(set(state_writes)),
            )
        )

    return summaries


def _extract_state_variables(source: str) -> list[str]:
    lines = []
    for candidate in re.finditer(r"(?m)^\s*(?:\w+\s+)+[A-Za-z_][A-Za-z0-9_]*\s*(?:\[[^\]]*\])?\s*;", source):
        text = candidate.group(0).strip().rstrip(";")
        if "function" in text or "modifier" in text or "constructor" in text:
            continue
        lines.append(text)
    return lines


def extract_contract_profile(file_path: str | Path) -> ContractProfile:
    path = Path(file_path)
    source = path.read_text(encoding="utf-8")
    contract_name = re.search(r"contract\s+([A-Za-z_][A-Za-z0-9_]*)", source)
    if contract_name is None:
        raise ValueError(f"Unable to find contract definition in {path}")

    state_variables = _extract_state_variables(source)
    functions = _extract_function_summaries(source)

    modifiers = re.findall(r"modifier\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(.*?\)\s*\{", source, re.DOTALL)
    external_calls = sorted(
        {
            call
            for function in functions
            for call in function.external_calls
        }
    )
    loops = sorted({loop for function in functions for loop in function.loops})
    mappings = re.findall(r"mapping\s*\((.*?)\)", source, re.DOTALL)
    arrays = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\s*\[[^\]]*\]\s*;", source)
    access_control_checks = []
    for pattern in (
        r"require\s*\(\s*msg\.sender\s*==",
        r"require\s*\(\s*msg\.sender\s*!=",
        r"require\s*\(\s*owner\s*==",
        r"require\s*\(\s*only[A-Z]",
        r"if\s*\(\s*msg\.sender\s*!=",
    ):
        if re.search(pattern, source, re.DOTALL):
            access_control_checks.append(pattern)

    eth_transfers = []
    if re.search(r"\.transfer\s*\(|\.send\s*\(|call\s*\{\s*value", source, re.DOTALL):
        eth_transfers.append("value-transfer path found")

    token_transfers = []
    for marker in ("transfer(", "transferFrom(", "safeTransfer(", "safeTransferFrom(", "approve("):
        if marker in source:
            token_transfers.append(marker)

    gas_sensitive_operations = []
    if loops:
        gas_sensitive_operations.append("loop over dynamic state")
    if mappings:
        gas_sensitive_operations.append("mapping lookup with dynamic state")
    if "keccak256" in source or "abi.encodePacked" in source:
        gas_sensitive_operations.append("hashing or encoding on dynamic data")
    if external_calls:
        gas_sensitive_operations.append("external call with state mutation")

    state_transitions = []
    for function in functions:
        if function.state_writes:
            state_transitions.append(f"{function.name}: {', '.join(function.state_writes)}")

    return ContractProfile(
        contract_name=contract_name.group(1),
        file_path=str(path),
        functions=functions,
        state_variables=state_variables,
        modifiers=modifiers,
        external_calls=external_calls,
        loops=loops,
        mappings=[item.strip() for item in mappings],
        arrays=arrays,
        access_control_checks=access_control_checks,
        eth_transfers=eth_transfers,
        token_transfers=token_transfers,
        gas_sensitive_operations=gas_sensitive_operations,
        state_transitions=state_transitions,
    )
