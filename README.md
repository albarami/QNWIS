# QNWIS - Qatar National Workforce Intelligence System

Production-grade workforce data intelligence and analysis platform for Qatar's Ministry of Labour.

## System Overview

A deterministic data integration and multi-agent analysis system providing:
- **5 specialized analytical agents** for labour market intelligence
- **Deterministic data layer** with caching, freshness tracking, and provenance
- **FastAPI-based query execution** with TTL-bounded caching and override controls
- **LangGraph orchestration** for multi-step analytical workflows
- **High coverage & type safety**: 90%+ test coverage, strict mypy typing

## Core Components

### Data Layer
- **Deterministic Query API**: Pre-defined queries with caching, normalization, and derived metrics
- **Connectors**: World Bank, Qatar Open Data, CSV catalog integration
- **Cache Backends**: Memory and Redis with TTL management
- **Freshness Tracking**: Data staleness detection and SLA warnings
- **Dataset Catalog**: License enrichment and metadata registry

### Agents Layer
- **LabourEconomistAgent**: Employment trends and YoY growth analysis
- **NationalizationAgent**: GCC unemployment comparisons and rankings
- **SkillsAgent**: Gender distribution and skills proxy analysis
- **PatternDetectiveAgent**: Data quality validation and consistency checks
- **NationalStrategyAgent**: Strategic overview combining multiple sources

### API Layer
- **FastAPI Application**: Async endpoints with request ID tracking
- **Query Endpoints**: List, run, and invalidate cached queries
- **Health Checks**: System status and dependency monitoring
- **Rate Limiting**: Optional RPS throttling

## Project Structure

```
lmis_int/
├── src/qnwis/
│   ├── agents/             # 5 analytical agents + LangGraph workflows
│   ├── data/
│   │   ├── deterministic/  # Query registry, cache, normalization
│   │   ├── derived/        # Metrics computation (share, YoY, CAGR)
│   │   ├── connectors/     # External data source integrations
│   │   ├── catalog/        # Dataset metadata and licensing
│   │   └── validation/     # Data quality verification
│   ├── api/                # FastAPI routers and models
│   ├── utils/              # Request ID, rate limiting, logging
│   └── config/             # Settings management
├── tests/
│   ├── unit/               # 90%+ coverage unit tests
│   └── integration/        # End-to-end API and agent tests
├── docs/                   # Implementation reviews and guides
└── tools/mcp/              # Model Context Protocol server

```

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

Key documentation available in `docs/`:
- `agents_v1.md` - Agent architecture, usage examples, API reference
- `reviews/step4_review.md` - Deterministic data layer v2 validation
- Implementation completion reports: `AGENTS_V1_IMPLEMENTATION_COMPLETE.md`

Additional technical specifications in legacy `docs/` folder (historical reference).

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
