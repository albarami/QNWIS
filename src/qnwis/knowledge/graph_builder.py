"""
Knowledge Graph Builder for QNWIS.

Builds a NetworkX knowledge graph from extracted entities and relationships.
Supports cross-domain reasoning (Oil Price -> Gov Revenue -> Education Spending).

Features:
- GPU-accelerated entity extraction (optional, with spaCy/transformers)
- Sector/Skill/Policy/Metric/Occupation entity types
- Causal relationship tracking
- Path finding for reasoning chains
"""

import logging
import re
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import pickle
import json

import networkx as nx

logger = logging.getLogger(__name__)


class EntityType(str, Enum):
    """Types of entities in the knowledge graph."""
    SECTOR = "sector"
    SKILL = "skill"
    POLICY = "policy"
    METRIC = "metric"
    OCCUPATION = "occupation"
    ORGANIZATION = "organization"
    COUNTRY = "country"
    PROGRAM = "program"
    TECHNOLOGY = "technology"


class RelationType(str, Enum):
    """Types of relationships between entities."""
    BELONGS_TO = "belongs_to"
    AFFECTS = "affects"
    REQUIRES = "requires"
    HAS_METRIC = "has_metric"
    EMPLOYS = "employs"
    IMPLEMENTS = "implements"
    TARGETS = "targets"
    DEPENDS_ON = "depends_on"
    COMPETES_WITH = "competes_with"
    COLLABORATES_WITH = "collaborates_with"


@dataclass
class Entity:
    """Represents an entity in the knowledge graph."""
    name: str
    entity_type: EntityType
    properties: Dict[str, Any] = field(default_factory=dict)
    source_documents: List[str] = field(default_factory=list)
    
    @property
    def node_id(self) -> str:
        """Unique identifier for the entity."""
        return f"{self.entity_type.value}:{self.name}".lower().replace(" ", "_")


@dataclass
class Relationship:
    """Represents a relationship between entities."""
    source: str  # node_id of source entity
    target: str  # node_id of target entity
    relation_type: RelationType
    weight: float = 1.0
    confidence: float = 1.0
    source_documents: List[str] = field(default_factory=list)


