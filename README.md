# QNWIS - Qatar National Workforce Intelligence System

Production Multi-Agent Matching Engine for Qatar's Ministry of Labour.

## System Overview

A high-performance, bias-mitigated job matching system implementing:
- **6 specialized agents** with LangGraph DAG orchestration
- **Stage-based processing**: Stage A (<50ms), Stage B (<60ms), Stage C (<40ms)
- **Intelligent skill inference**: 80% inferred, 20% explicit
- **Bias mitigation**: AraWEAT/SEAT scores <0.15
- **Performance targets**: NDCG@10 0.70-0.80, MRR >0.75

## Project Structure

```
lmis_int/
├── src/
│   └── qnwis/              # Main application package
│       ├── agents/         # 6 specialized agents
│       ├── models/         # Pydantic data models
│       ├── services/       # Business logic services
│       ├── api/            # FastAPI endpoints
│       ├── db/             # Database models and migrations
│       └── config/         # Configuration management
├── tests/                  # Pytest test suite
├── docs/                   # Technical documentation
├── external_data/          # External datasets
└── metadata/               # System metadata

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
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis for performance optimization
- **Orchestration**: LangGraph for agent DAG
- **Testing**: pytest with async support
- **Type Checking**: mypy strict mode
- **Linting**: ruff + flake8
- **Code Formatting**: black + isort

## Performance Requirements

- Stage A latency: <50ms
- Stage B latency: <60ms
- Stage C latency: <40ms
- NDCG@10: 0.70-0.80
- MRR: >0.75

## Documentation

Detailed documentation available in `docs/`:
- `Enhanced_Cutting_Edge_Multi_Agent_Matching_1.md` - Core specifications
- `Complete_Implementation_Plan_And_Development_Roadmap.md` - Technical details
- `Complete_Database_Schema_Document.md` - Database structure
- `Complete_API_Specification.md` - API contracts

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
