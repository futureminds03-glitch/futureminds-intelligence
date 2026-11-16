#!/usr/bin/env python3
"""Collect read-only GitHub commit and completed workflow evidence."""
from __future__ import annotations

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
MAX_CHECK_RUNS = 100


class EvidenceCollectionError(Exception):
    pass


def classify_workflow_result(workflow_run: dict[str, Any]) -> str:
    if workflow_run.get("status") != "completed":
        return "blocked"
    conclusion = workflow_run.get("conclusion")
    if conclusion == "success":
        return "passed"
    if conclusion in {"failure", "timed_out", "cancelled", "action_required"}:
        return "failed"
    return "blocked"


def github_get(path: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{API_ROOT}{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "FutureMinds-Intelligence-Evidence-Collector",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise EvidenceCollectionError(
            f"GitHub API returned HTTP {exc.code} for a read-only evidence request"
        ) from exc
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise EvidenceCollectionError(f"GitHub evidence request failed: {exc}") from exc
    if not isinstance(payload, dict):
        raise EvidenceCollectionError("GitHub API returned an unexpected response shape")
    return payload


def collect_evidence(repository: str, commit_sha: str, workflow_run: dict[str, Any], token: str) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise EvidenceCollectionError("GITHUB_REPOSITORY has an invalid format")
    if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", commit_sha):
        raise EvidenceCollectionError("The workflow event does not contain a valid commit SHA")
    if not token:
        raise EvidenceCollectionError("GITHUB_TOKEN is unavailable")

    commit = github_get(f"/repos/{repository}/commits/{commit_sha}", token)
    if commit.get("sha") != commit_sha:
        raise EvidenceCollectionError("GitHub commit identity did not match the requested SHA")

    checks_response = github_get(
        f"/repos/{repository}/commits/{commit_sha}/check-runs?per_page={MAX_CHECK_RUNS}",
        token,
    )
    check_runs = checks_response.get("check_runs")
    total_count = checks_response.get("total_count")
    if not isinstance(check_runs, list) or not isinstance(total_count, int):
        raise EvidenceCollectionError("GitHub check-run response was incomplete")
    if total_count > MAX_CHECK_RUNS:
        raise EvidenceCollectionError(
            f"Commit has {total_count} check runs; refusing to grade a truncated evidence set"
        )

    check_summaries = []
    for check in check_runs:
        if not isinstance(check, dict):
            continue
        check_summaries.append({
            "name": check.get("name"),
            "status": check.get("status"),
            "conclusion": check.get("conclusion"),
            "details_url": check.get("details_url"),
            "completed_at": check.get("completed_at"),
        })

    if workflow_run.get("name") != "Evaluation foundation checks":
        raise EvidenceCollectionError("Unexpected workflow name in completion event")

    # The triggering workflow_run event is the authoritative result for this
    # evaluation. Do not aggregate every commit check: this collector creates
    # its own check run and would otherwise observe itself while in progress.
    test_result = classify_workflow_result(workflow_run)

    files = commit.get("files", [])
    if not isinstance(files, list):
        files = []

    return {
        "evidence_schema_version": "1.0",
        "evidence_source": "github-actions-read-only-api",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "repository": repository,
        "source_revision": commit_sha,
        "commit_url": commit.get("html_url"),
        "commit_message": (commit.get("commit") or {}).get("message"),
        "changed_files": [
            item.get("filename")
            for item in files
            if isinstance(item, dict) and isinstance(item.get("filename"), str)
        ],
        "workflow_run": {
            "id": workflow_run.get("id"),
            "name": workflow_run.get("name"),
            "status": workflow_run.get("status"),
            "conclusion": workflow_run.get("conclusion"),
            "url": workflow_run.get("html_url"),
        },
        "check_run_count": total_count,
        "check_runs": check_summaries,
        "test_result": test_result,
        "test_result_source": "completed-workflow-run-event",
        "integrity_note": (
            "Commit identity and check-run metadata were read from GitHub's API. "
            "This records CI evidence; it does not prove application-level correctness."
        ),
    }


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    repository = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not event_path:
        print("ERROR: GITHUB_EVENT_PATH is required", file=sys.stderr)
        return 2

    try:
        event = json.loads(Path(event_path).read_text(encoding="utf-8"))
        workflow_run = event["workflow_run"]
        commit_sha = workflow_run["head_sha"]
        evidence = collect_evidence(repository, commit_sha, workflow_run, token)
        output = Path("evidence/github-evidence.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, json.JSONDecodeError, KeyError, TypeError, EvidenceCollectionError) as exc:
        print(f"ERROR: evidence collection failed: {exc}", file=sys.stderr)
        return 2

    print(f"Evidence written to {output}")
    print(f"Repository: {repository}")
    print(f"Revision: {commit_sha}")
    print(f"Test result: {evidence['test_result']}")
    print(f"Check runs observed: {evidence['check_run_count']}")
    return 0 if evidence["test_result"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
