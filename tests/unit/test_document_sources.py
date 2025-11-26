"""
Unit tests for document sources configuration.

Validates that document source paths and counts are correctly specified.
"""

import pytest
from pathlib import Path
from qnwis.rag.document_sources import DOCUMENT_SOURCES, TOTAL_EXPECTED_DOCUMENTS


def test_document_sources_paths_exist():
    """Test that document source paths are valid Path objects."""
    for source_name, config in DOCUMENT_SOURCES.items():
        if config['type'] == 'filesystem':
            # Path should be a Path object
            assert isinstance(config['path'], Path), \
                f"{source_name}: path should be pathlib.Path"
            
            # Path should be specified (even if it doesn't exist yet)
            assert str(config['path']), \
                f"{source_name}: path should not be empty"
            
            # Pattern should be specified
            assert config['pattern'], \
                f"{source_name}: pattern should not be empty"
        
        elif config['type'] == 'database':
            # Database sources should have connection string and tables
            assert 'connection' in config, \
                f"{source_name}: database source must have 'connection'"
            assert 'tables' in config, \
                f"{source_name}: database source must have 'tables'"
            assert len(config['tables']) > 0, \
                f"{source_name}: tables list should not be empty"
        
        # All sources should have these fields
        assert 'expected_count' in config, \
            f"{source_name}: missing expected_count"
        assert 'update_frequency' in config, \
            f"{source_name}: missing update_frequency"
        assert 'priority' in config, \
            f"{source_name}: missing priority"
        assert config['priority'] in ['low', 'medium', 'high', 'critical'], \
            f"{source_name}: priority must be low/medium/high/critical"


def test_document_sources_counts_reasonable():
    """Test that document counts are reasonable and meet target."""
    # Total should be at least 70,000 documents
    assert TOTAL_EXPECTED_DOCUMENTS >= 70000, \
        f"Total documents ({TOTAL_EXPECTED_DOCUMENTS}) should be >= 70,000"
    
    # Each source should have reasonable count
    for source_name, config in DOCUMENT_SOURCES.items():
        expected = config['expected_count']
        
        # Count should be positive
        assert expected > 0, \
            f"{source_name}: expected_count must be positive"
        
        # Count should not be unreasonably large (< 1 million per source)
        assert expected < 1_000_000, \
            f"{source_name}: expected_count seems too large ({expected})"
    
    # Verify specific sources exist
    assert 'world_bank' in DOCUMENT_SOURCES, "world_bank source missing"
    assert 'gcc_stat' in DOCUMENT_SOURCES, "gcc_stat source missing"
    assert 'mol_lmis' in DOCUMENT_SOURCES, "mol_lmis source missing"
    assert 'imf_reports' in DOCUMENT_SOURCES, "imf_reports source missing"
    
    # Verify MOL_LMIS is marked as critical (largest source)
    assert DOCUMENT_SOURCES['mol_lmis']['priority'] == 'critical', \
        "MOL LMIS should be marked as critical priority"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

