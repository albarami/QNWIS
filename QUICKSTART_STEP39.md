# ⚡ Quick Start - Step 39 Enterprise UI

**5-Minute Setup Guide**

---

## 🚀 Launch in 3 Steps

### 1. Set Environment Variables

```bash
export QNWIS_ENV=dev
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
```

### 2. Launch UI

```bash
cd d:\lmis_int
python -m chainlit run src/qnwis/ui/chainlit_app.py --port 8050
```

### 3. Open Browser

```
http://localhost:8050
```

---

## 💡 Try These Questions

```
"What is Qatar unemployment rate?"

"Forecast Healthcare qatarization for next 12 months"

"What if Construction retention improved by 10%?"

"Compare Qatar labour market to KSA and UAE"

"Detect anomalies in sector attrition rates"
```

---

## 🎨 What You'll See

1. **Timeline Widget** (top-right, updates live)
   - Shows: classify → prefetch → agents → verify → synthesize → done

2. **Per-Agent Cards**
   - Each agent shows: findings, metrics, evidence, confidence
   - Click "View raw evidence" to see deterministic rows

3. **Verification Panel**
   - Citations: ✅ All valid
   - Numeric checks: ✅ All valid
   - Confidence: 🟢 High (85%)
   - Data freshness: 2025-11-08

4. **Audit Trail**
   - Request ID, query IDs, sources
   - Cache stats (hits/misses/rate)
   - Total latency, timestamps

5. **Final Report**
   - Executive summary
   - Key metrics
   - Multi-agent analysis
   - Data sources

---

## 🏗️ Architecture (Why This Design?)

### LangGraph
- **Purpose**: Deterministic workflows with explicit stages
- **Benefit**: Users see progress, not a black box
- **Stages**: classify → route → prefetch → invoke → verify → synthesize

### Multi-Agent Personas
- **Purpose**: Each expert brings different analytic lens
- **Agents**: TimeMachine, Predictor, NationalStrategy, Skills, etc.
- **Benefit**: Rich, multi-faceted analysis with traceable reasoning

### RAG (Retrieval-Augmented Generation)
- **Purpose**: Supplement LMIS with regional/public context
- **Sources**: Qatar PSA, World Bank, GCC-STAT
- **Benefit**: Leaders trust recency and understand methodology
- **Constraint**: Never replaces deterministic data for numbers

---

## 🐛 Common Issues

### "Module not found"
```bash
pip install chainlit anthropic openai pyyaml sqlalchemy
```

### "API key not set"
```bash
echo $ANTHROPIC_API_KEY  # Should show your key
export ANTHROPIC_API_KEY="sk-ant-..."
```

### "Port already in use"
```bash
# Use different port
python -m chainlit run src/qnwis/ui/chainlit_app.py --port 8051
```

---

## 📊 Performance

- **Streaming starts**: <1s ✅
- **Simple queries**: <3s ✅
- **Complex queries**: <10s ✅
- **Cache hit rate**: 85-90% ✅

---

## 📚 Full Documentation

- **Launch Guide**: `STEP39_LAUNCH_GUIDE.md`
- **Implementation Review**: `docs/reviews/step39_review.md`
- **Test Results**: `tests/ui/test_chainlit_orchestration.py`

---

**Ready? Run the commands above! 🚀**
