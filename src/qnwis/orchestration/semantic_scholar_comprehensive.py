"""
COMPREHENSIVE Semantic Scholar Extraction

Semantic Scholar has 214 MILLION papers. We should extract 50-100+ relevant papers,
not just 1-3.

RATE LIMIT: 1 request per second (100 requests/5 min = 1/sec avg)

Strategy:
1. Multiple search queries (variations)
2. Pagination (get multiple pages)
3. Related papers (recommendations)
4. Filter by relevance and year
5. Rate limiting with 1-second delays
"""

import logging
import asyncio
import time
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Rate limiting: Semantic Scholar allows ~100 requests per 5 minutes = 1 req/sec avg
RATE_LIMIT_SECONDS = 1.1  # Slightly over 1 second to be safe
_last_request_time = 0


async def _rate_limited_delay():
    """Ensure we respect the 1 request/second rate limit."""
    global _last_request_time
    current_time = time.time()
    elapsed = current_time - _last_request_time
    
    if elapsed < RATE_LIMIT_SECONDS:
        wait_time = RATE_LIMIT_SECONDS - elapsed
        logger.debug(f"  Rate limit: waiting {wait_time:.2f}s")
        await asyncio.sleep(wait_time)
    
    _last_request_time = time.time()


async def extract_semantic_scholar_comprehensive(query: str) -> List[Dict[str, Any]]:
    """
    Extract 50-100+ relevant papers from Semantic Scholar's 214M database.
    
    Uses multiple strategies:
    1. Multiple query variations
    2. Pagination (multiple pages per query)
    3. Related paper recommendations
    4. Filtering by year and citation count
    
    Note: Uses synchronous client wrapped in async context.
    Rate limit: 1 request per second (handled with delays).
    """
    all_papers = []
    seen_paper_ids = set()
    
    try:
        # Import the synchronous client functions
        from src.data.apis.semantic_scholar import search_papers, get_paper_recommendations
        
        # Generate multiple query variations for broader coverage
        query_variations = _generate_query_variations(query)
        logger.info(f"  Searching Semantic Scholar with {len(query_variations)} query variations")
        
        # Search with each query variation (with rate limiting)
        for i, q in enumerate(query_variations):
            try:
                # Rate limit between queries
                await _rate_limited_delay()
                
                logger.debug(f"  Query {i+1}/{len(query_variations)}: {q[:40]}...")
                
                # Search using synchronous client (limit=50 per query)
                papers = search_papers(
                    query=q,
                    year_filter="2018-",
                    limit=50,
                    fields="title,year,abstract,citationCount,authors,url,paperId,venue,fieldsOfStudy"
                )
                
                for paper in papers:
                    paper_id = paper.get("paperId", "")
                    if paper_id and paper_id not in seen_paper_ids:
                        # Filter out irrelevant CS/NLP meta-papers
                        if _is_relevant_paper(paper, query):
                            seen_paper_ids.add(paper_id)
                            all_papers.append(_format_paper_as_fact(paper))
                
                logger.debug(f"    Found {len(papers)} papers")
                
                # Stop early if we have enough papers
                if len(all_papers) >= 100:
                    logger.info(f"  Reached 100 papers, stopping query expansion")
                    break
                
            except Exception as e:
                logger.warning(f"  Query '{q[:30]}...' failed: {e}")
                continue
        
        # Get recommendations for top-cited papers found (with rate limiting)
        if all_papers and len(all_papers) < 100:
            logger.info(f"  Getting recommendations for top-cited papers...")
            top_papers = sorted(
                [p for p in all_papers if p.get("citation_count", 0) > 0],
                key=lambda x: x.get("citation_count", 0),
                reverse=True
            )[:3]  # Reduced to 3 to save API calls
            
            for paper in top_papers:
                paper_id = paper.get("paper_id", "")
                if paper_id:
                    try:
                        # Rate limit before each recommendation request
                        await _rate_limited_delay()
                        
                        # Get recommendations using synchronous client
                        recommendations = get_paper_recommendations(
                            positive_paper_ids=[paper_id],
                            limit=20,
                            fields="title,year,citationCount,authors,url,paperId"
                        )
                        
                        added = 0
                        for rec in recommendations:
                            rec_id = rec.get("paperId", "")
                            if rec_id and rec_id not in seen_paper_ids:
                                seen_paper_ids.add(rec_id)
                                all_papers.append(_format_paper_as_fact(rec))
                                added += 1
                        
                        if added > 0:
                            logger.debug(f"    Added {added} recommendations from paper {paper_id[:8]}...")
                            
                    except Exception as e:
                        logger.warning(f"  Recommendations for {paper_id} failed: {e}")
        
        # Sort by relevance (citation count + year)
        all_papers = _rank_papers(all_papers)
        
        logger.info(f"  Semantic Scholar TOTAL: {len(all_papers)} unique papers")
        
    except ImportError as e:
        logger.warning(f"Semantic Scholar client not available: {e}")
    except RuntimeError as e:
        # API key not configured
        if "API_KEY" in str(e):
            logger.warning(f"Semantic Scholar API key not configured: {e}")
        else:
            logger.error(f"Semantic Scholar runtime error: {e}")
    except Exception as e:
        logger.error(f"Semantic Scholar comprehensive extraction error: {e}")
    
    return all_papers


