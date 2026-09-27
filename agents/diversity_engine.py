from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_MEMORY = ROOT / "research_memory"
FRONTIER_PATH = RESEARCH_MEMORY / "frontier.json"
GRAPH_PATH = RESEARCH_MEMORY / "mechanism-graph.json"


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def _similarity(left: str, right: str) -> float:
    left_tokens = {token for token in left.lower().replace("-", " ").replace("_", " ").split() if len(token) > 2}
    right_tokens = {token for token in right.lower().replace("-", " ").replace("_", " ").split() if len(token) > 2}
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    union = left_tokens | right_tokens
    intersection = left_tokens & right_tokens
    return len(intersection) / len(union)


def build_mechanism_graph(
    *,
    contract_name: str,
    functions: Iterable[str] | None = None,
    state_variables: Iterable[str] | None = None,
    inputs: Iterable[str] | None = None,
    invariants: Iterable[str] | None = None,
    attack_surfaces: Iterable[str] | None = None,
    hypotheses: Iterable[str] | None = None,
    experiments: Iterable[str] | None = None,
    observed_mechanisms: Iterable[str] | None = None,
) -> dict[str, Any]:
    functions_list = _as_list(functions)
    state_list = _as_list(state_variables)
    input_list = _as_list(inputs)
    invariant_list = _as_list(invariants)
    attack_list = _as_list(attack_surfaces)
    hypothesis_list = _as_list(hypotheses)
    experiment_list = _as_list(experiments)
    observed_list = _as_list(observed_mechanisms)

    edges = {contract_name: {}}
    for function_name in functions_list:
        edges[contract_name][function_name] = {
            "state_variables": [state for state in state_list],
            "inputs": input_list,
            "invariants": invariant_list,
            "attack_surfaces": attack_list,
        }

    graph = {
        "contracts": {contract_name: {"functions": functions_list}},
        "functions": {function_name: {"contract": contract_name} for function_name in functions_list},
        "state_variables": {state_name: {"contract": contract_name} for state_name in state_list},
        "inputs": {item: {"contract": contract_name} for item in input_list},
        "invariants": {item: {"contract": contract_name} for item in invariant_list},
        "attack_surfaces": {item: {"contract": contract_name} for item in attack_list},
        "hypotheses": {item: {"contract": contract_name} for item in hypothesis_list},
        "experiments": {item: {"contract": contract_name} for item in experiment_list},
        "observed_mechanisms": {item: {"contract": contract_name} for item in observed_list},
        "edges": edges,
    }
    return graph


