"""
Workflow adapter for streaming LangGraph execution to UI.

Provides async streaming interface that yields StageEvent objects as each
node in the LangGraph workflow completes.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional

from ..agents.base import DataClient
from ..rag.retriever import retrieve_external_context
from ..data.deterministic.cache_access import COUNTERS as CACHE_COUNTERS
from .classifier import QueryClassifier
from .council import default_agents

logger = logging.getLogger(__name__)


@dataclass
class StageEvent:
    """
    Event emitted when a workflow stage completes.
    
    Attributes:
        stage: Stage identifier (classify, prefetch, agent:<name>, verify, synthesize, done)
        payload: Stage-specific data (findings, metrics, errors, etc.)
        timestamp: ISO timestamp when stage completed
        latency_ms: Time taken for this stage in milliseconds
    """
    stage: str
    payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    latency_ms: int = 0


async def run_workflow_stream(
    question: str,
    user_ctx: Optional[Dict[str, Any]] = None
) -> AsyncIterator[StageEvent]:
    """
    Build the LangGraph workflow and stream StageEvent objects as each node completes.
    
    This is the main entry point for the UI. It orchestrates the complete workflow:
      1. Classify intent
      2. Route to appropriate agents
      3. Prefetch data (deterministic + RAG)
      4. Invoke agents (parallel/sequential per router)
      5. Verify results (citations, numeric checks)
      6. Synthesize council report
      7. Yield final results
    
    Args:
        question: User's natural language question
        user_ctx: Optional user context (permissions, preferences, etc.)
        
    Yields:
        StageEvent objects for each completed stage
        
    Example:
        >>> async for event in run_workflow_stream("What is Qatar unemployment?"):
        ...     print(f"{event.stage}: {event.payload.get('status')}")
        classify: completed
        prefetch: completed
        agent:Nationalization: completed
        verify: completed
        synthesize: completed
        done: completed
    """
    user_ctx = user_ctx or {}
    request_id = user_ctx.get("request_id", f"req_{int(time.time() * 1000)}")
    workflow_start_perf = time.perf_counter()  # For duration measurement
    workflow_start_utc = datetime.now(timezone.utc)  # For audit timestamps
    
    logger.info(f"[{request_id}] Starting workflow for question: {question[:50]}...")
    
    try:
        # ============================================================
        # STAGE 1: CLASSIFY INTENT
        # ============================================================
        classify_start = time.perf_counter()
        
        # Initialize classifier
        base_path = Path(__file__).parent
        catalog_path = base_path / "intent_catalog.yml"
        keywords_path = base_path / "keywords"
        
        classifier = QueryClassifier(
            catalog_path=str(catalog_path),
            sector_lex=str(keywords_path / "sectors.txt"),
            metric_lex=str(keywords_path / "metrics.txt"),
        )
        
        classification = classifier.classify_text(question)
        primary_intent = classification.intents[0] if classification.intents else "unknown"
        complexity_value = classification.complexity
        horizon = classification.entities.time_horizon or {}
        horizon_months = horizon.get("months")
        
        classify_latency = int((time.perf_counter() - classify_start) * 1000)
        
        yield StageEvent(
            stage="classify",
            payload={
                "intent": primary_intent,
                "alternative_intents": classification.intents,
                "complexity": complexity_value,
                "entities": {
                    "sectors": classification.entities.sectors,
                    "metrics": classification.entities.metrics,
                    "horizon_months": horizon_months,
                },
                "confidence": classification.confidence,
                "status": "completed"
            },
            latency_ms=classify_latency
        )
        
        logger.info(f"[{request_id}] Classified as: {primary_intent} ({complexity_value})")
        
        # ============================================================
        # STAGE 2: PREFETCH DATA
        # ============================================================
        prefetch_start = time.perf_counter()
        
        # Initialize data client
        data_client = DataClient()
        
        # Prefetch deterministic data (based on intent)
        # This would normally use the prefetch manager, but for simplicity we'll
        # let agents fetch their own data
        
        # Fetch RAG context
        rag_context = await retrieve_external_context(question, max_snippets=3)
        
        prefetch_latency = int((time.perf_counter() - prefetch_start) * 1000)
        
        yield StageEvent(
            stage="prefetch",
            payload={
                "rag_snippets": len(rag_context.get("snippets", [])),
                "rag_sources": rag_context.get("sources", []),
                "cache_stats": rag_context.get("metadata", {}).get("cache_hit", False),
                "status": "completed"
            },
            latency_ms=prefetch_latency
        )
        
        logger.info(f"[{request_id}] Prefetched {len(rag_context.get('snippets', []))} RAG snippets")
        
        # ============================================================
        # STAGE 3: INVOKE AGENTS
        # ============================================================
        # For now, we'll use the council approach (all 5 agents)
        # In a full implementation, this would route based on intent
        
        agents = default_agents(data_client)
        agent_reports = []
        
        for agent in agents:
            agent_start = time.perf_counter()
            agent_name = agent.__class__.__name__.replace("Agent", "")
            
            try:
                report = agent.run()
                agent_reports.append(report)
                
                agent_latency = int((time.perf_counter() - agent_start) * 1000)
                
                # Convert findings to serializable format
                findings_payload = []
                for finding in report.findings:
                    findings_payload.append({
                        "title": finding.title if hasattr(finding, 'title') else finding.get('title', ''),
                        "summary": finding.summary if hasattr(finding, 'summary') else finding.get('summary', ''),
                        "metrics": (finding.metrics or {}) if hasattr(finding, 'metrics') else finding.get('metrics', {}),
                        "evidence": [
                            {
                                "query_id": e.query_id if hasattr(e, 'query_id') else e.get('query_id', ''),
                                "dataset_id": e.dataset_id if hasattr(e, 'dataset_id') else e.get('dataset_id', ''),
                                "locator": e.locator if hasattr(e, 'locator') else e.get('locator', ''),
                                "fields": e.fields if hasattr(e, 'fields') else e.get('fields', []),
                                "freshness_as_of": e.freshness_as_of if hasattr(e, 'freshness_as_of') else e.get('freshness_as_of'),
                                "freshness_updated_at": e.freshness_updated_at if hasattr(e, 'freshness_updated_at') else e.get('freshness_updated_at'),
                            }
                            for e in (finding.evidence if hasattr(finding, 'evidence') else finding.get('evidence', []))
                        ],
                        "warnings": finding.warnings if hasattr(finding, 'warnings') else finding.get('warnings', []),
                        "confidence_score": finding.confidence_score if hasattr(finding, 'confidence_score') else finding.get('confidence_score', 0.8),
                    })
                
                yield StageEvent(
                    stage=f"agent:{agent_name}",
                    payload={
                        "agent": agent_name,
                        "findings": findings_payload,
                        "finding_count": len(report.findings),
                        "status": "completed"
                    },
                    latency_ms=agent_latency
                )
                
                logger.info(f"[{request_id}] Agent {agent_name} completed with {len(report.findings)} findings")
                
            except Exception as e:
                logger.error(f"[{request_id}] Agent {agent_name} failed: {e}")
                yield StageEvent(
                    stage=f"agent:{agent_name}",
                    payload={
                        "agent": agent_name,
                        "status": "error",
                        "error": str(e)
                    },
                    latency_ms=int((time.perf_counter() - agent_start) * 1000)
                )
        
        # ============================================================
        # STAGE 4: VERIFY RESULTS
        # ============================================================
        verify_start = time.perf_counter()
        
        from .verification import verify_report
        
        verification_results = {}
        all_issues = []
        
        for report in agent_reports:
            verification = verify_report(report)
            verification_results[report.agent] = verification.issues
            all_issues.extend(verification.issues)
        
        # Calculate confidence stats
        all_confidences = []
        for report in agent_reports:
            for finding in report.findings:
                conf_score = finding.confidence_score if hasattr(finding, 'confidence_score') else finding.get('confidence_score', 0.8)
                all_confidences.append(conf_score)
        
        confidence_stats = {}
        if all_confidences:
            confidence_stats = {
                "min": min(all_confidences),
                "avg": sum(all_confidences) / len(all_confidences),
                "max": max(all_confidences),
            }
        
        verify_latency = int((time.perf_counter() - verify_start) * 1000)
        
        yield StageEvent(
            stage="verify",
            payload={
                "citations": {
                    "status": "pass" if not any(i.code == "missing_citation" for i in all_issues) else "fail",
                    "details": [i.detail for i in all_issues if i.code == "missing_citation"]
                },
                "numeric_checks": {
                    "status": "pass" if not any(i.level == "error" for i in all_issues) else "warn",
                    "issues": [{"level": i.level, "code": i.code, "detail": i.detail} for i in all_issues]
                },
                "confidence": confidence_stats,
                "issues": [{"level": i.level, "code": i.code, "detail": i.detail} for i in all_issues],
                "status": "completed"
            },
            latency_ms=verify_latency
        )
        
        logger.info(f"[{request_id}] Verification completed with {len(all_issues)} issues")
        
        # ============================================================
        # STAGE 5: SYNTHESIZE COUNCIL REPORT
        # ============================================================
        synthesize_start = time.perf_counter()
        
        from .synthesis import synthesize
        
        council_report = synthesize(agent_reports)
        
        synthesize_latency = int((time.perf_counter() - synthesize_start) * 1000)
        
        yield StageEvent(
            stage="synthesize",
            payload={
                "agents": council_report.agents,
                "finding_count": len(council_report.findings),
                "consensus": council_report.consensus,
                "warnings": council_report.warnings,
                "status": "completed"
            },
            latency_ms=synthesize_latency
        )
        
        logger.info(f"[{request_id}] Synthesis completed with {len(council_report.findings)} findings")
        
        # ============================================================
        # STAGE 6: DONE - FINAL RESULTS
        # ============================================================
        total_latency = int((time.perf_counter() - workflow_start_perf) * 1000)
        
        # Collect all query IDs and sources
        all_query_ids = set()
        all_sources = set()
        
        for report in agent_reports:
            for finding in report.findings:
                evidence_list = finding.evidence if hasattr(finding, 'evidence') else finding.get('evidence', [])
                for evidence in evidence_list:
                    query_id = evidence.query_id if hasattr(evidence, 'query_id') else evidence.get('query_id')
                    dataset_id = evidence.dataset_id if hasattr(evidence, 'dataset_id') else evidence.get('dataset_id')
                    if query_id:
                        all_query_ids.add(query_id)
                    if dataset_id:
                        all_sources.add(dataset_id)
        
        yield StageEvent(
            stage="done",
            payload={
                "council_report": {
                    "agents": council_report.agents,
                    "findings": [
                        {
                            "title": f.title if hasattr(f, 'title') else f.get('title', ''),
                            "summary": f.summary if hasattr(f, 'summary') else f.get('summary', ''),
                            "metrics": (f.metrics or {}) if hasattr(f, 'metrics') else f.get('metrics', {}),
                            "confidence_score": f.confidence_score if hasattr(f, 'confidence_score') else f.get('confidence_score', 0.8),
                        }
                        for f in council_report.findings
                    ],
                    "consensus": council_report.consensus,
                    "warnings": council_report.warnings,
                },
                "verification": verification_results,
                "audit": {
                    "request_id": request_id,
                    "query_ids": sorted(all_query_ids),
                    "sources": sorted(all_sources),
                    "cache_stats": {
                        "hits": CACHE_COUNTERS.get("hits", 0),
                        "misses": CACHE_COUNTERS.get("misses", 0),
                        "invalidations": CACHE_COUNTERS.get("invalidations", 0),
                    },
                    "timestamps": {
                        "start": workflow_start_utc.isoformat(),
                        "end": datetime.now(timezone.utc).isoformat(),
                    },
                    "latency_ms": total_latency,
                },
                "rag_context": rag_context,
                "status": "completed"
            },
            latency_ms=total_latency
        )
        
        logger.info(f"[{request_id}] Workflow completed in {total_latency}ms")
        
    except Exception as e:
        logger.error(f"[{request_id}] Workflow failed: {e}", exc_info=True)
        
        yield StageEvent(
            stage="error",
            payload={
                "error": str(e),
                "error_type": type(e).__name__,
                "status": "failed"
            },
            latency_ms=int((time.perf_counter() - workflow_start_perf) * 1000)
        )
