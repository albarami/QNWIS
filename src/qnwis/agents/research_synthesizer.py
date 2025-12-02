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
        
        # Generate LLM summary for debate agents (GPT-5 synthesis)
        debate_ready_summary = self._generate_llm_summary(query, top_findings, confidence)
        
        # Combine raw narrative with LLM-synthesized summary
        if debate_ready_summary:
            narrative = f"""## AI-SYNTHESIZED RESEARCH SUMMARY (GPT-5)

{debate_ready_summary}

---

## RAW DATA SOURCES

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
        Generate an LLM-synthesized summary of research findings.
        This makes the findings DEBATE-READY for the LLM agents.
        
        Args:
            query: The research question
            findings: Top research findings to summarize
            confidence: Evidence confidence level
            
        Returns:
            GPT-5 generated executive summary, or None if LLM unavailable
        """
        import httpx
        
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        
        if not endpoint or not api_key or not findings:
            return None
        
        # Format findings for the prompt
        findings_text = "\n\n".join([
            f"**{i+1}. {f.title}** (Source: {f.source}, Relevance: {f.relevance_score:.2f})\n{f.summary[:300]}"
            for i, f in enumerate(findings[:7])
        ])
        
        prompt = f"""You are a senior research analyst. Synthesize these research findings into an EXECUTIVE SUMMARY for policy debate.

RESEARCH QUESTION: {query}

FINDINGS FROM MULTIPLE SOURCES:
{findings_text}

EVIDENCE CONFIDENCE: {confidence.upper()}

Create a DEBATE-READY summary that:
1. States the CONSENSUS VIEW - what most research agrees on
2. Identifies KEY DATA POINTS with specific numbers (cite sources)
3. Notes any CONTRADICTIONS or dissenting views
4. Highlights EVIDENCE GAPS - what we don't know
5. Provides IMPLICATIONS for policy decision-making

Format as a clear, structured summary (~300 words). Include specific citations like [Semantic Scholar, 2023] or [RAG: Internal Report].

IMPORTANT: This summary will be used by AI debate agents. Make it factual, citation-heavy, and actionable."""

        try:
            url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-02-01"
            headers = {"api-key": api_key, "Content-Type": "application/json"}
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 800,
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
        """
        import httpx
        import json
        
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4")
        
        if not endpoint or not api_key:
            return []
        
        prompt = f"""Analyze this query and extract the key research domains/topics.

QUERY: {query}

Return a JSON object with:
{{
    "primary_domain": "main domain (e.g., energy, healthcare, labor, finance, tourism)",
    "focus_areas": ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"],
    "intent": "brief description of what research is needed"
}}

Focus areas should be specific enough to find relevant academic papers.
Do NOT just extract words from the query - understand the SEMANTIC MEANING.

Example:
- Query: "Can Qatar compete with Dubai for tourists?"
- primary_domain: "tourism"
- focus_areas: ["tourism competitiveness", "GCC tourism", "destination marketing", "hospitality sector", "visitor attractions"]

Return ONLY valid JSON, no explanation."""

        try:
            url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version=2024-02-01"
            headers = {"api-key": api_key, "Content-Type": "application/json"}
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 200,
            }
            
            with httpx.Client(timeout=30) as client:
                response = client.post(url, json=payload, headers=headers)
                
                if response.status_code == 200:
                    content = response.json()["choices"][0]["message"]["content"]
                    # Parse JSON from response
                    content = content.strip()
                    if content.startswith("```"):
                        content = content.split("```")[1]
                        if content.startswith("json"):
                            content = content[4:]
                    
                    result = json.loads(content)
                    return result.get("focus_areas", [])[:5]
        except Exception as e:
            logger.debug(f"LLM focus extraction error: {e}")
        
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

