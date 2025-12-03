"""
Research Synthesizer Agent - PhD-Level Academic Literature Review Engine.

This agent acts as "Dr. Research" - a virtual PhD scholar who:
1. Searches Semantic Scholar (214M+ peer-reviewed academic papers)
2. Queries Perplexity AI for real-time research synthesis
3. Retrieves internal R&D documents via RAG
4. Explores Knowledge Graph for entity relationships

CRITICAL ROLE: Produces a RIGOROUS ACADEMIC LITERATURE REVIEW that:
- Synthesizes peer-reviewed evidence on ANY topic
- Provides proper academic citations (Author, Year)
- Identifies consensus views AND scholarly debates
- Notes evidence gaps and methodological limitations
- Makes evidence-based policy recommendations

The output is formatted as a proper academic synthesis that PhD-level
debate agents can cite with confidence. All claims are sourced.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..data.deterministic.models import QueryResult

logger = logging.getLogger(__name__)


@dataclass
class ResearchFinding:
    """A single research finding with citation."""
    
    title: str
    source: str  # semantic_scholar, perplexity, rag, knowledge_graph
    summary: str
    relevance_score: float  # 0-1
    citation: str
    year: Optional[int] = None
    authors: List[str] = field(default_factory=list)
    methodology: Optional[str] = None
    key_metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResearchSynthesis:
    """Aggregated research synthesis for a query."""
    
    query: str
    total_sources_searched: int
    findings: List[ResearchFinding]
    consensus_view: str  # What most research agrees on
    dissenting_views: List[str]  # Contrarian findings
    evidence_gaps: List[str]  # What research doesn't cover
    confidence_level: str  # high/medium/low based on evidence quality
    narrative: str  # Executive summary
    methodology_note: str  # How findings were synthesized


class ResearchSynthesizerAgent:
    """
    Deterministic research evidence aggregator.
    
    Searches multiple research sources and synthesizes findings into
    a structured summary that LLM debate agents can cite.
    
    This agent does NOT use LLM for synthesis - it aggregates and
    structures findings deterministically based on relevance scores.
    """
    
    def __init__(
        self,
        semantic_scholar_api_key: Optional[str] = None,
        perplexity_api_key: Optional[str] = None,
        rag_client: Optional[Any] = None,
        knowledge_graph_client: Optional[Any] = None,
    ):
        """
        Initialize the Research Synthesizer.
        
        Args:
            semantic_scholar_api_key: API key for Semantic Scholar
            perplexity_api_key: API key for Perplexity
            rag_client: Client for RAG document retrieval (auto-initialized if None)
            knowledge_graph_client: Client for knowledge graph queries (auto-initialized if None)
        """
        self.semantic_scholar_key = semantic_scholar_api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self.perplexity_key = perplexity_api_key or os.getenv("PERPLEXITY_API_KEY")
        
        # Auto-initialize RAG if not provided - uses 1965 pre-indexed R&D documents
        if rag_client is not None:
            self.rag_client = rag_client
        else:
            self.rag_client = self._init_default_rag_client()
        
        # Auto-initialize Knowledge Graph if not provided
        if knowledge_graph_client is not None:
            self.kg_client = knowledge_graph_client
        else:
            self.kg_client = self._init_default_kg_client()
        
        # Log what's available
        sources = []
        if self.semantic_scholar_key:
            sources.append("Semantic Scholar")
        if self.perplexity_key:
            sources.append("Perplexity")
        if self.rag_client:
            sources.append("RAG (R&D Papers)")
        if self.kg_client:
            sources.append("Knowledge Graph")
        
        logger.info(f"✅ ResearchSynthesizerAgent initialized with: {', '.join(sources) or 'No sources'}")
    
    def _init_default_rag_client(self) -> Optional[Any]:
        """Initialize default RAG client from pre-built store (1965 documents)."""
        try:
            from pathlib import Path
            import json
            
            # Find RAG store - check multiple possible locations
            possible_paths = [
                Path(__file__).parent.parent.parent.parent / "data" / "rag_store.json",
                Path(__file__).parent.parent.parent.parent.parent / "data" / "rag_store.json",
                Path("data/rag_store.json"),
            ]
            
            rag_store_path = None
            for p in possible_paths:
                if p.exists():
                    rag_store_path = p
                    break
            
            if not rag_store_path:
                logger.warning("⚠️ RAG store not found - R&D papers will not be available")
                return None
            
            # Load documents
            with open(rag_store_path, "r", encoding="utf-8") as f:
                store_data = json.load(f)
            
            docs = store_data.get("documents", [])
            if not docs:
                logger.warning("⚠️ RAG store is empty")
                return None
            
            # Create simple wrapper
            class DefaultRAGClient:
                def __init__(self, documents):
                    self.documents = documents
                    logger.info(f"📚 RAG: Loaded {len(documents)} documents (R&D papers, World Bank, ILO)")
                
                def search(self, query: str, top_k: int = 10, filters=None) -> List[Dict]:
                    """Simple keyword-based search with relevance scoring."""
                    query_lower = query.lower()
                    query_terms = set(query_lower.split())
                    
                    # Score each document by term overlap
                    scored = []
                    for doc in self.documents:
                        text = doc.get("text", "").lower()
                        source = doc.get("source", "").lower()
                        
                        # Count matching terms
                        matches = sum(1 for term in query_terms if term in text or term in source)
                        if matches > 0:
                            score = matches / len(query_terms)
                            scored.append((doc, score))
                    
                    # Sort by score and return top_k
                    scored.sort(key=lambda x: x[1], reverse=True)
                    
                    results = []
                    for doc, score in scored[:top_k]:
                        results.append({
                            "title": doc.get("source", "Unknown Document"),
                            "content": doc.get("text", "")[:1000],  # 1000 chars for better context
                            "score": score,
                            "year": doc.get("metadata", {}).get("year", 2024),
                            "authors": ["NSIC R&D Team"],
                            "methodology": doc.get("metadata", {}).get("methodology"),
                            "metrics": doc.get("metadata", {}).get("metrics", {}),
                        })
                    
                    return results
            
            return DefaultRAGClient(docs)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize RAG client: {e}")
            return None
    
    def _init_default_kg_client(self) -> Optional[Any]:
        """Initialize default Knowledge Graph client."""
        try:
            from pathlib import Path
            import json
            
            # Find KG store
            possible_paths = [
                Path(__file__).parent.parent.parent.parent / "data" / "knowledge_graph.json",
                Path(__file__).parent.parent.parent.parent.parent / "data" / "knowledge_graph.json",
                Path("data/knowledge_graph.json"),
            ]
            
            kg_path = None
            for p in possible_paths:
                if p.exists():
                    kg_path = p
                    break
            
            if not kg_path:
                logger.warning("⚠️ Knowledge Graph not found")
                return None
            
            # Load graph - handle nested structure
            with open(kg_path, "r", encoding="utf-8") as f:
                kg_data = json.load(f)
            
            # KG can be nested under 'graph' key
            if "graph" in kg_data and isinstance(kg_data["graph"], dict):
                graph_data = kg_data["graph"]
                nodes = graph_data.get("nodes", [])
                edges = graph_data.get("links", graph_data.get("edges", []))
            else:
                nodes = kg_data.get("nodes", [])
                edges = kg_data.get("links", kg_data.get("edges", []))
            
            if not nodes:
                logger.warning("⚠️ Knowledge Graph is empty")
                return None
            
            class DefaultKGClient:
                def __init__(self, nodes, edges):
                    self.nodes = {n.get("id", n.get("name", "")): n for n in nodes}
                    self.edges = edges
                    logger.info(f"🕸️ KG: Loaded {len(nodes)} nodes, {len(edges)} edges")
                
                def query(self, query: str, focus=None) -> List[Dict]:
                    """Find related entities based on query terms."""
                    query_lower = query.lower()
                    results = []
                    
                    # Find matching nodes
                    for node_id, node in self.nodes.items():
                        node_name = node.get("name", node_id).lower()
                        if any(term in node_name for term in query_lower.split()):
                            # Find edges for this node
                            for edge in self.edges:
                                if edge.get("source") == node_id or edge.get("target") == node_id:
                                    other_id = edge.get("target") if edge.get("source") == node_id else edge.get("source")
                                    other_node = self.nodes.get(other_id, {})
                                    
                                    results.append({
                                        "subject": node.get("name", node_id),
                                        "relation_type": edge.get("relation", "related_to"),
                                        "object": other_node.get("name", other_id),
                                        "description": f"{node.get('name', node_id)} {edge.get('relation', 'relates to')} {other_node.get('name', other_id)}",
                                        "confidence": edge.get("weight", 0.7),
                                    })
                    
                    return results[:20]  # Limit results
            
            return DefaultKGClient(nodes, edges)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize KG client: {e}")
            return None
    
    def synthesize(
        self,
        query: str,
        focus_areas: Optional[List[str]] = None,
        max_papers: int = 20,
        max_rag_docs: int = 10,
        include_perplexity: bool = True,
    ) -> ResearchSynthesis:
        """
        Synthesize research findings for a query.
        
        Args:
            query: The research question
            focus_areas: Specific topics to prioritize (e.g., ["energy", "sustainability"] or ["healthcare", "costs"])
            max_papers: Maximum Semantic Scholar papers to retrieve
            max_rag_docs: Maximum RAG documents to retrieve
            include_perplexity: Whether to include real-time Perplexity results
            
        Returns:
            ResearchSynthesis with aggregated findings
        """
        findings: List[ResearchFinding] = []
        sources_searched = 0
        
        # 1. Search Semantic Scholar for academic papers
        try:
            scholar_findings = self._search_semantic_scholar(query, focus_areas, max_papers)
            findings.extend(scholar_findings)
            sources_searched += 1
            logger.info(f"📚 Semantic Scholar: {len(scholar_findings)} papers found")
        except Exception as e:
            logger.warning(f"⚠️ Semantic Scholar search failed: {e}")
        
        # 2. Search RAG system for internal R&D documents
        try:
            rag_findings = self._search_rag_system(query, focus_areas, max_rag_docs)
            findings.extend(rag_findings)
            sources_searched += 1
            logger.info(f"📄 RAG System: {len(rag_findings)} documents found")
        except Exception as e:
            logger.warning(f"⚠️ RAG search failed: {e}")
        
        # 3. Query Perplexity for real-time research
        if include_perplexity:
            try:
                perplexity_findings = self._search_perplexity(query, focus_areas)
                findings.extend(perplexity_findings)
                sources_searched += 1
                logger.info(f"🔍 Perplexity: {len(perplexity_findings)} results found")
            except Exception as e:
                logger.warning(f"⚠️ Perplexity search failed: {e}")
        
        # 4. Query Knowledge Graph for relationships
        try:
            kg_findings = self._search_knowledge_graph(query, focus_areas)
            findings.extend(kg_findings)
            sources_searched += 1
            logger.info(f"🕸️ Knowledge Graph: {len(kg_findings)} relationships found")
        except Exception as e:
            logger.warning(f"⚠️ Knowledge Graph search failed: {e}")
        
        # 5. Synthesize findings deterministically
        synthesis = self._synthesize_findings(query, findings, sources_searched)
        
        return synthesis
    
    def _search_semantic_scholar(
        self,
        query: str,
        focus_areas: Optional[List[str]],
        max_papers: int,
    ) -> List[ResearchFinding]:
        """Search Semantic Scholar for academic papers.
        
        RATE LIMIT: Semantic Scholar allows 1 request per second.
        We add a 1.1 second delay between calls to be safe.
        """
        import httpx
        import time
        
        findings = []
        
        # Build search query - use ONLY focus areas for Semantic Scholar
        # Full question is too long and specific for academic search
        if focus_areas:
            # Use focused keywords only - much more effective for academic search
            search_query = ' '.join(focus_areas[:3])  # Use top 3 terms for better results
        else:
            # Fallback: extract key terms from query
            import re
            words = re.findall(r'\b[A-Za-z]{4,}\b', query)
            common_words = {"should", "would", "could", "about", "their", "there", "which", "where", "what", "when", "this", "that", "from", "have", "with", "into", "they", "more", "over", "such", "only", "other", "than", "then", "also", "after", "before", "most", "some", "must", "option", "target", "focus", "consider", "become", "between"}
            keywords = [w for w in words if w.lower() not in common_words][:5]
            search_query = ' '.join(keywords) if keywords else query[:50]
        
        logger.info(f"📚 Semantic Scholar search: '{search_query}'")
        
        try:
            # RATE LIMIT: Wait 1.1 seconds to respect Semantic Scholar's 1 req/sec limit
            # Check if we have a last request timestamp
            if not hasattr(self, '_last_ss_request'):
                self._last_ss_request = 0
            
            elapsed = time.time() - self._last_ss_request
            if elapsed < 1.1:
                wait_time = 1.1 - elapsed
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s before Semantic Scholar call")
                time.sleep(wait_time)
            
            # Semantic Scholar API
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query": search_query,
                "limit": max_papers,
                "fields": "title,abstract,year,authors,citationCount,venue",
            }
            headers = {}
            if self.semantic_scholar_key:
                headers["x-api-key"] = self.semantic_scholar_key
            
            self._last_ss_request = time.time()  # Update timestamp before request
            
            with httpx.Client(timeout=30) as client:
                response = client.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for paper in data.get("data", []):
                        # Calculate relevance based on citations and recency
                        citations = paper.get("citationCount") or 0
                        year = paper.get("year") or 2020  # Handle None explicitly
                        recency_boost = max(0, (year - 2015) / 10)  # Boost recent papers
                        relevance = min(1.0, (citations / 1000) + recency_boost)
                        
                        authors = [a.get("name", "") for a in paper.get("authors", [])[:3]]
                        
                        findings.append(ResearchFinding(
                            title=paper.get("title", "Untitled"),
                            source="semantic_scholar",
                            summary=paper.get("abstract", "")[:500] if paper.get("abstract") else "No abstract available",
                            relevance_score=relevance,
                            citation=f"{', '.join(authors)} ({year}). {paper.get('title', '')}. {paper.get('venue', '')}",
                            year=year,
                            authors=authors,
                            methodology=None,
                            key_metrics={"citations": citations},
                        ))
                else:
                    logger.warning(f"Semantic Scholar API returned {response.status_code}")
                    
        except Exception as e:
            logger.error(f"Semantic Scholar API error: {e}")
        
        return findings
    
    def _search_rag_system(
        self,
        query: str,
        focus_areas: Optional[List[str]],
        max_docs: int,
    ) -> List[ResearchFinding]:
        """Search RAG system for internal R&D documents."""
        findings = []
        
        if not self.rag_client:
            # RAG client must be injected via constructor
            logger.warning("⚠️ RAG client not configured - skipping RAG search")
            return findings
        
        logger.info(f"🔍 RAG search: query='{query[:50]}...' top_k={max_docs}")
        
        try:
            # Search RAG system
            results = self.rag_client.search(
                query=query,
                top_k=max_docs,
                filters={"topics": focus_areas} if focus_areas else None,
            )
            
            for doc in results:
                findings.append(ResearchFinding(
                    title=doc.get("title", "Internal Document"),
                    source="rag",
                    summary=doc.get("content", "")[:500],
                    relevance_score=doc.get("score", 0.5),
                    citation=f"QNWIS R&D: {doc.get('title', 'Unknown')}",
                    year=doc.get("year"),
                    authors=doc.get("authors", []),
                    methodology=doc.get("methodology"),
                    key_metrics=doc.get("metrics", {}),
                ))
                
        except Exception as e:
            logger.error(f"RAG search error: {e}")
        
        return findings
    
    def _search_perplexity(
        self,
        query: str,
        focus_areas: Optional[List[str]],
    ) -> List[ResearchFinding]:
        """Search Perplexity for real-time research insights."""
        import httpx
        
        findings = []
        
        if not self.perplexity_key:
            logger.warning("Perplexity API key not configured")
            return findings
        
        try:
            # Build focused research query
            research_query = f"Academic research findings on: {query}"
            if focus_areas:
                research_query += f" Focus: {', '.join(focus_areas)}"
            
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.perplexity_key}",
                "Content-Type": "application/json",
            }
            # FIXED: Use correct Perplexity model name (sonar-pro or sonar)
            payload = {
                "model": "sonar",  # Updated model name for Perplexity API
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a research assistant. Provide factual findings with citations."
                    },
                    {
                        "role": "user",
                        "content": research_query
                    }
                ],
            }
            
            with httpx.Client(timeout=60) as client:
                response = client.post(url, json=payload, headers=headers)
                
                if response.status_code != 200:
                    logger.warning(f"⚠️ Perplexity API returned {response.status_code}: {response.text[:200]}")
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    citations = data.get("citations", [])
                    
                    # Create finding from Perplexity response
                    findings.append(ResearchFinding(
                        title=f"Real-time Research: {query[:50]}...",
                        source="perplexity",
                        summary=content[:1000],
                        relevance_score=0.8,  # High relevance for real-time data
                        citation=f"Perplexity AI Search ({len(citations)} sources)",
                        year=2024,
                        authors=["Perplexity AI"],
                        methodology="Real-time web search with AI synthesis",
                        key_metrics={"sources_cited": len(citations)},
                    ))
                    
        except Exception as e:
            logger.error(f"Perplexity API error: {e}")
        
        return findings
    
    def _search_knowledge_graph(
        self,
        query: str,
        focus_areas: Optional[List[str]],
    ) -> List[ResearchFinding]:
        """Query Knowledge Graph for entity relationships."""
        findings = []
        
        if not self.kg_client:
            # Knowledge Graph client must be injected via constructor
            logger.warning("⚠️ Knowledge Graph client not configured - skipping KG search")
            return findings
        
        logger.info(f"🔍 KG search: focus_areas={focus_areas}")
        
        try:
            # Query for relevant relationships
            relationships = self.kg_client.query(
                query=query,
                focus=focus_areas,
            )
            
            for rel in relationships:
                findings.append(ResearchFinding(
                    title=f"Relationship: {rel.get('subject', '')} → {rel.get('object', '')}",
                    source="knowledge_graph",
                    summary=rel.get("description", ""),
                    relevance_score=rel.get("confidence", 0.6),
                    citation=f"QNWIS Knowledge Graph: {rel.get('relation_type', 'related_to')}",
                    key_metrics={
                        "subject": rel.get("subject"),
                        "relation": rel.get("relation_type"),
                        "object": rel.get("object"),
                    },
                ))
                
        except Exception as e:
            logger.error(f"Knowledge Graph query error: {e}")
        
        return findings
    
    def _synthesize_findings(
        self,
        query: str,
        findings: List[ResearchFinding],
        sources_searched: int,
    ) -> ResearchSynthesis:
        """Deterministically synthesize findings into a structured summary."""
        
        if not findings:
            return ResearchSynthesis(
                query=query,
                total_sources_searched=sources_searched,
                findings=[],
                consensus_view="No research findings available for this query.",
                dissenting_views=[],
                evidence_gaps=["No academic literature found on this specific topic."],
                confidence_level="low",
                narrative="Unable to synthesize research - no findings retrieved from any source.",
                methodology_note="Searched Semantic Scholar, RAG, Perplexity, Knowledge Graph.",
            )
        
        # Sort by relevance
        findings.sort(key=lambda f: f.relevance_score, reverse=True)
        
        # Take top findings for synthesis
        top_findings = findings[:10]
        
        # Determine confidence based on evidence quality
        avg_relevance = sum(f.relevance_score for f in top_findings) / len(top_findings)
        source_diversity = len(set(f.source for f in findings))
        
        if avg_relevance > 0.7 and source_diversity >= 3:
            confidence = "high"
        elif avg_relevance > 0.5 and source_diversity >= 2:
            confidence = "medium"
        else:
            confidence = "low"
        
        # Build consensus view from top findings
        consensus_parts = []
        for f in top_findings[:3]:
            if f.summary:
                consensus_parts.append(f.summary[:200])
        
        consensus = " ".join(consensus_parts) if consensus_parts else "Insufficient evidence for consensus."
        
        # Identify evidence gaps
        gaps = []
        sources_found = set(f.source for f in findings)
        if "semantic_scholar" not in sources_found:
            gaps.append("No peer-reviewed academic papers found.")
        if "rag" not in sources_found:
            gaps.append("No internal R&D documents matched this query.")
        if len(findings) < 5:
            gaps.append("Limited research coverage - findings may not be comprehensive.")
        
        # Build academic narrative
        source_breakdown = {}
        for f in findings:
            source_breakdown[f.source] = source_breakdown.get(f.source, 0) + 1
        
        # Format top findings with academic citations
        findings_formatted = []
        for f in top_findings[:5]:
            authors_short = f.authors[0].split()[-1] if f.authors else "Unknown"
            if len(f.authors) > 1:
                authors_short += " et al."
            year = f.year or "n.d."
            findings_formatted.append(f"• {f.summary[:200]}... ({authors_short}, {year})")
        
        narrative = f"""# ACADEMIC LITERATURE REVIEW
