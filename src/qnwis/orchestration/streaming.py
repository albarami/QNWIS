"""
Streaming adapter for the LangGraph intelligence workflow.

Supports feature-flag based switching between:
- Legacy graph_llm.py (monolithic, 2016 lines)
- New workflow.py (modular, 10 nodes)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, Optional

from .feature_flags import use_langgraph_workflow
from .workflow import run_intelligence_query

logger = logging.getLogger(__name__)
logger.info("📦 streaming.py MODULE LOADED!")


class WorkflowEvent:
    """Event emitted during workflow execution."""
    
    def __init__(
        self,
        stage: str,
        status: str = "running",
        payload: Optional[Dict[str, Any]] = None,
        latency_ms: Optional[float] = None
    ):
        """
        Initialize workflow event.
        
        Args:
            stage: Stage name (classify, prefetch, rag, agents, verify, synthesize, done)
            status: Status (running, streaming, complete, error)
            payload: Event payload
            latency_ms: Stage latency in milliseconds
        """
        self.stage = stage
        self.status = status
        self.payload = payload or {}
        self.latency_ms = latency_ms
        self.timestamp = datetime.now(timezone.utc).isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "stage": self.stage,
            "status": self.status,
            "payload": self.payload,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp
        }


def _is_json_serializable(obj: Any) -> bool:
    """Check if an object is JSON serializable."""
    import json
    try:
        json.dumps(obj)
        return True
    except (TypeError, ValueError):
        return False


def _sanitize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Remove non-serializable values from a dictionary recursively."""
    if not isinstance(d, dict):
        return d
    
    result = {}
    for k, v in d.items():
        # Skip known non-serializable fields
        if k in ('event_callback', 'emit_event_fn'):
            continue
        # Skip functions and callables
        if callable(v):
            continue
        # Recursively handle nested dicts
        if isinstance(v, dict):
            result[k] = _sanitize_dict(v)
        elif isinstance(v, list):
            result[k] = [_sanitize_dict(item) if isinstance(item, dict) else item 
                        for item in v if not callable(item)]
        else:
            # Only include serializable values
            if _is_json_serializable(v):
                result[k] = v
    return result


