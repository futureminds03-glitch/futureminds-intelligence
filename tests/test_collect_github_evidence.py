import unittest

from scripts.collect_github_evidence import classify_workflow_result


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


if __name__ == "__main__":
    unittest.main()
