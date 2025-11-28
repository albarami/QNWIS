"""
Phase 3 Tests: Hybrid CPU-GPU Knowledge Graph

Tests:
- CausalNode and CausalEdge dataclasses
- CausalChain construction
- GPUEmbeddingProcessor operations
- CausalGraph structure operations
- Causal chain discovery
- Blocking factor detection
- Cross-domain reasoning
- Similar node search with GPU acceleration
"""

import pytest
import numpy as np
from typing import List


class TestCausalDataclasses:
    """Test causal data structures."""
    
    def test_causal_node_creation(self):
        """CausalNode should store all fields correctly."""
        from src.nsic.knowledge.causal_graph import CausalNode
        
        embedding = np.random.rand(768).astype(np.float32)
        node = CausalNode(
            id="node_001",
            name="Oil Price Shock",
            node_type="event",
            domain="economic",
            embedding=embedding,
            attributes={"severity": "high"},
        )
        
        assert node.id == "node_001"
        assert node.name == "Oil Price Shock"
        assert node.node_type == "event"
        assert node.domain == "economic"
        assert node.embedding is not None
        assert node.attributes["severity"] == "high"
    
    def test_causal_node_hashable(self):
        """CausalNode should be hashable for use in sets."""
        from src.nsic.knowledge.causal_graph import CausalNode
        
        node1 = CausalNode(id="n1", name="Node 1", node_type="event", domain="economic")
        node2 = CausalNode(id="n1", name="Node 1 Copy", node_type="event", domain="economic")
        node3 = CausalNode(id="n2", name="Node 2", node_type="event", domain="economic")
        
        # Same ID = equal
        assert node1 == node2
        assert hash(node1) == hash(node2)
        
        # Different ID = not equal
        assert node1 != node3
    
    def test_causal_edge_creation(self):
        """CausalEdge should store relationship details."""
        from src.nsic.knowledge.causal_graph import CausalEdge
        
        edge = CausalEdge(
            source_id="node_001",
            target_id="node_002",
            relation_type="causes",
            strength=0.85,
            confidence=0.92,
            evidence=["study_1", "study_2"],
        )
        
        assert edge.source_id == "node_001"
        assert edge.target_id == "node_002"
        assert edge.relation_type == "causes"
        assert edge.strength == 0.85
        assert edge.confidence == 0.92
        assert len(edge.evidence) == 2
    
    def test_causal_edge_to_dict(self):
        """CausalEdge.to_dict() should return all fields."""
        from src.nsic.knowledge.causal_graph import CausalEdge
        
        edge = CausalEdge(
            source_id="a",
            target_id="b",
            relation_type="enables",
            strength=0.7,
            confidence=0.8,
            evidence=["e1"],
        )
        
        d = edge.to_dict()
        
        assert d["source"] == "a"
        assert d["target"] == "b"
        assert d["relation"] == "enables"
        assert d["strength"] == 0.7
        assert d["confidence"] == 0.8
        assert d["evidence_count"] == 1
    
    def test_causal_chain_creation(self):
        """CausalChain should aggregate path information."""
        from src.nsic.knowledge.causal_graph import CausalChain, CausalEdge
        
        edges = [
            CausalEdge("a", "b", "causes", 0.9, 0.85, []),
            CausalEdge("b", "c", "enables", 0.8, 0.90, []),
        ]
        
        chain = CausalChain(
            nodes=["a", "b", "c"],
            edges=edges,
            total_strength=0.72,
            avg_confidence=0.875,
            domains_crossed={"economic", "policy"},
        )
        
        assert len(chain.nodes) == 3
        assert len(chain.edges) == 2
        assert chain.total_strength == 0.72
        assert chain.avg_confidence == 0.875
        assert "economic" in chain.domains_crossed
    
    def test_causal_chain_to_dict(self):
        """CausalChain.to_dict() should indicate cross-domain status."""
        from src.nsic.knowledge.causal_graph import CausalChain
        
        chain = CausalChain(
            nodes=["a", "b"],
            edges=[],
            total_strength=0.9,
            avg_confidence=0.8,
            domains_crossed={"economic", "policy"},
        )
        
        d = chain.to_dict()
        
        assert d["is_cross_domain"] is True
        assert d["length"] == 2


