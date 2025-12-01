"""
Document source configuration for fact verification.

Specifies all document sources for GPU-accelerated RAG verification.
Target: 70,000+ documents for comprehensive fact checking.
"""

from pathlib import Path
from typing import Dict, Any

# Document source configuration
DOCUMENT_SOURCES: Dict[str, Dict[str, Any]] = {
    'world_bank': {
        'type': 'filesystem',
        'path': Path('data/external_data/world_bank_reports/'),
        'pattern': '*.pdf',
        'expected_count': 5000,
        'update_frequency': 'monthly',
        'priority': 'high',
        'description': 'World Bank economic reports and country data'
    },
    'gcc_stat': {
        'type': 'filesystem',
        'path': Path('data/external_data/gcc_stat/'),
        'pattern': '*.csv',
        'expected_count': 15000,
        'update_frequency': 'weekly',
        'priority': 'high',
        'description': 'GCC Statistical Center regional data'
    },
    'mol_lmis': {
        'type': 'database',
        'connection': 'postgresql://localhost/qnwis',  # Will be overridden by env
        'tables': ['labor_force', 'employment', 'qatarization'],
        'expected_count': 50000,
        'update_frequency': 'daily',
        'priority': 'critical',
        'description': 'Ministry of Labour Labour Market Information System'
    },
    'imf_reports': {
        'type': 'filesystem',
        'path': Path('data/external_data/imf/'),
        'pattern': '*.pdf',
        'expected_count': 500,
        'update_frequency': 'quarterly',
        'priority': 'medium',
        'description': 'IMF Article IV consultations and reports'
    },
    'rnd_reports': {
        'type': 'filesystem',
        'path': Path('R&D team summaries and reports/'),
        'pattern': '*.pdf',
        'expected_count': 60,
        'update_frequency': 'monthly',
        'priority': 'critical',
        'description': 'R&D team research reports - Qatar labor market, AI, skills, WEF'
    }
}

# Total expected documents
TOTAL_EXPECTED_DOCUMENTS = sum(
    source['expected_count'] 
    for source in DOCUMENT_SOURCES.values()
)

# Validation
assert TOTAL_EXPECTED_DOCUMENTS >= 70000, \
    f"Expected at least 70,000 documents, configured for {TOTAL_EXPECTED_DOCUMENTS}"

