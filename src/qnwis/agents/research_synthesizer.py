"""
Research Synthesizer Agent - Deterministic research evidence aggregator.

Aggregates findings from:
- Semantic Scholar (214M academic papers)
- Perplexity (real-time research/news)
- RAG System (56 internal R&D documents)
- Knowledge Graph (entity relationships, policy impacts)

Produces a structured research summary BEFORE the debate, so LLM agents
have academic backing for their arguments.
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
            rag_client: Client for RAG document retrieval
            knowledge_graph_client: Client for knowledge graph queries
        """
        self.semantic_scholar_key = semantic_scholar_api_key or os.getenv("SEMANTIC_SCHOLAR_API_KEY")
        self.perplexity_key = perplexity_api_key or os.getenv("PERPLEXITY_API_KEY")
        self.rag_client = rag_client
        self.kg_client = knowledge_graph_client
        
        logger.info("✅ ResearchSynthesizerAgent initialized")
    
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
        """Search Semantic Scholar for academic papers."""
        import httpx
        
        findings = []
        
        # Build search query
        search_query = query
        if focus_areas:
            search_query = f"{query} {' '.join(focus_areas)}"
        
        # Keep query as-is without domain-specific additions
        # The focus_areas parameter handles topic specificity
        
        try:
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
            
            with httpx.Client(timeout=30) as client:
                response = client.get(url, params=params, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    for paper in data.get("data", []):
                        # Calculate relevance based on citations and recency
                        citations = paper.get("citationCount", 0)
                        year = paper.get("year", 2020)
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
            # Fallback: Try to import and use the RAG system
            try:
                from ..data.rag import RAGClient
                self.rag_client = RAGClient()
            except ImportError:
                logger.warning("RAG client not available")
                return findings
        
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
            payload = {
                "model": "llama-3.1-sonar-small-128k-online",
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
                "return_citations": True,
            }
            
            with httpx.Client(timeout=60) as client:
                response = client.post(url, json=payload, headers=headers)
                
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
            # Fallback: Try to import knowledge graph client
            try:
                from ..data.knowledge_graph import KnowledgeGraphClient
                self.kg_client = KnowledgeGraphClient()
            except ImportError:
                logger.warning("Knowledge Graph client not available")
                return findings
        
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
        
        # Build narrative
        source_breakdown = {}
        for f in findings:
            source_breakdown[f.source] = source_breakdown.get(f.source, 0) + 1
        
        narrative = f"""Research Synthesis for: "{query}"

**Sources Analyzed:**
- Semantic Scholar: {source_breakdown.get('semantic_scholar', 0)} papers
- Internal R&D (RAG): {source_breakdown.get('rag', 0)} documents
- Perplexity Real-time: {source_breakdown.get('perplexity', 0)} results
- Knowledge Graph: {source_breakdown.get('knowledge_graph', 0)} relationships

**Confidence Level:** {confidence.upper()}

**Key Findings:**
{chr(10).join(f'• {f.title}: {f.summary[:150]}...' for f in top_findings[:5])}

**Evidence Gaps:**
{chr(10).join(f'• {gap}' for gap in gaps) if gaps else '• No significant gaps identified.'}
"""
        
        return ResearchSynthesis(
            query=query,
            total_sources_searched=sources_searched,
            findings=findings,
            consensus_view=consensus[:500],
            dissenting_views=[],  # Would need NLP to detect contradictions
            evidence_gaps=gaps,
            confidence_level=confidence,
            narrative=narrative,
            methodology_note=f"Searched {sources_searched} sources. Ranked {len(findings)} findings by relevance. Top {len(top_findings)} used for synthesis.",
        )
    
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
        Extract focus areas from query to guide research.
        Domain-agnostic keyword extraction.
        
        Args:
            query: User's research question
            
        Returns:
            List of focus area keywords
        """
        # Common domain keywords to look for
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
        
        # If no specific keywords found, extract nouns from query
        if not found_areas:
            # Simple extraction: take significant words (>4 chars, not common)
            common_words = {"should", "would", "could", "about", "their", "there", "which", "where", "what", "when", "this", "that", "from", "have", "with"}
            words = query_lower.split()
            found_areas = [w for w in words if len(w) > 4 and w not in common_words][:5]
        
        return found_areas[:5]  # Limit to 5 focus areas

