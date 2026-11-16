#!/usr/bin/env python3
"""Validate bounded AI coding-task contracts without executing task content."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ALLOWED_OPERATORS = {"is_non_empty_string", "equals"}
REQUIRED_FIELDS = {
    "schema_version": str,
    "task_id": str,
    "task_version": int,
    "title": str,
    "objective": str,
    "agent_instruction": str,
    "execution_policy": dict,
    "allowed_paths": list,
    "forbidden_actions": list,
    "required_evidence": list,
    "acceptance_criteria": list,
}


def validate_contract(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: cannot read valid JSON: {exc}"]

    if not isinstance(data, dict):
        return [f"{path}: contract root must be an object"]

    for field, expected_type in REQUIRED_FIELDS.items():
        value = data.get(field)
        if not isinstance(value, expected_type):
            errors.append(f"{path}: '{field}' must be a {expected_type.__name__}")
        elif expected_type is str and not value.strip():
            errors.append(f"{path}: '{field}' must be a non-empty string")

    if data.get("schema_version") != "1.0":
        errors.append(f"{path}: unsupported schema_version (expected '1.0')")
    if type(data.get("task_version")) is not int or data["task_version"] < 1:
        errors.append(f"{path}: task_version must be an integer >= 1")

    policy = data.get("execution_policy")
    if isinstance(policy, dict):
        expected_policy = {
            "branch_only": True,
            "pull_request_required": True,
            "production_deployment_allowed": False,
            "production_data_mutation_allowed": False,
            "secrets_exposure_allowed": False,
        }
        for key, expected in expected_policy.items():
            if policy.get(key) is not expected:
                errors.append(f"{path}: execution_policy.{key} must be {str(expected).lower()}")

    allowed_paths = data.get("allowed_paths")
    if isinstance(allowed_paths, list):
        if not allowed_paths or any(not isinstance(item, str) or not item.strip() for item in allowed_paths):
            errors.append(f"{path}: allowed_paths must contain non-empty relative paths")
        elif len(allowed_paths) != len(set(allowed_paths)):
            errors.append(f"{path}: allowed_paths entries must be unique")
        for item in allowed_paths:
            if isinstance(item, str) and (item.startswith("/") or ".." in Path(item).parts):
                errors.append(f"{path}: allowed_paths must not contain absolute paths or '..'")

    forbidden = data.get("forbidden_actions")
    if isinstance(forbidden, list):
        if not forbidden or any(not isinstance(item, str) or not item.strip() for item in forbidden):
            errors.append(f"{path}: forbidden_actions must contain non-empty strings")

    evidence = data.get("required_evidence")
    if isinstance(evidence, list):
        valid_keys = all(isinstance(item, str) and item.strip() for item in evidence)
        if not valid_keys:
            errors.append(f"{path}: required_evidence must contain non-empty strings")
        elif len(evidence) != len(set(evidence)):
            errors.append(f"{path}: required_evidence entries must be unique")
    else:
        valid_keys = False
    valid_keys_set = set(evidence) if isinstance(evidence, list) and valid_keys else set()

    criteria = data.get("acceptance_criteria")
    if not isinstance(criteria, list) or not criteria:
        errors.append(f"{path}: acceptance_criteria must be a non-empty list")
    else:
        seen: set[str] = set()
        for index, criterion in enumerate(criteria):
            prefix = f"{path}: acceptance_criteria[{index}]"
            if not isinstance(criterion, dict):
                errors.append(f"{prefix} must be an object")
                continue
            for field in ("id", "requirement", "evidence_key", "operator"):
                value = criterion.get(field)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{prefix}.{field} must be a non-empty string")
            criterion_id = criterion.get("id")
            if isinstance(criterion_id, str):
                if criterion_id in seen:
                    errors.append(f"{prefix}.id '{criterion_id}' is duplicated")
                seen.add(criterion_id)
            key = criterion.get("evidence_key")
            if isinstance(key, str) and key not in valid_keys_set:
                errors.append(f"{prefix}.evidence_key must be declared in required_evidence")
            operator = criterion.get("operator")
            if not isinstance(operator, str) or operator not in ALLOWED_OPERATORS:
                errors.append(f"{prefix}.operator must be one of {sorted(ALLOWED_OPERATORS)}")
            if not isinstance(criterion.get("required"), bool):
                errors.append(f"{prefix}.required must be a boolean")
            if operator == "equals" and "expected" not in criterion:
                errors.append(f"{prefix}.expected is required for equals")

    return errors


def main() -> int:
    paths = sorted(Path("benchmarks/task-contracts").glob("*.json"))
    if not paths:
        print("ERROR: no task contracts found in benchmarks/task-contracts", file=sys.stderr)
        return 1
    failures = 0
    for path in paths:
        errors = validate_contract(path)
        if errors:
            failures += len(errors)
            for error in errors:
                print(f"ERROR: {error}")
        else:
            print(f"VALID: {path}")
    print(f"Checked {len(paths)} task contract(s); {failures} validation error(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
