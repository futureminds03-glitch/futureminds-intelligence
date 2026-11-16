import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_task_eval import build_evaluation_case
from scripts.run_eval import evaluate


CONTRACT = {
    "task_id": "sample.task",
    "task_version": 1,
    "title": "Sample task",
    "objective": "A bounded task.",
    "required_evidence": ["source_revision", "ci_status"],
    "acceptance_criteria": [
        {
            "id": "revision",
            "requirement": "Revision is recorded.",
            "evidence_key": "source_revision",
            "operator": "is_non_empty_string",
            "required": True,
        },
        {
            "id": "ci",
            "requirement": "CI passed.",
            "evidence_key": "ci_status",
            "operator": "equals",
            "expected": "success",
            "required": True,
        },
    ],
}


class RunTaskEvaluationTests(unittest.TestCase):
    def test_contract_maps_to_shared_evaluation_case(self):
        case = build_evaluation_case(CONTRACT)
        self.assertEqual(case["case_id"], "sample.task")
        self.assertEqual(case["assertions"][1]["expected"], "success")

    def test_complete_evidence_passes(self):
        report = evaluate(
            build_evaluation_case(CONTRACT),
            {"source_revision": "abc123", "ci_status": "success"},
        )
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["summary"]["required_passed"], 2)

    def test_missing_required_evidence_is_blocked(self):
        report = evaluate(
            build_evaluation_case(CONTRACT),
            {"source_revision": "abc123"},
        )
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["summary"]["required_missing"], 1)

    def test_contradictory_evidence_fails(self):
        report = evaluate(
            build_evaluation_case(CONTRACT),
            {"source_revision": "abc123", "ci_status": "failure"},
        )
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["summary"]["required_failures"], 1)


if __name__ == "__main__":
    unittest.main()
