# Chainlit Removal Audit (Phase 5)

Phase 5 of `REACT_MIGRATION_REVISED.md` requires a full inventory of every Chainlit reference before we begin deletions. This document records the repo-wide search that was executed and groups every hit (files, scripts, configs, docs, and tests) so we can remove/replace them systematically without missing anything.

## Search Inputs

- Command: `rg -ni --hidden --glob '!_rg_refs.log' --glob '!nul' "chainlit"`
- Location: `d:\lmis_int`
- Timestamp: 2025-11-15 12:19:49 +00:00

## Summary by Category

| Category | Files |
| --- | --- |
| Runtime Python / UI modules | apps/chainlit/app.py, chainlit_app.py, create_chainlit_tables.py, src/qnwis/ui/chainlit_app.py, src/qnwis/ui/chainlit_app_llm.py, src/qnwis/ui/components/__init__.py, src/qnwis/ui/components/progress_panel.py, src/qnwis/ui/components/stage_timeline.py, src/qnwis/ui/components_legacy.py, src/qnwis/ui/error_handling.py, src/qnwis/ui/telemetry.py, src/qnwis/verification/ui_bridge.py |
| CLI / launch scripts & helpers | launch_system.py, launch_full_system.py, start_chainlit.py, start_chainlit_no_db.bat, start_with_env.ps1, RESTART_SERVERS.bat, QUICK_START.bat, scripts/init_database.{ps1,sh}, scripts/migrate_to_react.ps1, scripts/seed_production_database.py, scripts/verify_runtime_dependencies.py, src/qnwis/scripts/qa/readiness_gate.py |
| Config & environment | .chainlit/config.toml, chainlit.md, .env.chainlit, .env.example, Dockerfile (copies .chainlit), pyproject.toml (dependency), requirements.txt, RESTART_SERVERS.bat environment exports |
| Tests & QA | tests/unit/test_chainlit_import.py, tests/integration/ui/test_chainlit_streaming.py, tests/integration/ui/test_chainlit_streaming_happy_path.py, tests/integration/test_e2e_chainlit_workflow.py, tests/ui/test_chainlit_orchestration.py, tests/unit/test_pyproject_dependencies.py, tests/unit/test_requirements_txt_contains_core_deps.py, test_citations_direct.py |
| Documentation / status reports | (full list below) all contain operating guides, status updates, or migration notes that still describe Chainlit |
| Deployment / readiness artifacts | docs/ARCHITECTURE.md, docs/USER_GUIDE.md, PRODUCTION_DEPLOYMENT_GUIDE.md, INSTALL_POSTGRESQL.md, etc. referencing Chainlit setup instructions |
| Generated / misc | junit.xml (historical test output referencing Chainlit) |

## Detailed References

### Runtime Python + UI
- `apps/chainlit/app.py` – Chainlit UI entrypoint (imports `chainlit as cl`).
- `chainlit_app.py` – legacy deterministic Chainlit UI script.
- `create_chainlit_tables.py` – references `chainlit.data.sql_alchemy`.
- `src/qnwis/ui/chainlit_app.py` – packaged deterministic Chainlit app.
- `src/qnwis/ui/chainlit_app_llm.py` – LLM-based Chainlit UI (current).
- `src/qnwis/ui/components/__init__.py` – package docstring references Chainlit.
- `src/qnwis/ui/components/progress_panel.py` – imports Chainlit to render progress messages.
- `src/qnwis/ui/components/stage_timeline.py` – returns markdown targeted at Chainlit.
- `src/qnwis/ui/components_legacy.py` – helper components for Chainlit flows.
- `src/qnwis/ui/error_handling.py` – logs Chainlit errors and emits UI events.
- `src/qnwis/ui/telemetry.py` – telemetry helpers referencing Chainlit UI IDs.
- `src/qnwis/verification/ui_bridge.py` – formats verification output for Chainlit display.

### CLI, Launchers & Automation Scripts
- `launch_system.py` – CLI that shells out to `chainlit run ...`.
- `launch_full_system.py` – has `start_chainlit_ui`, `chainlit --version` checks, command invocation.
- `start_chainlit.py` – helper script that imports `chainlit` and runs UI.
- `start_chainlit_no_db.bat` – Windows batch file starting Chainlit UI.
- `start_with_env.ps1` – PowerShell script exporting env vars then starting Chainlit.
- `RESTART_SERVERS.bat` – references `chainlit run` restart instructions.
- `QUICK_START.bat` – includes Chainlit start command.
- `scripts/init_database.ps1` and `scripts/init_database.sh` – mention Chainlit verification steps.
- `scripts/migrate_to_react.ps1` – enumerates Chainlit removal TODOs.
- `scripts/seed_production_database.py` – describes Chainlit UI check commands.
- `scripts/verify_runtime_dependencies.py` – ensures `chainlit` package installed.
- `src/qnwis/scripts/qa/readiness_gate.py` – documentation pointers referencing Chainlit UI readiness.

