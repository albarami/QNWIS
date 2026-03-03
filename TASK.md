# TASK.md

## Discovered During Work

<!-- Format: - [ ] `file:line` | Severity | Description -->
- [x] `src/nsic/engine_b/services/financial_modeling.py:407` | Important | Bare except: in IRR fallback — fixed in Sprint 1
- [x] `src/nsic/integration/database.py:358` | Important | Bare except: in table stats query — fixed in Sprint 1
- [x] `src/nsic/orchestration/engine_b_deepseek.py:656,660` | Important | Two bare except: in verification — fixed in Sprint 1
- [x] `src/qnwis/api/routers/council_llm.py` | Minor | council_stream_llm missing request param for rate limiter — fixed in Sprint 4
- [x] `src/qnwis/agents/*.py` | Minor | DeprecationWarning: invalid escape sequence '\s' in 4 agent files — fixed in Sprint 4
- [x] `src/**/*.py` | Important | All `from src.qnwis.X` imports converted to relative imports — fixed in Sprint 4

