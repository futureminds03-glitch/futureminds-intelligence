import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_task_contracts import validate_contract


VALID_CONTRACT = {
    "schema_version": "1.0",
    "task_id": "sample.task",
    "task_version": 1,
    "title": "Sample task",
    "objective": "A bounded task.",
    "agent_instruction": "Implement the task and report evidence.",
    "execution_policy": {
        "branch_only": True,
        "pull_request_required": True,
        "production_deployment_allowed": False,
        "production_data_mutation_allowed": False,
        "secrets_exposure_allowed": False,
    },
    "allowed_paths": ["src/", "tests/"],
    "forbidden_actions": ["Deploy to production"],
    "required_evidence": ["ci_status"],
    "acceptance_criteria": [{
        "id": "ci",
        "requirement": "CI passes.",
        "evidence_key": "ci_status",
        "operator": "equals",
        "expected": "success",
        "required": True,
    }],
}


class ValidateTaskContractTests(unittest.TestCase):
    def write_contract(self, data):
        temporary = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False)
        with temporary:
            json.dump(data, temporary)
        path = Path(temporary.name)
        self.addCleanup(path.unlink, missing_ok=True)
        return path

    def test_accepts_valid_contract(self):
        self.assertEqual(validate_contract(self.write_contract(VALID_CONTRACT)), [])

    def test_rejects_boolean_task_version(self):
        data = json.loads(json.dumps(VALID_CONTRACT))
        data["task_version"] = True
        self.assertTrue(validate_contract(self.write_contract(data)))

    def test_rejects_unsafe_execution_policy(self):
        data = json.loads(json.dumps(VALID_CONTRACT))
        data["execution_policy"]["production_deployment_allowed"] = True
        self.assertTrue(any("production_deployment_allowed" in e for e in validate_contract(self.write_contract(data))))

    def test_rejects_path_traversal(self):
        data = json.loads(json.dumps(VALID_CONTRACT))
        data["allowed_paths"] = ["src/", "../secrets"]
        self.assertTrue(any("relative paths" in e for e in validate_contract(self.write_contract(data))))

    def test_rejects_undeclared_evidence_key(self):
        data = json.loads(json.dumps(VALID_CONTRACT))
        data["acceptance_criteria"][0]["evidence_key"] = "unknown"
        self.assertTrue(any("required_evidence" in e for e in validate_contract(self.write_contract(data))))

    def test_rejects_unknown_operator(self):
        data = json.loads(json.dumps(VALID_CONTRACT))
        data["acceptance_criteria"][0]["operator"] = "execute_shell"
        self.assertTrue(any("operator" in e for e in validate_contract(self.write_contract(data))))

    def test_rejects_duplicate_criterion_ids(self):
        data = json.loads(json.dumps(VALID_CONTRACT))
        data["acceptance_criteria"].append(dict(data["acceptance_criteria"][0]))
        self.assertTrue(any("duplicated" in e for e in validate_contract(self.write_contract(data))))


if __name__ == "__main__":
    unittest.main()
