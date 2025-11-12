"""
QNWIS Chainlit Application - Enterprise-Grade Multi-Agent UI.

Streams LangGraph workflow execution, renders per-agent conversations,
shows verification and audit trails, integrates RAG, and handles model fallback.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import chainlit as cl

from ..agents.base import DataClient
from ..config.model_select import call_with_model_fallback, resolve_models
from ..orchestration.workflow_adapter import run_workflow_stream
from ..verification.ui_bridge import (
    render_agent_finding_panel,
    render_audit_panel,
    render_verification_panel,
    render_raw_evidence_panel,
)
from .components import render_stage_card, render_timeline_widget, sanitize_markdown

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

RAW_EVIDENCE_MAX_ROWS = 5
_raw_data_client: Optional[DataClient] = None


def _get_data_client() -> DataClient:
    """Return (and lazily initialize) the deterministic data client used for previews."""
    global _raw_data_client
    if _raw_data_client is None:
        _raw_data_client = DataClient()
    return _raw_data_client


@cl.on_chat_start
async def start():
    """Initialize the chat session."""
    # Resolve models
    primary_model, fallback_model = resolve_models()
    
    welcome_message = f"""# 🇶🇦 Qatar National Workforce Intelligence System (QNWIS)

Welcome to the **enterprise-grade multi-agent intelligence platform** for Qatar's labour market.

## 🎯 System Capabilities

**Multi-Agent Analysis**:
- 🕐 **TimeMachine**: Historical trends & baselines
- 🔍 **PatternMiner**: Correlations & seasonal effects
- 📈 **Predictor**: 12-month forecasts & early warnings
- 🎭 **Scenario**: What-if analysis & policy simulation
- 🔬 **PatternDetective**: Anomaly detection & root cause
- 🌍 **NationalStrategy**: GCC benchmarking & Vision 2030
- 💼 **LabourEconomist**: Employment analysis
- 🎓 **Skills**: Skills gap analysis

**Data Sources**:
- 📊 Qatar Open Data Portal (1,152 datasets)
- 🌍 World Bank API (GCC labour indicators)
- 📈 Synthetic LMIS data (employment, wages, qatarization)
- 🔍 RAG-enhanced external context

**AI Models**:
- 🧠 Primary: `{primary_model}`
- 🔄 Fallback: `{fallback_model}`

**Quality Assurance**:
- ✅ Citation enforcement (every metric traceable)
- 🧪 Numeric verification (range checks)
- 📊 Confidence scoring (0-100%)
- 📋 Complete audit trails

## 💡 Example Questions

- "What are the current unemployment trends in the GCC region?"
- "Forecast Healthcare qatarization for the next 12 months"
- "What if Construction retention improved by 10%?"
- "Compare Qatar's labour market to KSA and UAE"
- "Detect anomalies in sector attrition rates"

---

