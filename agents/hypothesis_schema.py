from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


HYPOTHESIS_CATEGORIES = {
    "gas amplification",
    "unbounded iteration",
    "attacker-controlled state growth",
    "storage growth",
    "external-call amplification",
    "failed-call/griefing behavior",
    "state-transition blocking",
    "access-control interaction",
    "resource exhaustion",
    "economic/resource griefing",
}


@dataclass
class HypothesisRecord:
    id: str
    title: str
    mechanism: str
    category: str
    affected_functions: list[str]
    attacker_controlled_inputs: list[str]
    attacker_capabilities: list[str]
    required_state: list[str]
    target_invariant: str
    attack_sequence: list[str]
    predicted_failure: str
    expected_observation: str
    experiment_plan: dict[str, Any]
    priority: int
    novelty_status: str
    confidence: float
    status: str = "unverified"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["experiment_plan"] = dict(self.experiment_plan)
        return payload


def validate_hypothesis_schema(record: dict[str, Any]) -> bool:
    required_fields = {
        "id",
        "title",
        "mechanism",
        "category",
        "affected_functions",
        "attacker_controlled_inputs",
        "attacker_capabilities",
        "required_state",
        "target_invariant",
        "attack_sequence",
        "predicted_failure",
        "expected_observation",
        "experiment_plan",
        "priority",
        "novelty_status",
        "confidence",
        "status",
    }
    if not required_fields.issubset(record.keys()):
        return False
    if record["category"] not in HYPOTHESIS_CATEGORIES:
        return False
    if record["status"] == "":
        return False
    return True
