import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.apply_validated_patch import PatchApplyError, apply_validated_patch


class ApplyValidatedPatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Patch Gate Test")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "existing.py").write_text("before = True\n")
        (self.repo / "src" / "delete.py").write_text("remove = True\n")
        self.git("add", ".")
        self.git("commit", "-m", "base")
        self.base_sha = self.git("rev-parse", "HEAD")
        self.patch_root = self.root / "patch"
        self.patch_root.mkdir()
        self.contract = {"allowed_paths": ["src/", "tests/"]}

    def git(self, *args):
        result = subprocess.run(
            ["git", "-C", str(self.repo), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return result.stdout.strip()

    def entry(self, path, operation, content=None):
        if operation == "delete":
            return {"path": path, "operation": operation, "size_bytes": 0, "sha256": None}
        target = self.patch_root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return {
            "path": path,
            "operation": operation,
            "size_bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        }

    def apply(self, entries, output_name="worktree"):
        manifest = {"schema_version": "1.0", "base_sha": self.base_sha, "files": entries}
        return apply_validated_patch(
            self.repo, self.contract, manifest, self.patch_root,
            self.base_sha, self.root / output_name,
        )

    def test_applies_add_modify_delete_only_in_new_worktree(self):
        entries = [
            self.entry("src/new.py", "add", b"created = True\n"),
            self.entry("src/existing.py", "modify", b"after = True\n"),
            self.entry("src/delete.py", "delete"),
        ]
        report = self.apply(entries)
        worktree = Path(report["output_worktree"])
        self.assertEqual(report["status"], "passed")
        self.assertEqual((worktree / "src" / "new.py").read_bytes(), b"created = True\n")
        self.assertEqual((worktree / "src" / "existing.py").read_bytes(), b"after = True\n")
        self.assertFalse((worktree / "src" / "delete.py").exists())
        self.assertEqual((self.repo / "src" / "existing.py").read_text(), "before = True\n")
        self.assertTrue((self.repo / "src" / "delete.py").exists())
        self.assertEqual(self.git("rev-parse", "HEAD"), self.base_sha)

    def test_rejects_dirty_source_checkout(self):
        (self.repo / "src" / "dirty.py").write_text("dirty")
        with self.assertRaisesRegex(PatchApplyError, "must be clean"):
            self.apply([self.entry("src/new.py", "add", b"new")])

    def test_rejects_base_sha_mismatch(self):
        with self.assertRaisesRegex(PatchApplyError, "HEAD does not match"):
            apply_validated_patch(
                self.repo, self.contract,
                {"schema_version": "1.0", "base_sha": "b" * 40, "files": []},
                self.patch_root, "b" * 40, self.root / "worktree",
            )

    def test_rejects_output_worktree_inside_source_repository(self):
        with self.assertRaisesRegex(PatchApplyError, "outside"):
            self.apply([self.entry("src/new.py", "add", b"new")], "repo/inside")

    def test_rejects_existing_output_path(self):
        output = self.root / "already-there"
        output.mkdir()
        with self.assertRaisesRegex(PatchApplyError, "already exists"):
            apply_validated_patch(
                self.repo, self.contract,
                {"schema_version": "1.0", "base_sha": self.base_sha, "files": []},
                self.patch_root, self.base_sha, output,
            )

    def test_rejects_add_over_existing_file_and_cleans_worktree(self):
        entries = [self.entry("src/existing.py", "add", b"replacement")]
        output = self.root / "collision-worktree"
        with self.assertRaisesRegex(PatchApplyError, "existing path"):
            apply_validated_patch(
                self.repo, self.contract,
                {"schema_version": "1.0", "base_sha": self.base_sha, "files": entries},
                self.patch_root, self.base_sha, output,
            )
        self.assertFalse(output.exists())
        self.assertEqual(self.git("rev-parse", "HEAD"), self.base_sha)

    def test_rejects_parent_symlink_in_base_checkout(self):
        link = self.repo / "src" / "linked"
        link.symlink_to(self.root, target_is_directory=True)
        self.git("add", "src/linked")
        self.git("commit", "-m", "add symlink")
        self.base_sha = self.git("rev-parse", "HEAD")
        entries = [self.entry("src/linked/escape.py", "add", b"escape")]
        with self.assertRaisesRegex(PatchApplyError, "symlink"):
            self.apply(entries)


if __name__ == "__main__":
    unittest.main()
