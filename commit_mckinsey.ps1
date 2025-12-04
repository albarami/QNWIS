# Commit McKinsey-grade changes
Set-Location D:\lmis_int

# Stage new files
git add src/qnwis/engines/
git add src/qnwis/templates/
git add src/qnwis/orchestration/nodes/structure_data.py
git add src/qnwis/orchestration/nodes/calculate.py
git add src/qnwis/orchestration/state.py
git add src/qnwis/orchestration/graph_llm.py
git add src/qnwis/orchestration/legendary_debate_orchestrator.py
git add src/qnwis/orchestration/nodes/synthesis_ministerial.py
git add tests/engines/
git add tests/integration/test_mckinsey_flow.py
git add pyproject.toml

# Show status
Write-Host "=== Git Status ===" -ForegroundColor Green
git status --short

# Commit
Write-Host "`n=== Committing ===" -ForegroundColor Green
$message = @"
feat: add McKinsey-grade deterministic calculation pipeline

- Add FinancialEngine with NPV/IRR/payback/sensitivity calculations
- Add structure_data_node to convert extracted facts to model inputs
- Add calculate_node for deterministic Python calculations
- Add MinisterialBriefingTemplate for McKinsey-grade output
- Update state schema with structured_inputs and calculated_results
- Update workflow: Extract -> RAG -> Structure -> Calculate -> Agents
- Update debate orchestrator to include calculated results in prompts
- Update synthesis node to use template when calculations available
- Add data confidence threshold warnings
- Fix NoneType errors in ministerial_briefing.py

All 123 core QNWIS tests pass.
CRITICAL: LLMs are BANNED from doing math - all calculations deterministic
"@

git commit -m $message

# Show log
Write-Host "`n=== Recent Commits ===" -ForegroundColor Green
git log --oneline -3

Write-Host "`nDone!" -ForegroundColor Green








