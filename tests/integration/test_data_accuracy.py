"""
Integration tests for data accuracy across all sources.

Verifies:
- World Bank data is realistic (Qatar unemployment < 1%)
- RAG documents are properly embedded
- Knowledge graph has expected entities
- Data validation rules work correctly
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class TestWorldBankData:
    """Tests for World Bank data accuracy."""
    
    @pytest.fixture
    def db_engine(self):
        """Get database engine."""
        import os
        from sqlalchemy import create_engine
        
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://postgres:1234@localhost:5432/qnwis"
        )
        return create_engine(db_url)
    
    def test_qatar_unemployment_realistic(self, db_engine):
        """Qatar unemployment should be < 1% (historically 0.1-0.5%)."""
        from sqlalchemy import text
        
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT year, value FROM world_bank_indicators 
                WHERE indicator_code = 'SL.UEM.TOTL.ZS' 
                AND country_code = 'QAT'
                ORDER BY year DESC LIMIT 5
            """))
            rows = result.fetchall()
        
        assert len(rows) > 0, "No Qatar unemployment data found"
        
        for row in rows:
            assert row.value < 5.0, f"Qatar unemployment {row.value}% is unrealistic (year {row.year})"
            # Should ideally be < 1%
            if row.year >= 2015:
                assert row.value < 1.0, f"Recent Qatar unemployment {row.value}% seems too high"
    
    def test_all_gcc_countries_have_data(self, db_engine):
        """All 6 GCC countries should have data."""
        from sqlalchemy import text
        
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT country_code, COUNT(DISTINCT indicator_code) as indicators
                FROM world_bank_indicators
                GROUP BY country_code
            """))
            rows = {row.country_code: row.indicators for row in result.fetchall()}
        
        gcc_countries = ["QAT", "SAU", "ARE", "KWT", "BHR", "OMN"]
        
        for country in gcc_countries:
            assert country in rows, f"Missing data for {country}"
            assert rows[country] >= 10, f"{country} has only {rows[country]} indicators"
    
    def test_gdp_values_realistic(self, db_engine):
        """Qatar GDP per capita should be $50K-$100K (one of world's highest)."""
        from sqlalchemy import text
        
        with db_engine.connect() as conn:
            result = conn.execute(text("""
                SELECT year, value FROM world_bank_indicators 
                WHERE indicator_code = 'NY.GDP.PCAP.CD' 
                AND country_code = 'QAT'
                ORDER BY year DESC LIMIT 3
            """))
            rows = result.fetchall()
        
        for row in rows:
            if row.value:
                assert 30000 < row.value < 150000, \
                    f"Qatar GDP per capita ${row.value} seems unrealistic"


class TestDataValidation:
    """Tests for data validation rules."""
    
    def test_unemployment_validation_rejects_high_values(self):
        """Validation should reject Qatar unemployment > 5%."""
        from qnwis.data.validation.quality_rules import validate_data_point
        
        result = validate_data_point(
            value=56.0,  # Obviously wrong
            indicator_code="SL.UEM.TOTL.ZS",
            country_code="QAT"
        )
        
        assert not result.is_valid, "Should reject 56% unemployment"
        assert result.quality_flags.get("out_of_range"), "Should flag as out of range"
    
    def test_unemployment_validation_accepts_realistic_values(self):
        """Validation should accept Qatar unemployment 0.1-0.5%."""
        from qnwis.data.validation.quality_rules import validate_data_point
        
        result = validate_data_point(
            value=0.13,  # Realistic Qatar value
            indicator_code="SL.UEM.TOTL.ZS",
            country_code="QAT"
        )
        
        assert result.is_valid, "Should accept 0.13% unemployment"
        assert result.quality_score >= 0.8, f"Quality score {result.quality_score} too low"
    
    def test_gdp_validation_rules(self):
        """Validation should flag unrealistic GDP values."""
        from qnwis.data.validation.quality_rules import validate_data_point
        
        # Valid GDP per capita
        result = validate_data_point(
            value=80000,
            indicator_code="NY.GDP.PCAP.CD",
            country_code="QAT"
        )
        assert result.is_valid
        
        # Invalid GDP per capita (too high)
        result = validate_data_point(
            value=500000,
            indicator_code="NY.GDP.PCAP.CD",
            country_code="QAT"
        )
        assert not result.is_valid


class TestRAGDocuments:
    """Tests for RAG document store."""
    
    @pytest.fixture
    def document_store(self):
        """Get document store."""
        from qnwis.rag.retriever import get_document_store
        return get_document_store()
    
    def test_document_store_has_documents(self, document_store):
        """Document store should have documents loaded."""
        assert len(document_store.documents) > 0, "No documents in store"
    
    def test_document_search_returns_results(self, document_store):
        """Search should return relevant results."""
        results = document_store.search(
            "Qatar unemployment rate labor market",
            top_k=5,
            min_score=0.1
        )
        
        assert len(results) > 0, "No search results returned"
        
        # Check first result has reasonable score
        doc, score = results[0]
        assert score >= 0.1, f"Top result score {score} too low"


class TestKnowledgeGraph:
    """Tests for knowledge graph."""
    
    @pytest.fixture
    def knowledge_graph(self):
        """Load knowledge graph."""
        from qnwis.knowledge.graph_builder import QNWISKnowledgeGraph
        
        graph = QNWISKnowledgeGraph()
        graph_path = Path("data/knowledge_graph.json")
        
        if graph_path.exists():
            graph.load(graph_path)
        
        return graph
    
    def test_graph_has_qatar_entities(self, knowledge_graph):
        """Knowledge graph should have Qatar-related entities."""
        stats = knowledge_graph.get_stats()
        
        assert stats["total_nodes"] > 0, "Graph has no nodes"
        assert stats.get("entity_types", {}).get("sector", 0) > 0, "No sector entities"
        assert stats.get("entity_types", {}).get("policy", 0) > 0, "No policy entities"
    
    def test_graph_has_relationships(self, knowledge_graph):
        """Knowledge graph should have relationships."""
        stats = knowledge_graph.get_stats()
        
        assert stats["total_edges"] > 0, "Graph has no relationships"


class TestCrossDomainQuery:
    """Tests for cross-domain query capabilities."""
    
    def test_query_can_access_multiple_domains(self):
        """System should be able to access data across domains."""
        # This is a placeholder for more sophisticated testing
        # In production, this would test the full workflow
        
        domains_to_test = ["Labor", "Health", "Education", "Trade", "Energy"]
        
        # Verify data validation rules exist for each domain
        from qnwis.data.validation.quality_rules import VALIDATION_RULES
        
        found_domains = set()
        for rule_name, rule in VALIDATION_RULES.items():
            domain = rule.get("domain")
            if domain:
                found_domains.add(domain)
        
        for domain in domains_to_test:
            assert domain in found_domains, f"Missing validation rules for {domain} domain"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

