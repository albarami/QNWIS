**Step 13 Review**

**Why it changed**
- `detect_anomalous_retention` now validates parameters, applies two-sided thresholds, explains “why flagged,” and logs params plus query IDs before execution (`src/qnwis/agents/pattern_detective.py:59`).  
- `find_correlations` performs Spearman fallback on zero variance, records `{r, n}` in the derived QueryResult, and feeds source + derived results into `_verify_response` (`src/qnwis/agents/pattern_detective.py:183`).  
- Root-cause and best-practice tables share `format_evidence_table`, giving deterministic TOP 10 rows with an ellipsis entry, then passing every QueryResult to the verifier (`src/qnwis/agents/pattern_detective.py:325`, `:458`; `src/qnwis/agents/utils/evidence.py:15`).  
- National strategy methods add input guards, provenance-aware logging, deterministic evidence shaping, and verification coverage for every query (`src/qnwis/agents/national_strategy.py:63`, `:175`, `:276`).  
- Prompt templates now require “Per LMIS … [QueryID]” or “According to GCC-STAT/World Bank … [QueryID]” phrasing to keep citations reproducible (`src/qnwis/agents/prompts/pattern_detective_prompts.py:8`; `src/qnwis/agents/prompts/national_strategy_prompts.py:8`).  
- `AgentResponseVerifier` enforces citation-to-result matching, complementing the new evidence truncation utilities (`src/qnwis/agents/utils/verification.py:21`).  
- Tests capture correlation fallback, validation errors, DataClient invocation, and verifier failures (`tests/unit/test_agent_pattern_detective.py:79`, `:106`, `:113`; `tests/unit/test_agent_national_strategy.py:89`; `tests/unit/test_agents_evidence_utils.py:30`).

**Mocked usage snippets**
- `PatternDetectiveAgent(client).detect_anomalous_retention(z_threshold=2.5)`
- `PatternDetectiveAgent(client).find_correlations(method="pearson", min_sample_size=3)`
- `PatternDetectiveAgent(client).identify_root_causes(top_n=4)`
- `PatternDetectiveAgent(client).best_practices(metric="retention", top_n=8)`
- `PatternDetectiveAgent(client).run()`
- `NationalStrategyAgent(client).gcc_benchmark(min_countries=4)`
- `NationalStrategyAgent(client).talent_competition_assessment()`
- `NationalStrategyAgent(client).vision2030_alignment(target_year=2030, current_year=2024)`
- `NationalStrategyAgent(client).run()`
