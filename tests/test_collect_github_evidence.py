import unittest
from unittest.mock import patch

from scripts.collect_github_evidence import (
    EvidenceCollectionError,
    classify_workflow_result,
    collect_evidence,
)


class GitHubEvidenceClassificationTests(unittest.TestCase):
    def test_completed_success_is_passed(self):
        self.assertEqual(
            classify_workflow_result({"status": "completed", "conclusion": "success"}),
            "passed",
        )

    def test_completed_failure_is_failed(self):
        self.assertEqual(
            classify_workflow_result({"status": "completed", "conclusion": "failure"}),
            "failed",
        )

    def test_cancelled_is_failed(self):
        self.assertEqual(
            classify_workflow_result({"status": "completed", "conclusion": "cancelled"}),
            "failed",
        )

    def test_in_progress_is_blocked(self):
        self.assertEqual(
            classify_workflow_result({"status": "in_progress", "conclusion": None}),
            "blocked",
        )

    def test_unknown_conclusion_fails_closed(self):
        self.assertEqual(
            classify_workflow_result({"status": "completed", "conclusion": "neutral"}),
            "blocked",
        )

    @patch("scripts.collect_github_evidence.github_get")
    def test_completed_workflow_result_is_not_blocked_by_its_own_check_run(self, github_get):
        sha = "a" * 40
        github_get.side_effect = [
            {
                "sha": sha,
                "html_url": "https://github.com/example/repo/commit/" + sha,
                "commit": {"message": "test commit"},
                "files": [{"filename": "README.md"}],
            },
            {
                "total_count": 2,
                "check_runs": [
                    {"name": "Validate cases and unit tests", "status": "completed", "conclusion": "success"},
                    {"name": "Collect commit and CI evidence", "status": "in_progress", "conclusion": None},
                ],
            },
        ]
        evidence = collect_evidence(
            "example/repo",
            sha,
            {"name": "Evaluation foundation checks", "status": "completed", "conclusion": "success"},
            "synthetic-test-token",
        )
        self.assertEqual(evidence["test_result"], "passed")
        self.assertEqual(evidence["test_result_source"], "completed-workflow-run-event")
        self.assertEqual(evidence["check_run_count"], 2)

    @patch("scripts.collect_github_evidence.github_get")
    def test_unexpected_workflow_is_rejected(self, github_get):
        sha = "b" * 40
        github_get.side_effect = [
            {"sha": sha, "html_url": "url", "commit": {"message": "test"}, "files": []},
            {"total_count": 0, "check_runs": []},
        ]
        with self.assertRaises(EvidenceCollectionError):
            collect_evidence(
                "example/repo",
                sha,
                {"name": "Untrusted workflow", "status": "completed", "conclusion": "success"},
                "synthetic-test-token",
            )


if __name__ == "__main__":
    unittest.main()
