"""Unit tests for World Bank API client.

Verifies:
- Base URL configurable from environment
- Timeout handling
- raise_for_status() called
- No hardcoded secrets
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import httpx
import pandas as pd
import pytest

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from data.apis.world_bank import UDCGlobalDataIntegrator, _client, _get_base_url


def test_base_url_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that base URL can be configured from environment."""
    test_url = "https://test.worldbank.org/v2"
    monkeypatch.setenv("WORLD_BANK_BASE", test_url)

    url = _get_base_url()
    assert url == test_url.rstrip("/")


def test_base_url_default() -> None:
    """Test that default URL is used when env var not set."""
    url = _get_base_url()
    assert "worldbank.org" in url


def test_client_configuration() -> None:
    """Test HTTP client is configured with timeout."""
    client = _client(timeout=20.0)

    assert client.timeout.read == 20.0
    assert "User-Agent" in client.headers
    assert client.headers["User-Agent"] == "QNWIS-WorldBankClient/1.0"

    client.close()


def test_get_indicator_with_mocked_api(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test get_indicator with mocked World Bank API response."""
    # Mock API response
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {"page": 1, "total": 2},  # Metadata
        [  # Data
            {
                "date": "2023",
                "value": 180.5,
                "indicator": {"value": "GDP"},
                "country": {"value": "Qatar"},
            },
            {
                "date": "2022",
                "value": 175.2,
                "indicator": {"value": "GDP"},
                "country": {"value": "Qatar"},
            },
        ],
    ]

    with patch("data.apis.world_bank.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_instance.request.return_value = mock_response
        MockClient.return_value = mock_client_instance

        integrator = UDCGlobalDataIntegrator()
        df = integrator.get_indicator(
            indicator="NY.GDP.MKTP.CD",
            countries=["QAT"],
            year=2023,
        )

        # Verify raise_for_status was called
        mock_response.raise_for_status.assert_called()

        # Verify DataFrame structure
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "country" in df.columns
        assert "year" in df.columns
        assert "value" in df.columns
        assert df.attrs["request_metadata"]["endpoint"] == "world_bank_indicator"


def test_get_indicator_raises_on_http_error() -> None:
    """Test that HTTP errors are properly raised."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Server error", request=Mock(), response=mock_response
    )

    with patch("data.apis.world_bank.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_instance.request.return_value = mock_response
        MockClient.return_value = mock_client_instance

        integrator = UDCGlobalDataIntegrator()

        with pytest.raises(httpx.HTTPStatusError):
            integrator.get_indicator(
                indicator="NY.GDP.MKTP.CD",
                countries=["QAT"],
            )


def test_get_multiple_indicators() -> None:
    """Test get_multiple_indicators returns dict of DataFrames."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {},
        [
            {"date": "2023", "value": 100.0, "indicator": {"value": "Test"}},
        ],
    ]

    with patch("data.apis.world_bank.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_instance.request.return_value = mock_response
        MockClient.return_value = mock_client_instance

        integrator = UDCGlobalDataIntegrator()
        result = integrator.get_multiple_indicators(
            indicators=["NY.GDP.MKTP.CD", "NY.GDP.MKTP.KD.ZG"],
            countries=["QAT"],
        )

        assert isinstance(result, dict)
        assert len(result) == 2


def test_timeout_respected() -> None:
    """Test that timeout configuration is respected."""
    client = _client(timeout=15.0)
    assert client.timeout.read == 15.0
    client.close()


def test_no_hardcoded_secrets() -> None:
    """Verify no hardcoded API keys in module."""
    import inspect

    from data.apis import world_bank

    source = inspect.getsource(world_bank)

    # Should not have hardcoded URLs (should use env)
    assert "os.getenv" in source or "os.environ" in source

    # Should not contain any long secrets
    lines = source.split("\n")
    for line in lines:
        if "=" in line and '"' in line and not line.strip().startswith("#"):
            parts = line.split('"')
            for i in range(1, len(parts), 2):
                # Allow URLs but check for long alphanumeric strings that could be secrets
                if (len(parts[i]) > 30 and
                        parts[i].replace("_", "").replace("/", "").replace(".", "").isalnum() and
                        not parts[i].startswith("http")):
                    pytest.fail(f"Potential secret: {line.strip()[:50]}")
