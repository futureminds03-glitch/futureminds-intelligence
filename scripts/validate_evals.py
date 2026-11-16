#!/usr/bin/env python3
"""Validate the intentionally small v1 evaluation-case format (stdlib only)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ALLOWED_DOMAINS = {"agent", "product"}
ALLOWED_OPERATORS = {"is_non_empty_string", "equals"}


def validate_case(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{path}: cannot read valid JSON: {exc}"]

    if not isinstance(data, dict):
        return [f"{path}: case root must be an object"]

    required = {
        "schema_version": str,
        "case_id": str,
        "case_version": int,
        "title": str,
        "domain": str,
        "description": str,
        "required_evidence": list,
        "assertions": list,
    }
    for key, expected_type in required.items():
        if not isinstance(data.get(key), expected_type) or (
            expected_type is str and not data.get(key, "").strip()
        ):
            errors.append(f"{path}: '{key}' must be a non-empty {expected_type.__name__}")

    if data.get("schema_version") != "1.0":
        errors.append(f"{path}: unsupported schema_version (expected '1.0')")
    if type(data.get("case_version")) is not int or data["case_version"] < 1:
        errors.append(f"{path}: case_version must be an integer >= 1")
    if not isinstance(data.get("domain"), str) or data.get("domain") not in ALLOWED_DOMAINS:
        errors.append(f"{path}: domain must be one of {sorted(ALLOWED_DOMAINS)}")

    required_evidence = data.get("required_evidence", [])
    if isinstance(required_evidence, list):
        valid_evidence_keys = all(
            isinstance(item, str) and item.strip() for item in required_evidence
        )
        if not valid_evidence_keys:
            errors.append(f"{path}: required_evidence must contain non-empty strings")
        elif len(required_evidence) != len(set(required_evidence)):
            errors.append(f"{path}: required_evidence entries must be unique")

    valid_evidence_keys = (
        set(required_evidence)
        if isinstance(required_evidence, list)
        and all(isinstance(item, str) and item.strip() for item in required_evidence)
        else set()
    )

    assertions = data.get("assertions", [])
    if not isinstance(assertions, list) or not assertions:
        errors.append(f"{path}: assertions must be a non-empty list")
    else:
        seen: set[str] = set()
        for index, assertion in enumerate(assertions):
            prefix = f"{path}: assertions[{index}]"
            if not isinstance(assertion, dict):
                errors.append(f"{prefix} must be an object")
                continue
            for field in ("id", "evidence_key", "operator", "description"):
                if not isinstance(assertion.get(field), str) or not assertion[field].strip():
                    errors.append(f"{prefix}.{field} must be a non-empty string")
            assertion_id = assertion.get("id")
            if isinstance(assertion_id, str):
                if assertion_id in seen:
                    errors.append(f"{prefix}.id '{assertion_id}' is duplicated")
                seen.add(assertion_id)
            evidence_key = assertion.get("evidence_key")
            if isinstance(evidence_key, str) and evidence_key not in valid_evidence_keys:
                errors.append(
                    f"{prefix}.evidence_key must be declared in required_evidence"
                )
            operator = assertion.get("operator")
            if not isinstance(operator, str) or operator not in ALLOWED_OPERATORS:
                errors.append(f"{prefix}.operator must be one of {sorted(ALLOWED_OPERATORS)}")
            if not isinstance(assertion.get("required"), bool):
                errors.append(f"{prefix}.required must be a boolean")
            if operator == "equals" and "expected" not in assertion:
                errors.append(f"{prefix}.expected is required for equals")
    return errors


def main() -> int:
    paths = sorted(Path("evals/cases").glob("*.json"))
    if not paths:
        print("ERROR: no evaluation cases found in evals/cases", file=sys.stderr)
        return 1
    failures = 0
    for path in paths:
        errors = validate_case(path)
        if errors:
            failures += len(errors)
            for error in errors:
                print(f"ERROR: {error}")
        else:
            print(f"VALID: {path}")
    print(f"Checked {len(paths)} case(s); {failures} validation error(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
