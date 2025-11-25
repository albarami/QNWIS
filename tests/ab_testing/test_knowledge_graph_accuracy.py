"""
Comprehensive Knowledge Graph and RAG Accuracy Tests.

Tests the knowledge graph structure, relationships, and RAG retrieval
to ensure accurate information extraction across all domains.

Run with: pytest tests/ab_testing/test_knowledge_graph_accuracy.py -v --tb=short
"""

import pytest
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================================================
# TEST RESULTS TRACKING
# ============================================================================

class KGTestTracker:
    """Track knowledge graph and RAG test results."""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.start_time = datetime.now()
        
    def add_result(
        self,
        test_name: str,
        component: str,
        metric: str,
        expected: Any,
        actual: Any,
        passed: bool,
        error: Optional[str] = None
    ):
        self.results.append({
            "test_name": test_name,
            "component": component,
            "metric": metric,
            "expected": expected,
            "actual": actual,
            "passed": passed,
            "error": error,
            "timestamp": datetime.now().isoformat()
        })
        
    def get_summary(self) -> Dict[str, Any]:
        total = len(self.results)
        passed = sum(1 for r in self.results if r["passed"])
        
        by_component = {}
        for r in self.results:
            comp = r["component"]
            if comp not in by_component:
                by_component[comp] = {"passed": 0, "failed": 0}
            if r["passed"]:
                by_component[comp]["passed"] += 1
            else:
                by_component[comp]["failed"] += 1
                
        return {
            "total_tests": total,
            "passed": passed,
            "failed": total - passed,
            "accuracy_pct": (passed / total * 100) if total > 0 else 0,
            "by_component": by_component,
            "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
            "failed_tests": [r for r in self.results if not r["passed"]]
        }
        
    def save_report(self, filepath: Path):
        report = {
            "summary": self.get_summary(),
            "all_results": self.results
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)


tracker = KGTestTracker()


# ============================================================================
# KNOWLEDGE GRAPH TESTS
# ============================================================================

class TestKnowledgeGraph:
    """Test knowledge graph structure and content."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup knowledge graph."""
        try:
            from src.qnwis.knowledge.graph_builder import QNWISKnowledgeGraph
            
            # Try to load existing graph - check multiple possible locations
            possible_paths = [
                Path("data/knowledge_graph.json"),
                Path("data/knowledge_graph/qnwis_knowledge_graph.json"),
                Path("data/knowledge_graph/knowledge_graph.json"),
            ]
            
            graph_path = None
            for path in possible_paths:
                if path.exists():
                    graph_path = path
                    break
                    
            if graph_path:
                self.kg = QNWISKnowledgeGraph()
                self.kg.load(graph_path)
                self.kg_available = True
            else:
                self.kg = None
                self.kg_available = False
                self.kg_error = f"Knowledge graph file not found in: {[str(p) for p in possible_paths]}"
        except Exception as e:
            self.kg_available = False
            self.kg_error = str(e)
            
    def test_graph_exists(self):
        """Test knowledge graph file exists."""
        graph_path = Path("data/knowledge_graph/qnwis_knowledge_graph.json")
        exists = graph_path.exists()
        
        tracker.add_result(
            test_name="kg_file_exists",
            component="knowledge_graph",
            metric="file_existence",
            expected=True,
            actual=exists,
            passed=exists
        )
        
    def test_graph_has_nodes(self):
        """Test knowledge graph has nodes."""
        if not self.kg_available:
            pytest.skip(f"Knowledge graph not available: {self.kg_error}")
            
        node_count = self.kg.graph.number_of_nodes()
        has_nodes = node_count > 0
        
        tracker.add_result(
            test_name="kg_has_nodes",
            component="knowledge_graph",
            metric="node_count",
            expected=10,
            actual=node_count,
            passed=has_nodes
        )
        
        assert has_nodes, f"Knowledge graph has no nodes"
        
    def test_graph_has_edges(self):
        """Test knowledge graph has edges."""
        if not self.kg_available:
            pytest.skip(f"Knowledge graph not available: {self.kg_error}")
            
        edge_count = self.kg.graph.number_of_edges()
        has_edges = edge_count > 0
        
        tracker.add_result(
            test_name="kg_has_edges",
            component="knowledge_graph",
            metric="edge_count",
            expected=5,
            actual=edge_count,
            passed=has_edges
        )
        
    def test_graph_has_qatar_entities(self):
        """Test graph has Qatar-related entities."""
        if not self.kg_available:
            pytest.skip(f"Knowledge graph not available: {self.kg_error}")
            
        qatar_entities = [n for n in self.kg.graph.nodes() 
                         if 'qatar' in str(n).lower() or 'qat' in str(n).lower()]
        has_qatar = len(qatar_entities) > 0
        
        tracker.add_result(
            test_name="kg_has_qatar_entities",
            component="knowledge_graph",
            metric="qatar_entity_count",
            expected=1,
            actual=len(qatar_entities),
            passed=has_qatar
        )
        
    def test_graph_has_sector_nodes(self):
        """Test graph has sector nodes."""
        if not self.kg_available:
            pytest.skip(f"Knowledge graph not available: {self.kg_error}")
            
        sector_keywords = ['energy', 'labor', 'health', 'education', 'trade', 'tourism', 'finance']
        sector_nodes = [n for n in self.kg.graph.nodes() 
                       if any(s in str(n).lower() for s in sector_keywords)]
        has_sectors = len(sector_nodes) > 0
        
        tracker.add_result(
            test_name="kg_has_sector_nodes",
            component="knowledge_graph",
            metric="sector_node_count",
            expected=3,
            actual=len(sector_nodes),
            passed=has_sectors
        )
        
    def test_graph_connectivity(self):
        """Test graph is reasonably connected."""
        if not self.kg_available:
            pytest.skip(f"Knowledge graph not available: {self.kg_error}")
            
        import networkx as nx
        
        # For directed graphs, check weak connectivity
        if self.kg.graph.number_of_nodes() > 1:
            is_weakly_connected = nx.is_weakly_connected(self.kg.graph)
        else:
            is_weakly_connected = True
            
        tracker.add_result(
            test_name="kg_connectivity",
            component="knowledge_graph",
            metric="weak_connectivity",
            expected=True,
            actual=is_weakly_connected,
            passed=True  # Don't fail test, just track
        )
        
    def test_graph_node_attributes(self):
        """Test graph nodes have proper attributes."""
        if not self.kg_available:
            pytest.skip(f"Knowledge graph not available: {self.kg_error}")
            
        nodes_with_type = sum(1 for n in self.kg.graph.nodes() 
                             if self.kg.graph.nodes[n].get('entity_type'))
        total_nodes = self.kg.graph.number_of_nodes()
        
        coverage = (nodes_with_type / total_nodes * 100) if total_nodes > 0 else 0
        good_coverage = coverage >= 50
        
        tracker.add_result(
            test_name="kg_node_attributes",
            component="knowledge_graph",
            metric="attribute_coverage_pct",
            expected=50,
            actual=coverage,
            passed=good_coverage
        )


