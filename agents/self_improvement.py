from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_MEMORY = ROOT / "research_memory"
STRATEGY_DIR = RESEARCH_MEMORY / "strategies"

FAILURE_TAXONOMY = {
    "WRONG_PRECONDITION": "The observed mechanism did not satisfy the required preconditions for the target invariant.",
    "UNREACHABLE_STATE": "The intended state path was not reachable under the local experimentation setup.",
    "INSUFFICIENT_AMPLIFICATION": "The observed effect was too small or too bounded to support the hypothesis.",
    "NO_VICTIM_IMPACT": "The attack increased cost but did not materially affect victim execution or resource availability.",
    "GAS_NOT_SCALING": "Gas usage did not scale with the suspected attacker-controlled state growth.",
    "ATTACK_SEQUENCE_INVALID": "The sequence of calls or ordering assumptions was insufficient or invalid.",
    "INVARIANT_NOT_APPLICABLE": "The targeted invariant was not meaningful for the local contract behavior under test.",
    "IMPLEMENTATION_ERROR": "The experiment harness or local reproduction had an implementation or setup problem.",
    "INSUFFICIENT_EVIDENCE": "The run lacked enough measurement coverage to support a strong conclusion.",
    "OTHER": "The failure mode did not fit the known taxonomy and should be reviewed manually.",
}

RESEARCH_STRATEGIES = [
    "state-growth strategy",
    "sequence-mutation strategy",
    "boundary-value strategy",
    "gas-amplification strategy",
    "failure-path strategy",
    "external-call strategy",
    "invariant-breaking strategy",
    "cross-function interaction strategy",
    "state-history strategy",
]


def _read_json(path: str | Path) -> Any:
    target = Path(path)
    if not target.exists():
        return []
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []


def _list_json_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.glob("*.json"))


