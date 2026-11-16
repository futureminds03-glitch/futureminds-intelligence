# Disposable sandbox smoke test

**Status: smoke-test workflow implemented. This is not authorization to run coding agents.**

## What the workflow proves

The `.github/workflows/agent-sandbox-smoke.yml` workflow runs only after the trusted default-branch workflow named `Evaluation foundation checks` completes successfully. It does not check out or execute the triggering pull request's source code. It requests only the GitHub `statuses: write` permission so a trusted post-run step can publish a pass/fail status against the triggering commit. The ephemeral token is used only by that trusted status step after the container exits; it is never passed to the container.

The job runs on a disposable GitHub-hosted Linux runner and starts a pinned BusyBox image by immutable amd64 manifest digest. Inside the container it applies:

- No network: Docker `--network none`.
- Read-only root filesystem: `--read-only`.
- No Linux capabilities: `--cap-drop ALL`.
- No privilege escalation: `no-new-privileges`.
- Non-root UID/GID 65534.
- Process limit: 32.
- Memory limit: 128 MiB.
- CPU limit: 0.5 CPU.
- A read-only bind mount containing only a synthetic instruction file.
- Separate bounded tmpfs mounts for scratch and output.
- No host paths, credentials, source repository, Docker socket or production data are mounted.

The container verifies that it is non-root, the root filesystem is mounted read-only, effective capabilities are zero, the input mount cannot be modified, no sensitive environment-variable names are present, and an outbound network request fails. It writes one harmless proof file to the output tmpfs and prints its SHA-256.

## Why this is not yet a coding-agent sandbox

This is a controlled container inside an ephemeral CI virtual machine. Containers share the host kernel; this test does not establish resistance to kernel/container escapes, provide a dedicated microVM boundary, or prove network policy against every possible protocol. The test executes only a harmless synthetic shell command, not model-generated code.

Before real agent code is allowed, FutureMinds must evaluate a stronger per-task isolation boundary (for example, a disposable microVM or equivalent), verify host/guest separation, restrict and audit egress, verify cleanup, and prove that no runner credentials or secrets can be reached after a sandbox escape. A container smoke pass is not that proof.

## Trigger and trust model

The workflow uses `workflow_run` and is defined on the default branch. It deliberately does not check out `workflow_run.head_sha`, execute PR code, or request write permissions. This preserves the rule that privileged follow-up workflows must never execute untrusted PR-head code.

## Evidence

The smoke job's GitHub Actions logs must contain `SANDBOX_PROOF=passed` and the output SHA-256. The trusted post-run step publishes a `FutureMinds Intelligence / Disposable sandbox` commit status. A completed job is evidence only for the controls explicitly tested above. It is not evidence of a fully secure agent execution environment.

## Separate task-evidence job

The same trusted workflow also has a separate `evaluate-agent-task` job on its own ephemeral runner. That job checks out only the default branch, retrieves PR metadata/checks through GitHub's read-only API, grades the PR against the versioned task contract, and publishes a separate evidence status/artifact. It never shares its token with the sandbox container. The sandbox job and evidence job are separate jobs; credentials used by the evidence collector do not enter the container's environment or mounts.
