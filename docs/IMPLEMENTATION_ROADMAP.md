# QNWIS Implementation Roadmap
## 37-Step Development Plan (6 Weeks)

**Version:** 1.0  
**Created:** November 2024  
**Purpose:** High-level roadmap for OpenAI orchestration

---

## Overview

**Total Steps:** 37  
**Timeline:** 6 weeks (MVP) + 2 weeks (enhancement) = 8 weeks  
**Approach:** Incremental, one step at a time  
**Quality Gates:** Tests pass + Git push after every step  

**Critical Success Factor:** Build deterministic data layer (Steps 3-5) BEFORE agents (Steps 9-13)

---

## Phase Breakdown

| Phase | Steps | Duration | Focus |
|-------|-------|----------|-------|
| **Phase 1: Data Foundation** | 1-8 | Weeks 2-3 | Setup, DB, **Deterministic Layer**, APIs, Cache |
| **Phase 2: Core Agents** | 9-13 | Week 4 | 5 specialist agents (use Data API only) |
| **Phase 3: Orchestration** | 14-18 | Week 5 | LangGraph workflows, routing |
| **Phase 4: Verification** | 19-22 | Week 6 | 5-layer verification system |
| **Phase 5: Analysis Engines** | 23-27 | Week 6 | Time Machine, Pattern Detective, Predictors |
| **Phase 6: UI & Integration** | 28-32 | Week 7 | Chainlit, dashboards, alerts |
| **Phase 7: Testing & Hardening** | 33-37 | Week 7 | Security, performance, deployment |

---

## PHASE 1: Data Foundation (Weeks 2-3)

### Step 1: Project Structure & Configuration
**Time:** 2 hours  
**Dependencies:** None (first step)

**Description:**
Set up complete project structure with Docker, configuration management (Pydantic), structured logging, and development environment.

**Deliverables:**
- Project directory structure (`/src`, `/tests`, `/config`, `/docs`)
- Configuration system (`settings.py` with Pydantic)
- Logging framework (JSON support, file rotation)
- Docker Compose (PostgreSQL, Redis, App containers)
- Multi-stage Dockerfile (security hardened)
- Requirements files (production + dev)
- `.env.example` template
- Comprehensive README

**Tests:**
- Configuration loads correctly
- Logger produces output
- Docker containers build and start
- All dependencies install

**Git:** Push to `main` or `feature/step-1-project-structure`

---

### Step 2: Database Schema & Models
**Time:** 3 hours  
**Dependencies:** Step 1

**Description:**
Design and implement PostgreSQL database schema for LMIS data (employees, companies, sectors). Create SQLAlchemy models with proper indexes, constraints, and relationships.

**Deliverables:**
- Database schema design document
- SQLAlchemy models:
  - `Employee` (person_id, name, nationality, salary, dates, etc.)
  - `Company` (company_id, name, sector, size)
  - `Sector` (sector codes and descriptions)
  - `EmploymentHistory` (for tracking transitions)
- Alembic migration scripts
- Database indexes (optimized for common queries)
- Seed data scripts (for testing)

**Tests:**
- Models create tables correctly
- Constraints enforced (foreign keys, unique)
- Indexes created
- Sample data loads successfully

**Git:** Push to `feature/step-2-database-schema`

**Critical Note:** Design schema to support longitudinal tracking (8 years of data)

---

### Step 3: Query Registry (Deterministic Data Layer - Part 1) ⚠️ CRITICAL
**Time:** 4 hours  
**Dependencies:** Step 2

**Description:**
Create library of 50+ pre-validated, tested SQL queries. Each query is written by humans (not LLMs), optimized, and security-reviewed. This is the foundation of zero-hallucination architecture.

**Deliverables:**
- `/src/data/query_registry.py` with QueryRegistry class
- 50+ query methods covering:
  - Employee transitions (sector changes, career paths)
  - Retention analysis (by company, sector, cohort)
  - Salary statistics (distributions, percentiles)
  - Qatarization rates (current, historical, trends)
  - Skills gaps (supply vs demand)
  - Pattern detection (attrition predictors, success factors)
  - Competitive intelligence (regional flows)
  - Early warning indicators (15 metrics)
- Each query:
  - Parameterized (SQL injection proof)
  - Documented (inputs, outputs, examples)
  - Unit tested (validates against sample data)
  - Performance optimized

**Tests:**
- All 50+ queries execute successfully
- Queries return expected data structure
- Parameterization prevents SQL injection
- Query performance benchmarks met

**Git:** Push to `feature/step-3-query-registry`

**Critical Note:** This MUST be complete before agent development. Agents will ONLY call these queries.

---

### Step 4: Data Access API (Deterministic Data Layer - Part 2) ⚠️ CRITICAL
**Time:** 3 hours  
**Dependencies:** Step 3

**Description:**
Build high-level Python API that agents call. Wraps Query Registry with QueryResult objects, audit logging, and metadata tracking. Agents never touch SQL - only call these functions.

**Deliverables:**
- `/src/data/data_access.py` with DataAccessAPI class
- QueryResult dataclass (data + metadata)
- High-level functions matching all queries:
  - `get_employee_transitions(...)`
  - `get_retention_by_company(...)`
  - `get_salary_statistics(...)`
  - `get_qatarization_rates(...)`
  - [50+ total functions]
