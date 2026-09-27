from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from .contract_understander import ContractProfile
from .invariants import Invariant


@dataclass
class Hypothesis:
    id: str
    title: str
    mechanism: str
    affected_functions: list[str]
    required_attacker_capability: str
    expected_security_invariant: str
    predicted_failure_condition: str
    test_idea: str
    novelty_notes: str
    status: str = "new"


def _dedupe_tokens(values: Iterable[str]) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        for token in value.lower().replace("-", " ").replace("_", " ").split():
            if len(token) > 2:
                tokens.add(token)
    return tokens


def build_hypotheses(profile: ContractProfile, invariants: list[Invariant]) -> list[Hypothesis]:
    hypotheses: list[Hypothesis] = []
    function_names = [func.name for func in profile.functions]

    if profile.loops or profile.arrays:
        hypotheses.append(
            Hypothesis(
                id="H-001",
                title="Unbounded iteration over user-supplied state creates gas griefing",
                mechanism="An attacker appends many entries to a dynamic array or mapping-backed collection, then invokes a function that iterates over the full collection during a victim action.",
                affected_functions=function_names,
                required_attacker_capability="Add entries to a stateful collection or trigger growth of a dynamic list before another user calls the expensive path.",
                expected_security_invariant="A single user should not be able to make another user's operation excessively expensive.",
                predicted_failure_condition="As the collection grows, each call to the expensive function consumes increasing gas and may become unusable for legitimate users.",
                test_idea="Measure gas for a fixed operation as the number of attacker-controlled entries increases and assert that cost grows materially with the collection length.",
                novelty_notes="This is a classic local gas-griefing pattern; it is a strong candidate only when the contract actually iterates over a user-controlled set in a vulnerable path.",
                status="new",
            )
        )

    if profile.access_control_checks:
        hypotheses.append(
            Hypothesis(
                id="H-002",
                title="Authorization guard is present but may not cover all critical state transitions",
                mechanism="The contract wants to protect sensitive state, but some transitions may be reachable through a broader path than the intended privileged function.",
                affected_functions=function_names,
                required_attacker_capability="Understand and trigger an alternate entry point or a state transition path that bypasses or weakens the intended guard.",
                expected_security_invariant="Critical state transitions should remain protected by the intended access-control logic.",
                predicted_failure_condition="A privileged action can be called by a non-privileged path or can be forced to process excessive work before the guard is enforced.",
                test_idea="Trace each mutating function and compare whether the same state update is reachable without the expected authorization step.",
                novelty_notes="This is a review-oriented hypothesis that requires code path analysis before claiming a real bypass.",
                status="new",
            )
        )

    if profile.external_calls and profile.loops:
        hypotheses.append(
            Hypothesis(
                id="H-003",
                title="External call inside a loop amplifies denial-of-service cost",
                mechanism="A loop calls out to another contract or token endpoint for each iteration, which increases gas cost and introduces user-controlled amplification.",
                affected_functions=function_names,
                required_attacker_capability="Grow the loop count or cause repeated external interactions through a public input or stateful collection.",
                expected_security_invariant="Gas use should not scale unexpectedly with attacker-controlled state or repeated calls.",
                predicted_failure_condition="Each iteration triggers external work, causing total cost to grow superlinearly and making victim operations unusable.",
                test_idea="Add a large attacker-controlled set, then measure whether gas grows sharply when the loop invokes an external call per iteration.",
                novelty_notes="This pattern is important for gas griefing, but it depends on a specific loop-plus-call structure and should be validated with local measurements.",
                status="new",
            )
        )

    if not hypotheses:
        hypotheses.append(
            Hypothesis(
                id="H-999",
                title="No obvious gas-griefing pattern detected in the current local contract profile",
                mechanism="The contract lacks obvious unbounded loops, user-controlled arrays, or expensive external-call paths in the initial analysis.",
                affected_functions=function_names,
                required_attacker_capability="No obvious attacker capability identified from the static profile.",
                expected_security_invariant="The local research baseline should remain callable and should not expose obvious unbounded work paths.",
                predicted_failure_condition="A deeper flow analysis or additional edge conditions may reveal a hidden cost amplifier not visible in the initial pass.",
                test_idea="Review state transitions and repeated loops, then validate with minimal local fuzz or boundary tests.",
                novelty_notes="This is a low-confidence default hypothesis and is intended to trigger follow-up review rather than a claim of vulnerability.",
                status="review",
            )
        )

    return hypotheses
