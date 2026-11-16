import unittest
from pathlib import Path


class EvidenceArtifactProvenanceDocumentationTests(unittest.TestCase):
    def test_documentation_requires_source_and_report_review(self):
        content = Path("docs/PR-EVIDENCE-WORKFLOW.md").read_text(encoding="utf-8")
        self.assertIn("source evidence artifact", content)
        self.assertIn("evaluator report", content)

    def test_documentation_distinguishes_api_facts_from_agent_claim(self):
        content = Path("docs/PR-EVIDENCE-WORKFLOW.md").read_text(encoding="utf-8")
        self.assertIn("GitHub API fields", content)
        self.assertIn("PR-body completion claim", content)
        self.assertIn("remains unverified", content)

    def test_green_status_is_not_a_complete_review(self):
        content = Path("docs/PR-EVIDENCE-WORKFLOW.md").read_text(encoding="utf-8")
        self.assertIn("a green status alone is only a summary", content)


if __name__ == "__main__":
    unittest.main()
