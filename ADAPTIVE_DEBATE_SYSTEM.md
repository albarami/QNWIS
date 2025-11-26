# Adaptive Debate System

## Problem
The original system had **fixed debate limits** (125 turns for everything), causing:
- ❌ Simple questions taking 30 minutes (wasteful)
- ❌ No distinction between "What is unemployment?" vs "$15B investment decision"

## Solution: Adaptive Debate Depth

The system now **automatically detects question complexity** and adjusts debate depth accordingly.

### 🎯 Three Debate Configurations

| Configuration | Max Turns | Duration | Use Case | Example |
|--------------|-----------|----------|----------|---------|
| **SIMPLE** | 15 turns | 2-3 min | Factual queries, status checks | "What is Qatar's unemployment rate?" |
| **STANDARD** | 40 turns | 8-12 min | Analysis, trends, comparisons | "Compare Qatar's labor market to GCC" |
| **COMPLEX** | 125 turns | 20-30 min | Strategic decisions, investments | "$15B Food Valley investment?" |

### 🔍 Complexity Detection Algorithm

```python
def _detect_question_complexity(question):
    # SIMPLE indicators (factual)
    - "what is", "what are", "how many"
    - Short questions (< 15 words)
    - Single metrics
    
    # COMPLEX indicators (strategic)
    - Dollar amounts ($, billion)
    - "investment", "should Qatar", "strategic"
    - "food security", "self-sufficiency"
    - Multi-year planning ("by 2030")
    - "national", "policy", "economic development"
    
    # Decision logic:
    - If simple indicators + short → SIMPLE
    - If 3+ complex indicators → COMPLEX
    - Else → STANDARD
```

### 📊 Phase Turn Limits by Configuration

| Phase | Simple | Standard | Complex |
|-------|--------|----------|---------|
| Opening Statements | 4 | 8 | 12 |
| Challenge/Defense | 6 | 18 | 50 |
| Edge Cases | 2 | 8 | 25 |
| Risk Analysis | 2 | 4 | 25 |
| Consensus Building | 1 | 2 | 13 |
| **TOTAL** | **15** | **40** | **125** |

## Examples

### SIMPLE Question (15 turns, 2-3 min)
```
"What is Qatar's current unemployment rate?"
```
**Detection:**
- ✓ Contains "what is" (simple indicator)
- ✓ Short (7 words)
- **Result:** SIMPLE configuration

### COMPLEX Question (125 turns, 20-30 min)
```
"Should Qatar invest $15B in Food Valley project targeting 
40% food self-sufficiency by 2030?"
```
**Detection:**
- ✓ Contains "$15B" (investment indicator)
- ✓ Contains "invest" (strategic indicator)
- ✓ Contains "Food Valley" (project indicator)
- ✓ Contains "self-sufficiency" (strategic indicator)
- ✓ Contains "by 2030" (multi-year indicator)
- **Count:** 5 complex indicators (>= 3 threshold)
- **Result:** COMPLEX configuration

### STANDARD Question (40 turns, 8-12 min)
```
"What are Qatar's hospitality sector labor market trends?"
```
**Detection:**
- Contains "what are" but also "trends" (analytical)
- Medium complexity, no strategic decision
- **Result:** STANDARD configuration

## Benefits

✅ **Efficiency:** Simple questions get fast answers (2-3 min)
✅ **Depth:** Complex decisions get thorough debate (20-30 min)
✅ **Automatic:** No manual configuration needed
✅ **Smart:** System adapts to question nature

## Implementation Location

- **File:** `src/qnwis/orchestration/legendary_debate_orchestrator.py`
- **Methods:**
  - `_detect_question_complexity(question)` → Returns "simple"/"standard"/"complex"
  - `_apply_debate_config(complexity)` → Sets turn limits
  - `conduct_legendary_debate()` → Calls detection at start

## Circuit Breakers

Even with adaptive limits, circuit breakers prevent runaway debates:
- After Phase 1: Check if MAX_TURNS_TOTAL reached
- After Phase 2: Check if MAX_TURNS_TOTAL reached
- Graceful termination with partial synthesis if limits hit

## Expected Behavior

| Test Case | Expected Complexity | Expected Turns | Expected Duration |
|-----------|-------------------|----------------|------------------|
| Food Valley $15B | COMPLEX | ~80-100 | 20-25 minutes |
| Labor Market Trends | STANDARD | ~25-35 | 8-12 minutes |
| Unemployment Rate | SIMPLE | ~10-12 | 2-3 minutes |
