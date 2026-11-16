import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_eval import evaluate
from scripts.validate_evals import validate_case


CASE_PATH = Path("evals/cases/agent-claim-evidence.v1.json")


class DeterministicEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case = json.loads(CASE_PATH.read_text(encoding="utf-8"))

    def test_independent_evidence_passes(self):
        report = evaluate(self.case, {
            "source_revision": "abc123",
            "test_result": "passed",
        })
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["summary"]["required_passed"], 2)

    def test_failed_test_evidence_fails(self):
        report = evaluate(self.case, {
            "source_revision": "abc123",
            "test_result": "not_run",
        })
        self.assertEqual(report["status"], "failed")
        self.assertEqual(report["summary"]["required_failures"], 1)

    def test_agent_claim_without_evidence_is_blocked(self):
        report = evaluate(self.case, {"agent_claim": "Everything is complete."})
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["summary"]["required_missing"], 2)

    def test_evidence_must_be_an_object_at_cli_boundary(self):
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as tmp:
            tmp.write('["not", "an", "object"]')
            path = Path(tmp.name)
        self.addCleanup(path.unlink, missing_ok=True)
        self.assertNotIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)

    def test_case_is_valid_before_execution(self):
        self.assertEqual(validate_case(CASE_PATH), [])


if __name__ == "__main__":
    unittest.main()
