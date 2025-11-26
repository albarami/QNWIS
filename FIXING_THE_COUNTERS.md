# Fixing The Counters

**Problem:** UI shows "0 agents", "0/0 scenarios", "0%" even though everything is running

**Root Cause:** State updates weren't setting the counter values properly

**Fix Applied:**
1. When scenario_gen completes → Set totalScenarios and selectedAgents
2. When parallel_exec starts → Set totalScenarios = 6, scenariosCompleted = 0  
3. When scenario:ID completes → Increment scenariosCompleted
4. When parallel_progress event → Update both counters

**Restarting frontend now with fixes...**

**After restart:**
- AGENTS SELECTED should show: 5
- Scenarios should show: 0/6, then 1/6, 2/6, etc.
- Progress bar should advance

**Frontend restarting - refresh in 10 seconds and you should see active counters!**