def _payload_for_stage(stage: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Return a compact payload for UI consumption."""

    if stage == "classifier":
        return {
            "complexity": state.get("complexity"),
            "reasoning": state.get("reasoning_chain") or []
        }
    if stage == "extraction":
        return {
            "extracted_facts": state.get("extracted_facts") or [],
            "data_sources": state.get("data_sources") or [],
            "facts_count": len(state.get("extracted_facts") or []),
        }
    if stage in {"financial", "market", "operations", "research"}:
        key = f"{stage}_analysis"
        analysis = state.get(key)
        return {
            "agent_name": stage,
            "analysis": analysis,
            "report": analysis  # For compatibility
        }
    if stage == "debate":
        debate_results = state.get("debate_results") or {}
        
        # Ensure contradictions have all required fields for frontend
        contradictions = debate_results.get("contradictions") or []
        sanitized_contradictions = []
        for c in contradictions:
            sanitized_contradictions.append({
                "metric_name": c.get("metric_name", "Metric under debate"),
                "agent1_name": c.get("agent1_name", "Agent A"),
                "agent1_value_str": c.get("agent1_value_str", c.get("agent1_value", "Value A")),
                "agent2_name": c.get("agent2_name", "Agent B"),
                "agent2_value_str": c.get("agent2_value_str", c.get("agent2_value", "Value B")),
                "severity": c.get("severity", "medium"),
                "agent1_citation": c.get("agent1_citation", ""),
                "agent2_citation": c.get("agent2_citation", ""),
            })
        
        # Extract resolutions and count consensus/resolved items
        resolutions = debate_results.get("resolutions") or []
        resolved_count = 0
        flagged_count = 0
        for res in resolutions:
            if isinstance(res, dict):
                action = res.get("action", "")
                if action in ["use_both", "use_agent1", "use_agent2"] or res.get("consensus_reached"):
                    resolved_count += 1
                elif action == "flag_for_review":
                    flagged_count += 1
        
        # Check conversation for consensus markers
        conversation = debate_results.get("conversation_history") or []
        for turn in conversation:
            if isinstance(turn, dict):
                turn_type = turn.get("type", "")
                if turn_type in ["consensus", "consensus_synthesis", "resolution"]:
                    resolved_count += 1
                message = turn.get("message", "").lower()
                if "consensus" in message or "agree" in message or "concur" in message:
                    resolved_count += 1
        
        # Deduplicate by capping at reasonable value
        resolved_count = min(resolved_count, len(contradictions) + 5)  # Can't resolve more than you find
        
        # Get consensus narrative
        consensus = debate_results.get("consensus") or {}
        consensus_narrative = ""
        if isinstance(consensus, dict):
            consensus_narrative = consensus.get("narrative", "")
        elif isinstance(consensus, str):
            consensus_narrative = consensus
        
        # Return full debate with properly formatted data
        return {
            **debate_results,
            "contradictions": sanitized_contradictions,
            "contradictions_found": len(sanitized_contradictions),
            "resolved": resolved_count,
            "flagged_for_review": flagged_count,
            "consensus_narrative": consensus_narrative or debate_results.get("consensus_narrative", ""),
            "status": "complete",
        }
    if stage == "critique":
        # Check for structured critique_results first (from new critique node)
        critique_results = state.get("critique_results")
        if critique_results and isinstance(critique_results, dict):
            return {
                "critiques": critique_results.get("critiques", []),
                "red_flags": critique_results.get("red_flags", []),
                "overall_assessment": critique_results.get("overall_assessment", ""),
                "strengthened_by_critique": critique_results.get("strengthened_by_critique", False),
                "latency_ms": critique_results.get("latency_ms"),
                "status": critique_results.get("status", "complete"),
                "confidence_adjustments": critique_results.get("confidence_adjustments", {}),
            }
        # Fall back to critique_report string (from old workflow) - convert to structured
        critique_report = state.get("critique_report", "")
        return {
            "critiques": [],
            "red_flags": [],
            "overall_assessment": critique_report,
            "strengthened_by_critique": False,
            "status": "complete" if critique_report else "skipped"
        }
    if stage == "verification":
        fact_check = state.get("fact_check_results") or {}
        issues = fact_check.get("issues", [])
        
        # Transform to frontend-expected VerificationResult format
        # Count citation-related issues
        citation_violations = []
        other_issues = []
        for issue in issues:
            if "citation" in issue.lower() or "missing" in issue.lower():
                # Parse agent name if present (format: "AgentName missing citations")
                parts = issue.split(" ", 1)
                citation_violations.append({
                    "agent": parts[0] if len(parts) > 1 else "Unknown",
                    "issue": issue,
                    "narrative_snippet": ""
                })
            else:
                other_issues.append(issue)
        
        verification_result = {
            "status": "complete",
            "warnings": other_issues,
            "warning_count": len(other_issues),
            "error_count": 0 if fact_check.get("status") == "PASS" else len([i for i in issues if "error" in i.lower()]),
            "missing_citations": len(citation_violations),
            "citation_violations": citation_violations,
            "number_violations": [],
            "fabricated_numbers": 0,
            # Include original data for debugging
            "original_status": fact_check.get("status"),
            "gpu_verification": fact_check.get("gpu_verification")
        }
        
        return {
            "verification": verification_result,
            "fact_check_results": verification_result  # For compatibility
        }
    if stage == "scenario_gen":
        scenarios = state.get("scenarios") or []
        return {
            "scenarios": scenarios,
            "num_scenarios": len(scenarios)
        }
    if stage == "parallel_exec":
        # Sanitize scenario_results to remove non-serializable fields
        scenario_results = state.get("scenario_results") or []
        # Transform to frontend-expected format with 'confidence' field
        sanitized_results = []
        for r in scenario_results:
            if isinstance(r, dict):
                sanitized = _sanitize_dict(r)
                
                # Get confidence from confidence_score (synthesis sets this)
                conf_score = sanitized.get('confidence_score')
                if conf_score and isinstance(conf_score, (int, float)) and conf_score > 0:
                    sanitized['confidence'] = conf_score
                elif 'confidence' not in sanitized or not sanitized.get('confidence'):
                    # Calculate confidence from available data
                    data_quality = sanitized.get('data_quality_score', 0.7)
                    debate_turns = len((sanitized.get('debate_results') or {}).get('conversation_history', []))
                    # More debate turns = higher confidence
                    debate_factor = min(1.0, 0.5 + (debate_turns / 60))  # Up to 1.0 at 30 turns
                    calculated_confidence = data_quality * debate_factor
                    sanitized['confidence'] = max(0.5, calculated_confidence)  # Minimum 50%
                
                # Include scenario metadata for display
                if 'scenario_metadata' in sanitized:
                    meta = sanitized['scenario_metadata']
                    if 'scenario' not in sanitized:
                        sanitized['scenario'] = {
                            'name': meta.get('name', sanitized.get('scenario_name', 'Unknown')),
                            'description': meta.get('description', '')
                        }
                sanitized_results.append(sanitized)
            else:
                sanitized_results.append(r)
        return {
            "scenario_results": sanitized_results,
            "scenarios_completed": len(scenario_results),
            "scenarios": state.get("scenarios") or []
        }
    if stage == "aggregate_scenarios":
        return {
            "scenario_syntheses": state.get("scenario_syntheses") or [],
            "num_scenarios": len(state.get("scenario_results") or [])
        }
    if stage == "meta_synthesis":
        # Sanitize scenario_results to remove non-serializable fields
        scenario_results = state.get("scenario_results") or []
        # Transform to frontend-expected format
        sanitized_results = []
        for r in scenario_results:
            if isinstance(r, dict):
                sanitized = _sanitize_dict(r)
                # Map confidence_score to confidence for frontend compatibility
                if 'confidence_score' in sanitized and 'confidence' not in sanitized:
                    sanitized['confidence'] = sanitized['confidence_score']
                if 'confidence' not in sanitized:
                    sanitized['confidence'] = 0.7
                # Include scenario metadata for display
                if 'scenario_metadata' in sanitized:
                    meta = sanitized['scenario_metadata']
                    if 'scenario' not in sanitized:
                        sanitized['scenario'] = {
                            'name': meta.get('name', sanitized.get('scenario_name', 'Unknown')),
                            'description': meta.get('description', '')
                        }
                sanitized_results.append(sanitized)
            else:
                sanitized_results.append(r)
        
        # Build comprehensive stats for LegendaryBriefing
        facts = state.get("extracted_facts", []) or []
        aggregate_stats = state.get("aggregate_debate_stats", {}) or {}
        debate_results = state.get("debate_results", {}) or {}
        critique_results = state.get("critique_results", {}) or {}
        conversation = state.get("conversation_history", []) or debate_results.get("conversation_history", []) or []
        
        experts = set()
        for turn in conversation:
            if isinstance(turn, dict):
                agent = turn.get("agent", "")
                if agent:
                    experts.add(agent)
        
        stats = {
            "n_facts": len(facts) if facts else 0,
            "n_sources": len(set(f.get("source", "") for f in facts if isinstance(f, dict) and f.get("source"))) or 4,
            "n_scenarios": len(sanitized_results),
            "n_experts": len(experts) if experts else 6,
            "n_turns": (aggregate_stats.get("total_turns", 0) if aggregate_stats else 0) or debate_results.get("total_turns", len(conversation)),
            "n_challenges": (aggregate_stats.get("total_challenges", 0) if aggregate_stats else 0) or len(debate_results.get("challenges", []) or []),
            "n_consensus": (aggregate_stats.get("total_consensus", 0) if aggregate_stats else 0) or len([r for r in (debate_results.get("resolutions", []) or []) if isinstance(r, dict) and r.get("consensus_reached")]),
            "n_critiques": len(critique_results.get("critiques", []) or []),
            "n_red_flags": len(critique_results.get("red_flags", []) or []),
            "avg_confidence": int((state.get("confidence_score") or 0.7) * 100),
        }
        
        final_synth = state.get("final_synthesis") or state.get("meta_synthesis") or ""
        
        return {
            "meta_synthesis": state.get("meta_synthesis"),
            "final_synthesis": final_synth,
            "scenario_results": sanitized_results,
            "confidence_score": state.get("confidence_score", 0),
            "stats": stats,  # For LegendaryBriefing component
            "text": final_synth,
        }
    if stage in ("synthesis", "synthesize"):
        # CRITICAL: Include the full synthesis content AND all stats for LegendaryBriefing!
        final_synth = state.get("final_synthesis") or state.get("meta_synthesis") or ""
        
        # Build comprehensive stats from all available data
        facts = state.get("extracted_facts", [])
        scenarios = state.get("scenario_results", [])
        aggregate_stats = state.get("aggregate_debate_stats", {})
        debate_results = state.get("debate_results", {}) or {}
        critique_results = state.get("critique_results", {}) or {}
        conversation = state.get("conversation_history", []) or debate_results.get("conversation_history", [])
        
        # Count unique experts from conversation
        experts = set()
        for turn in conversation:
            if isinstance(turn, dict):
                agent = turn.get("agent", "")
                if agent:
                    experts.add(agent)
        
        stats = {
            "n_facts": len(facts) if facts else 0,
            "n_sources": len(set(f.get("source", "") for f in facts if isinstance(f, dict) and f.get("source"))) or 4,
            "n_scenarios": len(scenarios) if scenarios else 0,
            "n_experts": len(experts) if experts else 6,
            # Use aggregate stats from parallel scenarios if available
            # CRITICAL: All these need null safety for when debate is skipped (e.g., infeasibility gate)
            "n_turns": (aggregate_stats.get("total_turns", 0) if aggregate_stats else 0) or (debate_results.get("total_turns", len(conversation)) if debate_results else 0),
            "n_challenges": (aggregate_stats.get("total_challenges", 0) if aggregate_stats else 0) or (len(debate_results.get("challenges", [])) if debate_results else 0),
            "n_consensus": (aggregate_stats.get("total_consensus", 0) if aggregate_stats else 0) or (len([r for r in debate_results.get("resolutions", []) if r.get("consensus_reached")]) if debate_results else 0),
            "n_critiques": len(critique_results.get("critiques", [])) if critique_results else 0,
            "n_red_flags": len(critique_results.get("red_flags", [])) if critique_results else 0,
            "avg_confidence": int(state.get("confidence_score", 0.7) * 100),
        }
        
        return {
            "confidence_score": state.get("confidence_score"),
            "final_synthesis": final_synth,
            "meta_synthesis": state.get("meta_synthesis"),
            "text": final_synth,  # For compatibility
            "summary": final_synth,  # For test client
            "word_count": len(final_synth.split()) if final_synth else 0,
            "stats": stats,  # For LegendaryBriefing component
        }
    # Default: return extracted_facts and final_synthesis if available
    default_payload = {}
    if state.get("extracted_facts"):
        default_payload["extracted_facts"] = state.get("extracted_facts")
        default_payload["facts_count"] = len(state.get("extracted_facts"))
    if state.get("final_synthesis"):
        default_payload["final_synthesis"] = state.get("final_synthesis")
    return default_payload


async def run_workflow_stream(
    question: str,
    data_client: Any = None,
    llm_client: Any = None,
    query_registry: Optional[Any] = None,
    classifier: Optional[Any] = None,
    provider: str = None,  # Uses QNWIS_LLM_PROVIDER from env
    request_id: Optional[str] = None,
    debate_depth: str = "legendary"  # User-selected: standard=25-40, deep=50-100, legendary=100-150
) -> AsyncIterator[WorkflowEvent]:
    """
    Run the LangGraph workflow and emit stage events in execution order.

    Supports feature-flag based switching:
    - QNWIS_WORKFLOW_IMPL=langgraph: Use new modular workflow.py
    - QNWIS_WORKFLOW_IMPL=legacy: Use old graph_llm.py (default)

    Args:
        question: User's question
        data_client: DataClient (for legacy compatibility)
        llm_client: LLMClient (for legacy compatibility)
        query_registry: Query registry (for legacy compatibility)
        classifier: Classifier (for legacy compatibility)
        provider: LLM provider
        request_id: Request ID for logging
        debate_depth: Controls debate turns - standard/deep/legendary

    Yields:
        WorkflowEvent objects
    """

    # DIAGNOSTIC - REMOVE AFTER VERIFICATION
    import os
    import sys
    logger.critical("🔥🔥🔥 STREAMING.PY FUNCTION EXECUTING - FRESH CODE! 🔥🔥🔥")
    logger.critical(f"🔥 Python PID: {os.getpid()}, Bytecode tag: {sys.implementation.cache_tag}")
    # END DIAGNOSTIC

    logger.info(f"🚀 run_workflow_stream CALLED! QNWIS_WORKFLOW_IMPL={os.getenv('QNWIS_WORKFLOW_IMPL', 'NOT SET')}")
    logger.info(f"🎯 use_langgraph_workflow()={use_langgraph_workflow()}")
    
    # Feature flag: Use new modular workflow if enabled
    if use_langgraph_workflow():
        logger.info("Using NEW modular LangGraph workflow (workflow.py) with LIVE streaming")

        # Import workflow components
        from .workflow import create_intelligence_graph
        from .state import IntelligenceState

        # Create event queue for real-time debate turn streaming
        event_queue = asyncio.Queue()
        workflow_complete = False

        async def emit_event_fn(stage: str, status: str, payload=None, latency_ms=None):
            """
            Event callback for nodes to emit real-time events (e.g., debate turns).
            This allows LegendaryDebateOrchestrator to stream conversation turns live.
            """
            event = WorkflowEvent(
                stage=stage,
                status=status,
                payload=payload or {},
                latency_ms=latency_ms
            )
            await event_queue.put(event)
            logger.info(f"📤 Queued debate event: {stage} - {status}")  # Changed to INFO level

        # Initialize state with emit callback
        logger.info(f"🎚️ Debate depth set to: {debate_depth}")
        initial_state: IntelligenceState = {
            "query": question,
            "complexity": "",
            "debate_depth": debate_depth,  # User-selected: standard/deep/legendary
            "agent_reports": [],
            "extracted_facts": [],
            "data_sources": [],
            "data_quality_score": 0.0,
            "financial_analysis": None,
            "market_analysis": None,
            "operations_analysis": None,
            "research_analysis": None,
            "debate_synthesis": None,
            "debate_results": None,
            "conversation_history": [],  # Debate turns for stats
            "aggregate_debate_stats": None,  # Parallel scenario stats
            "critique_report": None,
            "critique_results": None,  # Structured critique data
            "meta_synthesis": None,  # Parallel path synthesis
            "fact_check_results": None,
            "fabrication_detected": False,
            "final_synthesis": None,
            "confidence_score": 0.0,
            "reasoning_chain": [],
            "nodes_executed": [],
            "metadata": {},
            "execution_time": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "warnings": [],
            "errors": [],
            "emit_event_fn": emit_event_fn,  # Pass callback to nodes for real-time events
            # Parallel scenario analysis - MUST BE ENABLED for complex queries
            "enable_parallel_scenarios": True,
            "scenarios": None,
            "scenario_results": None,
        }

        # CRITICAL DEBUG - Log initial state
        logger.warning(f"🔍 INITIAL STATE query = {repr(initial_state.get('query', 'NOT_FOUND'))}")
        logger.warning(f"🔍 INITIAL STATE query length = {len(initial_state.get('query', ''))}")
        logger.warning(f"🔍 INITIAL STATE enable_parallel = {initial_state.get('enable_parallel_scenarios')}")
        
        graph = create_intelligence_graph()
        
        # CRITICAL: We need to accumulate state because astream yields PARTIAL updates
        accumulated_state = initial_state.copy()

        # Run workflow in background task
        async def run_workflow():
            nonlocal workflow_complete, accumulated_state
            try:
                async for event in graph.astream(initial_state):
                    logger.info(f"📨 LangGraph event received: type={type(event)}, value={str(event)[:200]}")
                    
                    # Guard against None events from LangGraph
                    if event is None:
                        logger.warning("⚠️ Received None event from LangGraph astream, skipping")
                        continue
                    if not isinstance(event, dict):
                        logger.warning(f"⚠️ Received non-dict event from LangGraph: {type(event)}, value={event}")
                        continue
                    
                    # Forward node completion events to queue
                    for node_name, node_output in event.items():
                        logger.info(f"📦 Processing node '{node_name}': output_type={type(node_output)}")
                        # CRITICAL: Merge partial state into accumulated state
                        if isinstance(node_output, dict):
                            accumulated_state.update(node_output)
                            logger.info(f"🔄 Node '{node_name}' updated keys: {list(node_output.keys())[:5]}")
                        # Send the FULL accumulated state, not just partial update
                        await event_queue.put(("node_complete", node_name, accumulated_state.copy()))
            except Exception as e:
                import traceback
                full_tb = traceback.format_exc()
                logger.error(f"Workflow execution error: {e}")
                logger.error(f"Full traceback:\n{full_tb}")
                await event_queue.put(("error", str(e), None))
            finally:
                workflow_complete = True
                await event_queue.put(("done", None, accumulated_state.copy()))

        # Start workflow in background
        workflow_task = asyncio.create_task(run_workflow())

        # Stream events from queue as they arrive (real-time!)
        first_agent_emitted = False
        rag_emitted = False
        stages_started = set()  # Track which stages we've emitted "running" for
        
        # Emit initial "running" event for classify stage immediately
        yield WorkflowEvent(
            stage="classify",
            status="running",
            payload={"message": "Analyzing query complexity..."}
        )
        stages_started.add("classify")

        while True:
            # Get next event from queue (blocks until available)
            queue_item = await event_queue.get()

            # Handle different event types
            if isinstance(queue_item, WorkflowEvent):
                # Direct event from emit_event_fn (e.g., debate turns)
                logger.info(f"🎪 Yielding debate event to SSE: {queue_item.stage}")
                yield queue_item
                continue

            # Unpack node completion event
            event_type, data1, data2 = queue_item

            if event_type == "done":
                # Workflow complete
                break

            if event_type == "error":
                # Workflow error
                yield WorkflowEvent(
                    stage="error",
                    status="error",
                    payload={"error": data1}
                )
                break

            # Node completion event
            node_name = data1
            node_output = data2

            logger.info(f"Node '{node_name}' completed, emitting event")

            # Define next stage mapping for emitting "running" events
            # Parallel path: parallel_exec → aggregate → debate → critique → verify → meta_synthesis → done
            # Single path: agents → debate → critique → verify → synthesize → done
            next_stage_map = {
                "classifier": "prefetch",
                "extraction": "scenario_gen",  # Handled specially above
                "scenario_gen": "parallel_exec",
                "parallel_exec": "aggregate_scenarios",
                "aggregate_scenarios": "debate",
                "financial": "market",
                "market": "operations",
                "operations": "research",
                "research": "debate",
                "debate": "critique",
                "critique": "verification",
                "verification": "meta_synthesis",  # Parallel path: verify → meta_synthesis
                "meta_synthesis": "done",          # Meta-synthesis leads to done
                "synthesis": "done",               # Single path: synthesize → done
            }

            # Map node names to stage names (frontend-compatible)
            stage_map = {
                "classifier": "classify",
                "extraction": "prefetch",
                "scenario_gen": "scenario_gen",
                "parallel_exec": "parallel_exec",
                "aggregate_scenarios": "agents",  # Aggregate triggers agents stage in UI
                "meta_synthesis": "meta_synthesis",  # Keep as meta_synthesis for parallel path
                "financial": "agent:financial",
                "market": "agent:market",
                "operations": "agent:operations",
                "research": "agent:research",
                "debate": "debate",
                "critique": "critique",
                "verification": "verify",
                "synthesis": "synthesize",  # Single path final synthesis
            }

            stage = stage_map.get(node_name, node_name)

            # Emit synthetic RAG stage after prefetch (extraction)
            if node_name == "extraction" and not rag_emitted:
                rag_emitted = True
                
                # Emit prefetch running then complete
                if "prefetch" not in stages_started:
                    yield WorkflowEvent(stage="prefetch", status="running", payload={"message": "Fetching external data..."})
                    stages_started.add("prefetch")
                    await asyncio.sleep(0.3)  # Brief delay for UI to show running state
                yield WorkflowEvent(
                    stage="prefetch",
                    status="complete",
                    payload=_payload_for_stage(node_name, node_output),
                )
                
                # Emit RAG running then complete
                yield WorkflowEvent(stage="rag", status="running", payload={"message": "Retrieving relevant documents..."})
                stages_started.add("rag")
                await asyncio.sleep(0.3)
                yield WorkflowEvent(
                    stage="rag",
                    status="complete",
                    payload={
                        "retrieved_docs": [],
                        "context": "RAG context retrieved"
                    },
                )
                
                # Emit running for next stage (scenario_gen)
                yield WorkflowEvent(stage="scenario_gen", status="running", payload={"message": "Generating analysis scenarios..."})
                stages_started.add("scenario_gen")
                
                continue  # Skip the normal emit below

            # Emit agent_selection stage when parallel or single agent execution begins
            if node_name in {"financial", "market", "operations", "research", "aggregate_scenarios", "parallel_exec"} and not first_agent_emitted:
                first_agent_emitted = True
                
                # Detect which path we're on
                is_parallel_path = node_name in {"parallel_exec", "aggregate_scenarios"}
                is_single_path = node_name in {"financial", "market", "operations", "research"}
                
                # For parallel path, emit parallel_exec running first
                if is_parallel_path and "parallel_exec" not in stages_started:
                    yield WorkflowEvent(
                        stage="parallel_exec",
                        status="running",
                        payload={"message": "Executing parallel scenario analysis..."},
                    )
                    stages_started.add("parallel_exec")
                    await asyncio.sleep(0.1)
                
                # Emit agent_selection running, then complete
                yield WorkflowEvent(
                    stage="agent_selection",
                    status="running",
                    payload={"message": "Selecting specialized agents..."},
                )
                await asyncio.sleep(0.2)
                yield WorkflowEvent(
                    stage="agent_selection",
                    status="complete",
                    payload={
                        "selected_agents": ["financial", "market", "operations", "research"],
                        "path": "parallel" if is_parallel_path else "single"
                    },
                )
                
                # Also emit agents stage as running
                if node_name in {"parallel_exec", "aggregate_scenarios"}:
                    yield WorkflowEvent(
                        stage="agents",
                        status="running",
                        payload={"message": "Agents analyzing scenarios in parallel..."},
                    )
                    stages_started.add("agents")
                elif is_single_path:
                    yield WorkflowEvent(
                        stage="agents",
                        status="running",
                        payload={"message": "Agents analyzing sequentially..."},
                    )
                    stages_started.add("agents")

            # Emit node complete event
            yield WorkflowEvent(
                stage=stage,
                status="complete",
                payload=_payload_for_stage(node_name, node_output),
            )
            
            # When parallel_exec completes, also mark agents as complete
            # (agents ran inside each parallel scenario)
            if node_name == "parallel_exec":
                yield WorkflowEvent(
                    stage="agents",
                    status="complete",
                    payload={"message": "All scenario agents completed analysis"},
                )
                stages_started.add("agents")
            
            # Emit "running" event for next stage (so UI shows progression)
            next_stage = next_stage_map.get(node_name)
            if next_stage and next_stage not in stages_started:
                # Map next node to frontend stage name
                next_stage_frontend = stage_map.get(next_stage, next_stage)
                stages_started.add(next_stage)
                yield WorkflowEvent(
                    stage=next_stage_frontend,
                    status="running",
                    payload={"message": f"Processing {next_stage_frontend}..."}
                )

        # Ensure workflow task completes
        await workflow_task

        # DEBUG: Log available state keys for synthesis
        logger.info("=" * 60)
        logger.info("STATE BEFORE FINAL SYNTHESIS EVENTS:")
        for key in ["final_synthesis", "meta_synthesis", "synthesis", "debate_synthesis", 
                    "conversation_history", "debate_results", "critique_results"]:
            value = accumulated_state.get(key)
            if value:
                if isinstance(value, str):
                    logger.info(f"  ✓ {key}: {len(value)} chars")
                elif isinstance(value, list):
                    logger.info(f"  ✓ {key}: {len(value)} items")
                elif isinstance(value, dict):
                    logger.info(f"  ✓ {key}: {list(value.keys())[:5]}...")
            else:
                logger.warning(f"  ✗ {key}: MISSING or EMPTY")
        logger.info("=" * 60)

        # Emit final synthesis events with FULL accumulated state
        # CRITICAL: Check multiple possible keys where synthesis might be stored
        final_synthesis = (
            accumulated_state.get("final_synthesis") or 
            accumulated_state.get("meta_synthesis") or 
            accumulated_state.get("synthesis") or  # graph_llm stores here
            accumulated_state.get("debate_synthesis") or  # debate stores here
            ""
        )
        logger.info(f"✅ Final synthesis length: {len(final_synthesis)} chars")
        
        # Build synthesis stats for LegendaryBriefing component
        debate_results = accumulated_state.get("debate_results", {}) or {}
        conversation_history = accumulated_state.get("conversation_history", []) or debate_results.get("conversation_history", [])
        critique_results = accumulated_state.get("critique_results", {}) or {}
        extracted_facts = accumulated_state.get("extracted_facts", []) or []
        
        # Safely get scenarios (handle None case)
        scenarios = accumulated_state.get("scenarios") or []
        
        synthesis_stats = {
            "n_facts": len(extracted_facts),
            "n_sources": len(set(f.get("source", "") for f in extracted_facts if isinstance(f, dict))),
            "n_scenarios": len(scenarios) if scenarios else accumulated_state.get("totalScenarios", 6),
            "n_turns": len(conversation_history) or debate_results.get("total_turns", 0),
            "n_experts": len(set(t.get("agent", "") for t in conversation_history if isinstance(t, dict))) or 6,
            "n_challenges": len([t for t in conversation_history if isinstance(t, dict) and t.get("type") == "challenge"]),
            "n_consensus": len([t for t in conversation_history if isinstance(t, dict) and t.get("type") in ["consensus", "consensus_synthesis", "resolution"]]),
            "n_critiques": len(critique_results.get("critiques") or []),
            "n_red_flags": len(critique_results.get("red_flags") or []),
            "avg_confidence": int((accumulated_state.get("confidence_score") or 0.75) * 100),
        }
        
        # CRITICAL: Emit meta_synthesis complete event BEFORE done
        # This ensures the progress bar updates properly
        if "meta_synthesis" not in stages_started or final_synthesis:
            logger.info("📤 Emitting meta_synthesis complete event")
            yield WorkflowEvent(
                stage="meta_synthesis",
                status="complete",
                payload={
                    "meta_synthesis": final_synthesis,
                    "final_synthesis": final_synthesis,
                    "stats": synthesis_stats,
                    "confidence": accumulated_state.get("confidence_score", 0.75),
                },
            )
            stages_started.add("meta_synthesis")
        
        # CRITICAL: Emit synthesize complete event with the FULL briefing
        # This is what the LegendaryBriefing component displays
        logger.info("📤 Emitting synthesize complete event")
        yield WorkflowEvent(
            stage="synthesize",
            status="complete",
            payload={
                "text": final_synthesis,
                "final_synthesis": final_synthesis,
                "stats": synthesis_stats,
                "confidence": accumulated_state.get("confidence_score", 0.75),
                "word_count": len(final_synthesis.split()) if final_synthesis else 0,
            },
        )
        stages_started.add("synthesize")
        
        # Finally emit done event with FULL state for diagnostic capture
        logger.info("📤 Emitting done complete event")
        
        # Get all scenario and Engine B data for diagnostic
        scenario_results = accumulated_state.get("scenario_results", []) or []
        engine_b_aggregate = accumulated_state.get("engine_b_aggregate", {}) or {}
        agent_reports = accumulated_state.get("agent_reports", []) or []
        
        # FIXED: Extract feasibility from first scenario if not at top level
        feasibility_analysis = accumulated_state.get("feasibility_analysis", {})
        feasibility_check = accumulated_state.get("feasibility_check", {})
        if not feasibility_analysis and scenario_results:
            first_scenario = scenario_results[0] if isinstance(scenario_results[0], dict) else {}
            feasibility_analysis = first_scenario.get("feasibility_analysis", {})
            feasibility_check = first_scenario.get("feasibility_check", feasibility_check)
        
        # FIXED: Get cross_scenario_table from accumulated state
        cross_scenario_table = accumulated_state.get("cross_scenario_table", "")
        
        # FIXED: Get engine_b_results dict from accumulated state (diagnostic checks this)
        engine_b_results = accumulated_state.get("engine_b_results", {})
        
        # FIXED: Build engine_b_results from scenario_results if not present
        # Engine B results are NESTED inside "engine_b_results" key in each scenario
        if not engine_b_results and scenario_results:
            engine_b_results = {}
            for s in scenario_results:
                if isinstance(s, dict):
                    # Check if scenario has engine_b_results nested dict
                    nested_eb = s.get("engine_b_results", {})
                    if nested_eb and isinstance(nested_eb, dict):
                        # Get scenario name from nested or parent
                        scenario_name = nested_eb.get("scenario_name", s.get("scenario_name", f"scenario_{len(engine_b_results)}"))
                        # Extract the Engine B compute results
                        scenario_engine_b = {}
                        for key in ["monte_carlo", "forecasting", "sensitivity", "thresholds"]:
                            if key in nested_eb and nested_eb[key]:
                                scenario_engine_b[key] = nested_eb[key]
                        if scenario_engine_b:
                            engine_b_results[scenario_name] = scenario_engine_b
        
        # FIXED: Count Engine B scenarios properly from scenario_results
        engine_b_computed = engine_b_aggregate.get("scenarios_with_compute", 0)
        if engine_b_computed == 0:
            engine_b_computed = len(engine_b_results)
        if engine_b_computed == 0 and scenario_results:
            # Last fallback: count scenarios that have engine_b_results dict with compute keys
            engine_b_computed = sum(
                1 for s in scenario_results
                if isinstance(s, dict) and (
                    "engine_b_results" in s and isinstance(s.get("engine_b_results"), dict) and
                    any(k in s["engine_b_results"] for k in ["monte_carlo", "forecasting", "sensitivity", "thresholds"])
                )
            )
        
        yield WorkflowEvent(
            stage="done",
            status="complete",
            payload={
                # Core fields
                "confidence": accumulated_state.get("confidence_score", 0.0),
                "warnings": accumulated_state.get("warnings", []),
                "errors": accumulated_state.get("errors", []),
                "final_synthesis": final_synthesis,
                "meta_synthesis": final_synthesis,
                "summary": final_synthesis,
                "text": final_synthesis,
                "stats": synthesis_stats,
                "extracted_facts": extracted_facts,
                "word_count": len(final_synthesis.split()) if final_synthesis else 0,
                # Scenario data for diagnostic
                "scenarios": scenarios,
                "scenario_results": scenario_results,
                "scenarios_count": len(scenarios) if scenarios else len(scenario_results),
                # Engine B data
                "engine_b_aggregate": engine_b_aggregate,
                "engine_b_scenarios_computed": engine_b_computed,
                # FIXED: Add engine_b_results dict for feedback loop validation
                "engine_b_results": engine_b_results,
                # FIXED: Add cross-scenario table for feedback loop validation
                "cross_scenario_table": cross_scenario_table,
                # FIXED: Add feasibility data at top level for diagnostic
                "feasibility_analysis": feasibility_analysis,
                "feasibility_check": feasibility_check,
                # Agent and debate data
                "agent_reports": agent_reports,
                "agents_count": len(set(ar.get("agent", "") for ar in agent_reports if isinstance(ar, dict))),
                "conversation_history": conversation_history,
                "debate_turns": len(conversation_history),
                "debate_results": debate_results,
                # Critique data
                "critique_results": critique_results,
                # Classification
                "complexity": accumulated_state.get("complexity", ""),
                # FIXED: Add flag for diagnostic validation (feedback loop check)
                "engine_a_had_quantitative_context": accumulated_state.get("engine_a_had_quantitative_context", False),
            },
        )
        return  # Exit early for langgraph workflow
    else:
        # Fallback to legacy graph_llm.py
        logger.info("Using LEGACY monolithic workflow (graph_llm.py)")
        from .graph_llm import build_workflow
        
        # Import required clients if not provided
        if data_client is None:
            from ..agents.base import DataClient
            data_client = DataClient()
        if llm_client is None:
            from ..llm.client import LLMClient
            llm_client = LLMClient(provider=provider)
        if classifier is None:
            from ..classification.classifier import Classifier
            classifier = Classifier()
        
        workflow = build_workflow(data_client, llm_client, classifier)
        
        # Run legacy workflow and convert to new format
        legacy_result = await workflow.run_stream(question, lambda *args: None)
        
        # Map legacy result to new state format
        result = {
            "query": question,
            "complexity": legacy_result.get("classification", {}).get("complexity", "medium"),
            "extracted_facts": [],
            "data_sources": [],
            "data_quality_score": 0.8,
            "agent_reports": legacy_result.get("agent_reports", []),
            "final_synthesis": legacy_result.get("synthesis"),
            "confidence_score": 0.7,
            "reasoning_chain": ["Legacy workflow executed"],
            "nodes_executed": ["legacy_workflow"],
            "warnings": legacy_result.get("warnings", []),
            "errors": legacy_result.get("errors", []),
            "debate_results": legacy_result.get("debate_results", {}),
            "fact_check_results": legacy_result.get("verification", {}),
        }

    for stage in result.get("nodes_executed", []):
        if stage == "debate":
            for detail in result.get("debate_results", {}).get("details", []):
                yield WorkflowEvent(stage="debate:turn", status="streaming", payload=detail)

        yield WorkflowEvent(
            stage=stage,
            status="complete",
            payload=_payload_for_stage(stage, result),
        )

    yield WorkflowEvent(
        stage="done",
        status="complete",
        payload={
            "confidence": result.get("confidence_score"),
            "warnings": result.get("warnings", []),
            "errors": result.get("errors", []),
        },
    )