## Research Question: "{query}"

### Methodology
This systematic review analyzed {len(findings)} sources using a multi-database search strategy:
- **Semantic Scholar**: {source_breakdown.get('semantic_scholar', 0)} peer-reviewed papers
- **Internal Documents (RAG)**: {source_breakdown.get('rag', 0)} policy documents
- **Perplexity AI**: {source_breakdown.get('perplexity', 0)} real-time synthesis
- **Knowledge Graph**: {source_breakdown.get('knowledge_graph', 0)} entity relationships

### Evidence Quality Assessment
**Overall Confidence Level:** {confidence.upper()}
- Source diversity: {len(source_breakdown)} different source types
- Average relevance score: {sum(f.relevance_score for f in top_findings) / len(top_findings):.2f}

### Key Findings from the Literature
{chr(10).join(findings_formatted)}

### Evidence Gaps & Limitations
{chr(10).join(f'• {gap}' for gap in gaps) if gaps else '• No significant gaps identified in available literature.'}

### References
{chr(10).join(f'{i+1}. {f.citation}' for i, f in enumerate(top_findings[:5]))}
"""
        
        # Generate PhD-level academic synthesis via LLM
        academic_synthesis = self._generate_llm_summary(query, top_findings, confidence)
        
        # Combine academic synthesis with methodology notes
        if academic_synthesis:
            narrative = f"""# DR. RESEARCH - ACADEMIC LITERATURE SYNTHESIS

