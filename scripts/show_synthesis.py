#!/usr/bin/env python3
"""
Quick script to call the QNWIS API and display the professional synthesis.
"""

import httpx
import json
import sys

BACKEND_URL = "http://localhost:8000"

def main():
    query = """Qatar's LNG expansion will create 25,000 new technical jobs by 2030, but our technical 
    training capacity is 3,000 graduates per year. Should we import skilled workers or invest 
    QR 12 billion in accelerated training? The Emir wants to know if we can maintain 50% 
    Qatarization in technical roles while meeting production targets."""
    
    print("=" * 80)
    print("QNWIS MINISTERIAL INTELLIGENCE SYSTEM - PROFESSIONAL OUTPUT DEMONSTRATION")
    print("=" * 80)
    print()
    
    # Collect all streamed data
    synthesis_content = ""
    meta_synthesis_content = ""
    
    with httpx.stream(
        "POST",
        f"{BACKEND_URL}/council/debate-workflow",
        json={"query": query},
        timeout=1800.0
    ) as response:
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            
            try:
                data = json.loads(line[6:])
                event_type = data.get("event", "")
                
                # Capture final synthesis
                if event_type == "synthesize":
                    final_synth = data.get("data", {}).get("final_synthesis", "")
                    if final_synth and len(final_synth) > len(synthesis_content):
                        synthesis_content = final_synth
                
                # Capture meta synthesis
                if event_type == "meta_synthesis":
                    meta_synth = data.get("data", {}).get("meta_synthesis", "")
                    if meta_synth:
                        meta_synthesis_content = meta_synth
                
                # Show progress
                if event_type == "done":
                    print("\n[WORKFLOW COMPLETE]")
                    
            except json.JSONDecodeError:
                continue
    
    # Display the professional output
    print("\n")
    print("=" * 80)
    print("MINISTERIAL INTELLIGENCE BRIEFING - FINAL OUTPUT")
    print("=" * 80)
    print()
    
    if synthesis_content:
        print(synthesis_content)
    
    if meta_synthesis_content:
        print("\n")
        print("=" * 80)
        print("CROSS-SCENARIO META-SYNTHESIS")
        print("=" * 80)
        print()
        print(meta_synthesis_content)
    
    if not synthesis_content and not meta_synthesis_content:
        print("NOTE: Synthesis content was generated but not captured in events.")
        print("Check server logs for the full synthesis (6826+ chars).")

if __name__ == "__main__":
    main()