- Each function:
  - Accepts typed parameters
  - Returns QueryResult with:
    - Actual data (list of dicts)
    - Row count
    - Query ID (for reproducibility)
    - Execution timestamp
    - Data sources accessed
    - Freshness indicators
    - Execution time
  - Logs all access for audit
  - Validates results before returning

**Tests:**
- All API functions work correctly
- QueryResult wrapper includes all metadata
- Audit logs capture queries
- Function signatures type-checked

**Git:** Push to `feature/step-4-data-access-api`

**Critical Note:** This is how agents access data. Make API intuitive and well-documented.

---

### Step 5: Number Verification Engine (Deterministic Data Layer - Part 3) ⚠️ CRITICAL
**Time:** 2 hours  
**Dependencies:** Step 4

**Description:**
Build verification engine that validates LLM responses contain only numbers from actual QueryResults. Prevents agents from fabricating data even when given real results.

**Deliverables:**
- `/src/verification/number_verification.py`
- DataVerificationLayer class with methods:
  - `verify_response(response, query_results)` - main verification
  - `_extract_numbers(text)` - parse numbers from text
  - `_extract_numbers_from_results(query_results)` - get all valid numbers
  - `_number_exists_in_data(number, data_numbers)` - check with tolerance
- FabricationError exception for hallucinated numbers
- Verification report generator

**Tests:**
- Correctly extracts numbers from text (234, 18.5, 1,234,567)
- Detects fabricated numbers
- Allows numbers with rounding tolerance (18,234 vs 18,234.56)
- Handles percentages and rates correctly
- Generates clear error messages

**Git:** Push to `feature/step-5-number-verification`

**Critical Note:** This is the final safety layer. Even if agent tries to fabricate, this catches it.

---

### Step 6: LMIS Data Integration
**Time:** 3 hours  
**Dependencies:** Steps 2, 4

**Description:**
Build ETL pipeline to load LMIS data (2.3M employees, 80K companies) into PostgreSQL. Handle data quality issues, deduplication, and validation.

**Deliverables:**
- `/src/data/lmis_loader.py`
- ETL pipeline:
  - Extract from source (CSV/API)
  - Transform (clean, deduplicate, validate)
  - Load to PostgreSQL (bulk insert optimized)
- Data quality checks:
  - Duplicate detection (same person_id)
  - Missing field handling
  - Data type validation
  - Date range validation
- Data quality report generator
- Incremental update support (for ongoing sync)

**Tests:**
- Sample LMIS data loads correctly
- Duplicates handled appropriately
- Data quality checks catch issues
- Performance acceptable (large datasets)

**Git:** Push to `feature/step-6-lmis-integration`

**Critical Note:** Budget time for data cleaning - unglamorous but essential.

---

### Step 7: External API Connectors
**Time:** 3 hours  
**Dependencies:** Step 4

**Description:**
Build connectors for external data sources: GCC-STAT, World Bank, ESCWA, Qatar Open Data, Semantic Scholar. Handle rate limiting, caching, error retry.

**Deliverables:**
- `/src/data/api_connectors/` directory with:
  - `gcc_stat.py` - GCC Statistics connector
  - `world_bank.py` - World Bank API connector
  - `escwa.py` - ESCWA data connector
  - `qatar_open_data.py` - PSA open data
  - `semantic_scholar.py` - Research papers API
  - `base_connector.py` - Shared functionality
- Each connector:
  - Authentication handling
  - Rate limiting (respect API limits)
  - Response caching (Redis)
  - Error handling and retry logic
  - Data freshness tracking
- Unified data format for agents

**Tests:**
- Each API connector works with real endpoints
- Rate limiting prevents throttling
- Caching reduces redundant requests
- Error handling graceful
- Mock versions for testing

**Git:** Push to `feature/step-7-api-connectors`

---

### Step 8: Redis Caching Layer
**Time:** 2 hours  
**Dependencies:** Steps 4, 7

**Description:**
Implement caching layer for query results and API responses. Configure TTLs, cache invalidation, and performance monitoring.

**Deliverables:**
- `/src/cache/cache_manager.py`
- CacheManager class with methods:
  - `get(key)` - Retrieve cached value
  - `set(key, value, ttl)` - Store with expiration
  - `invalidate(pattern)` - Clear specific caches
  - `get_stats()` - Cache hit/miss metrics
- Cache decorators for functions:
  - `@cached(ttl=3600)` - Auto-cache function results
- Cache warming for common queries
- Integration with DataAccessAPI (cache QueryResults)

**Tests:**
- Cache stores and retrieves correctly
- TTLs respected
- Invalidation works
- Performance improvement measurable
- Cache statistics accurate

**Git:** Push to `feature/step-8-caching`

**Phase 1 Complete:** Data foundation solid, deterministic layer operational

---

## PHASE 2: Core Agents (Week 4)

### Step 9: Base Agent Framework
**Time:** 2 hours  
**Dependencies:** Steps 4, 5 (Data API + Verification)

**Description:**
Create base agent class that all specialist agents inherit from. Provides shared functionality: data access, verification integration, logging, result formatting.

