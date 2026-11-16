import unittest
from unittest.mock import patch

from scripts.collect_pr_task_evidence import (
    EvidenceCollectionError,
    collect_pr_evidence,
)


class CollectPrTaskEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.pull = {
            "html_url": "https://github.com/acme/app/pull/12",
            "state": "open",
            "body": "## Agent completion summary\nAdded the requested export flow.\n\n## Notes\nOther text.",
            "base": {"repo": {"full_name": "acme/app"}},
            "head": {"sha": "a" * 40},
        }
        self.files = [{"filename": "src/share.tsx"}, {"filename": "tests/share.test.ts"}]
        self.checks = {
            "total_count": 3,
            "check_runs": [
                {"name": "Unit tests", "status": "completed", "conclusion": "success"},
                {"name": "Share image export tests", "status": "completed", "conclusion": "success"},
                {"name": "Lint", "status": "completed", "conclusion": "success"},
            ],
        }

    def collect(self, checks=None, files=None, pull=None):
        responses = [
            self.pull if pull is None else pull,
            self.files if files is None else files,
            self.checks if checks is None else checks,
        ]
        with patch("scripts.collect_pr_task_evidence.github_get", side_effect=responses):
            return collect_pr_evidence("acme/app", 12, "read-only-test-token")

    def test_collects_revision_files_and_successful_checks(self):
        evidence = self.collect()
        self.assertEqual(evidence["source_revision"], "a" * 40)
        self.assertIn("src/share.tsx", evidence["changed_files"])
        self.assertEqual(evidence["ci_status"], "success")
        self.assertEqual(evidence["unit_test_result"], "success")
        self.assertEqual(evidence["share_image_test_result"], "success")
        self.assertEqual(evidence["agent_completion_summary"], "Added the requested export flow.")
        self.assertFalse(evidence["evidence_provenance"]["agent_claim_is_independently_verified"])

    def test_missing_feature_specific_check_is_not_a_pass(self):
        checks = {
            "total_count": 2,
            "check_runs": [self.checks["check_runs"][0], self.checks["check_runs"][2]],
        }
        evidence = self.collect(checks=checks)
        self.assertIsNone(evidence["share_image_test_result"])

    def test_in_progress_checks_are_not_reported_as_success(self):
        checks = {
            "total_count": 1,
            "check_runs": [{"name": "Unit tests", "status": "in_progress", "conclusion": None}],
        }
        evidence = self.collect(checks=checks)
        self.assertIsNone(evidence["ci_status"])
        self.assertIsNone(evidence["unit_test_result"])

    def test_failed_check_is_preserved(self):
        checks = {
            "total_count": 1,
            "check_runs": [{"name": "Unit tests", "status": "completed", "conclusion": "failure"}],
        }
        evidence = self.collect(checks=checks)
        self.assertEqual(evidence["ci_status"], "failure")
        self.assertEqual(evidence["unit_test_result"], "failure")

    def test_rejects_truncated_file_inventory(self):
        files = [{"filename": f"file-{i}.py"} for i in range(100)]
        with self.assertRaises(EvidenceCollectionError):
            self.collect(files=files)

    def test_rejects_check_count_mismatch(self):
        checks = {"total_count": 4, "check_runs": self.checks["check_runs"]}
        with self.assertRaises(EvidenceCollectionError):
            self.collect(checks=checks)

    def test_rejects_base_repository_mismatch(self):
        pull = dict(self.pull)
        pull["base"] = {"repo": {"full_name": "other/repo"}}
        with self.assertRaises(EvidenceCollectionError):
            self.collect(pull=pull)


if __name__ == "__main__":
    unittest.main()
