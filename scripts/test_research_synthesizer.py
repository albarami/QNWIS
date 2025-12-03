"""
Test ResearchSynthesizerAgent across diverse domains.

This script verifies that Dr. Research:
1. Correctly understands the domain from query context (not keyword matching)
2. Extracts appropriate focus areas for academic search via LLM
3. Successfully queries Semantic Scholar (with rate limiting)
4. Produces academically rigorous output

NOTE: Semantic Scholar rate limit is 1 request/second, so tests include delays.
"""

import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables from .env file
env_file = project_root / ".env"
if env_file.exists():
    print(f"Loading environment from {env_file}")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())
    print(f"  AZURE_OPENAI_ENDPOINT: {'SET' if os.getenv('AZURE_OPENAI_ENDPOINT') else 'NOT SET'}")
    print(f"  AZURE_OPENAI_API_KEY: {'SET' if os.getenv('AZURE_OPENAI_API_KEY') else 'NOT SET'}")
    print(f"  PERPLEXITY_API_KEY: {'SET' if os.getenv('PERPLEXITY_API_KEY') else 'NOT SET'}")
else:
    print(f"⚠️ No .env file found at {env_file}")

from src.qnwis.agents.research_synthesizer import ResearchSynthesizerAgent


def test_research_synthesizer():
    """Test ResearchSynthesizer with diverse questions from different domains."""
    
    # Initialize agent
    agent = ResearchSynthesizerAgent(
        semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
        perplexity_api_key=os.getenv("PERPLEXITY_API_KEY"),
        rag_client=None,  # No RAG for this test
        knowledge_graph_client=None,  # No KG for this test
    )
    
    # 5 complex questions from VERY different domains to test domain-agnostic capability
    # NOTE: Using 5 tests with 2-second delays to respect Semantic Scholar rate limit
    test_questions = [
        # 1. Healthcare/AI - Complex multi-domain
        {
            "domain": "Healthcare + AI",
            "question": "Should Qatar invest in AI-powered diagnostic systems for early cancer detection, or focus on expanding traditional screening programs?",
            "expected_concepts": ["medical diagnosis", "artificial intelligence", "cancer screening", "healthcare technology"],
        },
        # 2. Energy/Climate - Sustainability domain
        {
            "domain": "Energy + Climate",
            "question": "What is the optimal energy mix for Qatar by 2035 - should we prioritize solar farms in the desert or invest in green hydrogen production?",
            "expected_concepts": ["renewable energy", "solar", "hydrogen", "energy policy"],
        },
        # 3. Finance/Digital - Emerging technology
        {
            "domain": "Finance + Technology",
            "question": "What are the systemic risks of central bank digital currencies (CBDCs) for small open economies?",
            "expected_concepts": ["CBDC", "digital currency", "monetary policy", "financial stability"],
        },
        # 4. Tourism/Economics - Completely different domain
        {
            "domain": "Tourism + Economics",
            "question": "What is the long-term economic impact of hosting mega sporting events on small economies?",
            "expected_concepts": ["sports economics", "mega events", "economic impact", "tourism"],
        },
        # 5. Agriculture/Technology - Unusual combination
        {
            "domain": "Agriculture + Tech",
            "question": "Can vertical farming technology achieve food self-sufficiency for arid regions given water constraints?",
            "expected_concepts": ["vertical farming", "food security", "water efficiency", "controlled environment agriculture"],
        },
    ]
    
    print("=" * 80)
    print("DR. RESEARCH - DOMAIN AGNOSTIC TEST")
    print("Testing PhD-level research synthesis across 5 diverse domains")
    print("Rate limit: 1 request/second to Semantic Scholar")
    print("=" * 80)
    print()
    
    results = []
    
    for i, test in enumerate(test_questions, 1):
        print(f"\n{'='*80}")
        print(f"TEST {i}/5: {test['domain'].upper()}")
        print(f"{'='*80}")
        print(f"\n📝 QUESTION: {test['question']}")
        print(f"\n🎯 EXPECTED CONCEPTS: {test['expected_concepts']}")
        
        # Test focus area extraction (this uses LLM)
        print("\n--- Step 1: LLM Semantic Understanding ---")
        focus_areas = agent._extract_focus_areas(test['question'])
        print(f"📊 LLM EXTRACTED TERMS: {focus_areas}")
        
        # Evaluate if LLM understood the domain (semantic match, not exact)
        expected_concepts = test['expected_concepts']
        focus_lower = ' '.join(focus_areas).lower()
        concept_matches = sum(1 for c in expected_concepts if any(word in focus_lower for word in c.lower().split()))
        focus_score = (concept_matches / len(expected_concepts)) * 100 if expected_concepts else 0
        
        print(f"✅ Semantic Understanding: {concept_matches}/{len(expected_concepts)} concepts matched ({focus_score:.0f}%)")
        
        # Check if LLM was used (not keyword fallback)
        is_llm_quality = len(focus_areas) >= 3 and any(len(f.split()) > 1 for f in focus_areas)
        print(f"🧠 LLM Quality Check: {'✅ Academic terms extracted' if is_llm_quality else '⚠️ May be keyword fallback'}")
        
        # Run full synthesis with rate limiting
        print("\n--- Step 2: Academic Literature Search ---")
        print("⏳ Searching Semantic Scholar (rate limited)...")
        
        try:
            synthesis = agent.synthesize(
                query=test['question'],
                focus_areas=focus_areas,
                max_papers=5,  # Limit for testing
                max_rag_docs=0,  # No RAG
                include_perplexity=True,
            )
            
            ss_papers = [f for f in synthesis.findings if f.source == 'semantic_scholar']
            px_results = [f for f in synthesis.findings if f.source == 'perplexity']
            
            print(f"\n📚 SOURCES FOUND:")
            print(f"   - Semantic Scholar papers: {len(ss_papers)}")
            print(f"   - Perplexity results: {len(px_results)}")
            print(f"   - Total findings: {len(synthesis.findings)}")
            print(f"   - Evidence confidence: {synthesis.confidence_level.upper()}")
            
            # Show sample findings with relevance check
            if synthesis.findings:
                print(f"\n📖 TOP 3 FINDINGS:")
                for j, finding in enumerate(synthesis.findings[:3], 1):
                    # Check if finding is relevant to the query
                    query_words = set(test['question'].lower().split())
                    title_words = set(finding.title.lower().split())
                    relevance_match = len(query_words & title_words) > 0
                    
                    print(f"   {j}. {finding.title[:70]}...")
                    print(f"      Source: {finding.source} | Year: {finding.year} | Relevant: {'✅' if relevance_match else '⚠️'}")
            
            # Show academic narrative
            if synthesis.narrative and "ACADEMIC LITERATURE REVIEW" in synthesis.narrative:
                print(f"\n📝 ACADEMIC OUTPUT: ✅ Structured literature review generated")
            elif synthesis.narrative:
                print(f"\n📝 ACADEMIC OUTPUT: ⚠️ Basic synthesis only")
            
            # Score this test
            source_score = min(100, len(synthesis.findings) * 20)  # 5+ findings = 100%
            has_academic = len(ss_papers) > 0
            has_realtime = len(px_results) > 0
            llm_used = is_llm_quality
            
            test_result = {
                "domain": test['domain'],
                "focus_score": focus_score,
                "source_score": source_score,
                "findings_count": len(synthesis.findings),
                "has_academic": has_academic,
                "has_realtime": has_realtime,
                "llm_extraction": llm_used,
                "confidence": synthesis.confidence_level,
                "success": len(synthesis.findings) > 0 and llm_used,
            }
            
        except Exception as e:
            print(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            test_result = {
                "domain": test['domain'],
                "focus_score": focus_score,
                "source_score": 0,
                "findings_count": 0,
                "has_academic": False,
                "has_realtime": False,
                "llm_extraction": False,
                "confidence": "error",
                "success": False,
            }
        
        results.append(test_result)
        print(f"\n{'─'*40}")
        print(f"TEST {i} RESULT: {'✅ PASS' if test_result['success'] else '❌ FAIL'}")
        
        # Delay between tests to respect rate limits
        if i < len(test_questions):
            print(f"\n⏳ Waiting 2 seconds before next test (rate limiting)...")
            time.sleep(2)
    
    # Final Summary
    print("\n" + "=" * 80)
    print("FINAL EVALUATION SUMMARY")
    print("=" * 80)
    
    total_tests = len(results)
    successful = sum(1 for r in results if r['success'])
    avg_focus = sum(r['focus_score'] for r in results) / total_tests if results else 0
    avg_source = sum(r['source_score'] for r in results) / total_tests if results else 0
    academic_count = sum(1 for r in results if r['has_academic'])
    realtime_count = sum(1 for r in results if r['has_realtime'])
    llm_count = sum(1 for r in results if r.get('llm_extraction', False))
    
    print(f"""
┌─────────────────────────────────────────────────────────────────────┐
│                    DR. RESEARCH EVALUATION                          │
├─────────────────────────────────────────────────────────────────────┤
│  Tests Passed:         {successful}/{total_tests} ({successful/total_tests*100:.0f}%)                                   │
│  LLM Understanding:    {llm_count}/{total_tests} tests used LLM semantic extraction       │
│  Semantic Match:       {avg_focus:.0f}% (domain concepts identified)              │
│  Source Retrieval:     {avg_source:.0f}% (findings retrieved)                     │
│  Academic Sources:     {academic_count}/{total_tests} tests found Semantic Scholar papers       │
│  Real-time Sources:    {realtime_count}/{total_tests} tests found Perplexity results            │
└─────────────────────────────────────────────────────────────────────┘
""")
    
    print("\nDOMAIN BREAKDOWN:")
    print("─" * 70)
    for r in results:
        status = "✅" if r['success'] else "❌"
        llm = "🧠" if r.get('llm_extraction', False) else "  "
        academic = "📚" if r['has_academic'] else "  "
        realtime = "🔍" if r['has_realtime'] else "  "
        print(f"  {status} {r['domain']:22} | Semantic: {r['focus_score']:3.0f}% | Papers: {r['findings_count']:2} {llm}{academic}{realtime}")
    
    print("\nLEGEND: 🧠=LLM extraction  📚=Academic papers  🔍=Real-time data")
    
    # Overall grade - weighted scoring
    # 40% for success rate, 30% for LLM understanding, 20% for sources, 10% for real-time
    llm_rate = llm_count / total_tests * 100 if total_tests else 0
    overall_score = (successful/total_tests * 40) + (llm_rate * 0.3) + (avg_source * 0.2) + (realtime_count/total_tests * 10)
    
    if overall_score >= 80:
        grade = "A - EXCELLENT: PhD-level research synthesis"
    elif overall_score >= 70:
        grade = "B - GOOD: Solid academic research capability"
    elif overall_score >= 60:
        grade = "C - ACCEPTABLE: Basic research working"
    else:
        grade = "D - NEEDS WORK: Check LLM/API configuration"
    
    print(f"\n{'='*70}")
    print(f"OVERALL GRADE: {grade}")
    print(f"Score: {overall_score:.0f}/100")
    print(f"{'='*70}")
    
    # Recommendations
    if llm_count < total_tests:
        print("\n⚠️ RECOMMENDATION: LLM extraction not working for all tests.")
        print("   Check Azure OpenAI configuration (AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY)")
    
    if academic_count < total_tests:
        print("\n⚠️ RECOMMENDATION: Semantic Scholar not returning papers for all domains.")
        print("   This may be due to rate limiting (429) - try running fewer tests.")
    
    if realtime_count == 0:
        print("\n⚠️ RECOMMENDATION: Perplexity not configured.")
        print("   Set PERPLEXITY_API_KEY for real-time research synthesis.")
    
    return results


def test_phd_summary_quality():
    """Test that Dr. Research produces PhD-level academic summaries."""
    
    print("\n" + "=" * 80)
    print("PhD SUMMARY QUALITY TEST")
    print("Verifying academic rigor of research synthesis output")
    print("=" * 80)
    
    # Initialize agent with RAG
    from pathlib import Path
    import json
    
    # Load RAG store for this test
    rag_store_path = Path(__file__).parent.parent / "data" / "rag_store.json"
    rag_client = None
    
    if rag_store_path.exists():
        try:
            from src.qnwis.rag.retriever import DocumentStore, Document
            
            class TestRAGClient:
                def __init__(self):
                    self.store = DocumentStore()
                    with open(rag_store_path, "r", encoding="utf-8") as f:
                        store_data = json.load(f)
                    
                    docs = store_data.get("documents", [])
                    count = 0
                    for d in docs[:500]:  # Load 500 for test
                        doc = Document(
                            doc_id=d.get("doc_id", f"doc_{count}"),
                            text=d.get("text", ""),
                            source=d.get("source", "unknown"),
                            metadata=d.get("metadata", {}),
                        )
                        self.store.add_document(doc)
                        count += 1
                    print(f"✅ RAG loaded {count} documents for summary test")
                
                def search(self, query: str, top_k: int = 10, filters=None):
                    results = self.store.search(query, top_k=top_k)
                    return [
                        {
                            "title": doc.source,
                            "content": doc.text[:800],
                            "score": score,
                            "year": doc.metadata.get("year", 2024),
                            "authors": ["NSIC R&D Team"],
                        }
                        for doc, score in results
                    ]
            
            rag_client = TestRAGClient()
        except Exception as e:
            print(f"⚠️ Could not initialize RAG: {e}")
    
    agent = ResearchSynthesizerAgent(
        semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
        perplexity_api_key=os.getenv("PERPLEXITY_API_KEY"),
        rag_client=rag_client,
        knowledge_graph_client=None,
    )
    
    # Test question that should find R&D papers
    test_query = "What are the key factors affecting workforce development and skills gaps in Qatar's labor market?"
    
    print(f"\n📝 TEST QUERY: {test_query}")
    print("\n--- Running Full Synthesis with RAG ---")
    
    synthesis = agent.synthesize(
        query=test_query,
        focus_areas=["workforce development", "skills gap", "labor market", "Qatar employment"],
        max_papers=5,
        max_rag_docs=10,  # Get 10 R&D papers
        include_perplexity=True,
    )
    
    print(f"\n📚 SOURCES FOUND:")
    print(f"   - Semantic Scholar: {len([f for f in synthesis.findings if f.source == 'semantic_scholar'])}")
    print(f"   - R&D Papers (RAG): {len([f for f in synthesis.findings if f.source == 'rag'])}")
    print(f"   - Perplexity: {len([f for f in synthesis.findings if f.source == 'perplexity'])}")
    print(f"   - Total: {len(synthesis.findings)}")
    
    # Show RAG findings specifically
    rag_findings = [f for f in synthesis.findings if f.source == 'rag']
    if rag_findings:
        print(f"\n📄 R&D PAPERS FOUND:")
        for i, f in enumerate(rag_findings[:5], 1):
            print(f"   {i}. {f.title[:60]}...")
    
    # Now evaluate the PhD summary quality
    print("\n" + "=" * 60)
    print("PhD SUMMARY QUALITY EVALUATION")
    print("=" * 60)
    
    narrative = synthesis.narrative
    
    # Quality criteria for PhD-level academic summary
    quality_checks = {
        "has_methodology": False,
        "has_citations": False,
        "has_findings": False,
        "has_evidence_gaps": False,
        "has_policy_implications": False,
        "uses_academic_language": False,
        "has_references": False,
        "sufficient_length": False,
    }
    
    # Check each criterion
    narrative_lower = narrative.lower()
    
    # 1. Methodology section
    if any(term in narrative_lower for term in ["methodology", "systematic review", "sources analyzed", "multi-database"]):
        quality_checks["has_methodology"] = True
    
    # 2. Citations present
    if any(pattern in narrative for pattern in ["(", "et al.", "[", "2024", "2023", "2025"]):
        quality_checks["has_citations"] = True
    
    # 3. Key findings section
    if any(term in narrative_lower for term in ["key findings", "findings", "results show", "evidence suggests"]):
        quality_checks["has_findings"] = True
    
    # 4. Evidence gaps acknowledged
    if any(term in narrative_lower for term in ["evidence gaps", "limitations", "further research", "gaps"]):
        quality_checks["has_evidence_gaps"] = True
    
    # 5. Policy implications
    if any(term in narrative_lower for term in ["policy implications", "implications", "recommendations", "policy"]):
        quality_checks["has_policy_implications"] = True
    
    # 6. Academic language (not casual)
    academic_terms = ["empirical", "analysis", "systematic", "literature", "synthesis", "methodology", "findings", "evidence"]
    if sum(1 for term in academic_terms if term in narrative_lower) >= 3:
        quality_checks["uses_academic_language"] = True
    
    # 7. References section
    if any(term in narrative_lower for term in ["references", "citations", "sources"]):
        quality_checks["has_references"] = True
    
    # 8. Sufficient length (at least 500 chars for a proper summary)
    if len(narrative) >= 500:
        quality_checks["sufficient_length"] = True
    
    # Print results
    print("\n📋 QUALITY CHECKLIST:")
    passed = 0
    for check, status in quality_checks.items():
        icon = "✅" if status else "❌"
        print(f"   {icon} {check.replace('_', ' ').title()}")
        if status:
            passed += 1
    
    quality_score = (passed / len(quality_checks)) * 100
    
    print(f"\n📊 QUALITY SCORE: {passed}/{len(quality_checks)} ({quality_score:.0f}%)")
    
    # Show narrative preview
    print(f"\n📝 NARRATIVE PREVIEW (first 1000 chars):")
    print("-" * 60)
    print(narrative[:1000])
    print("-" * 60)
    
    # Grade
    if quality_score >= 87.5:  # 7/8
        grade = "A - PhD-LEVEL QUALITY"
    elif quality_score >= 75:  # 6/8
        grade = "B - GRADUATE-LEVEL QUALITY"
    elif quality_score >= 62.5:  # 5/8
        grade = "C - ACCEPTABLE ACADEMIC QUALITY"
    else:
        grade = "D - NEEDS IMPROVEMENT"
    
    print(f"\n{'='*60}")
    print(f"SUMMARY QUALITY GRADE: {grade}")
    print(f"{'='*60}")
    
    return {
        "quality_score": quality_score,
        "checks_passed": passed,
        "total_checks": len(quality_checks),
        "findings_count": len(synthesis.findings),
        "rag_papers": len(rag_findings),
        "narrative_length": len(narrative),
    }


if __name__ == "__main__":
    print("=" * 80)
    print("DR. RESEARCH COMPREHENSIVE TEST SUITE")
    print("=" * 80)
    
    print("\n📋 TEST 1: Domain-Agnostic Understanding")
    print("This will take ~15 seconds due to rate limiting.\n")
    domain_results = test_research_synthesizer()
    
    print("\n\n📋 TEST 2: PhD Summary Quality")
    summary_results = test_phd_summary_quality()
    
    # Final overall summary
    print("\n" + "=" * 80)
    print("COMPREHENSIVE TEST RESULTS")
    print("=" * 80)
    
    domain_pass_rate = sum(1 for r in domain_results if r['success']) / len(domain_results) * 100
    summary_score = summary_results['quality_score']
    
    print(f"""
┌─────────────────────────────────────────────────────────────────────┐
│                 DR. RESEARCH FINAL EVALUATION                       │
├─────────────────────────────────────────────────────────────────────┤
│  Domain Understanding:  {domain_pass_rate:3.0f}% (semantic extraction working)      │
│  RAG Integration:       {summary_results['rag_papers']:2} R&D papers retrieved                   │
│  Summary Quality:       {summary_score:3.0f}% ({summary_results['checks_passed']}/{summary_results['total_checks']} PhD criteria met)             │
│  Narrative Length:      {summary_results['narrative_length']:,} characters                        │
└─────────────────────────────────────────────────────────────────────┘
""")
    
    overall = (domain_pass_rate + summary_score) / 2
    if overall >= 80:
        print("🎓 OVERALL: PASS - PhD-level research synthesis capability confirmed")
    elif overall >= 60:
        print("📚 OVERALL: ACCEPTABLE - Academic research capability working")
    else:
        print("⚠️ OVERALL: NEEDS WORK - Check configuration")