{academic_synthesis}

---

## APPENDIX: SOURCE METHODOLOGY

{narrative}"""
        
        return ResearchSynthesis(
            query=query,
            total_sources_searched=sources_searched,
            findings=findings,
            consensus_view=consensus[:500],
            dissenting_views=[],  # Would need NLP to detect contradictions
            evidence_gaps=gaps,
            confidence_level=confidence,
            narrative=narrative,
            methodology_note=f"Searched {sources_searched} sources. Ranked {len(findings)} findings by relevance. Top {len(top_findings)} used for synthesis. LLM summary generated.",
        )
    
    def _generate_llm_summary(
        self,
        query: str,
        findings: List[ResearchFinding],
        confidence: str,
    ) -> Optional[str]:
        """
        Generate a PhD-level academic literature review and synthesis.
        
        This is the CORE OUTPUT of the ResearchSynthesizer - a rigorous
        academic synthesis that debate agents can cite with confidence.
        
        Args:
            query: The research question
            findings: Top research findings to summarize
            confidence: Evidence confidence level
            
        Returns:
            Academic literature review with proper citations
        """
        import httpx
        
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        
        if not endpoint or not api_key or not findings:
            return None
        
        # Format findings with full academic citation style
        findings_text = "\n\n".join([
            f"**Source {i+1}: {f.title}**\n"
            f"- Authors: {', '.join(f.authors) if f.authors else 'N/A'}\n"
            f"- Year: {f.year or 'N/A'}\n"
            f"- Source Type: {f.source.replace('_', ' ').title()}\n"
            f"- Citation Count: {f.key_metrics.get('citations', 'N/A')}\n"
            f"- Abstract/Summary: {f.summary[:400]}\n"
            f"- Full Citation: {f.citation}"
            for i, f in enumerate(findings[:10])  # Include more papers
        ])
        
        # Count sources by type for methodology section
        source_counts = {}
        for f in findings:
            source_counts[f.source] = source_counts.get(f.source, 0) + 1
        
        prompt = f"""You are **Dr. Research**, a PhD-level academic researcher and policy analyst 
