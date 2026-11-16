#!/usr/bin/env python3
"""Apply a validated patch into a fresh detached Git worktree, never the source checkout."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.validate_agent_patch import validate_patch_manifest


class PatchApplyError(Exception):
    """Raised when the trusted worktree application cannot safely complete."""


def _git(repository: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repository), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise PatchApplyError(f"git {' '.join(args[:2])} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _assert_no_symlink_ancestors(root: Path, relative: str) -> Path:
    current = root
    for segment in PurePosixPath(relative).parts:
        current = current / segment
        if current.is_symlink():
            raise PatchApplyError(f"target checkout contains a symlink at patch path: {relative}")
    return current


def _apply_entries(
    worktree: Path,
    patch_root: Path,
    entries: list[dict[str, Any]],
) -> None:
    for entry in entries:
        relative = entry["path"]
        operation = entry["operation"]
        target = _assert_no_symlink_ancestors(worktree, relative)
        exists = target.exists()
        if operation == "add" and exists:
            raise PatchApplyError(f"add operation targets an existing path: {relative}")
        if operation in {"modify", "delete"} and not exists:
            raise PatchApplyError(f"{operation} operation targets a missing path: {relative}")
        if exists and not target.is_file():
            raise PatchApplyError(f"target is not a regular file: {relative}")

    for entry in entries:
        relative = entry["path"]
        operation = entry["operation"]
        target = _assert_no_symlink_ancestors(worktree, relative)
        if operation == "delete":
            target.unlink()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        source = patch_root / relative
        with source.open("rb") as input_file:
            payload = input_file.read()
        descriptor, temporary_name = tempfile.mkstemp(prefix=".fm-patch-", dir=target.parent)
        try:
            with os.fdopen(descriptor, "wb") as output_file:
                output_file.write(payload)
                output_file.flush()
                os.fsync(output_file.fileno())
            os.replace(temporary_name, target)
        except Exception:
            try:
                os.unlink(temporary_name)
            except FileNotFoundError:
                pass
            raise


def apply_validated_patch(
    repository: Path,
    contract: dict[str, Any],
    manifest: dict[str, Any],
    patch_root: Path,
    expected_base_sha: str,
    output_worktree: Path,
) -> dict[str, Any]:
    if repository.is_symlink() or not repository.is_dir():
        raise PatchApplyError("source repository must be an existing, non-symlink directory")
    repository = repository.resolve(strict=True)
    top_level = Path(_git(repository, "rev-parse", "--show-toplevel")).resolve(strict=True)
    if top_level != repository:
        raise PatchApplyError("source repository path must be the Git working-tree root")
    head_sha = _git(repository, "rev-parse", "HEAD")
    if head_sha != expected_base_sha:
        raise PatchApplyError("source checkout HEAD does not match the approved base SHA")
    if _git(repository, "status", "--porcelain", "--untracked-files=all"):
        raise PatchApplyError("source checkout must be clean before patch application")

    output_worktree = output_worktree.resolve(strict=False)
    if output_worktree.exists():
        raise PatchApplyError("output worktree path already exists")
    try:
        output_worktree.relative_to(repository)
    except ValueError:
        pass
    else:
        raise PatchApplyError("output worktree must be outside the source repository")

    report = validate_patch_manifest(
        manifest,
        patch_root,
        expected_base_sha,
        contract["allowed_paths"],
    )
    output_worktree.parent.mkdir(parents=True, exist_ok=True)
    created = False
    try:
        _git(repository, "worktree", "add", "--detach", str(output_worktree), expected_base_sha)
        created = True
        _apply_entries(output_worktree, patch_root, manifest["files"])

        changed = set(filter(None, _git(output_worktree, "diff", "--name-only", "-z", "HEAD").split("\x00")))
        untracked = set(filter(None, _git(output_worktree, "ls-files", "--others", "--exclude-standard", "-z").split("\x00")))
        observed = changed | untracked
        expected = {entry["path"] for entry in manifest["files"]}
        if observed != expected:
            raise PatchApplyError(
                f"applied worktree file inventory differs from manifest; observed={sorted(observed)}, expected={sorted(expected)}"
            )
        if _git(output_worktree, "rev-parse", "HEAD") != expected_base_sha:
            raise PatchApplyError("output worktree base revision changed unexpectedly")
        return {
            "schema_version": "1.0",
            "status": "passed",
            "base_sha": expected_base_sha,
            "output_worktree": str(output_worktree),
            "files_applied": len(manifest["files"]),
            "patch_validation": report,
            "limitations": [
                "Changes are applied only to a new detached temporary Git worktree.",
                "No commit, push, pull request, test execution, deployment or source-checkout mutation is performed.",
                "A human or trusted controller must separately inspect and verify the resulting worktree.",
            ],
        }
    except Exception:
        if created:
            subprocess.run(
                ["git", "-C", str(repository), "worktree", "remove", "--force", str(output_worktree)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
                check=False,
            )
        if output_worktree.exists():
            shutil.rmtree(output_worktree, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True, type=Path, help="Clean source Git checkout")
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--patch-root", required=True, type=Path)
    parser.add_argument("--expected-base-sha", required=True)
    parser.add_argument("--output-worktree", required=True, type=Path, help="New path outside source checkout")
    parser.add_argument("--report", type=Path, help="Optional JSON report path")
    args = parser.parse_args()

    try:
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        result = apply_validated_patch(
            args.repository,
            contract,
            manifest,
            args.patch_root,
            args.expected_base_sha,
            args.output_worktree,
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, PatchApplyError, ValueError) as exc:
        result = {"schema_version": "1.0", "status": "failed", "rejection_reason": str(exc)}
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
