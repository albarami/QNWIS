"""
QNWIS - Qatar National Workforce Intelligence System
Multi-Agent Matching Engine for Ministry of Labour

This package implements a production-grade matching system with:
- 6 specialized agents orchestrated via LangGraph DAG
- Stage A: <50ms, Stage B: <60ms, Stage C: <40ms
- 80% skill inference, 20% explicit extraction
- Bias mitigation (AraWEAT/SEAT <0.15)
- Performance targets: NDCG@10 0.70-0.80, MRR >0.75
"""

__version__ = "0.1.0"
__author__ = "Qatar Ministry of Labour"
