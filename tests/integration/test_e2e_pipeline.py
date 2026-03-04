"""End-to-end pipeline integration test.

Sends a real question through the full NCIS pipeline via SSE and validates
that every stage completes successfully with real data. No mocks.

Requires: running server at localhost:8000 with valid .env
"""

import json
import os

import httpx
import pytest
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("QNWIS_TEST_BASE_URL", "http://localhost:8000")
TIMEOUT = httpx.Timeout(connect=10, read=1800, write=30, pool=30)


def _server_reachable() -> bool:
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=5)
        return r.status_code in (200, 503)
    except Exception:
        return False


needs_server = pytest.mark.skipif(
    not _server_reachable(),
    reason="NCIS server not running at localhost:8000",
)


def _stream_council(question: str, depth: str = "standard") -> dict:
    """Send a question via SSE and collect all events."""
    payload = {"question": question, "provider": "azure", "debate_depth": depth}
    events = []
    stages = set()

    with httpx.Client(timeout=TIMEOUT) as client:
        with client.stream(
            "POST",
            f"{BASE_URL}/api/v1/council/stream",
            json=payload,
            headers={"Content-Type": "application/json"},
        ) as response:
            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}"
            )
            buffer = ""
            for chunk in response.iter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    event_text, buffer = buffer.split("\n\n", 1)
                    for line in event_text.strip().split("\n"):
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                            except json.JSONDecodeError:
                                continue
                            events.append(data)
                            stages.add(data.get("stage", ""))
                            if data.get("stage") == "done" and data.get("status") == "complete":
                                break

    return {"events": events, "stages": stages}


@needs_server
class TestE2EPipeline:
    """Full pipeline E2E tests with real infrastructure."""

    def test_health_endpoint(self):
        r = httpx.get(f"{BASE_URL}/health", timeout=10)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "healthy"

    def test_diagnostic_question_completes(self):
        """A diagnostic question should traverse the full pipeline."""
        result = _stream_council(
            "What is the current Qatarization rate in the private sector?",
            depth="standard",
        )

        assert "classify" in result["stages"]
        assert "done" in result["stages"]
        assert len(result["events"]) > 5

        done_events = [e for e in result["events"] if e.get("stage") == "done"]
        assert len(done_events) > 0

        final = done_events[-1].get("data", {})
        if isinstance(final, dict):
            synthesis = final.get("synthesis", final.get("final_synthesis", ""))
            assert synthesis or any(
                e.get("stage") == "synthesize" for e in result["events"]
            ), "No synthesis output found"

    def test_pipeline_stages_are_ordered(self):
        """Verify that key pipeline stages appear in correct order."""
        result = _stream_council(
            "What are the biggest labor market challenges in Qatar?",
            depth="standard",
        )

        stage_sequence = [e.get("stage") for e in result["events"]]
        expected_order = ["classify", "research_fetch", "prefetch"]

        seen = []
        for expected in expected_order:
            if expected in stage_sequence:
                idx = stage_sequence.index(expected)
                seen.append((expected, idx))

        for i in range(1, len(seen)):
            assert seen[i][1] > seen[i - 1][1], (
                f"Stage {seen[i][0]} appeared before {seen[i-1][0]}"
            )

    def test_no_errors_in_pipeline(self):
        """Pipeline should complete with zero error events."""
        result = _stream_council(
            "How does Qatar's unemployment rate compare to the GCC average?",
            depth="standard",
        )

        error_events = [
            e for e in result["events"]
            if e.get("status") == "error"
        ]
        assert len(error_events) == 0, (
            f"Pipeline had {len(error_events)} error events: "
            + str([e.get("stage") for e in error_events])
        )