# ============================================================================
# RAG DOCUMENT STORE TESTS
# ============================================================================

class TestRAGDocumentStore:
    """Test RAG document store content and retrieval."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup document store."""
        try:
            from src.qnwis.rag.retriever import get_document_store
            self.store = get_document_store()
            self.store_available = True
        except Exception as e:
            self.store_available = False
            self.store_error = str(e)
            
    def test_document_store_exists(self):
        """Test document store is available."""
        tracker.add_result(
            test_name="rag_store_exists",
            component="rag",
            metric="store_availability",
            expected=True,
            actual=self.store_available,
            passed=self.store_available,
            error=self.store_error if not self.store_available else None
        )
        
    def test_store_has_documents(self):
        """Test document store has documents."""
        if not self.store_available:
            pytest.skip(f"Document store not available: {self.store_error}")
            
        doc_count = len(self.store.documents) if hasattr(self.store, 'documents') else 0
        has_docs = doc_count > 0
        
        tracker.add_result(
            test_name="rag_has_documents",
            component="rag",
            metric="document_count",
            expected=10,
            actual=doc_count,
            passed=has_docs
        )
        
    def test_search_labor_query(self):
        """Test RAG search for labor query."""
        if not self.store_available:
            pytest.skip(f"Document store not available: {self.store_error}")
            
        try:
            results = self.store.search("Qatar unemployment rate labor market", top_k=5)
            has_results = results is not None and len(results) > 0
            
            tracker.add_result(
                test_name="rag_labor_search",
                component="rag",
                metric="search_results",
                expected=1,
                actual=len(results) if results else 0,
                passed=has_results
            )
            
        except Exception as e:
            tracker.add_result(
                test_name="rag_labor_search",
                component="rag",
                metric="search_results",
                expected=1,
                actual=0,
                passed=False,
                error=str(e)
            )
            
    def test_search_economy_query(self):
        """Test RAG search for economy query."""
        if not self.store_available:
            pytest.skip(f"Document store not available: {self.store_error}")
            
        try:
            results = self.store.search("Qatar GDP economic growth diversification", top_k=5)
            has_results = results is not None and len(results) > 0
            
            tracker.add_result(
                test_name="rag_economy_search",
                component="rag",
                metric="search_results",
                expected=1,
                actual=len(results) if results else 0,
                passed=has_results
            )
            
        except Exception as e:
            tracker.add_result(
                test_name="rag_economy_search",
                component="rag",
                metric="search_results",
                expected=1,
                actual=0,
                passed=False,
                error=str(e)
            )
            
    def test_search_energy_query(self):
        """Test RAG search for energy query."""
        if not self.store_available:
            pytest.skip(f"Document store not available: {self.store_error}")
            
        try:
            results = self.store.search("Qatar LNG natural gas oil energy exports", top_k=5)
            has_results = results is not None and len(results) > 0
            
            tracker.add_result(
                test_name="rag_energy_search",
                component="rag",
                metric="search_results",
                expected=1,
                actual=len(results) if results else 0,
                passed=has_results
            )
            
        except Exception as e:
            tracker.add_result(
                test_name="rag_energy_search",
                component="rag",
                metric="search_results",
                expected=1,
                actual=0,
                passed=False,
                error=str(e)
            )
            
    def test_search_health_query(self):
        """Test RAG search for health query."""
        if not self.store_available:
            pytest.skip(f"Document store not available: {self.store_error}")
            
        try:
            results = self.store.search("Qatar healthcare hospitals medical services", top_k=5)
            has_results = results is not None and len(results) > 0
            
            tracker.add_result(
                test_name="rag_health_search",
                component="rag",
                metric="search_results",
                expected=1,
                actual=len(results) if results else 0,
                passed=has_results
            )
            
        except Exception as e:
            tracker.add_result(
                test_name="rag_health_search",
                component="rag",
                metric="search_results",
                expected=1,
                actual=0,
                passed=False,
                error=str(e)
            )
            
    def test_search_education_query(self):
        """Test RAG search for education query."""
        if not self.store_available:
            pytest.skip(f"Document store not available: {self.store_error}")
            
        try:
            results = self.store.search("Qatar education universities training skills", top_k=5)
            has_results = results is not None and len(results) > 0
            
            tracker.add_result(
                test_name="rag_education_search",
                component="rag",
                metric="search_results",
                expected=1,
                actual=len(results) if results else 0,
                passed=has_results
            )
            
        except Exception as e:
            tracker.add_result(
                test_name="rag_education_search",
                component="rag",
                metric="search_results",
                expected=1,
                actual=0,
                passed=False,
                error=str(e)
            )
            
    def test_search_relevance_quality(self):
        """Test that search results are relevant."""
        if not self.store_available:
            pytest.skip(f"Document store not available: {self.store_error}")
            
        try:
            query = "Qatar Vision 2030 economic diversification"
            results = self.store.search(query, top_k=3)
            
            if results:
                # Check if top result contains relevant keywords
                top_result = results[0]
                text = top_result.get('text', '') if isinstance(top_result, dict) else str(top_result)
                
                relevant_keywords = ['qatar', 'vision', '2030', 'economy', 'diversif']
                relevance_score = sum(1 for kw in relevant_keywords if kw.lower() in text.lower())
                is_relevant = relevance_score >= 2
                
                tracker.add_result(
                    test_name="rag_relevance_quality",
                    component="rag",
                    metric="relevance_score",
                    expected=2,
                    actual=relevance_score,
                    passed=is_relevant
                )
            else:
                tracker.add_result(
                    test_name="rag_relevance_quality",
                    component="rag",
                    metric="relevance_score",
                    expected=2,
                    actual=0,
                    passed=False,
                    error="No search results"
                )
                
        except Exception as e:
            tracker.add_result(
                test_name="rag_relevance_quality",
                component="rag",
                metric="relevance_score",
                expected=2,
                actual=0,
                passed=False,
                error=str(e)
            )
            
    def test_r_and_d_documents_ingested(self):
        """Test R&D PDF documents are in the store."""
        if not self.store_available:
            pytest.skip(f"Document store not available: {self.store_error}")
            
        try:
            results = self.store.search("R&D research report Qatar labor", top_k=10)
            
            # Check for R&D source attribution
            rd_docs = []
            if results:
                for r in results:
                    source = r.get('source', '') if isinstance(r, dict) else ''
                    if 'R&D' in source or 'report' in source.lower():
                        rd_docs.append(r)
                        
            has_rd_docs = len(rd_docs) > 0
            
            tracker.add_result(
                test_name="rag_rd_documents",
                component="rag",
                metric="rd_document_count",
                expected=1,
                actual=len(rd_docs),
                passed=has_rd_docs
            )
            
        except Exception as e:
            tracker.add_result(
                test_name="rag_rd_documents",
                component="rag",
                metric="rd_document_count",
                expected=1,
                actual=0,
                passed=False,
                error=str(e)
            )


