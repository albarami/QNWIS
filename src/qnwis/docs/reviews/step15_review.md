# Step 15 Routing Review

## Hardening Summary
- Classifier now enforces deterministic ordering (`score desc`, `intent asc`), applies a fixed tie delta of 0.05, and records score/latency metadata for observability.
- Default horizon of 36 months is injected when queries omit timing, with reasons logged and downstream YAML-driven prefetch using the resolved window.
- Router rejects unregistered intents with explicit allowlist guidance, emits structured metadata, and returns a single clarifying question when confidence < 0.55.
- Ambiguity handling keeps the top two intents (when within delta) in parallel mode while retaining the primary route for Step-14 graph compatibility.
- CLI logs the query snippet for `--query` runs and keeps JSON output pretty-printed for auditability.

## Determinism, Rules, and Thresholds
- `DEFAULT_HORIZON_MONTHS = 36` applied inside `extract_entities`; reason `"Applied default time horizon of 36 months"` accompanies classifications that rely on it.
- Tie handler triggers when `abs(score_1 - score_2) <= 0.05`, flagging `tie_within_threshold=True`, adding a deterministic note, and forcing router mode `parallel` with exactly two agents.
- Confidence gate stays at `min_confidence=0.55`; on failure router returns `Clarification required ... "Could you clarify the primary labour market metric or sector for "<query snippet>"?"`.
- Classification metadata logged via `logger.info` includes `intent_scores`, `complexity`, `confidence`, and `elapsed_ms`, all echoed into `routing` metadata for later nodes.
- Pydantic validators guarantee `0 <= confidence <= 1`, tie metadata consistency, and `RoutingDecision` mode/agent-count alignment.

## Prefetch Policy (intent_catalog.yml)
| Intent | Prefetch Hints |
| --- | --- |
| `pattern.anomalies` | `get_retention_by_company(sectors, months)`; `get_turnover_stats(sectors)` |
| `pattern.correlation` | `get_multi_metric_data(metrics, sectors, horizon_months)` |
| `pattern.root_causes` | `get_multi_metric_data(metrics, sectors, horizon_months)` |
| `pattern.best_practices` | `get_multi_metric_data(sectors, metrics, horizon_months)` |
| `strategy.gcc_benchmark` | `get_gcc_comparison(metrics, min_countries=4)` |
| `strategy.talent_competition` | `get_multi_metric_data(metrics, sectors, horizon_months)` |
| `strategy.vision2030` | `get_qatarization_progress(sectors, horizon_months)` |

Prefetch entries honour `when_metrics_any`, `require_sectors`, `require_metrics`, and reuse the default 36-month horizon when no explicit window is supplied.

## Intent -> Agent Mapping (Step-14 Registry)
| Intent | Agent Method |
| --- | --- |
| `pattern.anomalies` | `PatternDetectiveAgent.detect_anomalous_retention` |
| `pattern.correlation` | `PatternDetectiveAgent.find_correlations` |
| `pattern.root_causes` | `PatternDetectiveAgent.identify_root_causes` |
| `pattern.best_practices` | `PatternDetectiveAgent.best_practices` |
| `strategy.gcc_benchmark` | `NationalStrategyAgent.gcc_benchmark` |
| `strategy.talent_competition` | `NationalStrategyAgent.talent_competition_assessment` |
| `strategy.vision2030` | `NationalStrategyAgent.vision2030_alignment` |

## Validation
- Unit: `python -m pytest tests/unit/test_classifier.py tests/unit/test_classifier_entities.py tests/unit/test_router_classification.py`
- All new behaviour covered: tie-handling, default horizon parsing (incl. `Qn YYYY` and bare year), clarifying question flow, metadata population, and YAML-based prefetch resolution.