class TestGPUEmbeddingProcessor:
    """Test GPU embedding operations."""
    
    def test_processor_init(self):
        """GPUEmbeddingProcessor should initialize correctly."""
        from src.nsic.knowledge.causal_graph import GPUEmbeddingProcessor
        
        processor = GPUEmbeddingProcessor(device="cpu", embedding_dim=768)
        
        assert processor.embedding_dim == 768
        # Device should be CPU when CUDA not available
        assert "cpu" in processor.device or "cuda" in processor.device
    
    def test_compute_similarity_batch_cpu(self):
        """Similarity computation should work on CPU."""
        from src.nsic.knowledge.causal_graph import GPUEmbeddingProcessor
        
        processor = GPUEmbeddingProcessor(device="cpu", embedding_dim=128)
        
        # Create query and candidates
        query = np.random.rand(128).astype(np.float32)
        query = query / np.linalg.norm(query)  # Normalize
        
        # Candidate identical to query should have similarity ~1.0
        candidates = [
            query.copy(),  # Same as query
            np.random.rand(128).astype(np.float32),  # Random
            -query,  # Opposite direction
        ]
        
        similarities = processor.compute_similarity_batch(query, candidates)
        
        assert len(similarities) == 3
        assert abs(similarities[0] - 1.0) < 0.01  # Same vector = 1.0
        assert similarities[2] < 0  # Opposite direction = negative
    
    def test_compute_similarity_empty(self):
        """Similarity computation should handle empty candidates."""
        from src.nsic.knowledge.causal_graph import GPUEmbeddingProcessor
        
        processor = GPUEmbeddingProcessor(device="cpu")
        query = np.random.rand(768).astype(np.float32)
        
        similarities = processor.compute_similarity_batch(query, [])
        
        assert len(similarities) == 0
    
    def test_project_embeddings_identity(self):
        """Projection without matrix should return original embeddings."""
        from src.nsic.knowledge.causal_graph import GPUEmbeddingProcessor
        
        processor = GPUEmbeddingProcessor(device="cpu", embedding_dim=128)
        
        embeddings = [
            np.random.rand(128).astype(np.float32),
            np.random.rand(128).astype(np.float32),
        ]
        
        projected = processor.project_embeddings(embeddings)
        
        assert len(projected) == 2
        assert np.allclose(projected[0], embeddings[0])


