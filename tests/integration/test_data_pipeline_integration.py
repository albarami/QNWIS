"""
Data Pipeline Integration Tests.

Verifies that all data sources are properly integrated and accessible.
Tests that agents know about and can utilize all available data.
"""

import pytest
import asyncio
from typing import List, Dict


class TestDataSourceIntegration:
    """Test that all data sources are properly connected."""
    
    def test_prefetch_layer_has_all_connectors(self):
        """Verify prefetch layer initializes all connectors."""
        from src.qnwis.orchestration.prefetch_apis import CompletePrefetchLayer
        
        layer = CompletePrefetchLayer()
        
        # Tier 1 - Core APIs
        assert hasattr(layer, 'imf_connector'), "Missing IMF connector"
        assert hasattr(layer, 'world_bank_connector'), "Missing World Bank connector"
        
        # Tier 2 - Specialized APIs
        assert hasattr(layer, 'unctad_connector'), "Missing UNCTAD connector"
        assert hasattr(layer, 'ilo_connector'), "Missing ILO connector"
        assert hasattr(layer, 'fao_connector'), "Missing FAO connector"
        assert hasattr(layer, 'unwto_connector'), "Missing UNWTO connector"
        assert hasattr(layer, 'iea_connector'), "Missing IEA connector"
        
        # Tier 3 - Regional APIs
        assert hasattr(layer, 'adp_connector'), "Missing Arab Dev Portal connector"
        assert hasattr(layer, 'escwa_connector'), "Missing ESCWA connector"
        
        # Research APIs
        assert hasattr(layer, 'semantic_scholar'), "Missing Semantic Scholar"
        assert hasattr(layer, 'brave_api_key'), "Missing Brave API key attribute"
        assert hasattr(layer, 'perplexity_api_key'), "Missing Perplexity API key attribute"
        
        # Knowledge Graph
        assert hasattr(layer, '_knowledge_graph'), "Missing Knowledge Graph"
    
    def test_prefetch_layer_has_fetch_methods(self):
        """Verify prefetch layer has all required fetch methods."""
        from src.qnwis.orchestration.prefetch_apis import CompletePrefetchLayer
        
        layer = CompletePrefetchLayer()
        
        # Core fetch methods
        assert hasattr(layer, '_fetch_world_bank'), "Missing World Bank fetch"
        assert hasattr(layer, '_fetch_gcc_stat'), "Missing GCC-STAT fetch"
        assert hasattr(layer, '_fetch_imf'), "Missing IMF fetch"
        
        # Specialized fetch methods
        assert hasattr(layer, '_fetch_unctad_investment'), "Missing UNCTAD fetch"
        assert hasattr(layer, '_fetch_ilo_benchmarks'), "Missing ILO fetch"
        assert hasattr(layer, '_fetch_fao_food_security'), "Missing FAO fetch"
        assert hasattr(layer, '_fetch_unwto_tourism'), "Missing UNWTO fetch"
        assert hasattr(layer, '_fetch_iea_energy'), "Missing IEA fetch"
        
        # Regional fetch methods
        assert hasattr(layer, '_fetch_adp_data'), "Missing ADP fetch"
        assert hasattr(layer, '_fetch_escwa_trade'), "Missing ESCWA fetch"
        
        # Research fetch methods
        assert hasattr(layer, '_fetch_semantic_scholar_labor'), "Missing Semantic Scholar labor fetch"
        assert hasattr(layer, '_fetch_semantic_scholar_policy'), "Missing Semantic Scholar policy fetch"
        assert hasattr(layer, '_fetch_brave_economic'), "Missing Brave fetch"
        assert hasattr(layer, '_fetch_perplexity_gcc'), "Missing Perplexity GCC fetch"
        assert hasattr(layer, '_fetch_perplexity_policy'), "Missing Perplexity policy fetch"
        
        # Knowledge Graph fetch
        assert hasattr(layer, '_fetch_knowledge_graph_context'), "Missing Knowledge Graph fetch"


class TestAgentDataSourceAwareness:
    """Test that agents know about all available data sources."""
    
    def test_micro_economist_knows_data_sources(self):
        """Verify micro economist agent knows about all data sources."""
        from src.qnwis.agents.micro_economist import MicroEconomist
        
        prompt = MicroEconomist.SYSTEM_PROMPT
        
        # Check for Tier 1 sources
        assert "World Bank" in prompt
        assert "IMF" in prompt
        
        # Check for specialized sources (no longer marked as unavailable)
        assert "UNWTO" in prompt
        assert "FAO" in prompt
        assert "UNCTAD" in prompt
        assert "IEA" in prompt
        assert "ILO" in prompt
        
        # Check for research sources
        assert "Semantic Scholar" in prompt
        assert "Perplexity" in prompt
        assert "Brave" in prompt
        
        # Check for regional sources
        assert "Arab Development Portal" in prompt
        assert "ESCWA" in prompt
        
        # Check for knowledge resources
        assert "Knowledge Graph" in prompt
        assert "RAG" in prompt
        assert "PostgreSQL" in prompt
        
        # Verify no outdated "gap" messages
        assert "Cannot analyze tourism" not in prompt
        assert "Cannot assess domestic food production" not in prompt
        assert "Cannot analyze oil/gas production" not in prompt
    
    def test_macro_economist_knows_data_sources(self):
        """Verify macro economist agent knows about all data sources."""
        from src.qnwis.agents.macro_economist import MacroEconomist
        
        prompt = MacroEconomist.SYSTEM_PROMPT
        
        # Check for all tiers
        assert "TIER 1" in prompt
        assert "TIER 2" in prompt
        assert "TIER 3" in prompt
        assert "TIER 4" in prompt
        assert "TIER 5" in prompt
        
        # Verify sources are listed as ACTIVE
        assert "ALL 18 SOURCES ACTIVE" in prompt or "ALL ACTIVE" in prompt
        
        # Verify no outdated "gap" messages
        assert "Cannot assess economic diversification" not in prompt
        assert "Cannot evaluate tourism development" not in prompt
        assert "Cannot assess strategic food security" not in prompt


