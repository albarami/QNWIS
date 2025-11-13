"""
CLI command for querying QNWIS using the LLM multi-agent workflow.

Streams tokens by default for real-time output. Use --no-stream for
complete response after all stages finish.
"""

from __future__ import annotations

import asyncio
import logging

import click

from ..agents.base import DataClient
from ..classification.classifier import Classifier
from ..llm.client import LLMClient
from ..orchestration.streaming import run_workflow_stream

logger = logging.getLogger(__name__)


@click.command(name="query-llm")
@click.argument("question")
@click.option(
    "--provider",
    default="anthropic",
    type=click.Choice(["anthropic", "openai", "stub"]),
    help="LLM provider to use",
)
@click.option("--model", default=None, help="Model override (provider-specific)")
@click.option(
    "--no-stream",
    is_flag=True,
    default=False,
    help="Disable token streaming (wait for complete response)",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    default=False,
    help="Show stage transitions and metadata",
)
def query_llm(
    question: str, provider: str, model: str | None, no_stream: bool, verbose: bool
) -> None:
    """
    Query QNWIS using the LLM multi-agent workflow (streams by default).

    Executes the multi-stage council workflow:
    classify → prefetch → agents → verify → synthesize

    Examples:

        \b
        # Stream response with Anthropic Claude
        qnwis query-llm "What are Qatar's unemployment trends?"

        \b
        # Complete response (no streaming)
        qnwis query-llm "Analyze healthcare workforce" --no-stream

        \b
        # Use OpenAI with verbose output
        qnwis query-llm "Compare GCC labor markets" --provider openai -v

        \b
        # Test with stub provider (deterministic output)
        qnwis query-llm "Test query" --provider stub
    """
    asyncio.run(_run(question, provider, model, not no_stream, verbose))


async def _run(
    question: str, provider: str, model: str | None, stream: bool, verbose: bool
) -> None:
    """
    Execute the LLM workflow asynchronously.

    Args:
        question: User question to analyze
        provider: LLM provider (anthropic, openai, stub)
        model: Optional model override
        stream: Whether to stream tokens in real-time
        verbose: Show stage transitions and metadata
    """
    try:
        # Initialize clients
        data_client = DataClient()
        llm_client = LLMClient(provider=provider, model=model)
        classifier = Classifier()

        if verbose:
            click.echo(f"🔧 Provider: {provider}")
            click.echo(f"🤖 Model: {llm_client.model}")
            click.echo(f"📝 Question: {question}\n")

        synthesis_text = []

        # Execute workflow and process events
        async for event in run_workflow_stream(
            question=question,
            data_client=data_client,
            llm_client=llm_client,
            classifier=classifier,
        ):
            # Handle streaming tokens
            if stream and event.status == "streaming" and "token" in event.payload:
                click.echo(event.payload["token"], nl=False)

            # Handle stage transitions
            elif verbose and event.status == "running":
                click.echo(f"\n▶ {event.stage} ...", err=True)

            # Handle stage completion
            elif event.status == "complete":
                if verbose:
                    latency = event.latency_ms or 0
                    click.echo(f"\n✅ {event.stage} ({latency:.0f} ms)", err=True)

                # Capture synthesis for non-streaming mode
                if event.stage == "synthesize" and not stream:
                    synthesis = event.payload.get("synthesis", "")
                    synthesis_text.append(synthesis)

        # Print synthesis in non-streaming mode
        if not stream and synthesis_text:
            click.echo(synthesis_text[0])
        elif stream:
            # Add final newline after streaming output
            click.echo()

    except KeyboardInterrupt:
        click.echo("\n⏹ Interrupted by user", err=True)
        raise SystemExit(130)  # Standard Unix SIGINT exit code
    except Exception as e:
        logger.exception("query_llm failed")
        click.echo(f"\n❌ Error: {e}", err=True)
        raise SystemExit(1)


if __name__ == "__main__":
    query_llm()