def _normalize_experiment_result(result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    return {
        "classification": str(result.get("classification", "inconclusive")).lower(),
        "hypothesis_id": str(result.get("hypothesis_id", "H-000")),
        "experiment_id": str(result.get("experiment_id", "EXP-000")),
        "measurements": result.get("measurements", {}),
        "feedback": result.get("feedback", {}),
        "evidence": result.get("evidence", {}),
    }


class SelfImprovementEngine:
    def __init__(self, root: str | Path = ROOT):
        self.root = Path(root)
        self.memory_dir = self.root / "research_memory"
        self.strategy_dir = self.memory_dir / "strategies"
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.strategy_dir.mkdir(parents=True, exist_ok=True)

    def load_previous_state(self) -> dict[str, Any]:
        cycle_files = sorted((self.memory_dir).glob("research-cycle-*.json"))
        strategy_files = sorted(self.strategy_dir.glob("strategy-v*.json"))
        previous_cycles = []
        for cycle_file in cycle_files:
            payload = _read_json(cycle_file)
            if isinstance(payload, dict):
                previous_cycles.append(payload)
        strategy_versions = []
        for strategy_file in strategy_files:
            payload = _read_json(strategy_file)
            if isinstance(payload, dict):
                strategy_versions.append(payload)
        return {"cycles": previous_cycles, "strategy_versions": strategy_versions}

    def _next_strategy_version(self) -> str:
        existing = sorted(self.strategy_dir.glob("strategy-v*.json"))
        max_num = 0
        for path in existing:
            match = str(path.stem).split("strategy-v")[-1]
            if match.isdigit():
                max_num = max(max_num, int(match))
        return f"strategy-v{max_num + 1:03d}"

    def _strategy_score(self, strategy_name: str, previous_state: dict[str, Any] | None = None) -> float:
        results = previous_state or self.load_previous_state()
        current = 0.0
        cycles = results.get("cycles", [])
        for cycle in cycles:
            for strategy_batch in cycle.get("strategies_used", []):
                if str(strategy_batch.get("name")) == strategy_name:
                    current += float(strategy_batch.get("score", 0.0))
        return current

    def choose_strategy(self, exploration_ratio: float = 0.35, previous_state: dict[str, Any] | None = None) -> str:
        history = previous_state or self.load_previous_state()
        scores = {}
        for strategy in RESEARCH_STRATEGIES:
            scores[strategy] = self._strategy_score(strategy, history)
        if not scores or all(value == 0 for value in scores.values()):
            return "state-growth strategy"
        sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if sorted_scores[0][1] > 0:
            return sorted_scores[0][0]
        base = sorted_scores[0][0]
        exploration = sorted_scores[-1][0]
        if exploration_ratio > 0.5:
            return exploration
        return base

    def learn_success(self, hypothesis: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        normalized = _normalize_experiment_result(result)
        success_pattern = {
            "hypothesis_id": str(hypothesis.get("id", normalized.get("hypothesis_id", "H-000"))),
            "title": str(hypothesis.get("title", "local state-growth hypothesis")),
            "mechanism": str(hypothesis.get("mechanism", "")),
            "contract_characteristics": [
                "dynamic storage",
                "loop over attacker-controlled entries",
                "state that grows with user interactions",
            ],
            "function_sequence": [
                "populate attacker-controlled entries",
                "trigger victim function",
                "measure gas growth",
            ],
            "important_preconditions": [
                "attacker-controlled storage must be reachable before victim call",
                "victim must iterate over attacker-controlled state",
                "cost must grow with state size",
            ],
            "useful_input_patterns": [
                "large but bounded input set",
                "repeated state growth before victim action",
                "boundary values near the linear threshold",
            ],
            "follow_up_hypotheses": [
                {
                    "title": "state growth -> nested iteration",
                    "mechanism": "Nested iteration amplifies the observed success pattern by combining storage growth and additional loop nesting.",
                    "category": "nested-state-growth",
                    "status": "unverified",
                },
                {
                    "title": "state growth -> failure-path amplification",
                    "mechanism": "The same storage growth pattern is applied pathologically on a revert or failure route to amplify cost.",
                    "category": "failure-path amplification",
                    "status": "unverified",
                },
                {
                    "title": "state growth -> external call amplification",
                    "mechanism": "A repeated external call path combined with the successful storage-growth pattern magnifies total cost.",
                    "category": "external-call amplification",
                    "status": "unverified",
                },
            ],
            "reason_for_success": "The successful pattern reproduced a monotonic and observable gas scaling effect under local execution.",
            "useful_mutations": [
                "increase state size while keeping function sequence fixed",
                "swap victim ordering to confirm the sensitivity of the sequence",
                "add a repeated interaction before victim work",
            ],
        }
        return success_pattern

    def learn_failure(self, hypothesis: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        normalized = _normalize_experiment_result(result)
        classification = normalized.get("classification", "inconclusive")
        feedback = normalized.get("feedback", {})
        if classification == "disproven":
            taxonomy = "GAS_NOT_SCALING"
            reason = "The local experiment did not show a useful gas ramp with the expected attacker-controlled state growth."
        elif classification == "inconclusive":
            taxonomy = "INSUFFICIENT_EVIDENCE"
            reason = "The measurements were insufficient to distinguish between a bound and a true amplification mechanism."
        else:
            taxonomy = "OTHER"
            reason = "The failure mode did not fit the standard local amplification pattern."

        if feedback.get("disproven_assumptions"):
            reason = str(feedback["disproven_assumptions"][0])
        failure_summary = {
            "hypothesis_id": str(hypothesis.get("id", normalized.get("hypothesis_id", "H-000"))),
            "title": str(hypothesis.get("title", "local hypothesis")),
            "classification": classification,
            "failure_taxonomy": taxonomy,
            "reason": reason,
            "wrong_assumption": "The original hypothesis assumed a monotonic gas increase without verifying the required state path or victim call ordering.",
            "missing_precondition": "A larger attacker-controlled collection or different call ordering may be required to trigger the victim cost growth.",
            "modified_hypotheses": [
                {
                    "title": "sequence-order mutation for the failed state-growth hypothesis",
                    "mechanism": "Reorder attacker and victim calls to test whether the original failure was caused by invalid sequence assumptions.",
                    "status": "unverified",
                },
                {
                    "title": "boundary-value mutation for the failed state-growth hypothesis",
                    "mechanism": "Measure boundary values around the previous state size to test whether the actual amplification threshold was underestimated.",
                    "status": "unverified",
                },
            ],
        }
        return failure_summary

    def classify_failure(self, result: dict[str, Any]) -> str:
        classification = str(result.get("classification", "inconclusive")).lower()
        if classification == "disproven":
            return "GAS_NOT_SCALING"
        if classification == "inconclusive":
            return "INSUFFICIENT_EVIDENCE"
        if result.get("feedback", {}).get("human_review_required"):
            return "OTHER"
        return "OTHER"

    def minimize_counterexample(self, candidate: dict[str, Any]) -> dict[str, Any]:
        minimized = dict(candidate)
        values = minimized.get("parameters", {})
        if isinstance(values, dict):
            minimal_values = {}
            for key, value in values.items():
                if isinstance(value, int):
                    minimal_values[key] = max(1, value // 2)
                else:
                    minimal_values[key] = value
            minimized["parameters"] = minimal_values
        if "attack_sequence" in minimized:
            sequence = minimized["attack_sequence"]
            if isinstance(sequence, list) and len(sequence) > 1:
                minimized["attack_sequence"] = sequence[: max(1, len(sequence) // 2)]
        return minimized

    def generate_mutations(self, hypothesis: dict[str, Any], result: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        base = dict(hypothesis)
        candidate_title = str(base.get("title", "local state-growth hypothesis"))
        candidates = [
            {
                **base,
                "id": str(base.get("id", "H-100")),
                "title": f"{candidate_title} -> nested iteration variant",
                "mechanism": "A secondary loop or nested traversal path amplifies the original state-growth mechanism without changing the core logic.",
                "category": "nested-state-growth",
                "attack_sequence": [
                    "grow attacker-controlled state",
                    "trigger nested victim iteration",
                    "measure gas before and after the nested path",
                ],
                "parameters": {"small_state": 10, "medium_state": 80, "large_state": 200},
            },
            {
                **base,
                "id": str(base.get("id", "H-101")),
                "title": f"{candidate_title} -> failure-path variant",
                "mechanism": "The same storage-growth mechanism is forced through a revert or error path to determine if failure handling amplifies cost.",
                "category": "failure-path amplification",
                "attack_sequence": [
                    "grow attacker-controlled state",
                    "trigger the failure path",
                    "measure revert cost and repeated failures",
                ],
                "parameters": {"small_state": 25, "medium_state": 120, "large_state": 260},
            },
            {
                **base,
                "id": str(base.get("id", "H-102")),
                "title": f"{candidate_title} -> external-call variant",
                "mechanism": "The successful state-growth pattern is combined with repeated external-call behavior to test whether the cost is dominated by the victim path or by callback amplification.",
                "category": "external-call amplification",
                "attack_sequence": [
                    "grow attacker-controlled data",
                    "trigger repeated external interactions",
                    "measure total cost before and after each call",
                ],
                "parameters": {"small_state": 20, "medium_state": 100, "large_state": 220},
            },
        ]
        if result is not None:
            classification = str(result.get("classification", "inconclusive")).lower()
            if classification == "confirmed_mechanism":
                candidates.insert(0, {
                    **base,
                    "id": str(base.get("id", "H-103")),
                    "title": f"{candidate_title} -> state-history variant",
                    "mechanism": "The success depends on state history, so we test whether a prior growth pattern or previous calls alter the victim cost profile.",
                    "category": "state-history strategy",
                    "attack_sequence": [
                        "grow state over multiple rounds",
                        "invoke the victim path again",
                        "compare cost before and after repeated growth",
                    ],
                    "parameters": {"small_state": 12, "medium_state": 90, "large_state": 180},
                })
            else:
                candidates.insert(0, {
                    **base,
                    "id": str(base.get("id", "H-104")),
                    "title": f"{candidate_title} -> boundary-value variant",
                    "mechanism": "The disproven pattern may still have a threshold where gas scales sharply, so we test boundary values around the prior state sizes.",
                    "category": "boundary-value strategy",
                    "attack_sequence": [
                        "test small and near-threshold inputs",
                        "repeat the victim action",
                        "measure whether the cost spikes at a boundary",
                    ],
                    "parameters": {"small_state": 8, "medium_state": 16, "large_state": 32},
                })

        deduped = []
        seen = set()
        for item in candidates:
            signature = json.dumps(item.get("title", ""), sort_keys=True)
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(item)
        return deduped

    def persist_strategy_version(
        self,
        previous_strategy: str,
        observed_evidence: list[str],
        proposed_change: str,
        reason: str,
        expected_benefit: str,
        tests_performed: list[str],
        resulting_performance: dict[str, Any],
        run_id: str,
    ) -> dict[str, Any]:
        version_name = self._next_strategy_version()
        payload = {
            "version": version_name,
            "previous_strategy": previous_strategy,
            "observed_evidence": observed_evidence,
            "proposed_change": proposed_change,
            "reason": reason,
            "expected_benefit": expected_benefit,
            "tests_performed": tests_performed,
            "resulting_performance": resulting_performance,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
        }
        self.strategy_dir.joinpath(f"{version_name}.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return payload

    def evaluate_cycle(self, cycle_record: dict[str, Any]) -> dict[str, Any]:
        executed = len(cycle_record.get("executed_experiments", []))
        confirmed = sum(1 for item in cycle_record.get("executed_experiments", []) if item.get("classification") == "confirmed_mechanism")
        disproven = sum(1 for item in cycle_record.get("executed_experiments", []) if item.get("classification") == "disproven")
        metrics = {
            "hypotheses_generated": cycle_record.get("hypotheses_generated", 0),
            "unique_hypotheses": len({item.get("hypothesis_id") for item in cycle_record.get("executed_experiments", []) if item.get("hypothesis_id")}),
            "duplicate_rate": 0.0,
            "experiments_executed": executed,
            "useful_experiments": confirmed + disproven,
            "disproven_hypotheses": disproven,
            "confirmed_mechanisms": confirmed,
            "minimized_counterexamples": cycle_record.get("minimized_counterexamples", 0),
            "strategy_effectiveness": cycle_record.get("strategy_effectiveness", 0.0),
            "repeated_failure_rate": cycle_record.get("repeated_failure_rate", 0.0),
            "unexplored_areas": cycle_record.get("unexplored_areas", []),
            "coverage": cycle_record.get("coverage", {"functions": [], "invariants": []}),
        }
        if executed:
            metrics["duplicate_rate"] = round((max(0, executed - metrics["unique_hypotheses"])) / executed, 4)
        return metrics
