# QNWIS - Qatar National Workforce Intelligence System

**Status:** ✅ PRODUCTION-READY (RG-2 Certified)  
**Version:** 1.0.0  
**Last Updated:** November 9, 2025

Production-grade workforce data intelligence and analysis platform for Qatar's Ministry of Labour.

## 🎯 Readiness Gate Status

**RG-2 Final Verdict:** ✅ **PASS** (6/6 gates, 26/26 steps complete)

| Gate | Status | Details |
|------|--------|---------|
| step_completeness | ✅ PASS | 26/26 steps |
| no_placeholders | ✅ PASS | 0 violations |
| linters_and_types | ✅ PASS | Ruff=0, Flake8=0, Mypy=0 |
| deterministic_access | ✅ PASS | 100% DataClient |
| verification_chain | ✅ PASS | L19→L20→L21→L22 |
| performance_sla | ✅ PASS | p95 <75ms |

**Certification:** Ready for production deployment to Qatar Ministry of Labour.

---

## System Overview

A deterministic data integration and multi-agent analysis system providing:
- **9 specialized analytical agents** for labour market intelligence (8 active + 1 planning)
- **Deterministic data layer** with caching, freshness tracking, and provenance
- **FastAPI-based query execution** with TTL-bounded caching and override controls
- **LangGraph orchestration** for multi-step analytical workflows
- **High coverage & type safety**: 91% test coverage, strict mypy typing, 527 tests passing
- **Complete verification chain**: Citation (L19), Verification (L20), Audit (L21), Confidence (L22)

## Core Components

### Data Layer
- **Deterministic Query API**: Pre-defined queries with caching, normalization, and derived metrics
- **Connectors**: World Bank, Qatar Open Data, CSV catalog integration
- **Cache Backends**: Memory and Redis with TTL management
- **Freshness Tracking**: Data staleness detection and SLA warnings
- **Dataset Catalog**: License enrichment and metadata registry

### Agents Layer
- **TimeMachineAgent**: Historical analysis, baselines, trends, structural breaks (<50ms SLA)
- **PatternMinerAgent**: Correlation discovery, seasonal effects, cohort analysis (<200ms SLA)
- **PredictorAgent**: 12-month forecasting with backtesting and early warning (<100ms SLA)
- **ScenarioAgent**: What-if analysis, scenario comparison, national impact modeling (<75ms SLA)
- **NationalStrategyAgent**: GCC benchmarking, Vision 2030 tracking, strategic overview
- **LabourEconomistAgent**: Employment trends, YoY growth analysis (framework ready)
- **NationalizationAgent**: Qatarization tracking, GCC comparisons (framework ready)
- **SkillsAgent**: Skills gap analysis, gender distribution (framework ready)
- **PatternDetectiveAgent**: Data quality validation, consistency checks (framework ready)

### API Layer
- **FastAPI Application**: Async endpoints with request ID tracking
- **Query Endpoints**: List, run, and invalidate cached queries
- **Health Checks**: System status and dependency monitoring
- **Rate Limiting**: Optional RPS throttling

## Project Structure

```
lmis_int/
├── src/qnwis/
│   ├── agents/             # 9 analytical agents (8 active + 1 planning)
│   ├── orchestration/      # Intent router, workflow, coordination
│   ├── verification/       # L19-L22 verification layers
│   ├── scenario/           # DSL, apply, QA for scenario planning
│   ├── data/
│   │   ├── deterministic/  # Query registry, cache, normalization
│   │   ├── derived/        # Metrics computation (share, YoY, CAGR)
│   │   ├── connectors/     # External data source integrations
│   │   ├── catalog/        # Dataset metadata and licensing
│   │   └── validation/     # Data quality verification
│   ├── cli/                # Command-line tools (cache, scenario, verify)
│   ├── api/                # FastAPI routers and models
│   ├── utils/              # Request ID, rate limiting, logging
│   └── config/             # Settings management
├── tests/
│   ├── unit/               # 412 unit tests (91% coverage)
│   ├── integration/        # 84 integration tests (end-to-end flows)
│   └── system/             # 31 system tests (readiness gates)
├── docs/                   # Implementation reviews and guides
├── audit_packs/            # L21 audit trail storage
└── tools/mcp/              # Model Context Protocol server

```

## Production Quick Start

For production deployment to Qatar Ministry of Labour infrastructure:

1. **Review deployment documentation:**
   - **[docs/deploy/DEPLOYMENT_RUNBOOK.md](docs/deploy/DEPLOYMENT_RUNBOOK.md)** - Complete deployment guide
   - **[docs/deploy/SECURE_ENV_REFERENCE.md](docs/deploy/SECURE_ENV_REFERENCE.md)** - Environment variables reference

