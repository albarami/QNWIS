"""
Comparative Case Study Extraction - Using Real Data Sources

Fetches real case studies from:
1. Semantic Scholar - Academic papers with case study analysis
2. Perplexity - Real-time web intelligence on implementations
3. Brave Search - News and reports on policy outcomes

Domain-agnostic: automatically identifies relevant cases based on query topic.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
import re

logger = logging.getLogger(__name__)


async def extract_case_studies(query: str, max_cases: int = 4) -> List[Dict[str, Any]]:
    """
    Extract real case studies from multiple data sources.
    
    Uses:
    1. Perplexity for comprehensive case study search
    2. Semantic Scholar for academic case studies
    3. Brave for recent implementations and outcomes
    
    Domain-agnostic: works for any query topic.
    """
    all_cases = []
    
    # Extract key topics from query for case study search
    case_study_queries = _generate_case_study_queries(query)
    logger.info(f"🔍 Searching for case studies with {len(case_study_queries)} queries")
    
    try:
        # 1. Perplexity - Best for comprehensive case studies with real data
        perplexity_cases = await _fetch_perplexity_case_studies(query, case_study_queries)
        all_cases.extend(perplexity_cases)
        logger.info(f"  Perplexity: {len(perplexity_cases)} case studies")
        
        # 2. Semantic Scholar - Academic case studies
        academic_cases = await _fetch_academic_case_studies(query, case_study_queries)
        all_cases.extend(academic_cases)
        logger.info(f"  Semantic Scholar: {len(academic_cases)} academic cases")
        
        # 3. Brave - Recent implementations
        news_cases = await _fetch_brave_case_studies(query, case_study_queries)
        all_cases.extend(news_cases)
        logger.info(f"  Brave: {len(news_cases)} recent cases")
        
    except Exception as e:
        logger.error(f"Case study extraction error: {e}")
    
    # Deduplicate and rank
    unique_cases = _deduplicate_cases(all_cases)
    ranked_cases = _rank_cases_by_relevance(unique_cases, query)
    
    logger.info(f"📚 Total unique case studies: {len(ranked_cases)}")
    return ranked_cases[:max_cases]


def _generate_case_study_queries(query: str) -> List[str]:
    """
    Generate search queries for finding case studies from AUTHORITATIVE SOURCES.
    
    Targets:
    - Harvard Business Review / HBS Cases
    - McKinsey Global Institute
    - World Bank Policy Research
    - IMF Working Papers
    - OECD Economic Surveys
    - Brookings Institution
    - Academic journals (Journal of Economic Perspectives, etc.)
    """
    # Extract key topics from query
    topics = _extract_topics(query)
    
    queries = []
    
    # AUTHORITATIVE SOURCE PATTERNS - These target high-quality case studies
    authoritative_patterns = [
        # Harvard
        "site:hbr.org {topic} case study",
        "Harvard Business Review {topic} implementation",
        # McKinsey
        "site:mckinsey.com {topic} case study",
        "McKinsey Global Institute {topic} transformation",
        # World Bank
        "World Bank policy research {topic} implementation",
        "World Bank {topic} country case study",
        # IMF
        "IMF working paper {topic} policy lessons",
        # OECD
        "OECD economic survey {topic} reform",
        "OECD {topic} country comparison",
        # Brookings
        "Brookings Institution {topic} analysis",
        # Academic
        "Journal of Economic Perspectives {topic}",
        "Journal of Development Economics {topic} case",
    ]
    
    for topic in topics[:2]:  # Top 2 topics
        for pattern in authoritative_patterns[:8]:  # 8 patterns per topic
            queries.append(pattern.format(topic=topic))
    
    # COUNTRY-SPECIFIC CASE STUDY QUERIES
    benchmark_countries = [
        ("Singapore", "tech hub transformation skills policy"),
        ("Ireland", "FDI technology sector growth"),
        ("UAE Dubai", "economic diversification tourism"),
        ("South Korea", "industrial policy workforce development"),
        ("Estonia", "digital government e-governance"),
        ("Norway", "sovereign wealth fund management"),
        ("Israel", "startup ecosystem innovation"),
        ("Germany", "apprenticeship workforce training"),
    ]
    
    for country, context in benchmark_countries[:4]:
        for topic in topics[:2]:
            queries.append(f"{country} {topic} case study {context}")
    
    # SPECIFIC METRIC QUERIES - Get numbers not just narratives
    metric_patterns = [
        "{topic} investment billion outcomes GDP impact",
        "{topic} jobs created employment statistics",
        "{topic} success rate implementation timeline",
        "{topic} ROI return economic multiplier",
    ]
    
    for topic in topics[:2]:
        for pattern in metric_patterns:
            queries.append(pattern.format(topic=topic))
    
    return queries[:20]  # Up to 20 queries for comprehensive coverage


def _extract_topics(query: str) -> List[str]:
    """
    Extract key topics from query for case study search.
    Domain-agnostic extraction.
    """
    # Common topic keywords to extract
    topic_indicators = {
        "technology": ["ai", "technology", "tech", "digital", "innovation", "automation", "ict"],
        "tourism": ["tourism", "hospitality", "destination", "visitors", "travel"],
        "workforce": ["workforce", "employment", "labor", "skills", "nationalization", "jobs"],
        "investment": ["investment", "fund", "capital", "billion", "allocation"],
        "diversification": ["diversification", "economic", "non-oil", "gdp"],
        "infrastructure": ["infrastructure", "development", "construction"],
        "education": ["education", "training", "university", "skills"],
        "healthcare": ["health", "healthcare", "medical"],
        "financial": ["financial", "banking", "monetary", "fiscal"],
        "energy": ["energy", "oil", "gas", "renewable", "sustainability"],
    }
    
    query_lower = query.lower()
    found_topics = []
    
    for topic, keywords in topic_indicators.items():
        if any(kw in query_lower for kw in keywords):
            found_topics.append(topic)
    
    # If no specific topics found, use generic
    if not found_topics:
        found_topics = ["economic policy", "national development"]
    
    return found_topics


async def _fetch_perplexity_case_studies(
    query: str, 
    search_queries: List[str]
) -> List[Dict[str, Any]]:
    """
    Fetch case studies from Perplexity Pro Search.
    Best source for comprehensive, real-time case study data.
    
    Targets authoritative sources:
    - Harvard Business Review / HBS Cases
    - McKinsey Global Institute Reports
    - World Bank Policy Research Papers
    - IMF Working Papers
    - OECD Economic Surveys
    """
    cases = []
    
    try:
        from src.qnwis.orchestration.perplexity_comprehensive import (
            extract_perplexity_comprehensive
        )
        
        # Build case study specific query targeting AUTHORITATIVE SOURCES
        case_query = f"""Find 3-4 detailed CASE STUDIES with SPECIFIC DATA from authoritative sources about:
{query[:200]}

