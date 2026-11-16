#!/usr/bin/env python3
"""Evaluate a bounded coding-task contract against a supplied evidence document."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from scripts.run_eval import evaluate
from scripts.validate_task_contracts import validate_contract


def build_evaluation_case(contract: dict[str, Any]) -> dict[str, Any]:
    """Translate a validated task contract into the shared deterministic case format."""
    return {
        "schema_version": "1.0",
        "case_id": contract["task_id"],
        "case_version": contract["task_version"],
        "title": contract["title"],
        "domain": "agent",
        "description": contract["objective"],
        "required_evidence": contract["required_evidence"],
        "assertions": [
            {
                "id": criterion["id"],
                "evidence_key": criterion["evidence_key"],
                "operator": criterion["operator"],
                "required": criterion["required"],
                "description": criterion["requirement"],
                **({"expected": criterion["expected"]} if "expected" in criterion else {}),
            }
            for criterion in contract["acceptance_criteria"]
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path, help="Task contract JSON")
    parser.add_argument("--evidence", required=True, type=Path, help="Evidence JSON object")
    parser.add_argument("--output", type=Path, help="Optional path for the JSON report")
    args = parser.parse_args()

    errors = validate_contract(args.contract)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2

    try:
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
        evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read input JSON: {exc}", file=sys.stderr)
        return 2

    if not isinstance(evidence, dict):
        print("ERROR: evidence root must be a JSON object", file=sys.stderr)
        return 2

    report = evaluate(build_evaluation_case(contract), evidence)
    report["task_contract"] = {
        "id": contract["task_id"],
        "version": contract["task_version"],
        "title": contract["title"],
    }
    report["evidence_provenance"] = evidence.get(
        "evidence_provenance",
        {
            "source": "user-supplied-json",
            "integrity_note": (
                "This report grades supplied evidence only. It does not authenticate GitHub, "
                "CI, browser, agent, or deployment evidence."
            ),
        },
    )
    report["limitations"].append(
        "Task contract evaluation does not execute or sandbox an AI coding agent."
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
