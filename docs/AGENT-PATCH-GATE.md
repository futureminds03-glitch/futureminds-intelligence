# Offline agent patch gate

**Status: implemented as a validator only. It does not apply patches or execute agents.**

## Purpose

The patch gate is the first executable part of the proposed agent isolation boundary. It accepts a machine-readable manifest and a directory containing only the changed output files. It checks that the proposed output is bound to the expected immutable base commit, stays inside the task's allowed paths, contains no symlinks or unlisted files, and respects strict size and protected-file rules.

It does not apply the patch, merge code, publish a branch, run tests or prove application correctness.

## Manifest format

Example:

```json
{
  "schema_version": "1.0",
  "base_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "files": [
    {
      "path": "src/feature.py",
      "operation": "add",
      "size_bytes": 15,
      "sha256": "<64-character lowercase SHA-256 of exact file bytes>"
    },
    {
      "path": "src/old-feature.py",
      "operation": "delete",
      "size_bytes": 0,
      "sha256": null
    }
  ]
}
```

The patch output directory contains only the new/modified file contents at their repository-relative paths. Deleted files are represented in the manifest and must not be present in the output directory.

## Run it

```bash
python -m scripts.validate_agent_patch \
  --contract benchmarks/task-contracts/notely-branded-share-image.v1.json \
  --manifest /path/to/patch-manifest.json \
  --patch-root /path/to/patch-output \
  --expected-base-sha <approved-40-or-64-character-commit-sha> \
  --output patch-validation-report.json
```

Defaults:
- Maximum 50 changed files.
- Maximum 256,000 bytes per output file.
- Maximum 2,000,000 bytes of aggregate output.

The task contract provides the path allowlist. The validator rejects absolute paths, Windows-style separators, traversal and ambiguous path segments, Git metadata paths, duplicate/case-colliding paths, symlinks, special files, unlisted output files, hash/size mismatches, protected files and base-revision mismatches.

Protected paths include workflows/actions, dependency manifests and lockfiles, authentication/security directories, migrations, deployment/infra files, and common credential/key file extensions. There is no override flag in this initial gate.

## Trust boundary

- Treat the manifest, file contents and logs as untrusted.
- The validator never executes content from the patch.
- A passing report means only that the patch output satisfies these structural and policy checks.
- The trusted controller must still apply the patch atomically to a clean checkout of the expected base revision and independently run CI.
- This is not a sandbox. It does not protect the host from a process that generated the files; agent execution remains disabled until a disposable isolation environment is separately implemented and verified.