REQUIRED SOURCES (prioritize these):
- Harvard Business Review or Harvard Business School cases
- McKinsey Global Institute reports
- World Bank Policy Research Working Papers
- IMF Working Papers or Country Reports
- OECD Economic Surveys
- Brookings Institution analysis
- Academic journals (Journal of Economic Perspectives, etc.)

FOR EACH CASE STUDY, YOU MUST PROVIDE:
1. COUNTRY and SPECIFIC PROGRAM NAME (e.g., "Singapore SkillsFuture Program")
2. INVESTMENT AMOUNT with YEAR (e.g., "$1.2 billion from 2015-2020")
3. QUANTIFIED OUTCOMES:
   - Jobs created: exact number
   - GDP impact: percentage or dollar amount
   - Timeline: how long to achieve results
   - National participation rate if relevant
4. SUCCESS FACTORS: 3-4 specific factors with evidence
5. CHALLENGES: what went wrong or required adjustment
6. SOURCE CITATION: exact report name, author, year, URL if available

DO NOT provide vague generalizations. Every claim needs a NUMBER and a SOURCE.
Example format:
"Singapore invested $1 billion annually in SkillsFuture (2015-2020), training 660,000 workers 
with 85% completion rate. Source: SkillsFuture Singapore Annual Report 2020"
"""
        
        facts = await extract_perplexity_comprehensive(case_query)
        
        # Parse facts into case study format
        for fact in facts:
            case = _parse_perplexity_to_case(fact)
            if case:
                cases.append(case)
                
    except ImportError:
        logger.warning("Perplexity extractor not available")
    except Exception as e:
        logger.error(f"Perplexity case study extraction failed: {e}")
    
    return cases


async def _fetch_academic_case_studies(
    query: str,
    search_queries: List[str]
) -> List[Dict[str, Any]]:
    """
    Fetch academic case studies from Semantic Scholar.
    
    Targets peer-reviewed policy research:
    - Journal of Economic Perspectives
    - Quarterly Journal of Economics
    - Journal of Development Economics
    - World Development
    - Journal of Policy Analysis and Management
    - American Economic Review
    """
    cases = []
    topics = _extract_topics(query)
    
    try:
        from src.qnwis.orchestration.semantic_scholar_comprehensive import (
            extract_semantic_scholar_comprehensive
        )
        
        # Multiple academic search queries for comprehensive coverage
        academic_queries = [
            f"case study {topics[0] if topics else 'policy'} implementation evaluation",
            f"comparative analysis {topics[0] if topics else 'economic'} policy outcomes",
            f"policy evaluation {topics[0] if topics else 'development'} success factors",
            f"country comparison {topics[0] if topics else 'reform'} lessons learned",
        ]
        
        for aq in academic_queries[:3]:
            try:
                papers = await extract_semantic_scholar_comprehensive(aq)
                
                # Filter for high-quality case study papers
                for paper in papers:
                    if _is_case_study_paper(paper):
                        # Prioritize highly cited papers
                        citations = paper.get("citations", 0)
                        if citations >= 10 or _is_case_study_paper(paper):
                            case = _parse_paper_to_case(paper)
                            if case:
                                cases.append(case)
            except Exception as e:
                logger.debug(f"Academic query failed: {e}")
                continue
                    
    except ImportError:
        logger.warning("Semantic Scholar extractor not available")
    except Exception as e:
        logger.error(f"Semantic Scholar case study extraction failed: {e}")
    
    # Sort by citations and return top cases
    cases.sort(key=lambda x: x.get("citations", 0), reverse=True)
    return cases[:5]


async def _fetch_brave_case_studies(
    query: str,
    search_queries: List[str]
) -> List[Dict[str, Any]]:
    """
    Fetch recent case studies from Brave Search.
    Best source for recent implementations and news.
    """
    cases = []
    
    try:
        from src.qnwis.orchestration.brave_comprehensive import (
            extract_brave_comprehensive
        )
        
        # Search for recent implementations
        for sq in search_queries[:3]:
            results = await extract_brave_comprehensive(sq)
            
            for result in results:
                case = _parse_brave_to_case(result)
                if case:
                    cases.append(case)
                    
    except ImportError:
        logger.warning("Brave extractor not available")
    except Exception as e:
        logger.error(f"Brave case study extraction failed: {e}")
    
    return cases[:5]  # Limit news cases


def _is_case_study_paper(paper: Dict[str, Any]) -> bool:
    """Check if paper is a case study analysis."""
    title = paper.get("metric", paper.get("title", "")).lower()
    abstract = paper.get("value", paper.get("abstract", "")).lower()
    citations = paper.get("citations", paper.get("citationCount", 0)) or 0
    
    # Must have case study indicators in title or abstract
    case_indicators = [
        "case study", "implementation", "policy evaluation",
        "lessons learned", "comparative analysis", "country experience",
        "economic impact", "success factors", "benchmark",
        "singapore", "ireland", "uae", "dubai", "korea", "germany",
        "norway", "estonia", "israel", "sovereign wealth", "fdi",
        "technology hub", "tourism", "digital transformation"
    ]
    
    has_indicator = any(ind in title or ind in abstract for ind in case_indicators)
    
    # Prefer highly cited papers (more credible)
    is_well_cited = citations >= 5
    
    # Exclude meta-analysis papers about research itself
    exclude_patterns = [
        "systematic review of", "meta-analysis", "literature review",
        "natural language processing", "machine learning model",
        "deep learning", "neural network", "classification algorithm"
    ]
    is_excluded = any(ex in title or ex in abstract for ex in exclude_patterns)
    
    return has_indicator and not is_excluded and (is_well_cited or has_indicator)


def _parse_perplexity_to_case(fact: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse Perplexity fact into case study format."""
    try:
        # Perplexity stores content in 'text' field, title in 'title'
        content = fact.get("text", fact.get("value", fact.get("content", "")))
        source = fact.get("source", "Perplexity AI")
        url = fact.get("url", "")
        metric = fact.get("title", fact.get("metric", ""))
        
        # Add URL to source if available
        if url:
            source = f"{source} ({url[:50]}...)" if len(url) > 50 else f"{source} ({url})"
        
        # Skip very short content
        if len(content) < 100:
            return None
        
        # Check if this looks like a case study or policy analysis
        case_indicators = [
            "case study", "implementation", "policy", "invest", 
            "billion", "million", "program", "initiative", "reform",
            "success", "growth", "gdp", "jobs", "employment"
        ]
        content_lower = content.lower()
        if not any(ind in content_lower for ind in case_indicators):
            return None
        
        # Extract country/region - more lenient now
        country = _extract_country_from_text(content)
        
        # Extract numbers
        numbers = _extract_numbers_from_text(content)
        
        # Create title from metric or first sentence
        if metric and len(metric) > 10:
            title = metric[:80]
        else:
            # Use first sentence as title
            first_sentence = content.split('.')[0][:80] if '.' in content else content[:80]
            title = first_sentence
        
        return {
            "id": f"PPLX-{hash(content) % 10000:04d}",
            "title": title,
            "country": country or "Multiple/Various",
            "source": source,
            "source_type": "perplexity",
            "content": content[:1000],
            "extracted_numbers": numbers,
            "investment": numbers.get("investment", "See source"),
            "outcomes": {
                "description": content[:500],
                "jobs": numbers.get("jobs", "See source"),
                "gdp_impact": numbers.get("gdp", "See source"),
                "source": source
            },
            "lessons": _extract_lessons_from_text(content),
            "relevance_score": 0.7 if country else 0.5  # Lower score if no country
        }
    except Exception as e:
        logger.debug(f"Failed to parse Perplexity case: {e}")
        return None