**Ask me anything about Qatar's labour market!**
"""
    
    await cl.Message(content=sanitize_markdown(welcome_message)).send()
    
    # Store session state
    cl.user_session.set("stages_completed", [])
    cl.user_session.set("agent_findings", {})
    cl.user_session.set("model_fallback_used", False)
    cl.user_session.set("raw_evidence_registry", {})
    cl.user_session.set("raw_evidence_counter", 0)


@cl.on_message
async def handle_message(message: cl.Message):
    """
    Handle incoming user messages and stream LangGraph workflow execution.
    
    This function orchestrates the complete workflow:
    1. Stream timeline updates
    2. Render stage cards as they complete
    3. Display per-agent findings with full details
    4. Show verification and audit results
    5. Present final synthesized answer
    """
    user_question = message.content
    request_id = f"req_{int(datetime.utcnow().timestamp() * 1000)}"
    
    logger.info(f"[{request_id}] Processing question: {user_question[:50]}...")
    
    # Reset per-request state
    cl.user_session.set("model_fallback_used", False)
    cl.user_session.set("raw_evidence_registry", {})
    cl.user_session.set("raw_evidence_counter", 0)
    cl.user_session.set("current_request_id", request_id)
    
    # Initialize tracking
    stages_completed: List[str] = []
    agent_findings: Dict[str, List[Dict[str, Any]]] = {}
    timeline_msg = None
    
    try:
        # Create initial timeline
        timeline_msg = await cl.Message(
            content=sanitize_markdown(render_timeline_widget(stages_completed, "classify"))
        ).send()
        
        # Stream workflow execution
        async for event in run_workflow_stream(user_question, {"request_id": request_id}):
            stage = event.stage
            payload = event.payload
            latency_ms = event.latency_ms
            
            logger.info(f"[{request_id}] Stage completed: {stage} ({latency_ms}ms)")
            
            # Update timeline
            if stage.startswith("agent:"):
                current_stage = "agents"
            else:
                current_stage = stage
            
            if stage not in ["error"] and not stage.startswith("agent:"):
                stages_completed.append(stage)
            
            if timeline_msg:
                await timeline_msg.update(
                    content=sanitize_markdown(
                        render_timeline_widget(stages_completed, current_stage)
                    )
                )
            
            # Render stage card
            if stage == "classify":
                card_content = render_stage_card(stage, payload, latency_ms)
                await cl.Message(content=sanitize_markdown(card_content)).send()
            
            elif stage == "prefetch":
                card_content = render_stage_card(stage, payload, latency_ms)
                await cl.Message(content=sanitize_markdown(card_content)).send()
                
                # Show RAG context if available
                if payload.get("rag_snippets", 0) > 0:
                    rag_msg = "### 🔍 External Context Retrieved\n\n"
                    rag_msg += f"Retrieved {payload['rag_snippets']} context snippets "
                    rag_msg += f"from: {', '.join(payload.get('rag_sources', []))}\n\n"
                    rag_msg += "*Note: External context augments narrative only. "
                    rag_msg += "All metrics come from deterministic data layer.*"
                    await cl.Message(content=sanitize_markdown(rag_msg)).send()
            
            elif stage.startswith("agent:"):
                agent_name = payload.get("agent", stage.replace("agent:", ""))
                
                # Store findings
                if payload.get("status") == "completed":
                    agent_findings[agent_name] = payload.get("findings", [])
                    
                    # Render agent card
                    card_content = render_stage_card(stage, payload, latency_ms)
                    await cl.Message(content=sanitize_markdown(card_content)).send()
                    
                    # Render detailed findings
                    for finding in payload.get("findings", []):
                        finding_panel = render_agent_finding_panel(
                            agent_name,
                            finding,
                            show_full_evidence=False
                        )
                        evidence_key = _register_raw_evidence_payload(
                            request_id,
                            agent_name,
                            finding
                        )
                        message_kwargs: Dict[str, Any] = {
                            "content": sanitize_markdown(finding_panel)
                        }
                        if evidence_key:
                            message_kwargs["actions"] = [
                                cl.Action(
                                    name="view_raw_evidence",
                                    value=evidence_key,
                                    label="View raw evidence"
                                )
                            ]
                        await cl.Message(**message_kwargs).send()
                else:
                    # Error case
                    card_content = render_stage_card(stage, payload, latency_ms)
                    await cl.Message(content=sanitize_markdown(card_content)).send()
            
            elif stage == "verify":
                card_content = render_stage_card(stage, payload, latency_ms)
                await cl.Message(content=sanitize_markdown(card_content)).send()
                
                # Render detailed verification panel
                verification_panel = render_verification_panel(payload)
                await cl.Message(content=sanitize_markdown(verification_panel)).send()
            
            elif stage == "synthesize":
                card_content = render_stage_card(stage, payload, latency_ms)
                await cl.Message(content=sanitize_markdown(card_content)).send()
            
            elif stage == "done":
                # Final completion card
                card_content = render_stage_card(stage, payload, latency_ms)
                await cl.Message(content=sanitize_markdown(card_content)).send()
                
                # Render audit trail
                audit_data = payload.get("audit", {})
                if audit_data:
                    audit_panel = render_audit_panel(audit_data)
                    await cl.Message(content=sanitize_markdown(audit_panel)).send()
                
                # Render final synthesized answer
                council_report = payload.get("council_report", {})
                if council_report:
                    final_answer = _generate_final_answer(
                        council_report,
                        payload.get("rag_context", {}),
                        user_question
                    )
                    await cl.Message(content=sanitize_markdown(final_answer)).send()
                    
                    if cl.user_session.get("model_fallback_used"):
                        fallback_note = _render_fallback_notice()
                        await cl.Message(content=sanitize_markdown(fallback_note)).send()
            
            elif stage == "error":
                error_msg = f"""## ❌ Workflow Error