def coverage_report(
    *,
    functions: Iterable[str] | None = None,
    state_variables: Iterable[str] | None = None,
    attacker_inputs: Iterable[str] | None = None,
    loops: Iterable[str] | None = None,
    external_calls: Iterable[str] | None = None,
    revert_paths: Iterable[str] | None = None,
    state_transitions: Iterable[str] | None = None,
    tested: dict[str, Any] | None = None,
    partially_tested: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tested = tested or {}
    partially_tested = partially_tested or {}
    categories = {
        "functions": _as_list(functions),
        "state_variables": _as_list(state_variables),
        "attacker_inputs": _as_list(attacker_inputs),
        "loops": _as_list(loops),
        "external_calls": _as_list(external_calls),
        "revert_paths": _as_list(revert_paths),
        "state_transitions": _as_list(state_transitions),
    }
    report: dict[str, Any] = {}
    for category, values in categories.items():
        mapping: dict[str, str] = {}
        tested_set = set(_as_list(tested.get(category, [])))
        partially_set = set(_as_list(partially_tested.get(category, [])))
        for value in values:
            if value in tested_set:
                mapping[value] = "TESTED"
            elif value in partially_set:
                mapping[value] = "PARTIALLY_TESTED"
            else:
                mapping[value] = "UNTESTED"
        report[category] = mapping
    return report


def _build_fingerprint(hypothesis: dict[str, Any]) -> dict[str, Any]:
    return {
        "affected_functions": sorted(_as_list(hypothesis.get("affected_functions", []))),
        "state_dependencies": sorted(_as_list(hypothesis.get("state_dependencies", hypothesis.get("required_state", [])))),
        "invariant": str(hypothesis.get("invariant", hypothesis.get("target_invariant", ""))).strip().lower(),
        "attack_sequence": [str(item).strip().lower() for item in _as_list(hypothesis.get("attack_sequence", []))],
        "resource_affected": str(hypothesis.get("resource_affected", hypothesis.get("expected_observation", ""))).strip().lower(),
    }


def detect_duplicate_hypothesis(existing: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    existing_fp = _build_fingerprint(existing)
    candidate_fp = _build_fingerprint(candidate)
    existing_functions = set(existing_fp["affected_functions"])
    candidate_functions = set(candidate_fp["affected_functions"])
    union_functions = existing_functions | candidate_functions
    function_overlap = len(existing_functions & candidate_functions) / max(1, len(union_functions)) if union_functions else 1.0

    match_score = 0.0
    match_score += 0.35 * function_overlap
    match_score += 0.25 * (1.0 if existing_fp["invariant"] and existing_fp["invariant"] == candidate_fp["invariant"] else 0.0)
    match_score += 0.2 * (1.0 if existing_fp["resource_affected"] and existing_fp["resource_affected"] == candidate_fp["resource_affected"] else 0.0)

    if existing_fp["attack_sequence"] and candidate_fp["attack_sequence"]:
        seq_score = max(
            _similarity(" ".join(existing_fp["attack_sequence"]), " ".join(candidate_fp["attack_sequence"])),
            _similarity(" ".join(candidate_fp["attack_sequence"]), " ".join(existing_fp["attack_sequence"])),
        )
        match_score += 0.2 * seq_score

    if match_score >= 0.75:
        return {"status": "duplicate", "match_score": round(match_score, 4), "reason": "Similar mechanism fingerprint and attack sequence."}
    if match_score >= 0.45:
        return {"status": "similar", "match_score": round(match_score, 4), "reason": "Related but not equivalent mechanism fingerprint."}
    return {"status": "distinct", "match_score": round(match_score, 4), "reason": "The mechanism fingerprint differs materially."}


def generate_function_combinations(functions: Iterable[str], max_depth: int = 2) -> list[list[str]]:
    fn_list = _as_list(functions)
    combos: list[list[str]] = []
    for depth in range(2, min(max_depth, len(fn_list)) + 1):
        for combo in __import__("itertools").combinations(fn_list, depth):
            combos.append(list(combo))
    # ensure some direct pairings remain even for tiny lists
    if len(fn_list) >= 2:
        combos.append([fn_list[0], fn_list[1]])
    return deduplicate_list_of_lists(combos)


def deduplicate_list_of_lists(items: Iterable[list[str]]) -> list[list[str]]:
    seen: set[tuple[str, ...]] = set()
    result: list[list[str]] = []
    for item in items:
        key = tuple(item)
        if key in seen:
            continue
        seen.add(key)
        result.append(list(item))
    return result


def generate_state_histories() -> list[dict[str, Any]]:
    return [
        {"id": "history-001", "description": "fresh state -> attacker action", "kind": "fresh-state"},
        {"id": "history-002", "description": "attacker action repeated N times -> victim action", "kind": "repeated-state"},
        {"id": "history-003", "description": "attacker action -> victim action -> attacker action", "kind": "reordering"},
        {"id": "history-004", "description": "multiple users -> different ordering", "kind": "multi-user"},
        {"id": "history-005", "description": "failure -> retry -> state transition", "kind": "failure-retry"},
    ]


def generate_resource_dimensions() -> dict[str, list[int | str]]:
    return {
        "input_size": [4, 16, 32, 64, 128],
        "state_size": [8, 32, 64, 128, 256],
        "repetitions": [1, 3, 5, 10],
        "number_of_users": [1, 2, 3],
        "call_depth": [1, 2, 3],
        "sequence_length": [1, 2, 4, 8],
    }


def mechanism_fingerprint(
    *,
    affected_functions: Iterable[str] | None = None,
    state_dependencies: Iterable[str] | None = None,
    invariant: str | None = None,
    attack_sequence: Iterable[str] | None = None,
    resource_affected: str | None = None,
) -> dict[str, Any]:
    return {
        "affected_functions": sorted(_as_list(affected_functions)),
        "state_dependencies": sorted(_as_list(state_dependencies)),
        "invariant": str(invariant or "").strip().lower(),
        "attack_sequence": [str(item).strip().lower() for item in _as_list(attack_sequence)],
        "resource_affected": str(resource_affected or "").strip().lower(),
    }


def classify_mechanism_fingerprint(fingerprint: dict[str, Any], history: Iterable[dict[str, Any]] | None = None) -> str:
    history = list(history or [])
    if not fingerprint.get("affected_functions") and not fingerprint.get("state_dependencies"):
        return "UNKNOWN"
    if fingerprint.get("invariant") and "gas" in fingerprint["invariant"]:
        return "KNOWN"
    if history:
        if any("failure" in str(item.get("description", "")).lower() for item in history):
            return "VARIANT"
    if fingerprint.get("attack_sequence") and len(fingerprint["attack_sequence"]) > 2:
        return "POTENTIALLY_DISTINCT"
    return "KNOWN"


def generate_frontier(coverage: dict[str, Any], context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    frontier: list[dict[str, Any]] = []
    for category, mapping in coverage.items():
        for target, state in mapping.items():
            if state != "UNTESTED":
                continue
            frontier.append({
                "target": f"{category}:{target}",
                "category": category,
                "priority": 0.8 if category in {"state_variables", "functions", "revert_paths"} else 0.6,
                "reason": f"{category} is not yet covered by the local evidence base.",
                "context": context or {},
            })
    return sorted(frontier, key=lambda item: item["priority"], reverse=True)


def select_exploration_targets(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = []
    for target in targets:
        score = float(target.get("priority", 0.0))
        label = str(target.get("target", "")).lower()
        if label.startswith("duplicate:"):
            score -= 0.35
        elif label.startswith("state:"):
            score += 0.1
        scored.append({**target, "adjusted_priority": score})
    return sorted(scored, key=lambda item: item["adjusted_priority"], reverse=True)


class ResearchDiversityEngine:
    def __init__(self, root: str | Path = ROOT):
        self.root = Path(root)
        self.memory_dir = self.root / "research_memory"
        self.memory_dir.mkdir(parents=True, exist_ok=True)

    def save_graph(self, graph: dict[str, Any]) -> dict[str, Any]:
        GRAPH_PATH.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return graph

    def save_frontier(self, frontier: list[dict[str, Any]]) -> list[dict[str, Any]]:
        FRONTIER_PATH.write_text(json.dumps(frontier, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return frontier

    def compute_frontier_from_coverage(self, coverage: dict[str, Any], context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        frontier = generate_frontier(coverage, context)
        self.save_frontier(frontier)
        return frontier

    def update_graph(self, **kwargs: Any) -> dict[str, Any]:
        graph = build_mechanism_graph(**kwargs)
        self.save_graph(graph)
        return graph

    def choose_next_targets(self, targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
        selected = select_exploration_targets(targets)
        return selected
