#!/usr/bin/env python3
"""Check existing knowledge graph structure."""

import json
from pathlib import Path

def main():
    kg_path = Path("data/knowledge_graph.json")
    
    if not kg_path.exists():
        print("Knowledge graph not found!")
        return
    
    with open(kg_path) as f:
        data = json.load(f)
    
    print("=" * 60)
    print("EXISTING KNOWLEDGE GRAPH")
    print("=" * 60)
    
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    
    print(f"Total nodes: {len(nodes)}")
    print(f"Total edges: {len(edges)}")
    
    # Node types
    types = {}
    for node in nodes:
        t = node.get("type", "unknown")
        types[t] = types.get(t, 0) + 1
    
    print(f"\nNode types:")
    for t, count in sorted(types.items(), key=lambda x: -x[1]):
        print(f"  {t}: {count}")
    
    # Edge types
    edge_types = {}
    for edge in edges:
        t = edge.get("relation", "unknown")
        edge_types[t] = edge_types.get(t, 0) + 1
    
    print(f"\nEdge types:")
    for t, count in sorted(edge_types.items(), key=lambda x: -x[1])[:10]:
        print(f"  {t}: {count}")
    
    # Sample nodes
    print(f"\nSample nodes:")
    for node in nodes[:5]:
        node_id = node.get("id", "?")
        node_name = node.get("name", "?")[:40]
        print(f"  - {node_id}: {node_name}")

if __name__ == "__main__":
    main()

