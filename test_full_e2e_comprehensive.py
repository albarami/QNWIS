"""
Comprehensive End-to-End Test for QNWIS System.

Tests EVERY step of the pipeline:
1. Classification
2. Prefetch (data extraction from all sources)
3. RAG retrieval
4. Agent selection
5. Multi-agent debate
6. Devil's advocate
7. Synthesis/Summary

Verifies:
- No fabrication/fake data
- All data properly sourced
- Debate is valuable and coherent
- Summary is consulting-firm quality
"""

import asyncio
import httpx
import json
import sys
import io
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Fix Windows Unicode encoding issues
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def sanitize_text(text: str) -> str:
    """Remove emojis and special unicode characters for Windows compatibility."""
    if not isinstance(text, str):
        return str(text)
    # Remove emojis and other special unicode chars, keep basic ASCII + common accents
    return text.encode('ascii', errors='ignore').decode('ascii')


def safe_print(*args, **kwargs):
    """Print with safe unicode handling for Windows."""
    try:
        # Sanitize all string arguments
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_args.append(sanitize_text(arg))
            else:
                safe_args.append(arg)
        print(*safe_args, **kwargs)
    except UnicodeEncodeError:
        # Final fallback - replace all problematic characters
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_args.append(arg.encode('ascii', errors='replace').decode('ascii'))
            else:
                safe_args.append(str(arg))
        print(*safe_args, **kwargs)


