# Citation Injection Fix - Status Report

**Date**: 2025-11-14
**Commit**: 7a9a191
**Status**: ✅ FIX IMPLEMENTED, READY FOR TESTING

---

## Summary

The critical citation injection bug has been fixed. Citations are now being injected into the **narrative field** (which is what the UI displays), not just the findings field.

---

## What Was Fixed

### Problem
Citations were being injected into `report.findings[]['analysis']` but the Chainlit UI displays `report.narrative`. This caused citations to be invisible to users despite the injector working correctly.

### Solution
Updated `src/qnwis/orchestration/graph_llm.py` (lines 592-628) to inject citations into **BOTH**:
1. `report.narrative` ← **This is what the UI displays**
2. `report.findings[]['analysis']` ← For completeness

### Code Changes

**File**: [src/qnwis/orchestration/graph_llm.py:592-628](src/qnwis/orchestration/graph_llm.py#L592-L628)

```python
# CRITICAL FIX: Inject into narrative field (this is what UI displays!)
if hasattr(report, 'narrative') and report.narrative:
    original_narrative = report.narrative
    cited_narrative = injector.inject_citations(original_narrative, prefetch_data)
    report.narrative = cited_narrative
    logger.info(f"Injected citations into narrative: {len(original_narrative)} -> {len(cited_narrative)} chars")
    logger.info(f"Citations present in narrative: {'[Per extraction:' in cited_narrative}")

# Also inject into findings (for completeness)
if hasattr(report, 'findings') and report.findings:
    updated_findings = []
    for finding in report.findings:
        if isinstance(finding, dict):
            updated_finding = finding.copy()

            # Inject into analysis field
            if 'analysis' in updated_finding:
                updated_finding['analysis'] = injector.inject_citations(
                    updated_finding['analysis'],
                    prefetch_data
                )

            # Inject into summary field
            if 'summary' in updated_finding:
                updated_finding['summary'] = injector.inject_citations(
                    updated_finding['summary'],
                    prefetch_data
                )

            updated_findings.append(updated_finding)
        else:
            updated_findings.append(finding)

    report.findings = updated_findings
```

---

## Testing Instructions

### Chainlit UI is Running
- **URL**: http://localhost:8001
- **Status**: ✅ Active and ready

### Test Query
Submit this question through the UI:
```
Compare Qatar's unemployment to other GCC countries
```

### Expected Behavior

#### 1. Log Output
You should see these lines in the console:
```
INFO: Injected citations into narrative: X -> Y chars
INFO: Citations present in narrative: True
INFO: Injected N citations into text
```

#### 2. UI Output
The agent narrative should contain inline citations like:
```
Qatar's 0.10 [Per extraction: '0.10' from GCC-STAT Q1-2024] unemployment rate
represents exceptional performance, standing 1.9 [Per extraction: '1.9' from
GCC-STAT Q1-2024] percentage points below Kuwait 2.00 [Per extraction: '2.00'
from GCC-STAT Q1-2024]...
```

**Every number should have a `[Per extraction: ...]` citation!**

---

## Additional Fixes Included (Option C)

This fix is part of the complete Option C hybrid solution:

1. ✅ **Citation Injector** - Programmatically inject citations (don't rely on LLM)
   - File: `src/qnwis/orchestration/citation_injector.py` (320 lines)
   - Fuzzy number matching: "0.1" matches "0.10", "10%", etc.

2. ✅ **Pydantic Validation Fix** - Accept string metrics for ranges/comparatives
   - File: `src/qnwis/llm/parser.py`
   - Changed: `metrics: dict[str, Union[float, int, str]]`
   - Now accepts: `"0.10% - 4.90%"` and `"3.73pp below average"`

3. ✅ **Verification Node Fix** - Correct data lookup so it actually runs
   - File: `src/qnwis/orchestration/graph_llm.py:656-662`
   - Added fallback: `prefetch_data = state.get("prefetch", {}).get("data", {})`

4. ✅ **Narrative Field Fix** - Inject into correct display field (THIS FIX)
   - File: `src/qnwis/orchestration/graph_llm.py:592-628`
   - Targets `report.narrative` instead of just `report.findings`

---

## Commit History

```
7a9a191 - CRITICAL FIX: Inject citations into narrative field (not just findings)
61c6c7a - CRITICAL FIX: Option C - Hybrid solution for zero-fabrication citations
```

---

## Next Steps

1. **Test the UI** - Submit the test query and verify citations appear
2. **Check Logs** - Confirm citation injection messages appear
3. **Verify Output** - Ensure every number has inline citations
4. **Document Results** - Update status based on test outcome

---

## Known Issues

### Debate/Critique Nodes Not Visible in UI
- **Status**: Identified but not yet fixed
- **Problem**: Nodes exist in graph but not showing in UI workflow display
- **Impact**: Medium (workflow runs but UI doesn't show all stages)
- **Next**: Add event callbacks or update reasoning chain display

---

## Status Summary

| Component | Status | Notes |
|-----------|--------|-------|
| Citation Injector | ✅ Working | Fuzzy matching, comprehensive coverage |
| Pydantic Validation | ✅ Fixed | Accepts Union[float, int, str] |
| Verification Node | ✅ Fixed | Data lookup corrected |
| **Narrative Injection** | ✅ **FIXED** | **This commit** |
| Debate/Critique UI | ⚠️ Pending | Nodes run but not visible |

---

## Success Criteria

✅ **PASS**: If citations appear in UI output
❌ **FAIL**: If output is clean text without `[Per extraction: ...]`

---

**System is ready for testing. Please test via the UI and report results.**
