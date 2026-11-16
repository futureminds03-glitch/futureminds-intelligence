#!/usr/bin/env python3
"""Run a v1 deterministic evaluation case against a JSON evidence document."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.validate_evals import validate_case


def evaluate(case: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    """Grade a validated case using only the explicitly supported operators."""
    grades: list[dict[str, Any]] = []
    required_failures = 0
    required_missing = 0

    for assertion in case["assertions"]:
        key = assertion["evidence_key"]
        present = key in evidence
        actual = evidence.get(key)
        operator = assertion["operator"]
        passed = False
        outcome = "missing"
        explanation = f"Evidence key '{key}' is missing."

        if present:
            if operator == "is_non_empty_string":
                passed = isinstance(actual, str) and bool(actual.strip())
                explanation = (
                    f"Evidence key '{key}' contains a non-empty string."
                    if passed
                    else f"Evidence key '{key}' must contain a non-empty string."
                )
            elif operator == "equals":
                passed = actual == assertion["expected"]
                explanation = (
                    f"Evidence key '{key}' matches the expected value."
                    if passed
                    else f"Evidence key '{key}' does not match the expected value."
                )
            outcome = "passed" if passed else "failed"

        required = assertion["required"]
        if required and outcome == "failed":
            required_failures += 1
        if required and outcome == "missing":
            required_missing += 1

        grades.append({
            "assertion_id": assertion["id"],
            "evidence_key": key,
            "required": required,
            "outcome": outcome,
            "expected": assertion.get("expected"),
            "actual": actual if present else None,
            "explanation": explanation,
        })

    if required_failures:
        status = "failed"
    elif required_missing:
        status = "blocked"
    else:
        status = "passed"

    return {
        "schema_version": "1.0",
        "run_id": str(uuid.uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "case": {"id": case["case_id"], "version": case["case_version"]},
        "status": status,
        "summary": {
            "assertions_total": len(grades),
            "required_failures": required_failures,
            "required_missing": required_missing,
            "required_passed": sum(
                1 for grade in grades
                if grade["required"] and grade["outcome"] == "passed"
            ),
        },
        "grades": grades,
        "evidence_provenance": {
            "source": "user-supplied-json",
            "integrity_note": "The runner grades supplied evidence; it does not independently authenticate its origin.",
        },
        "limitations": [
            "This runner does not execute or authenticate an agent.",
            "Evidence provenance must be independently established by a trusted adapter.",
            "Only deterministic operators declared in the case are supported.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, type=Path, help="Evaluation case JSON")
    parser.add_argument("--evidence", required=True, type=Path, help="Evidence JSON object")
    parser.add_argument("--output", type=Path, help="Optional path for the JSON report")
    args = parser.parse_args()

    errors = validate_case(args.case)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2

    try:
        case = json.loads(args.case.read_text(encoding="utf-8"))
        evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read input JSON: {exc}", file=sys.stderr)
        return 2

    if not isinstance(evidence, dict):
        print("ERROR: evidence root must be a JSON object", file=sys.stderr)
        return 2

    report = evaluate(case, evidence)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
