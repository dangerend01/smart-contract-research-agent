from __future__ import annotations

import re
from typing import Any


class DeepAnalysisEngine:
    def __init__(self) -> None:
        self.layer_policy = "escalate_to_lower_layers_only_when_needed"

    def _extract_functions(self, source: str) -> list[str]:
        return re.findall(r"function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source)

    def _extract_state_variables(self, source: str) -> list[str]:
        matches = re.findall(r"(?:^|\s)(?:mapping\s*\([^\)]*\)|[A-Za-z_][A-Za-z0-9_]*\s*(?:\[[^\]]*\])?)\s+[A-Za-z_][A-Za-z0-9_]*\s*;", source, re.MULTILINE)
        values: list[str] = []
        for match in matches:
            pieces = match.strip().split()
            if len(pieces) >= 2:
                values.append(pieces[-1].rstrip(";"))
        return values

    def analyze_source(self, source: str, contract_name: str) -> dict[str, Any]:
        functions = self._extract_functions(source)
        state_vars = self._extract_state_variables(source)
        recommended_layers = [
            "Layer 1: Solidity source",
            "Layer 2: ABI/function/state analysis",
            "Layer 3: control-flow and data-flow analysis",
            "Layer 4: Yul/IR where available",
            "Layer 5: EVM bytecode",
            "Layer 6: EVM opcode/control-flow analysis",
            "Layer 7: storage and memory behavior",
            "Layer 8: gas/resource measurements",
            "Layer 9: compiler/build metadata",
        ]
        return {
            "contract_name": contract_name,
            "solidity_source": source,
            "function_names": functions,
            "state_variables": state_vars,
            "abi_summary": [{"name": name, "signature": f"{name}(...)"} for name in functions],
            "recommended_layers": recommended_layers,
            "layer_policy": self.layer_policy,
            "analysis_notes": [
                "Begin with source-level reasoning and only escalate when evidence indicates the higher-level view is insufficient.",
                "Look for cross-function dependencies, storage growth, and state-history-sensitive paths.",
            ],
            "next_most_likely_exploration": [
                "function sequencing",
                "state-history mutation",
                "resource amplification",
            ],
        }
