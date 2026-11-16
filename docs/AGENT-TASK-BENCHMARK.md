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

## Security boundaries

A contract is data. The validator parses and checks its structure; it never executes instructions, shell commands, scripts, or paths from the contract. A future executor must separately enforce repository allowlists, branch isolation, least-privilege credentials, network policy, resource limits, and human approval before any release.

The pilot does not yet launch coding agents, create sandboxes, authenticate screenshots/browser state, or grant write access to product repositories. A passing contract validation means only that the benchmark definition is structurally valid.

## Acceptance for this milestone

- The sample contract is valid and versioned.
- Unsafe execution-policy values and path traversal are rejected.
- Acceptance criteria must reference declared evidence keys and supported deterministic operators.
- CI runs the contract validator and its unit tests.
