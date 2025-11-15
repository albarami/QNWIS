# 🚀 Complete QNWIS System Deployment Guide

## Overview
This guide will get the entire QNWIS multi-agent system running with all components operational.

---

## ✅ Prerequisites

- **Python 3.11+**
- **PostgreSQL 14+**
- **Redis 7+**
- **LLM API Key** (Anthropic Claude or OpenAI GPT-4)

---

## 📦 Step 1: Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Verify installation
python -c "import fastapi, langgraph; print('✅ All packages installed')"
```

---

## 🗄️ Step 2: Setup PostgreSQL Database

### Install PostgreSQL
```bash
# Windows: Download from https://www.postgresql.org/download/windows/
# Or use Docker:
docker run -d --name qnwis-postgres \
  -e POSTGRES_PASSWORD=yourpassword \
  -e POSTGRES_DB=qnwis_dev \
  -p 5432:5432 \
  postgres:14
```

### Initialize Database
```bash
# Create database (if not using Docker)
createdb qnwis_dev

# Run schema migrations
python scripts/init_database.py

# Seed with test data
python scripts/seed_employment_quick.py

# Verify
python -c "from sqlalchemy import create_engine; engine = create_engine('postgresql://user:password@localhost:5432/qnwis_dev'); print('✅ Database connected')"
```

---

## 🔴 Step 3: Setup Redis

### Install Redis
```bash
# Option A: Docker (Recommended)
docker run -d --name qnwis-redis -p 6379:6379 redis:latest

# Option B: Windows
# Download from: https://github.com/microsoftarchive/redis/releases

# Verify
redis-cli ping
# Should return: PONG
```

---

## ⚙️ Step 4: Configure Environment

### Create `.env` file

Copy from `.env.example` and update:

```bash
# ========================================
# DATABASE
# ========================================
DATABASE_URL=postgresql://user:password@localhost:5432/qnwis_dev
DB_HOST=localhost
DB_PORT=5432
DB_NAME=qnwis_dev
DB_USER=qnwis_user
DB_PASSWORD=your_secure_password_here

# ========================================
# REDIS
# ========================================
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379

# ========================================
# LLM PROVIDERS (Choose one or both)
# ========================================
# Option A: Anthropic Claude (Recommended)
QNWIS_LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here
QNWIS_ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Option B: OpenAI GPT-4
# QNWIS_LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-your-openai-api-key-here
# QNWIS_OPENAI_MODEL=gpt-4-turbo-preview

# Option C: Stub (Testing only - no real LLM)
# QNWIS_LLM_PROVIDER=stub

# ========================================
# AUTHENTICATION
# ========================================
# JWT secret (minimum 32 characters)
QNWIS_JWT_SECRET=your-super-secret-jwt-key-change-in-production-min-32-chars

# API Keys (format: label:key)
QNWIS_API_KEY_MINISTER=minister:your-secure-minister-api-key-here
QNWIS_API_KEY_ANALYST=analyst:your-secure-analyst-api-key-here
QNWIS_API_KEY_DEVELOPER=developer:your-secure-dev-api-key-here

# For development ONLY (bypasses all auth)
# QNWIS_BYPASS_AUTH=true

# ========================================
# API CONFIGURATION
# ========================================
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
QNWIS_API_URL=http://localhost:8000

# ========================================
# PERFORMANCE
# ========================================
QNWIS_LLM_TIMEOUT=60
QNWIS_LLM_MAX_RETRIES=3
AGENT_TIMEOUT_SECONDS=5

# ========================================
# LOGGING
# ========================================
ENVIRONMENT=development
LOG_LEVEL=INFO
```

---

## 🚀 Step 5: Start All Services

### Option A: Use Startup Script (Recommended)

```bash
# Windows
.\START_SYSTEM.bat

# Linux/Mac
./start_system.sh
```

### Option B: Manual Startup

#### Terminal 1: API Server
```bash
python -m uvicorn src.qnwis.api.server:app --host 127.0.0.1 --port 8000 --reload
```

#### Terminal 2: React UI
```bash
cd qnwis-ui
npm install   # first launch only
npm run dev -- --host 0.0.0.0 --port 3000
```

---

## ✅ Step 6: Verify System

### 1. Check API Health
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

### 2. Test API Endpoint
```bash
curl -X POST http://localhost:8000/api/v1/council/stream \
  -H "Content-Type: application/json" \
  -H "X-API-Key: developer:your-secure-dev-api-key-here" \
  -d '{"question":"What is Qatar unemployment rate?","provider":"stub"}'
