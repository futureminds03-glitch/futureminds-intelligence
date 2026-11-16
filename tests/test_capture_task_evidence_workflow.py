import unittest
from pathlib import Path


WORKFLOW = Path(".github/workflows/capture-github-evidence.yml")


class IntegratedTaskEvidenceCollectorWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = WORKFLOW.read_text(encoding="utf-8")

    def test_uses_existing_trusted_workflow_run_trigger(self):
        self.assertIn("workflow_run:", self.content)
        self.assertIn('workflows: ["Evaluation foundation checks"]', self.content)
        self.assertIn("types: [completed]", self.content)

    def test_checks_out_only_default_branch_and_never_pr_head(self):
        self.assertIn("ref: ${{ github.event.repository.default_branch }}", self.content)
        self.assertIn("persist-credentials: false", self.content)
        self.assertNotIn("ref: ${{ github.event.workflow_run.head_sha }}", self.content)

    def test_uses_least_privilege_for_read_only_evidence_and_status(self):
        for permission in ("contents: read", "checks: read", "actions: read", "pull-requests: read", "statuses: write"):
            with self.subTest(permission=permission):
                self.assertIn(permission, self.content)
        self.assertNotIn("contents: write", self.content)
        self.assertNotIn("pull-requests: write", self.content)

    def test_resolves_task_pr_by_same_repo_branch_and_exact_sha(self):
        self.assertIn("head.sha == $sha", self.content)
        self.assertIn("head.repo.full_name == $repo", self.content)
        self.assertIn("head.ref == $branch", self.content)
        self.assertIn("agent-task/*", self.content)

    def test_uses_contract_declared_required_checks(self):
        self.assertIn("required_ci_check_names", self.content)
        self.assertIn("--required-check-name", self.content)
        self.assertIn("run_task_eval", self.content)

    def test_preserves_evidence_artifacts_and_distinct_statuses(self):
        self.assertIn("actions/upload-artifact@v4", self.content)
        self.assertIn("FutureMinds Intelligence / Agent task discovery", self.content)
        self.assertIn("FutureMinds Intelligence / Agent task evidence", self.content)
        self.assertIn("retention-days: 14", self.content)

    def test_never_executes_triggering_pr_code(self):
        self.assertNotIn("workflow_run.head_sha }}", self.content.split("Check out trusted default-branch source", 1)[1].split("Set up Python", 1)[0])
        self.assertNotIn("pull_request_target:", self.content)


if __name__ == "__main__":
    unittest.main()