**Deliverables:**
- `/src/agents/base_agent.py`
- BaseAgent class with:
  - `__init__(data_api, verification_layer)` - Dependencies injection
  - `_format_query_result(result)` - Format QueryResult for LLM
  - `_format_data_table(data)` - Create readable tables
  - `_format_freshness(freshness)` - Display data ages
  - `_call_llm(prompt)` - Anthropic API wrapper
  - `_verify_response(response, results)` - Auto-verification
- Shared prompt templates
- Error handling patterns
- Response formatting utilities

**Tests:**
- BaseAgent initializes correctly
- Data formatting methods work
- LLM integration functional
- Verification automatically enforced

**Git:** Push to `feature/step-9-base-agent`

**Critical Note:** Agents MUST use DataAccessAPI - enforce in base class.

---

### Step 10: Agent 1 - Labour Market Economist
**Time:** 3 hours  
**Dependencies:** Step 9

**Description:**
Implement specialist agent for macroeconomic labour market analysis. Analyzes sector performance, wage trends, supply-demand dynamics, and economic context.

**Deliverables:**
- `/src/agents/labour_economist.py`
- LabourEconomistAgent class (extends BaseAgent)
- Capabilities:
  - Sector performance analysis
  - Wage trend analysis
  - Labour supply-demand gaps
  - Economic indicators interpretation
  - Regional comparisons (GCC context)
- Integration with:
  - DataAccessAPI (salary stats, sector trends)
  - External APIs (World Bank, GCC-STAT)
- Agent-specific prompts

**Tests:**
- Agent analyzes sector performance correctly
- Uses only DataAccessAPI (no direct SQL)
- Responses cite sources
- Numbers verified against QueryResults

**Git:** Push to `feature/step-10-labour-economist`

---

### Step 11: Agent 2 - Nationalization Strategist
**Time:** 3 hours  
**Dependencies:** Step 9

**Description:**
Implement specialist agent for Qatarization strategy. Identifies opportunities, analyzes retention, plans replacement of expat roles, and recommends interventions.

**Deliverables:**
- `/src/agents/nationalization_strategist.py`
- NationalizationStrategistAgent class
- Capabilities:
  - Qatarization opportunity identification
  - Retention cliff analysis (month 18, 24, 36)
  - Expat role replacement planning
  - Success pathway mapping (career progressions)
  - Intervention recommendations (targeted, data-driven)
- Integration with:
  - Employee transition queries
  - Retention analysis queries
  - Kawader job seeker data

**Tests:**
- Identifies high-opportunity sectors correctly
- Retention analysis accurate
- Recommendations actionable and specific
- All data from DataAccessAPI

**Git:** Push to `feature/step-11-nationalization-strategist`

---

### Step 12: Agent 3 - Skills & Development Analyst
**Time:** 3 hours  
**Dependencies:** Step 9

**Description:**
Implement specialist agent for skills gap analysis and workforce development. Matches education programs to market needs, prioritizes training, and tracks pipeline effectiveness.

**Deliverables:**
- `/src/agents/skills_analyst.py`
- SkillsAnalystAgent class
- Capabilities:
  - Skills gap identification (demand vs supply)
  - Training program prioritization
  - Education-employment pipeline analysis
  - Skills demand forecasting
  - Training ROI measurement
- Integration with:
  - University programs database
  - Job posting data (when available)
  - Skills taxonomy
  - Employment outcomes tracking

**Tests:**
- Skills gaps identified correctly
- Training priorities make sense
- Pipeline analysis accurate
- All recommendations data-backed

**Git:** Push to `feature/step-12-skills-analyst`

---

### Step 13: Agent 4 & 5 - Pattern Detective & National Strategy
**Time:** 4 hours  
**Dependencies:** Step 9

**Description:**
Implement final two specialist agents: Pattern Detective (discovers hidden correlations and root causes) and National Strategy & Competitiveness (GCC positioning, competitive intelligence).

**Deliverables:**
- `/src/agents/pattern_detective.py` 
  - PatternDetectiveAgent class
  - Capabilities:
    - Correlation discovery (non-obvious patterns)
    - Root cause analysis (why X leads to Y)
    - Anomaly detection (outlier companies/sectors)
    - Best practice identification
    - Causal inference

- `/src/agents/national_strategy.py`
  - NationalStrategyAgent class
  - Capabilities:
    - GCC competitive positioning (Qatar vs UAE vs Saudi)
    - Talent flow tracking (regional competition)
    - Economic security monitoring
    - Vision 2030 alignment tracking
    - Geopolitical risk assessment

**Tests:**
- Pattern Detective finds meaningful correlations
- National Strategy Agent provides regional context
- Both agents use only DataAccessAPI
- Responses verified

**Git:** Push to `feature/step-13-final-agents`

**Phase 2 Complete:** All 5 agents operational, using deterministic data layer only

---

## PHASE 3: Orchestration (Week 5)

### Step 14: LangGraph Workflow Foundation
**Time:** 3 hours  
**Dependencies:** Steps 9-13 (all agents)

**Description:**
Set up LangGraph framework for multi-agent orchestration. Define graph structure, state management, and basic routing logic.

**Deliverables:**
- `/src/orchestration/graph.py`
- Workflow components:
  - State definition (AgentState with query, results, reasoning)
  - Graph structure (nodes = agents + functions)
  - Basic edges (simple routing)
  - State persistence (checkpointing)
