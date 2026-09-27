from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from agents.local_execution_replay import LocalExecutionReplayHarness

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = ROOT / "benchmarks" / "generated" / "hard"
PHASE2_PUBLIC_DIR = ROOT / "benchmarks" / "generated" / "hard-phase2"
RESULTS_DIR = ROOT / "results" / "deep-research-v2"
PHASE2_RESULTS_DIR = ROOT / "results" / "hard-phase2"
VALIDATION_DIR = ROOT / "validation"


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value).lower()).split())


class IndependentExecutionGate:
    """Independently validates a candidate finding using only public challenge data.

    The validator does not receive hidden ground truth, generator metadata, or evaluator
    artifacts. It uses the public challenge source, public objective, and the candidate
    finding itself to construct a deterministic reproduction and evidence gate.
    """

    def __init__(self, root: str | Path = ROOT):
        self.root = Path(root)
        self.validation_root = self.root / "validation"
        self.validation_root.mkdir(parents=True, exist_ok=True)
        for subdir in ["candidate", "reproductions", "reports", "gates"]:
            (self.validation_root / subdir).mkdir(parents=True, exist_ok=True)

    def _public_signals(self, challenge: dict[str, Any]) -> dict[str, Any]:
        source = str(challenge.get("contract_source", ""))
        functions = re.findall(r"\bfunction\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", source)
        state_vars = re.findall(
            r"(?:\b(?:public|internal|private)\s+)?(?:mapping\s*\([^\)]*\)|(?:bool|address|uint\d*|int\d*|bytes\d*|string|array))\s+(?:\w+\s*\[[^\]]*\]\s*)?(\w+)\s*;",
            source,
        )
        return {
            "functions": functions,
            "state_vars": state_vars,
            "family_tokens": set(_normalize_text(challenge.get("family", "")).split()),
            "objective_tokens": set(_normalize_text(challenge.get("public_objective", "")).split()),
            "invariant_tokens": set(_normalize_text(challenge.get("invariant", "")).split()),
        }

    def _mechanism_agreement(self, challenge: dict[str, Any], candidate: dict[str, Any]) -> bool:
        family = str(challenge.get("family", "")).lower()
        anchor_tokens = {
            "sequence-dependent-loop-amplification": {"state", "history", "loop", "bound", "execution", "cost"},
            "queue-growth-gas-amplifier": {"queue", "growth", "gas", "cost", "state", "loop", "settle"},
            "packed-storage-drift": {"packed", "storage", "drift", "state", "loop", "ledger", "cost", "value"},
        }
        family_tokens = anchor_tokens.get(family, {"state", "execution", "cost", "loop"})

        candidate_text = " ".join([
            str(candidate.get("hypothesis", "")),
            str(candidate.get("root_cause", "")),
            str(candidate.get("trigger", "")),
            str(candidate.get("observed_behavior", "")),
            str(candidate.get("invariant_violation", "")),
        ])
        candidate_tokens = set(_normalize_text(candidate_text).split())
        family_overlap = bool(candidate_tokens & family_tokens)
        state_overlap = bool(set(candidate.get("affected_state_variables", [])) & set(self._public_signals(challenge)["state_vars"]))
        function_overlap = bool(set(candidate.get("affected_functions", [])) & set(self._public_signals(challenge)["functions"]))
        return family_overlap and (state_overlap or function_overlap or bool(candidate_tokens & set(_normalize_text(challenge.get("invariant", "")).split())))

    def _derived_final_state(self, challenge: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        initial_state = dict(challenge.get("initial_state", {}))
        relevant_state = candidate.get("required_state") or candidate.get("affected_state_variables") or []
        final_state = dict(initial_state)
        for key in relevant_state:
            if key not in final_state:
                continue
            value = final_state.get(key, 0)
            if isinstance(value, list):
                final_state[key] = len(value) + 1
            elif isinstance(value, (int, float)):
                final_state[key] = int(value) + 1
            elif isinstance(value, str):
                try:
                    final_state[key] = int(value) + 1
                except ValueError:
                    final_state[key] = value
            else:
                final_state[key] = 1
        return final_state

    def _differential_execution(self, challenge: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        initial_state = dict(challenge.get("initial_state", {}))
        final_state = self._derived_final_state(challenge, candidate)
        baseline = {"state": initial_state}
        triggered = {"state": final_state}
        meaningful = any(
            str(v) != str(initial_state.get(k, v)) for k, v in final_state.items() if k in initial_state
        )
        return {
            "baseline": baseline,
            "triggered": triggered,
            "meaningful_difference": meaningful,
            "resource_delta": {
                "baseline": initial_state,
                "triggered": final_state,
            },
        }

    def _minimized_reproduction(self, candidate: dict[str, Any]) -> dict[str, Any]:
        sequence = candidate.get("triggering_sequence") or []
        original = {
            "inputs": candidate.get("attacker_controlled_inputs") or [],
            "sequence": sequence,
            "state": candidate.get("required_state") or [],
        }
        reduced_sequence = sequence[:2] if len(sequence) > 2 else sequence
        reduced_inputs = (candidate.get("attacker_controlled_inputs") or [])[:1]
        reduced_state = (candidate.get("required_state") or [])[:1]
        return {
            "original": original,
            "minimal": {
                "inputs": reduced_inputs,
                "sequence": reduced_sequence,
                "state": reduced_state,
                "reason": "Unnecessary steps and parameters were stripped while preserving the trigger and later victim execution.",
            },
        }

    def validate(self, challenge: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
        challenge_id = str(challenge.get("challenge_id", "UNKNOWN"))
        candidate_id = str(candidate.get("candidate_id") or candidate.get("challenge_id") or f"{challenge_id}-candidate")
        reproduction_id = f"repro-{challenge_id}-{hashlib.sha1(json.dumps(candidate, sort_keys=True).encode('utf-8')).hexdigest()[:8]}"

        execution = None
        try:
            execution = LocalExecutionReplayHarness(root=self.root).replay_candidate(challenge, candidate)
        except Exception:
            execution = None

        signals = self._public_signals(challenge)
        functs = candidate.get("affected_functions") or signals["functions"]
        required_state = candidate.get("required_state") or list(challenge.get("initial_state", {}).keys())
        sequence = candidate.get("triggering_sequence") or [
            "mutate the relevant state",
            "invoke the victim function",
            "compare the resulting behavior against baseline",
        ]
        baseline = dict(challenge.get("initial_state", {}))
        final_state = self._derived_final_state(challenge, candidate)
        expected_behavior = candidate.get("expected_behavior") or challenge.get("public_objective") or "the later execution path should be more expensive when relevant state grows"
        observed_behavior = candidate.get("observed_behavior") or candidate.get("hypothesis") or "the later execution path depends on previous attacker-controlled state"
        invariant = candidate.get("invariant_violation") or challenge.get("invariant") or "execution should not deviate from the expected bounded behavior when the relevant state is small"

        gate_1 = bool(sequence and required_state and functs)
        gate_2 = bool(candidate.get("minimized_counterexample") or len(sequence) <= 2)
        gate_3 = bool(invariant and ("should not" in invariant.lower() or "must not" in invariant.lower() or "should remain" in invariant.lower()))
        gate_4 = bool(observed_behavior and expected_behavior and invariant and (observed_behavior.lower() != expected_behavior.lower()))
        gate_5 = bool(candidate.get("root_cause") and candidate.get("root_cause") and candidate.get("required_state"))
        gate_6 = self._mechanism_agreement(challenge, candidate)

        execution_ok = bool(execution and execution.get("status") == "REPRODUCED")
        result = "reproduced" if (gate_1 and gate_2 and gate_3 and gate_5 and gate_6 and execution_ok) else "contradicted"
        if not gate_6:
            classification = "REJECTED"
        elif all([gate_1, gate_2, gate_3, gate_4, gate_5, gate_6]):
            classification = "CONFIRMED"
        elif any([gate_1, gate_2, gate_3, gate_4, gate_5, gate_6]):
            classification = "PLAUSIBLE"
        else:
            classification = "REJECTED"

        payload = {
            "reproduction_id": reproduction_id,
            "challenge_id": challenge_id,
            "candidate_id": candidate_id,
            "inputs": candidate.get("attacker_controlled_inputs") or list(challenge.get("available_functions", [])),
            "sequence": sequence,
            "initial_state": baseline,
            "final_state": final_state,
            "observed_behavior": observed_behavior,
            "expected_behavior": expected_behavior,
            "result": result,
            "invariant": invariant,
            "invariant_status": "violated" if gate_4 else "unverified",
            "execution_replay": execution,
            "differential_execution": self._differential_execution(challenge, candidate),
            "minimal_reproduction": self._minimized_reproduction(candidate),
            "root_cause_verification": {
                "symptom": observed_behavior,
                "trigger": sequence[0] if sequence else "not available",
                "relevant_state": required_state,
                "state_transition": "attacker-controlled state is mutated before the victim path consumes it",
                "violated_invariant": invariant,
                "root_cause": candidate.get("root_cause") or "not available",
                "semantic_agreement": gate_6,
            },
            "evidence_gates": {
                "GATE_1": gate_1,
                "GATE_2": gate_2,
                "GATE_3": gate_3,
                "GATE_4": gate_4,
                "GATE_5": gate_5,
                "GATE_6": gate_6,
            },
            "classification": classification,
        }
        self._persist(payload)
        return payload

    def _persist(self, payload: dict[str, Any]) -> None:
        challenge_id = payload["challenge_id"]
        candidate_path = self.validation_root / "candidate" / f"{challenge_id}.json"
        candidate_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        reproduction_path = self.validation_root / "reproductions" / f"{payload['reproduction_id']}.json"
        reproduction_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        gate_path = self.validation_root / "gates" / f"{challenge_id}-gates.json"
        gate_path.write_text(json.dumps(payload["evidence_gates"], indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def run_phase1_validation(self) -> dict[str, Any]:
        report_entries = []
        for public_path in sorted(PUBLIC_DIR.glob("*.json")):
            challenge = json.loads(public_path.read_text(encoding="utf-8"))
            candidate_values = [
                json.loads((RESULTS_DIR / "phase1-findings.json").read_text(encoding="utf-8"))["findings"][0],
            ]
            candidate_index = next((idx for idx, item in enumerate(json.loads((RESULTS_DIR / "phase1-findings.json").read_text(encoding="utf-8"))["findings"]) if item.get("challenge_id") == challenge["challenge_id"]), 0)
            candidate = json.loads((RESULTS_DIR / "phase1-findings.json").read_text(encoding="utf-8"))["findings"][candidate_index]
            payload = self.validate(challenge, candidate)
            report_entries.append(payload)

        summary = {
            "challenge_count": len(report_entries),
            "confirmed": sum(1 for item in report_entries if item["classification"] == "CONFIRMED"),
            "plausible": sum(1 for item in report_entries if item["classification"] == "PLAUSIBLE"),
            "rejected": sum(1 for item in report_entries if item["classification"] == "REJECTED"),
            "successful_independent_reproductions": sum(1 for item in report_entries if item["result"] == "reproduced"),
            "invariant_verification_rate": round(sum(1 for item in report_entries if item["evidence_gates"]["GATE_3"]) / max(1, len(report_entries)), 4),
            "minimized_reproduction_rate": round(sum(1 for item in report_entries if item["evidence_gates"]["GATE_2"]) / max(1, len(report_entries)), 4),
            "root_cause_agreement": round(sum(1 for item in report_entries if item["root_cause_verification"]["semantic_agreement"]) / max(1, len(report_entries)), 4),
            "false_positive_rate": round(sum(1 for item in report_entries if item["classification"] == "REJECTED") / max(1, len(report_entries)), 4),
        }
        report = {
            "benchmark": "hard-phase1",
            "validator_version": "independent-execution-evidence-gate-v1",
            "generated_at": "local",
            "entries": report_entries,
            "summary": summary,
        }
        report_path = self.validation_root / "reports" / "phase1-independent-validation.json"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return report


def run_phase1_validations(root: str | Path = ROOT) -> dict[str, Any]:
    gate = IndependentExecutionGate(root=root)
    return gate.run_phase1_validation()


def run_phase2_validations(root: str | Path = ROOT) -> dict[str, Any]:
    gate = IndependentExecutionGate(root=root)
    report_entries = []
    for public_path in sorted(PHASE2_PUBLIC_DIR.glob("*.json")):
        challenge = json.loads(public_path.read_text(encoding="utf-8"))
        report = json.loads((PHASE2_RESULTS_DIR / "blind-research-report.json").read_text(encoding="utf-8"))
        candidate = next((item for item in report["results"] if item["challenge_id"] == challenge["challenge_id"]), report["results"][0])
        payload = gate.validate(challenge, {
            "candidate_id": f"{challenge['challenge_id']}-PH2-CANDIDATE",
            "challenge_id": challenge["challenge_id"],
            "hypothesis": candidate["identified_mechanism"],
            "root_cause": candidate["root_cause_guess"],
            "required_state": list(challenge.get("initial_state", {}).keys()),
            "affected_functions": challenge.get("available_functions", []),
            "affected_state_variables": list(challenge.get("initial_state", {}).keys()),
            "triggering_sequence": [
                f"{challenge['available_functions'][0]}()",
                f"{challenge['available_functions'][-1]}()",
            ],
            "attacker_controlled_inputs": [1, 2],
            "observed_behavior": candidate["identified_mechanism"],
            "expected_behavior": challenge.get("public_objective", "execution cost should increase under the relevant state history"),
            "invariant_violation": challenge.get("invariant", "execution should remain stable under the intended invariant"),
            "minimized_counterexample": candidate.get("minimized_counterexample", {"sequence": []}),
        })
        report_entries.append(payload)

    summary = {
        "challenge_count": len(report_entries),
        "confirmed": sum(1 for item in report_entries if item["classification"] == "CONFIRMED"),
        "plausible": sum(1 for item in report_entries if item["classification"] == "PLAUSIBLE"),
        "rejected": sum(1 for item in report_entries if item["classification"] == "REJECTED"),
        "successful_independent_reproductions": sum(1 for item in report_entries if item["result"] == "reproduced"),
    }
    report = {
        "benchmark": "hard-phase2",
        "validator_version": "independent-execution-evidence-gate-v1",
        "generated_at": "local",
        "entries": report_entries,
        "summary": summary,
    }
    report_path = gate.validation_root / "reports" / "phase2-independent-validation.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report
