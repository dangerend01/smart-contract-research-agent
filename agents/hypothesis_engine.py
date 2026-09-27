from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from .contract_understander import ContractProfile
from .hypothesis_schema import HypothesisRecord, HYPOTHESIS_CATEGORIES, validate_hypothesis_schema


ROOT = Path(__file__).resolve().parents[1]
HYPOTHESIS_DIR = ROOT / "hypotheses"


def _normalize_list(values: Iterable[str] | str | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        return [values]
    return [str(value) for value in values if str(value).strip()]


def _tokenize(value: str) -> set[str]:
    return {
        token
        for token in value.lower().replace("-", " ").replace("_", " ").split()
        if len(token) > 2
    }


def _similarity(left: str, right: str) -> float:
    left_tokens = _tokenize(left)
    right_tokens = _tokenize(right)
    if not left_tokens and not right_tokens:
        return 1.0
    if not left_tokens or not right_tokens:
        return 0.0
    union = left_tokens | right_tokens
    intersection = left_tokens & right_tokens
    return len(intersection) / len(union)


def _next_hypothesis_id(existing_records: list[dict[str, Any]]) -> str:
    max_num = 0
    for record in existing_records:
        candidate = str(record.get("id", "")).strip()
        if candidate.startswith("H-"):
            try:
                num = int(candidate.split("-")[-1])
                max_num = max(max_num, num)
            except ValueError:
                continue
    return f"H-{max_num + 1:03d}"


def _score_priority(hypothesis: HypothesisRecord) -> int:
    score = 0
    if "state" in " ".join(hypothesis.attacker_controlled_inputs).lower():
        score += 18
    if "gas" in hypothesis.title.lower() or "amplif" in hypothesis.title.lower():
        score += 22
    if "loop" in hypothesis.mechanism.lower() or "iteration" in hypothesis.mechanism.lower():
        score += 18
    if len(hypothesis.affected_functions) > 1:
        score += 10
    if hypothesis.category in {"attacker-controlled state growth", "gas amplification", "unbounded iteration"}:
        score += 20
    if hypothesis.category in {"storage growth", "resource exhaustion", "economic/resource griefing"}:
        score += 8
    score += min(10, len(hypothesis.attack_sequence))
    return min(score, 100)


def _default_experiment_plan(title: str, functions: list[str], category: str) -> dict[str, Any]:
    return {
        "setup": "Deploy the local contract and initialize attacker-controlled state with a small baseline.",
        "attacker_action": "Grow the attacker-controlled data set or trigger repeated input processing before a victim call.",
        "victim_action": f"Call the relevant mutating path in {', '.join(functions) if functions else 'the target function'}.",
        "state_changes": "Observe whether attacker-controlled growth causes a larger resource requirement in the victim path.",
        "measurement": "Record gas usage and execution cost as the attacker-controlled input size increases.",
        "expected_observation": f"{title} should produce progressively higher cost as attacker-controlled state expands.",
        "falsification_condition": "If the victim operation remains flat or bounded despite growth in the attacker-controlled state, the hypothesis is weakened or falsified.",
        "category": category,
    }


def _build_hypotheses_for_profile(profile: ContractProfile | dict[str, Any]) -> list[HypothesisRecord]:
    if isinstance(profile, dict):
        loops = _normalize_list(profile.get("loops", []))
        arrays = _normalize_list(profile.get("arrays", []))
        mappings = _normalize_list(profile.get("mappings", []))
        external_calls = _normalize_list(profile.get("external_calls", []))
        functions = _normalize_list(profile.get("functions", []))
        state_variables = _normalize_list(profile.get("state_variables", []))
        access = _normalize_list(profile.get("access_control_checks", []))
        gas_sensitive = _normalize_list(profile.get("gas_sensitive_operations", []))
        state_transitions = _normalize_list(profile.get("state_transitions", []))
    else:
        loops = [loop for loop in profile.loops]
        arrays = [item for item in profile.arrays]
        mappings = [item for item in profile.mappings]
        external_calls = [item for item in profile.external_calls]
        functions = [func.name for func in profile.functions]
        state_variables = [item for item in profile.state_variables]
        access = [item for item in profile.access_control_checks]
        gas_sensitive = [item for item in profile.gas_sensitive_operations]
        state_transitions = [item for item in profile.state_transitions]

    hypotheses: list[HypothesisRecord] = []

    if loops or arrays or mappings:
        hypotheses.append(
            HypothesisRecord(
                id="",
                title="Attacker-controlled participant set amplifies processing cost",
                mechanism="A dynamic list or mapping is populated by an attacker and later processed in a loop, causing the victim operation to become more expensive as the attacker-controlled set grows.",
                category="attacker-controlled state growth",
                affected_functions=functions,
                attacker_controlled_inputs=["participant list length", "dynamic storage entries", "caller-controlled list growth"],
                attacker_capabilities=["append attacker-controlled entries", "increase collection size before victim call"],
                required_state=["participants array or mapping-backed state must contain attacker-created entries"],
                target_invariant="One user should not be able to make another user's operation excessively expensive.",
                attack_sequence=[
                    "populate a dynamic array or mapping with attacker-controlled entries",
                    "invoke the processing function",
                    "observe cost increase as collection size grows",
                ],
                predicted_failure="The victim operation's gas use rises with the size of the attack-controlled state and eventually becomes impractical.",
                expected_observation="gas usage increases materially when the attacker-controlled collection is larger.",
                experiment_plan=_default_experiment_plan(
                    "Attacker-controlled participant set amplifies processing cost",
                    functions,
                    "attacker-controlled state growth",
                ),
                priority=0,
                novelty_status="new",
                confidence=0.72,
                status="unverified",
            )
        )

    if loops:
        hypotheses.append(
            HypothesisRecord(
                id="",
                title="Unbounded iteration across dynamic state raises gas requirements",
                mechanism="Repeated iteration over storage-backed user-controlled data introduces a direct relationship between attacker-controlled input size and per-call resource use.",
                category="unbounded iteration",
                affected_functions=functions,
                attacker_controlled_inputs=arrays + mappings,
                attacker_capabilities=["increase loop length", "grow attacker-controlled collection"],
                required_state=["storage-backed dynamic collection with looped processing"],
                target_invariant="Gas usage should not grow unexpectedly with attacker-controlled state.",
                attack_sequence=[
                    "grow the looped collection",
                    "trigger the function containing the iteration",
                    "measure induced gas usage",
                ],
                predicted_failure="The operation becomes more expensive as loop length increases, producing gas griefing or blocking a victim path.",
                expected_observation="gas cost scales monotonically with collection size.",
                experiment_plan=_default_experiment_plan(
                    "Unbounded iteration across dynamic state raises gas requirements",
                    functions,
                    "unbounded iteration",
                ),
                priority=0,
                novelty_status="new",
                confidence=0.75,
                status="unverified",
            )
        )

    if external_calls and loops:
        hypotheses.append(
            HypothesisRecord(
                id="",
                title="Repeated external calls inside a loop magnify denial cost",
                mechanism="Each loop iteration invokes an external call or token transfer path, multiplying per-item work and amplifying resource cost.",
                category="external-call amplification",
                affected_functions=functions,
                attacker_controlled_inputs=["dynamic collection length", "external call count"],
                attacker_capabilities=["add entries to make iteration larger", "trigger repeated call behavior"],
                required_state=["looped collection plus external call path"],
                target_invariant="A single user should not force disproportionate work on other users through repeated external operations.",
                attack_sequence=[
                    "grow the collection",
                    "invoke the function with repeated external interactions",
                    "measure call and gas amplification",
                ],
                predicted_failure="A victim action triggers many external operations and becomes impractical or expensive to execute.",
                expected_observation="gas rises sharply as the iteration count increases.",
                experiment_plan=_default_experiment_plan(
                    "Repeated external calls inside a loop magnify denial cost",
                    functions,
                    "external-call amplification",
                ),
                priority=0,
                novelty_status="new",
                confidence=0.7,
                status="unverified",
            )
        )

    if state_variables and ("loop" in " ".join(gas_sensitive).lower() or "mapping" in " ".join(gas_sensitive).lower()):
        hypotheses.append(
            HypothesisRecord(
                id="",
                title="Storage growth creates a resource-exhaustion path",
                mechanism="The contract stores attacker-controlled data and later reprocesses it, creating a path where storage growth increases per-user cost without a bounded limit.",
                category="storage growth",
                affected_functions=functions,
                attacker_controlled_inputs=["state growth", "storage entry count"],
                attacker_capabilities=["push more state", "repeatedly grow a collection before victim action"],
                required_state=["contract state stores dynamic entries"],
                target_invariant="Critical state transitions should remain reachable and not become prohibitively expensive.",
                attack_sequence=[
                    "fill storage with attacker-controlled entries",
                    "invoke state-consuming function",
                    "measure cost and accessibility",
                ],
                predicted_failure="The contract eventually becomes unusable due to rising persistent storage and processing cost.",
                expected_observation="resource use rises as storage grows, even without changing contract logic.",
                experiment_plan=_default_experiment_plan(
                    "Storage growth creates a resource-exhaustion path",
                    functions,
                    "storage growth",
                ),
                priority=0,
                novelty_status="new",
                confidence=0.68,
                status="unverified",
            )
        )

    if not hypotheses:
        hypotheses.append(
            HypothesisRecord(
                id="",
                title="No obvious unbounded-work path detected from local contract heuristics",
                mechanism="The static analysis did not reveal an obvious loop or state-growth amplifier, but a deeper flow analysis may still reveal a resource path.",
                category="resource exhaustion",
                affected_functions=functions,
                attacker_controlled_inputs=["unidentified external quantities"],
                attacker_capabilities=["trigger an overlooked state mutation path"],
                required_state=["additional contract-flow review required"],
                target_invariant="The contract should remain callable and bounded even under attacker influence.",
                attack_sequence=["review deeper control flow", "test edge conditions", "verify gas scaling"],
                predicted_failure="A hidden unbounded path may still exist despite a shallow local analysis.",
                expected_observation="a deeper analysis could reveal a cost amplifier not visible in the first pass.",
                experiment_plan=_default_experiment_plan(
                    "No obvious unbounded-work path detected from local contract heuristics",
                    functions,
                    "resource exhaustion",
                ),
                priority=0,
                novelty_status="requires_review",
                confidence=0.25,
                status="unverified",
            )
        )

    for hypothesis in hypotheses:
        hypothesis.priority = _score_priority(hypothesis)
        hypothesis.confidence = max(0.1, min(0.99, hypothesis.confidence))
    return hypotheses


def deduplicate_hypotheses(new_hypotheses: list[HypothesisRecord], existing_records: list[dict[str, Any]]) -> list[HypothesisRecord]:
    deduped: list[HypothesisRecord] = []
    for hypothesis in new_hypotheses:
        status = "new"
        for record in existing_records:
            title = str(record.get("title", ""))
            mechanism = str(record.get("mechanism", ""))
            similarity = max(_similarity(hypothesis.title, title), _similarity(hypothesis.mechanism, mechanism))
            if similarity >= 0.80:
                status = "duplicate"
                hypothesis.novelty_status = "duplicate"
                break
            if similarity >= 0.50:
                status = "similar"
                hypothesis.novelty_status = "similar"
                break
        if status == "new":
            hypothesis.novelty_status = "new"
        deduped.append(hypothesis)
    return deduped


def persist_hypotheses(hypotheses: list[HypothesisRecord], path: str | Path | None = None) -> list[dict[str, Any]]:
    target = Path(path) if path is not None else HYPOTHESIS_DIR
    target.mkdir(parents=True, exist_ok=True)

    existing = []
    index_file = target / "index.json"
    if index_file.exists():
        try:
            existing = json.loads(index_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []

    combined = list(existing)
    payload: list[dict[str, Any]] = []
    for hypothesis in hypotheses:
        if not hypothesis.id:
            hypothesis.id = _next_hypothesis_id(combined)
        record = hypothesis.to_dict()
        payload.append(record)
        combined.append(record)
        (target / f"{hypothesis.id}.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    index_file.write_text(json.dumps(combined, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def generate_hypotheses(profile: ContractProfile | dict[str, Any], *, existing_records: list[dict[str, Any]] | None = None) -> list[HypothesisRecord]:
    if existing_records is None:
        existing_records = []
    if HYPOTHESIS_DIR.joinpath("index.json").exists():
        try:
            existing_records = json.loads(HYPOTHESIS_DIR.joinpath("index.json").read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing_records = []

    candidates = _build_hypotheses_for_profile(profile)
    deduped = deduplicate_hypotheses(candidates, existing_records)
    return deduped


def run_local_hypothesis_engine(contract_path: str | Path) -> list[dict[str, Any]]:
    from .contract_understander import extract_contract_profile

    profile = extract_contract_profile(contract_path)
    hypotheses = generate_hypotheses(profile, existing_records=[])
    records = persist_hypotheses(hypotheses, HYPOTHESIS_DIR)
    return records
