# TASK.md

## Discovered During Work

<!-- Format: - [ ] `file:line` | Severity | Description -->
- [x] `src/nsic/engine_b/services/financial_modeling.py:407` | Important | Bare except: in IRR fallback — fixed in Sprint 1
- [x] `src/nsic/integration/database.py:358` | Important | Bare except: in table stats query — fixed in Sprint 1
- [x] `src/nsic/orchestration/engine_b_deepseek.py:656,660` | Important | Two bare except: in verification — fixed in Sprint 1
- [ ] `src/qnwis/scripts/qa/rg8_continuity_gate.py` | Minor | RG-8 gate fails on council_stream_llm missing request param after rate limiter added
- [ ] `src/qnwis/agents/*.py` | Minor | DeprecationWarning: invalid escape sequence '\s' in 4 agent files
- [ ] `mypy.ini` / `pyproject.toml` | Important | mypy finds dual module names (qnwis.X and src.qnwis.X) after follow_imports=normal — needs package install or path config fix