class QNWISKnowledgeGraph:
    """
    Knowledge graph for Qatar National Workforce Intelligence System.
    
    Connects:
    - Skills -> Occupations -> Sectors -> Companies
    - Skills -> Education Programs -> Institutions
    - Policies -> Targets -> Metrics
    - Sectors -> Metrics -> Performance
    """
    
    # Pre-defined Qatar/GCC entities
    KNOWN_SECTORS = {
        "Energy", "Oil & Gas", "LNG", "Petrochemicals",
        "Finance", "Banking", "Insurance",
        "Healthcare", "Medical", "Pharmaceutical",
        "Education", "Higher Education", "Vocational Training",
        "Tourism", "Hospitality", "Aviation",
        "Construction", "Real Estate", "Infrastructure",
        "Technology", "IT", "Digital", "Telecom",
        "Retail", "Trade", "Commerce",
        "Manufacturing", "Industry",
        "Government", "Public Sector",
        "Transportation", "Logistics"
    }
    
    KNOWN_POLICIES = {
        "Qatar Vision 2030", "QNV2030", "Vision 2030",
        "Qatarization", "Nationalization",
        "NDS", "National Development Strategy",
        "Labor Law", "Labour Law",
        "Workforce Development",
        "Skills Framework",
        "Digital Transformation",
    }
    
    KNOWN_METRICS = {
        "Unemployment Rate", "Employment Rate",
        "Labor Force Participation",
        "Qatarization Rate", "Nationalization Rate",
        "GDP Growth", "GDP Per Capita",
        "FDI", "Foreign Direct Investment",
        "Trade Balance", "Exports", "Imports",
        "Education Enrollment", "Literacy Rate",
        "Skills Gap", "Training Completion Rate",
        "Workforce Size", "Employment Growth",
    }
    
    def __init__(self):
        """Initialize knowledge graph."""
        self.graph = nx.DiGraph()
        self._entity_index: Dict[str, Entity] = {}
        self._source_docs: Set[str] = set()
    
    def add_entity(
        self,
        name: str,
        entity_type: EntityType,
        properties: Optional[Dict[str, Any]] = None,
        source_document: Optional[str] = None,
    ) -> str:
        """
        Add an entity to the graph.
        
        Args:
            name: Entity name
            entity_type: Type of entity
            properties: Additional properties
            source_document: Source document reference
            
        Returns:
            Node ID of the added entity
        """
        entity = Entity(
            name=name,
            entity_type=entity_type,
            properties=properties or {},
            source_documents=[source_document] if source_document else []
        )
        
        node_id = entity.node_id
        
        if node_id in self._entity_index:
            # Merge with existing entity
            existing = self._entity_index[node_id]
            existing.properties.update(entity.properties)
            if source_document and source_document not in existing.source_documents:
                existing.source_documents.append(source_document)
        else:
            self._entity_index[node_id] = entity
            self.graph.add_node(
                node_id,
                name=name,
                type=entity_type.value,
                properties=properties or {},
            )
        
        if source_document:
            self._source_docs.add(source_document)
        
        return node_id
    
    def add_relationship(
        self,
        source_name: str,
        source_type: EntityType,
        target_name: str,
        target_type: EntityType,
        relation_type: RelationType,
        weight: float = 1.0,
        confidence: float = 1.0,
        source_document: Optional[str] = None,
    ) -> None:
        """
        Add a relationship between two entities.
        
        Args:
            source_name: Name of source entity
            source_type: Type of source entity
            target_name: Name of target entity
            target_type: Type of target entity
            relation_type: Type of relationship
            weight: Relationship strength (0-1)
            confidence: Confidence in relationship (0-1)
            source_document: Source document reference
        """
        # Ensure entities exist
        source_id = self.add_entity(source_name, source_type, source_document=source_document)
        target_id = self.add_entity(target_name, target_type, source_document=source_document)
        
        # Add edge
        if self.graph.has_edge(source_id, target_id):
            # Update existing edge
            existing = self.graph.edges[source_id, target_id]
            existing["weight"] = max(existing.get("weight", 0), weight)
            existing["confidence"] = max(existing.get("confidence", 0), confidence)
            if source_document:
                docs = existing.get("source_documents", [])
                if source_document not in docs:
                    docs.append(source_document)
                existing["source_documents"] = docs
        else:
            self.graph.add_edge(
                source_id,
                target_id,
                relation_type=relation_type.value,
                weight=weight,
                confidence=confidence,
                source_documents=[source_document] if source_document else []
            )
    
    def find_path(
        self,
        from_entity: str,
        to_entity: str,
        max_length: int = 5,
    ) -> Optional[List[str]]:
        """
        Find shortest path between two entities.
        
        Args:
            from_entity: Starting entity name or node_id
            to_entity: Target entity name or node_id
            max_length: Maximum path length
            
        Returns:
            List of node IDs in path, or None if no path exists
        """
        # Try to find nodes
        from_id = self._resolve_node_id(from_entity)
        to_id = self._resolve_node_id(to_entity)
        
        if not from_id or not to_id:
            return None
        
        try:
            path = nx.shortest_path(self.graph, from_id, to_id)
            if len(path) <= max_length:
                return path
            return None
        except nx.NetworkXNoPath:
            return None
    
    def find_all_paths(
        self,
        from_entity: str,
        to_entity: str,
        max_length: int = 5,
    ) -> List[List[str]]:
        """
        Find all paths between two entities.
        
        Args:
            from_entity: Starting entity name or node_id
            to_entity: Target entity name or node_id
            max_length: Maximum path length
            
        Returns:
            List of paths (each path is a list of node IDs)
        """
        from_id = self._resolve_node_id(from_entity)
        to_id = self._resolve_node_id(to_entity)
        
        if not from_id or not to_id:
            return []
        
        try:
            paths = list(nx.all_simple_paths(
                self.graph, from_id, to_id, cutoff=max_length
            ))
            return paths
        except nx.NetworkXError:
            return []
    
    def get_related_entities(
        self,
        entity: str,
        relation_type: Optional[RelationType] = None,
        max_hops: int = 1,
    ) -> List[Tuple[str, Dict[str, Any]]]:
        """
        Get entities related to a given entity.
        
        Args:
            entity: Entity name or node_id
            relation_type: Filter by relationship type
            max_hops: Maximum number of hops
            
        Returns:
            List of (node_id, edge_data) tuples
        """
        node_id = self._resolve_node_id(entity)
        
        if not node_id or node_id not in self.graph:
            return []
        
        results = []
        
        # Get immediate neighbors
        for neighbor in self.graph.neighbors(node_id):
            edge_data = self.graph.edges[node_id, neighbor]
            
            if relation_type is None or edge_data.get("relation_type") == relation_type.value:
                results.append((neighbor, edge_data))
        
        # Multi-hop if requested
        if max_hops > 1:
            visited = {node_id}
            current_level = [node_id]
            
            for _ in range(max_hops):
                next_level = []
                for node in current_level:
                    for neighbor in self.graph.neighbors(node):
                        if neighbor not in visited:
                            visited.add(neighbor)
                            edge_data = self.graph.edges[node, neighbor]
                            if relation_type is None or edge_data.get("relation_type") == relation_type.value:
                                results.append((neighbor, edge_data))
                            next_level.append(neighbor)
                current_level = next_level
        
        return results
    
    def get_causal_chain(
        self,
        start_entity: str,
        end_entity: str,
    ) -> List[Dict[str, Any]]:
        """
        Get the causal chain (reasoning path) between entities.
        
        Args:
            start_entity: Starting entity
            end_entity: Ending entity
            
        Returns:
            List of steps in the causal chain with explanations
        """
        path = self.find_path(start_entity, end_entity)
        
        if not path:
            return []
        
        chain = []
        for i in range(len(path) - 1):
            source = path[i]
            target = path[i + 1]
            edge_data = self.graph.edges[source, target]
            
            source_node = self.graph.nodes[source]
            target_node = self.graph.nodes[target]
            
            chain.append({
                "from": source_node.get("name", source),
                "from_type": source_node.get("type"),
                "to": target_node.get("name", target),
                "to_type": target_node.get("type"),
                "relationship": edge_data.get("relation_type"),
                "confidence": edge_data.get("confidence", 1.0),
            })
        
        return chain
    
    def _resolve_node_id(self, entity: str) -> Optional[str]:
        """Resolve entity name to node ID."""
        # Check if already a node ID
        if entity in self.graph:
            return entity
        
        # Search by name
        entity_lower = entity.lower().replace(" ", "_")
        
        for node_id in self.graph.nodes():
            if entity_lower in node_id.lower():
                return node_id
            
            node_data = self.graph.nodes[node_id]
            if node_data.get("name", "").lower() == entity.lower():
                return node_id
        
        return None
    
    def extract_entities_from_text(
        self,
        text: str,
        source_document: Optional[str] = None,
    ) -> List[str]:
        """
        Extract entities from text using pattern matching.
        
        Args:
            text: Text to extract entities from
            source_document: Source document reference
            
        Returns:
            List of extracted entity node IDs
        """
        extracted = []
        
        # Extract known sectors
        for sector in self.KNOWN_SECTORS:
            if sector.lower() in text.lower():
                node_id = self.add_entity(
                    sector, EntityType.SECTOR, source_document=source_document
                )
                extracted.append(node_id)
        
        # Extract known policies
        for policy in self.KNOWN_POLICIES:
            if policy.lower() in text.lower():
                node_id = self.add_entity(
                    policy, EntityType.POLICY, source_document=source_document
                )
                extracted.append(node_id)
        
        # Extract known metrics
        for metric in self.KNOWN_METRICS:
            if metric.lower() in text.lower():
                node_id = self.add_entity(
                    metric, EntityType.METRIC, source_document=source_document
                )
                extracted.append(node_id)
        
        # Extract skills (pattern-based)
        skill_patterns = [
            r'\b(data analytics?|machine learning|AI|artificial intelligence)\b',
            r'\b(programming|software development|coding)\b',
            r'\b(project management|leadership|communication)\b',
            r'\b(engineering|technical skills?)\b',
            r'\b(arabic|english|language skills?)\b',
        ]
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                skill_name = match if isinstance(match, str) else match[0]
                node_id = self.add_entity(
                    skill_name.title(), EntityType.SKILL, source_document=source_document
                )
                extracted.append(node_id)
        
        return list(set(extracted))
    
    def infer_relationships(self, source_document: Optional[str] = None) -> int:
        """
        Infer relationships between entities based on co-occurrence.
        
        Args:
            source_document: Filter to entities from specific document
            
        Returns:
            Number of relationships inferred
        """
        count = 0
        
        # Group entities by type
        sectors = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "sector"]
        skills = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "skill"]
        policies = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "policy"]
        metrics = [n for n, d in self.graph.nodes(data=True) if d.get("type") == "metric"]
        
        # Skills -> Sectors (REQUIRES relationship)
        for skill in skills:
            for sector in sectors:
                skill_entity = self._entity_index.get(skill)
                sector_entity = self._entity_index.get(sector)
                
                if skill_entity and sector_entity:
                    # Check co-occurrence in documents
                    common_docs = set(skill_entity.source_documents) & set(sector_entity.source_documents)
                    if common_docs:
                        self.graph.add_edge(
                            sector, skill,
                            relation_type=RelationType.REQUIRES.value,
                            weight=min(1.0, len(common_docs) * 0.2),
                            confidence=0.7,
                            source_documents=list(common_docs)
                        )
                        count += 1
        
        # Policies -> Metrics (TARGETS relationship)
        for policy in policies:
            for metric in metrics:
                policy_entity = self._entity_index.get(policy)
                metric_entity = self._entity_index.get(metric)
                
                if policy_entity and metric_entity:
                    common_docs = set(policy_entity.source_documents) & set(metric_entity.source_documents)
                    if common_docs:
                        self.graph.add_edge(
                            policy, metric,
                            relation_type=RelationType.TARGETS.value,
                            weight=min(1.0, len(common_docs) * 0.2),
                            confidence=0.6,
                            source_documents=list(common_docs)
                        )
                        count += 1
        
        # Sectors -> Metrics (HAS_METRIC relationship)
        for sector in sectors:
            for metric in metrics:
                sector_entity = self._entity_index.get(sector)
                metric_entity = self._entity_index.get(metric)
                
                if sector_entity and metric_entity:
                    common_docs = set(sector_entity.source_documents) & set(metric_entity.source_documents)
                    if common_docs:
                        self.graph.add_edge(
                            sector, metric,
                            relation_type=RelationType.HAS_METRIC.value,
                            weight=min(1.0, len(common_docs) * 0.2),
                            confidence=0.6,
                            source_documents=list(common_docs)
                        )
                        count += 1
        
        logger.info(f"Inferred {count} relationships")
        return count
    
    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        type_counts = {}
        for _, data in self.graph.nodes(data=True):
            t = data.get("type", "unknown")
            type_counts[t] = type_counts.get(t, 0) + 1
        
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "entity_types": type_counts,
            "source_documents": len(self._source_docs),
            "density": nx.density(self.graph) if self.graph.number_of_nodes() > 0 else 0,
        }
    
    def save(self, path: Path) -> None:
        """Save graph to disk."""
        data = {
            "graph": nx.node_link_data(self.graph),
            "entity_index": {k: {
                "name": v.name,
                "entity_type": v.entity_type.value,
                "properties": v.properties,
                "source_documents": v.source_documents
            } for k, v in self._entity_index.items()},
            "source_docs": list(self._source_docs)
        }
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved knowledge graph to {path}")
    
    def load(self, path: Path) -> None:
        """Load graph from disk."""
        with open(path, 'r') as f:
            data = json.load(f)
        
        # Use explicit edges parameter to avoid FutureWarning in NetworkX 3.6+
        self.graph = nx.node_link_graph(data["graph"], edges="links")
        self._entity_index = {k: Entity(
            name=v["name"],
            entity_type=EntityType(v["entity_type"]),
            properties=v.get("properties", {}),
            source_documents=v.get("source_documents", [])
        ) for k, v in data.get("entity_index", {}).items()}
        self._source_docs = set(data.get("source_docs", []))
        
        logger.info(f"Loaded knowledge graph from {path}")


def build_graph_from_documents(
    documents: List[Dict[str, Any]],
    graph: Optional[QNWISKnowledgeGraph] = None,
) -> QNWISKnowledgeGraph:
    """
    Build knowledge graph from a list of documents.
    
    Args:
        documents: List of document dicts with 'text' and 'source' keys
        graph: Optional existing graph to add to
        
    Returns:
        Knowledge graph with extracted entities and relationships
    """
    if graph is None:
        graph = QNWISKnowledgeGraph()
    
    logger.info(f"Building knowledge graph from {len(documents)} documents")
    
    for doc in documents:
        text = doc.get("text", "")
        source = doc.get("source", "unknown")
        
        # Extract entities
        graph.extract_entities_from_text(text, source_document=source)
    
    # Infer relationships
    graph.infer_relationships()
    
    stats = graph.get_stats()
    logger.info(f"Built graph with {stats['total_nodes']} nodes, {stats['total_edges']} edges")
    
    return graph

