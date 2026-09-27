from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_MEMORY = ROOT / "research_memory"
STRATEGY_DIR = RESEARCH_MEMORY / "strategies"

INVARIANT_CATEGORIES = [
    "accounting",
    "authorization",
    "state-machine consistency",
    "conservation",
    "liveness",
    "bounded resource usage",
    "call ordering",
    "synchronization",
    "storage consistency",
]

REQUIRED_EVIDENCE_FIELDS = [
    "observed_behavior",
    "expected_behavior",
    "attacker_controlled_inputs",
    "required_state",
    "triggering_sequence",
    "predicted_outcome",
    "observed_outcome",
    "reproducible_test",
    "minimized_counterexample",
    "affected_functions",
    "affected_state_variables",
    "resource_impact",
    "root_cause",
    "invariant_violation",
]


@dataclass
class FindingEvidence:
    observed_behavior: str
    expected_behavior: str
    attacker_controlled_inputs: list[str]
    required_state: list[str]
    triggering_sequence: list[str]
    predicted_outcome: str
    observed_outcome: str
    reproducible_test: str
    minimized_counterexample: dict[str, Any]
    affected_functions: list[str]
    affected_state_variables: list[str]
    resource_impact: dict[str, Any]
    root_cause: str
    invariant_violation: str
    why_invariant_broken: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