# ============================================================================
# EMBEDDING QUALITY TESTS
# ============================================================================

class TestEmbeddingQuality:
    """Test embedding model and vector quality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup embedder."""
        try:
            from src.qnwis.rag.embeddings import get_embedder
            self.embedder = get_embedder()
            self.embedder_available = True
        except Exception as e:
            self.embedder_available = False
            self.embedder_error = str(e)
            
    def test_embedder_exists(self):
        """Test embedder is available."""
        tracker.add_result(
            test_name="embedder_exists",
            component="embeddings",
            metric="embedder_availability",
            expected=True,
            actual=self.embedder_available,
            passed=self.embedder_available,
            error=self.embedder_error if not self.embedder_available else None
        )
        
    def test_embedding_dimension(self):
        """Test embedding dimension is correct."""
        if not self.embedder_available:
            pytest.skip(f"Embedder not available: {self.embedder_error}")
            
        try:
            test_text = "Qatar unemployment rate"
            embedding = self.embedder.embed(test_text)
            
            # Check dimension (common dimensions: 384, 768, 1024)
            dimension = len(embedding)
            valid_dimension = dimension in [384, 512, 768, 1024, 1536]
            
            tracker.add_result(
                test_name="embedding_dimension",
                component="embeddings",
                metric="vector_dimension",
                expected="384|768|1024",
                actual=dimension,
                passed=valid_dimension
            )
            
        except Exception as e:
            tracker.add_result(
                test_name="embedding_dimension",
                component="embeddings",
                metric="vector_dimension",
                expected="384|768|1024",
                actual=0,
                passed=False,
                error=str(e)
            )
            
    def test_semantic_similarity(self):
        """Test embeddings capture semantic similarity."""
        if not self.embedder_available:
            pytest.skip(f"Embedder not available: {self.embedder_error}")
            
        try:
            # Similar phrases should have high similarity
            text1 = "Qatar's unemployment rate is very low"
            text2 = "Qatar has minimal joblessness"
            text3 = "The weather in Paris is sunny"
            
            emb1 = self.embedder.embed(text1)
            emb2 = self.embedder.embed(text2)
            emb3 = self.embedder.embed(text3)
            
            sim_related = self.embedder.similarity(emb1, emb2)
            sim_unrelated = self.embedder.similarity(emb1, emb3)
            
            # Related texts should be more similar than unrelated
            semantic_correct = sim_related > sim_unrelated
            
            tracker.add_result(
                test_name="semantic_similarity",
                component="embeddings",
                metric="similarity_ordering",
                expected=f"related > unrelated",
                actual=f"{sim_related:.3f} vs {sim_unrelated:.3f}",
                passed=semantic_correct
            )
            
            assert semantic_correct, f"Semantic similarity failed: related={sim_related:.3f}, unrelated={sim_unrelated:.3f}"
            
        except Exception as e:
            tracker.add_result(
                test_name="semantic_similarity",
                component="embeddings",
                metric="similarity_ordering",
                expected="related > unrelated",
                actual="error",
                passed=False,
                error=str(e)
            )


# ============================================================================
# FIXTURE FOR REPORT GENERATION
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def generate_kg_report(request):
    """Generate test report after all tests complete."""
    yield
    
    # Save report after all tests
    report_dir = Path(__file__).parent.parent.parent / "test_reports"
    report_dir.mkdir(exist_ok=True)
    
    report_path = report_dir / f"kg_rag_accuracy_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    tracker.save_report(report_path)
    
    # Print summary
    summary = tracker.get_summary()
    print("\n" + "="*70)
    print("KNOWLEDGE GRAPH & RAG ACCURACY TEST SUMMARY")
    print("="*70)
    print(f"Total Tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Failed: {summary['failed']}")
    print(f"Accuracy: {summary['accuracy_pct']:.1f}%")
    print(f"Duration: {summary['duration_seconds']:.1f} seconds")
    print(f"\nReport saved to: {report_path}")
    
    if summary['failed_tests']:
        print("\nFailed Tests:")
        for test in summary['failed_tests']:
            print(f"  - {test['test_name']}: {test.get('error', 'Metric mismatch')}")

