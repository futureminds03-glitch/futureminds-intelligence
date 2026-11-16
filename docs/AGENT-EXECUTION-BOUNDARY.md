# Isolated agent execution boundary

**Status: proposed security architecture. No agent execution is enabled by this document.**

## 1. Security objective

Allow a coding agent to work on a narrowly scoped task without giving it credentials, direct write access to a product repository, access to production systems, or a path to deploy. Treat all agent output as untrusted until a separate trusted controller validates it and independent CI evaluates the resulting pull request.

The system must remain safe if the agent prompt, generated code, dependency, tool response, or task output is malicious.

## 2. Trust zones

| Zone | Responsibility | Trust |
|---|---|---|
| Orchestrator | Validates task contract, selects an approved repository and immutable base SHA, creates a run record | Trusted control plane |
| Agent sandbox | Reads a source snapshot, edits files, runs bounded local tools, emits a patch and logs | Untrusted execution zone |
| Patch gate | Validates patch format, file paths, size, symlinks, binary files and allowed-path policy | Trusted controller |
| GitHub publisher | Uses a short-lived, narrowly scoped credential to create a branch and pull request | Privileged trusted zone |
| GitHub CI | Builds/tests the proposed change with read-only permissions and no production secrets | Independent verification zone |
| Evaluator | Compares authenticated GitHub evidence and agent claims with the task contract | Trusted evaluation zone |
| Human release gate | Reviews and explicitly approves merge/deployment | Human-controlled |

The agent sandbox must never share a process, filesystem, credential store, network namespace or writable volume with the orchestrator, patch gate or publisher.

## 3. Required execution sequence

1. Validate the task contract. Reject unsupported schema versions, unsafe execution policy, unapproved repository, empty acceptance criteria and path traversal.
2. Resolve the target repository from an explicit allowlist. Record the exact repository ID, base branch and immutable base commit SHA.
3. Create a fresh, disposable sandbox for this single task. Never reuse a sandbox between tasks or tenants.
4. Provide a source snapshot without .git, credentials, environment files, production data, deployment configuration secrets or unrelated repositories.
5. Give the agent only the task instruction, source snapshot, allowed-path list and bounded tool interface.
6. Agent edits the snapshot and emits a patch bundle, a machine-readable file manifest, tool-call log and completion summary.
7. Destroy the sandbox before privileged publishing begins. Preserve only bounded output artifacts after scanning them for secrets and unsafe file types.
8. In the trusted patch gate, verify the patch applies to the recorded base SHA; reject paths outside the allowlist, absolute paths, .., symlinks, submodules, unexpected binary files, oversized output and modifications to protected workflow/security files unless separately approved.
9. The trusted publisher applies the validated patch to a new branch and opens a pull request. The publisher credential is never mounted in or sent to the agent sandbox.
10. GitHub CI independently builds and tests the PR with read-only permissions, no production secrets and no production deployment.
11. The evidence adapter retrieves the PR head SHA, complete changed-file inventory and completed checks from GitHub. The evaluator compares these facts with the contract.
12. A human reviews the PR and explicitly approves merge. Deployment remains a separate explicit release action.

## 4. Non-negotiable sandbox controls

### Isolation
- One disposable VM or equivalent strong isolation boundary per task.
- Non-root execution; no privileged container mode, host PID/network namespaces, Docker socket, host mounts or device access.
- CPU, memory, process-count, disk, wall-clock and output-size limits.
- Automatic destruction after success, failure, timeout or cancellation.
- No persistence between runs.

### Credentials and data
- No GitHub write token, cloud credentials, Supabase keys, Vercel tokens, SSH keys, browser cookies, production environment variables or customer data in the sandbox.
- Do not expose the publisher credential to model context, tool output, process environment or mounted files.
- Use short-lived least-privilege credentials only in the trusted publisher.
- Never let an agent choose its own repository, base SHA, permissions or credential scope.

### Network
- Default deny outbound network access from the sandbox.
- If dependency retrieval is required, use a separate controlled proxy or immutable dependency cache with an explicit domain allowlist.
- Deny access to cloud metadata endpoints, localhost control-plane services, private network ranges and internal DNS.
- Do not rely on prompt instructions as a network security control.

### Filesystem and patch
- Mount the initial source snapshot read-only; provide a separate bounded writable work directory.
- Do not include .git, .env files, secrets, production data or unrelated workspaces.
- Treat every generated file, patch, symlink, archive and log as hostile input.
- Apply patches only after path normalization and policy checks; reject traversal and ambiguous paths.
- Keep protected workflow, dependency, authentication and security files outside normal task allowlists unless a human approves the exception.

