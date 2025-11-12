"""Qatar Open Data Portal API Client for QNWIS.

PRODUCTION-READY: Uses environment variables for configuration.
Provides access to Qatar government open datasets via Opendatasoft API v2.1.
API Documentation: https://www.data.gov.qa/api/explore/v2.1/console/
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from ._http import send_with_retry

DEFAULT_TIMEOUT = 30.0
DEFAULT_BASE_URL = "https://www.data.gov.qa/api/explore/v2.1"
USER_AGENT = "QNWIS-QatarOpenDataClient/1.0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _get_base_url() -> str:
    """Get Qatar Open Data API base URL from environment or use default.

    Returns:
        Base URL string
    """
    return os.getenv("QATAR_OPENDATA_BASE", DEFAULT_BASE_URL).rstrip("/")


def _client(timeout: float = DEFAULT_TIMEOUT) -> httpx.Client:
    """Create HTTP client with standard configuration.

    Args:
        timeout: Request timeout in seconds

    Returns:
        Configured httpx.Client
    """
    return httpx.Client(
        timeout=timeout,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )


class QatarOpenDataScraperV2:
    """Qatar Open Data Portal API client using Opendatasoft Explore API v2.1.

    Production-ready client with environment-based configuration.
    """

    def __init__(self, base_dir: Path | None = None):
        """Initialize Qatar Open Data scraper.

        Args:
            base_dir: Base directory for downloaded data.
                     Defaults to current directory + 'qatar_data'
        """
        self.base_url = _get_base_url()
        self.base_dir = base_dir or Path("qatar_data")
        self._last_request_metadata: dict[str, Any] = {}

        # Create directory structure
        self.create_directory_structure()

        logger.info(f"QatarOpenDataScraperV2 initialized (API: {self.base_url})")

    def create_directory_structure(self):
        """Create the directory structure for organizing data."""
        directories = [
            'raw/real_estate',
            'raw/population',
            'raw/economy',
            'raw/tourism',
            'raw/labor',
            'raw/energy',
            'raw/infrastructure',
            'raw/other',
            'processed',
            'metadata'
        ]

        for directory in directories:
            (self.base_dir / directory).mkdir(parents=True, exist_ok=True)

    @property
    def last_request_metadata(self) -> dict[str, Any]:
        """Return metadata describing the most recent API operations."""
        return self._last_request_metadata

    def test_api_connection(self) -> bool:
        """Test connection to the API.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            logger.info("Testing connection to Qatar Open Data API v2.1...")
            with _client(timeout=10.0) as client:
                response, metadata = send_with_retry(
                    client,
                    "GET",
                    f"{self.base_url}/catalog/datasets",
                    timeout=client.timeout,
                    max_retries=3,
                )
                self._last_request_metadata["ping"] = {
                    "rate_limited": metadata.rate_limited,
                    "retries": metadata.retries,
                    "endpoint": "catalog/datasets",
                }
                data = response.json()
                total_count = data.get("total_count", 0)
                logger.info(
                    "API connection successful; catalog reports %s datasets",
                    total_count,
                )
                return True
        except Exception as exc:
            self._last_request_metadata["ping"] = {
                "error": str(exc),
                "endpoint": "catalog/datasets",
            }
            logger.error("API connection error: %s", exc)
            return False

    def get_all_datasets(self, limit: int = 100, max_results: int | None = None) -> list[dict[str, Any]]:
        """Retrieve datasets from the catalog.

        Args:
            limit: Maximum number of datasets to retrieve per request
            max_results: Maximum total results to return (None for all)

        Returns:
            List of dataset dictionaries

        Raises:
            ValueError: If input parameters are invalid.
            httpx.HTTPStatusError: If API request fails
        """
        if limit <= 0:
            raise ValueError("limit must be a positive integer")
        if max_results is not None and max_results <= 0:
            raise ValueError("max_results must be a positive integer when provided")

        all_datasets: list[dict[str, Any]] = []
        offset = 0
        rate_limited = False
        max_retries_used = 0

        with _client() as client:
            while True:
                logger.info("Fetching datasets: offset=%s, limit=%s", offset, limit)
                params = {"limit": limit, "offset": offset}
                response, metadata = send_with_retry(
                    client,
                    "GET",
                    f"{self.base_url}/catalog/datasets",
                    params=params,
                    timeout=client.timeout,
                    max_retries=3,
                )
                rate_limited = rate_limited or metadata.rate_limited
                max_retries_used = max(max_retries_used, metadata.retries)

                data = response.json()
                datasets = data.get("results", [])

                if not datasets:
                    break

                all_datasets.extend(datasets)
                logger.info(
                    "Retrieved %s datasets (running total: %s)",
                    len(datasets),
                    len(all_datasets),
                )

                if max_results is not None and len(all_datasets) >= max_results:
                    all_datasets = all_datasets[:max_results]
                    break

                if len(datasets) < limit:
                    break

                offset += limit
                time.sleep(0.5)  # Be respectful to the API

        self._last_request_metadata["catalog"] = {
            "rate_limited": rate_limited,
            "max_retries_used": max_retries_used,
            "requested_limit": limit,
            "requested_max_results": max_results,
            "returned_records": len(all_datasets),
        }
        if rate_limited:
            logger.warning(
                "Received HTTP 429 from catalog/datasets; results may be incomplete."
            )
        logger.info("Total datasets retrieved: %s", len(all_datasets))
        return all_datasets

    def categorize_datasets(self, datasets: list[dict[str, Any]]) -> dict[str, list[dict]]:
        """
        Categorize datasets by relevance to UDC business needs.

        Args:
            datasets: List of dataset dictionaries

        Returns:
            Dictionary with categories as keys and dataset lists as values
        """
        categories = {
            'real_estate': [],
            'population': [],
            'economy': [],
            'tourism': [],
            'labor': [],
            'energy': [],
            'infrastructure': [],
            'other': []
        }

        # Keywords for categorization
        category_keywords = {
            'real_estate': ['real estate', 'property', 'housing', 'land', 'building', 'construction', 'permit'],
            'population': ['population', 'demographic', 'census', 'resident', 'nationality', 'age', 'household'],
            'economy': ['gdp', 'economic', 'inflation', 'trade', 'export', 'import', 'financial', 'revenue'],
            'tourism': ['tourism', 'tourist', 'hotel', 'visitor', 'hospitality', 'travel'],
            'labor': ['labor', 'employment', 'workforce', 'job', 'salary', 'wage', 'unemployment'],
            'energy': ['energy', 'electricity', 'power', 'consumption', 'utility', 'cooling'],
            'infrastructure': ['infrastructure', 'transport', 'road', 'development', 'project', 'government']
        }

        for dataset in datasets:
            dataset_title = dataset.get('dataset_id', '').lower()
            dataset_description = dataset.get('metas', {}).get('default', {}).get('description', '').lower()
            combined_text = f"{dataset_title} {dataset_description}"

            categorized = False

            # Check each category
            for category, keywords in category_keywords.items():
                if any(keyword in combined_text for keyword in keywords):
                    categories[category].append(dataset)
                    categorized = True
                    break

            if not categorized:
                categories['other'].append(dataset)

        # Log categorization results
        for category, dataset_list in categories.items():
            logging.info(f"{category.title()}: {len(dataset_list)} datasets")

        return categories

    def download_dataset(
        self, dataset_id: str, format_type: str = "csv", category: str = "other"
    ) -> Path | None:
        """Download a dataset in the specified format.

        Args:
            dataset_id: Dataset identifier
            format_type: Export format (csv, json, etc.)
            category: Category subdirectory for organization

        Returns:
            Path to downloaded file or None if failed

        Raises:
            ValueError: If input parameters are invalid.
            httpx.HTTPStatusError: If API request fails
        """
        if not dataset_id.strip():
            raise ValueError("dataset_id must be a non-empty string")
        if not format_type.strip():
            raise ValueError("format_type must be a non-empty string")

        try:
            logger.info("Downloading dataset %s as %s", dataset_id, format_type)
            export_url = f"{self.base_url}/catalog/datasets/{dataset_id}/exports/{format_type}"

            with _client(timeout=60.0) as client:
                response, metadata = send_with_retry(
                    client,
                    "GET",
                    export_url,
                    timeout=client.timeout,
                    max_retries=3,
                )
                filename = f"{dataset_id}.{format_type}"
                filepath = self.base_dir / "raw" / category / filename
                filepath.parent.mkdir(parents=True, exist_ok=True)
                filepath.write_bytes(response.content)

            self._last_request_metadata["download"] = {
                "dataset_id": dataset_id,
                "format": format_type,
                "rate_limited": metadata.rate_limited,
                "retries": metadata.retries,
            }
            if metadata.rate_limited:
                logger.warning("Rate limit encountered while downloading %s", dataset_id)
            logger.info("Downloaded dataset to %s", filepath)
            return filepath
        except Exception as exc:
            self._last_request_metadata["download"] = {
                "dataset_id": dataset_id,
                "format": format_type,
                "error": str(exc),
            }
            logger.error("Error downloading %s: %s", dataset_id, exc)
            return None

    def generate_catalog_report(self, datasets: list[dict[str, Any]], categories: dict[str, list[dict]]):
        """Generate a comprehensive catalog report."""

        report = {
            'generated_at': datetime.now().isoformat(),
            'api_version': 'v2.1',
            'total_datasets': len(datasets),
            'categories': {},
            'top_datasets_by_category': {}
        }

        # Category summaries
        for category, dataset_list in categories.items():
            report['categories'][category] = {
                'count': len(dataset_list),
                'datasets': []
            }

            # Add dataset summaries
            for dataset in dataset_list[:5]:  # Top 5 per category
                dataset_info = {
                    'id': dataset.get('dataset_id'),
                    'title': dataset.get('metas', {}).get('default', {}).get('title', 'Unknown'),
                    'description': dataset.get('metas', {}).get('default', {}).get('description', '')[:200] + '...',
                    'modified': dataset.get('metas', {}).get('default', {}).get('modified', ''),
                    'records_count': dataset.get('metas', {}).get('default', {}).get('records_count', 0)
                }
                report['categories'][category]['datasets'].append(dataset_info)

        # Save report
        report_path = self.base_dir / 'metadata' / 'catalog_report_v2.json'
        with report_path.open('w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        logging.info(f"📊 Catalog report saved: {report_path}")
        return report_path

    def run_quick_test(self):
        """Run a quick test of the API functionality."""
        print("="*80)
        print("QATAR OPEN DATA PORTAL - API V2.1 QUICK TEST")
        print("="*80)

        # Test connection
        if not self.test_api_connection():
            print("❌ API connection failed. Check internet connection and API status.")
            return False

        # Get first 10 datasets for testing
        print("\n🔍 Fetching sample datasets...")
        datasets = self.get_all_datasets(limit=10)

        if not datasets:
            print("❌ No datasets retrieved")
            return False

        print(f"✅ Retrieved {len(datasets)} sample datasets")

        # Categorize datasets
        print("\n📊 Categorizing datasets...")
        categories = self.categorize_datasets(datasets)

        # Show results
        print("\nDataset Categories:")
        for category, dataset_list in categories.items():
            if dataset_list:
                print(f"  • {category.title()}: {len(dataset_list)} datasets")
                for i, dataset in enumerate(dataset_list[:2], 1):  # Show first 2
                    title = dataset.get('metas', {}).get('default', {}).get('title', 'Unknown')
                    print(f"    {i}. {title}")

        # Generate report
        print("\n📋 Generating catalog report...")
        report_path = self.generate_catalog_report(datasets, categories)

        print("\n✅ Quick test completed successfully!")
        print(f"📄 Report saved: {report_path}")
        return True


def main():
    """Main execution function."""
    scraper = QatarOpenDataScraperV2()

    print("Qatar Open Data Portal Scraper v2.1")
    print("====================================")
    print("1. Quick API test (10 datasets)")
    print("2. Full catalog download")
    print("3. Download specific datasets")

    choice = input("\nSelect option (1-3): ").strip()

    if choice == '1':
        scraper.run_quick_test()
    elif choice == '2':
        print("Full catalog download not implemented yet")
        print("Use option 1 to test API connectivity first")
    elif choice == '3':
        print("Specific dataset download not implemented yet")
        print("Use option 1 to see available datasets first")
    else:
        print("Invalid choice. Running quick test...")
        scraper.run_quick_test()


if __name__ == "__main__":
    main()
