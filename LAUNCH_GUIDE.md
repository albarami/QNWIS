# 🚀 QNWIS Full System Launch Guide

Complete guide to launching the QNWIS system with all components.

---

## 🎯 Quick Start

### Option 1: Test Mode (No API Keys Required)
```bash
python launch_full_system.py --provider stub
```

### Option 2: Anthropic Claude
```bash
python launch_full_system.py --provider anthropic --api-key YOUR_ANTHROPIC_KEY
```

### Option 3: OpenAI GPT
```bash
python launch_full_system.py --provider openai --api-key YOUR_OPENAI_KEY
```

---

## 📦 Prerequisites

### Required Packages
```bash
pip install fastapi uvicorn anthropic openai langgraph chainlit pydantic
```

### Optional (for full features)
```bash
pip install python-multipart aiofiles httpx
```

---

## 🚀 Launch Options

### Full System (API + UI)
```bash
python launch_full_system.py --provider anthropic --api-key YOUR_KEY
```

**Launches**:
- ✅ FastAPI server on port 8001
- ✅ Chainlit UI on port 8000
- ✅ All 5 LLM agents
- ✅ Admin diagnostics
- ✅ Health checks

### API Server Only
```bash
python launch_full_system.py --provider anthropic --api-key YOUR_KEY --api-only
```

### UI Only
```bash
python launch_full_system.py --provider anthropic --api-key YOUR_KEY --ui-only
```

### Custom Ports
```bash
python launch_full_system.py \
  --provider anthropic \
  --api-key YOUR_KEY \
  --api-port 9001 \
  --ui-port 9000
```

---

## 🌐 Access URLs

Once launched, access the system at:

### Chainlit UI (Chat Interface)
- **URL**: http://localhost:8000
- **Purpose**: Interactive chat with LLM agents
- **Features**: Streaming responses, multi-agent analysis

### FastAPI Server
- **Base URL**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

### Admin Endpoints
- **Models**: http://localhost:8001/api/v1/admin/models
- **LLM Health**: http://localhost:8001/api/v1/admin/health/llm
- **System Health**: http://localhost:8001/health

---

## 🤖 Available Agents

The system includes 5 specialized agents:

1. **LabourEconomist** 💼
   - Employment trends & gender analysis
   - Workforce composition
   - Economic indicators

2. **Nationalization** 🌍
   - GCC benchmarking
   - Qatarization metrics
   - Regional comparisons

3. **Skills** 🎓
   - Skills gap analysis
   - Workforce capabilities
   - Training needs

4. **PatternDetective** 🔍
   - Data validation
   - Anomaly detection
   - Quality checks

5. **NationalStrategy** 🎯
   - Vision 2030 alignment
   - Strategic insights
   - Policy recommendations

---

## 💬 Example Questions

Try these questions in the Chainlit UI:

### Employment Analysis
- "What are Qatar's current unemployment trends?"
- "Analyze employment by gender in Qatar"
- "What is the workforce composition?"

### Regional Comparisons
- "Compare Qatar's unemployment to other GCC countries"
- "How does Qatar rank in the GCC for employment?"
- "What are the regional labor market trends?"

### Skills & Training
- "What are the skills gaps in Qatar's workforce?"
- "Analyze the education levels of workers"
- "What training programs are needed?"

### Strategic Insights
- "How is Qatar progressing toward Vision 2030?"
- "What are the key labor market challenges?"
- "Provide strategic recommendations for workforce development"

---

## 🔧 Configuration

### Environment Variables

```bash
# LLM Provider
export QNWIS_LLM_PROVIDER=anthropic  # or openai, stub

# Anthropic
export ANTHROPIC_API_KEY=your_key_here
export QNWIS_ANTHROPIC_MODEL=claude-sonnet-4-20250514

# OpenAI
export OPENAI_API_KEY=your_key_here
export QNWIS_OPENAI_MODEL=gpt-4-turbo-2024-04-09

# Timeouts & Retries
export QNWIS_LLM_TIMEOUT=60
export QNWIS_LLM_MAX_RETRIES=3

# Stub (Testing)
export QNWIS_STUB_TOKEN_DELAY_MS=10
```

