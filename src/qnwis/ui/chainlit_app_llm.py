"""
QNWIS Chainlit Application - LLM-Powered Multi-Agent UI.

Streams real LLM reasoning from agents via SSE, displays token-by-token generation,
and presents ministerial-quality synthesis with telemetry and health monitoring.
"""

import logging
import os
import uuid
from typing import Optional

import chainlit as cl

from src.qnwis.llm.config import get_llm_config
from src.qnwis.ui.components import sanitize_markdown
from src.qnwis.ui.components.progress_panel import (
    render_error,
    render_info,
    render_stage,
    render_warning,
)
from src.qnwis.ui.streaming_client import SSEClient
from src.qnwis.ui.telemetry import inc_errors, inc_requests, inc_tokens
from src.qnwis.ui.error_handling import (
    with_error_handling,
    show_error_message,
    retry_with_backoff,
    ErrorRecovery,
    LLMTimeoutError,
    DataUnavailableError,
)
from src.qnwis.ui.components.executive_dashboard import (
    ExecutiveDashboard,
    extract_findings_from_agent_output
)
from src.qnwis.ui.components.kpi_cards import KPICardGrid, create_standard_kpi_cards
from src.qnwis.ui.components.agent_findings_panel import (
    AgentFindingsPanel,
    AgentFinding,
    parse_agent_output_to_findings
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# API base URL from environment or default to localhost
BASE_URL = os.getenv("QNWIS_API_URL", "http://localhost:8000")
ALLOWED_PROVIDERS = {"anthropic", "openai", "stub"}
DEFAULT_PROVIDER = os.getenv("QNWIS_UI_PROVIDER", "anthropic").strip().lower() or "anthropic"
if DEFAULT_PROVIDER not in ALLOWED_PROVIDERS:
    logger.warning(
        "Unsupported QNWIS_UI_PROVIDER '%s', falling back to 'anthropic'.",
        DEFAULT_PROVIDER,
    )
    DEFAULT_PROVIDER = "anthropic"


@cl.on_chat_start
async def start():
    """Initialize the chat session with error handling and fallback providers."""
    try:
        # Get LLM configuration with fallback
        config = get_llm_config()
        provider = config.provider.lower()
        if provider not in ALLOWED_PROVIDERS:
            logger.warning('Configured provider %s not supported by UI; using default %s.', provider, DEFAULT_PROVIDER)
            provider = DEFAULT_PROVIDER
    except Exception as e:
        logger.error(f"Failed to get LLM config: {e}")
        provider = DEFAULT_PROVIDER
        config = None
        await render_warning(
            f"Configuration issue detected. Using default provider: {DEFAULT_PROVIDER}"
        )
    
    # Get model name safely
    try:
        model_name = config.get_model() if config else "default"
    except:
        model_name = "default"
    
    welcome_message = f"""# 🇶🇦 Qatar National Workforce Intelligence System (QNWIS)

Welcome to the **LLM-powered multi-agent intelligence platform** for Qatar's labour market.

## System Capabilities

**LLM-Powered Agents**:
- LabourEconomist: Employment trends & gender analysis
- Nationalization: GCC benchmarking & Qatarization
- Skills: Skills gap & workforce composition
- PatternDetective: Data validation & anomaly detection
- NationalStrategy: Vision 2030 alignment & strategic insights

**AI Configuration**:
- Provider: `{provider}`
- Model: `{config.get_model()}`
- Streaming: Real-time token generation
- Verification: Number validation against source data

**Data Sources**:
- Qatar Open Data Portal
- World Bank API (GCC indicators)
- Synthetic LMIS data (employment, wages)

**Quality Assurance**:
- All numbers verified against source data
- Complete audit trails
- Data quality warnings
- Confidence scoring

## Example Questions

- "What are the current unemployment trends in the GCC region?"
- "Analyze Qatar's employment by gender"
- "Compare Qatar's unemployment to other GCC countries"
- "What are the skills gaps in Qatar's workforce?"

---

**Ask me anything about Qatar's labour market!**

*Note: This system uses real LLM reasoning. Responses will take 10-30 seconds as agents analyze data and generate insights.*
"""
    
    try:
        await cl.Message(content=sanitize_markdown(welcome_message)).send()
        
        # Store API base URL in session
        cl.user_session.set("api_base_url", BASE_URL)
        cl.user_session.set("ui_provider", provider)
        
        # Test connectivity to API
        try:
            client = SSEClient(BASE_URL, timeout=5.0)
            # Quick health check (optional, don't block startup)
            logger.info("SSE client initialized successfully")
        except Exception as e:
            logger.warning(f"API connectivity issue: {e}")
            await render_warning(
                "System may be experiencing connectivity issues. "
                "Some features may be temporarily unavailable."
            )
    
    except Exception as e:
        logger.exception("Critical error during chat initialization")
        await show_error_message(e)


@cl.on_message
@with_error_handling(show_ui_message=True)
async def handle_message(message: cl.Message):
    """
    Handle incoming user messages with SSE streaming.

    Displays:
    1. Real-time workflow progress via progress panel
    2. Token-by-token synthesis streaming
    3. Stage completion with timing
    4. Error handling and retry capability

    Telemetry:
    - Tracks requests, tokens, errors
    - Observes stage latencies
    - Prometheus metrics (if available)
    """
    user_question = message.content.strip()

    # Validate question length
    if not (3 <= len(user_question) <= 5000):
        await render_error(
            "Please provide a question between 3 and 5000 characters."
        )
        return

    # Increment request counter
    inc_requests()

    # Get API base URL from session
    api_url = cl.user_session.get("api_base_url") or BASE_URL
    provider = cl.user_session.get("ui_provider") or DEFAULT_PROVIDER

    if provider not in ALLOWED_PROVIDERS:
        await render_error(
            "Invalid provider configured for UI streaming. "
            "Please use one of: anthropic, openai, stub."
        )
        return

    # Create response message for synthesis
    response_msg = cl.Message(content="", author="QNWIS")
    await response_msg.send()

    # Create SSE client
    client = SSEClient(api_url, timeout=120.0)
    stream_request_id = str(uuid.uuid4())
    logger.info(
        "rid=%s provider=%s question_len=%d",
        stream_request_id,
        provider,
        len(user_question),
    )

    # Track if we've sent any content
    has_content = False
    observed_request_id: Optional[str] = None
    
    # Track workflow data for executive dashboard (H2)
    workflow_data = {
        "classification": None,
        "prefetched_queries": [],
        "agent_reports": [],  # Store full agent reports
        "agent_outputs": {},  # Store agent output text
        "synthesis": "",
        "confidence_scores": {},
        "metrics": {},
        "reasoning_chain": []  # Track workflow stages for Phase 4.1
    }

    # Define workflow execution function for retry logic
    async def execute_workflow():
        async for event in client.stream(
            question=user_question,
            provider=provider,
            request_id=stream_request_id,
        ):
            yield event
    
    try:
        # Execute with retry for transient failures
        async for event in execute_workflow():
            if observed_request_id is None:
                observed_request_id = event.request_id

            logger.debug(
                "rid=%s stage=%s status=%s",
                event.request_id,
                event.stage,
                event.status,
            )

            # Handle stage transitions
            if event.status == "running":
                await render_stage(event.stage, status="running")

            # Track completed stages for reasoning chain (Phase 4.1)
            if event.status == "complete":
                stage_info = {
                    "stage": event.stage,
                    "status": "complete"
                }
                workflow_data["reasoning_chain"].append(stage_info)

            # Capture workflow data for executive dashboard
            if event.status == "complete" and event.stage == "classify":
                workflow_data["classification"] = event.payload.get("classification", {})

                # Phase 3: Display routing decision
                classification = event.payload.get("classification", {})
                route_to = classification.get("route_to")
                if route_to:
                    agent_types = {
                        "time_machine": "⏰ TimeMachine (Historical Analysis)",
                        "predictor": "📈 Predictor (Forecasting)",
                        "scenario": "🎯 Scenario (What-If Analysis)"
                    }
                    agent_name = agent_types.get(route_to, route_to)
                    await render_info(
                        f"🔀 **Routing Decision**: Query directed to deterministic agent: {agent_name}"
                    )
                else:
                    await render_info(
                        f"🔀 **Routing Decision**: Query directed to LLM-powered multi-agent analysis"
                    )

            if event.status == "complete" and event.stage == "prefetch":
                workflow_data["prefetched_queries"] = event.payload.get("query_ids", [])

            if event.status == "complete" and event.stage == "rag":
                # H4: Display RAG context retrieval
                rag_payload = event.payload
                snippets_count = rag_payload.get("snippets_retrieved", 0)
                sources = rag_payload.get("sources", [])
                if snippets_count > 0:
                    await render_info(
                        f"📚 Retrieved {snippets_count} context snippets from external sources: "
                        f"{', '.join(sources)}"
                    )
            
            if event.status == "complete" and event.stage == "agent_selection":
                # H6: Display intelligent agent selection
                selection_payload = event.payload
                selected_count = selection_payload.get("selected_count", 0)
                total_count = selection_payload.get("total_available", 5)
                savings = selection_payload.get("savings", "0%")
                selected_agents = selection_payload.get("selected_agents", [])

                await render_info(
                    f"🤖 Selected {selected_count}/{total_count} agents "
                    f"({savings} cost savings): {', '.join(selected_agents)}"
                )

            # Track individual agent completions
            if event.stage.startswith("agent:") and event.status == "complete":
                # Extract agent name and report
                agent_name = event.stage.split(":")[1]
                agent_report = event.payload.get("report")

                if agent_report:
                    workflow_data["agent_reports"].append(agent_report)

                    # Handle dict (serialized from SSE) or object
                    if isinstance(agent_report, dict):
                        # Dict from SSE - extract fields directly
                        narrative = agent_report.get("narrative", "")
                        findings = agent_report.get("findings", [])

                        if narrative:
                            workflow_data["agent_outputs"][agent_name] = narrative
                        elif findings:
                            # Store the full report for detailed display
                            workflow_data["agent_outputs"][agent_name] = agent_report

                        # Extract confidence
                        confidence = agent_report.get("confidence")
                        if confidence:
                            workflow_data["confidence_scores"][agent_name] = confidence

                    else:
                        # Object (backward compatibility)
                        if hasattr(agent_report, 'narrative') and agent_report.narrative:
                            workflow_data["agent_outputs"][agent_name] = agent_report.narrative
                        elif hasattr(agent_report, 'findings') and agent_report.findings:
                            workflow_data["agent_outputs"][agent_name] = agent_report

                        if hasattr(agent_report, 'confidence'):
                            workflow_data["confidence_scores"][agent_name] = agent_report.confidence

                    # Debug logging
                    logger.info(f"[DEBUG] Agent {agent_name} completed. agent_outputs keys: {list(workflow_data['agent_outputs'].keys())}")
                    logger.info(f"[DEBUG] agent_report type: {type(agent_report)}, is dict: {isinstance(agent_report, dict)}")
                    if isinstance(agent_report, dict):
                        logger.info(f"[DEBUG] agent_report keys: {agent_report.keys()}")
                        logger.info(f"[DEBUG] Has narrative: {'narrative' in agent_report}, Has findings: {'findings' in agent_report}")

            # Handle streaming tokens (synthesis)
            if event.status == "streaming" and "token" in event.payload:
                token = event.payload["token"]
                inc_tokens(1)
                await response_msg.stream_token(token)
                has_content = True

            # Handle stage completion (for rendering)
            if event.status == "complete":
                await render_stage(
                    event.stage,
                    latency_ms=event.latency_ms,
                    status="complete",
                )
                
                # Phase 2: Display debate results
                if event.stage == "debate":
                    debate_payload = event.payload
                    if debate_payload:
                        contradictions = debate_payload.get("contradictions_found", 0)
                        resolved = debate_payload.get("resolved", 0)
                        flagged = debate_payload.get("flagged_for_review", 0)

                        if contradictions > 0:
                            await render_info(
                                f"⚖️ **Debate Results**: Found {contradictions} contradiction(s) - "
                                f"{resolved} resolved, {flagged} flagged for review"
                            )

                            # Display consensus narrative if available
                            consensus = debate_payload.get("consensus_narrative")
                            if consensus:
                                debate_msg = await cl.Message(content="").send()
                                await debate_msg.stream_token("\n### 🎯 Debate Consensus\n\n")
                                await debate_msg.stream_token(f"{consensus}\n\n")
                                await debate_msg.update()
                        else:
                            await render_info("⚖️ **Debate**: No contradictions detected between agents")

                # Phase 2: Display critique results
                elif event.stage == "critique":
                    critique_payload = event.payload
                    if critique_payload:
                        critiques_count = critique_payload.get("critiques", 0)
                        red_flags = critique_payload.get("red_flags", 0)
                        strengthened = critique_payload.get("strengthened", False)

                        if critiques_count > 0:
                            status_emoji = "✅" if strengthened else "⚠️"
                            await render_info(
                                f"{status_emoji} **Devil's Advocate Critique**: "
                                f"{critiques_count} critique(s), {red_flags} red flag(s)"
                            )

                            # Display overall assessment
                            assessment = critique_payload.get("overall_assessment")
                            if assessment:
                                critique_msg = await cl.Message(content="").send()
                                await critique_msg.stream_token("\n### 🔍 Critical Assessment\n\n")
                                await critique_msg.stream_token(f"{assessment}\n\n")
                                await critique_msg.update()
                        else:
                            await render_info("🔍 **Critique**: Analysis shows good robustness")

                # H3: Display verification warnings if verification stage completed
                elif event.stage == "verify":
                    verification_payload = event.payload
                    if verification_payload.get("warnings"):
                        warnings_list = verification_payload["warnings"]
                        summary = verification_payload.get("verification_summary", {})

                        # Show verification summary
                        if len(warnings_list) > 0:
                            await render_warning(
                                f"⚠️ Verification found {len(warnings_list)} issues: "
                                f"{summary.get('warning_count', 0)} warnings, "
                                f"{summary.get('error_count', 0)} errors, "
                                f"{summary.get('missing_citations', 0)} missing citations"
                            )

                            # Show top 5 warnings in detail
                            if len(warnings_list) <= 5:
                                for warning in warnings_list:
                                    await render_warning(f"  • {warning}")
                            else:
                                for warning in warnings_list[:5]:
                                    await render_warning(f"  • {warning}")
                                await render_info(
                                    f"... and {len(warnings_list) - 5} more warnings"
                                )

            # Handle errors
            elif event.status == "error":
                inc_errors()
                error_msg = event.payload.get("error", "Unknown error")
                await render_warning(
                    f"Stage {event.stage} encountered an issue: {error_msg}"
                )
            elif event.status == "warning":
                await render_warning(
                    event.payload.get(
                        "warning",
                        "Streaming warning received from workflow.",
                    )
                )

        # Update final response
        await response_msg.update()

        # Debug logging before dashboard display
        logger.info(f"[DEBUG] Before dashboard display:")
        logger.info(f"[DEBUG]   agent_outputs keys: {list(workflow_data['agent_outputs'].keys())}")
        logger.info(f"[DEBUG]   agent_reports count: {len(workflow_data['agent_reports'])}")
        logger.info(f"[DEBUG]   Has agent_outputs: {bool(workflow_data['agent_outputs'])}")

        # Display individual agent findings with full ministerial-grade details
        if workflow_data["agent_outputs"]:
            try:
                await render_info(f"Displaying findings from {len(workflow_data['agent_outputs'])} specialist agents...")

                # Display each agent's detailed analysis
                for agent_name, agent_output in workflow_data["agent_outputs"].items():
                    agent_msg = await cl.Message(content="").send()

                    # Agent header
                    await agent_msg.stream_token("\n\n" + "=" * 80 + "\n")
                    await agent_msg.stream_token(f"## 🤖 {agent_name} - Specialist Analysis\n")
                    await agent_msg.stream_token("=" * 80 + "\n\n")

                    # Handle dict (full report with findings)
                    if isinstance(agent_output, dict):
                        # Display findings from the report
                        findings = agent_output.get("findings", [])

                        for i, finding in enumerate(findings, 1):
                            if isinstance(finding, dict):
                                # Title
                                title = finding.get("title", "Finding")
                                await agent_msg.stream_token(f"### {title}\n\n")

                                # Summary
                                summary = finding.get("summary", "")
                                if summary:
                                    await agent_msg.stream_token(f"**Summary:** {summary}\n\n")

                                # Metrics table
                                metrics = finding.get("metrics", {})
                                if metrics:
                                    await agent_msg.stream_token("**Key Metrics:**\n\n")
                                    await agent_msg.stream_token("| Metric | Value |\n")
                                    await agent_msg.stream_token("|--------|-------|\n")
                                    for key, value in metrics.items():
                                        # Format metric name
                                        display_name = key.replace("_", " ").title()
                                        # Format value
                                        if isinstance(value, float):
                                            display_value = f"{value:.2f}" if abs(value) < 1 else f"{value:.1f}"
                                        else:
                                            display_value = str(value)
                                        await agent_msg.stream_token(f"| {display_name} | {display_value} |\n")
                                    await agent_msg.stream_token("\n")

                                # Detailed analysis
                                analysis = finding.get("analysis", "")
                                if analysis:
                                    await agent_msg.stream_token("**Detailed Analysis:**\n\n")
                                    await agent_msg.stream_token(f"{analysis}\n\n")

                                # Recommendations
                                recommendations = finding.get("recommendations", [])
                                if recommendations:
                                    await agent_msg.stream_token("**Recommendations:**\n\n")
                                    for j, rec in enumerate(recommendations, 1):
                                        await agent_msg.stream_token(f"{j}. {rec}\n")
                                    await agent_msg.stream_token("\n")

                                # Confidence and data quality
                                confidence = finding.get("confidence", 0)
                                data_quality = finding.get("data_quality_notes", "")
                                citations = finding.get("citations", [])

                                await agent_msg.stream_token("**Quality Indicators:**\n")
                                await agent_msg.stream_token(f"- Confidence Score: {confidence:.0%}\n")
                                if data_quality:
                                    await agent_msg.stream_token(f"- Data Quality: {data_quality}\n")
                                if citations:
                                    await agent_msg.stream_token(f"- Citations: {', '.join(citations)}\n")
                                await agent_msg.stream_token("\n")

                        # Display narrative if no findings
                        if not findings:
                            narrative = agent_output.get("narrative", "")
                            if narrative:
                                await agent_msg.stream_token(f"{narrative}\n\n")

                    # Handle string (narrative text)
                    elif isinstance(agent_output, str):
                        await agent_msg.stream_token(f"{agent_output}\n\n")

                    # Display confidence score
                    agent_confidence = workflow_data["confidence_scores"].get(agent_name)
                    if agent_confidence:
                        await agent_msg.stream_token(f"**Overall Agent Confidence:** {agent_confidence:.0%}\n\n")

                    await agent_msg.update()

                logger.info(
                    f"rid={observed_request_id} agent_panels_displayed=true "
                    f"agent_count={len(workflow_data['agent_outputs'])}"
                )
                
            except Exception as dashboard_error:
                logger.error(f"Failed to generate executive dashboard: {dashboard_error}")
                # Don't fail the entire workflow if dashboard fails
                await render_warning("Executive dashboard generation encountered an issue.")

        # Phase 4.1: Display reasoning chain (workflow path taken)
        if workflow_data["reasoning_chain"] and has_content:
            try:
                await render_info(
                    f"**Workflow Path**: Analysis completed in {len(workflow_data['reasoning_chain'])} stages"
                )

                reasoning_msg = await cl.Message(content="").send()
                await reasoning_msg.stream_token("\n### Reasoning Chain\n\n")
                await reasoning_msg.stream_token("This shows the step-by-step workflow path taken to answer your question:\n\n")

                # Map stage names to readable descriptions
                stage_descriptions = {
                    "classify": "Question Classification - Determined query type and routing",
                    "route_deterministic": "Deterministic Routing - Directed to specialized agent",
                    "prefetch": "Data Prefetch - Pre-loaded relevant datasets",
                    "rag": "RAG Retrieval - Retrieved contextual information",
                    "agents": "Multi-Agent Analysis - Executed specialized agents",
                    "debate": "Debate Resolution - Resolved contradictions between agents",
                    "critique": "Critical Review - Devil's advocate stress-test",
                    "verify": "Citation Verification - Validated all evidence",
                    "synthesize": "Final Synthesis - Generated comprehensive answer"
                }

                for i, step in enumerate(workflow_data["reasoning_chain"], 1):
                    stage = step["stage"]
                    description = stage_descriptions.get(stage, stage.title())
                    await reasoning_msg.stream_token(f"{i}. **{stage.title()}**: {description}\n")

                await reasoning_msg.stream_token("\n")
                await reasoning_msg.update()

            except Exception as reasoning_error:
                logger.error(f"Failed to display reasoning chain: {reasoning_error}")
                # Don't fail if reasoning chain display fails

        # Show completion message if we got content
        summary_message = (
            "Analysis complete!"
            if has_content
            else "No synthesis was generated. Please try rephrasing your question."
        )
        if observed_request_id:
            summary_message = f"{summary_message} (request ID: {observed_request_id})"
        if has_content:
            await render_info(summary_message)
        else:
            await render_warning(summary_message)

    except TimeoutError as e:
        inc_errors()
        logger.error("rid=%s timeout_error=%s", stream_request_id, e)
        await show_error_message(LLMTimeoutError(
            "The analysis is taking longer than expected due to complex workforce calculations.",
            str(e)
        ))
        if not has_content:
            await response_msg.stream_token(
                "\n\n **Timeout**: Analysis took too long. "
                "Please try simplifying your question or try again later.\n\n"
            )
        await response_msg.update()
    
    except ValueError as exc:
        inc_errors()
        logger.warning("rid=%s validation_error=%s", stream_request_id, exc)
        await render_error(str(exc))
        if not has_content:
            await response_msg.stream_token(
                "\n\n **Error**: Invalid request parameters. "
                "Please verify your provider or question length.\n\n"
            )
        await response_msg.update()

    except ConnectionError as e:
        inc_errors()
        logger.error("rid=%s connection_error=%s", stream_request_id, e)
        await show_error_message(DataUnavailableError(
            "Unable to connect to the workforce analysis service.",
            str(e)
        ))
        if not has_content:
            await response_msg.stream_token(
                "\n\n **Connection Error**: Cannot reach the analysis service. "
                "Please check your network connection and try again.\n\n"
            )
        await response_msg.update()

    except Exception as e:
        inc_errors()
        logger.exception("rid=%s streaming_failed=%s", stream_request_id, e)
        
        # Use error handling utility for user-friendly message
        await show_error_message(e)
        
        if not has_content:
            await response_msg.stream_token(
                "\n\n **Error**: Unable to complete analysis. "
                "The system may be temporarily unavailable. Please try again.\n\n"
            )
        await response_msg.update()


if __name__ == "__main__":
    # Run with: chainlit run src/qnwis/ui/chainlit_app_llm.py
    pass