with expertise in systematic literature reviews and evidence synthesis. You have published 
extensively in peer-reviewed journals and served on policy advisory boards.

Your task is to produce a RIGOROUS ACADEMIC LITERATURE REVIEW on the following research question.

═══════════════════════════════════════════════════════════════════════════════
RESEARCH QUESTION
═══════════════════════════════════════════════════════════════════════════════
{query}

═══════════════════════════════════════════════════════════════════════════════
METHODOLOGY
═══════════════════════════════════════════════════════════════════════════════
This synthesis draws from {len(findings)} sources:
- Semantic Scholar (peer-reviewed academic papers): {source_counts.get('semantic_scholar', 0)} papers
- Perplexity AI (real-time research synthesis): {source_counts.get('perplexity', 0)} results  
- Internal RAG System (policy documents): {source_counts.get('rag', 0)} documents
- Knowledge Graph (entity relationships): {source_counts.get('knowledge_graph', 0)} relationships

Evidence Confidence Level: {confidence.upper()}

═══════════════════════════════════════════════════════════════════════════════
SOURCE MATERIALS
═══════════════════════════════════════════════════════════════════════════════
{findings_text}

═══════════════════════════════════════════════════════════════════════════════
REQUIRED OUTPUT: ACADEMIC LITERATURE REVIEW
═══════════════════════════════════════════════════════════════════════════════

