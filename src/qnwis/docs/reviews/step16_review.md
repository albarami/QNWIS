# Step 16 Coordination Hardening Review

## Overview

Step 16 focuses on hardening the multi‑agent coordination layer. Key goals were safety (strict intent/method controls), determinism (predictable wave orchestration and merge outcomes), and testability (explicit traces and unit coverage). The work also introduces timestamp range tracking, timeout awareness, and new sanitisation features to align with enterprise review checkpoints.

## Highlights

- **Spec normalisation & validation**
  - Every `AgentCallSpec` now resolves against the registry before planning; mismatched methods are rejected.
  - Optional `alias` and `depends_on` hints support dependency-aware sequential waves with duplicate alias detection.

- **Execution hardening**
  - Wave runner enforces per-agent and total time budgets, emitting structured warnings and placeholder results when budgets are exceeded.
  - Sequential waves honour dependency failures, skipping downstream work with auditable traces.
  - Execution traces now follow the {intent, agent, method, elapsed_ms, attempt, warnings, error?} envelope and flow into final results for audit.

- **Merge determinism**
  - Freshness metadata retains `min_timestamp`/`max_timestamp` ranges while preserving the latest `age_days`.
  - Warnings and sections run through a dedicated PII masker covering proper names, email addresses, and long IDs.
  - Agent traces, warnings, citations, and sections have explicit dedupe/sort rules baked into the merge contract.

- **Tests & coverage**
  - New unit tests simulate dependency skips, timeout cascades, freshness ranges, PII masking, and trace dedupe behaviour.
  - Existing Step 14/15 scenarios remain intact; only coordination fixtures required updates.

## Coordination Mode Flows

```mermaid
flowchart LR
    subgraph Single
        A[Intents] --> B[Registry resolve]
        B --> C[Execute agent]
        C --> D[Merge partials]
    end

    subgraph Parallel
        P[Intents] -->|Chunk by max_parallel| Q[Create waves]
        Q --> R[Validate registry + aliases]
        R --> S[Execute wave sequentially (deterministic ordering)]
        S --> T[Per-wave metrics + traces]
        T --> D
    end

    subgraph Sequential w/ dependencies
        X[Intents + depends_on] --> Y[Validate DAG order]
        Y --> Z[Wave 1 execute]
        Z --> AA{Result ok?}
        AA -- No --> AB[Mark alias failed]
        AB --> AC[Skip dependent waves w/ warnings]
        AA -- Yes --> AD[Proceed to next wave]
        AD --> T
    end

    D[merge_results()]
```

## Merge Policy Cheat Sheet

| Component        | Rule / Dedup Criterion                             | Deterministic Ordering                          |
|------------------|----------------------------------------------------|-------------------------------------------------|
| Sections         | First occurrence of (title, body prefix)           | Canonical section order (Executive → Warnings)  |
| Citations        | Unique `(dataset_id, query_id)` pairs               | Sorted by `(dataset_id, query_id)`              |
| Freshness        | Track min/max timestamps per source                | `last_updated = max_ts`, expose `min/max`       |
| Warnings         | Strip/trim, mask PII, unique strings                | Encounter order post masking                    |
| Agent Traces     | Unique `(intent, agent, method, attempt)` tuples   | Sorted by `(intent, method, attempt, elapsed)`  |
| Reproducibility  | Aggregate method names + timestamped union         | Timestamped with merge time                     |

## Safety & Compliance Notes

- Placeholder results are generated for dependency skips and timeout breaches to keep audit trails intact.
- `mask_pii()` now covers proper names, email addresses, and long numeric identifiers across sections and warnings.
- Total execution interruptions propagate warnings back into the triggering trace and mark success states accordingly.

## Test Coverage

- `python -m pytest tests/unit/orchestration/test_coordination.py`
  - Exercises planning validation, dependency skipping, timeout handling, freshness ranges, PII masking, and trace merging.

## Next Steps

- Extend integration tests to cover multi-wave timeout cascades under LangGraph orchestration.
- Consider exposing dependency outcome summaries via the public API for easier client telemetry.
