# Delivery roadmap

Each phase has an acceptance gate. Do not mark a phase complete from implementation claims alone.

## Phase 0 — Foundation (current)

- [x] Establish independent repository.
- [x] Define mission, boundaries and initial architecture.
- [ ] Add versioned evaluation case format and validator.
- [ ] Add deterministic grader and run report.
- [ ] Add unit tests and CI validation.
- [ ] Verify CI on a pull request.

**Exit gate:** a reproducible local and CI run can pass and fail deterministically, with evidence attached.

## Phase 1 — Agent evaluation pilot

- Define a narrow coding-task contract.
- Capture repository revision, changed-file inventory and test results.
- Compare agent completion claims with independently retrieved evidence.
- Preserve known failure cases.
- Measure false passes, false failures and human review effort.

**Exit gate:** demonstrate a meaningful unsupported claim or regression caught by the evaluator.

## Phase 2 — CI and regression intelligence

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
