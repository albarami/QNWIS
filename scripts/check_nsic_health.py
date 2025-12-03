#!/usr/bin/env python3
"""
NSIC System Health Check Script

Verifies all components of the NSIC system are running and connected:
- PostgreSQL database
- Engine B (GPU compute services)
- RAG document store
- Knowledge Graph
- Embeddings model
- Deterministic agents data access
- API endpoints

Usage:
    python scripts/check_nsic_health.py
    python scripts/check_nsic_health.py --verbose
"""

import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

import json
import httpx
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class HealthCheck:
    component: str
    status: str  # "OK", "WARN", "FAIL"
    message: str
    details: Optional[Dict[str, Any]] = None


class NSICHealthChecker:
    """Comprehensive health checker for NSIC system."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.results: List[HealthCheck] = []
        
    def check_all(self) -> bool:
        """Run all health checks and return overall status."""
        print("\n" + "=" * 60)
        print(" NSIC SYSTEM HEALTH CHECK")
        print("=" * 60)
        print(f" Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60 + "\n")
        
        # Run all checks
        self._check_database()
        self._check_engine_b()
        self._check_rag()
        self._check_knowledge_graph()
        self._check_embeddings()
        self._check_deterministic_agents()
        self._check_query_registry()
        
        # Print summary
        self._print_summary()
        
        # Return overall status
        return all(r.status == "OK" for r in self.results)
    
    def _add_result(self, component: str, status: str, message: str, details: Dict = None):
        result = HealthCheck(component, status, message, details)
        self.results.append(result)
        
        # Print result
        icon = {"OK": "[+]", "WARN": "[!]", "FAIL": "[-]"}[status]
        color = {"OK": "\033[92m", "WARN": "\033[93m", "FAIL": "\033[91m"}[status]
        reset = "\033[0m"
        
        print(f"{color}{icon}{reset} {component}: {message}")
        
        if self.verbose and details:
            for k, v in details.items():
                print(f"    {k}: {v}")
    
    def _check_database(self):
        """Check PostgreSQL database connection."""
        try:
            from sqlalchemy import create_engine, text
            
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                self._add_result("PostgreSQL", "FAIL", "DATABASE_URL not set")
                return
            
            engine = create_engine(db_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
                
            self._add_result("PostgreSQL", "OK", "Connected", 
                           {"version": version[:50] if version else "unknown"})
            
        except Exception as e:
            self._add_result("PostgreSQL", "FAIL", str(e)[:50])
    
    def _check_engine_b(self):
        """Check Engine B GPU compute services."""
        try:
            response = httpx.get("http://localhost:8001/health", timeout=5)
            
            if response.status_code == 200:
                health = response.json()
                
                services = ["monte_carlo", "forecasting", "sensitivity", 
                           "thresholds", "benchmark", "correlation", "optimization"]
                
                healthy_count = sum(1 for s in services if health.get(s, {}).get("status") == "healthy")
                gpu_count = sum(1 for s in services if health.get(s, {}).get("gpu_available", False))
                
                self._add_result("Engine B", "OK", 
                               f"{healthy_count}/{len(services)} services, {gpu_count} with GPU",
                               {"services": healthy_count, "gpu_enabled": gpu_count})
            else:
                self._add_result("Engine B", "WARN", f"Status {response.status_code}")
                
        except httpx.ConnectError:
            self._add_result("Engine B", "FAIL", "Not running on port 8001")
        except Exception as e:
            self._add_result("Engine B", "FAIL", str(e)[:50])
    
    def _check_rag(self):
        """Check RAG document store."""
        try:
            from src.qnwis.rag.document_loader import load_source_documents
            
            docs = load_source_documents()
            doc_count = len(docs)
            
            if doc_count > 0:
                sources = set(d.get("source", "unknown") for d in docs)
                self._add_result("RAG Documents", "OK", 
                               f"{doc_count} documents from {len(sources)} sources",
                               {"documents": doc_count, "sources": list(sources)[:5]})
            else:
                self._add_result("RAG Documents", "WARN", "No documents loaded")
                
        except Exception as e:
            self._add_result("RAG Documents", "WARN", str(e)[:50])
    
    def _check_knowledge_graph(self):
        """Check Knowledge Graph."""
        try:
            from src.qnwis.knowledge.graph_builder import QNWISKnowledgeGraph
            
            kg = QNWISKnowledgeGraph()
            kg_path = PROJECT_ROOT / "data" / "knowledge_graph.json"
            
            if kg_path.exists():
                kg.load(kg_path)
                node_count = len(kg.graph.nodes)
                edge_count = len(kg.graph.edges)
                
                self._add_result("Knowledge Graph", "OK", 
                               f"{node_count} nodes, {edge_count} edges",
                               {"nodes": node_count, "edges": edge_count})
            else:
                self._add_result("Knowledge Graph", "WARN", "Graph file not found")
                
        except Exception as e:
            self._add_result("Knowledge Graph", "WARN", str(e)[:50])
    
    def _check_embeddings(self):
        """Check embeddings model."""
        try:
            from src.qnwis.rag.embeddings import SentenceEmbedder
            
            embedder = SentenceEmbedder()
            
            # Test embedding
            test_text = "Test embedding generation"
            embedding = embedder.embed(test_text)
            
            self._add_result("Embeddings", "OK", 
                           f"Model: {embedder.model_name}, dim={len(embedding)}",
                           {"model": embedder.model_name, "dimension": len(embedding)})
            
        except Exception as e:
            self._add_result("Embeddings", "WARN", str(e)[:50])
    
    def _check_deterministic_agents(self):
        """Check deterministic agent data access."""
        try:
            from src.qnwis.agents.base import DataClient
            from src.qnwis.agents.national_strategy import NationalStrategyAgent
            
            client = DataClient()
            
            # Test a query
            result = client.run("syn_unemployment_gcc_latest")
            rows = list(result.rows) if result.rows else []
            
            if len(rows) > 0:
                self._add_result("DataClient", "OK", 
                               f"Test query returned {len(rows)} rows",
                               {"test_rows": len(rows)})
            else:
                self._add_result("DataClient", "WARN", "Test query returned no data")
                
        except Exception as e:
            self._add_result("DataClient", "FAIL", str(e)[:50])
    
    def _check_query_registry(self):
        """Check query registry."""
        try:
            from src.qnwis.data.deterministic.registry import QueryRegistry
            
            registry = QueryRegistry()
            registry.load_all()
            
            query_ids = registry.list_query_ids()
            
            self._add_result("Query Registry", "OK", 
                           f"{len(query_ids)} queries registered",
                           {"queries": len(query_ids)})
            
        except Exception as e:
            self._add_result("Query Registry", "WARN", str(e)[:50])
    
    def _print_summary(self):
        """Print summary of all checks."""
        print("\n" + "=" * 60)
        print(" SUMMARY")
        print("=" * 60)
        
        ok_count = sum(1 for r in self.results if r.status == "OK")
        warn_count = sum(1 for r in self.results if r.status == "WARN")
        fail_count = sum(1 for r in self.results if r.status == "FAIL")
        
        print(f"\n  OK:   {ok_count}")
        print(f"  WARN: {warn_count}")
        print(f"  FAIL: {fail_count}")
        print(f"  Total: {len(self.results)}")
        
        if fail_count == 0 and warn_count == 0:
            print("\n  [ALL SYSTEMS HEALTHY]")
        elif fail_count == 0:
            print("\n  [SYSTEM OPERATIONAL WITH WARNINGS]")
        else:
            print("\n  [SOME COMPONENTS NEED ATTENTION]")
        
        print("\n" + "=" * 60 + "\n")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="NSIC System Health Check")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Show detailed information")
    
    args = parser.parse_args()
    
    checker = NSICHealthChecker(verbose=args.verbose)
    healthy = checker.check_all()
    
    sys.exit(0 if healthy else 1)


if __name__ == "__main__":
    main()