```

### 3. Open React UI
```
http://localhost:3000
```

### 4. Run Integration Tests
```bash
# Test citations
python test_citations_now.py

# Test full workflow
python -m pytest tests/unit/orchestration/ -v

# Test API endpoints
python -m pytest tests/integration/api/ -v
```

---

## 🎯 System Components

### Running Services

| Service | URL | Purpose |
|---------|-----|---------|
| **API Server** | http://localhost:8000 | FastAPI backend with LangGraph workflow |
| **React UI** | http://localhost:3000 | Interactive chat interface |
| **PostgreSQL** | localhost:5432 | Database for LMIS data |
| **Redis** | localhost:6379 | Caching and rate limiting |

### Key Features

✅ **5 LLM Agents**
- LabourEconomist
- Nationalization
- Skills
- PatternDetectiveLLM
- NationalStrategyLLM

✅ **3 Deterministic Agents**
- TimeMachine (historical analysis)
- Predictor (forecasting)
- Scenario (what-if analysis)

✅ **LangGraph Workflow**
- Classification → Prefetch → RAG → Agent Selection
- Multi-agent execution with parallel processing
- Debate & Critique for consensus building
- Verification for citation completeness
- Synthesis for final report

✅ **Citation Injection**
- Every number cited with `[Per extraction: 'value' from source period]`
- Fuzzy matching for format variations
- Validation against source data

✅ **Streaming UI**
- Real-time token-by-token generation
- Executive dashboard with KPIs
- Agent findings panel
- Reasoning chain visualization
- Debate and critique summaries

---

## 🔧 Troubleshooting

### Issue: "Redis unavailable"
**Solution**: Ensure Redis is running
```bash
docker ps | grep redis
# Or
redis-cli ping
```

### Issue: "Database connection failed"
**Solution**: Check PostgreSQL is running and credentials are correct
```bash
psql -U qnwis_user -d qnwis_dev -h localhost
```

### Issue: "401 Unauthorized" in UI
**Solution**: Ensure `QNWIS_UI_API_KEY` is set in `.env`
```bash
# Add to .env:
QNWIS_UI_API_KEY=developer:your-secure-dev-api-key-here
```

### Issue: "LLM timeout"
**Solution**: Increase timeout in `.env`
```bash
QNWIS_LLM_TIMEOUT=120
```

### Issue: "No citations in output"
**Solution**: Verify citation injector is working
```bash
python test_citations_now.py
```

---

## 📊 Monitoring

### View Logs
```bash
# API logs
tail -f logs/api.log

# React UI logs (see npm dev server output)
# npm run dev --prefix qnwis-ui -- --host 0.0.0.0 --port 3000
```

### Check System Status
```bash
# API health
curl http://localhost:8000/health

# Database connections
psql -U qnwis_user -d qnwis_dev -c "SELECT count(*) FROM pg_stat_activity;"

# Redis info
redis-cli info stats
```

---

## 🎉 Success Criteria

Your system is fully operational when:

- ✅ API returns 200 on `/health`
- ✅ React UI loads at http://localhost:3000
- ✅ Test query returns agent reports with citations
- ✅ All unit tests pass
- ✅ Database has seeded data
- ✅ Redis is connected

---

## 📚 Next Steps

1. **Configure LLM Provider** - Add real Anthropic or OpenAI API key
2. **Load Production Data** - Import real LMIS data from Qatar MOL
3. **Configure Authentication** - Set up proper JWT secrets and API keys
4. **Deploy to Production** - Follow `PRODUCTION_DEPLOYMENT_GUIDE.md`
5. **Monitor Performance** - Set up Grafana dashboards

---

## 🆘 Support

- **Documentation**: `docs/` directory
- **Tests**: `tests/` directory
- **Examples**: `examples/` directory
- **Issues**: Check `SYSTEM_AUDIT_REPORT.md` for known issues

---

**System Version**: 1.0.0  
**Last Updated**: 2025-01-14  
**Status**: ✅ Production Ready
