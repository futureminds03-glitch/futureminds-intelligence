import unittest
from pathlib import Path


class PrEvidenceWorkflowDocumentationTests(unittest.TestCase):
    def test_contract_declares_exact_required_ci_checks(self):
        content = Path("docs/PR-EVIDENCE-WORKFLOW.md").read_text(encoding="utf-8")
        self.assertIn("required_ci_check_names", content)
        self.assertIn("Validate cases and unit tests", content)

    def test_missing_or_ambiguous_required_checks_cannot_pass(self):
        content = Path("docs/PR-EVIDENCE-WORKFLOW.md").read_text(encoding="utf-8")
        self.assertIn("missing or ambiguous", content)
        self.assertIn("still running", content)

    def test_evaluator_does_not_grade_its_own_concurrent_run(self):
        content = Path("docs/PR-EVIDENCE-WORKFLOW.md").read_text(encoding="utf-8")
        self.assertIn("evidence collector itself", content)
        self.assertIn("only this declared check", content)


if __name__ == "__main__":
    unittest.main()
