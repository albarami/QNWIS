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
        "agent_outputs": {},
        "synthesis": "",
        "confidence_scores": {},
        "metrics": {}
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
            
            # Capture workflow data for executive dashboard
            elif event.status == "complete" and event.stage == "classify":
                workflow_data["classification"] = event.payload.get("classification", {})
            
            elif event.status == "complete" and event.stage == "prefetch":
                workflow_data["prefetched_queries"] = event.payload.get("query_ids", [])
            
            elif event.status == "complete" and event.stage == "rag":
                # H4: Display RAG context retrieval
                rag_payload = event.payload
                snippets_count = rag_payload.get("snippets_retrieved", 0)
                sources = rag_payload.get("sources", [])
                if snippets_count > 0:
                    await render_info(
                        f"📚 Retrieved {snippets_count} context snippets from external sources: "
                        f"{', '.join(sources)}"
                    )
            
            elif event.status == "complete" and event.stage == "agent_selection":
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
            
            elif event.status == "complete" and event.stage == "agents":
                # Extract agent outputs from payload
                agent_results = event.payload.get("agent_results", {})
                workflow_data["agent_outputs"] = agent_results
                workflow_data["confidence_scores"] = event.payload.get("confidence_scores", {})

            # Handle streaming tokens (synthesis)
            elif event.status == "streaming" and "token" in event.payload:
                token = event.payload["token"]
                inc_tokens(1)
                await response_msg.stream_token(token)
                has_content = True

            # Handle stage completion
            elif event.status == "complete":
                await render_stage(
                    event.stage,
                    latency_ms=event.latency_ms,
                    status="complete",
                )
                
                # H3: Display verification warnings if verification stage completed
                if event.stage == "verify":
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
        
        # Generate Executive Dashboard (H2) if we have content
        if has_content and workflow_data["agent_outputs"]:
            try:
                dashboard_msg = await cl.Message(content="").send()
                await dashboard_msg.stream_token("\n\n---\n\n")
                await dashboard_msg.stream_token("# 📊 Executive Dashboard\n\n")
                
                # Create executive dashboard
                dashboard = ExecutiveDashboard()
                findings_panel = AgentFindingsPanel()
                
                # Process agent outputs
                for agent_name, agent_output in workflow_data["agent_outputs"].items():
                    if isinstance(agent_output, str) and agent_output.strip():
                        # Parse findings from agent output
                        agent_findings = parse_agent_output_to_findings(
                            agent_name=agent_name,
                            output=agent_output,
                            default_confidence=workflow_data["confidence_scores"].get(agent_name, 0.75)
                        )
                        
                        # Add to findings panel
                        for finding in agent_findings:
                            findings_panel.add_finding(finding)
                            dashboard.add_agent_finding(
                                agent_name=finding.agent_name,
                                finding=finding.content,
                                confidence=finding.confidence,
                                category=finding.category
                            )
                
                # Set overall confidence
                if workflow_data["confidence_scores"]:
                    avg_confidence = sum(workflow_data["confidence_scores"].values()) / len(workflow_data["confidence_scores"])
                    dashboard.set_confidence_score(avg_confidence)
                
                # Generate and display executive summary
                executive_summary = dashboard.generate_executive_summary()
                await dashboard_msg.stream_token(executive_summary)
                
                # Show top findings summary
                await dashboard_msg.stream_token("\n\n---\n\n")
                summary_stats = findings_panel.render_summary()
                await dashboard_msg.stream_token(summary_stats)
                
                await dashboard_msg.update()
                
                logger.info(
                    f"rid={observed_request_id} dashboard_generated=true "
                    f"findings_count={len(findings_panel.findings)}"
                )
                
            except Exception as dashboard_error:
                logger.error(f"Failed to generate executive dashboard: {dashboard_error}")
                # Don't fail the entire workflow if dashboard fails
                await render_warning("Executive dashboard generation encountered an issue.")

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
