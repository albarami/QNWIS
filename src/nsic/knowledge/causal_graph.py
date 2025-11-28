"""
NSIC Hybrid CPU-GPU Knowledge Graph for Causal Reasoning

Architecture:
- CPU: Graph structure (NetworkX), traversal, path finding
- GPU (4): Embedding projection, similarity computation

Key features:
- Causal chain discovery
- Blocking factor detection
- Cross-domain reasoning
- Prevents memory fragmentation with hybrid approach
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import defaultdict
import time

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

try:
    import torch
    import torch.nn.functional as F
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class CausalNode:
    """Node in the causal graph."""
    id: str
    name: str
    node_type: str  # "event", "factor", "entity", "concept"
    domain: str  # "economic", "policy", "social", "competitive", "timing"
    embedding: Optional[np.ndarray] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, CausalNode):
            return self.id == other.id
        return False


@dataclass
class CausalEdge:
    """Edge representing causal relationship."""
    source_id: str
    target_id: str
    relation_type: str  # "causes", "enables", "blocks", "amplifies", "mitigates"
    strength: float  # 0.0 to 1.0
    confidence: float  # 0.0 to 1.0
    evidence: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "relation": self.relation_type,
            "strength": self.strength,
            "confidence": self.confidence,
            "evidence_count": len(self.evidence),
        }


@dataclass
class CausalChain:
    """A chain of causal relationships."""
    nodes: List[str]
    edges: List[CausalEdge]
    total_strength: float
    avg_confidence: float
    domains_crossed: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.nodes,
            "length": len(self.nodes),
            "total_strength": self.total_strength,
            "avg_confidence": self.avg_confidence,
            "domains": list(self.domains_crossed),
            "is_cross_domain": len(self.domains_crossed) > 1,
        }


class GPUEmbeddingProcessor:
    """GPU-accelerated embedding operations."""
    
    def __init__(self, device: str = "cuda:4", embedding_dim: int = 768):
        """
        Initialize GPU processor.
        
        Args:
            device: GPU device to use (default: cuda:4 per architecture)
            embedding_dim: Embedding dimension
        """
        self.device = device if TORCH_AVAILABLE and torch.cuda.is_available() else "cpu"
        self.embedding_dim = embedding_dim
        
        if TORCH_AVAILABLE and "cuda" in self.device:
            # Pre-allocate workspace on GPU
            self._workspace = torch.zeros(
                (1000, embedding_dim),
                device=self.device,
                dtype=torch.float32,
            )
        
        logger.info(f"GPUEmbeddingProcessor initialized on {self.device}")
    
    def compute_similarity_batch(
        self,
        query_embedding: np.ndarray,
        candidate_embeddings: List[np.ndarray],
    ) -> np.ndarray:
        """
        Compute cosine similarity between query and candidates on GPU.
        
        Args:
            query_embedding: Query embedding (dim,)
            candidate_embeddings: List of candidate embeddings
            
        Returns:
            Similarity scores array
        """
        if not candidate_embeddings:
            return np.array([])
        
        if not TORCH_AVAILABLE or "cuda" not in self.device:
            # CPU fallback
            query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-8)
            similarities = []
            for emb in candidate_embeddings:
                emb_norm = emb / (np.linalg.norm(emb) + 1e-8)
                similarities.append(np.dot(query_norm, emb_norm))
            return np.array(similarities)
        
        # GPU computation
        query_tensor = torch.from_numpy(query_embedding).float().to(self.device)
        candidates_tensor = torch.stack([
            torch.from_numpy(emb).float()
            for emb in candidate_embeddings
        ]).to(self.device)
        
        # Normalize
        query_tensor = F.normalize(query_tensor.unsqueeze(0), dim=1)
        candidates_tensor = F.normalize(candidates_tensor, dim=1)
        
        # Compute cosine similarity
        similarities = torch.mm(query_tensor, candidates_tensor.t()).squeeze(0)
        
        return similarities.cpu().numpy()
    
    def compute_similarity(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
    ) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding
            embedding2: Second embedding
            
        Returns:
            Cosine similarity score
        """
        # Normalize
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)
        
        if norm1 < 1e-8 or norm2 < 1e-8:
            return 0.0
        
        emb1_norm = embedding1 / norm1
        emb2_norm = embedding2 / norm2
        
        return float(np.dot(emb1_norm, emb2_norm))
    
    def project_embeddings(
        self,
        embeddings: List[np.ndarray],
        projection_matrix: Optional[np.ndarray] = None,
    ) -> List[np.ndarray]:
        """
        Project embeddings to a different space on GPU.
        
        Args:
            embeddings: List of embeddings to project
            projection_matrix: Optional projection matrix
            
        Returns:
            Projected embeddings
        """
        if not embeddings:
            return []
        
        if projection_matrix is None or not TORCH_AVAILABLE:
            return embeddings
        
        if "cuda" not in self.device:
            # CPU fallback
            return [emb @ projection_matrix for emb in embeddings]
        
        # GPU computation
        embeddings_tensor = torch.stack([
            torch.from_numpy(emb).float()
            for emb in embeddings
        ]).to(self.device)
        
        proj_tensor = torch.from_numpy(projection_matrix).float().to(self.device)
        
        projected = torch.mm(embeddings_tensor, proj_tensor)
        
        return [p.cpu().numpy() for p in projected]


