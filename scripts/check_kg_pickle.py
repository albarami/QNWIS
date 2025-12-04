#!/usr/bin/env python3
"""Check the contents of the knowledge graph pickle file."""
import pickle

with open('data/knowledge_graph.pkl', 'rb') as f:
    kg = pickle.load(f)

print("=== KNOWLEDGE GRAPH PICKLE CONTENTS ===")
print(f"Type: {type(kg)}")
print(f"Keys: {kg.keys() if isinstance(kg, dict) else 'Not a dict'}")

if isinstance(kg, dict):
    if 'nodes' in kg:
        print(f"Nodes: {len(kg['nodes'])}")
        print("Sample nodes:")
        for i, (node_id, node_data) in enumerate(list(kg['nodes'].items())[:5]):
            print(f"  - {node_id}: {node_data.get('name', 'N/A')}")
    
    if 'edges' in kg:
        print(f"Edges: {len(kg['edges'])}")
        print("Sample edges:")
        for edge in kg['edges'][:5]:
            print(f"  - {edge[0]} -> {edge[1]}")
    
    if 'stats' in kg:
        print(f"Stats: {kg['stats']}")








