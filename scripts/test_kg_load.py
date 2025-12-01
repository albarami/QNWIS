#!/usr/bin/env python3
"""Test loading the pre-built Knowledge Graph."""
import sys
sys.path.insert(0, '.')

from src.nsic.knowledge import load_causal_graph

print('Loading pre-built Knowledge Graph...')
graph = load_causal_graph('data/knowledge_graph.pkl', gpu_device='cuda:4')

stats = graph.get_stats()
print('✅ Loaded KG:')
print(f'   Nodes: {len(graph.nodes)}')
print(f'   Edges: {graph.graph.number_of_edges()}')
print(f'   Domains: {stats["domains"]}')
print(f'   Types: {stats["types"]}')

# Test a query
chains = graph.find_causal_chains('oil_price_shock', 'gdp_decline')
print(f'   Causal chain test: {len(chains)} paths found')
if chains:
    print(f'   Best path: {chains[0].nodes}')
    print(f'   Path strength: {chains[0].total_strength:.3f}')


