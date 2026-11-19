import json
import unittest
from pathlib import Path


CONTRACT = Path("benchmarks/task-contracts/github-pr-evidence-demo.v1.json")


class GithubPrEvidenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_names_exact_required_ci_check(self):
        self.assertEqual(
            self.contract["required_ci_check_names"],
            ["Validate cases and unit tests"],
        )

    def test_all_acceptance_evidence_keys_are_declared(self):
        declared = set(self.contract["required_evidence"])
        referenced = {item["evidence_key"] for item in self.contract["acceptance_criteria"]}
        self.assertEqual(referenced, declared)

    def test_contract_requires_successful_ci_and_unit_tests(self):
        criteria = {item["id"]: item for item in self.contract["acceptance_criteria"]}
        self.assertEqual(criteria["ci"]["expected"], "success")
        self.assertEqual(criteria["tests"]["expected"], "success")


if __name__ == "__main__":
    unittest.main()
