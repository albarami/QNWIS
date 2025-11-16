"""Test that SSE stream completes properly"""
import requests
import time

url = "http://localhost:8000/api/v1/council/stream"
payload = {
    "question": "Test query",
    "provider": "stub",
    "model": None
}

print(f"Starting SSE stream test at {time.strftime('%H:%M:%S')}")
print(f"URL: {url}")
print(f"Payload: {payload}\n")

start_time = time.time()
response = requests.post(url, json=payload, stream=True)

print(f"Status: {response.status_code}")

if response.status_code == 200:
    event_count = 0
    last_event = None
    
    for line in response.iter_lines():
        if line:
            line_str = line.decode('utf-8')
            if line_str.startswith('data: '):
                event_count += 1
                try:
                    import json
                    data = json.loads(line_str[6:])
                    stage = data.get('stage', 'unknown')
                    status = data.get('status', 'unknown')
                    print(f"  [{event_count}] {stage} - {status}")
                    last_event = (stage, status)
                except:
                    pass
    
    elapsed = time.time() - start_time
    print(f"\nStream completed!")
    print(f"Total events: {event_count}")
    print(f"Last event: {last_event}")
    print(f"Elapsed: {elapsed:.1f}s")
    
    if last_event and last_event[0] == 'done' and last_event[1] == 'complete':
        print("\n✅ SUCCESS! Stream closed properly after 'done' event")
    else:
        print(f"\n⚠️ WARNING! Last event was not 'done/complete': {last_event}")
else:
    print(f"Error: {response.text}")