- Entry point node (receives user query)
- Agent wrapper nodes (call specialist agents)
- Result synthesis node (combines agent outputs)

**Tests:**
- Graph compiles successfully
- State flows between nodes
- Single agent execution works
- State persists correctly

**Git:** Push to `feature/step-14-langgraph-foundation`

---

### Step 15: Query Classification & Routing
**Time:** 3 hours  
**Dependencies:** Step 14

**Description:**
Build intelligent routing that determines which agents are needed based on query analysis. Classifies queries by complexity and topic.

**Deliverables:**
- `/src/orchestration/router.py`
- QueryRouter class with:
  - `classify_query(query)` - Determine query type
    - Simple (single agent, one data call)
    - Medium (2-3 agents, multiple data calls)
    - Complex (4-5 agents, synthesis required)
    - Crisis (urgent, early warning triggered)
  - `route_to_agents(classification)` - Select agents
  - `determine_data_needs(query)` - Pre-fetch data requirements
- Classification criteria:
  - Keywords/topic analysis
  - Complexity indicators
  - Data requirements estimation
  - Response time targets

**Tests:**
- Classification accurate for sample queries
- Routing selects appropriate agents
- Data needs correctly identified
- Performance acceptable (<1 second)

**Git:** Push to `feature/step-15-routing`

---

### Step 16: Multi-Agent Coordination
**Time:** 3 hours  
**Dependencies:** Step 15

**Description:**
Implement coordination logic for multi-agent collaboration. Agents work in parallel or sequence, share context, and build on each other's analysis.

