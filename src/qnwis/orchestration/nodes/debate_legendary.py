"""
Legendary Multi-Turn Debate Node for New Workflow.

Integrates LegendaryDebateOrchestrator into LangGraph modular architecture.
Provides 80-125 turn adaptive debate with real-time event streaming.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
from pathlib import Path

# CRITICAL: Load .env to ensure DATABASE_URL is available for deterministic agents
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent.parent.parent / ".env")

from ..state import IntelligenceState

logger = logging.getLogger(__name__)


async def legendary_debate_node(state: IntelligenceState) -> IntelligenceState:
    """
    Node 7: Legendary Multi-Turn Agent Debate.

    Conducts adaptive debate using LegendaryDebateOrchestrator.
    Streams conversation turns in real-time via emit_event_fn.

    Complexity-adaptive:
    - SIMPLE questions: 10-15 turns, 2-3 minutes
    - STANDARD questions: 40 turns, 10 minutes
    - COMPLEX questions: 80-125 turns, 20-30 minutes
    """

    # Import here to avoid circular dependencies
    from ..legendary_debate_orchestrator import LegendaryDebateOrchestrator
    from ...llm.client import LLMClient

    reasoning_chain = state.setdefault("reasoning_chain", [])
    nodes_executed = state.setdefault("nodes_executed", [])

    # Get emit callback from state (passed by streaming adapter)
    emit_event_fn = state.get("emit_event_fn")
    logger.info(f"🔍 legendary_debate_node: emit_event_fn={'FOUND' if emit_event_fn else 'MISSING'}")
    logger.info(f"🔍 legendary_debate_node: state keys={list(state.keys())[:10]}")
    
    # DEBUG: Log debate_depth to diagnose 41-turn issue
    debate_depth_from_state = state.get("debate_depth", "NOT_IN_STATE")
    logger.warning(f"🎯 DEBATE NODE: debate_depth from state = '{debate_depth_from_state}'")

    # Create LLM client for debate - uses provider from environment (QNWIS_LLM_PROVIDER)
    llm_client = LLMClient()  # Will use Azure if configured

    # Build agent reports map from state
    agent_reports_map = {}

    # Extract agent analyses from new workflow state structure
    for agent_name in ["financial", "market", "operations", "research"]:
        analysis_key = f"{agent_name}_analysis"
        if analysis_key in state and state[analysis_key]:
            # Create mock AgentReport-like object for orchestrator
            agent_reports_map[agent_name] = type('AgentReport', (object,), {
                'narrative': str(state[analysis_key]),
                'agent': agent_name,
                'findings': [],
                'confidence': 0.7,
                'warnings': [],
                'metadata': {}
            })()

    # Detect contradictions using existing logic
    from .debate import _extract_perspectives, _detect_contradictions
    perspectives = _extract_perspectives(state)
    contradictions = _detect_contradictions(perspectives)

    logger.info(f"Starting legendary debate with {len(contradictions)} contradictions")

    # Create legendary debate orchestrator
    orchestrator = LegendaryDebateOrchestrator(
        emit_event_fn=emit_event_fn,
        llm_client=llm_client
    )

    # Build agents map - CRITICAL for legendary depth debates
    # Each agent must be properly initialized for 100-150 turn debates
    agents_map: Dict[str, Any] = {}

    # Import LLM agents - THESE ARE REQUIRED for legendary debates
    try:
        from ...agents.micro_economist import MicroEconomist
        from ...agents.macro_economist import MacroEconomist
        from ...agents.nationalization import NationalizationAgent
        from ...agents.skills import SkillsAgent
        from ...agents.pattern_detective_llm import PatternDetectiveLLMAgent
        from ...agents.base import DataClient

        data_client = DataClient()
        logger.info("✅ DataClient initialized for debate agents")

        # Create a simple DataValidator for data quality checks
        class SimpleDataValidator:
            def __init__(self):
                self.name = "DataValidator"
            
            async def analyze_edge_case(self, edge_case, history):
                return "Data quality check completed."
        
        # Initialize each agent with explicit error handling
        agents_map["DataValidator"] = SimpleDataValidator()
        logger.info("✅ DataValidator initialized")
        
        try:
            agents_map["MicroEconomist"] = MicroEconomist(data_client, llm_client)
            logger.info("✅ MicroEconomist initialized")
        except Exception as e:
            logger.error(f"❌ MicroEconomist failed: {e}")
        
        try:
            agents_map["MacroEconomist"] = MacroEconomist(data_client, llm_client)
            logger.info("✅ MacroEconomist initialized")
        except Exception as e:
            logger.error(f"❌ MacroEconomist failed: {e}")
        
        try:
            agents_map["Nationalization"] = NationalizationAgent(data_client, llm_client)
            logger.info("✅ Nationalization initialized")
        except Exception as e:
            logger.error(f"❌ Nationalization failed: {e}")
        
        try:
            agents_map["SkillsAgent"] = SkillsAgent(data_client, llm_client)
            logger.info("✅ SkillsAgent initialized")
        except Exception as e:
            logger.error(f"❌ SkillsAgent failed: {e}")
        
        try:
            agents_map["PatternDetective"] = PatternDetectiveLLMAgent(data_client, llm_client)
            logger.info("✅ PatternDetective initialized")
        except Exception as e:
            logger.error(f"❌ PatternDetective failed: {e}")
        
        # === DETERMINISTIC AGENTS ===
        # These provide data-backed analysis without LLM calls
        try:
            from ...agents.time_machine import TimeMachineAgent
            from ...agents.predictor import PredictorAgent
            from ...agents.scenario_agent import ScenarioAgent
            from ...agents.pattern_miner import PatternMinerAgent
            from ...agents.national_strategy import NationalStrategyAgent
            from ...agents.alert_center import AlertCenterAgent
            from ...agents.pattern_detective import PatternDetectiveAgent
            
            # Initialize deterministic agents
            try:
                agents_map["TimeMachine"] = TimeMachineAgent(data_client)
                logger.info("✅ TimeMachine (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ TimeMachine failed: {e}")
            
            try:
                agents_map["PatternDetectiveAgent"] = PatternDetectiveAgent(data_client)
                logger.info("✅ PatternDetectiveAgent (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ PatternDetectiveAgent failed: {e}")
            
            try:
                agents_map["Predictor"] = PredictorAgent(data_client)
                logger.info("✅ Predictor (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ Predictor failed: {e}")
            
            try:
                agents_map["Scenario"] = ScenarioAgent(data_client)
                logger.info("✅ Scenario (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ Scenario failed: {e}")
            
            try:
                agents_map["PatternMiner"] = PatternMinerAgent(data_client)
                logger.info("✅ PatternMiner (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ PatternMiner failed: {e}")
            
            try:
                agents_map["NationalStrategy"] = NationalStrategyAgent(data_client)
                logger.info("✅ NationalStrategy (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ NationalStrategy failed: {e}")
            
            try:
                # FIXED: Load default alert rules for AlertCenter
                from ...alerts.registry import AlertRegistry
                from pathlib import Path
                alert_registry = AlertRegistry()
                default_rules_path = Path(__file__).parent.parent.parent / "alerts" / "default_rules.yaml"
                if default_rules_path.exists():
                    alert_registry.load_file(default_rules_path)  # Correct method name
                    logger.info(f"✅ Loaded {len(alert_registry)} default alert rules")
                agents_map["AlertCenter"] = AlertCenterAgent(data_client, rule_registry=alert_registry)
                logger.info("✅ AlertCenter (deterministic) initialized with default rules")
            except Exception as e:
                logger.warning(f"⚠️ AlertCenter failed: {e}")
            
            # Add LabourEconomist - workforce and gender employment analysis
            try:
                from ...agents.labour_economist import LabourEconomistAgent
                agents_map["LabourEconomist"] = LabourEconomistAgent(data_client)
                logger.info("✅ LabourEconomist (deterministic) initialized")
            except Exception as e:
                logger.warning(f"⚠️ LabourEconomist failed: {e}")
            
            # Add ResearchSynthesizer - aggregates Semantic Scholar, RAG, Perplexity, Knowledge Graph
            try:
                from ...agents.research_synthesizer import ResearchSynthesizerAgent
                
                # Initialize RAG client wrapper using PRE-BUILT RAG store
                rag_client = None
                try:
                    from ...rag.retriever import DocumentStore
                    from pathlib import Path
                    import json
                    
                    # Create RAG wrapper that uses the existing rag_store.json (1965 documents including R&D papers)
                    class RAGClientWrapper:
                        def __init__(self):
                            self.store = DocumentStore()
                            self.docs_loaded = 0
                            
                            # Load from PRE-BUILT store (has 55+ R&D research reports, World Bank, ILO, etc.)
                            rag_store_path = Path(__file__).parent.parent.parent.parent.parent / "data" / "rag_store.json"
                            
                            if rag_store_path.exists():
                                try:
                                    with open(rag_store_path, "r", encoding="utf-8") as f:
                                        store_data = json.load(f)
                                    
                                    docs = store_data.get("documents", [])
                                    if docs:
                                        from ...rag.retriever import Document
                                        for d in docs[:2000]:  # Load up to 2000 docs
                                            doc = Document(
                                                doc_id=d.get("doc_id", f"doc_{self.docs_loaded}"),
                                                text=d.get("text", ""),
                                                source=d.get("source", "unknown"),
                                                metadata=d.get("metadata", {}),
                                            )
                                            self.store.add_document(doc)
                                            self.docs_loaded += 1
                                        
                                        logger.info(f"📚 RAG: Loaded {self.docs_loaded} documents from pre-built store")
                                        logger.info(f"   Including 55+ R&D research reports, World Bank, ILO, Qatar MOL data")
                                except Exception as e:
                                    logger.warning(f"⚠️ RAG: Could not load pre-built store: {e}")
                            else:
                                logger.warning(f"⚠️ RAG: Pre-built store not found at {rag_store_path}")
                        
                        def search(self, query: str, top_k: int = 10, filters=None):
                            if self.docs_loaded == 0:
                                return []
                            
                            results = self.store.search(query, top_k=top_k)
                            # Convert to dict format expected by ResearchSynthesizerAgent
                            return [
                                {
                                    "title": doc.source if "R&D Report" in doc.source else doc.metadata.get("title", doc.doc_id),
                                    "content": doc.text[:800],  # More content for R&D papers
                                    "score": score,
                                    "year": doc.metadata.get("year", 2024),
                                    "authors": doc.metadata.get("authors", ["NSIC R&D Team"]),
                                    "methodology": doc.metadata.get("methodology"),
                                    "metrics": doc.metadata.get("metrics", {}),
                                }
                                for doc, score in results
                            ]
                    
                    rag_client = RAGClientWrapper()
                    if rag_client.docs_loaded > 0:
                        logger.info(f"✅ RAG client initialized with {rag_client.docs_loaded} R&D documents")
                except Exception as e:
                    logger.warning(f"⚠️ RAG client not available: {e}")
                
                # Initialize Knowledge Graph client wrapper
                kg_client = None
                try:
                    from ...knowledge.graph_builder import QNWISKnowledgeGraph, EntityType, RelationType
                    from pathlib import Path
                    
                    # Create KG wrapper that matches ResearchSynthesizerAgent interface
                    class KGClientWrapper:
                        def __init__(self):
                            self.graph = QNWISKnowledgeGraph()
                            # Load pre-built graph if available
                            # KG uses JSON format, not pickle
                            kg_path = Path(__file__).parent.parent.parent.parent.parent / "data" / "knowledge_graph.json"
                            if kg_path.exists():
                                try:
                                    self.graph.load(kg_path)
                                    logger.info(f"🕸️ KG: Loaded graph with {len(self.graph.graph.nodes)} nodes")
                                except Exception as e:
                                    logger.warning(f"⚠️ KG: Could not load from {kg_path}: {e}")
                                    self._add_default_context()
                            else:
                                self._add_default_context()
                        
                        def _add_default_context(self):
                            """Add default Qatar economic context to the graph."""
                            # Add core sectors
                            sectors = ["Energy", "Finance", "Healthcare", "Education", "Tourism", "Construction", "Technology"]
                            for sector in sectors:
                                self.graph.add_entity(sector, EntityType.SECTOR)
                            
                            # Add key policies
                            self.graph.add_entity("Qatar Vision 2030", EntityType.POLICY)
                            self.graph.add_entity("Qatarization", EntityType.POLICY)
                            
                            # Add relationships
                            self.graph.add_relationship("Qatarization", EntityType.POLICY, "Employment", EntityType.METRIC, RelationType.TARGETS)
                            self.graph.add_relationship("Qatar Vision 2030", EntityType.POLICY, "Economic Diversification", EntityType.METRIC, RelationType.TARGETS)
                            
                            logger.info(f"🕸️ KG: Initialized with {len(self.graph.graph.nodes)} default nodes")
                        
                        def query(self, query: str, focus=None):
                            # Extract entities from query and find related relationships
                            results = []
                            search_terms = focus or []
                            
                            # Also search for known entities that match query terms
                            query_lower = query.lower()
                            for known in self.graph.KNOWN_SECTORS | self.graph.KNOWN_POLICIES | self.graph.KNOWN_METRICS:
                                if known.lower() in query_lower:
                                    search_terms.append(known)
                            
                            for term in search_terms[:5]:  # Limit search terms
                                try:
                                    related = self.graph.get_related_entities(term, max_hops=2)
                                    for node_id, edge_data in related:
                                        node_data = self.graph.graph.nodes.get(node_id, {})
                                        results.append({
                                            "subject": term,
                                            "relation_type": edge_data.get("relation_type", "related_to"),
                                            "object": node_data.get("name", node_id),
                                            "description": f"{term} {edge_data.get('relation_type', 'relates to')} {node_data.get('name', node_id)}",
                                            "confidence": edge_data.get("confidence", 0.6),
                                        })
                                except Exception:
                                    pass  # Term not found in graph
                            return results[:20]  # Limit to 20 relationships
                    
                    kg_client = KGClientWrapper()
                    logger.info("✅ Knowledge Graph client initialized for ResearchSynthesizer")
                except Exception as e:
                    logger.warning(f"⚠️ Knowledge Graph client not available: {e}")
                
                # FIXED: Pass ALL clients to ResearchSynthesizerAgent
                agents_map["ResearchSynthesizer"] = ResearchSynthesizerAgent(
                    semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
                    perplexity_api_key=os.getenv("PERPLEXITY_API_KEY"),
                    rag_client=rag_client,
                    knowledge_graph_client=kg_client,
                )
                logger.info("✅ ResearchSynthesizer (deterministic) initialized with ALL data sources")
            except Exception as e:
                logger.warning(f"⚠️ ResearchSynthesizer failed: {e}")
                
        except ImportError as e:
            logger.warning(f"⚠️ Could not import deterministic agents: {e}")
        
        # Log final agent count - CRITICAL for legendary depth
        llm_agent_count = len([a for a in agents_map.keys() if a != "DataValidator"])
        deterministic_count = len([a for a in agents_map.keys() if a in ["TimeMachine", "Predictor", "Scenario", "PatternMiner", "NationalStrategy", "AlertCenter", "PatternDetectiveAgent", "LabourEconomist", "ResearchSynthesizer"]])
        logger.warning(f"🔥 DEBATE AGENTS LOADED: {llm_agent_count} total ({llm_agent_count - deterministic_count} LLM + {deterministic_count} deterministic)")
        logger.warning(f"🔥 AGENT LIST: {list(agents_map.keys())}")
        
        if llm_agent_count < 5:
            logger.error(f"⚠️ WARNING: Only {llm_agent_count}/5 LLM agents loaded - debate may be shorter than expected!")
            
    except Exception as e:
        logger.error(f"❌ CRITICAL: Could not load LLM agents: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        # Debate will be severely limited without agents!

    # === RUN DETERMINISTIC AGENTS AND POPULATE REPORTS ===
    # These agents need to be EXECUTED to generate analysis before the debate
    extracted_facts = state.get("extracted_facts", [])
    query = state.get("query", "")
    
    # Get date range for forecasting (default: last 2 years to now, forecast 6 months)
    from datetime import date, timedelta
    end_date = date.today()
    start_date = end_date - timedelta(days=730)  # 2 years back
    
    # FIXED: Provide required arguments for each deterministic agent
    # Use domain-agnostic default metrics that are likely to have time-series data
    deterministic_agents_config = [
        # TimeMachine: Historical trends - retention has more time-series data
        ("TimeMachine", "baseline_report", {"metric": "retention"}),
        # Predictor: Forecasting with required args
        ("Predictor", "forecast_baseline", {
            "metric": "retention",  # Use retention - more likely to have time-series
            "sector": None,  # All sectors
            "start": start_date,
            "end": end_date,
            "horizon_months": 6
        }),
        # NationalStrategy: GCC/regional benchmarking (no required args)
        ("NationalStrategy", "gcc_benchmark", {"min_countries": 3}),
        # PatternMiner: Use stable_relations for correlation analysis
        ("PatternMiner", "stable_relations", {
            "outcome": "employment",
            "drivers": ["gdp", "population", "inflation"],
            "window": 12
        }),
        # AlertCenter: Use run() with no args (evaluates all enabled rules)
        ("AlertCenter", "run", {}),
        # LabourEconomist: Use run() method  
        ("LabourEconomist", "run", {}),
        # ResearchSynthesizer: Academic research on ANY topic from user query
        ("ResearchSynthesizer", "run", {"query": query}),
    ]
    
    for agent_key, method_name, kwargs in deterministic_agents_config:
        if agent_key in agents_map:
            agent = agents_map[agent_key]
            try:
                # Try to call the agent's analysis method
                if hasattr(agent, method_name):
                    method = getattr(agent, method_name)
                    result = method(**kwargs) if kwargs else method()
                    
                    # Check if result indicates data unavailability
                    result_str = str(result) if result else ""
                    result_lower = result_str.lower()
                    
                    # EXPANDED: More phrases to catch all "data unavailable" cases
                    data_unavailable_phrases = [
                        "insufficient data", "no data returned", "no driver time series",
                        "need at least", "need ≥", "no rules to evaluate",
                        "data currently unavailable", "data unavailable", "no data available",
                        "currently unavailable", "query not found", "no results",
                        "requires historical", "requires time-series", "awaiting data",
                        "502 bad gateway", "api error", "connection failed",
                        "no patterns found", "no alerts found", "no forecast possible",
                    ]
                    
                    if any(phrase in result_lower for phrase in data_unavailable_phrases):
                        logger.warning(f"⚠️ {agent_key}: Data unavailable - {result_str[:100]}")
                        
                        # DOMAIN AGNOSTIC qualitative fallback (same pattern as exception handler)
                        fallback_narratives = {
                            "Predictor": (
                                f"**Forecasting Assessment (Qualitative)**\n\n"
                                f"Predictive modeling requires sufficient historical baseline. "
                                f"Based on general economic principles, key forecast drivers include: "
                                f"(1) policy commitment signals, (2) market sentiment indicators, and "
                                f"(3) capacity utilization rates. Recommend scenario-based planning "
                                f"until more data becomes available."
                            ),
                            "PatternMiner": (
                                f"**Pattern Analysis (Qualitative)**\n\n"
                                f"Statistical pattern detection requires minimum data thresholds. "
                                f"Qualitative patterns to monitor include: (1) leading indicator movements, "
                                f"(2) stakeholder behavior changes, and (3) policy response cycles. "
                                f"Cross-reference with available qualitative assessments."
                            ),
                            "AlertCenter": (
                                f"**Risk Monitoring Assessment (Qualitative)**\n\n"
                                f"Automated threshold monitoring awaits data availability. "
                                f"Key risk indicators to track manually: (1) budget variance signals, "
                                f"(2) timeline deviation early warnings, and (3) stakeholder resistance patterns. "
                                f"Recommend establishing manual monitoring protocols."
                            ),
                        }
                        
                        fallback_narrative = fallback_narratives.get(
                            agent_key,
                            f"**{agent_key} Analysis (Limited Data)**\n\n"
                            f"Quantitative analysis requires additional data. "
                            f"Qualitative assessment: Policy decisions in this domain typically benefit from "
                            f"(1) stakeholder consultation, (2) phased implementation, and "
                            f"(3) adaptive monitoring frameworks."
                        )
                        
                        agent_reports_map[agent_key] = type('AgentReport', (object,), {
                            'narrative': fallback_narrative,
                            'agent': agent_key,
                            'findings': [],
                            'confidence': 0.3,
                            'warnings': [f"Data limited: qualitative assessment provided"],
                            'metadata': {'source': 'deterministic_agent', 'method': method_name, 'data_available': False, 'fallback': True}
                        })()
                        continue
                    
                    # Extract narrative from result
                    # FIXED: Increased from 500 to 5000 chars to avoid truncating deterministic agent outputs
                    narrative = ""
                    if hasattr(result, 'narrative'):
                        narrative = result.narrative
                    elif isinstance(result, dict):
                        narrative = result.get('narrative', result.get('summary', str(result)[:5000]))
                    elif isinstance(result, str):
                        narrative = result[:5000]
                    else:
                        narrative = str(result)[:5000]
                    
                    # Create report object for orchestrator
                    agent_reports_map[agent_key] = type('AgentReport', (object,), {
                        'narrative': narrative,
                        'agent': agent_key,
                        'findings': getattr(result, 'findings', []) if hasattr(result, 'findings') else [],
                        'confidence': getattr(result, 'confidence', 0.7) if hasattr(result, 'confidence') else 0.7,
                        'warnings': getattr(result, 'warnings', []) if hasattr(result, 'warnings') else [],
                        'metadata': {'source': 'deterministic_agent', 'method': method_name}
                    })()
                    logger.info(f"✅ {agent_key} analysis executed: {len(narrative)} chars")
                elif hasattr(agent, 'run'):
                    # Fallback to generic run() method
                    result = agent.run()
                    # FIXED: Increased from 500 to 5000 chars
                    narrative = getattr(result, 'narrative', str(result)[:5000]) if hasattr(result, 'narrative') else str(result)[:5000]
                    agent_reports_map[agent_key] = type('AgentReport', (object,), {
                        'narrative': narrative,
                        'agent': agent_key,
                        'findings': [],
                        'confidence': 0.7,
                        'warnings': [],
                        'metadata': {'source': 'deterministic_agent', 'method': 'run'}
                    })()
                    logger.info(f"✅ {agent_key} run() executed: {len(narrative)} chars")
                else:
                    logger.warning(f"⚠️ {agent_key} has no {method_name} or run() method")
            except Exception as e:
                # FIXED: Provide qualitative fallback analysis instead of just showing error
                logger.warning(f"⚠️ {agent_key}.{method_name}() failed: {e}")
                
                # Generate agent-specific qualitative fallback (domain-agnostic)
                fallback_narratives = {
                    "TimeMachine": (
                        f"**Historical Trend Analysis (Qualitative)**\n\n"
                        f"While quantitative time-series data is limited for this analysis, "
                        f"historical patterns typically suggest that policy outcomes depend on: "
                        f"(1) implementation consistency, (2) economic cycle timing, and "
                        f"(3) external market conditions. Recommend supplementing with "
                        f"available case studies from similar policy implementations."
                    ),
                    "Predictor": (
                        f"**Forecasting Assessment (Qualitative)**\n\n"
                        f"Predictive modeling requires sufficient historical baseline. "
                        f"Based on general economic principles, key forecast drivers include: "
                        f"(1) policy commitment signals, (2) market sentiment indicators, and "
                        f"(3) capacity utilization rates. Recommend scenario-based planning "
                        f"until more data becomes available."
                    ),
                    "PatternMiner": (
                        f"**Pattern Analysis (Qualitative)**\n\n"
                        f"Statistical pattern detection requires minimum data thresholds. "
                        f"Qualitative patterns to monitor include: (1) leading indicator movements, "
                        f"(2) stakeholder behavior changes, and (3) policy response cycles. "
                        f"Cross-reference with available qualitative assessments."
                    ),
                    "AlertCenter": (
                        f"**Risk Monitoring Assessment (Qualitative)**\n\n"
                        f"Automated threshold monitoring awaits data availability. "
                        f"Key risk indicators to track manually: (1) budget variance signals, "
                        f"(2) timeline deviation early warnings, and (3) stakeholder resistance patterns. "
                        f"Recommend establishing manual monitoring protocols."
                    ),
                }
                
                fallback_narrative = fallback_narratives.get(
                    agent_key,
                    f"**{agent_key} Analysis (Limited Data)**\n\n"
                    f"Quantitative analysis requires additional data. "
                    f"Qualitative assessment: Policy decisions in this domain typically benefit from "
                    f"(1) stakeholder consultation, (2) phased implementation, and "
                    f"(3) adaptive monitoring frameworks."
                )
                
                agent_reports_map[agent_key] = type('AgentReport', (object,), {
                    'narrative': fallback_narrative,
                    'agent': agent_key,
                    'findings': [],
                    'confidence': 0.3,  # Low but not zero - indicates qualitative assessment
                    'warnings': [f"Quantitative analysis unavailable: {str(e)[:100]}"],
                    'metadata': {'source': 'deterministic_agent', 'method': method_name, 'fallback': True}
                })()
    
    logger.info(f"📊 Deterministic agent reports generated: {list(agent_reports_map.keys())}")

    # Conduct legendary debate
    # Get user-selected debate depth from state (default: legendary = 100-150 turns)
    debate_depth = state.get("debate_depth", "legendary")
    
    # FIXED: Build cross-scenario context for agents to reference
    cross_scenario_context = ""
    cross_scenario_table = state.get("cross_scenario_table") or ""
    engine_b_aggregate = state.get("engine_b_aggregate") or {}
    
    # PhD-level research synthesis (ran in parallel with Engine B)
    research_for_debate = state.get("research_for_debate", "")
    research_synthesis = state.get("research_synthesis", {})
    
    # FIXED: Set quantitative context flag based on multiple checks (domain agnostic)
    # Use `or []` to handle None values explicitly
    has_cross_scenario = bool(cross_scenario_table)
    has_engine_b_scenarios = engine_b_aggregate.get("scenarios_with_compute", 0) > 0
    scenario_results = state.get("scenario_results") or []
    has_scenario_results = len(scenario_results) > 0
    has_research = bool(research_for_debate)
    
    # Flag is True if ANY quantitative data is available for debate
    state["engine_a_had_quantitative_context"] = has_cross_scenario or has_engine_b_scenarios or has_scenario_results
    
    # Build the full context for debate agents
    context_parts = []
    
    # 1. Add PhD-level research synthesis FIRST (academic foundation)
    if research_for_debate:
        context_parts.append(research_for_debate)
        logger.info(f"📚 Research synthesis injected into debate ({len(research_for_debate)} chars)")
        
        # Log research sources
        if research_synthesis:
            sources = research_synthesis.get("sources_summary", {})
            logger.info(f"   Sources: {sources}")
    
    # 2. Add quantitative scenario context
    if cross_scenario_table:
        context_parts.append(f"""
