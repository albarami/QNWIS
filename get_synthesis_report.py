"""Get and display the actual synthesis report from a query."""

import asyncio
import httpx
import json


async def get_full_report():
    """Get the full synthesis report from a test query."""
    
    query = """
    Qatar's LNG expansion will create 25,000 new technical jobs by 2030, but our technical 
    training capacity is 3,000 graduates per year. Should we import skilled workers or invest 
    QR 12 billion in accelerated training? The Emir wants to know if we can maintain 50% 
    Qatarization in technical roles while meeting production targets.
    """
    
    print("=" * 80)
    print("GETTING FULL SYNTHESIS REPORT")
    print("=" * 80)
    print(f"\nQuery: {query.strip()}\n")
    print("Waiting for response (this may take several minutes)...")
    
    all_events = []
    synthesis_data = None
    data_facts = []
    agent_reports = []
    debate_content = []
    
    async with httpx.AsyncClient(timeout=900.0) as client:
        async with client.stream(
            "POST",
            "http://localhost:8000/api/v1/council/stream",
            json={"question": query.strip()},
            timeout=900.0
        ) as response:
            
            async for line in response.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                
                try:
                    data = json.loads(line[5:].strip())
                    all_events.append(data)
                    
                    stage = data.get("stage", "")
                    status = data.get("status", "")
                    payload = data.get("payload", {})
                    
                    # Collect prefetched data
                    if stage == "prefetch" and status == "complete":
                        if "facts" in payload:
                            data_facts.extend(payload["facts"])
                        if "data" in payload:
                            data_facts.extend(payload.get("data", []))
                    
                    # Collect agent reports
                    if stage == "agents" and "report" in payload:
                        agent_reports.append(payload)
                    
                    # Collect debate content
                    if "debate" in stage:
                        if "message" in payload or "content" in payload:
                            debate_content.append(payload)
                    
                    # Collect synthesis
                    if stage == "synthesize" and status == "complete":
                        synthesis_data = payload
                    
                    # Print progress
                    if status in ["running", "complete"]:
                        print(f"  {stage}: {status}")
                    
                    if stage == "done":
                        break
                        
                except json.JSONDecodeError:
                    continue
    
    # Output results
    print("\n" + "=" * 80)
    print("DATA EXTRACTION RESULTS")
    print("=" * 80)
    print(f"\nTotal events received: {len(all_events)}")
    print(f"Data facts extracted: {len(data_facts)}")
    
    if data_facts:
        print("\n--- Sample Facts (first 5) ---")
        for i, fact in enumerate(data_facts[:5]):
            source = fact.get("source", "Unknown")
            metric = fact.get("metric", fact.get("indicator", "Unknown"))
            value = fact.get("value", "N/A")
            print(f"  {i+1}. {metric}: {value} [Source: {source}]")
    
    print(f"\nAgent reports collected: {len(agent_reports)}")
    print(f"Debate turns collected: {len(debate_content)}")
    
    print("\n" + "=" * 80)
    print("SYNTHESIS REPORT")
    print("=" * 80)
    
    if synthesis_data:
        # Try to extract the report text
        report = synthesis_data.get("report") or synthesis_data.get("summary") or synthesis_data.get("text", "")
        
        if isinstance(report, dict):
            report = report.get("text", "") or report.get("content", "") or str(report)
        
        if report:
            print(f"\nWord count: {len(report.split())}")
            print(f"Character count: {len(report)}")
            print("\n--- FULL SYNTHESIS REPORT ---\n")
            print(report)
            print("\n--- END OF REPORT ---")
            
            # Quality analysis
            print("\n" + "=" * 80)
            print("QUALITY ANALYSIS")
            print("=" * 80)
            
            checks = {
                "Has structured sections": any(m in report for m in ["##", "**", "###", "1.", "•", "- "]),
                "Has citations": "[Per " in report or "Source:" in report or "according to" in report.lower(),
                "Has recommendations": "recommend" in report.lower(),
                "Has executive summary": "executive" in report.lower() or "summary" in report.lower(),
                "Has data/numbers": any(c.isdigit() for c in report),
                "Professional length (>500 words)": len(report.split()) > 500,
                "Has key findings": "finding" in report.lower() or "key" in report.lower(),
                "Has analysis": "analysis" in report.lower() or "analyze" in report.lower(),
            }
            
            passed = sum(1 for v in checks.values() if v)
            total = len(checks)
            
            for check, result in checks.items():
                status = "PASS" if result else "FAIL"
                print(f"  [{status}] {check}")
            
            print(f"\nQuality Score: {passed}/{total} ({passed/total*100:.0f}%)")
            
            if passed >= 6:
                print("\nVERDICT: CONSULTING-FIRM QUALITY")
            elif passed >= 4:
                print("\nVERDICT: GOOD QUALITY - Minor improvements needed")
            else:
                print("\nVERDICT: NEEDS IMPROVEMENT")
        else:
            print("\nNo report text found in synthesis payload")
            print(f"Synthesis payload keys: {synthesis_data.keys() if synthesis_data else 'None'}")
    else:
        print("\nNo synthesis data captured")
        
        # Try to find it in all events
        print("\nSearching all events for synthesis content...")
        for event in all_events:
            if "synthesize" in event.get("stage", ""):
                print(f"Found synthesis event: {event}")
    
    # Save full results
    with open("test_reports/full_synthesis_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "query": query.strip(),
            "total_events": len(all_events),
            "data_facts_count": len(data_facts),
            "data_facts_sample": data_facts[:10],
            "synthesis_data": synthesis_data,
            "debate_turns": len(debate_content),
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\nFull results saved to: test_reports/full_synthesis_results.json")


if __name__ == "__main__":
    asyncio.run(get_full_report())

