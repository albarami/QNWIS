# STEP 39 Quick Start Guide

**Get the LLM-powered system running in 5 minutes**

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install anthropic openai langgraph chainlit pydantic
```

### 2. Set Environment Variables

#### Option A: Use Anthropic (Recommended)
```bash
export QNWIS_LLM_PROVIDER=anthropic
export ANTHROPIC_API_KEY=your_anthropic_key_here
export QNWIS_ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

#### Option B: Use OpenAI
```bash
export QNWIS_LLM_PROVIDER=openai
export OPENAI_API_KEY=your_openai_key_here
export QNWIS_OPENAI_MODEL=gpt-4-turbo-2024-04-09
```

#### Option C: Use Stub (No API Key Needed - For Testing)
```bash
export QNWIS_LLM_PROVIDER=stub
```

### 3. Run Chainlit

```bash
chainlit run src/qnwis/ui/chainlit_app_llm.py
```

### 4. Open Browser

Navigate to: `http://localhost:8000`

### 5. Ask a Question

Try:
- "What are the current unemployment trends in the GCC region?"
- "Analyze Qatar's employment by gender"
- "Compare Qatar to other GCC countries"

---

## ✅ What to Expect

### With Real LLM (Anthropic/OpenAI)
- ⏱️ **Response time**: 20-45 seconds total
- 🔄 **Streaming**: You'll see tokens appear progressively
- 🤖 **Agent reasoning**: Each agent's analysis streams in real-time
- ✨ **Synthesis**: Final answer is LLM-generated, not templated

### With Stub Provider
- ⏱️ **Response time**: 5-10 seconds (simulated)
- 🔄 **Streaming**: Simulated token streaming
- 🤖 **Test data**: Returns mock findings
- ✨ **No API costs**: Perfect for development

---

## 🔍 Verify It's Working

### Check 1: Response Time
- ❌ **BAD**: Instant response (<1 second) = LLM not running
- ✅ **GOOD**: 20-45 seconds = LLM is running

### Check 2: Streaming
- ❌ **BAD**: All text appears at once = No streaming
- ✅ **GOOD**: Text appears word-by-word = Streaming works

### Check 3: Content Quality
- ❌ **BAD**: Same response every time = Templates
- ✅ **GOOD**: Context-aware, varied responses = Real LLM

### Check 4: Agent Execution
- ❌ **BAD**: "Agent completed in 0.02s" = Not using LLM
- ✅ **GOOD**: "Agent completed in 8.5s" = Using LLM

---

## 🐛 Troubleshooting

### Problem: "ANTHROPIC_API_KEY not set"
**Solution**: Export your API key
```bash
export ANTHROPIC_API_KEY=your_key_here
```

### Problem: "anthropic package not installed"
**Solution**: Install the package
```bash
pip install anthropic
```

### Problem: "Request timed out after 60s"
**Solution**: Increase timeout
```bash
export QNWIS_LLM_TIMEOUT=120
```

### Problem: "Rate limit exceeded"
**Solution**: Wait a few seconds and try again, or use stub provider
```bash
export QNWIS_LLM_PROVIDER=stub
```

### Problem: Responses are instant (< 1 second)
**Solution**: Check that LLM provider is set correctly
```bash
# Verify configuration
python -c "from src.qnwis.llm.config import get_llm_config; c = get_llm_config(); print(f'Provider: {c.provider}, Model: {c.get_model()}')"
```

---

## 📊 Test Commands

### Test LLM Client
```python
import asyncio
from src.qnwis.llm.client import LLMClient

async def test():
    client = LLMClient()
    async for token in client.generate_stream(
        prompt="Say hello in 5 words",
        system="You are helpful"
    ):
        print(token, end="", flush=True)
    print()

asyncio.run(test())
```

### Test Agent
```python
import asyncio
from src.qnwis.agents.labour_economist import LabourEconomistAgent
from src.qnwis.agents.base import DataClient
from src.qnwis.llm.client import LLMClient

async def test():
    data_client = DataClient()
    llm_client = LLMClient()
    agent = LabourEconomistAgent(data_client, llm_client)
    
    async for event in agent.run_stream("What are employment trends?"):
        if event["type"] == "token":
            print(event["content"], end="", flush=True)
        elif event["type"] == "complete":
            print("\n\nDone!")

asyncio.run(test())
```

---

## 🎯 Next Steps

1. **Test with real questions** - Try various queries
2. **Check streaming** - Verify tokens appear progressively
3. **Validate responses** - Ensure context-aware answers
4. **Review logs** - Check for errors or warnings
5. **Run tests** - Execute unit and integration tests

---

## 📚 Documentation

- **Full implementation**: See `STEP39_IMPLEMENTATION_COMPLETE.md`
- **Progress tracking**: See `STEP39_PROGRESS.md`
- **Remaining work**: See `STEP39_REMAINING_WORK.md`

---

## 🎉 Success!

If you see:
- ✅ Streaming tokens
- ✅ 20-45 second response times
- ✅ Context-aware answers
- ✅ Agent reasoning displayed

**Congratulations! The LLM-powered system is working!**
