import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_evals import validate_case


VALID_CASE = {
    "schema_version": "1.0",
    "case_id": "test.case",
    "case_version": 1,
    "title": "Test case",
    "domain": "agent",
    "description": "A test.",
    "required_evidence": ["revision"],
    "assertions": [
        {
            "id": "revision-present",
            "evidence_key": "revision",
            "operator": "is_non_empty_string",
            "required": True,
            "description": "Revision exists.",
        }
    ],
}


class ValidateEvaluationCaseTests(unittest.TestCase):
    def write_case(self, data):
        temporary = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False)
        with temporary:
            json.dump(data, temporary)
        self.addCleanup(Path(temporary.name).unlink, missing_ok=True)
        return Path(temporary.name)

    def test_accepts_valid_case(self):
        self.assertEqual(validate_case(self.write_case(VALID_CASE)), [])

    def test_rejects_unknown_operator(self):
        data = json.loads(json.dumps(VALID_CASE))
        data["assertions"][0]["operator"] = "execute_python"
        self.assertTrue(any("operator" in error for error in validate_case(self.write_case(data))))

    def test_rejects_duplicate_assertion_ids(self):
        data = json.loads(json.dumps(VALID_CASE))
        data["assertions"].append(dict(data["assertions"][0]))
        self.assertTrue(any("duplicated" in error for error in validate_case(self.write_case(data))))

    def test_rejects_missing_expected_value(self):
        data = json.loads(json.dumps(VALID_CASE))
        data["assertions"][0]["operator"] = "equals"
        self.assertTrue(any("expected" in error for error in validate_case(self.write_case(data))))

    def test_rejects_unhashable_evidence_key_without_crashing(self):
        data = json.loads(json.dumps(VALID_CASE))
        data["required_evidence"] = [["nested"]]
        self.assertTrue(validate_case(self.write_case(data)))

    def test_rejects_unhashable_domain_and_operator_without_crashing(self):
        data = json.loads(json.dumps(VALID_CASE))
        data["domain"] = ["agent"]
        data["assertions"][0]["operator"] = ["equals"]
        self.assertTrue(validate_case(self.write_case(data)))

    def test_rejects_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".json", delete=False) as temporary:
            temporary.write("{not json")
        path = Path(temporary.name)
        self.addCleanup(path.unlink, missing_ok=True)
        self.assertTrue(validate_case(path))
