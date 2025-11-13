"""
Query History Tracking for QNWIS (M3).

Stores and retrieves user query history for analytics and convenience.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QueryHistory:
    """
    Track and manage user query history.
    
    Provides query history for:
    - Recent queries display
    - Usage analytics
    - Quick re-run capability
    """
    
    def __init__(self, storage_dir: str = "data/history"):
        """
        Initialize query history.
        
        Args:
            storage_dir: Directory for history storage
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.storage_dir / "query_history.jsonl"
        logger.info(f"QueryHistory initialized: {storage_dir}")
    
    def add_query(
        self,
        question: str,
        request_id: str,
        provider: str = "anthropic",
        response_time_ms: Optional[float] = None,
        result_summary: Optional[str] = None
    ) -> None:
        """
        Add query to history.
        
        Args:
            question: User question
            request_id: Request correlation ID
            provider: LLM provider used
            response_time_ms: Response time in milliseconds
            result_summary: Brief summary of results
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "question": question,
            "request_id": request_id,
            "provider": provider,
            "response_time_ms": response_time_ms,
            "result_summary": result_summary
        }
        
        try:
            with open(self.history_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry) + '\n')
            logger.debug(f"Added query to history: {request_id}")
        except Exception as e:
            logger.error(f"Failed to add query to history: {e}")
    
    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get recent queries.
        
        Args:
            limit: Maximum number of queries to return
            
        Returns:
            List of query entries (most recent first)
        """
        if not self.history_file.exists():
            return []
        
        entries = []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        entry = json.loads(line)
                        entries.append(entry)
            
            # Return most recent first
            entries.reverse()
            return entries[:limit]
        
        except Exception as e:
            logger.error(f"Failed to read history: {e}")
            return []
    
    def search(self, query_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search query history.
        
        Args:
            query_text: Text to search for
            limit: Maximum results
            
        Returns:
            Matching query entries
        """
        all_queries = self.get_recent(limit=1000)
        
        query_text_lower = query_text.lower()
        matches = [
            q for q in all_queries
            if query_text_lower in q.get("question", "").lower()
        ]
        
        return matches[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get query history statistics.
        
        Returns:
            Statistics dictionary
        """
        all_queries = self.get_recent(limit=10000)
        
        if not all_queries:
            return {
                "total_queries": 0,
                "avg_response_time_ms": 0,
                "providers": {}
            }
        
        # Calculate statistics
        total = len(all_queries)
        
        response_times = [
            q["response_time_ms"]
            for q in all_queries
            if q.get("response_time_ms") is not None
        ]
        
        avg_response = (
            sum(response_times) / len(response_times)
            if response_times else 0
        )
        
        providers = {}
        for q in all_queries:
            provider = q.get("provider", "unknown")
            providers[provider] = providers.get(provider, 0) + 1
        
        return {
            "total_queries": total,
            "avg_response_time_ms": avg_response,
            "providers": providers,
            "oldest_query": all_queries[-1].get("timestamp") if all_queries else None,
            "newest_query": all_queries[0].get("timestamp") if all_queries else None
        }
    
    def render_recent_history(self, limit: int = 10) -> str:
        """
        Render recent history as markdown.
        
        Args:
            limit: Number of recent queries
            
        Returns:
            Markdown formatted history
        """
        queries = self.get_recent(limit=limit)
        
        if not queries:
            return "## Query History\n\nNo previous queries found."
        
        output = f"## Recent Query History ({len(queries)} queries)\n\n"
        
        for idx, query in enumerate(queries, 1):
            timestamp = query.get("timestamp", "")[:19]
            question = query.get("question", "")[:80]
            response_time = query.get("response_time_ms")
            
            output += f"### {idx}. {timestamp}\n\n"
            output += f"**Question:** {question}...\n"
            
            if response_time:
                output += f"**Response Time:** {response_time:.0f}ms\n"
            
            output += "\n"
        
        return output


# Global history instance
_history: Optional[QueryHistory] = None


def get_query_history() -> QueryHistory:
    """Get or create global query history instance."""
    global _history
    if _history is None:
        _history = QueryHistory()
    return _history
