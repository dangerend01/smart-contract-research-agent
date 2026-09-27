import json
from pathlib import Path

from agents.local_execution_replay import LocalExecutionReplayHarness

ROOT = Path(__file__).resolve().parents[1]


def test_local_execution_replay_deploys_and_executes_sequence():
    challenge = json.loads((ROOT / "benchmarks" / "generated" / "hard" / "HB-001.json").read_text(encoding="utf-8"))
    candidate = {
        "candidate_id": "repro-candidate-hb001",
        "challenge_id": "HB-001",
        "call_sequence": [
            {"function": "prepare", "args": [5]},
            {"function": "run", "args": []},
        ],
    }

    result = LocalExecutionReplayHarness(root=ROOT).replay_candidate(challenge, candidate)
    assert result["status"] == "REPRODUCED"
    assert result["execution_results"]
    assert result["state_delta"]["diff"]


def test_local_execution_replay_rejects_invalid_call_sequence():
    challenge = json.loads((ROOT / "benchmarks" / "generated" / "hard" / "HB-002.json").read_text(encoding="utf-8"))
    candidate = {
        "candidate_id": "invalid-candidate",
        "challenge_id": "HB-002",
        "call_sequence": [
            {"function": "settle", "args": []},
        ],
    }

    result = LocalExecutionReplayHarness(root=ROOT).replay_candidate(challenge, candidate)
    assert result["execution_results"]
