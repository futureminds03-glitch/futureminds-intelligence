import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_agent_patch import PatchRejected, validate_patch_manifest


BASE_SHA = "a" * 40
ALLOWED = ["src/", "tests/"]


class ValidateAgentPatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patch = self.root / "patch"
        self.patch.mkdir()

    def manifest_for(self, path="src/feature.py", content=b"print('safe')", operation="add"):
        target = self.patch / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if operation != "delete":
            target.write_bytes(content)
        return {
            "schema_version": "1.0",
            "base_sha": BASE_SHA,
            "files": [{
                "path": path,
                "operation": operation,
                "size_bytes": len(content) if operation != "delete" else 0,
                "sha256": hashlib.sha256(content).hexdigest() if operation != "delete" else None,
            }],
        }

    def validate(self, manifest, **kwargs):
        return validate_patch_manifest(manifest, self.patch, BASE_SHA, ALLOWED, **kwargs)

    def test_accepts_valid_patch_output(self):
        report = self.validate(self.manifest_for())
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["files_checked"], 1)

    def test_rejects_base_sha_mismatch(self):
        manifest = self.manifest_for()
        manifest["base_sha"] = "b" * 40
        with self.assertRaisesRegex(PatchRejected, "base SHA"):
            self.validate(manifest)

    def test_rejects_path_traversal(self):
        manifest = self.manifest_for("../outside.py")
        with self.assertRaisesRegex(PatchRejected, "traversal"):
            self.validate(manifest)

    def test_rejects_absolute_path(self):
        manifest = self.manifest_for("/tmp/outside.py")
        with self.assertRaisesRegex(PatchRejected, "absolute"):
            self.validate(manifest)

    def test_rejects_path_outside_task_allowlist(self):
        manifest = self.manifest_for("docs/readme.md")
        with self.assertRaisesRegex(PatchRejected, "allowlist"):
            self.validate(manifest)

    def test_rejects_protected_files(self):
        manifest = self.manifest_for("src/auth/session.py")
        with self.assertRaisesRegex(PatchRejected, "protected"):
            self.validate(manifest)

    def test_rejects_workflow_files(self):
        manifest = self.manifest_for(".github/workflows/build.yml")
        with self.assertRaisesRegex(PatchRejected, "allowlist"):
            self.validate(manifest)

    def test_rejects_symlink_output(self):
        target = self.patch / "src" / "link.py"
        target.parent.mkdir()
        target.symlink_to(self.root / "outside.py")
        manifest = {
            "schema_version": "1.0",
            "base_sha": BASE_SHA,
            "files": [{
                "path": "src/link.py",
                "operation": "add",
                "size_bytes": 0,
                "sha256": hashlib.sha256(b"").hexdigest(),
            }],
        }
        with self.assertRaisesRegex(PatchRejected, "symlink"):
            self.validate(manifest)

    def test_rejects_unlisted_output_file(self):
        manifest = self.manifest_for()
        (self.patch / "src" / "extra.py").write_text("not in manifest")
        with self.assertRaisesRegex(PatchRejected, "unlisted"):
            self.validate(manifest)

    def test_rejects_hash_mismatch(self):
        manifest = self.manifest_for()
        manifest["files"][0]["sha256"] = "0" * 64
        with self.assertRaisesRegex(PatchRejected, "SHA-256"):
            self.validate(manifest)

    def test_rejects_file_size_limit(self):
        manifest = self.manifest_for(content=b"x" * 20)
        with self.assertRaisesRegex(PatchRejected, "file exceeds"):
            self.validate(manifest, max_file_bytes=10)

    def test_rejects_total_size_limit(self):
        manifest = self.manifest_for(content=b"x" * 20)
        with self.assertRaisesRegex(PatchRejected, "aggregate"):
            self.validate(manifest, max_total_bytes=10)

    def test_rejects_duplicate_paths(self):
        manifest = self.manifest_for()
        manifest["files"].append(dict(manifest["files"][0]))
        with self.assertRaisesRegex(PatchRejected, "duplicate"):
            self.validate(manifest)

    def test_rejects_case_insensitive_path_collision(self):
        manifest = self.manifest_for("src/Feature.py")
        other = self.patch / "src" / "feature.py"
        other.write_text("different")
        manifest["files"].append({
            "path": "src/feature.py",
            "operation": "add",
            "size_bytes": len(b"different"),
            "sha256": hashlib.sha256(b"different").hexdigest(),
        })
        with self.assertRaisesRegex(PatchRejected, "case-insensitive"):
            self.validate(manifest)

    def test_accepts_delete_entry_without_output_file(self):
        manifest = self.manifest_for("src/old.py", operation="delete")
        report = self.validate(manifest)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["output_files_checked"], 0)

    def test_rejects_unknown_operation(self):
        manifest = self.manifest_for()
        manifest["files"][0]["operation"] = "execute"
        with self.assertRaisesRegex(PatchRejected, "unsupported operation"):
            self.validate(manifest)


if __name__ == "__main__":
    unittest.main()