class TestKnowledgeGraphIntegration:
    """Test knowledge graph integration."""
    
    def test_knowledge_graph_can_load(self):
        """Verify knowledge graph can be loaded."""
        from pathlib import Path
        from src.qnwis.knowledge.graph_builder import QNWISKnowledgeGraph
        
        kg_path = Path("data/knowledge_graph.json")
        
        if kg_path.exists():
            kg = QNWISKnowledgeGraph()
            kg.load(kg_path)
            
            stats = kg.get_stats()
            assert stats["total_nodes"] > 0, "Knowledge graph has no nodes"
            assert stats["total_edges"] >= 0, "Knowledge graph edge count invalid"
    
    def test_knowledge_graph_entity_extraction(self):
        """Verify knowledge graph can extract entities from text."""
        from src.qnwis.knowledge.graph_builder import QNWISKnowledgeGraph
        
        kg = QNWISKnowledgeGraph()
        
        test_text = """
        The Energy sector in Qatar is implementing Vision 2030 goals.
        The Unemployment Rate has decreased due to Healthcare expansion.
        """
        
        entities = kg.extract_entities_from_text(test_text)
        
        assert len(entities) > 0, "No entities extracted"
        
        # Check expected entities
        entity_names = [e.lower() for e in entities]
        assert any("energy" in e for e in entity_names), "Energy sector not extracted"
        assert any("vision" in e or "2030" in e for e in entity_names), "Vision 2030 not extracted"


class TestAPIConnectors:
    """Test that API connectors are properly implemented."""
    
    def test_arab_dev_portal_connector_exists(self):
        """Verify Arab Dev Portal connector exists and has required methods."""
        from src.data.apis.arab_dev_portal import ArabDevPortalClient
        
        client = ArabDevPortalClient()
        
        assert hasattr(client, 'search_datasets'), "Missing search_datasets method"
        assert hasattr(client, 'get_country_indicators'), "Missing get_country_indicators method"
        assert hasattr(client, 'get_domain_data'), "Missing get_domain_data method"
        assert hasattr(client, 'get_available_domains'), "Missing get_available_domains method"
    
    def test_escwa_connector_exists(self):
        """Verify ESCWA connector exists and has required methods."""
        from src.data.apis.escwa_etdp import ESCWATradeAPI
        
        client = ESCWATradeAPI()
        
        assert hasattr(client, 'get_qatar_exports'), "Missing get_qatar_exports method"
        assert hasattr(client, 'get_qatar_imports'), "Missing get_qatar_imports method"
        assert hasattr(client, 'get_trade_balance'), "Missing get_trade_balance method"
        assert hasattr(client, 'get_strategic_commodities'), "Missing get_strategic_commodities method"
    
    def test_all_api_connectors_exist(self):
        """Verify all API connectors exist."""
        from src.data.apis import (
            world_bank_api,
            gcc_stat,
            arab_dev_portal,
            escwa_etdp,
            fao_api,
            ilo_api,
            unctad_api,
            unwto_api,
            iea_api,
            semantic_scholar,
        )
        
        # All modules should be importable
        assert world_bank_api is not None
        assert gcc_stat is not None
        assert arab_dev_portal is not None
        assert escwa_etdp is not None
        assert fao_api is not None
        assert ilo_api is not None
        assert unctad_api is not None
        assert unwto_api is not None
        assert iea_api is not None
        assert semantic_scholar is not None


class TestDomainAgnosticCapability:
    """Test that the system can handle queries across all domains."""
    
    def test_prefetch_triggers_for_all_domains(self):
        """Verify prefetch has triggers for all domains."""
        from src.qnwis.orchestration.prefetch_apis import CompletePrefetchLayer
        import inspect
        
        layer = CompletePrefetchLayer()
        fetch_method = layer.fetch_all_sources
        source_code = inspect.getsource(fetch_method)
        
        # Check for domain triggers
        domains = [
            "labor",
            "employment",
            "economic",
            "gdp",
            "trade",
            "export",
            "import",
            "energy",
            "oil",
            "gas",
            "tourism",
            "hotel",
            "food",
            "agriculture",
            "health",
            "education",
            "policy",
            "strategy",
        ]
        
        missing_domains = []
        for domain in domains:
            if domain.lower() not in source_code.lower():
                missing_domains.append(domain)
        
        assert len(missing_domains) == 0, f"Missing domain triggers: {missing_domains}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

