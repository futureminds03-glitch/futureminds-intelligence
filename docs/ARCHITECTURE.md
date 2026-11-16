# Architecture

## Guiding decision

Start with a modular monolith and a deterministic evaluation core. Add services only when measured scale, isolation or ownership requirements justify them.

## Logical flow

```text
Versioned Evaluation Case
          |
          v
     Case Validator
          |
          v
     Evaluation Runner <---- Subject Adapter (agent / product / CI)
          |
          v
     Evidence Collector
          |
          v
     Deterministic Graders
          |
          v
   Status + Run Manifest
          |
          v
    Human-readable Report
```

## Core concepts

- **Evaluation case:** versioned task contract, subject type, inputs, checks and expected evidence.
- **Run:** one execution of one case against one identified subject/version.
- **Evidence item:** a typed, timestamped observation with provenance and a content reference or safe summary.
- **Assertion:** a deterministic rule applied to evidence.
- **Grade:** outcome of an assertion, with explanation and evidence references.
- **Report:** a human-readable rendering of run status, grades, limitations and provenance.

## Initial implementation boundary

The first vertical slice validates evaluation-case JSON and executes deterministic assertions against a supplied evidence document. It does not yet execute arbitrary agents, clone repositories, run untrusted code, access production systems or call model APIs. This keeps the first implementation safe, cheap and testable.

## Proposed modules

- `packages/eval-core`: schemas, validation, run lifecycle, graders and status aggregation.
- `packages/adapters`: isolated connectors to GitHub, CI, browser and product systems.
- `apps/console`: inspection UI, added after the core proves useful.
- `evals/`: versioned cases and synthetic fixtures.
- `scripts/`: local developer and CI utilities.

The directory structure may evolve as implementation starts; boundaries matter more than package count.

## Evidence design

Evidence should record:
- source type and stable source identifier;
- observed timestamp (UTC);
- subject and revision identity where applicable;
- check/assertion identifier;
- outcome and concise explanation;
- artifact digest and protected artifact location when applicable.

Do not put secrets, access tokens, full environment dumps or unnecessary customer data in evidence. Prefer redacted summaries and hashes/references. Evidence integrity and provenance must be designed before accepting external submissions.

## Status aggregation

Statuses are not a numeric average:
- `failed` if any mandatory assertion fails;
- `blocked` if execution cannot continue due to a recorded blocker and no mandatory failure already determines failure;
- `not_run` if no valid execution occurred;
- `passed` only if every mandatory assertion ran, passed and has valid evidence;
- `partially_verified` if some checks ran but the required set is incomplete.

A mandatory security gate cannot be compensated for by passing functional checks.

## Data lifecycle

The first slice writes local JSON output and CI artifacts only. A database and object store are not prerequisites. When persistence is introduced, define retention, deletion, access controls, tenant boundaries and export before collecting sensitive traces.

## Deployment

No deployment is part of the initial foundation. Use GitHub Actions for validation. Any future hosted console must remain within approved free-tier constraints unless explicitly authorized.