An error occurred during execution:

**Error**: {payload.get('error', 'Unknown error')}
**Type**: {payload.get('error_type', 'Unknown')}

Please try rephrasing your question or contact support if the issue persists.
"""
                await cl.Message(content=sanitize_markdown(error_msg)).send()
                return
        
        # Update final timeline
        if timeline_msg:
            await timeline_msg.update(
                content=sanitize_markdown(
                    render_timeline_widget(stages_completed + ["done"], "done")
                )
            )
        
        logger.info(f"[{request_id}] Workflow completed successfully")
        
    except Exception as e:
        logger.error(f"[{request_id}] Fatal error: {e}", exc_info=True)
        
        error_msg = f"""## ❌ System Error

A critical error occurred:

**Error**: {str(e)}

Please try again or contact support.
"""
        await cl.Message(content=sanitize_markdown(error_msg)).send()


@cl.action_callback("view_raw_evidence")
async def _handle_view_raw_evidence(action: cl.Action):
    """Display deterministic raw evidence rows when the user clicks the action button."""
    registry: Dict[str, Any] = cl.user_session.get("raw_evidence_registry") or {}
    payload = registry.get(action.value)
    
    if not payload:
        await cl.Message(
            content=sanitize_markdown("Raw evidence preview expired for this finding.")
        ).send()
        return
    
    evidence_tables = _build_raw_evidence_tables(payload.get("evidence", []))
    
    if not evidence_tables:
        await cl.Message(
            content=sanitize_markdown("No deterministic rows available for this finding.")
        ).send()
        return
    
    panel = render_raw_evidence_panel(
        payload.get("agent", "Agent"),
        payload.get("finding_title", "Finding"),
        evidence_tables
    )
    await cl.Message(content=sanitize_markdown(panel)).send()


def _generate_final_answer(
    council_report: Dict[str, Any],
    rag_context: Dict[str, Any],
    user_question: str
) -> str:
    """Render the final answer using model fallback if necessary."""
    primary_model, fallback_model = resolve_models()
    cl.user_session.set(
        "model_pair",
        {"primary": primary_model, "fallback": fallback_model}
    )
    
    def _primary() -> str:
        return _format_final_answer(
            council_report,
            rag_context,
            user_question,
            model_used=primary_model
        )
    
    def _fallback() -> str:
        return _format_final_answer(
            council_report,
            rag_context,
            user_question,
            model_used=fallback_model
        )
    
    final_answer, used_fallback = call_with_model_fallback(_primary, _fallback)
    cl.user_session.set("model_fallback_used", used_fallback)
    return final_answer


def _render_fallback_notice() -> str:
    """Build a user-facing note describing model fallback behavior."""
    pair = cl.user_session.get("model_pair") or {}
    request_id = cl.user_session.get("current_request_id", "unknown")
    primary = pair.get("primary", "Anthropic")
    fallback = pair.get("fallback", "OpenAI")
    
    return (
        "### 🔁 Model Fallback Engaged\n\n"
        f"Primary model `{primary}` became unavailable, "
        f"so the system seamlessly switched to `{fallback}`.\n\n"
        f"- **Request ID**: `{request_id}`\n"
        "- **Status**: Fallback succeeded, streaming uninterrupted\n"
        "- **Audit**: Logged in model_fallback channel"
    )


def _register_raw_evidence_payload(
    request_id: str,
    agent_name: str,
    finding: Dict[str, Any]
) -> Optional[str]:
    """Register per-finding evidence payload so it can be replayed on demand."""
    evidence = finding.get("evidence") or []
    if not evidence:
        return None
    
    registry: Dict[str, Any] = cl.user_session.get("raw_evidence_registry") or {}
    counter = int(cl.user_session.get("raw_evidence_counter", 0)) + 1
    cl.user_session.set("raw_evidence_counter", counter)
    
    key = f"{request_id}:{agent_name}:{counter}"
    registry[key] = {
        "agent": agent_name,
        "finding_title": finding.get("title", "Finding"),
        "evidence": evidence,
    }
    cl.user_session.set("raw_evidence_registry", registry)
    return key


def _build_raw_evidence_tables(evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fetch deterministic rows for each evidence entry (top-N rows only)."""
    tables: List[Dict[str, Any]] = []
    cache: Dict[str, List[Dict[str, Any]]] = {}
    
    for entry in evidence:
        query_id = entry.get("query_id")
        if not query_id:
            continue
        
        if query_id not in cache:
            cache[query_id] = _sample_query_rows(query_id)
        
        tables.append(
            {
                "query_id": query_id,
                "dataset_id": entry.get("dataset_id", "unknown"),
                "freshness": entry.get("freshness_as_of")
                or (entry.get("freshness") or {}).get("as_of"),
                "rows": cache[query_id],
            }
        )
    
    return tables