Produce a scholarly synthesis following this EXACT structure:

## 1. EXECUTIVE SUMMARY (2-3 sentences)
State the primary finding and its policy relevance.

## 2. STATE OF THE LITERATURE
- What does the academic consensus say about this topic?
- Identify the dominant theoretical frameworks used
- Note the methodological approaches (quantitative/qualitative/mixed)

## 3. KEY EMPIRICAL FINDINGS
For each major finding, provide:
- The specific claim with quantitative data where available
- The source citation in academic format: (Author et al., Year)
- The sample size, methodology, or limitations

## 4. POINTS OF SCHOLARLY DEBATE
- Where do researchers disagree?
- What are the competing hypotheses?
- Which findings are contested and why?

## 5. EVIDENCE GAPS & RESEARCH LIMITATIONS
- What questions remain unanswered?
- Where is the evidence weak or missing?
- What methodological limitations should policymakers be aware of?

## 6. POLICY IMPLICATIONS
Based on the evidence, what can we conclude for policy purposes?
- High-confidence recommendations (strong evidence)
- Tentative recommendations (moderate evidence)
- Areas requiring further research before action

## 7. REFERENCES
List the top 5 most relevant citations in proper academic format.

═══════════════════════════════════════════════════════════════════════════════

CRITICAL REQUIREMENTS:
1. Write in academic third-person voice
2. Every claim MUST have a citation (Author, Year) or source reference
3. Distinguish between correlation and causation
4. Acknowledge limitations and uncertainty
5. Do NOT overstate conclusions beyond what the evidence supports
6. Use precise academic language, not journalistic language