**Deliverables:**
- `/src/orchestration/coordinator.py`
- Coordination patterns:
  - Parallel execution (independent agents)
  - Sequential execution (agent B needs agent A's output)
  - Hierarchical (one agent coordinates others)
- Context sharing between agents
- Intermediate result caching
- Timeout and fallback handling

**Tests:**
- Parallel execution works (multiple agents run simultaneously)
- Sequential dependencies respected
- Context properly shared
- Timeouts handled gracefully

**Git:** Push to `feature/step-16-coordination`

---

### Step 17: Response Synthesis Engine
**Time:** 3 hours  
**Dependencies:** Step 16

**Description:**
Build synthesis engine that combines outputs from multiple agents into coherent, executive-ready response. Removes redundancy, resolves conflicts, structures output.

**Deliverables:**
- `/src/orchestration/synthesizer.py`
- ResponseSynthesizer class with:
  - `synthesize(agent_outputs, query)` - Combine outputs
  - `resolve_conflicts(outputs)` - Handle disagreements
  - `remove_redundancy(text)` - Deduplicate information
  - `structure_response(content)` - Format appropriately
  - `add_executive_summary(content)` - TL;DR at top
- Output formatting:
  - Executive summary (2-3 sentences)
  - Main analysis (paragraphs, not lists)
  - Key findings (bolded)
  - Data sources cited
  - Audit trails included

**Tests:**
- Multiple outputs synthesized coherently
- Conflicts handled appropriately
- Executive summary accurate
- No redundant information

**Git:** Push to `feature/step-17-synthesis`

---

### Step 18: End-to-End Workflow Integration
**Time:** 2 hours  
**Dependencies:** Steps 14-17

**Description:**
Integrate all orchestration components into complete workflow. Test full pipeline from user query to synthesized response.

**Deliverables:**
- `/src/orchestration/workflow.py`
- Complete workflow:
  - Query → Classification → Routing → Agent Execution → Synthesis → Response
- Error handling throughout pipeline
- Performance monitoring (timing each stage)
- Workflow visualization (for debugging)
- Integration tests with real queries

**Tests:**
- End-to-end workflow executes successfully
- All query types handled (simple, medium, complex, crisis)
- Performance acceptable (90 seconds for complex)
- Error handling works at each stage

**Git:** Push to `feature/step-18-workflow-integration`

**Phase 3 Complete:** Orchestration operational, multi-agent coordination working

---

## PHASE 4: Verification (Week 6)

### Step 19: Citation Enforcement System
**Time:** 2 hours  
**Dependencies:** Step 9 (agents)

**Description:**
Implement Layer 2 verification: mandatory citations. Every statistic must be cited with source, otherwise flagged as potential fabrication.

**Deliverables:**
- `/src/verification/citation_enforcer.py`
- CitationEnforcer class with:
  - `enforce_citations(response, query_results)` - Main enforcement
  - `extract_uncited_stats(text)` - Find numbers without citations
  - `validate_citation_format(text)` - Check citation syntax
  - `generate_citation_report(response)` - Audit of sources used
- Citation format: "Per LMIS: [data]" or "According to GCC-STAT: [stat]"
- Auto-flagging of uncited statistics

**Tests:**
- Uncited numbers detected
- Citation format validated
- Properly cited responses pass
- Reports accurate

**Git:** Push to `feature/step-19-citation-enforcement`

---

### Step 20: Automated Result Verification
**Time:** 3 hours  
**Dependencies:** Steps 5 (number verification), 19 (citations)

**Description:**
Implement Layer 3 verification: automated checking of every number against source data. Combines number verification from Step 5 with citation enforcement.

**Deliverables:**
- `/src/verification/result_verifier.py`
- ResultVerifier class integrating:
  - Number verification (from Step 5)
  - Citation enforcement (from Step 19)
  - Cross-reference checking (cited sources match data)
  - Statistical validation (numbers mathematically consistent)
- Verification workflow:
  1. Extract all numbers from response
  2. Check each has citation
  3. Verify number exists in cited QueryResult
  4. Check mathematical consistency (percentages add up, etc.)
  5. Generate verification report
- Automatic rejection if verification fails
- Agent retry with enhanced prompts

**Tests:**
- All verification layers work together
- False positives minimal
- Fabrications caught reliably
- Performance acceptable (<5 seconds)

**Git:** Push to `feature/step-20-result-verification`

---

### Step 21: Audit Trail System Enhancement
**Time:** 2 hours  
**Dependencies:** Steps 4 (QueryResult), 20 (verification)

**Description:**
Enhance Layer 4 verification: complete audit trail. Every response includes query IDs, data sources, timestamps, and reproducibility instructions.

**Deliverables:**
- `/src/verification/audit_trail.py`
- AuditTrail class with:
  - `generate_trail(response, query_results, agent_outputs)` - Create trail
  - `format_for_user(trail)` - User-friendly format
  - `format_for_system(trail)` - Machine-readable format
  - `enable_reproduction(trail)` - Instructions to reproduce
- Trail components:
  - All query IDs used
  - All data sources accessed
  - Timestamps of data retrieval
  - Agent reasoning chains
  - Reproducibility code snippet
- Storage in database (for historical audit)

**Tests:**
- Trails generated for all responses
- Reproducibility instructions work
- Historical trails retrievable
- Format clear and professional

**Git:** Push to `feature/step-21-audit-trail`

---

### Step 22: Confidence Scoring System
**Time:** 2 hours  
**Dependencies:** Step 20 (verification)

**Description:**
Implement confidence scoring for responses. Quantify certainty based on data quality, agent consensus, and evidence strength.

**Deliverables:**
- `/src/verification/confidence_scorer.py`
- ConfidenceScorer class calculating scores from:
  - Data quality (completeness, freshness)
  - Agent consensus (agreement level)
  - Evidence strength (sample size, statistical significance)
  - Verification results (all checks passed?)
- Confidence levels:
  - High (>90%): Strong evidence, agent consensus
  - Medium (70-90%): Good evidence, minor disagreements
  - Low (<70%): Limited evidence, significant uncertainty
- Confidence display in responses
- Threshold enforcement (reject low-confidence responses)

**Tests:**
- Confidence scores reasonable
- Levels correctly assigned
- Low confidence flagged appropriately
- Scores explainable

**Git:** Push to `feature/step-22-confidence-scoring`

**Phase 4 Complete:** 5-layer verification operational (Layer 0-4)

---

## PHASE 5: Analysis Engines (Week 6)

### Step 23: Time Machine Analysis Engine
**Time:** 3 hours  
**Dependencies:** Steps 4 (Data API), 9-13 (agents)

**Description:**
Implement Time Machine capability: reconstruct past with perfect accuracy using 8 years of individual career records. Track any employee's journey through time.

**Deliverables:**
- `/src/analysis/time_machine.py`
- TimeMachineAnalyzer class with:
  - `track_individual(person_id, time_range)` - Individual career path
  - `track_cohort(criteria, time_range)` - Group analysis
  - `find_pathways(from_state, to_state)` - Career progression patterns
  - `analyze_transitions(sector, time_range)` - Sector flows
- Visualization of career paths
- Success factor identification
- Timeline analysis

**Tests:**
- Individual tracking accurate
- Cohort analysis comprehensive
- Pathways identified correctly
- Performance acceptable (large cohorts)

**Git:** Push to `feature/step-23-time-machine`

---

### Step 24: Pattern Detective Engine
**Time:** 3 hours  
**Dependencies:** Steps 4, 9-13

**Description:**
Implement Pattern Detective capability: discover hidden correlations and root causes in 2.3M records. Find insights human analysts cannot see.

**Deliverables:**
- `/src/analysis/pattern_detector.py`
- PatternDetector class with:
  - `find_correlations(variables, threshold)` - Correlation analysis
  - `identify_root_causes(outcome, candidates)` - Causal inference
  - `detect_anomalies(sector, metric)` - Outlier detection
  - `discover_best_practices(success_metric)` - What works
- Statistical methods:
  - Correlation analysis (Pearson, Spearman)
  - Causal inference (matching, regression)
  - Anomaly detection (isolation forest, z-score)
  - Clustering (similar companies/sectors)
- Pattern explanation (why pattern exists)

**Tests:**
- Known correlations detected
- Causal relationships identified
- Anomalies found accurately
- Explanations reasonable

**Git:** Push to `feature/step-24-pattern-detector`

---

### Step 25: Future Predictor Engine
**Time:** 3 hours  
**Dependencies:** Steps 23, 24 (historical patterns)

**Description:**
Implement Future Predictor capability: forecast outcomes based on 8 years of behavioral patterns. Predict what will happen if policy X is implemented.

**Deliverables:**
- `/src/analysis/future_predictor.py`
- FuturePredictor class with:
  - `predict_outcome(policy, parameters)` - Policy impact prediction
  - `simulate_scenario(scenario_spec)` - What-if simulation
  - `forecast_trend(metric, horizon)` - Time series forecasting
  - `identify_risks(scenario)` - Risk assessment
- Prediction methods:
  - Pattern-based (historical analogs)
  - Time series (trend projection)
  - Monte Carlo (probabilistic)
- Confidence intervals for predictions
- Risk quantification

**Tests:**
- Historical predictions validated (backtest)
- Confidence intervals calibrated
- Predictions explainable
- Performance acceptable

**Git:** Push to `feature/step-25-future-predictor`

---

### Step 26: Competitive Intelligence Dashboard
**Time:** 3 hours  
**Dependencies:** Steps 4 (Data API), 7 (external APIs)

**Description:**
Implement Competitive Intelligence capability: real-time Qatar vs GCC positioning, talent flow tracking, early warning of competitor actions.

**Deliverables:**
- `/src/analysis/competitive_intelligence.py`
- CompetitiveIntelligence class with:
  - `analyze_regional_flows(time_range)` - Talent movement
  - `benchmark_sectors(sector)` - Qatar vs GCC
  - `detect_competitor_actions()` - Early warnings
  - `assess_competitive_position(metric)` - Where Qatar stands
- Data integration:
  - LMIS (Qatar outflows)
  - GCC-STAT (regional data)
  - Job postings (competitor recruitment)
- Alerts for competitive threats
- Sector-by-sector battle maps

**Tests:**
- Regional flows tracked accurately
- Benchmarking comprehensive
- Early warnings timely
- Visualizations clear

**Git:** Push to `feature/step-26-competitive-intelligence`

---

### Step 27: Early Warning System
**Time:** 3 hours  
**Dependencies:** Steps 24, 25, 26

**Description:**
Implement Crisis Early Warning System: monitor 15 leading indicators, alert when thresholds crossed, predict crises 3-6 months ahead.

**Deliverables:**
- `/src/analysis/early_warning.py`
- EarlyWarningSystem class monitoring:
  1. Qatari attrition rate (rolling 90-day)
  2. Salary gap vs government
  3. Regional competitor recruitment
  4. Sector retention drops
  5. Mass layoff signals
  6. Skills gap widening
  7. Graduate absorption rate
  8. Kawader registration surge
  9. Inspection violation trends
  10. Company closure rate
  11. Qatarization velocity
  12. Wage stagnation
  13. Expat concentration
  14. Sector volatility
  15. Vision 2030 KPI deviation
- Alert generation:
  - Threshold crossing detection
  - Root cause analysis
  - Impact projection
  - Recommended countermeasures
- Alert prioritization (critical/warning/info)
- Alert routing (who needs to know)

**Tests:**
- All 15 indicators monitored
- Thresholds appropriately set
- Alerts generated correctly
- False positive rate acceptable

**Git:** Push to `feature/step-27-early-warning`

**Phase 5 Complete:** All analysis engines operational

---

## PHASE 6: UI & Integration (Week 7)

### Step 28: Chainlit User Interface
**Time:** 3 hours  
**Dependencies:** Step 18 (workflow)

**Description:**
Build Chainlit web interface for natural language queries. Secure, role-based access, executive-friendly design.

**Deliverables:**
- `/src/ui/chainlit_app.py`
- Chainlit interface with:
  - Natural language query input
  - Real-time response streaming
  - Result visualization (tables, charts)
  - Audit trail viewer
  - Data freshness indicators
  - Query history
- Role-based access control (RBAC):
  - Executive (full access)
  - Analyst (most queries)
  - Viewer (read-only)
- Secure authentication (JWT tokens)
- Mobile-responsive design

**Tests:**
- UI loads correctly
- Queries execute via UI
- RBAC enforced
- Mobile view functional

**Git:** Push to `feature/step-28-chainlit-ui`

---

### Step 29: Executive Dashboards
**Time:** 3 hours  
**Dependencies:** Steps 26 (competitive intelligence), 27 (early warning)

**Description:**
Build executive dashboards showing key metrics, competitive positioning, and early warnings. One-page views for decision-makers.

**Deliverables:**
- `/src/ui/dashboards/` directory with:
  - `executive_summary.py` - Top-level KPIs
  - `competitive_position.py` - Qatar vs GCC
  - `early_warnings.py` - Active alerts
  - `qatarization_progress.py` - Nationalization tracking
  - `sector_health.py` - Sector-by-sector view
- Dashboard features:
  - Auto-refresh (real-time data)
  - Drill-down capability
  - Export to PDF/PowerPoint
  - Multi-language (Arabic/English toggle)
- Visual design:
  - Clean, executive-appropriate
  - Color-coded alerts (red/yellow/green)
  - Trends shown with sparklines
  - Key numbers prominent

**Tests:**
- Dashboards render correctly
- Data updates in real-time
- Exports work
- Language toggle functional

**Git:** Push to `feature/step-29-dashboards`

---

### Step 30: Alert Notification System
**Time:** 2 hours  
**Dependencies:** Step 27 (early warning)

**Description:**
Build notification system for early warning alerts. Email, SMS, and in-app notifications for critical events.

**Deliverables:**
- `/src/notifications/alert_manager.py`
- AlertManager class with:
  - `send_alert(alert, recipients)` - Dispatch notification
  - `route_alert(alert)` - Determine recipients based on severity
  - `format_alert(alert, channel)` - Format for email/SMS/app
  - `track_delivery(alert_id)` - Confirm receipt
- Notification channels:
  - Email (detailed reports)
  - SMS (critical alerts only)
  - In-app (all alerts)
  - Slack webhook (optional)
- Alert scheduling (avoid notification fatigue)
- Delivery confirmation

**Tests:**
- Alerts sent correctly
- Routing appropriate
- Formatting clear
- Delivery tracked

**Git:** Push to `feature/step-30-notifications`

---

### Step 31: API Endpoints (Optional)
**Time:** 2 hours  
**Dependencies:** Step 18 (workflow)

**Description:**
Build REST API for programmatic access. Enables integration with other Ministry systems.

**Deliverables:**
- `/src/api/endpoints.py`
- FastAPI REST endpoints:
  - `POST /query` - Submit query, get response
  - `GET /query/{query_id}` - Retrieve past query
  - `GET /dashboards/{dashboard_type}` - Get dashboard data
  - `GET /alerts/active` - List active alerts
  - `GET /data/qatarization` - Get Qatarization data
  - `GET /health` - System health check
- API authentication (API keys)
- Rate limiting
- OpenAPI documentation

**Tests:**
- All endpoints functional
- Authentication enforced
- Rate limiting works
- Documentation accurate

**Git:** Push to `feature/step-31-api`

---

### Step 32: Multi-Language Support
**Time:** 2 hours  
**Dependencies:** Steps 28, 29 (UI)

**Description:**
Implement Arabic/English language support throughout UI. Executive summaries in both languages.

**Deliverables:**
- `/src/localization/` directory with:
  - `translator.py` - Translation service
  - `ar.json` - Arabic translations
  - `en.json` - English translations
- UI language toggle (persistent preference)
- Automatic translation of:
  - Executive summaries
  - Dashboard labels
  - Alert messages
  - System messages
- RTL support for Arabic
- Language detection (optional)

**Tests:**
- Both languages render correctly
- Toggle works
- RTL layout correct
- Translations accurate

**Git:** Push to `feature/step-32-multilanguage`

**Phase 6 Complete:** User interface operational, production-ready

---

## PHASE 7: Testing & Hardening (Week 7)

### Step 33: Comprehensive Testing Suite
**Time:** 3 hours  
**Dependencies:** All previous steps

**Description:**
Build comprehensive test suite covering unit, integration, and end-to-end tests. Achieve >90% code coverage.

**Deliverables:**
- Expanded test coverage:
  - Unit tests for all modules (>90% coverage)
  - Integration tests for all workflows
  - End-to-end tests (user query → response)
  - Edge case tests (unusual inputs)
  - Error handling tests (failures at each stage)
- Test utilities:
  - Mock data generators
  - Test fixtures
  - Database reset scripts
  - Performance benchmarks
- CI/CD integration:
  - GitHub Actions workflow
  - Automated testing on push
  - Coverage reporting

**Tests:**
- All tests pass
- Coverage >90%
- No flaky tests
- CI/CD pipeline works

**Git:** Push to `feature/step-33-comprehensive-testing`

---

### Step 34: Security Audit & Hardening
**Time:** 3 hours  
**Dependencies:** All previous steps

**Description:**
Conduct security audit, fix vulnerabilities, harden system against attacks.

**Deliverables:**
- Security audit report
- Fixes for:
  - SQL injection risks (verify parameterized queries)
  - XSS vulnerabilities (sanitize UI inputs)
  - CSRF protection (API endpoints)
  - Authentication bypass (verify RBAC)
  - Data exposure (ensure encryption)
  - API rate limiting
- Security enhancements:
  - Input validation everywhere
  - Output sanitization
  - Secrets management (environment variables only)
  - Audit logging (all sensitive operations)
- Penetration testing (basic)
- Security documentation

**Tests:**
- Security scan tools pass (Bandit, Safety)
- Penetration tests fail gracefully
- No secrets in code
- RBAC enforced everywhere

**Git:** Push to `feature/step-34-security-hardening`

---

### Step 35: Performance Optimization
**Time:** 3 hours  
**Dependencies:** Steps 33, 34

**Description:**
Optimize system performance to meet <90 second response time for complex queries. Database tuning, caching optimization, code profiling.

**Deliverables:**
- Performance audit report
- Optimizations:
  - Database query optimization (indexes, explain plans)
  - Redis caching enhancement (optimal TTLs)
  - Code profiling and fixes (hot paths)
  - Async operations where beneficial
  - Connection pooling
  - Query batching
- Performance benchmarks:
  - Simple queries: <10 seconds
  - Medium queries: <30 seconds
  - Complex queries: <90 seconds
  - Dashboard load: <3 seconds
- Monitoring setup (Prometheus + Grafana)

**Tests:**
- All benchmarks met
- No performance regressions
- Monitoring captures metrics
- Load testing passed

**Git:** Push to `feature/step-35-performance`

---

### Step 36: Deployment & DevOps
**Time:** 3 hours  
**Dependencies:** Steps 33-35

**Description:**
Prepare for production deployment. Docker optimization, deployment scripts, monitoring, backup strategies.

**Deliverables:**
- Production Docker configuration:
  - Multi-stage optimized Dockerfile
  - Docker Compose for production
  - Environment-specific configs
- Deployment scripts:
  - Database migration scripts
  - Data seeding scripts
  - Health check endpoints
  - Graceful shutdown
- Monitoring and observability:
  - Application logs (centralized)
  - Performance metrics (response times)
  - Error tracking (Sentry optional)
  - Uptime monitoring
- Backup and recovery:
  - Database backup strategy (daily)
  - Configuration backup
  - Disaster recovery plan
- Deployment documentation

**Tests:**
- Docker deployment works
- Monitoring captures events
- Backups restorable
- Health checks functional

**Git:** Push to `feature/step-36-deployment`

---

### Step 37: Documentation & Handover
**Time:** 2 hours  
**Dependencies:** All previous steps

**Description:**
Complete all documentation for production handover. User guides, API docs, operational runbooks, troubleshooting guides.

**Deliverables:**
- `/docs/` directory with:
  - `USER_GUIDE.md` - End-user documentation
  - `API_REFERENCE.md` - API documentation (auto-generated)
  - `OPERATIONS_RUNBOOK.md` - Operational procedures
  - `TROUBLESHOOTING.md` - Common issues and fixes
  - `ARCHITECTURE.md` - System architecture overview
  - `DEVELOPMENT.md` - Developer onboarding
  - `SECURITY.md` - Security practices
  - `DATA_DICTIONARY.md` - Data schemas
- Video tutorials (optional):
  - Executive user walkthrough
  - Analyst query examples
  - Dashboard navigation
- Handover checklist:
  - All tests passing
  - Documentation complete
  - Deployment ready
  - Training completed
  - Support process defined

**Tests:**
- Documentation complete
- Links work
- Examples accurate
- No TODOs remaining

**Git:** Push to `feature/step-37-documentation`
**Final merge:** Merge all features to `main`
**Tag release:** `v1.0.0`

**Phase 7 Complete:** System production-ready, documented, deployed

---

## Summary: 37 Steps Complete

| Phase | Steps | Key Deliverables |
|-------|-------|------------------|
| **1. Foundation** | 1-8 | Project setup, Database, **Deterministic Data Layer**, APIs, Cache |
| **2. Agents** | 9-13 | 5 specialist agents (using Data API only) |
| **3. Orchestration** | 14-18 | LangGraph workflows, routing, synthesis |
| **4. Verification** | 19-22 | 5-layer verification system |
| **5. Analysis** | 23-27 | Time Machine, Pattern Detective, Predictors, Early Warning |
| **6. UI** | 28-32 | Chainlit interface, dashboards, alerts, API, i18n |
| **7. Hardening** | 33-37 | Testing, security, performance, deployment, docs |

**Total:** 37 steps, 6 weeks, production-ready system

---

## Critical Path Dependencies

**Must Complete in Order:**
1. Steps 1-2 (Foundation) → Required by everything
2. **Steps 3-5 (Deterministic Data Layer)** → Required by agents ⚠️
3. Steps 9-13 (Agents) → Required by orchestration
4. Steps 14-18 (Orchestration) → Required by UI
5. Everything else can parallelize within phases

**Longest Path:** Steps 1-5, 9-13, 14-18 (critical sequence)

---

## Time Estimates Summary

| Step Range | Phase | Estimated Hours | Calendar Days |
|------------|-------|-----------------|---------------|
| 1-8 | Foundation | 20 hours | 3 days |
| 9-13 | Agents | 15 hours | 2 days |
| 14-18 | Orchestration | 14 hours | 2 days |
| 19-22 | Verification | 9 hours | 1.5 days |
| 23-27 | Analysis | 15 hours | 2 days |
| 28-32 | UI | 12 hours | 2 days |
| 33-37 | Hardening | 14 hours | 2 days |
| **Total** | **All Phases** | **99 hours** | **~15 working days** |

**With buffer and meetings:** 6 weeks (30 working days)

---

## Quality Gates (Every Step Must Meet)

✅ **Before "NEXT STEP":**
- All code complete (no placeholders)
- All tests passing (100%)
- Code coverage >90%
- No linter errors
- No security vulnerabilities
- **Git committed and pushed** ⚠️
- Documentation updated
- Claude Code sign-off received

---

## Usage Instructions (For OpenAI)

**When user says "BEGIN QNWIS DEVELOPMENT":**
1. Start with Step 1
2. Generate 3 prompts (CASCADE, CODEX 5, CLAUDE CODE)
3. Wait for completion confirmation

**When user says "NEXT STEP":**
1. Reference this roadmap
2. Generate prompts for next sequential step
3. Check dependencies (previous steps must be complete)
4. Ensure continuity (reference previous step outputs)

**When user asks "WHERE ARE WE?":**
1. Report completed steps
2. Show current step
3. List remaining steps
4. Estimate time to completion

---

## Notes for OpenAI Orchestrator

- **This roadmap is high-level** - You provide detailed specifications
- **Check dependencies** - Don't skip ahead
- **Maintain context** - Each step builds on previous
- **Enforce quality gates** - No step complete until git pushed
- **Adapt as needed** - If step takes longer, acknowledge and adjust
- **Critical path:** Steps 3-5 MUST be complete before Step 9

---

**END OF ROADMAP**

This roadmap guides OpenAI through 37 incremental steps to build production-ready QNWIS system in 6 weeks.
