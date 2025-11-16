"""
Query-level metrics tracking for workflow executions.

Provides a context manager for tracking metrics across an entire query execution,
including LLM calls, agent invocations, and overall latency.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

from src.qnwis.observability.metrics import record_query_execution


@dataclass
class QueryMetrics:
    """
    Tracks metrics for a single query execution.
    
    Aggregates LLM calls, agent invocations, and provides cost/latency summaries.
    """
    
    query_id: str
    query_text: str
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    
    # Workflow data
    complexity: str = "unknown"
    status: str = "pending"
    agents_invoked: List[str] = field(default_factory=list)
    confidence: float = 0.0
    citation_violations: int = 0
    facts_extracted: int = 0
    
    # LLM tracking
    llm_calls: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_llm_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        agent_name: str | None = None,
        purpose: str | None = None
    ) -> None:
        """Record an LLM call for this query."""
        self.llm_calls.append({
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": latency_ms,
            "agent": agent_name,
            "purpose": purpose
        })
    
    def finish(
        self,
        complexity: str,
        status: str,
        agents_invoked: List[str],
        confidence: float,
        citation_violations: int,
        facts_extracted: int
    ) -> None:
        """Mark query as complete and set final metrics."""
        self.end_time = time.time()
        self.complexity = complexity
        self.status = status
        self.agents_invoked = agents_invoked
        self.confidence = confidence
        self.citation_violations = citation_violations
        self.facts_extracted = facts_extracted
        
        # Record to global metrics
        total_latency_ms = (self.end_time - self.start_time) * 1000
        record_query_execution(
            complexity=complexity,
            status=status,
            total_latency_ms=total_latency_ms,
            agents_invoked=agents_invoked,
            confidence=confidence,
            citation_violations=citation_violations,
            facts_extracted=facts_extracted
        )
    
    def summary(self) -> Dict[str, Any]:
        """
        Get metrics summary for this query.
        
        Returns:
            Dictionary with comprehensive metrics
        """
        total_latency_ms = 0.0
        if self.end_time:
            total_latency_ms = (self.end_time - self.start_time) * 1000
        
        # Aggregate LLM metrics
        total_input_tokens = sum(call["input_tokens"] for call in self.llm_calls)
        total_output_tokens = sum(call["output_tokens"] for call in self.llm_calls)
        total_tokens = total_input_tokens + total_output_tokens
        
        # Calculate cost (Anthropic Claude 3.5 Sonnet pricing)
        # $3/M input, $15/M output
        cost_input = (total_input_tokens / 1_000_000) * 3.0
        cost_output = (total_output_tokens / 1_000_000) * 15.0
        total_cost_usd = cost_input + cost_output
        
        # Cost per token
        cost_per_token = total_cost_usd / total_tokens if total_tokens > 0 else 0.0
        
        return {
            "query_id": self.query_id,
            "query_text": self.query_text[:100],  # Truncate for privacy
            "total_latency_ms": total_latency_ms,
            "total_cost_usd": total_cost_usd,
            "llm_calls_count": len(self.llm_calls),
            "total_tokens": total_tokens,
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "cost_per_token": cost_per_token,
            "agents_invoked": self.agents_invoked,
            "agent_count": len(self.agents_invoked),
            "complexity": self.complexity,
            "confidence": self.confidence,
            "citation_violations": self.citation_violations,
            "facts_extracted": self.facts_extracted,
            "status": self.status
        }


# Global tracking of active queries
_active_queries: Dict[str, QueryMetrics] = {}


def start_query(query_text: str) -> str:
    """
    Start tracking a new query.
    
    Args:
        query_text: The query text
        
    Returns:
        Query ID for tracking
    """
    query_id = str(uuid.uuid4())
    _active_queries[query_id] = QueryMetrics(
        query_id=query_id,
        query_text=query_text
    )
    return query_id


def get_query_metrics(query_id: str) -> QueryMetrics | None:
    """
    Get metrics for an active query.
    
    Args:
        query_id: Query ID
        
    Returns:
        QueryMetrics instance or None if not found
    """
    return _active_queries.get(query_id)


def finish_query(
    query_id: str,
    complexity: str,
    status: str,
    agents_invoked: List[str],
    confidence: float,
    citation_violations: int,
    facts_extracted: int
) -> QueryMetrics:
    """
    Finish tracking a query and return final metrics.
    
    Args:
        query_id: Query ID
        complexity: Query complexity (simple, medium, complex)
        status: Execution status (success, error)
        agents_invoked: List of agents invoked
        confidence: Final confidence score
        citation_violations: Number of citation violations
        facts_extracted: Number of facts extracted
        
    Returns:
        QueryMetrics with final summary
    """
    query_metrics = _active_queries.get(query_id)
    if not query_metrics:
        # Create a placeholder if not found
        query_metrics = QueryMetrics(query_id=query_id, query_text="unknown")
    
    query_metrics.finish(
        complexity=complexity,
        status=status,
        agents_invoked=agents_invoked,
        confidence=confidence,
        citation_violations=citation_violations,
        facts_extracted=facts_extracted
    )
    
    # Remove from active queries to free memory
    _active_queries.pop(query_id, None)
    
    return query_metrics