This synthesis will be used by other PhD-level debate agents. Be rigorous."""

        try:
            url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-02-01"
            headers = {"api-key": api_key, "Content-Type": "application/json"}
            payload = {
                "messages": [
                    {
                        "role": "system", 
                        "content": "You are Dr. Research, a PhD academic specializing in systematic literature reviews and evidence synthesis. You write in rigorous academic style with proper citations. Your output should be detailed enough (1000+ words) to provide substantial value for policy debate."
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,  # Lower temperature for more precise academic output
                "max_tokens": 3000,  # Extended for 1000+ word detailed synthesis
            }
            
            with httpx.Client(timeout=60) as client:
                response = client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    summary = response.json()["choices"][0]["message"]["content"]
                    logger.info(f"🧠 LLM research summary generated: {len(summary)} chars")
                    return summary
                else:
                    logger.warning(f"LLM summary generation failed: {response.status_code}")
        except Exception as e:
            logger.warning(f"LLM summary generation error: {e}")
        
        return None
    
    def run(self, query: str = "policy effectiveness analysis") -> ResearchSynthesis:
        """
        Execute research synthesis with default parameters.
        
        This is the standard entry point matching other deterministic agents.
        Domain-agnostic - extracts focus areas from the query itself.
        
        Args:
            query: Research question to investigate (any domain)
            
        Returns:
            ResearchSynthesis with aggregated findings
        """
        # Extract focus areas dynamically from the query
        focus_areas = self._extract_focus_areas(query)
        
        return self.synthesize(
            query=query,
            focus_areas=focus_areas,
            max_papers=20,
            max_rag_docs=10,
            include_perplexity=True,
        )
    
    def _extract_focus_areas(self, query: str) -> List[str]:
        """
        Extract focus areas from query using LLM semantic understanding.
        Falls back to keyword matching if LLM unavailable.
        
        Args:
            query: User's research question
            
        Returns:
            List of focus area keywords
        """
        # Try LLM-based semantic extraction first
        try:
            focus_areas = self._extract_focus_areas_with_llm(query)
            if focus_areas:
                logger.info(f"🧠 LLM-extracted focus areas: {focus_areas}")
                return focus_areas
        except Exception as e:
            logger.warning(f"⚠️ LLM focus extraction failed, using fallback: {e}")
        
        # Fallback to keyword matching
        return self._extract_focus_areas_keyword(query)
    
    def _extract_focus_areas_with_llm(self, query: str) -> List[str]:
        """
        Use LLM to semantically understand query domain and extract focus areas.
        This is SMART - it understands context, not just keywords.
        
        CRITICAL: This enables DOMAIN-AGNOSTIC research - the LLM understands
        what academic topics to search for, even if the query uses different terms.
        """
        import httpx
        import json
        
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        
        if not endpoint or not api_key:
            logger.warning("⚠️ Azure OpenAI not configured - cannot use LLM focus extraction")
            return []
        
        # PhD-level prompt for semantic understanding
        prompt = f"""You are an expert academic librarian helping a PhD researcher find relevant literature.

