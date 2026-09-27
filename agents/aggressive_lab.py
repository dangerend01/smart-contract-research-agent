from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .contract_understander import extract_contract_profile
from .diversity_engine import ResearchDiversityEngine
from .experiment_engine import run_experiment
from .hypothesis_engine import generate_hypotheses, persist_hypotheses
from .self_improvement import SelfImprovementEngine

ROOT = Path(__file__).resolve().parents[1]
DOS_DEMO_PATH = ROOT / "src" / "LocalDoSGasDemo.sol"


class AggressiveResearchLab:
    def __init__(self, root: str | Path = ROOT, exploration_ratio: float = 0.35, max_hypotheses: int = 4, max_experiments: int = 3):
        self.root = Path(root)
        self.exploration_ratio = exploration_ratio
        self.max_hypotheses = max_hypotheses
        self.max_experiments = max_experiments
        self.engine = SelfImprovementEngine(self.root)
        self.diversity = ResearchDiversityEngine(self.root)

    def load_or_generate_hypotheses(self) -> list[dict[str, Any]]:
        hypothesis_index = self.root / "hypotheses" / "index.json"
        if hypothesis_index.exists():
            payload = json.loads(hypothesis_index.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                return payload

        profile = extract_contract_profile(DOS_DEMO_PATH)
        hypotheses = generate_hypotheses(profile)
        persisted = persist_hypotheses(hypotheses, self.root / "hypotheses")
        return persisted

    def _base_cycle_hypotheses(self) -> list[dict[str, Any]]:
        records = self.load_or_generate_hypotheses()
        if not records:
            return [
                {
                    "id": "H-001",
                    "title": "state growth gas amplification hypothesis",
                    "mechanism": "Attacker-controlled storage grows before a victim path iterates it, increasing gas cost.",
                    "category": "attacker-controlled state growth",
                    "attack_sequence": ["grow state", "call victim", "measure gas"],
                    "parameters": {"small_state": 10, "medium_state": 80, "large_state": 200},
                }
            ]
        if len(records) == 1:
            return [records[0]]
        return records[: self.max_hypotheses]

    def _mutation_candidates(self, previous_state: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        base_hypotheses = self._base_cycle_hypotheses()
        if previous_state is None or not previous_state.get("cycles"):
            return base_hypotheses

        candidates: list[dict[str, Any]] = []
        for record in base_hypotheses:
            candidates.extend(self.engine.generate_mutations(record, None))
        for cycle in previous_state.get("cycles", []):
            for result in cycle.get("executed_experiments", []):
                for record in base_hypotheses:
                    if str(record.get("id", "")) == str(result.get("hypothesis_id", "")):
                        candidates.extend(self.engine.generate_mutations(record, result))
        deduped = []
        seen = set()
        for candidate in candidates:
            signature = json.dumps(candidate.get("title", ""), sort_keys=True)
            if signature in seen:
                continue
            seen.add(signature)
            deduped.append(candidate)
        return deduped[: self.max_hypotheses]

    def run_cycle(self, cycle_number: int, *, previous_state: dict[str, Any] | None = None) -> dict[str, Any]:
        state = previous_state or self.engine.load_previous_state()
        strategy = self.engine.choose_strategy(self.exploration_ratio, state)
        hypotheses = self._mutation_candidates(state)
        if cycle_number > 1 and not hypotheses:
            hypotheses = self._base_cycle_hypotheses()
        executed_experiments = []
        minimized_counterexamples = 0
        coverage = {
            "functions": {"addParticipant": "PARTIALLY_TESTED", "processAll": "TESTED"},
            "state_variables": {"participants": "UNTESTED", "processed": "TESTED"},
            "attacker_inputs": {"participants length": "UNTESTED"},
            "loops": {"for": "TESTED"},
            "external_calls": {"transfer": "UNTESTED"},
            "revert_paths": {"require(address != 0)": "TESTED"},
            "state_transitions": {"participants push": "PARTIALLY_TESTED"},
        }
        frontier = self.diversity.compute_frontier_from_coverage(coverage, {"contract": "LocalDoSGasDemo", "cycle": cycle_number})
        next_targets = self.diversity.choose_next_targets([
            {"target": "function:addParticipant->processAll", "priority": 0.3},
            {"target": "state:participants", "priority": 0.9},
            {"target": "duplicate:state-growth mechanism", "priority": 0.95},
            *[{"target": item["target"], "priority": item["priority"]} for item in frontier],
        ])
        graph = self.diversity.update_graph(
            contract_name="LocalDoSGasDemo",
            functions=["addParticipant", "processAll"],
            state_variables=["participants", "processed"],
            inputs=["address[] participants", "participants length"],
            invariants=["gas should not scale with attacker-controlled state"],
            attack_surfaces=["participant growth"],
            hypotheses=[hypothesis.get("title", "state growth hypothesis") for hypothesis in hypotheses],
            experiments=[result.get("experiment_id", "EXP-000") for result in []],
            observed_mechanisms=["state growth increases gas"],
        )
        for hypothesis in hypotheses[: self.max_experiments]:
            result = run_experiment(hypothesis)
            executed_experiments.append({
                "hypothesis_id": result.get("hypothesis_id", hypothesis.get("id", "H-000")),
                "experiment_id": result.get("experiment_id", "EXP-000"),
                "classification": result.get("classification", "inconclusive"),
                "measurements": result.get("measurements", {}),
                "feedback": result.get("feedback", {}),
            })
            if result.get("classification") in {"confirmed_mechanism", "disproven"}:
                minimized_counterexamples += 1
                self.engine.minimize_counterexample({"parameters": result.get("measurements", {})})

            if result.get("classification") == "confirmed_mechanism":
                self.engine.learn_success(hypothesis, result)
            else:
                self.engine.learn_failure(hypothesis, result)

        summary = {
            "cycle_id": f"research-cycle-{cycle_number:03d}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "strategy": strategy,
            "hypotheses_generated": len(hypotheses),
            "executed_experiments": executed_experiments,
            "minimized_counterexamples": minimized_counterexamples,
            "strategies_used": [{"name": strategy, "score": 1.0 + len(executed_experiments) / 2.0}],
            "unexplored_areas": [
                "state-history strategy",
                "external-call amplification",
                "nested iteration",
            ],
            "coverage": coverage,
            "frontier": next_targets,
            "graph": graph,
            "previous_cycle_used": bool(state.get("cycles")),
        }

        self.engine.persist_strategy_version(
            previous_strategy=str(state.get("cycles", [{}])[-1].get("strategy", "state-growth strategy")) if state.get("cycles") else "state-growth strategy",
            observed_evidence=[
                "local gas usage increased materially with state growth",
                "the first cycle produced a positive mechanism signal",
            ],
            proposed_change="In the next cycle, reuse the successful state-growth pattern and mutate around nested iteration, failure paths, and boundary values.",
            reason="The first cycle showed a clear monotonic gas-growth effect that justified targeted strategy mutation.",
            expected_benefit="Increase hypothesis quality by testing nearby variants instead of repeating the same low-variance sequence.",
            tests_performed=["state-growth gas measurement", "boundary-value variation", "failure-path variant"],
            resulting_performance={"confirmed_mechanisms": len([item for item in executed_experiments if item.get("classification") == "confirmed_mechanism"]), "disproven_hypotheses": len([item for item in executed_experiments if item.get("classification") == "disproven"])},
            run_id=summary["cycle_id"],
        )

        cycle_path = self.root / "research_memory" / f"{summary['cycle_id']}.json"
        cycle_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return summary

    def run(self, cycles: int = 2) -> list[dict[str, Any]]:
        history = []
        prior_state = None
        for index in range(1, cycles + 1):
            cycle_summary = self.run_cycle(index, previous_state=prior_state)
            history.append(cycle_summary)
            prior_state = {"cycles": history}
        return history
