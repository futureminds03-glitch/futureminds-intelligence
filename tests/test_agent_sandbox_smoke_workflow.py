import unittest
from pathlib import Path


WORKFLOW = Path(".github/workflows/agent-sandbox-smoke.yml")


class AgentSandboxSmokeWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = WORKFLOW.read_text(encoding="utf-8")

    def test_runs_only_after_trusted_foundation_workflow(self):
        self.assertIn('workflow_run:', self.content)
        self.assertIn('workflows: ["Evaluation foundation checks"]', self.content)
        self.assertIn("types: [completed]", self.content)

    def test_has_no_github_permissions_or_checkout(self):
        self.assertIn("permissions: {}", self.content)
        self.assertNotIn("actions/checkout", self.content)
        self.assertNotIn("GITHUB_TOKEN", self.content)
        self.assertNotIn("secrets.", self.content)

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
                self.assertIn(control, self.content)

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
                self.assertIn(evidence, self.content)


if __name__ == "__main__":
    unittest.main()
