# Step 19 Citation Enforcement Review

## What Changed
- Hardened regex coverage to support currency, percentages, basis points (`bps`), and canonical QR/QAR units while keeping the year/token ignore list deterministic.
- Introduced contextual evaluation metadata (missing-QID severity, strict keyword hits, canonical prefix normalization) so the verifier can distinguish warnings vs. errors and uphold per-metric strictness.
- Added source-synonym handling (`According to GCCSTAT:` → `According to GCC-STAT:`) plus a configurable adjacent-bullet scanner so reports that cite sources on the next bullet line are not flagged as false positives.
- Wired runtime instrumentation (`runtime_ms`) into `CitationReport`, surfaced it in the formatter’s “Citations Summary,” and validated that typical narratives complete in <20 ms.
- Ensured verify-node integration now fails on ERROR issues but simply annotates WARNINGs, and expanded formatter output with counts, concrete examples, and remediation tips.

## Edge Cases Exercised
- Multi-year narratives (2019/2020) and identifier-like tokens (e.g., `ID 2020`, `ISO-3166`) are ignored, preventing noise.
- QID detection now covers both `QID:` and `query_id=` syntax, with strict keywords (attrition spikes/hotspots) forcing QIDs even if the global requirement is relaxed.
- Source->dataset mapping now tested across LMIS, GCC-STAT, and World Bank results, including synonym normalization.
- Adjacent bullet lists that split the statistic and its citation are linked, eliminating recurring markdown false negatives.
- Formatter scenarios covering citation warnings, missing QIDs (warning severity), unknown sources, and runtime metadata are covered by unit tests.

## Citation Examples
- **Good:** `- Employment jumped 12%.\n- Per LMIS: Survey Q2 2024 (QID: lmis_ret_002).` ← Bullet-aware heuristic treats the pair as cited and LMIS datasets are confirmed.
- **Good:** `According to GCCSTAT: Attrition fell 3% (query_id=gcc_attrition_007).` ← Synonym is normalized and the `query_id=` format satisfies strict metrics.
- **Bad:** `Attrition spiked to 9%.` ← Lacks prefix and QID; strict keyword escalates to an ERROR that now fails the workflow.
- **Bad:** `Per LMIS: Productivity is 18%.` (no QID) ← Emits a WARNING when global severity is relaxed, but still enumerated in the formatter with remediation guidance.