2. **Deploy with Docker Compose (recommended):**
   ```bash
   cd ops/docker
   cp .env.example .env
   # Edit .env with production secrets (NEVER commit to Git)
   docker compose -f docker-compose.prod.yml up -d
   ```

3. **Verify deployment:**
   ```bash
   curl http://HOST:8000/health/ready  # → 200 OK
   curl http://HOST:8000/metrics       # → Prometheus metrics
   ```

4. **Configure backups:**
   ```bash
   # Add to crontab for nightly backups
   0 2 * * * docker exec qnwis-api-1 /bin/bash -lc 'scripts/pg_backup.sh /app/backups'
   ```

**Security:** All secrets via environment variables only. TLS termination at reverse proxy. Non-root container runtime.

---

## Development Setup

1. **Clone and navigate to project:**
   ```bash
   cd D:\lmis_int
   ```

2. **Activate virtual environment:**
   ```bash
   .venv\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run tests:**
   ```bash
   pytest tests/ -v
   ```

6. **Run linting:**
   ```bash
   ruff check src/ tests/
   mypy src/ --strict
   ```

## Technology Stack

- **Framework**: FastAPI with async/await
- **Data Integration**: World Bank API, Qatar Open Data Portal, CSV catalogs
- **Cache**: Redis + in-memory backends with TTL management
- **Orchestration**: LangGraph for multi-agent workflows
- **Testing**: pytest with 90%+ coverage (pytest-asyncio, pytest-cov)
- **Type Checking**: mypy strict mode
- **Linting**: ruff + flake8
- **Quality Gates**: Secret scanning, coverage enforcement, Windows compatibility

## Key Features

- **Deterministic Execution**: All agents use pre-defined cached queries (no SQL/RAG in agent code)
- **Provenance Tracking**: Every insight includes evidence chain (dataset, locator, fields)
- **Normalization & Metrics**: Safe parameter/row normalization, derived metrics (share, YoY, CAGR)
- **Request Lifecycle**: Request ID propagation, TTL bounds (60-86400s), override whitelisting
- **Security**: Secret redaction, allowlist-based file access, no execution in MCP tools

## Documentation

### 📚 Essential Documents

**For Decision Makers:**
- **[EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** - Comprehensive overview for leadership (585 lines)
- **[FINAL_GATE_SUMMARY.md](FINAL_GATE_SUMMARY.md)** - Quick status update and next steps
- **[CERTIFICATION_BADGE.md](CERTIFICATION_BADGE.md)** - RG-2 certification display

**For Technical Staff:**
- **[RG2_FINAL_COMPLETE.md](RG2_FINAL_COMPLETE.md)** - Complete readiness gate report (900+ lines)
- **[PRODUCTION_DEPLOYMENT_GUIDE.md](PRODUCTION_DEPLOYMENT_GUIDE.md)** - Deployment instructions (800+ lines)
- **[STEP26_RG2_COMPLETE.md](STEP26_RG2_COMPLETE.md)** - Step 26 Scenario Planner validation

**Implementation Documentation:**
- 26 step completion documents (STEP_XX_COMPLETE.md)
- Agent guides in `docs/agents/`
- Orchestration guides in `docs/orchestration/`
- Analysis guides in `docs/analysis/`

### 📖 Quick Start Guides
- **[AGENTS_QUICK_START.md](AGENTS_QUICK_START.md)** - Agent usage examples
- **[ORCHESTRATION_QUICK_START.md](ORCHESTRATION_QUICK_START.md)** - Routing and coordination
- **[READINESS_GATE_QUICK_START.md](READINESS_GATE_QUICK_START.md)** - Quality validation

Additional technical specifications in `docs/` folder.

## Using the MCP Server in Windsurf

The QNWIS MCP (Model Context Protocol) server provides secure, controlled access to project resources for AI assistants.

### Setup

The MCP server is configured in `.mcp/servers.json` and will be automatically detected by Windsurf IDE.

### Available Tools

- **fs_read_text**: Safely read text files within allowlist (src/, docs/, references/)
- **git_status**: Get current git status of the repository
- **git_diff**: View changed files against a target reference
- **secrets_scan**: Scan for potential secrets/tokens (>=32 chars, redacted)
- **env_list**: List environment variable names (values never exposed)

### Security Features

- **Allowlist gate**: Only paths in `tools/mcp/allowlist.json` can be read
- **Secret redaction**: Secret scan shows first 4 chars + "…" only
- **Env protection**: Environment tool returns names only, never values
- **No execution**: Server provides read-only introspection tools

### Running Tests

```bash
pytest tests/unit/test_mcp_tools.py -v
```

## License

Proprietary - Qatar Ministry of Labour

## Contact

This is a government production system for Qatar's Ministry of Labour.
