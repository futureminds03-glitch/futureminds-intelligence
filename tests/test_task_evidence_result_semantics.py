import unittest
from pathlib import Path


class TaskEvidenceResultSemanticsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = Path("docs/PR-EVIDENCE-WORKFLOW.md").read_text(encoding="utf-8")

    def test_pass_requires_every_required_assertion(self):
        self.assertIn("passed", self.content)
        self.assertIn("every required assertion", self.content)

    def test_failed_means_observed_contradictory_evidence(self):
        self.assertIn("failed", self.content)
        self.assertIn("completed with failure", self.content)

    def test_blocked_covers_missing_pending_or_ambiguous_evidence(self):
        self.assertIn("blocked", self.content)
        self.assertIn("absent, incomplete, pending or ambiguous", self.content)

    def test_agent_claim_cannot_override_evidence(self):
        self.assertIn("cannot turn missing or failed GitHub evidence into a pass", self.content)


if __name__ == "__main__":
    unittest.main()
