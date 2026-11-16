import unittest
from pathlib import Path


class SandboxSmokeDocumentationTests(unittest.TestCase):
    def test_documentation_preserves_isolation_limits(self):
        content = Path("docs/SANDBOX-SMOKE-TEST.md").read_text(encoding="utf-8")
        self.assertIn("Containers share the host kernel", content)
        self.assertIn("does not authorize", content.lower())
        self.assertIn("no token passed to the container", content.lower())

    def test_documentation_explains_trusted_status_boundary(self):
        content = Path("docs/SANDBOX-SMOKE-TEST.md").read_text(encoding="utf-8")
        self.assertIn("statuses: write", content)
        self.assertIn("trusted workflow step", content)
        self.assertIn("never passed to the container", content)

    def test_documentation_rejects_security_certification_claim(self):
        content = Path("docs/SANDBOX-SMOKE-TEST.md").read_text(encoding="utf-8")
        self.assertIn("not a security certification", content)
        self.assertIn("model-generated code", content)


if __name__ == "__main__":
    unittest.main()
