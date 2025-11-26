# QNWIS System Capabilities Manifesto

**Generated on:** Nov 19, 2025
**Status:** 100% Verified & Operational

This document outlines the full capabilities of the "Legendary 12 Agent System" following a comprehensive codebase audit.

## 1. Core Architecture
- **Orchestration:** LangGraph DAG (Directed Acyclic Graph) with 10 distinct stages.
- **Flow:** Classify → Prefetch → RAG → Agent Selection → Parallel Execution → Debate → Critique → Verify → Synthesize.
- **Routing:** `AgentSelector` maps user intent/entities to 1-12 agents dynamically.
- **Streaming:** Server-Sent Events (SSE) provide real-time telemetry of every step to the React frontend.

## 2. The 12 Agents
The system features a mix of LLM-powered reasoning agents and high-precision deterministic agents.

### LLM Reasoning Agents (Cognitive Layer)
1. **Nationalization Agent**
   - **Role:** Qatarization policy expert & GCC benchmarker.
   - **Capabilities:** Analyzes policy impact on GDP, FDI, and labor markets.
   - **Persona:** Dr. Mohammed Al-Khater (Financial Economist).
   
2. **Skills Agent**
   - **Role:** Workforce development & skills gap analyst.
   - **Capabilities:** Game-theoretic analysis of regional talent competition (vs UAE/Saudi).
   - **Persona:** Dr. Layla Al-Said (Competitiveness Expert).

3. **Pattern Detective (LLM)**
   - **Role:** Data quality & anomaly investigator.
   - **Capabilities:** Semantic analysis of data inconsistencies and outliers.

4. **National Strategy (LLM)**
   - **Role:** Vision 2030 strategic advisor.
   - **Capabilities:** High-level policy alignment and strategic recommendations.

### Deterministic Agents (Precision Layer)
5. **Labour Economist**
   - **Role:** Baseline statistics provider.
   - **Capabilities:** Fetches and formats core employment/unemployment data.

6. **Time Machine**
   - **Role:** Historical analysis.
   - **Capabilities:** Structural break detection (CUSUM), seasonality removal, trend analysis.

7. **Predictor**
   - **Role:** Future forecasting.
   - **Capabilities:** Projects trends forward using statistical models (ARIMA-like logic).

8. **Scenario Agent**
   - **Role:** Simulation engine.
   - **Capabilities:** "What-if" modeling for policy impacts (e.g., "If minimum wage +10%...").

9. **Pattern Miner**
   - **Role:** Deep insight discovery.
   - **Capabilities:** Finds stable relationships and cohorts across historical data windows.

10. **Pattern Detective (Deterministic)**
    - **Role:** Statistical validation.
    - **Capabilities:** Z-score outlier detection, correlation verification.

11. **National Strategy (Deterministic)**
    - **Role:** KPI Tracker.
    - **Capabilities:** Tracks progress against specific numeric Vision 2030 targets.

12. **Alert Center**
    - **Role:** Risk monitoring.
    - **Capabilities:** Scans for critical thresholds (e.g., "Youth unemployment > 5%").

## 3. Data Capabilities
- **Deterministic Layer:** ~45 predefined YAML queries covering employment, attrition, salaries, and demographics.
- **RAG Layer:** Semantic retrieval system ingesting reports from ILO, World Bank, and GCC-STAT to augment agent context.
- **Zero Fabrication:** strict "citation required" rules enforced in prompts and verification logic.

## 4. Unique Features
- **Debate Stage:** Agents challenge each other's findings (e.g., Economist challenges Skills Agent on cost assumptions).
- **Critique Stage:** "Devil's Advocate" review to find logical fallacies.
- **Synthesis:** Final unified report merging all 12 perspectives into a cohesive ministerial brief.

## 5. Verification Status
- **All Agents Active:** `AgentSelector` logic updated to route to all 12 agents.
- **Prompt Safety:** All LLM prompts hardened against JSON formatting errors.
- **Frontend:** Fully connected via SSE with error handling and full narrative display.

The system is now fully understood and mapped.
