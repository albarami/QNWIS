"""
HONEST diagnostic - capture RAW SSE output to see what's actually being returned.
"""

import asyncio
import httpx
import json


async def capture_raw_output():
    """Capture and display RAW SSE output."""
    
    query = "What is Qatar's unemployment rate and GDP?"
    
    print("=" * 80)
    print("RAW SSE OUTPUT CAPTURE")
    print("=" * 80)
    print(f"Query: {query}")
    print("=" * 80)
    
    all_raw_lines = []
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            async with client.stream(
                "POST",
                "http://localhost:8000/api/v1/council/stream",
                json={"question": query},
                timeout=300.0
            ) as response:
                
                print(f"\nStatus: {response.status_code}")
                print(f"Headers: {dict(response.headers)}")
                print("\n--- RAW SSE LINES ---\n")
                
                line_count = 0
                async for line in response.aiter_lines():
                    line_count += 1
                    all_raw_lines.append(line)
                    
                    # Print first 50 lines
                    if line_count <= 50:
                        print(f"[{line_count:03d}] {line[:200]}")
                    
                    # Parse to find actual data
                    if line.startswith("data:"):
                        try:
                            data = json.loads(line[5:].strip())
                            stage = data.get("stage", "")
                            status = data.get("status", "")
                            payload = data.get("payload", {})
                            
                            # Look for actual content
                            if payload:
                                payload_keys = list(payload.keys())
                                if any(k in payload_keys for k in ["facts", "data", "report", "summary", "text", "content"]):
                                    print(f"\n*** FOUND DATA at line {line_count} ***")
                                    print(f"    Stage: {stage}, Status: {status}")
                                    print(f"    Payload keys: {payload_keys}")
                                    
                                    # Print actual content
                                    for key in ["facts", "data", "report", "summary", "text", "content"]:
                                        if key in payload:
                                            val = payload[key]
                                            if isinstance(val, str) and len(val) > 0:
                                                print(f"    {key}: {val[:500]}...")
                                            elif isinstance(val, list) and len(val) > 0:
                                                print(f"    {key}: {len(val)} items")
                                                print(f"    First item: {val[0]}")
                                            elif val:
                                                print(f"    {key}: {val}")
                                    
                        except json.JSONDecodeError:
                            pass
                    
                    # Check for done
                    if "done" in line:
                        print(f"\n... Total lines: {line_count}")
                        break
                        
        except Exception as e:
            print(f"ERROR: {e}")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total SSE lines received: {len(all_raw_lines)}")
    
    # Count data lines
    data_lines = [l for l in all_raw_lines if l.startswith("data:")]
    print(f"Data lines: {len(data_lines)}")
    
    # Save all for analysis
    with open("test_reports/raw_sse_output.txt", "w", encoding="utf-8") as f:
        for line in all_raw_lines:
            f.write(line + "\n")
    
    print(f"\nFull output saved to: test_reports/raw_sse_output.txt")
    
    # Parse all events and show what we got
    print("\n" + "=" * 80)
    print("PARSED EVENTS")
    print("=" * 80)
    
    for line in data_lines:
        try:
            data = json.loads(line[5:].strip())
            stage = data.get("stage", "?")
            status = data.get("status", "?")
            payload = data.get("payload", {})
            
            payload_preview = str(payload)[:100] if payload else "(empty)"
            print(f"  {stage}:{status} -> {payload_preview}")
            
        except:
            pass


if __name__ == "__main__":
    asyncio.run(capture_raw_output())

