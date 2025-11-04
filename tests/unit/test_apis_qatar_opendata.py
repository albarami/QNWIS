"""Unit tests for Qatar Open Data Portal API client.

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
import pytest

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from data.apis.qatar_opendata import QatarOpenDataScraperV2, _client, _get_base_url


def test_base_url_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that base URL can be configured from environment."""
    test_url = "https://test.data.gov.qa/api/explore/v2.1"
    monkeypatch.setenv("QATAR_OPENDATA_BASE", test_url)

    url = _get_base_url()
    assert url == test_url.rstrip("/")


def test_base_url_default() -> None:
    """Test default URL is used when env var not set."""
    url = _get_base_url()
    assert "data.gov.qa" in url


def test_client_configuration() -> None:
    """Test HTTP client configuration."""
    client = _client(timeout=25.0)

    assert client.timeout.read == 25.0
    assert client.headers["User-Agent"] == "QNWIS-QatarOpenDataClient/1.0"
    assert client.headers["Accept"] == "application/json"

    client.close()


def test_scraper_initialization(tmp_path: Path) -> None:
    """Test scraper initializes with custom directory."""
    scraper = QatarOpenDataScraperV2(base_dir=tmp_path)

    assert scraper.base_dir == tmp_path
    assert (tmp_path / "raw" / "labor").exists()
    assert (tmp_path / "metadata").exists()


def test_test_api_connection_success() -> None:
    """Test successful API connection check."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"total_count": 1500}

    with patch("data.apis.qatar_opendata.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_instance.request.return_value = mock_response
        MockClient.return_value = mock_client_instance

        scraper = QatarOpenDataScraperV2()
        result = scraper.test_api_connection()

        assert result is True
        mock_response.raise_for_status.assert_called()
        ping_meta = scraper.last_request_metadata.get("ping")
        assert ping_meta is not None
        assert ping_meta["endpoint"] == "catalog/datasets"


def test_test_api_connection_failure() -> None:
    """Test API connection failure handling."""
    with patch("data.apis.qatar_opendata.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_instance.request.side_effect = httpx.ConnectError("Connection failed")
        MockClient.return_value = mock_client_instance

        scraper = QatarOpenDataScraperV2()
        result = scraper.test_api_connection()

        assert result is False


def test_get_all_datasets_with_limit() -> None:
    """Test get_all_datasets respects max_results limit."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "results": [
            {"dataset_id": "ds1", "metas": {}},
            {"dataset_id": "ds2", "metas": {}},
            {"dataset_id": "ds3", "metas": {}},
        ]
    }

    with patch("data.apis.qatar_opendata.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_instance.request.return_value = mock_response
        MockClient.return_value = mock_client_instance

        scraper = QatarOpenDataScraperV2()
        datasets = scraper.get_all_datasets(limit=100, max_results=2)

        assert len(datasets) == 2
        mock_response.raise_for_status.assert_called()
        catalog_meta = scraper.last_request_metadata.get("catalog")
        assert catalog_meta is not None
        assert catalog_meta["returned_records"] == 2


def test_download_dataset(tmp_path: Path) -> None:
    """Test dataset download creates file."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.content = b"col1,col2\nval1,val2"

    with patch("data.apis.qatar_opendata.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_instance.request.return_value = mock_response
        MockClient.return_value = mock_client_instance

        scraper = QatarOpenDataScraperV2(base_dir=tmp_path)
        filepath = scraper.download_dataset(
            dataset_id="test-dataset",
            format_type="csv",
            category="labor",
        )

        assert filepath is not None
        assert filepath.exists()
        assert filepath.read_bytes() == b"col1,col2\nval1,val2"
        mock_response.raise_for_status.assert_called()
        download_meta = scraper.last_request_metadata.get("download")
        assert download_meta is not None
        assert download_meta["dataset_id"] == "test-dataset"


def test_download_dataset_http_error() -> None:
    """Test download_dataset handles HTTP errors gracefully."""
    mock_response = Mock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not found", request=Mock(), response=mock_response
    )

    with patch("data.apis.qatar_opendata.httpx.Client") as MockClient:
        mock_client_instance = MagicMock()
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client_instance.request.return_value = mock_response
        MockClient.return_value = mock_client_instance

        scraper = QatarOpenDataScraperV2()
        filepath = scraper.download_dataset("nonexistent")

        assert filepath is None
        error_meta = scraper.last_request_metadata.get("download")
        assert error_meta is not None
        assert "error" in error_meta


def test_timeout_configuration() -> None:
    """Test that timeout can be configured."""
    client = _client(timeout=35.0)
    assert client.timeout.read == 35.0
    client.close()


def test_no_hardcoded_secrets() -> None:
    """Verify no hardcoded credentials in module."""
    import inspect

    from data.apis import qatar_opendata

    source = inspect.getsource(qatar_opendata)

    # Should use environment variables
    assert "os.getenv" in source or "os.environ" in source

    # Should not contain hardcoded tokens
    lines = source.split("\n")
    for line in lines:
        if ("=" in line and '"' in line and not line.strip().startswith("#") and
                ("API_KEY" in line.upper() or "TOKEN" in line.upper()) and
                "os.getenv" not in line and "example" not in line.lower()):
            pytest.fail(f"Potential hardcoded credential: {line.strip()[:50]}")
