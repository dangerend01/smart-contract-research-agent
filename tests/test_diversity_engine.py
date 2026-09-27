from agents.diversity_engine import (
    build_mechanism_graph,
    classify_mechanism_fingerprint,
    coverage_report,
    detect_duplicate_hypothesis,
    generate_function_combinations,
    generate_frontier,
    generate_state_histories,
    select_exploration_targets,
)


def test_mechanism_graph_includes_contract_and_function_links():
    graph = build_mechanism_graph(
        contract_name="LocalDoSGasDemo",
        functions=["addParticipant", "processAll"],
        state_variables=["participants", "processed"],
        inputs=["address[] participants", "uint256 count"],
        invariants=["gas should scale predictably"],
        attack_surfaces=["participant growth"],
        hypotheses=["attacker-controlled participant set amplifies processing cost"],
        experiments=["EXP-001"],
        observed_mechanisms=["state growth increases gas"],
    )
    assert "LocalDoSGasDemo" in graph["contracts"]
    assert "addParticipant" in graph["functions"]
    assert "participants" in graph["state_variables"]
    assert graph["edges"]["LocalDoSGasDemo"]["addParticipant"]


def test_coverage_report_marks_unexplored_dimensions():
    report = coverage_report(
        functions=["addParticipant", "processAll"],
        state_variables=["participants", "processed"],
        attacker_inputs=["participants length"],
        loops=["for"],
        external_calls=[],
        revert_paths=["require(address != 0)"],
        state_transitions=["participants push", "processed increment"],
        tested={"functions": ["processAll"], "state_variables": ["processed"], "inputs": ["participants length"], "loops": ["for"], "revert_paths": ["require(address != 0)"], "state_transitions": ["processed increment"]},
        partially_tested={"functions": ["addParticipant"], "state_variables": []},
    )
    assert report["functions"]["processAll"] == "TESTED"
    assert report["functions"]["addParticipant"] == "PARTIALLY_TESTED"
    assert report["state_variables"]["participants"] == "UNTESTED"


def test_duplicate_detection_rejects_equivalent_mechanisms():
    existing = {
        "affected_functions": ["processAll"],
        "state_dependencies": ["participants"],
        "invariant": "gas should not scale with attacker-controlled state",
        "attack_sequence": ["grow participants", "processAll"],
        "resource_affected": "gas",
    }
    candidate = {
        "affected_functions": ["processAll"],
        "state_dependencies": ["participants"],
        "invariant": "gas should not scale with attacker-controlled state",
        "attack_sequence": ["grow participants", "processAll"],
        "resource_affected": "gas",
    }
    assert detect_duplicate_hypothesis(existing, candidate)["status"] == "duplicate"


def test_combination_generation_creates_local_sequences():
    combos = generate_function_combinations(["addParticipant", "processAll", "setNumber"], max_depth=2)
    assert any("addParticipant" in combo and "processAll" in combo for combo in combos)
    assert any(len(combo) == 2 for combo in combos)


def test_state_history_generation_includes_sequences_and_failures():
    histories = generate_state_histories()
    assert any("fresh state" in item["description"].lower() for item in histories)
    assert any("failure" in item["description"].lower() for item in histories)


def test_frontier_generation_tracks_unexplored_items():
    frontier = generate_frontier(
        {"functions": {"addParticipant": "UNTESTED", "processAll": "TESTED"}, "state_variables": {"participants": "UNTESTED"}},
        {"function": "addParticipant", "state": "participants", "invariant": "gas scaling"},
    )
    assert frontier
    assert any("participants" in item["target"] for item in frontier)


def test_exploration_selection_prefers_frontier_over_duplicate():
    targets = select_exploration_targets(
        [
            {"target": "function:addParticipant->processAll", "priority": 0.2},
            {"target": "state:participants", "priority": 0.8},
            {"target": "duplicate:processAll", "priority": 0.9},
        ]
    )
    assert targets[0]["target"] == "state:participants"
