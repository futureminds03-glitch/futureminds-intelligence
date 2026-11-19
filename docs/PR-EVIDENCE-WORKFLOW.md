# Automated pull-request task evidence workflow

**Status: implemented for the reference benchmark. It evaluates PR evidence; it does not execute coding agents.**

## Trigger

The task-evaluation job is integrated into the existing `Capture independent GitHub evidence` workflow. It runs after `Evaluation foundation checks`, resolves a same-repository PR by exact completed SHA, repository identity and `agent-task/` branch, and skips when no matching task PR exists. It checks out only the trusted default branch and never checks out or executes the triggering PR head.

## Evidence collection

The trusted workflow resolves the pull request by querying GitHub for the PR associated with the exact completed commit SHA, then calls `scripts/collect_pr_task_evidence.py` with a read-only GitHub token. It does not rely on a potentially empty PR list in the workflow-run event. The adapter retrieves:
- PR head commit SHA.
- Complete changed-file inventory.
- Check-run metadata and completed outcomes.
- An optional `## Agent completion summary` from the PR body, retained as an unverified claim.

The task evaluator compares these facts with `benchmarks/task-contracts/github-pr-evidence-demo.v1.json`. The contract requires a source revision, changed files, successful CI, successful unit-test checks and an agent completion summary. Missing evidence blocks the evaluation.

## Permissions and secrets

The workflow grants only:
- `contents: read` for trusted default-branch checkout.
- `pull-requests: read` and `checks: read` for evidence retrieval.
- `statuses: write` to publish the final evaluation state.

The ephemeral token is used only by trusted workflow steps. It is never passed to the triggering PR code, agent process or sandbox. Checkout uses `persist-credentials: false`.

## Outputs

The workflow uploads source evidence and the evaluation report as a 14-day artifact, writes a job summary, and publishes the commit status `FutureMinds Intelligence / Agent task evidence`.

A `passed` result means the evidence assertions in this reference contract passed. It does not prove UI behavior or that the agent ran in an isolated sandbox. The agent-authored PR summary is still only a claim.

## Reference task branch convention

Use `agent-task/<short-task-name>` for PRs that should enter this reference evidence pipeline. The workflow currently uses one generic benchmark contract for demonstration; task-specific contract selection and authenticated tool-trace evidence are future work.

The contract declares exact `required_ci_check_names`. Only those named checks contribute to the task's required CI/unit-test grade. This prevents the evidence collector's own in-progress check (and unrelated concurrent workflows) from contaminating its result. A missing or ambiguous required check remains blocked; the workflow does not silently broaden the allowlist.

The workflow publishes a separate `FutureMinds Intelligence / Agent task discovery` status so PR resolution failures are visible instead of silently skipping the final task-evidence status. A resolved PR begins as pending; missing eligibility is marked not applicable; resolution errors are surfaced for investigation.