def _is_relevant_paper(paper: Dict[str, Any], original_query: str) -> bool:
    """
    Filter out irrelevant papers - especially CS/NLP meta-papers.
    
    When searching for "Qatar labor policy", we don't want papers about
    "Knowledge Graph construction" or "BERT for text classification".
    """
    title = (paper.get("title") or "").lower()
    abstract = (paper.get("abstract") or "").lower()
    fields = paper.get("fieldsOfStudy") or []
    
    # =================================================================
    # EXCLUDE: Computer Science meta-papers (about techniques, not policy)
    # =================================================================
    cs_meta_keywords = [
        # NLP/ML technique papers
        "knowledge graph", "rdf", "ontology", "semantic web", "linked data",
        "transformer", "bert", "gpt", "language model", "neural network",
        "deep learning", "machine learning algorithm", "text classification",
        "named entity recognition", "relation extraction", "text mining",
        "information retrieval", "document clustering", "word embedding",
        # Software/systems papers  
        "repository", "github", "codebase", "software engineering",
        "api design", "database schema", "query optimization",
        # Pure methodology papers
        "benchmark", "evaluation metric", "dataset", "annotation",
    ]
    
    # Check if title contains CS meta-keywords
    cs_keyword_count = sum(1 for kw in cs_meta_keywords if kw in title)
    if cs_keyword_count >= 2:
        return False  # Likely a CS methodology paper
    
    # Check fieldsOfStudy - reject pure CS papers
    if fields:
        field_names = [f.lower() if isinstance(f, str) else f.get("category", "").lower() for f in fields]
        pure_cs_fields = {"computer science", "mathematics", "engineering"}
        policy_fields = {"economics", "political science", "sociology", "business", 
                        "environmental science", "geography", "medicine", "law"}
        
        # If ALL fields are CS/Math and NONE are policy-related, reject
        if all(f in pure_cs_fields for f in field_names) and not any(f in policy_fields for f in field_names):
            # Unless it's specifically about the query domain
            query_lower = original_query.lower()
            domain_keywords = ["labor", "employment", "workforce", "economy", "policy", 
                              "qatar", "gcc", "tourism", "energy", "trade"]
            if not any(kw in title or kw in abstract for kw in domain_keywords):
                return False
    
    # =================================================================
    # INCLUDE: Papers with domain relevance
    # =================================================================
    # Bonus: papers mentioning specific regions/policies are more likely relevant
    relevance_keywords = [
        "qatar", "gcc", "gulf", "middle east", "saudi", "uae", "bahrain", "kuwait", "oman",
        "labor market", "workforce", "employment", "unemployment", "nationalization",
        "economic policy", "fiscal policy", "monetary policy", "trade policy",
        "tourism sector", "energy sector", "diversification", "vision 2030"
    ]
    
    if any(kw in title or kw in abstract for kw in relevance_keywords):
        return True  # Definitely relevant
    
    # Default: include if not filtered out
    return True


def _generate_query_variations(query: str) -> List[str]:
    """
    Generate multiple query variations for broader coverage.
    """
    variations = [
        query,  # Original query
    ]
    
    # Add domain-specific variations
    domains = {
        "labor": ["labor market", "employment", "workforce", "unemployment", "jobs"],
        "economy": ["economic", "GDP", "fiscal", "monetary policy", "growth"],
        "energy": ["oil", "gas", "LNG", "renewable", "petroleum"],
        "education": ["skills", "training", "university", "STEM", "graduates"],
        "trade": ["exports", "imports", "commerce", "trade balance"],
        "health": ["healthcare", "medical", "hospital", "public health"],
        "tourism": ["tourist", "hospitality", "visitors", "travel"],
        "technology": ["digital", "AI", "automation", "ICT", "innovation"],
        "nationalization": ["Qatarization", "localization", "workforce nationalization"],
    }
    
    query_lower = query.lower()
    
    # Add variations based on detected domains
    for domain, keywords in domains.items():
        if any(kw in query_lower for kw in keywords):
            for kw in keywords[:3]:
                variations.append(f"{kw} {query[:50]}")
                variations.append(f"Qatar {kw} policy")
                variations.append(f"GCC {kw} research")
    
    # Add Qatar-specific variations
    variations.append(f"Qatar {query[:50]}")
    variations.append(f"Gulf {query[:50]}")
    variations.append(f"Middle East {query[:50]}")
    
    # Add policy-focused variations
    variations.append(f"{query[:50]} policy analysis")
    variations.append(f"{query[:50]} economic impact")
    
    # Deduplicate
    seen = set()
    unique_variations = []
    for v in variations:
        v_lower = v.lower().strip()
        if v_lower not in seen and len(v_lower) > 5:
            seen.add(v_lower)
            unique_variations.append(v)
    
    return unique_variations[:15]  # Max 15 variations


def _format_paper_as_fact(paper: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format a paper as a fact for the extraction system.
    """
    authors = paper.get("authors", [])
    author_names = ", ".join([a.get("name", "") for a in authors[:3]]) if authors else "Unknown"
    if len(authors) > 3:
        author_names += " et al."
    
    return {
        "metric": "academic_paper",
        "paper_id": paper.get("paperId", ""),
        "title": paper.get("title", ""),
        "abstract": paper.get("abstract", "")[:500] if paper.get("abstract") else "",
        "authors": author_names,
        "year": paper.get("year"),
        "citation_count": paper.get("citationCount", 0),
        "venue": paper.get("venue", ""),
        "url": paper.get("url", ""),
        "fields": paper.get("fieldsOfStudy", []),
        "source": "Semantic Scholar (214M papers)",
        "source_priority": 85,
        "confidence": min(0.9, 0.5 + (paper.get("citationCount", 0) / 1000))
    }


def _rank_papers(papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank papers by relevance (citations + recency).
    """
    def score(paper):
        citation_score = min(paper.get("citation_count", 0) / 100, 5)  # Max 5 points
        year = paper.get("year") or 2020
        recency_score = max(0, (year - 2015) / 2)  # More recent = higher score
        return citation_score + recency_score
    
    return sorted(papers, key=score, reverse=True)