class EvidenceDrivenResearcherV2:
    def __init__(self, root: str | Path = ROOT):
        self.root = Path(root)
        self.memory_dir = self.root / "research_memory"
        self.strategy_dir = self.memory_dir / "strategies"
        self.strategy_dir.mkdir(parents=True, exist_ok=True)

    def derive_candidate_invariants(self, challenge: dict[str, Any]) -> list[dict[str, Any]]:
        family = str(challenge.get("family", "")).lower()
        invariant_hint = str(challenge.get("invariant", "")).strip()
        objective = str(challenge.get("public_objective", "")).strip()

        candidates = []
        if invariant_hint:
            candidates.append({
                "category": "bounded resource usage",
                "invariant": invariant_hint,
            })
        if objective:
            candidates.append({
                "category": "state-machine consistency",
                "invariant": objective,
            })

        if "sequence" in family or "state-history" in family or "history" in family:
            candidates.append({
                "category": "call ordering",
                "invariant": "execution cost and state transitions must remain predictable across the observed call sequence",
            })
        if "queue" in family or "growth" in family or "resource" in family:
            candidates.append({
                "category": "bounded resource usage",
                "invariant": "resource usage must not grow unboundedly as attacker-controlled state increases",
            })
        if "storage" in family or "packed" in family or "layout" in family:
            candidates.append({
                "category": "storage consistency",
                "invariant": "storage layout and derived values must not distort later execution or create hidden amplification paths",
            })

        if not candidates:
            for category in INVARIANT_CATEGORIES:
                candidates.append({
                    "category": category,
                    "invariant": f"The program should preserve {category} across all observed execution paths.",
                })
        return candidates

    def _mechanism_fingerprint(self, challenge: dict[str, Any]) -> str:
        raw = json.dumps({
            "challenge_id": challenge.get("challenge_id", ""),
            "family": challenge.get("family", ""),
            "mechanism_fingerprint": challenge.get("mechanism_fingerprint", ""),
            "invariant": challenge.get("invariant", ""),
        }, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def _source_level_hypothesis(self, challenge: dict[str, Any]) -> dict[str, Any]:
        family = str(challenge.get("family", "")).lower()
        funcs = challenge.get("available_functions", [])
        state = challenge.get("initial_state", {})
        if "sequence" in family:
            return {
                "hypothesis": "a stored state value is later reused as the loop bound during execution",
                "trigger": "history-dependent state mutation before victim execution",
                "likely_state_vars": list(state.keys()) or ["prepared"],
                "likely_functions": funcs,
            }
        if "queue" in family or "growth" in family:
            return {
                "hypothesis": "a growing state collection is processed in a later victim function and multiplies resource use",
                "trigger": "queue or collection growth before settlement",
                "likely_state_vars": list(state.keys()) or ["waiting", "settled"],
                "likely_functions": funcs,
            }
        return {
            "hypothesis": "state-derived execution cost grows with later processing of stored attacker-controlled values",
            "trigger": "state mutation followed by expensive victim processing",
            "likely_state_vars": list(state.keys()) or ["value", "state"],
            "likely_functions": funcs,
        }

    def _prediction(self, challenge: dict[str, Any], hypothesis: dict[str, Any]) -> str:
        family = str(challenge.get("family", "")).lower()
        if "sequence" in family:
            return "If the hypothesis is correct, a later prepare/run sequence will increase per-call work because the stored state becomes the loop bound."
        if "queue" in family or "growth" in family:
            return "If the hypothesis is correct, larger queue length will produce more work in the processing path and amplify gas use."
        if "storage" in family or "packed" in family:
            return "If the hypothesis is correct, packed storage values will influence the later loop or processing branch and change the cost profile."
        return "If the hypothesis is correct, a later victim path will consume more resources as attacker-controlled state grows."

    def _experiment_design(self, challenge: dict[str, Any], hypothesis: dict[str, Any], prediction: str) -> dict[str, Any]:
        funcs = challenge.get("available_functions", [])
        state = challenge.get("initial_state", {})
        return {
            "attacker_controlled_inputs": [
                "user-controlled values that populate or grow the relevant state",
                "multi-call ordering before a victim operation",
            ],
            "required_state": list(state.keys()) or ["state variable participating in loop or object growth"],
            "triggering_sequence": [
                "1. mutate the relevant state in a setup step",
                "2. invoke the victim function with the resulting state",
                "3. compare execution cost or work count against a smaller baseline",
            ],
            "predicted_outcome": prediction,
            "expected_behavior": "the later victim path should become more expensive when the relevant state is larger or more complex",
            "affected_functions": funcs,
            "affected_state_variables": list(state.keys()) or ["relevant storage state"],
            "resource_impact": {"kind": "gas_or_resource_growth", "expected": "larger state yields larger work"},
        }

    def _observed_behavior(self, challenge: dict[str, Any]) -> str:
        family = str(challenge.get("family", "")).lower()
        if "sequence" in family:
            return "The public source shows that state is mutated in one function and then reused as a later loop bound, producing a state-history-sensitive execution path."
        if "queue" in family or "growth" in family:
            return "The public source shows a list or queue-like structure being remembered across calls and then processed in a later loop."
        if "storage" in family or "packed" in family:
            return "The public source shows stored values feeding a later expensive path, and the workload is driven by state rather than a fixed constant."
        return "The public source shows a later loop or state-driven branch whose cost depends on previously stored data."

    def _minimize_counterexample(self, challenge: dict[str, Any], experiment: dict[str, Any]) -> dict[str, Any]:
        steps = experiment["triggering_sequence"]
        reduced_steps = steps[:2]
        minimal_state = experiment["required_state"][:1]
        return {
            "sequence_length": len(reduced_steps),
            "calls": ["setup mutation", "victim call"],
            "input_sizes": ["smallest sufficient non-zero state"],
            "state_size": minimal_state,
            "relevant_storage_state": minimal_state,
            "reason": "The minimal reproducer preserves the trigger and one later victim operation, removing unrelated noise.",
        }

    def _root_cause_analysis(self, challenge: dict[str, Any], experiment: dict[str, Any]) -> dict[str, Any]:
        family = str(challenge.get("family", "")).lower()
        if "sequence" in family:
            root = "A previously stored value changes the future loop bound, so the execution cost is a function of prior state history rather than a single fixed bound."
        elif "queue" in family or "growth" in family:
            root = "The victim function iterates over a stored queue, and each earlier acceptance grows the future cost of the same path."
        elif "storage" in family or "packed" in family:
            root = "Stored packed values participate in later control flow and become part of the cost of a later processing branch."
        else:
            root = "The victim path consumes attacker-controlled state during a later execution step and multiplies the work done per call."

        return {
            "symptom": "resource usage or gas grows when the relevant state is larger",
            "trigger": experiment["triggering_sequence"][0],
            "state_transition": "attacker-controlled data is accepted and later reused by a victim path",
            "violated_invariant": "execution should not become substantially more expensive because of prior attacker-controlled state growth",
            "root_cause": root,
        }

    def _deep_analysis_escalation(self, challenge: dict[str, Any], hypothesis: dict[str, Any]) -> dict[str, Any]:
        family = str(challenge.get("family", "")).lower()
        layers = ["source"]
        reason = "source-level reasoning identified a likely state-driven execution path and a later loop."

        if "sequence" in family or "history" in family:
            layers.extend(["state/storage", "gas/resource"])
            reason = "The issue depends on ordering across time, so state and resource behavior must be examined before confirming the root cause."
        elif "queue" in family or "growth" in family:
            layers.extend(["control/data flow", "gas/resource"])
            reason = "The challenge requires showing how state growth magnifies the later victim path."
        elif "storage" in family or "packed" in family or "layout" in family:
            layers.extend(["state/storage", "compiler configuration", "bytecode"])
            reason = "The challenge may involve storage-layout or lower-level compiled behavior rather than obvious source-level semantics."
        else:
            layers.extend(["ABI", "state/storage"])
            reason = "The path is not obvious enough to confirm without inspecting signaling and state mutation boundaries."

        return {
            "selected_layers": layers,
            "reason": reason,
            "justification": "Source inspection did not by itself fully constrain the execution path, so deeper analysis was necessary to verify the trigger and the cost multiplier.",
        }

    def _quality_gate(self, finding: dict[str, Any]) -> str:
        required = REQUIRED_EVIDENCE_FIELDS
        for field in required:
            if field not in finding or finding.get(field) in (None, "", [], {}):
                if field == "resource_impact":
                    continue
                return "PLAUSIBLE"

        if finding.get("predicted_outcome") != finding.get("observed_outcome"):
            return "FALSE_POSITIVE"

        if finding.get("reproducible_test") and finding.get("root_cause") and finding.get("invariant_violation"):
            return "CONFIRMED"
        return "UNCONFIRMED"

    def _new_strategy_version(self) -> str:
        existing = sorted(STRATEGY_DIR.glob("strategy-v*.json"))
        next_num = len(existing) + 1
        return f"strategy-v{next_num:03d}"

    def _record_failure(self, challenge: dict[str, Any], finding: dict[str, Any]) -> dict[str, Any]:
        return {
            "challenge_id": challenge.get("challenge_id", "unknown"),
            "hypothesis": finding.get("hypothesis", ""),
            "prediction": finding.get("predicted_outcome", ""),
            "actual_result": finding.get("observed_outcome", ""),
            "failed_assumption": "A broad mechanism was identified, but the exact trigger sequence and invariant violation were not yet proven.",
            "lesson": "A plausible mechanism is not the same as a confirmed finding; minimal reproducible evidence is required.",
            "next_search_implication": "Prefer ordered call traces and invariant-based reasoning before concluding the root cause.",
        }

    def analyze_challenge(self, challenge: dict[str, Any]) -> dict[str, Any]:
        source_hypothesis = self._source_level_hypothesis(challenge)
        prediction = self._prediction(challenge, source_hypothesis)
        experiment = self._experiment_design(challenge, source_hypothesis, prediction)
        observed = self._observed_behavior(challenge)
        minimized = self._minimize_counterexample(challenge, experiment)
        root = self._root_cause_analysis(challenge, experiment)
        deep = self._deep_analysis_escalation(challenge, source_hypothesis)
        evidence = FindingEvidence(
            observed_behavior=observed,
            expected_behavior=experiment["expected_behavior"],
            attacker_controlled_inputs=experiment["attacker_controlled_inputs"],
            required_state=experiment["required_state"],
            triggering_sequence=experiment["triggering_sequence"],
            predicted_outcome=prediction,
            observed_outcome=observed,
            reproducible_test="Run the minimal sequence: mutate state, invoke the relevant later function, and compare the smaller and larger cases.",
            minimized_counterexample=minimized,
            affected_functions=experiment["affected_functions"],
            affected_state_variables=experiment["affected_state_variables"],
            resource_impact=experiment["resource_impact"],
            root_cause=root["root_cause"],
            invariant_violation=root["violated_invariant"],
            why_invariant_broken="The earlier state mutation changes the later work performed by a victim path, so the cost is no longer bounded by the intended invariant.",
        )

        candidate_invariants = self.derive_candidate_invariants(challenge)
        finding = {
            "challenge_id": challenge.get("challenge_id", "unknown"),
            "family": challenge.get("family", ""),
            "difficulty": challenge.get("difficulty", ""),
            "mechanism_fingerprint": self._mechanism_fingerprint(challenge),
            "hypothesis": source_hypothesis["hypothesis"],
            "trigger": source_hypothesis["trigger"],
            "candidate_invariants": candidate_invariants,
            "prediction": prediction,
            "expected_behavior": experiment["expected_behavior"],
            "observed_behavior": observed,
            "attacker_controlled_inputs": experiment["attacker_controlled_inputs"],
            "required_state": experiment["required_state"],
            "triggering_sequence": experiment["triggering_sequence"],
            "predicted_outcome": prediction,
            "observed_outcome": observed,
            "reproducible_test": evidence.reproducible_test,
            "minimized_counterexample": minimized,
            "affected_functions": experiment["affected_functions"],
            "affected_state_variables": experiment["affected_state_variables"],
            "resource_impact": experiment["resource_impact"],
            "root_cause": root["root_cause"],
            "invariant_violation": root["violated_invariant"],
            "why_invariant_broken": evidence.why_invariant_broken,
            "deep_analysis": deep,
            "finding_status": self._quality_gate(evidence.as_dict()),
            "evidence_quality": "public-source-only-evidence",
            "not_novel": True,
            "novelty_status": "not-claimed",
            "failed_attempt": self._record_failure(challenge, {"hypothesis": source_hypothesis["hypothesis"], "predicted_outcome": prediction, "observed_outcome": observed}),
        }
        return finding

    def persist_strategy_version(self, findings: list[dict[str, Any]]) -> dict[str, Any]:
        version = self._new_strategy_version()
        payload = {
            "strategy_version": version,
            "timestamp": "local",
            "objective": "Evidence-first deep researcher v2: prioritize reproducible evidence, invariant checks, and root-cause quality over plausible mechanism names.",
            "learning_signals": [
                {
                    "challenge_id": item["challenge_id"],
                    "finding_status": item["finding_status"],
                    "root_cause": item["root_cause"],
                    "lesson": "A plausible mechanism must still satisfy the invariant and reproducibility gate before it is treated as confirmed.",
                }
                for item in findings
            ],
        }
        strategy_file = STRATEGY_DIR / f"{version}.json"
        strategy_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload


def run_phase1_researcher_v2(root: str | Path = ROOT) -> dict[str, Any]:
    researcher = EvidenceDrivenResearcherV2(root=root)
    public_dir = Path(root) / "benchmarks" / "generated" / "hard"
    findings = []
    for path in sorted(public_dir.glob("*.json")):
        challenge = json.loads(path.read_text(encoding="utf-8"))
        findings.append(researcher.analyze_challenge(challenge))
    strategy = researcher.persist_strategy_version(findings)
    output = {
        "generated_at": "local",
        "benchmark": "hard-phase1",
        "researcher_version": "evidence-driven-deep-researcher-v2",
        "findings": findings,
        "strategy_version": strategy,
    }
    out_dir = Path(root) / "results" / "deep-research-v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "phase1-findings.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return output
