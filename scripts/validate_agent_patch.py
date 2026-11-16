#!/usr/bin/env python3
"""Validate an untrusted, offline patch manifest without applying the patch."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.validate_task_contracts import validate_contract

SHA_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
FILE_SHA_PATTERN = re.compile(r"[0-9a-f]{64}")
PROTECTED_EXACT = {
    "codeowners",
    ".github/codeowners",
    "vercel.json",
    "dockerfile",
    "docker-compose.yml",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
    "pyproject.toml",
    "poetry.lock",
    "requirements.txt",
    "cargo.toml",
    "cargo.lock",
    "go.mod",
    "go.sum",
}
PROTECTED_PREFIXES = (
    ".github/workflows/",
    ".github/actions/",
    "supabase/migrations/",
    "migrations/",
    "db/migrations/",
    "deployment/",
    "deploy/",
    "infra/",
    "terraform/",
)


class PatchRejected(Exception):
    """Raised when a patch bundle violates the offline patch policy."""


def _safe_relative_path(raw: Any) -> str:
    if not isinstance(raw, str) or not raw:
        raise PatchRejected("file path must be a non-empty string")
    if "\x00" in raw or "\\" in raw:
        raise PatchRejected(f"file path contains an invalid character: {raw!r}")
    if raw.startswith("/") or re.match(r"^[A-Za-z]:", raw):
        raise PatchRejected(f"absolute paths are forbidden: {raw!r}")
    parts = raw.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise PatchRejected(f"path traversal or ambiguous path segment is forbidden: {raw!r}")
    if any(part.startswith(".git") for part in parts):
        raise PatchRejected(f"Git metadata paths are forbidden: {raw!r}")
    normalized = PurePosixPath(raw).as_posix()
    if normalized != raw:
        raise PatchRejected(f"path is not in canonical POSIX form: {raw!r}")
    return normalized


def _is_allowed(path: str, allowed_paths: list[str]) -> bool:
    for allowed in allowed_paths:
        if path == allowed.rstrip("/"):
            return True
        if allowed.endswith("/") and path.startswith(allowed):
            return True
    return False


def _is_protected(path: str) -> bool:
    lowered = path.lower()
    basename = lowered.rsplit("/", 1)[-1]
    if lowered in PROTECTED_EXACT or basename in PROTECTED_EXACT:
        return True
    if any(lowered.startswith(prefix) for prefix in PROTECTED_PREFIXES):
        return True
    parts = lowered.split("/")
    if any(part in {"auth", "security", "authentication", "authorization"} for part in parts[:-1]):
        return True
    if basename.endswith((".lock", ".pem", ".key", ".p12", ".pfx")):
        return True
    return False


def _scan_patch_root(root: Path) -> set[str]:
    if not root.exists() or not root.is_dir() or root.is_symlink():
        raise PatchRejected("patch root must be an existing, non-symlink directory")
    found: set[str] = set()
    for path in root.rglob("*"):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise PatchRejected(f"symlinks are forbidden in patch output: {relative}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise PatchRejected(f"special filesystem entries are forbidden: {relative}")
        found.add(relative)
    return found


def validate_patch_manifest(
    manifest: dict[str, Any],
    patch_root: Path,
    expected_base_sha: str,
    allowed_paths: list[str],
    max_files: int = 50,
    max_file_bytes: int = 256_000,
    max_total_bytes: int = 2_000_000,
) -> dict[str, Any]:
    if not isinstance(manifest, dict):
        raise PatchRejected("manifest root must be an object")
    if manifest.get("schema_version") != "1.0":
        raise PatchRejected("unsupported patch manifest schema_version")
    if not isinstance(expected_base_sha, str) or not SHA_PATTERN.fullmatch(expected_base_sha):
        raise PatchRejected("expected base SHA must be a 40- or 64-character lowercase hex revision")
    if manifest.get("base_sha") != expected_base_sha:
        raise PatchRejected("patch base SHA does not match the approved immutable base revision")

    if not isinstance(allowed_paths, list) or not allowed_paths:
        raise PatchRejected("task allowlist must be a non-empty list")
    normalized_allowlist: list[str] = []
    for allowed in allowed_paths:
        if not isinstance(allowed, str) or not allowed:
            raise PatchRejected("task allowlist entries must be non-empty relative paths")
        is_directory = allowed.endswith("/")
        normalized = _safe_relative_path(allowed[:-1] if is_directory else allowed)
        normalized_allowlist.append(normalized + ("/" if is_directory else ""))
    if len(normalized_allowlist) != len(set(normalized_allowlist)):
        raise PatchRejected("task allowlist contains duplicate paths")
    allowed_paths = normalized_allowlist

    if min(max_files, max_file_bytes, max_total_bytes) < 1:
        raise PatchRejected("patch size limits must all be positive integers")

    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise PatchRejected("manifest files must be a non-empty list")
    if len(entries) > max_files:
        raise PatchRejected(f"patch contains more than the maximum of {max_files} files")

    seen: set[str] = set()
    casefolded: set[str] = set()
    expected_output_files: set[str] = set()
    total_bytes = 0
    accepted: list[dict[str, Any]] = []

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise PatchRejected(f"files[{index}] must be an object")
        path = _safe_relative_path(entry.get("path"))
        if path in seen:
            raise PatchRejected(f"duplicate file path: {path}")
        seen.add(path)
        folded = path.casefold()
        if folded in casefolded:
            raise PatchRejected(f"case-insensitive path collision: {path}")
        casefolded.add(folded)
        if not _is_allowed(path, allowed_paths):
            raise PatchRejected(f"path is outside the task allowlist: {path}")
        if _is_protected(path):
            raise PatchRejected(f"protected file path requires separate human approval: {path}")

        operation = entry.get("operation")
        if operation not in {"add", "modify", "delete"}:
            raise PatchRejected(f"unsupported operation for {path}")
        size = entry.get("size_bytes")
        if type(size) is not int or size < 0:
            raise PatchRejected(f"size_bytes must be a non-negative integer for {path}")

        if operation == "delete":
            if size != 0 or entry.get("sha256") not in {None, ""}:
                raise PatchRejected(f"delete entries must have size_bytes 0 and no output sha256: {path}")
            if (patch_root / path).exists() or (patch_root / path).is_symlink():
                raise PatchRejected(f"deleted file must not be present in patch output: {path}")
            accepted.append({"path": path, "operation": operation, "size_bytes": 0, "sha256": None})
            continue

        digest = entry.get("sha256")
        if not isinstance(digest, str) or not FILE_SHA_PATTERN.fullmatch(digest):
            raise PatchRejected(f"sha256 must be a lowercase SHA-256 digest for {path}")
        if size > max_file_bytes:
            raise PatchRejected(f"file exceeds the {max_file_bytes}-byte limit: {path}")
        total_bytes += size
        if total_bytes > max_total_bytes:
            raise PatchRejected(f"patch exceeds the {max_total_bytes}-byte aggregate limit")

        output_path = patch_root / path
        current = patch_root
        for segment in PurePosixPath(path).parts:
            current = current / segment
            if current.is_symlink():
                raise PatchRejected(f"symlink traversal is forbidden: {path}")
        if not output_path.exists() or not output_path.is_file():
            raise PatchRejected(f"patch output file is missing or not a regular file: {path}")
        content = output_path.read_bytes()
        if len(content) != size:
            raise PatchRejected(f"file size does not match manifest: {path}")
        actual_digest = hashlib.sha256(content).hexdigest()
        if actual_digest != digest:
            raise PatchRejected(f"file SHA-256 does not match manifest: {path}")
        expected_output_files.add(path)
        accepted.append({
            "path": path,
            "operation": operation,
            "size_bytes": size,
            "sha256": digest,
        })

    actual_output_files = _scan_patch_root(patch_root)
    if actual_output_files != expected_output_files:
        unlisted = sorted(actual_output_files - expected_output_files)
        missing = sorted(expected_output_files - actual_output_files)
        raise PatchRejected(f"patch output does not match manifest; unlisted={unlisted}, missing={missing}")

    return {
        "schema_version": "1.0",
        "status": "passed",
        "base_sha": expected_base_sha,
        "files_checked": len(accepted),
        "output_files_checked": len(expected_output_files),
        "total_output_bytes": total_bytes,
        "files": accepted,
        "limitations": [
            "This gate validates a manifest and patch output snapshot; it does not apply the patch.",
            "It does not prove code correctness, test results, or sandbox isolation.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, type=Path, help="Validated task contract JSON")
    parser.add_argument("--manifest", required=True, type=Path, help="Patch manifest JSON")
    parser.add_argument("--patch-root", required=True, type=Path, help="Directory containing only changed output files")
    parser.add_argument("--expected-base-sha", required=True, help="Immutable approved base commit SHA")
    parser.add_argument("--output", type=Path, help="Optional JSON report path")
    parser.add_argument("--max-files", type=int, default=50)
    parser.add_argument("--max-file-bytes", type=int, default=256_000)
    parser.add_argument("--max-total-bytes", type=int, default=2_000_000)
    args = parser.parse_args()

    contract_errors = validate_contract(args.contract)
    if contract_errors:
        for error in contract_errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        contract = json.loads(args.contract.read_text(encoding="utf-8"))
        report = validate_patch_manifest(
            manifest,
            args.patch_root,
            args.expected_base_sha,
            contract["allowed_paths"],
            args.max_files,
            args.max_file_bytes,
            args.max_total_bytes,
        )
    except (OSError, json.JSONDecodeError, KeyError, TypeError, PatchRejected) as exc:
        report = {
            "schema_version": "1.0",
            "status": "failed",
            "rejection_reason": str(exc),
        }
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