class TestCausalGraph:
    """Test causal graph operations."""
    
    def test_graph_init(self):
        """CausalGraph should initialize correctly."""
        from src.nsic.knowledge.causal_graph import CausalGraph
        
        graph = CausalGraph(gpu_device="cpu", embedding_dim=768)
        
        assert len(graph) == 0
        stats = graph.get_stats()
        assert stats["total_nodes"] == 0
        assert stats["total_edges"] == 0
    
    def test_add_node(self):
        """Graph should accept new nodes."""
        from src.nsic.knowledge.causal_graph import CausalGraph, CausalNode
        
        graph = CausalGraph(gpu_device="cpu")
        
        node = CausalNode(
            id="oil_shock",
            name="Oil Price Shock",
            node_type="event",
            domain="economic",
        )
        
        graph.add_node(node)
        
        assert len(graph) == 1
        assert "oil_shock" in graph.nodes
    
    def test_add_edge(self):
        """Graph should accept edges between existing nodes."""
        from src.nsic.knowledge.causal_graph import CausalGraph, CausalNode, CausalEdge
        
        graph = CausalGraph(gpu_device="cpu")
        
        # Add nodes first
        graph.add_node(CausalNode("a", "Node A", "event", "economic"))
        graph.add_node(CausalNode("b", "Node B", "factor", "economic"))
        
        # Add edge
        edge = CausalEdge("a", "b", "causes", 0.8, 0.9, ["evidence1"])
        graph.add_edge(edge)
        
        stats = graph.get_stats()
        assert stats["total_edges"] == 1
    
    def test_domain_indexing(self):
        """Graph should index nodes by domain."""
        from src.nsic.knowledge.causal_graph import CausalGraph, CausalNode
        
        graph = CausalGraph(gpu_device="cpu")
        
        graph.add_node(CausalNode("e1", "Econ 1", "event", "economic"))
        graph.add_node(CausalNode("e2", "Econ 2", "factor", "economic"))
        graph.add_node(CausalNode("p1", "Policy 1", "event", "policy"))
        
        stats = graph.get_stats()
        assert stats["domains"]["economic"] == 2
        assert stats["domains"]["policy"] == 1
    
    def test_find_causal_chains_simple(self):
        """Should find direct causal chain."""
        from src.nsic.knowledge.causal_graph import CausalGraph, CausalNode, CausalEdge
        
        graph = CausalGraph(gpu_device="cpu")
        
        # A -> B -> C
        graph.add_node(CausalNode("a", "A", "event", "economic"))
        graph.add_node(CausalNode("b", "B", "factor", "economic"))
        graph.add_node(CausalNode("c", "C", "event", "policy"))
        
        graph.add_edge(CausalEdge("a", "b", "causes", 0.9, 0.95, []))
        graph.add_edge(CausalEdge("b", "c", "enables", 0.8, 0.85, []))
        
        chains = graph.find_causal_chains("a", "c")
        
        assert len(chains) == 1
        assert chains[0].nodes == ["a", "b", "c"]
        assert abs(chains[0].total_strength - 0.72) < 0.01
    
    def test_find_causal_chains_no_path(self):
        """Should return empty when no path exists."""
        from src.nsic.knowledge.causal_graph import CausalGraph, CausalNode
        
        graph = CausalGraph(gpu_device="cpu")
        
        graph.add_node(CausalNode("a", "A", "event", "economic"))
        graph.add_node(CausalNode("b", "B", "factor", "policy"))
        # No edge between them
        
        chains = graph.find_causal_chains("a", "b")
        
        assert len(chains) == 0
    
    def test_find_blocking_factors(self):
        """Should identify blocking factors."""
        from src.nsic.knowledge.causal_graph import CausalGraph, CausalNode, CausalEdge
        
        graph = CausalGraph(gpu_device="cpu")
        
        # Setup: blocker -> target (blocks)
        graph.add_node(CausalNode("target", "Target", "event", "economic"))
        graph.add_node(CausalNode("blocker", "Blocker", "factor", "policy"))
        
        graph.add_edge(CausalEdge("blocker", "target", "blocks", 0.9, 0.85, []))
        
        blockers = graph.find_blocking_factors("target")
        
        assert len(blockers) == 1
        assert blockers[0]["factor_id"] == "blocker"
        assert blockers[0]["relation"] == "blocks"
    
    def test_find_similar_nodes(self):
        """Should find similar nodes using embeddings."""
        from src.nsic.knowledge.causal_graph import CausalGraph, CausalNode
        
        graph = CausalGraph(gpu_device="cpu", embedding_dim=128)
        
        # Use fixed seed for reproducibility
        np.random.seed(42)
        
        # Create nodes with embeddings - make similar VERY similar
        base_emb = np.random.rand(128).astype(np.float32)
        base_emb = base_emb / np.linalg.norm(base_emb)
        
        # Similar: base + tiny noise (cosine sim should be > 0.99)
        similar_emb = base_emb.copy()
        similar_emb[:10] += 0.01  # Tiny perturbation
        similar_emb = similar_emb / np.linalg.norm(similar_emb)
        
        # Different: orthogonal vector (cosine sim should be ~0)
        different_emb = np.zeros(128, dtype=np.float32)
        different_emb[64:] = base_emb[:64]  # Shuffled/orthogonal-ish
        different_emb = different_emb / np.linalg.norm(different_emb)
        
        graph.add_node(CausalNode("similar", "Similar", "event", "economic", embedding=similar_emb))
        graph.add_node(CausalNode("different", "Different", "event", "economic", embedding=different_emb))
        
        results = graph.find_similar_nodes(base_emb, top_k=2)
        
        assert len(results) == 2
        # Similar node should rank higher (has much higher cosine similarity)
        assert results[0][0] == "similar"
        assert results[0][1] > results[1][1]
    
    def test_cross_domain_reasoning(self):
        """Should find paths crossing domains."""
        from src.nsic.knowledge.causal_graph import CausalGraph, CausalNode, CausalEdge
        
        graph = CausalGraph(gpu_device="cpu")
        
        # Economic -> Policy path
        graph.add_node(CausalNode("econ_event", "Econ Event", "event", "economic"))
        graph.add_node(CausalNode("bridge", "Bridge", "factor", "social"))
        graph.add_node(CausalNode("policy_result", "Policy Result", "event", "policy"))
        
        graph.add_edge(CausalEdge("econ_event", "bridge", "causes", 0.8, 0.9, []))
        graph.add_edge(CausalEdge("bridge", "policy_result", "enables", 0.7, 0.85, []))
        
        paths = graph.cross_domain_reasoning("economic", "policy", "econ_event")
        
        assert len(paths) == 1
        assert paths[0]["target_node"] == "policy_result"
    
    def test_get_subgraph(self):
        """Should extract subgraph around a center node."""
        from src.nsic.knowledge.causal_graph import CausalGraph, CausalNode, CausalEdge
        
        graph = CausalGraph(gpu_device="cpu")
        
        # Create star topology: center connected to a, b, c
        graph.add_node(CausalNode("center", "Center", "event", "economic"))
        graph.add_node(CausalNode("a", "A", "factor", "economic"))
        graph.add_node(CausalNode("b", "B", "factor", "policy"))
        graph.add_node(CausalNode("c", "C", "factor", "social"))
        graph.add_node(CausalNode("far", "Far", "event", "timing"))  # Not connected
        
        graph.add_edge(CausalEdge("center", "a", "causes", 0.9, 0.9, []))
        graph.add_edge(CausalEdge("center", "b", "enables", 0.8, 0.8, []))
        graph.add_edge(CausalEdge("c", "center", "amplifies", 0.7, 0.7, []))
        
        subgraph = graph.get_subgraph("center", radius=1)
        
        assert len(subgraph["nodes"]) == 4  # center, a, b, c
        assert len(subgraph["edges"]) == 3
        # "far" should not be included
        node_ids = [n["id"] for n in subgraph["nodes"]]
        assert "far" not in node_ids