def _sample_query_rows(query_id: str) -> List[Dict[str, Any]]:
    """Load deterministic rows for previews without mutating core workflow."""
    try:
        result = _get_data_client().run(query_id)
    except Exception as exc:  # pragma: no cover - defensive logging only
        logger.warning("Failed to load rows for %s: %s", query_id, exc)
        return []
    
    preview_rows: List[Dict[str, Any]] = []
    for row in result.rows[:RAW_EVIDENCE_MAX_ROWS]:
        preview_rows.append({key: row.data.get(key) for key in row.data})
    return preview_rows


def _format_final_answer(
    council_report: Dict,
    rag_context: Dict,
    user_question: str,
    model_used: Optional[str] = None
) -> str:
    """
    Format the final synthesized answer with council findings.
    
    Args:
        council_report: Council synthesis results
        rag_context: RAG context data
        user_question: Original user question
        
    Returns:
        Formatted markdown answer
    """
    lines = ["# 📊 Intelligence Report\n"]
    
    # Executive summary
    lines.append("## Executive Summary\n")
    
    findings = council_report.get("findings", [])
    if findings:
        # Use first finding's summary as executive summary
        lines.append(findings[0].get("summary", "Analysis completed."))
        lines.append("")
    
    # Key metrics from consensus
    consensus = council_report.get("consensus", {})
    if consensus:
        lines.append("## Key Metrics\n")
        for key, value in consensus.items():
            readable_key = key.replace("_", " ").title()
            if isinstance(value, float):
                if "percent" in key:
                    formatted = f"{value:.1f}%"
                else:
                    formatted = f"{value:.2f}"
            else:
                formatted = str(value)
            lines.append(f"- **{readable_key}**: {formatted}")
        lines.append("")
    
    # Agent insights
    if len(findings) > 1:
        lines.append("## Multi-Agent Analysis\n")
        for finding in findings[:5]:  # Limit to top 5
            title = finding.get("title", "Untitled")
            summary = finding.get("summary", "")
            confidence = finding.get("confidence_score", 1.0)
            
            conf_icon = "🟢" if confidence >= 0.85 else "🟡" if confidence >= 0.70 else "🟠"
            
            lines.append(f"### {title} {conf_icon}")
            lines.append(f"{summary}\n")
    
    # Warnings
    warnings = council_report.get("warnings", [])
    if warnings:
        lines.append("## ⚠️ Data Quality Notes\n")
        for warning in warnings[:3]:
            lines.append(f"- {warning}")
        lines.append("")
    
    # Data sources
    lines.append("## 📚 Data Sources\n")
    lines.append("All metrics are traceable to deterministic data sources:")
    lines.append("- Qatar Open Data Portal")
    lines.append("- World Bank API")
    lines.append("- Synthetic LMIS aggregates")
    
    if rag_context.get("sources"):
        lines.append("\nExternal context provided by:")
        for source in rag_context["sources"]:
            lines.append(f"- {source}")
    
    lines.append("\n---")
    if model_used:
        lines.append(f"*Rendered via {model_used} with multi-agent consensus*")
    else:
        lines.append("*Generated by QNWIS Multi-Agent Intelligence System*")
    
    return "\n".join(lines)


# Entry point for running the app
# Run via: chainlit run src/qnwis/ui/chainlit_app.py
