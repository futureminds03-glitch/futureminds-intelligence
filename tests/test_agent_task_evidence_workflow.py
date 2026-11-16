import unittest
from pathlib import Path


WORKFLOW = Path(".github/workflows/evaluate-agent-task-evidence.yml")


class AgentTaskEvidenceWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = WORKFLOW.read_text(encoding="utf-8")

    def test_uses_trusted_workflow_run_trigger(self):
        self.assertIn("workflow_run:", self.content)
        self.assertIn('workflows: ["Evaluation foundation checks"]', self.content)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", self.content)

    def test_checks_out_only_trusted_default_branch(self):
        self.assertIn("ref: ${{ github.event.repository.default_branch }}", self.content)
        self.assertIn("persist-credentials: false", self.content)
        self.assertNotIn("ref: ${{ github.event.workflow_run.head_sha }}", self.content)
        self.assertNotIn("actions/checkout", self.content.split("ref:")[1].split("persist-credentials")[0])

    def test_uses_only_read_permissions_and_status_publication(self):
        for permission in ("contents: read", "pull-requests: read", "checks: read", "statuses: write"):
            with self.subTest(permission=permission):
                self.assertIn(permission, self.content)
        self.assertNotIn("contents: write", self.content)
        self.assertNotIn("pull-requests: write", self.content)


    def test_resolves_pr_by_exact_completed_commit(self):
        self.assertIn("/commits/$SOURCE_SHA/pulls?per_page=10", self.content)
        self.assertIn(".head.sha == $sha", self.content)
        self.assertIn(".head.ref | startswith(\"agent-task/\")", self.content)
        self.assertIn("steps.resolve.outputs.pr_number != ''", self.content)
        self.assertNotIn("pull_requests[0]", self.content)
        self.assertNotIn("workflow_run.head_branch", self.content)
        self.assertNotIn("workflow_run.head_repository", self.content)


    def test_passes_contract_required_checks_to_evidence_adapter(self):
        self.assertIn("required_ci_check_names", self.content)
        self.assertIn("--required-check-name", self.content)
        self.assertIn("check_args", self.content)

    def test_agent_claim_is_not_executed(self):
        self.assertIn("collect_pr_task_evidence", self.content)
        self.assertIn("run_task_eval", self.content)
        self.assertNotIn("workflow_run.head_sha", self.content.split("Check out trusted default-branch evaluator", 1)[1].split("Set up Python", 1)[0])

    def test_preserves_artifacts_and_status(self):
        self.assertIn("actions/upload-artifact@v4", self.content)
        self.assertIn("retention-days: 14", self.content)
        self.assertIn("FutureMinds Intelligence / Agent task evidence", self.content)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", self.content)


if __name__ == "__main__":
    unittest.main()
