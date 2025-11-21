import asyncio

import pytest

from src.qnwis.verification.citation_enforcer import (
    verify_agent_output_with_retry,
    verify_citations_strict,
)


def test_verify_citations_strict_flags_missing():
    output = "The project will cost $10 billion without citing sources."
    report = verify_citations_strict(output, [])

    assert not report["passed"]
    assert report["violation_count"] >= 1
    assert any(v["type"] == "missing_citation" for v in report["violations"])


@pytest.mark.asyncio
async def test_verify_agent_output_with_retry_rejects():
    bad_output = "Approximately $5 billion in subsidies are planned."
    result = await verify_agent_output_with_retry(
        agent_name="TestAgent",
        agent_output=bad_output,
        extracted_facts=[],
        max_retries=2,
    )
    assert result["status"] == "rejected"
    assert result["attempts"] == 2
