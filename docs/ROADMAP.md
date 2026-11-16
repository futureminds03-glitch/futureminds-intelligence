# Delivery roadmap

Each phase has an acceptance gate. Do not mark a phase complete from implementation claims alone.

## Phase 0 — Foundation (current)

- [x] Establish independent repository.
- [x] Define mission, boundaries and initial architecture.
- [x] Add versioned evaluation case format and validator.
- [x] Add deterministic grader and run report.
- [x] Add unit tests and CI validation.
- [x] Verify CI on a pull request.

**Exit gate:** a reproducible local and CI run can pass and fail deterministically, with evidence attached.

## Phase 1 — Agent evaluation pilot

- [x] Define a versioned, bounded coding-task contract with explicit acceptance criteria and execution restrictions.
- [x] Add deterministic contract validation and a task-evaluation CLI that reuses the shared grading engine.
- [x] Add synthetic passing, failing and missing-evidence fixtures to prove status behavior.
- [x] Implement a read-only GitHub PR adapter for authenticated revision, changed-file inventory and completed check evidence (mocked API tests pass).
- [ ] Run the adapter against an actual target-product PR and inspect the resulting evidence report.
- [ ] Compare a real agent completion claim with independently retrieved evidence.
- [ ] Preserve confirmed real-world failures as regression cases.
- [ ] Measure false passes, false failures and human review effort.

**Exit gate:** demonstrate a meaningful unsupported claim or regression caught by the evaluator using independently authenticated evidence from a real bounded agent task. Synthetic fixtures do not satisfy this gate.

## Phase 2 — CI and regression intelligence

- [x] Propose and document the isolated agent execution trust zones, patch gate, credential separation and rollout gates. This is a design only; no sandbox or agent execution is enabled.
- [x] Implement Gate A offline patch manifest validation with adversarial tests for base-SHA mismatch, path traversal, allowlist escape, symlinks, protected paths, unlisted files, hash/size mismatch and path collisions.
- [ ] Prove atomic patch application to a clean checkout of the approved base revision; the current validator does not apply patches.

- Integrate selected repositories through least-privilege GitHub access.
- Run deterministic evaluations on pull requests.
- Store historical results and regression links.
- Handle flaky checks explicitly; never silently retry into a pass.

## Phase 3 — Release intelligence

- Verify build and deployment terminal states.
- Verify deployed commit identity matches the approved source revision.
- Run post-deployment smoke tests and record rollback readiness.
- Keep deployment approval separate from evaluation.

## Phase 4 — AI product evaluation

- Create separate customer-facing AI benchmark datasets.
- Add groundedness, task completion, safety, privacy and UX checks.
- Compare model/prompt/config versions against fixed datasets.
- Add human review for subjective or high-impact judgments.

## Phase 5 — Console and governance

- Add run explorer, evidence viewer, history and trends.
- Add role-based access, audit trail, retention and policy management.
- Add meta-evaluation of grader quality and benchmark coverage.

## Deferred

Commercial SaaS, billing, broad multi-tenancy, autonomous release authority and expensive hosted evaluation infrastructure remain deferred pending demonstrated internal value and explicit product decisions.