class CausalGraph:
    """
    Hybrid CPU-GPU Knowledge Graph for causal reasoning.
    
    CPU handles:
    - Graph structure (NetworkX)
    - Path traversal
    - Topological operations
    
    GPU handles:
    - Embedding similarity
    - Batch projections
    - Nearest neighbor search
    """
    
    # Relation types with semantic meaning
    RELATION_TYPES = {
        "causes": {"direction": "forward", "polarity": "positive"},
        "enables": {"direction": "forward", "polarity": "positive"},
        "blocks": {"direction": "forward", "polarity": "negative"},
        "amplifies": {"direction": "forward", "polarity": "positive"},
        "mitigates": {"direction": "forward", "polarity": "negative"},
        "correlates": {"direction": "bidirectional", "polarity": "neutral"},
    }
    
    def __init__(
        self,
        gpu_device: str = "cuda:4",
        embedding_dim: int = 768,
    ):
        """
        Initialize the causal graph.
        
        Args:
            gpu_device: GPU device for embeddings (default: cuda:4)
            embedding_dim: Dimension of node embeddings
        """
        if not NETWORKX_AVAILABLE:
            raise ImportError("NetworkX is required for CausalGraph")
        
        # CPU: Graph structure
        self.graph = nx.DiGraph()
        self.nodes: Dict[str, CausalNode] = {}
        
        # GPU: Embedding processor
        self.gpu_processor = GPUEmbeddingProcessor(
            device=gpu_device,
            embedding_dim=embedding_dim,
        )
        
        # Indices for fast lookup
        self._domain_index: Dict[str, Set[str]] = defaultdict(set)
        self._type_index: Dict[str, Set[str]] = defaultdict(set)
        
        # Stats
        self._queries = 0
        self._chains_found = 0
        
        logger.info(f"CausalGraph initialized: GPU={gpu_device}, dim={embedding_dim}")
    
    def add_node(self, node: CausalNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node
        self.graph.add_node(
            node.id,
            name=node.name,
            type=node.node_type,
            domain=node.domain,
        )
        
        # Update indices
        self._domain_index[node.domain].add(node.id)
        self._type_index[node.node_type].add(node.id)
    
    def add_edge(self, edge: CausalEdge) -> None:
        """Add a causal edge to the graph."""
        if edge.source_id not in self.nodes or edge.target_id not in self.nodes:
            logger.warning(f"Edge references unknown nodes: {edge.source_id} -> {edge.target_id}")
            return
        
        self.graph.add_edge(
            edge.source_id,
            edge.target_id,
            relation=edge.relation_type,
            strength=edge.strength,
            confidence=edge.confidence,
            evidence=edge.evidence,
        )
    
    def find_causal_chains(
        self,
        source_id: str,
        target_id: str,
        max_length: int = 5,
        min_strength: float = 0.3,
    ) -> List[CausalChain]:
        """
        Find causal chains between two nodes.
        
        Args:
            source_id: Starting node ID
            target_id: Ending node ID
            max_length: Maximum chain length
            min_strength: Minimum edge strength to consider
            
        Returns:
            List of CausalChain objects
        """
        self._queries += 1
        
        if source_id not in self.nodes or target_id not in self.nodes:
            return []
        
        # CPU: Find all simple paths
        try:
            paths = list(nx.all_simple_paths(
                self.graph,
                source_id,
                target_id,
                cutoff=max_length,
            ))
        except nx.NetworkXError:
            return []
        
        chains = []
        for path in paths:
            # Extract edges along path
            edges = []
            total_strength = 1.0
            confidences = []
            domains = set()
            
            valid_chain = True
            for i in range(len(path) - 1):
                edge_data = self.graph.get_edge_data(path[i], path[i + 1])
                if edge_data is None or edge_data.get("strength", 0) < min_strength:
                    valid_chain = False
                    break
                
                edge = CausalEdge(
                    source_id=path[i],
                    target_id=path[i + 1],
                    relation_type=edge_data.get("relation", "causes"),
                    strength=edge_data.get("strength", 0.5),
                    confidence=edge_data.get("confidence", 0.5),
                    evidence=edge_data.get("evidence", []),
                )
                edges.append(edge)
                total_strength *= edge.strength
                confidences.append(edge.confidence)
                
                # Track domains
                if path[i] in self.nodes:
                    domains.add(self.nodes[path[i]].domain)
                if path[i + 1] in self.nodes:
                    domains.add(self.nodes[path[i + 1]].domain)
            
            if valid_chain and edges:
                chain = CausalChain(
                    nodes=path,
                    edges=edges,
                    total_strength=total_strength,
                    avg_confidence=np.mean(confidences) if confidences else 0,
                    domains_crossed=domains,
                )
                chains.append(chain)
                self._chains_found += 1
        
        # Sort by strength
        chains.sort(key=lambda c: c.total_strength, reverse=True)
        
        return chains
    
    def find_blocking_factors(
        self,
        target_id: str,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Find factors that block or mitigate effects on target.
        
        Args:
            target_id: Target node ID
            max_depth: Maximum search depth
            
        Returns:
            List of blocking factors with details
        """
        if target_id not in self.nodes:
            return []
        
        blockers = []
        
        # Find incoming edges with blocking relations
        for pred in self.graph.predecessors(target_id):
            edge_data = self.graph.get_edge_data(pred, target_id)
            if edge_data and edge_data.get("relation") in ["blocks", "mitigates"]:
                blocker = {
                    "factor_id": pred,
                    "factor_name": self.nodes[pred].name if pred in self.nodes else pred,
                    "relation": edge_data.get("relation"),
                    "strength": edge_data.get("strength", 0),
                    "confidence": edge_data.get("confidence", 0),
                }
                blockers.append(blocker)
        
        # Recursively find upstream blockers
        if max_depth > 1:
            for pred in self.graph.predecessors(target_id):
                upstream_blockers = self.find_blocking_factors(pred, max_depth - 1)
                for blocker in upstream_blockers:
                    blocker["path_to_target"] = [pred, target_id]
                    blockers.append(blocker)
        
        return blockers
    
    def find_similar_nodes(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        domain_filter: Optional[str] = None,
        type_filter: Optional[str] = None,
    ) -> List[Tuple[str, float]]:
        """
        Find nodes similar to query embedding using GPU acceleration.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            domain_filter: Filter by domain (optional)
            type_filter: Filter by node type (optional)
            
        Returns:
            List of (node_id, similarity_score) tuples
        """
        # Filter candidate nodes
        candidate_ids = set(self.nodes.keys())
        
        if domain_filter:
            candidate_ids &= self._domain_index.get(domain_filter, set())
        
        if type_filter:
            candidate_ids &= self._type_index.get(type_filter, set())
        
        # Get embeddings for candidates (only those with embeddings)
        candidates_with_emb = [
            (node_id, self.nodes[node_id].embedding)
            for node_id in candidate_ids
            if self.nodes[node_id].embedding is not None
        ]
        
        if not candidates_with_emb:
            return []
        
        # GPU: Compute similarities
        candidate_embeddings = [emb for _, emb in candidates_with_emb]
        similarities = self.gpu_processor.compute_similarity_batch(
            query_embedding,
            candidate_embeddings,
        )
        
        # Combine with IDs and sort
        results = [
            (candidates_with_emb[i][0], float(similarities[i]))
            for i in range(len(candidates_with_emb))
        ]
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]
    
    def cross_domain_reasoning(
        self,
        source_domain: str,
        target_domain: str,
        source_node_id: str,
        max_hops: int = 4,
    ) -> List[Dict[str, Any]]:
        """
        Find reasoning paths that cross from one domain to another.
        
        Args:
            source_domain: Starting domain
            target_domain: Target domain
            source_node_id: Starting node
            max_hops: Maximum path length
            
        Returns:
            List of cross-domain paths with details
        """
        if source_node_id not in self.nodes:
            return []
        
        target_nodes = self._domain_index.get(target_domain, set())
        
        paths = []
        for target_id in target_nodes:
            chains = self.find_causal_chains(
                source_node_id,
                target_id,
                max_length=max_hops,
            )
            
            for chain in chains:
                if len(chain.domains_crossed) > 1:
                    paths.append({
                        "source_node": source_node_id,
                        "target_node": target_id,
                        "chain": chain.to_dict(),
                        "bridge_nodes": [
                            n for n in chain.nodes
                            if n in self.nodes and
                            self.nodes[n].domain not in [source_domain, target_domain]
                        ],
                    })
        
        # Sort by chain strength
        paths.sort(key=lambda p: p["chain"]["total_strength"], reverse=True)
        
        return paths
    
    def get_subgraph(
        self,
        center_node_id: str,
        radius: int = 2,
    ) -> Dict[str, Any]:
        """
        Get a subgraph around a center node.
        
        Args:
            center_node_id: Center node ID
            radius: Number of hops from center
            
        Returns:
            Subgraph data with nodes and edges
        """
        if center_node_id not in self.nodes:
            return {"nodes": [], "edges": []}
        
        # Get nodes within radius using BFS
        visited = {center_node_id}
        frontier = {center_node_id}
        
        for _ in range(radius):
            next_frontier = set()
            for node in frontier:
                # Predecessors and successors
                next_frontier.update(self.graph.predecessors(node))
                next_frontier.update(self.graph.successors(node))
            next_frontier -= visited
            visited.update(next_frontier)
            frontier = next_frontier
        
        # Build subgraph data
        subgraph_nodes = [
            {
                "id": node_id,
                "name": self.nodes[node_id].name if node_id in self.nodes else node_id,
                "type": self.nodes[node_id].node_type if node_id in self.nodes else "unknown",
                "domain": self.nodes[node_id].domain if node_id in self.nodes else "unknown",
            }
            for node_id in visited
        ]
        
        subgraph_edges = []
        for node_id in visited:
            for successor in self.graph.successors(node_id):
                if successor in visited:
                    edge_data = self.graph.get_edge_data(node_id, successor)
                    subgraph_edges.append({
                        "source": node_id,
                        "target": successor,
                        "relation": edge_data.get("relation", "causes"),
                        "strength": edge_data.get("strength", 0.5),
                    })
        
        return {"nodes": subgraph_nodes, "edges": subgraph_edges}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "total_nodes": len(self.nodes),
            "total_edges": self.graph.number_of_edges(),
            "domains": dict([(d, len(nodes)) for d, nodes in self._domain_index.items()]),
            "types": dict([(t, len(nodes)) for t, nodes in self._type_index.items()]),
            "queries": self._queries,
            "chains_found": self._chains_found,
            "gpu_device": self.gpu_processor.device,
        }
    
    def __len__(self) -> int:
        return len(self.nodes)


def create_causal_graph(
    gpu_device: str = "cuda:4",
    embedding_dim: int = 768,
) -> CausalGraph:
    """
    Factory function to create a CausalGraph instance.
    
    Args:
        gpu_device: GPU device for embeddings
        embedding_dim: Embedding dimension
        
    Returns:
        CausalGraph instance
    """
    return CausalGraph(gpu_device=gpu_device, embedding_dim=embedding_dim)

