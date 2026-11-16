# Product definition

## Mission

Give FutureMinds an independent, inspectable way to determine whether AI agents and AI-powered product features meet explicit requirements safely and reliably.

## Two evaluation domains

### Agent Intelligence
Evaluate agents that perform work: coding, research, operations, tool use and multi-step workflows. The unit under test is an agent execution against a task contract in a controlled environment.

### AI Product Intelligence
Evaluate AI capabilities exposed to customers: shopping assistants, support agents, retrieval, content generation and other model-backed workflows. The unit under test is a product behaviour against a versioned scenario and expected outcome.

These domains share infrastructure (cases, runners, graders, evidence and reporting) but must not share assumptions, datasets, policies or pass thresholds by default.

## Initial user

The first user is the FutureMinds engineering/product team. The initial use case is internal verification of AI-assisted engineering work. External multi-tenant SaaS, billing, customer onboarding and public APIs are explicitly out of scope for the first milestone.

## Non-goals for the first milestone

- No autonomous production deployment or release approval.
- No model judge as the sole grader.
- No broad agent orchestration framework.
- No multi-tenant SaaS or billing.
- No collection of raw secrets, credentials or unnecessary personal data.
- No claim that a score proves general intelligence or guarantees safety.

## Product requirements

1. Every evaluation has a stable case ID and version.
2. Acceptance criteria are explicit and machine-checkable where possible.
3. Every run has a unique ID, timestamps, subject/version, status and evidence references.
4. A run cannot pass when a required check did not execute or its evidence is missing.
5. Failed cases can be retained and replayed as regression tests.
6. Reports distinguish observed facts, grader conclusions and unresolved uncertainty.
7. Evaluation code and datasets are version controlled.
8. Security/privacy gates are independently enforceable.

## Success criteria for the first pilot

- A deterministic evaluation case can be validated and executed locally and in GitHub Actions.
- Invalid case definitions fail CI with actionable errors.
- A passing result requires all required assertions to be present and pass.
- A failing result preserves which assertion failed and why.
- A reviewer can reproduce the result from the repository revision and run output.
- The system demonstrates at least one case where an unsupported completion claim is not accepted as proof.

## Product status

This is a proposed product definition for the internal MVP. Commercial packaging and formal policy ratification are future decisions.
