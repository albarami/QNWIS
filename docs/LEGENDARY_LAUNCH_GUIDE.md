# QNWIS Legendary Launch & Test Guide

This document explains how to start the full LangGraph multi-agent workflow, verify it produces legendary intelligence, and expose all intermediate reasoning in the new React console.

---

## 1. Prerequisites

1. **Python & Node**
   - Python 3.11+
   - Node.js 20+
2. **Environment**
   - Copy `.env.example` → `.env`
   - Set the Anthropic credentials:
     ```bash
     QNWIS_LLM_PROVIDER=anthropic
     ANTHROPIC_API_KEY=sk-...
     ANTHROPIC_MODEL=claude-sonnet-4-20250514
     ```
   - Ensure Redis is reachable if using rate limits (optional).
3. **Dependencies**
   ```bash
   pip install -r requirements.txt
   cd qnwis-ui && npm install
   ```

---

## 2. Run the Legendary Workflow End-to-End

Open two terminals. All commands assume the repository root (`d:\lmis_int`).

### Terminal A – Backend API (FastAPI + LangGraph)
```bash
python -m uvicorn src.qnwis.api.server:app --host 127.0.0.1 --port 8000 --reload
```
- Uses the real Anthropic client (enforced in `LLMWorkflow`).
- Streams LangGraph events (classify → prefetch → RAG → agents → debate → critique → verify → synthesize).

### Terminal B – React Intelligence Console
```bash
cd qnwis-ui
npm run dev -- --port 3000
```
- Vite will print the actual URL (ex: `http://localhost:3000`).
- The console now renders:
  - Final synthesis w/ confidence badge.
  - **New `AgentOutputs` panel** showing each PhD agent, the multi-agent debate, and devil's advocate critique with Markdown rendering.

---

## 3. Quality Verification

From repo root (`d:\lmis_int`):
```bash
python test_output_quality.py
```
- Confirms 6/6 quality checks (facts, agents, citations, debate, confidence, synthesis).
- Logs debate contradictions and critique severity in the reasoning chain.

---

## 4. Launch Checklist

1. **Backend logs** show each stage completion and debate output length.
2. **UI** displays:
   - Extracted facts table.
   - Stage indicator following LangGraph order.
   - Expandable cards for the five agents.
   - Multi-agent debate + devil's advocate critique sections.
3. **Confidence** near 70–80% with final synthesis referencing debate outcomes.
4. **No emojis** remain in backend logs/prompts (UTF-8 safe).

---

## 5. Troubleshooting

| Symptom | Fix |
|---------|-----|
| UI shows only summary | Ensure `AgentOutputs` component is visible (see `App.tsx`). |
| Debate missing | Check backend logs for `multi_agent_debate` length in `_synthesize_node`. |
| Stub LLM used | Verify `QNWIS_LLM_PROVIDER=anthropic` and `.env` loaded before running scripts. |
| Ports busy | Stop existing `uvicorn`/`npm` processes or choose alternate ports (`--port 3002`). |

---

## 6. Production Handoff Notes

- **Agents**: Labour, Financial, Market, Operations, Research (all run for complex/critical queries).
- **Debate**: Three-phase contradictions → cross-exam → synthesis, forcing disagreements.
- **Critique**: Devil's advocate attack; severity reflected in reasoning chain.
- **UI**: Uses `react-markdown` to render structured outputs; CSS in `src/components/AgentOutputs.css`.
- **Re-run instructions**: Follow Sections 2 & 3 before any demo to guarantee legendary output.

Happy launching! 🚀
