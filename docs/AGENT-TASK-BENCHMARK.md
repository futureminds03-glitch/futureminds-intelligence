# Agent task benchmark — first pilot

## Why task contracts exist

An agent task contract records what an AI coding agent was asked to do, the boundaries it was expected to respect, and the evidence required to judge its completion claim. It is the evaluation target, not an execution engine.

The first reference contract is `benchmarks/task-contracts/notely-branded-share-image.v1.json`. It is based on a previously discussed Notely sharing requirement and is a benchmark fixture only. It does not authorize changes to the Notely repository or a production deployment.

## How the pilot works

1. A human selects a task and explicitly identifies the target repository and base revision at execution time.
2. The agent receives the task instruction and operates only on an isolated branch/worktree.
3. The agent opens a pull request; it cannot deploy or mutate production.
4. Trusted CI and independent GitHub collection record the evaluated commit, changed files and completed checks.
5. The evaluator compares that evidence with the contract's acceptance criteria.
6. The report preserves passed, failed and missing evidence separately. Missing evidence is never a pass.

## Contract contents

- Task identity and version: stable benchmark identity.
- Objective and agent instruction: what the agent is expected to deliver.
- Execution policy: branch/PR-only, no production deployment, no production data mutation, and no secret exposure.
- Allowed paths and forbidden actions: scope boundaries.
- Required evidence and acceptance criteria: explicit, machine-checkable completion conditions.

## Run the reference benchmark

The task contract can be evaluated against a structured evidence JSON document:

```bash
python -m scripts.run_task_eval --contract benchmarks/task-contracts/notely-branded-share-image.v1.json --evidence benchmarks/fixtures/notely-share-image-evidence-passed.json --output task-evaluation-report.json
```

Three synthetic evidence fixtures demonstrate the evaluator's status behavior:

- `notely-share-image-evidence-passed.json` — every required evidence assertion is satisfied.
- `notely-share-image-evidence-failed.json` — contradictory CI/test evidence produces `failed`.
- `notely-share-image-evidence-missing.json` — missing required evidence produces `blocked`.

These fixtures validate grading behavior only. They are not claims that an agent performed the task or that the Notely feature exists.

## Security boundaries

A contract is data. The validator parses and checks its structure; it never executes instructions, shell commands, scripts, or paths from the contract. A future executor must separately enforce repository allowlists, branch isolation, least-privilege credentials, network policy, resource limits, and human approval before any release.

The pilot does not yet launch coding agents, create sandboxes, authenticate screenshots/browser state, or grant write access to product repositories. A passing contract validation means only that the benchmark definition is structurally valid.

## Acceptance for this milestone

- The sample contract is valid and versioned.
- Unsafe execution-policy values and path traversal are rejected.
- Acceptance criteria must reference declared evidence keys and supported deterministic operators.
- CI runs the contract validator and its unit tests.

## Collecting evidence from a real pull request

The read-only adapter can collect evidence for a specific GitHub pull request:

```bash
export GITHUB_TOKEN="<read-only GitHub token>"
python -m scripts.collect_pr_task_evidence \
  --repository owner/repository \
  --pull-request 123 \
  --output evidence/pr-task-evidence.json

python -m scripts.run_task_eval \
  --contract benchmarks/task-contracts/notely-branded-share-image.v1.json \
  --evidence evidence/pr-task-evidence.json \
  --output evidence/task-evaluation-report.json
```

The token should be fine-grained and limited to the target repository with Metadata: read, Pull requests: read and Checks: read. The adapter does not need write permissions. It fetches the pull request head commit, changed files and check runs directly from GitHub. It refuses incomplete or potentially truncated file/check inventories.

CI is considered successful only when all observed check runs have completed successfully. Unit-test and feature-specific evidence are only populated when matching completed check runs exist. A pending check or absent feature-specific test remains missing and therefore blocks the task evaluation. A failed check remains a failure.

The optional `## Agent completion summary` section in the PR body is treated as an agent-authored claim, not independent proof. The report preserves that distinction. The adapter does not run the submitted code, validate browser behavior, or prove a feature works merely because CI is green.
