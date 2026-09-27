from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


EXPERIMENT_STATUSES = {
    "generated",
    "executing",
    "completed",
    "failed",
}

EXPERIMENT_CLASSIFICATIONS = {
    "confirmed_mechanism",
    "disproven",
    "inconclusive",
    "needs_more_testing",
    "implementation_error",
}


@dataclass
class ExperimentRecord:
    experiment_id: str
    hypothesis_id: str
    target_contract: str
    setup: str
    attacker_actions: list[str]
    victim_actions: list[str]
    parameters: dict[str, Any]
    measurements: dict[str, Any]
    expected_behavior: str
    falsification_condition: str
    test_strategy: str
    status: str = "generated"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_experiment_schema(record: dict[str, Any]) -> bool:
    required = {
        "experiment_id",
        "hypothesis_id",
        "target_contract",
        "setup",
        "attacker_actions",
        "victim_actions",
        "parameters",
        "measurements",
        "expected_behavior",
        "falsification_condition",
        "test_strategy",
        "status",
    }
    if not required.issubset(record.keys()):
        return False
    if record["status"] not in EXPERIMENT_STATUSES:
        return False
    return True
