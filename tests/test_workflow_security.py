from pathlib import Path
import unittest


class WorkflowRunSecurityTests(unittest.TestCase):
    def test_privileged_workflow_run_checks_out_trusted_default_branch(self):
        workflow = Path(".github/workflows/capture-github-evidence.yml").read_text(encoding="utf-8")
        self.assertIn("workflow_run:", workflow)
        self.assertIn("persist-credentials: false", workflow)
        self.assertNotIn("ref: ${{ github.event.workflow_run.head_sha }}", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("checks: read", workflow)
        self.assertIn("actions: read", workflow)

    def test_evidence_workflow_grades_and_uploads_both_records(self):
        workflow = Path(".github/workflows/capture-github-evidence.yml").read_text(encoding="utf-8")
        self.assertIn("python -m scripts.run_eval", workflow)
        self.assertIn("evidence/evaluation-report.json", workflow)
        self.assertIn("path: evidence/*.json", workflow)
        self.assertIn("retention-days: 14", workflow)


if __name__ == "__main__":
    unittest.main()