### Configurations & Environment Files
- `.chainlit/config.toml` – Chainlit-specific configuration (banner, metadata, auth).
- `chainlit.md` – Chainlit welcome screen content.
- `.env.chainlit` – environment overrides for Chainlit UI (API keys, ports, session secret, etc.).
- `.env.example` – contains CHAINLIT_* variables (ports, tokens) for reference.
- `Dockerfile` – copies `.chainlit/` into image and installs dependencies.
- `pyproject.toml` – lists `chainlit` under `[project.dependencies]`.
- `requirements.txt` – pins `chainlit>=2.x`.
- `requirements-dev.txt` / runtime check scripts indirectly reference Chainlit when verifying dependency parity (captured by `tests/unit/test_requirements_txt_contains_core_deps.py`).

### Tests & QA
- `tests/unit/test_chainlit_import.py` – ensures Chainlit modules import cleanly.
- `tests/integration/ui/test_chainlit_streaming.py` – integration suite for Chainlit SSE streaming.
- `tests/integration/ui/test_chainlit_streaming_happy_path.py` – same domain.
- `tests/integration/test_e2e_chainlit_workflow.py` – system-level Chainlit workflow coverage.
- `tests/ui/test_chainlit_orchestration.py` – coverage for orchestration pieces exposed through Chainlit UI.
- `test_citations_direct.py` – docstring references bypassing Chainlit.
- `tests/unit/test_pyproject_dependencies.py` and `tests/unit/test_requirements_txt_contains_core_deps.py` – assert the Chainlit dependency pins exist.

### Documentation, Guides & Status Logs
All of the following guides, summaries, and reviews contain explicit Chainlit instructions (setup commands, UI screenshots, or references to the Chainlit UI as the front-end). Each must be rewritten to describe the React client or archived if obsolete:

