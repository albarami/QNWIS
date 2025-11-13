# Step 1 (C2) Packaging & Docs Review

## What changed and why
- **Packaging metadata** – `pyproject.toml` now keeps the ministerial-grade dependency set (FastAPI, SQLAlchemy, Redis, LangChain stack, Anthropic/OpenAI, Chainlit) under the `[project.dependencies]` block and adds `build>=1.0.0` to the `dev` extra so contributors always have the wheel builder handy. The license field was converted to `LicenseRef-Proprietary`, clearing the setuptools deprecation warning observed during the first build attempt.
- **Distribution docs** – `docs/INSTALLATION.md` explains the dev, production, Docker, and verification flows plus a new *Packaging / Wheel Build* section that walks through `python -m build --wheel --sdist` and optional wheel re-install checks, satisfying the “wheel sanity” requirement.
- **CI stub** – Added `.github/workflows/ci.yml` to exercise `pip install -e ".[dev]"` followed by `pytest -v --cov=src` on every push/PR, providing immediate feedback that the packaging metadata stays installable.
- **Build verification** – `python -m build --wheel --sdist` was executed locally after the license update; both artifacts (`qnwis-1.0.0-py3-none-any.whl`, `qnwis-1.0.0.tar.gz`) were produced cleanly and then removed so the workspace remains tidy.

## Dependency conflict risks
- No resolver conflicts surfaced while installing `build` or during the isolated `python -m build` step. The only warnings seen earlier (`~cipy`, `~orch`) stem from the host user site-packages, not from QNWIS metadata.
- Optional extras remain `dev`, `production`, and `all`, matching the roadmap expectations. Because `chainlit>=2.9.0` already depends on modern LangChain packages, we kept explicit pins for `langgraph`, `langchain`, and `langchain-core` to avoid resolver drift.

## Declarative imports (no network at import time)
- Core packages such as `src/qnwis/__init__.py` only expose `__version__` via `importlib.metadata` and defer all API calls until runtime, so `pip install -e .` followed by `pytest` does not require outbound network access. All network credentials remain environment-driven via `.env.example` placeholders, keeping installs declarative.

## Next-step prerequisites
- CI + packaging guardrails are in place (editable install, wheel build, pytest run). Documentation covers dev/prod/Docker/verification paths and explicitly lists the wheel build procedure, so the Step 1 (C2) gate can flow into the remaining ministerial-grade tasks without additional prerequisites.
