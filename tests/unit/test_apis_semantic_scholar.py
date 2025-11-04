"""Unit tests for Semantic Scholar API client.

Verifies:
- API key loaded from environment
- No hardcoded secrets in module
- Timeout and error handling
- HTTP client configuration
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from data.apis import semantic_scholar


def test_api_key_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that API key is loaded from environment."""
    test_key = "test_semantic_scholar_key_12345"
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", test_key)

    key = semantic_scholar._get_api_key()
    assert key == test_key


def test_api_key_missing_raises_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that missing API key raises RuntimeError."""
    monkeypatch.delenv("SEMANTIC_SCHOLAR_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SEMANTIC_SCHOLAR_API_KEY"):
        semantic_scholar._get_api_key()


def test_client_configuration() -> None:
    """Test HTTP client is configured correctly."""
    client = semantic_scholar._client(timeout=10.0)

    assert client.timeout.read == 10.0
    assert "User-Agent" in client.headers
    assert client.headers["User-Agent"] == "QNWIS-SemanticScholarClient/1.0"
    assert client.headers["Accept"] == "application/json"

    client.close()


def test_search_papers_with_mocked_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test search_papers with mocked API response."""
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test_key_123")

    # Mock response
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {"paperId": "1", "title": "Labor Market Research", "year": 2023},
            {"paperId": "2", "title": "Employment Study", "year": 2022},
        ]
    }

    # Mock httpx.Client
    with patch("data.apis.semantic_scholar.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_instance.request.return_value = mock_response
        MockClient.return_value = mock_client_instance

        # Call function
        papers = semantic_scholar.search_papers(query="test", limit=5)

        # Verify
        assert isinstance(papers, list)
        assert len(papers) == 2
        assert papers[0]["title"] == "Labor Market Research"
        assert hasattr(papers, "metadata")
        assert papers.metadata["endpoint"] == "paper/search"

        # Verify API key was passed in header
        call_args, call_kwargs = mock_client_instance.request.call_args
        assert call_args[0] == "GET"
        assert "headers" in call_kwargs
        assert call_kwargs["headers"]["x-api-key"] == "test_key_123"


def test_search_papers_raises_on_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that HTTP errors are properly raised."""
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test_key_123")

    # Mock error response
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 429
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Too many requests", request=Mock(), response=mock_response
    )

    with patch("data.apis.semantic_scholar.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_instance.request.return_value = mock_response
        MockClient.return_value = mock_client_instance

        with pytest.raises(httpx.HTTPStatusError):
            semantic_scholar.search_papers(query="test")


def test_get_paper_recommendations(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_paper_recommendations with mocked API."""
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test_key_123")

    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "recommendedPapers": [
            {"paperId": "3", "title": "Recommended Paper", "year": 2023}
        ]
    }

    with patch("data.apis.semantic_scholar.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_instance.request.return_value = mock_response
        MockClient.return_value = mock_client_instance

        recommendations = semantic_scholar.get_paper_recommendations(
            positive_paper_ids=["1", "2"],
            limit=5,
        )

        assert len(recommendations) == 1
        assert recommendations[0]["title"] == "Recommended Paper"
        assert recommendations.metadata["seed_count"] == 2


def test_get_paper_by_id_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_paper_by_id returns None for 404."""
    monkeypatch.setenv("SEMANTIC_SCHOLAR_API_KEY", "test_key_123")

    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 404

    with patch("data.apis.semantic_scholar.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_instance.request.return_value = mock_response
        MockClient.return_value = mock_client_instance

        paper = semantic_scholar.get_paper_by_id("nonexistent_id")

        assert paper is None
        last_meta = semantic_scholar.get_last_request_metadata()["paper_by_id"]
        assert last_meta["status"] == 404


def test_no_hardcoded_secrets_in_module() -> None:
    """Verify no hardcoded API keys exist in the module."""
    import inspect

    source = inspect.getsource(semantic_scholar)

    # Should not contain any long alphanumeric strings that look like keys
    # (excluding variable names, URLs, and comments)
    lines = source.split("\n")
    for line in lines:
        # Skip comments and docstrings
        if line.strip().startswith("#") or '"""' in line:
            continue

        # Check for assignment patterns like API_KEY = "xyz123..."
        if "=" in line and '"' in line:
            # Extract string literals
            parts = line.split('"')
            for i in range(1, len(parts), 2):  # Odd indices are inside quotes
                potential_secret = parts[i]
                # Flag if it's a long alphanumeric string (likely a key)
                if len(potential_secret) > 30 and potential_secret.replace("_", "").isalnum():
                    pytest.fail(
                        f"Potential hardcoded secret found: {line.strip()[:50]}..."
                    )

    # Should require environment variable
    assert "os.getenv" in source or "os.environ" in source
    assert "SEMANTIC_SCHOLAR_API_KEY" in source


def test_timeout_is_configurable() -> None:
    """Test that timeout can be configured."""
    client = semantic_scholar._client(timeout=5.0)
    assert client.timeout.read == 5.0
    client.close()