### CI and release
- PR workflows use explicit least-privilege permissions and no production secrets.
- Never execute privileged workflow_run code from an untrusted PR head.
- Do not deploy from an agent sandbox or from an unreviewed PR.
- Merge and release are separate gates; a green test suite is not release approval.

## 5. Patch gate policy

The patch gate must validate at least:
- Patch references the expected immutable base SHA.
- Every changed path resolves within the repository and the task's allowed-path set.
- No absolute paths, traversal segments, symlinks, submodules or path collisions.
- No unexpected changes to workflows, CODEOWNERS, dependency lockfiles, auth, permissions, migrations, deployment configuration or security policy.
- File count, individual file size, aggregate patch size and archive expansion are within fixed limits.
- No credential-like material or private key blocks in patch content or logs.
- Patch applies cleanly to a fresh checkout of the expected base revision.
- A complete hash manifest is recorded for all accepted outputs.

A rejected patch must not be partially applied. The patch gate is atomic: accept the entire validated patch or reject it.

## 6. Audit record

Every run should record:
- Task contract ID/version and its content hash.
- Repository ID, base branch and immutable base SHA.
- Sandbox image digest, policy version and start/end timestamps.
- Agent/model identifier and tool configuration, without recording secrets.
- Tool-call log and bounded output hashes.
- Patch hash, accepted/rejected decision and rejection reasons.
- Publisher identity, created branch and PR number.
- CI run IDs, completed check conclusions and evidence artifact hashes.
- Evaluator report, human reviewer and final disposition.

Logs must not contain secrets or unrestricted customer content. Apply retention and access controls to audit records.

## 7. Threat model and required defenses

| Threat | Required defense |
|---|---|
| Prompt injection in source files or issue text | Treat repository content as untrusted data; sandbox cannot access control-plane tools or credentials |
| Malicious generated code | Disposable isolated VM, no secrets, default-deny network, resource limits |
| Path traversal or symlink escape in patch | Canonical path validation, reject symlinks, atomic patch gate |
| Secret exfiltration | No secrets in sandbox, restricted egress, output secret scanning |
| Supply-chain compromise | Pinned sandbox image and action versions, controlled dependency cache, provenance |
| Privilege escalation | Non-root sandbox, no host mounts/socket, separate publisher identity |
| Fake completion claims | Agent summary is untrusted; use authenticated GitHub/CI evidence |
| CI self-verification or workflow_run abuse | Trusted default-branch collector; never checkout untrusted PR head in privileged workflows |
| Resource exhaustion | CPU/memory/disk/time/output quotas and automatic termination |
| Cross-task data leakage | Fresh isolated sandbox and clean source snapshot per task |
| Unauthorized release | No deploy credential in sandbox; separate human approval gate |

## 8. Rollout gates

### Gate A — Offline patch validation
- Implement and test patch manifest/path validation using synthetic patches.
- Prove traversal, symlink, protected-file and oversized-patch cases are rejected.
- No agent process or external sandbox provider.

### Gate B — Disposable sandbox proof
- Select a sandbox implementation only after verifying isolation, network controls, lifecycle and cost.
- Run a harmless synthetic task with no credentials and no network.
- Verify sandbox destruction and absence of persistent state.

### Gate C — Read-only real repository pilot
- Give the sandbox a public or explicitly approved source snapshot only.
- Agent can return a patch artifact but cannot push, open PRs, deploy or access secrets.
- Trusted controller validates and reports the patch without publishing.

### Gate D — Controlled PR publishing
- Add a trusted publisher with a short-lived, repository-scoped credential.
- Publish only validated patches to a task branch.
- Require CI and human PR review; keep production deployment disabled.

No later gate is implicitly authorized by passing an earlier gate.

## 9. Current implementation boundary

Implemented today:
- Versioned task contracts and structural validator.
- Deterministic evidence evaluator.
- Read-only GitHub evidence collectors for completed workflows and pull requests.
- CI tests for missing, failed and successful evidence.

Not implemented:
- Agent process execution.
- Sandbox provisioning or network isolation.
- Patch artifact format, validator or trusted publisher.
- Real target-product PR evaluation.
- Browser/UI behavior evaluation.
- Production deployment or automatic merge.

This document is a proposed engineering design. It does not grant permission to execute agents or access product repositories.
