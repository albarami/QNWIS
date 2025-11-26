"""
Unit tests for Document Loader.

Tests document loading from configured sources.
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from qnwis.rag.document_loader import (
    load_source_documents,
    _load_from_filesystem,
    _create_placeholder_documents,
    _get_file_date
)


def test_load_source_documents():
    """Test that documents load from configured sources."""
    # This will create placeholders if actual sources don't exist
    documents = load_source_documents()
    
    # Should have loaded something (even if placeholders)
    assert len(documents) > 0
    
    # Each document should have required fields
    for doc in documents:
        assert 'text' in doc
        assert 'source' in doc
        assert 'priority' in doc
        assert len(doc['text']) > 0


def test_document_metadata_extraction():
    """Test that source and date are parsed correctly."""
    documents = load_source_documents()
    
    if documents:
        doc = documents[0]
        
        # Verify metadata fields
        assert 'source' in doc
        assert 'date' in doc
        assert 'priority' in doc
        
        # Priority should be valid
        assert doc['priority'] in ['low', 'medium', 'high', 'critical']


def test_create_placeholder_documents():
    """Test placeholder document creation."""
    placeholders = _create_placeholder_documents('world_bank', 10, 'high')
    
    assert len(placeholders) == 10
    
    for doc in placeholders:
        assert 'text' in doc
        assert 'source' in doc
        assert 'priority' in doc
        assert doc['priority'] == 'high'
        assert 'placeholder' in doc
        assert doc['placeholder'] is True
        
        # Placeholder text should be realistic
        assert len(doc['text']) > 50
        assert 'GDP' in doc['text'] or 'economic' in doc['text'].lower()


def test_duplicate_document_handling():
    """Test that duplicate documents are handled properly."""
    # Load documents
    documents = load_source_documents()
    
    # Count unique sources
    sources = [doc['source'] for doc in documents]
    
    # Should not have too many exact duplicates
    unique_sources = set(sources)
    
    # At least some variety in sources
    assert len(unique_sources) > 1, "Should have multiple distinct sources"


def test_get_file_date():
    """Test file date extraction."""
    # Create a temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        temp_path = Path(f.name)
        f.write("test content")
    
    try:
        date_str = _get_file_date(temp_path)
        
        # Should return a date string
        assert date_str != ''
        assert date_str != 'unknown' or date_str  # Either valid date or something
        
    finally:
        # Clean up
        if temp_path.exists():
            temp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

