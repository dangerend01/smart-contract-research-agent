from __future__ import annotations

from typing import Any


class Evaluator:
    VALID_FINDING_STATUSES = {
        "PLAUSIBLE",
        "CONFIRMED",
        "MISSED",
        "FALSE_POSITIVE",
        "KNOWN_PATTERN",
        "KNOWN_VARIANT",
        "POTENTIALLY_DISTINCT",
    }

    def classify_finding_status(self, challenge: dict[str, Any], researcher_result: dict[str, Any]) -> str:
        status = str(researcher_result.get("finding_status") or researcher_result.get("status") or "PLAUSIBLE").upper()
        if status in self.VALID_FINDING_STATUSES:
            return status

        ground_truth = challenge.get("ground_truth", challenge.get("hidden_ground_truth", {}))
        identified = str(researcher_result.get("identified_mechanism", "") or researcher_result.get("hypothesis", "")).lower()
        expected = str(ground_truth.get("mechanism", "")).lower()
        if identified and expected and identified == expected:
            if researcher_result.get("correct_root_cause") and researcher_result.get("reproducible"):
                return "CONFIRMED"
            return "KNOWN_PATTERN"
        if not identified and expected:
            return "MISSED"
        if identified and expected and identified != expected:
            return "FALSE_POSITIVE"
        if researcher_result.get("mechanism_fingerprint"):
            return "POTENTIALLY_DISTINCT"
        return "PLAUSIBLE"

    def evaluate(self, challenge: dict[str, Any], researcher_result: dict[str, Any]) -> dict[str, Any]:
        ground_truth = challenge.get("ground_truth", challenge.get("hidden_ground_truth", {}))
        identified = str(researcher_result.get("identified_mechanism", "")).lower()
        expected = str(ground_truth.get("mechanism", "")).lower()
        correct_root = bool(researcher_result.get("correct_root_cause", False))
        reproducible = bool(researcher_result.get("reproducible", False))
        threshold = min(1.0, 0.5 + (0.25 if identified == expected else 0.0) + (0.25 if correct_root and reproducible else 0.0))
        passed = identified == expected and correct_root and reproducible
        reason = "Mechanism match and reproducible root cause were identified." if passed else "Mechanism does not match the local benchmark ground truth or lacks reproducible evidence."
        return {
            "pass": passed,
            "score": round(threshold, 4),
            "mechanism_match": identified == expected,
            "correct_root_cause": correct_root,
            "reproducible": reproducible,
            "reason": reason,
            "classification": self.classify_finding_status(challenge, researcher_result),
        }
