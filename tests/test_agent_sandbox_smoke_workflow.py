import unittest
from pathlib import Path


WORKFLOW = Path(".github/workflows/agent-sandbox-smoke.yml")


class AgentSandboxSmokeWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = WORKFLOW.read_text(encoding="utf-8")
        cls.sandbox_job = cls.content.split("  sandbox-smoke:", 1)[1].split("  evaluate-agent-task:", 1)[0]
        cls.docker_section = cls.sandbox_job.split("      - name: Run constrained sandbox proof", 1)[1].split("      - name: Publish sandbox proof status", 1)[0]

    def test_runs_only_after_trusted_foundation_workflow(self):
        self.assertIn("workflow_run:", self.content)
        self.assertIn('workflows: ["Evaluation foundation checks"]', self.content)
        self.assertIn("types: [completed]", self.content)

    def test_uses_least_privilege_and_keeps_token_out_of_sandbox(self):
        for permission in ("contents: read", "pull-requests: read", "checks: read", "statuses: write"):
            with self.subTest(permission=permission):
                self.assertIn(permission, self.content)
        self.assertNotIn("actions/checkout", self.sandbox_job)
        self.assertNotIn("GITHUB_TOKEN", self.docker_section)
        self.assertNotIn("github.token", self.docker_section)
        self.assertIn("GITHUB_TOKEN: ${{ github.token }}", self.content)

    def test_pins_container_by_digest(self):
        self.assertIn(
            "docker.io/library/busybox@sha256:66a6306db78bf2dbf3487f293aa8d6990d8e506fdffab9cc43fe422becf886e4",
            self.content,
        )
        self.assertNotRegex(self.content, r"busybox:(?:latest|1(?:\.\d+)?)(?:\s|$)")

    def test_applies_container_isolation_controls(self):
        for control in (
            "--network none",
            "--read-only",
            "--cap-drop ALL",
            "--security-opt no-new-privileges",
            "--pids-limit 32",
            "--memory 128m",
            "--cpus 0.5",
            "--user 65534:65534",
            "--mount",
        ):
            with self.subTest(control=control):
                self.assertIn(control, self.docker_section)

    def test_does_not_mount_host_credentials_or_docker_socket(self):
        self.assertNotIn("/var/run/docker.sock", self.content)
        self.assertNotIn("~/.ssh", self.content)
        self.assertNotIn(".env", self.content)

    def test_sandbox_proof_checks_readonly_network_caps_and_output(self):
        for evidence in (
            "SANDBOX_PROOF=passed",
            "/proc/mounts",
            "CapEff:",
            "wget -T 2",
            "/output/result.txt",
            "/input/should-not-write",
        ):
            with self.subTest(evidence=evidence):
                self.assertIn(evidence, self.docker_section)

    def test_task_evaluation_uses_trusted_default_branch(self):
        task_job = self.content.split("  evaluate-agent-task:", 1)[1]
        self.assertIn("actions/checkout@v4", task_job)
        self.assertIn("ref: ${{ github.event.repository.default_branch }}", task_job)
        self.assertIn("persist-credentials: false", task_job)
        self.assertNotIn("ref: ${{ github.event.workflow_run.head_sha }}", task_job)

    def test_task_evaluation_uses_authenticated_evidence_and_contract(self):
        self.assertIn("collect_pr_task_evidence", self.content)
        self.assertIn("run_task_eval", self.content)
        self.assertIn("required_ci_check_names", self.content)
        self.assertIn("--required-check-name", self.content)

    def test_task_evaluation_publishes_artifacts_and_status(self):
        self.assertIn("agent-task-evidence-", self.content)
        self.assertIn("FutureMinds Intelligence / Agent task evidence", self.content)
        self.assertIn("retention-days: 14", self.content)


if __name__ == "__main__":
    unittest.main()