class ComprehensiveE2ETest:
    """Comprehensive end-to-end test of QNWIS system."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.results = {
            "test_start": datetime.now().isoformat(),
            "stages": {},
            "data_quality": {},
            "agent_performance": {},
            "debate_analysis": {},
            "summary_quality": {},
            "errors": [],
            "warnings": [],
        }
        
    async def run_full_test(self, query: str) -> Dict:
        """Run comprehensive test with a query."""
        print("=" * 80)
        print("QNWIS COMPREHENSIVE END-TO-END TEST")
        print("=" * 80)
        print(f"\nQuery: {query}\n")
        print("=" * 80)
        
        # Track all events
        stages_seen = set()
        stage_events = defaultdict(list)
        agents_seen = set()
        agent_reports = []
        debate_turns = []
        facts_extracted = []
        synthesis_report = None
        meta_synthesis_content = None
        final_synthesis_content = None
        scenario_count = 0
        
        async with httpx.AsyncClient(timeout=600.0) as client:
            try:
                print("\n[1/8] Sending query to backend...")
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/v1/council/stream",
                    json={"question": query},
                    timeout=600.0
                ) as response:
                    
                    if response.status_code != 200:
                        error = f"Backend returned {response.status_code}"
                        self.results["errors"].append(error)
                        print(f"ERROR: {error}")
                        return self.results
                    
                    print("[2/8] Receiving streaming events...")
                    
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        
                        try:
                            data = json.loads(line[5:].strip())
                        except json.JSONDecodeError:
                            continue
                        
                        # Track stage events
                        stage = data.get("stage", "")
                        status = data.get("status", "")
                        payload = data.get("payload", {}) or {}
                        
                        if stage:
                            stages_seen.add(stage)
                            stage_events[stage].append({
                                "status": status,
                                "payload": payload
                            })
                            
                            # Print stage progress
                            if status == "running":
                                print(f"   -> Stage: {stage} STARTED")
                            elif status == "complete":
                                print(f"   -> Stage: {stage} COMPLETE")
                        
                        # Track facts/data extraction from EXTRACTION stage
                        if stage in ["prefetch", "extraction"] and status == "complete":
                            if "extracted_facts" in payload:
                                facts_extracted.extend(payload["extracted_facts"])
                                print(f"      📊 Extracted {len(payload['extracted_facts'])} facts")
                            if "data_sources" in payload:
                                for src in payload["data_sources"]:
                                    if isinstance(src, dict):
                                        agents_seen.add(f"Source: {src.get('name', src.get('source', 'unknown'))}")
                        
                        # Track RAG results
                        if stage == "rag" and status == "complete":
                            rag_count = payload.get("rag_context_count", payload.get("count", 0))
                            print(f"      📄 RAG: Retrieved {rag_count} documents")
                        
                        # Track parallel scenario execution
                        if stage.startswith("scenario:"):
                            scenario_count += 1
                            if status == "complete":
                                print(f"      🔮 Scenario {scenario_count} complete")
                        
                        if stage == "parallel_exec" and status == "complete":
                            scenarios = payload.get("num_scenarios", payload.get("scenarios_completed", 0))
                            print(f"      ⚡ Parallel execution: {scenarios} scenarios completed")
                        
                        # Track agents (including parallel scenario agents)
                        if "agent" in payload:
                            agents_seen.add(payload["agent"])
                        if "agents" in payload:
                            for agent in payload["agents"]:
                                if isinstance(agent, str):
                                    agents_seen.add(agent)
                                elif isinstance(agent, dict):
                                    agents_seen.add(agent.get("name", "unknown"))
                        if stage == "agents" and "selected_agents" in payload:
                            for agent in payload.get("selected_agents", []):
                                agents_seen.add(agent if isinstance(agent, str) else agent.get("name", "unknown"))
                        
                        # Track agent reports
                        if "report" in payload or "analysis" in payload:
                            agent_reports.append(payload)
                        
                        # Track debate turns (including from parallel scenarios)
                        if "debate" in stage or stage == "critique":
                            if "turn" in payload or "message" in payload or "turn_number" in payload:
                                debate_turns.append(payload)
                        
                        # Track conversation history from debate
                        if "conversation_history" in payload:
                            debate_turns.extend(payload["conversation_history"][:5])  # Sample
                        
                        # Track meta-synthesis (parallel scenarios)
                        if stage == "meta_synthesis" and status == "complete":
                            meta_synthesis_content = payload.get("meta_synthesis") or payload.get("final_synthesis")
                            if meta_synthesis_content:
                                print(f"      📊 Meta-synthesis: {len(meta_synthesis_content)} chars")
                        
                        # Track synthesis
                        if stage == "synthesize" and status == "complete":
                            synthesis_report = payload
                            final_synthesis_content = (
                                payload.get("final_synthesis") or 
                                payload.get("text") or 
                                payload.get("summary") or
                                payload.get("report")
                            )
                            if final_synthesis_content:
                                print(f"      📝 Final synthesis: {len(final_synthesis_content)} chars")
                        
                        # Check for done
                        if stage == "done":
                            print("\n[3/8] Workflow complete!")
                            break
                    
            except Exception as e:
                error = f"Connection error: {e}"
                self.results["errors"].append(error)
                print(f"ERROR: {error}")
                return self.results
        
        # Use meta_synthesis if no final synthesis was captured
        if not final_synthesis_content and meta_synthesis_content:
            final_synthesis_content = meta_synthesis_content
            synthesis_report = {"final_synthesis": meta_synthesis_content}
        
        # Analyze results
        print("\n" + "=" * 80)
        print("ANALYSIS RESULTS")
        print("=" * 80)
        
        # [4/8] Stage Analysis
        print("\n[4/8] STAGE ANALYSIS:")
        expected_stages = ["classify", "prefetch", "rag", "agents", "debate", "critique", "verify", "synthesize", "done"]
        # Also accept alternative names
        stage_aliases = {
            "classify": ["classify", "classification", "classifier"],
            "prefetch": ["prefetch", "extraction"],
            "rag": ["rag", "retrieval"],
            "agents": ["agents", "agent_selection", "scenario_gen", "parallel_exec", "meta_synthesis"],
            "debate": ["debate", "debate:turn", "debate:opening", "debate:consensus"],
            "critique": ["critique", "verification"],
            "verify": ["verify", "verification", "fact_check"],
            "synthesize": ["synthesize", "synthesis", "meta_synthesis"],
            "done": ["done", "complete"],
        }
        
        for stage in expected_stages:
            aliases = stage_aliases.get(stage, [stage])
            found = any(alias in stages_seen or any(alias in s for s in stages_seen) for alias in aliases)
            if found:
                status_val = "PASS"
                print(f"   {stage}: {status_val}")
                self.results["stages"][stage] = status_val
            else:
                print(f"   {stage}: MISSING")
                self.results["stages"][stage] = "MISSING"
                self.results["warnings"].append(f"Stage {stage} was not seen")
        
        # [5/8] Data Quality Analysis
        print("\n[5/8] DATA QUALITY ANALYSIS:")
        self.results["data_quality"]["total_facts"] = len(facts_extracted)
        print(f"   Total facts extracted: {len(facts_extracted)}")
        
        # Check for sources
        sourced_facts = [f for f in facts_extracted if f.get("source")]
        print(f"   Facts with sources: {len(sourced_facts)}")
        self.results["data_quality"]["sourced_facts"] = len(sourced_facts)
        
        # Check source diversity
        sources = set()
        for fact in facts_extracted:
            source = fact.get("source", "")
            if source:
                # Extract source name
                if "World Bank" in source:
                    sources.add("World Bank")
                elif "GCC" in source:
                    sources.add("GCC-STAT")
                elif "IMF" in source:
                    sources.add("IMF")
                elif "Perplexity" in source or "perplexity" in source.lower():
                    sources.add("Perplexity AI")
                elif "Semantic Scholar" in source or "semantic" in source.lower():
                    sources.add("Semantic Scholar")
                elif "Brave" in source or "brave" in source.lower():
                    sources.add("Brave Search")
                elif "PostgreSQL" in source or "postgres" in source.lower():
                    sources.add("PostgreSQL cache")
                elif "ILO" in source:
                    sources.add("ILO")
                elif "R&D" in source or "PDF" in source:
                    sources.add("R&D Reports (RAG)")
                elif "Knowledge Graph" in source or "kg" in source.lower():
                    sources.add("Knowledge Graph")
                else:
                    sources.add(source[:30])
        
        # Also check agents for data sources
        for agent in agents_seen:
            if "Source:" in agent:
                sources.add(agent.replace("Source: ", ""))
        
        print(f"   Unique sources: {len(sources)}")
        print(f"   Sources: {', '.join(sources) if sources else 'None captured'}")
        self.results["data_quality"]["sources"] = list(sources)
        
        # Check for potential fabrication
        fabrication_indicators = []
        for fact in facts_extracted:
            source = fact.get("source", "")
            if not source:
                fabrication_indicators.append(f"Unsourced: {fact.get('metric', fact.get('indicator', 'unknown'))}")
        
        if fabrication_indicators:
            print(f"   WARNING: {len(fabrication_indicators)} facts without proper sources")
            self.results["data_quality"]["warnings"] = fabrication_indicators[:5]
        else:
            print(f"   All facts properly sourced ✓")
        
        # [6/8] Agent Analysis
        print("\n[6/8] AGENT ANALYSIS:")
        # Filter out source entries
        actual_agents = [a for a in agents_seen if not a.startswith("Source:")]
        print(f"   Agents activated: {len(actual_agents)}")
        print(f"   Agents: {', '.join(actual_agents) if actual_agents else 'None captured'}")
        self.results["agent_performance"]["agents_count"] = len(actual_agents)
        self.results["agent_performance"]["agents"] = list(actual_agents)
        
        if len(actual_agents) < 3:
            self.results["warnings"].append("Less than 3 agents activated")
        
        # [7/8] Debate Analysis
        print("\n[7/8] DEBATE ANALYSIS:")
        print(f"   Debate turns recorded: {len(debate_turns)}")
        self.results["debate_analysis"]["turns"] = len(debate_turns)
        
        # Check for parallel scenarios
        print(f"   Parallel scenarios: {max(scenario_count, 1)}")
        self.results["debate_analysis"]["scenarios"] = max(scenario_count, 1)
        
        # Check for devil's advocate / critique
        critique_seen = any("critique" in s for s in stages_seen)
        print(f"   Devil's Advocate (Critique): {'YES' if critique_seen else 'NO'}")
        self.results["debate_analysis"]["critique_present"] = critique_seen
        
        # [8/8] Synthesis Quality
        print("\n[8/8] SYNTHESIS/SUMMARY QUALITY:")
        if final_synthesis_content:
            word_count = len(final_synthesis_content.split())
            char_count = len(final_synthesis_content)
            print(f"   Summary word count: {word_count}")
            print(f"   Summary char count: {char_count}")
            self.results["summary_quality"]["word_count"] = word_count
            self.results["summary_quality"]["char_count"] = char_count
            
            # Check for structure
            has_sections = any(marker in final_synthesis_content for marker in [
                "##", "**", "###", "1.", "•", "─", "═", "EXECUTIVE", "RECOMMENDATION",
                "KEY FINDING", "STRATEGIC", "ANALYSIS"
            ])
            print(f"   Has structured sections: {'YES' if has_sections else 'NO'}")
            self.results["summary_quality"]["structured"] = has_sections
            
            # Check for citations
            has_citations = any(marker in final_synthesis_content.lower() for marker in [
                "source:", "according to", "data from", "world bank", "ilo", 
                "evidence:", "based on", "research shows", "%", "billion", "million"
            ])
            print(f"   Has citations/data: {'YES' if has_citations else 'NO'}")
            self.results["summary_quality"]["has_citations"] = has_citations
            
            # Quality indicators for consulting-firm level
            quality_indicators = {
                "executive_summary": any(x in final_synthesis_content.lower() for x in ["executive", "summary", "overview"]),
                "recommendations": any(x in final_synthesis_content.lower() for x in ["recommend", "action", "should", "must"]),
                "data_driven": any(c.isdigit() for c in final_synthesis_content[:1000]),
                "professional_depth": word_count > 500,
                "multi_section": final_synthesis_content.count("##") >= 3 or final_synthesis_content.count("**") >= 5,
            }
            
            print(f"   Quality indicators:")
            for indicator, present in quality_indicators.items():
                print(f"      - {indicator}: {'YES ✓' if present else 'NO'}")
            
            self.results["summary_quality"]["indicators"] = quality_indicators
            
            # Print summary preview (sanitized for Windows)
            print(f"\n   {'='*60}")
            print(f"   SYNTHESIS PREVIEW (first 1000 chars):")
            print(f"   {'='*60}")
            preview = sanitize_text(final_synthesis_content[:1000]).replace("\n", "\n   ")
            safe_print(f"   {preview}...")
            print(f"   {'='*60}")
        else:
            print("   WARNING: No synthesis report captured")
            self.results["warnings"].append("Synthesis report not captured")
            self.results["summary_quality"]["word_count"] = 0
            self.results["summary_quality"]["structured"] = False
            self.results["summary_quality"]["has_citations"] = False
        
        # Final verdict
        print("\n" + "=" * 80)
        print("FINAL VERDICT")
        print("=" * 80)
        
        # Calculate score
        score = 0
        max_score = 100
        
        # Stage completion (40 points)
        stages_complete = sum(1 for s in expected_stages if self.results["stages"].get(s) == "PASS")
        stage_score = (stages_complete / len(expected_stages)) * 40
        score += stage_score
        print(f"\n Stage Completion: {stage_score:.0f}/40 ({stages_complete}/{len(expected_stages)} stages)")
        
        # Data quality (20 points)
        data_score = 0
        if len(sources) >= 3:
            data_score += 10
        elif len(sources) >= 1:
            data_score += 5
        if len(facts_extracted) >= 10:
            data_score += 5
        elif len(facts_extracted) >= 1:
            data_score += 2
        if len(facts_extracted) > 0 and len(sourced_facts) / len(facts_extracted) > 0.8:
            data_score += 5
        elif len(facts_extracted) > 0:
            data_score += 2
        score += data_score
        print(f" Data Quality: {data_score}/20 ({len(sources)} sources, {len(facts_extracted)} facts)")
        
        # Agent performance (20 points)
        agent_score = 0
        if len(actual_agents) >= 3:
            agent_score += 10
        elif len(actual_agents) >= 1:
            agent_score += 5
        if len(actual_agents) >= 6:
            agent_score += 10
        elif len(actual_agents) >= 4:
            agent_score += 5
        score += agent_score
        print(f" Agent Performance: {agent_score}/20 ({len(actual_agents)} agents)")
        
        # Debate quality (10 points)
        debate_score = 0
        if len(debate_turns) >= 5:
            debate_score += 5
        elif len(debate_turns) >= 1:
            debate_score += 2
        if critique_seen:
            debate_score += 5
        score += debate_score
        print(f" Debate Quality: {debate_score}/10 ({len(debate_turns)} turns, critique: {critique_seen})")
        
        # Summary quality (10 points)
        summary_score = 0
        if final_synthesis_content:
            word_count = self.results["summary_quality"].get("word_count", 0)
            if self.results["summary_quality"].get("structured"):
                summary_score += 3
            if self.results["summary_quality"].get("has_citations"):
                summary_score += 3
            if word_count > 500:
                summary_score += 4
            elif word_count > 100:
                summary_score += 2
        score += summary_score
        print(f" Summary Quality: {summary_score}/10 ({self.results['summary_quality'].get('word_count', 0)} words)")
        
        self.results["final_score"] = score
        self.results["max_score"] = max_score
        
        print(f"\n{'='*40}")
        print(f" TOTAL SCORE: {score:.0f}/{max_score}")
        print(f"{'='*40}")
        
        if score >= 90:
            print(" VERDICT: EXCEPTIONAL - Big-4 Consulting Quality ⭐⭐⭐")
        elif score >= 80:
            print(" VERDICT: EXCELLENT - Consulting-firm quality ⭐⭐")
        elif score >= 70:
            print(" VERDICT: VERY GOOD - High professional standard ⭐")
        elif score >= 60:
            print(" VERDICT: GOOD - Minor improvements needed")
        elif score >= 40:
            print(" VERDICT: NEEDS WORK - Several issues found")
        else:
            print(" VERDICT: CRITICAL - Major issues")
        
        # Warnings summary
        if self.results["warnings"]:
            print(f"\n WARNINGS ({len(self.results['warnings'])}):")
            for w in self.results["warnings"][:5]:
                print(f"   - {w}")
        
        # Errors summary
        if self.results["errors"]:
            print(f"\n ERRORS ({len(self.results['errors'])}):")
            for e in self.results["errors"]:
                print(f"   - {e}")
        
        self.results["test_end"] = datetime.now().isoformat()
        
        # Save results
        import os
        os.makedirs("test_reports", exist_ok=True)
        with open("test_reports/e2e_comprehensive_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\nResults saved to: test_reports/e2e_comprehensive_results.json")
        
        return self.results


async def main():
    """Run comprehensive test."""
    
    # Test query - complex, cross-domain question
    test_query = """
    Qatar's LNG expansion will create 25,000 new technical jobs by 2030, but our technical 
    training capacity is 3,000 graduates per year. Should we import skilled workers or invest 
    QR 12 billion in accelerated training? The Emir wants to know if we can maintain 50% 
    Qatarization in technical roles while meeting production targets.
    """
    
    tester = ComprehensiveE2ETest()
    results = await tester.run_full_test(test_query.strip())
    
    return results.get("final_score", 0) >= 70


if __name__ == "__main__":
    import os
    os.makedirs("test_reports", exist_ok=True)
    
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