`100_PERCENT_COMPLETE.md`, `ALL_FEATURES_COMPLETE_FINAL.md`, `C1_API_LLM_MIGRATION_COMPLETE.md`, `C5_ERROR_HANDLING_COMPLETE.md`, `CHAINLIT_ERROR_FIX.md`, `CITATION_FIX_STATUS.md`, `COMPLETE_SYSTEM_INVENTORY.md`, `DEPENDENCY_MANAGEMENT_COMPLETE.md`, `docs/ARCHITECTURE.md`, `docs/IMPLEMENTATION_QUICK_REFERENCE.md`, `docs/IMPLEMENTATION_ROADMAP.md`, `docs/LMIS_INTELLIGENCE_SYSTEM_PROPOSAL_V2.md`, `docs/PROPOSAL_CHANGES_SUMMARY.md`, `docs/RELEASE_NOTES.md`, `docs/reviews/step3_ui_streaming_notes.md`, `docs/reviews/step3_ui_streaming_review.md`, `docs/reviews/step34_review.md`, `docs/reviews/step39_review.md`, `docs/ui_demos.md`, `docs/USER_GUIDE.md`, `DOCUMENTATION_INDEX.md`, `EVALUATION_RESPONSE_AND_ACTION_PLAN.md`, `EXECUTIVE_ACTION_PLAN.md`, `EXECUTIVE_SUMMARY.md`, `FIX_STUB_MODE_ISSUE.md`, `FIXES_APPLIED.md`, `FIXES_COMPLETE_SUMMARY.md`, `FULL_SYSTEM_DEPLOYMENT.md`, `H2_EXECUTIVE_DASHBOARD_COMPLETE.md`, `H3_VERIFICATION_STAGE_COMPLETE.md`, `H4_RAG_INTEGRATION_COMPLETE.md`, `H6_INTELLIGENT_AGENT_SELECTION_COMPLETE.md`, `H8_AUDIT_TRAIL_VIEWER_COMPLETE.md`, `HOTFIX_SPEC_ALIGNMENT.md`, `IMPLEMENTATION_PLAN_LLM_AGENTS.md`, `INSTALL_POSTGRESQL.md`, `INTEGRATION_COMPLETE.md`, `LAUNCH_GUIDE.md`, `LAUNCH_INSTRUCTIONS.md`, `MASTER_INTEGRATION_PLAN.md`, `MIGRATION_SUMMARY.md`, `MINISTERIAL_GRADE_IMPLEMENTATION_PLAN.md`, `OPTION_C_FIXES_COMPLETE.md`, `PHASE3_COMPLETE.md`, `PHASE4_1_COMPLETE.md`, `PHASE4_INTEGRATION_POLISH_STATUS.md`, `PRODUCTION_DEPLOYMENT_GUIDE.md`, `QNWIS_AGENT_INTEGRATION_PLAN.md`, `QNWIS_COMPLETE_GAP_ANALYSIS.md`, `QUICK_REFERENCE.md`, `QUICK_STATUS.md`, `QUICKSTART_DEPENDENCY_MANAGEMENT.md`, `QUICKSTART_STEP39.md`, `QUICKSTART_UI_STREAMING.md`, `REACT_EXECUTION_CHECKLIST.md`, `REACT_MIGRATION_PLAN.md`, `REACT_MIGRATION_REVISED.md`, `SESSION_COMPLETE_PHASE_1_2.md`, `SPEC_ALIGNMENT_COMPLETE.md`, `START_MIGRATION_NOW.md`, `STEP39_ENTERPRISE_UI_COMPLETE.md`, `STEP39_IMPLEMENTATION_COMPLETE.md`, `STEP39_LAUNCH_GUIDE.md`, `STEP39_LAUNCH_SUMMARY.md`, `STEP39_PROGRESS.md`, `STEP39_QUICK_START.md`, `STEP39_REMAINING_WORK.md`, `SYSTEM_AUDIT_REPORT.md`, `SYSTEM_FIXED_AND_READY.md`, `SYSTEM_LAUNCHED_READY_TO_TEST.md`, `SYSTEM_NOW_WORKING.md`, `SYSTEM_OPERATIONAL_FINAL.md`, `SYSTEM_OPERATIONAL_STATUS.md`, `SYSTEM_READY.md`, `SYSTEM_REALITY_CHECK.md`, `SYSTEM_VERIFICATION_COMPLETE.md`, `TEST_READY_STATUS.md`, `UI_DEPTH_PROBLEM_DIAGNOSIS.md`, `UI_FIXES_APPLIED.md`, `UI_FIXES_READY_FOR_TESTING.md`, `UI_OUTPUT_IMPROVEMENTS.md`, `UI_STREAMING_IMPLEMENTATION_COMPLETE.md`, `WHAT_IS_ACTUALLY_MISSING.md`, `WHAT_NEEDS_TO_BE_FIXED.md`.

Additionally, audit artifacts stored inside `src/qnwis/docs/audit/{readiness_report.json, READINESS_REPORT_1_25.md, READINESS_SUMMARY.html}` and `src/qnwis/docs/reviews/step1_c2_review.md` reference Chainlit readiness for gates (these will need updating or archival).

### Deployment & Ops Guides
- `PRODUCTION_DEPLOYMENT_GUIDE.md`, `INSTALL_POSTGRESQL.md`, `FULL_SYSTEM_DEPLOYMENT.md`, etc. include “chainlit run …” instructions that must be replaced by React deployment steps.
- `LAUNCH_GUIDE.md`, `LAUNCH_INSTRUCTIONS.md`, `QUICK_START.bat`, and `RESTART_SERVERS.bat` include CLI commands pointing to `chainlit_app_llm.py`.
- `REACT_EXECUTION_CHECKLIST.md` and `REACT_MIGRATION_REVISED.md` define the requirement to remove Chainlit entirely (Phase 5) and list the docs that must be rewritten once the React UI is dominant.

### Miscellaneous / Generated
- `junit.xml` – recorded a test failure referencing Chainlit (safe to delete or regenerate once Chainlit suites are gone).

## Next Steps
1. Remove/replace every runtime file or dependency listed above (apps, modules, scripts, env).
2. Delete the Chainlit-specific directories/files (`apps/chainlit/`, `.chainlit/`, `chainlit_app*.py`, etc.) after confirming React parity.
3. Update dependency manifests (`pyproject.toml`, `requirements*.txt`) and scripts/tests that enforce Chainlit availability.
4. Rewrite or archive every documentation item to describe the React frontend and SSE validation.
5. Rerun the search command afterwards; Phase 5 completes only when `rg -ni "chainlit"` returns no hits.