class TestFactoryFunction:
    """Test factory function."""
    
    def test_create_causal_graph(self):
        """create_causal_graph should return configured instance."""
        from src.nsic.knowledge.causal_graph import create_causal_graph
        
        graph = create_causal_graph(gpu_device="cpu", embedding_dim=512)
        
        assert graph is not None
        assert graph.gpu_processor.embedding_dim == 512


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_edge_with_missing_nodes(self):
        """Adding edge with missing nodes should log warning."""
        from src.nsic.knowledge.causal_graph import CausalGraph, CausalEdge
        
        graph = CausalGraph(gpu_device="cpu")
        
        # Try to add edge without nodes
        edge = CausalEdge("nonexistent_a", "nonexistent_b", "causes", 0.5, 0.5, [])
        graph.add_edge(edge)  # Should not crash
        
        assert graph.get_stats()["total_edges"] == 0
    
    def test_find_chains_nonexistent_nodes(self):
        """Finding chains with nonexistent nodes should return empty."""
        from src.nsic.knowledge.causal_graph import CausalGraph
        
        graph = CausalGraph(gpu_device="cpu")
        
        chains = graph.find_causal_chains("nonexistent_a", "nonexistent_b")
        
        assert chains == []
    
    def test_similar_nodes_empty_graph(self):
        """Similar node search on empty graph should return empty."""
        from src.nsic.knowledge.causal_graph import CausalGraph
        
        graph = CausalGraph(gpu_device="cpu", embedding_dim=128)
        
        query = np.random.rand(128).astype(np.float32)
        results = graph.find_similar_nodes(query)
        
        assert results == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

