#!/usr/bin/env python3
"""Collect read-only, PR-scoped GitHub evidence for a coding-task evaluation."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API_ROOT = "https://api.github.com"
API_VERSION = "2022-11-28"
MAX_ITEMS = 100
TEST_NAME = re.compile(r"test|pytest|unit", re.IGNORECASE)
FEATURE_TEST_NAME = re.compile(r"share|image|export", re.IGNORECASE)


class EvidenceCollectionError(Exception):
    """Raised when GitHub evidence is incomplete or inconsistent."""


def github_get(path: str, token: str) -> Any:
    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "FutureMinds-Intelligence-PR-Evidence-Adapter",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise EvidenceCollectionError(
            f"GitHub API returned HTTP {exc.code} for a read-only evidence request"
        ) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise EvidenceCollectionError(f"GitHub evidence request failed: {exc}") from exc


def _check_group_status(checks: list[dict[str, Any]]) -> str | None:
    if not checks or any(check.get("status") != "completed" for check in checks):
        return None
    conclusions = [check.get("conclusion") for check in checks]
    return "success" if all(value == "success" for value in conclusions) else "failure"


def _extract_agent_summary(body: str | None) -> str | None:
    if not isinstance(body, str):
        return None
    match = re.search(
        r"(?ims)^##\s+Agent completion summary\s*\n(.*?)(?=^##\s+|\Z)",
        body,
    )
    summary = match.group(1).strip() if match else ""
    return summary or None


def collect_pr_evidence(repository: str, pull_number: int, token: str) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise EvidenceCollectionError("Repository must use owner/repository format")
    if type(pull_number) is not int or pull_number < 1:
        raise EvidenceCollectionError("Pull request number must be a positive integer")
    if not token:
        raise EvidenceCollectionError("A GitHub token with read-only repository access is required")

    pull = github_get(f"/repos/{repository}/pulls/{pull_number}", token)
    base_repo = ((pull.get("base") or {}).get("repo") or {}).get("full_name")
    if base_repo and base_repo.lower() != repository.lower():
        raise EvidenceCollectionError("Pull request base repository did not match the requested repository")
    head = pull.get("head") or {}
    commit_sha = head.get("sha")
    if not isinstance(commit_sha, str) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", commit_sha):
        raise EvidenceCollectionError("Pull request does not expose a valid head commit SHA")

    files = github_get(
        f"/repos/{repository}/pulls/{pull_number}/files?per_page={MAX_ITEMS}", token
    )
    if not isinstance(files, list):
        raise EvidenceCollectionError("GitHub returned an incomplete pull-request file inventory")
    if len(files) >= MAX_ITEMS:
        raise EvidenceCollectionError(
            "Pull request file inventory reached the API page limit; refusing potentially truncated evidence"
        )
    changed_files = [
        item["filename"]
        for item in files
        if isinstance(item, dict) and isinstance(item.get("filename"), str)
    ]
    if len(changed_files) != len(files):
        raise EvidenceCollectionError("Pull request file inventory contained malformed entries")

    checks_response = github_get(
        f"/repos/{repository}/commits/{commit_sha}/check-runs?per_page={MAX_ITEMS}", token
    )
    checks = checks_response.get("check_runs") if isinstance(checks_response, dict) else None
    total_count = checks_response.get("total_count") if isinstance(checks_response, dict) else None
    if not isinstance(checks, list) or not isinstance(total_count, int):
        raise EvidenceCollectionError("GitHub returned an incomplete check-run response")
    if total_count > MAX_ITEMS or total_count != len(checks):
        raise EvidenceCollectionError("Check-run inventory is incomplete; refusing to grade a truncated result")

    summaries = [
        {
            "name": item.get("name"),
            "status": item.get("status"),
            "conclusion": item.get("conclusion"),
            "details_url": item.get("details_url"),
            "completed_at": item.get("completed_at"),
        }
        for item in checks
        if isinstance(item, dict)
    ]
    if len(summaries) != len(checks):
        raise EvidenceCollectionError("Check-run inventory contained malformed entries")

    ci_status = _check_group_status(checks)
    test_checks = [item for item in checks if TEST_NAME.search(str(item.get("name", "")))]
    feature_checks = [item for item in checks if FEATURE_TEST_NAME.search(str(item.get("name", "")))]
    unit_status = _check_group_status(test_checks)
    feature_status = _check_group_status(feature_checks)

    evidence: dict[str, Any] = {
        "repository": repository,
        "pull_request_number": pull_number,
        "pull_request_url": pull.get("html_url"),
        "pull_request_state": pull.get("state"),
        "source_revision": commit_sha,
        "changed_files": "\n".join(changed_files) if changed_files else "",
        "changed_file_count": len(changed_files),
        "ci_status": ci_status,
        "unit_test_result": unit_status,
        "share_image_test_result": feature_status,
        "check_runs": summaries,
        "evidence_provenance": {
            "source": "github-rest-api-read-only",
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "authenticated_fields": [
                "repository",
                "pull_request_number",
                "pull_request_url",
                "source_revision",
                "changed_files",
                "check_runs",
                "ci_status",
                "unit_test_result",
                "share_image_test_result",
            ],
            "agent_claim_source": "pull-request-body",
            "agent_claim_is_independently_verified": False,
            "integrity_note": (
                "Repository, PR metadata, changed files and check runs were retrieved from GitHub's "
                "read-only API. PR text is an agent claim, not independent proof. No browser or "
                "application-level behavior is inferred from CI status alone."
            ),
        },
    }
    summary = _extract_agent_summary(pull.get("body"))
    if summary:
        evidence["agent_completion_summary"] = summary
    return evidence


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, help="GitHub owner/repository")
    parser.add_argument("--pull-request", required=True, type=int, help="Pull request number")
    parser.add_argument("--output", type=Path, required=True, help="Output evidence JSON path")
    args = parser.parse_args()
    token = os.environ.get("GITHUB_TOKEN", "")
    try:
        evidence = collect_pr_evidence(args.repository, args.pull_request, token)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, EvidenceCollectionError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Evidence written: {args.output}")
    print(f"Repository: {args.repository}  PR: #{args.pull_request}")
    print(f"Revision: {evidence['source_revision']}")
    print(f"Changed files: {evidence['changed_file_count']}")
    print(f"CI: {evidence['ci_status'] or 'missing/incomplete'}")
    print(f"Unit tests: {evidence['unit_test_result'] or 'missing/incomplete'}")
    print(f"Feature tests: {evidence['share_image_test_result'] or 'missing/incomplete'}")
    print(f"Agent summary: {'present (unverified claim)' if 'agent_completion_summary' in evidence else 'missing'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
