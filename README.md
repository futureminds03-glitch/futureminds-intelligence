# FutureMinds Intelligence

**Evidence, not promises.**

FutureMinds Intelligence is an independent evaluation and evidence platform for:
1. AI agents used to build and operate FutureMinds products.
2. AI capabilities delivered inside FutureMinds products and services.

It treats an agent's completion statement as a claim. Outcomes are established from independently observable evidence: requirements, source changes, test results, tool traces, application state, deployment identity, and production checks.

> **Current status:** foundation repository and proposed architecture. This is an internal engineering project, not a production-ready product. The framework's architecture and roadmap remain proposed until validated and approved.

## First milestone

Build a small, deterministic evaluation runner that can:
- load a versioned evaluation case;
- execute a controlled task adapter;
- collect structured evidence;
- grade the outcome against explicit assertions;
- report `passed`, `failed`, `blocked`, or `not_run`;
- preserve the run and evidence so another person can inspect the result.

The first pilot will test whether an AI coding agent's completion claim is supported by repository and test evidence. No model-based judge is required for the first milestone.

## Architecture direction

A modular monolith first; no microservices until measured needs justify them.

- **Evaluation core:** case schema, runner, lifecycle and deterministic graders.
- **Adapters:** GitHub, CI, browser and product-specific integrations behind narrow interfaces.
- **Evidence:** immutable run manifest and references to source artifacts; redact secrets.
- **Storage:** PostgreSQL for structured records; object storage only when artifacts need it.
- **Console:** human-readable run and evidence inspection.
- **Automation:** GitHub Actions for CI; deployment is deliberately out of scope for the initial milestone.

## Repository map

- `docs/PRODUCT.md` — product purpose, users, boundaries and success criteria.
- `docs/ARCHITECTURE.md` — system boundaries and initial technical design.
- `docs/ROADMAP.md` — staged delivery plan and acceptance gates.
- `docs/SECURITY.md` — security baseline and threat model.
- `docs/ADR/` — architecture decision records.
- `evals/` — versioned evaluation cases and fixtures.
- `packages/` — application and engine code (introduced incrementally).
- `.github/workflows/` — CI workflows.

## Governing principles

1. Evidence over assertions.
2. Missing evidence is not a pass.
3. Implementers do not solely verify their own critical work.
4. Mandatory security checks are hard gates, not score components.
5. Preserve failures as regression cases.
6. Separate agent evaluation from AI product evaluation even when they share infrastructure.
7. Do not store secrets or unnecessary personal data in traces.
8. Respect free-tier constraints; no paid services or upgrades without explicit approval.

## Development

The repository is being bootstrapped in stages. The initial deterministic vertical slice is implemented in Python using only the standard library. Validate cases with `python scripts/validate_evals.py`, run tests with `python -m unittest discover -s tests -v`, and evaluate evidence with:

```bash
python -m scripts.run_eval --case evals/cases/agent-claim-evidence.v1.json --evidence evals/fixtures/evidence-passed.json
```

The runner accepts JSON evidence, grades only the declared deterministic operators, and emits an inspectable JSON report. It does not authenticate evidence origin or execute agents. Avoid introducing a large framework or vendor dependency before it earns its place.

## Status vocabulary

- `passed`: required checks ran and all passed with attached evidence.
- `failed`: one or more required checks ran and failed.
- `blocked`: execution could not proceed because of a recorded blocker.
- `not_run`: no valid execution evidence exists.
- `not_applicable`: a documented rule excludes the check.
- `partially_verified`: some evidence exists, but the complete acceptance set is not satisfied.

A green summary never overrides a failed mandatory security or release gate.