def _parse_paper_to_case(paper: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse Semantic Scholar paper into case study format."""
    try:
        title = paper.get("metric", paper.get("title", ""))
        abstract = paper.get("value", paper.get("abstract", ""))
        year = paper.get("year", "")
        citations = paper.get("citations", 0)
        source = paper.get("source", "Semantic Scholar")
        
        # Extract country from title/abstract
        country = _extract_country_from_text(f"{title} {abstract}")
        
        return {
            "id": f"SS-{hash(title) % 10000:04d}",
            "title": title[:100],
            "country": country or "Multiple countries",
            "source": source,
            "source_type": "academic",
            "year": year,
            "citations": citations,
            "content": abstract[:800],
            "outcomes": {
                "description": abstract[:400],
                "source": f"{source} ({year})"
            },
            "lessons": _extract_lessons_from_text(abstract),
            "relevance_score": min(1.0, 0.5 + (citations / 1000)) if citations else 0.6
        }
    except Exception as e:
        logger.debug(f"Failed to parse paper case: {e}")
        return None


def _parse_brave_to_case(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse Brave search result into case study format."""
    try:
        title = result.get("metric", result.get("title", ""))
        snippet = result.get("value", result.get("snippet", ""))
        url = result.get("url", "")
        source = result.get("source", url)
        
        # Only include if it looks like a case study
        case_keywords = ["case study", "implementation", "policy", "success", "lessons", "example"]
        if not any(kw in title.lower() or kw in snippet.lower() for kw in case_keywords):
            return None
        
        country = _extract_country_from_text(f"{title} {snippet}")
        
        return {
            "id": f"BRAVE-{hash(url) % 10000:04d}",
            "title": title[:100],
            "country": country or "See source",
            "source": source,
            "source_type": "news",
            "url": url,
            "content": snippet[:500],
            "outcomes": {
                "description": snippet[:300],
                "source": source
            },
            "lessons": _extract_lessons_from_text(snippet),
            "relevance_score": 0.6
        }
    except Exception as e:
        logger.debug(f"Failed to parse Brave case: {e}")
        return None


def _extract_country_from_text(text: str) -> Optional[str]:
    """Extract country name from text."""
    countries = [
        "Singapore", "UAE", "United Arab Emirates", "Dubai", "Abu Dhabi",
        "Ireland", "Israel", "Estonia", "South Korea", "Korea",
        "Norway", "Denmark", "Finland", "Sweden",
        "Germany", "France", "UK", "United Kingdom", "Japan",
        "China", "India", "Malaysia", "Thailand", "Vietnam",
        "Saudi Arabia", "Qatar", "Kuwait", "Bahrain", "Oman",
        "Chile", "Brazil", "Mexico", "Canada", "Australia",
        "New Zealand", "Iceland", "Switzerland", "Netherlands",
    ]
    
    text_lower = text.lower()
    for country in countries:
        if country.lower() in text_lower:
            return country
    return None


def _extract_numbers_from_text(text: str) -> Dict[str, str]:
    """Extract quantified metrics from text."""
    numbers = {}
    
    # Investment amounts
    investment_pattern = r'\$[\d,.]+\s*(?:billion|million|B|M)'
    inv_match = re.search(investment_pattern, text, re.IGNORECASE)
    if inv_match:
        numbers["investment"] = inv_match.group()
    
    # Jobs created
    jobs_pattern = r'([\d,]+)\s*(?:jobs|workers|employees)'
    jobs_match = re.search(jobs_pattern, text, re.IGNORECASE)
    if jobs_match:
        numbers["jobs"] = jobs_match.group()
    
    # GDP impact
    gdp_pattern = r'(\d+(?:\.\d+)?)\s*%\s*(?:of GDP|GDP|growth)'
    gdp_match = re.search(gdp_pattern, text, re.IGNORECASE)
    if gdp_match:
        numbers["gdp"] = gdp_match.group()
    
    # Percentages
    pct_pattern = r'(\d+(?:\.\d+)?)\s*%'
    pct_matches = re.findall(pct_pattern, text)
    if pct_matches:
        numbers["percentages"] = pct_matches[:5]
    
    return numbers


def _extract_lessons_from_text(text: str) -> List[str]:
    """Extract key lessons from case study text."""
    lessons = []
    
    # Look for lesson indicators
    lesson_patterns = [
        r'(?:key )?(?:lesson|takeaway|insight)[s]?[:\s]+([^.]+)',
        r'(?:success(?:ful)?|effective) (?:because|due to|factor)[s]?[:\s]+([^.]+)',
        r'(?:recommend|suggest|advise)[s]?[:\s]+([^.]+)',
        r'(?:best practice|critical factor)[s]?[:\s]+([^.]+)',
    ]
    
    for pattern in lesson_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        lessons.extend(matches[:2])
    
    return lessons[:5]


def _deduplicate_cases(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate case studies based on content similarity."""
    seen_countries = set()
    unique = []
    
    for case in cases:
        country = case.get("country", "")
        title = case.get("title", "")
        
        # Simple dedup by country+title prefix
        key = f"{country}:{title[:30]}"
        if key not in seen_countries:
            seen_countries.add(key)
            unique.append(case)
    
    return unique


def _rank_cases_by_relevance(
    cases: List[Dict[str, Any]], 
    query: str
) -> List[Dict[str, Any]]:
    """Rank cases by relevance to query."""
    query_lower = query.lower()
    
    for case in cases:
        score = case.get("relevance_score", 0.5)
        
        # Boost for academic sources
        if case.get("source_type") == "academic":
            score += 0.1
        
        # Boost for matching country in query
        country = case.get("country", "").lower()
        if country in query_lower:
            score += 0.2
        
        # Boost for extracted numbers
        if case.get("extracted_numbers"):
            score += len(case["extracted_numbers"]) * 0.05
        
        case["final_score"] = min(1.0, score)
    
    return sorted(cases, key=lambda x: x.get("final_score", 0), reverse=True)


def format_case_studies_for_synthesis(cases: List[Dict[str, Any]]) -> str:
    """
    Format case studies for inclusion in synthesis prompt.
    Includes source citations for each case.
    """
    if not cases:
        return """
⚠️ NO CASE STUDIES FOUND
Unable to fetch comparable case studies from data sources.
Synthesis should note: "International benchmarking data not available for this analysis."
"""
    
    output = []
    for i, case in enumerate(cases, 1):
        source_type = case.get("source_type", "web")
        source_label = {
            "perplexity": "🌐 Web Intelligence",
            "academic": "📚 Academic Paper",
            "news": "📰 News/Report"
        }.get(source_type, "📄 Source")
        
        output.append(f"""
**CASE {i}: {case.get('title', 'Case Study')}** [{case.get('id', f'CASE-{i}')}]
├── **Country:** {case.get('country', 'See source')}
├── **Source:** {source_label} - {case.get('source', 'N/A')}
├── **Investment:** {case.get('investment', 'See source')}
├── **Outcomes:**
│   └── {case.get('outcomes', {}).get('description', 'See source')[:300]}...
│   └── Source: {case.get('outcomes', {}).get('source', 'N/A')}
└── **Key Lessons:** {', '.join(case.get('lessons', ['See source content'])[:3])}
""")
    
    return "\n".join(output)


async def get_case_study_section(query: str) -> str:
    """
    Get the complete case study section for synthesis.
    Main entry point - fetches real data from APIs.
    """
    cases = await extract_case_studies(query)
    formatted = format_case_studies_for_synthesis(cases)
    
    section = f"""
═══════════════════════════════════════════════════════════════════════════════
              COMPARATIVE CASE STUDIES (FROM REAL DATA SOURCES)
═══════════════════════════════════════════════════════════════════════════════
Sources: Perplexity AI, Semantic Scholar, Brave Search
Cases found: {len(cases)}

{formatted}

⚠️ CITATION INSTRUCTIONS:
- Cite as [Case {i}, source_type] where i=1-{len(cases)}
- All data comes from external sources - cite the original source
- If numbers seem inconsistent, note the source discrepancy
═══════════════════════════════════════════════════════════════════════════════
"""
    return section


# Synchronous wrapper for synthesis node
def get_case_study_section_sync(query: str) -> str:
    """Synchronous wrapper for get_case_study_section."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If we're in an async context, create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, 
                    get_case_study_section(query)
                )
                return future.result(timeout=30)
        else:
            return loop.run_until_complete(get_case_study_section(query))
    except Exception as e:
        logger.error(f"Case study sync wrapper failed: {e}")
        return f"""
═══════════════════════════════════════════════════════════════════════════════
              COMPARATIVE CASE STUDIES
═══════════════════════════════════════════════════════════════════════════════
⚠️ Case study extraction failed: {e}
The synthesis should proceed without international benchmarking data.
═══════════════════════════════════════════════════════════════════════════════
"""
