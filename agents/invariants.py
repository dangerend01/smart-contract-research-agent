from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .contract_understander import ContractProfile


@dataclass
class Invariant:
    id: str
    title: str
    description: str
    category: str
    impacted_functions: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)


def _add_invariant(invariants: list[Invariant], kind: str, title: str, description: str, affected: Iterable[str], evidence: Iterable[str]) -> None:
    invariants.append(
        Invariant(
            id=f"INV-{len(invariants) + 1:03d}",
            title=title,
            description=description,
            category=kind,
            impacted_functions=list(affected),
            evidence=list(evidence),
        )
    )


def extract_invariants(profile: ContractProfile) -> list[Invariant]:
    invariants: list[Invariant] = []
    function_names = [func.name for func in profile.functions]

    if profile.loops or profile.arrays:
        _add_invariant(
            invariants,
            "unbounded-work",
            "Operation cost should not grow without bound with attacker-controlled state",
            "User-controlled array or loop growth should not make a call prohibitively expensive for other participants.",
            function_names,
            [
                "dynamic loop pattern detected",
                "state array or mapping widened by user-controlled input",
            ],
        )

    if profile.access_control_checks:
        _add_invariant(
            invariants,
            "access-control",
            "Critical state transitions must remain protected by the intended authorization path",
            "Authorized state changes should not be reachable without the expected guard conditions.",
            function_names,
            [
                "authorization checks were identified in the source",
            ],
        )

    if profile.eth_transfers or profile.token_transfers:
        _add_invariant(
            invariants,
            "funds-safety",
            "ETH or token flows should not become a griefing or denial vector",
            "Value-moving logic should remain bounded and not enable repeated expensive transfer loops or forced call chains.",
            function_names,
            [
                "value transfer or token transfer pattern detected",
            ],
        )

    if profile.external_calls and profile.loops:
        _add_invariant(
            invariants,
            "call-safety",
            "A single user should not be able to force excessive external call or iteration cost on others",
            "A loop with external-call behavior can amplify calldata or state cost unpredictably.",
            function_names,
            [
                "loop plus external call pattern detected",
            ],
        )

    if profile.state_transitions:
        _add_invariant(
            invariants,
            "state-reachability",
            "Critical transitions should remain reachable under legitimate conditions",
            "State mutation paths must stay available for valid users while remaining bounded by the contract policy.",
            function_names,
            [
                "state transitions identified in function bodies",
            ],
        )

    return invariants