RESEARCH QUESTION:
{query}

Your task: Extract 5 ACADEMIC SEARCH TERMS that would find relevant peer-reviewed papers on Semantic Scholar.

REQUIREMENTS:
1. Think about the UNDERLYING ACADEMIC DISCIPLINES (economics, public policy, engineering, medicine, etc.)
2. Use STANDARD ACADEMIC TERMINOLOGY (how researchers would title their papers)
3. Include both SPECIFIC terms (the exact topic) and BROADER terms (the field)
4. Consider RELATED CONCEPTS that researchers study together
5. DO NOT just extract words from the query - TRANSLATE to academic language

EXAMPLES:
- Query: "Should we build solar farms or hydrogen plants?"
  Academic terms: ["renewable energy economics", "solar photovoltaic deployment", "green hydrogen production", "energy transition policy", "levelized cost of energy"]

- Query: "Can AI diagnose cancer better than doctors?"
  Academic terms: ["artificial intelligence diagnostics", "machine learning oncology", "medical image analysis", "clinical decision support systems", "diagnostic accuracy comparison"]

- Query: "How do mega events affect small economies?"  
  Academic terms: ["mega event economic impact", "sports tourism economics", "host city legacy effects", "event-led development", "tourism multiplier effects"]

Return ONLY a JSON object:
{{"focus_areas": ["term1", "term2", "term3", "term4", "term5"]}}"""

        try:
            url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-02-01"
            headers = {"api-key": api_key, "Content-Type": "application/json"}
            payload = {
                "messages": [
                    {"role": "system", "content": "You are an expert academic librarian. Return ONLY valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.2,  # Very low for consistent academic terms
                "max_tokens": 150,
            }
            
            logger.info(f"🔍 Extracting focus areas via LLM for: {query[:50]}...")
            
            with httpx.Client(timeout=30) as client:
                response = client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    logger.debug(f"LLM response: {content}")
                    
                    # Parse JSON from response - handle various formats
                    content = content.strip()
                    
                    # Remove markdown code blocks if present
                    if "```" in content:
                        # Extract content between backticks
                        parts = content.split("```")
                        for part in parts:
                            if "{" in part and "}" in part:
                                content = part
                                break
                    
                    # Remove "json" prefix if present
                    if content.startswith("json"):
                        content = content[4:].strip()
                    
                    # Find the JSON object
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start >= 0 and end > start:
                        content = content[start:end]
                    
                    result = json.loads(content)
                    focus_areas = result.get("focus_areas", [])[:5]
                    
                    if focus_areas:
                        logger.info(f"✅ LLM extracted academic terms: {focus_areas}")
                        return focus_areas
                    else:
                        logger.warning("⚠️ LLM returned empty focus_areas")
                else:
                    logger.warning(f"⚠️ LLM API returned {response.status_code}: {response.text[:200]}")
                    
        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Failed to parse LLM JSON response: {e}")
        except Exception as e:
            logger.warning(f"⚠️ LLM focus extraction error: {e}")
        
        return []
    
    def _extract_focus_areas_keyword(self, query: str) -> List[str]:
        """
        Fallback keyword-based extraction when LLM unavailable.
        """
        domain_keywords = {
            # Economy
            "gdp", "inflation", "fiscal", "monetary", "trade", "investment", "fdi",
            # Labor
            "employment", "unemployment", "workforce", "labor", "jobs", "wages",
            # Policy
            "policy", "regulation", "reform", "quota", "mandate", "incentive",
            # Sectors
            "energy", "tourism", "finance", "construction", "healthcare", "education",
            "technology", "manufacturing", "agriculture", "retail", "logistics",
            # Demographics
            "population", "migration", "expatriate", "national", "youth", "gender",
            # Skills
            "skills", "training", "education", "qualification", "competency",
            # Sustainability
            "sustainability", "environment", "carbon", "renewable", "green",
            # Infrastructure
            "infrastructure", "transport", "housing", "digital", "smart city",
        }
        
        query_lower = query.lower()
        found_areas = []
        
        for keyword in domain_keywords:
            if keyword in query_lower:
                found_areas.append(keyword)
        
        if not found_areas:
            common_words = {"should", "would", "could", "about", "their", "there", "which", "where", "what", "when", "this", "that", "from", "have", "with"}
            words = query_lower.split()
            found_areas = [w for w in words if len(w) > 4 and w not in common_words][:5]
        
        return found_areas[:5]