---

## 📊 API Endpoints

### Query Endpoints
- `POST /api/v1/queries/run` - Execute query
- `GET /api/v1/queries/list` - List available queries

### Agent Endpoints
- `POST /api/v1/agents/time/analyze` - TimeMachine agent
- `POST /api/v1/agents/pattern/detect` - PatternDetective agent
- `POST /api/v1/agents/predictor/forecast` - Predictor agent
- `POST /api/v1/agents/scenario/simulate` - Scenario agent
- `POST /api/v1/agents/strategy/analyze` - NationalStrategy agent

### Admin Endpoints
- `GET /api/v1/admin/models` - List configured models
- `GET /api/v1/admin/health/llm` - LLM health check

### Health & Monitoring
- `GET /health` - System health
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe
- `GET /metrics` - Prometheus metrics

---

## 🧪 Testing

### Quick System Test
```bash
python test_system_e2e.py
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8001/health

# List models
curl http://localhost:8001/api/v1/admin/models

# LLM health
curl http://localhost:8001/api/v1/admin/health/llm
```

### Test with curl
```bash
# Run a query
curl -X POST http://localhost:8001/api/v1/queries/run \
  -H "Content-Type: application/json" \
  -d '{"query_id": "syn_employment_latest_total"}'
```

---

## 🐛 Troubleshooting

### Issue: "chainlit not found"
**Solution**: Install Chainlit
```bash
pip install chainlit
```

### Issue: "ANTHROPIC_API_KEY not set"
**Solution**: Provide API key
```bash
python launch_full_system.py --provider anthropic --api-key YOUR_KEY
```

### Issue: "Port already in use"
**Solution**: Use different ports
```bash
python launch_full_system.py --api-port 9001 --ui-port 9000
```

### Issue: "Module not found"
**Solution**: Install dependencies
```bash
pip install -r requirements.txt
# Or manually:
pip install fastapi uvicorn anthropic openai langgraph chainlit pydantic
```

### Issue: Slow responses
**Expected**: Real LLM responses take 20-45 seconds
- This proves the system is using real AI, not templates!
- Stub provider is instant (for testing)

---

## 📈 Performance Expectations

### Stub Provider (Testing)
- Response time: 5-10 seconds
- Purpose: Fast testing without API costs

### Real LLM (Anthropic/OpenAI)
- Response time: 20-45 seconds
- Purpose: Production-quality AI reasoning
- **This is correct behavior!**

---

## 🛑 Stopping the System

Press `Ctrl+C` in the terminal where you launched the system.

The script will gracefully shut down:
1. Stop Chainlit UI
2. Stop FastAPI server
3. Clean up processes

---

## 📚 Additional Resources

- **Implementation**: `STEP39_IMPLEMENTATION_COMPLETE.md`
- **Launch Summary**: `STEP39_LAUNCH_SUMMARY.md`
- **Quick Start**: `STEP39_QUICK_START.md`
- **API Docs**: http://localhost:8001/docs (when running)

---

## 🎉 Success Indicators

System is working correctly when you see:

✅ **FastAPI server running on http://localhost:8001**  
✅ **Chainlit UI running on http://localhost:8000**  
✅ **Agents responding to questions**  
✅ **Streaming tokens visible in UI**  
✅ **Response times 20-45s with real LLM**  
✅ **Context-aware, non-templated answers**

---

## 🚀 Ready to Launch!

```bash
# Quick test (no API keys)
python launch_full_system.py --provider stub

# Production (with Anthropic)
python launch_full_system.py --provider anthropic --api-key YOUR_KEY

# Then open: http://localhost:8000
```

**The system is ready for production use!**