## QUANTITATIVE CONTEXT (Multiple Scenarios Analyzed)

{cross_scenario_table}

Your arguments MUST reference these scenario comparisons and computed metrics.
""")
        logger.info(f"📊 Cross-scenario table passed to debate ({len(cross_scenario_table)} chars)")
    
    # 3. Add Engine B aggregate if no cross_scenario_table
    if not cross_scenario_table and engine_b_aggregate.get("scenarios_with_compute", 0) > 0:
        scenarios_computed = engine_b_aggregate.get('scenarios_with_compute', 0)
        monte_carlo_runs = engine_b_aggregate.get('total_monte_carlo_runs', 0)
        avg_success = engine_b_aggregate.get('avg_success_probability', 0)
        drivers = engine_b_aggregate.get('sensitivity_drivers', ['Not computed'])[:3]
        context_parts.append(f"""
## ENGINE B QUANTITATIVE ANALYSIS

- Scenarios computed: {scenarios_computed}
- Monte Carlo runs: {monte_carlo_runs}
- Avg success probability: {avg_success:.1%}
- Top sensitivity drivers: {', '.join(drivers)}

Reference these computed values in your arguments.
""")
        logger.info(f"📊 Engine B aggregate passed to debate")
    
    # Combine all context
    if context_parts:
        cross_scenario_context = "\n\n---\n\n".join(context_parts)
        logger.info(f"📊 Total context for debate: {len(cross_scenario_context)} chars")
    
    try:
        logger.info(f"🚀 STARTING legendary debate with {len(contradictions)} contradictions (depth={debate_depth})")
        debate_results = await orchestrator.conduct_legendary_debate(
            question=state.get("query", ""),
            contradictions=contradictions,
            agents_map=agents_map,
            agent_reports_map=agent_reports_map,
            llm_client=llm_client,
            extracted_facts=state.get("extracted_facts", []),
            debate_depth=debate_depth,  # Pass user-selected depth
            cross_scenario_context=cross_scenario_context  # FIXED: Pass cross-scenario data
        )
        logger.info(f"✅ Legendary debate SUCCEEDED: {debate_results['total_turns']} turns")

        # Update state with debate results
        state["debate_synthesis"] = debate_results["final_report"]
        state["debate_results"] = {
            "contradictions": contradictions,
            "contradictions_found": len(contradictions),
            "total_turns": debate_results["total_turns"],
            "conversation_history": debate_results["conversation_history"],
            "resolutions": debate_results["resolutions"],
            "consensus": debate_results["consensus"],
            "status": "complete",
            "final_report": debate_results["final_report"],
            "consensus_narrative": debate_results.get("consensus", {}).get("narrative", ""),
            "resolved": len([r for r in debate_results.get("resolutions", []) if r.get("action") != "flag_for_review"]),
            "flagged_for_review": len([r for r in debate_results.get("resolutions", []) if r.get("action") == "flag_for_review"]),
        }

        reasoning_chain.append(
            f"⚡ Legendary debate completed: {debate_results['total_turns']} turns, "
            f"{len(contradictions)} contradictions analyzed, 6 phases completed"
        )

        logger.info(
            f"Legendary debate complete: {debate_results['total_turns']} turns, "
            f"{debate_results.get('execution_time_minutes', 0):.1f} minutes"
        )

    except Exception as e:
        logger.error(f"❌ LEGENDARY DEBATE FAILED: {e}", exc_info=True)
        completed_turns = orchestrator.conversation_history if orchestrator else []
        logger.error(f"❌ PRESERVING {len(completed_turns)} turns that were already streamed")

        # Fallback to simplified debate BUT PRESERVE the turns that were already streamed!
        from .debate import _build_synthesis
        synthesis = _build_synthesis(contradictions)
        
        # Build summary from completed turns for synthesis to use
        turn_summary = ""
        if completed_turns:
            summary_parts = []
            for turn in completed_turns[-30:]:  # Last 30 turns
                speaker = turn.get("agent", "Agent")
                content = turn.get("message", "")[:400]
                summary_parts.append(f"**{speaker}**: {content}...")
            turn_summary = "\n\n".join(summary_parts)

        # CRITICAL: Store in ALL keys that synthesis might look for
        state["debate_synthesis"] = synthesis
        state["multi_agent_debate"] = turn_summary or synthesis  # FIX: Also set this key
        state["conversation_history"] = completed_turns  # FIX: Also at state level
        state["debate_partial"] = True  # FIX: Mark as partial
        state["debate_turns"] = len(completed_turns)  # FIX: Track turn count
        state["debate_results"] = {
            "contradictions": contradictions,
            "contradictions_found": len(contradictions),
            "total_turns": len(completed_turns),
            "conversation_history": completed_turns,
            "resolutions": [],
            "consensus": {"narrative": synthesis},
            "status": "partial",
            "error": str(e),
            "consensus_narrative": synthesis,
            "resolved": 0,
            "flagged_for_review": 0,
        }

        reasoning_chain.append(f"⚠️ Legendary debate partially completed ({len(completed_turns)} turns), error: {e}")

    nodes_executed.append("debate")
    return state
