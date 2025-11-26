
import requests
import json
import sys
import time

def run_validation():
    url = "http://localhost:8000/api/v1/council/stream"
    headers = {"Content-Type": "application/json"}
    data = {
        "question": "Should Qatar invest $15B in Food Valley project targeting 40% food self-sufficiency?",
        "provider": "anthropic"
    }
    
    print(f"Sending request to {url}...")
    print(f"Question: {data['question']}")
    
    try:
        response = requests.post(url, headers=headers, json=data, stream=True, timeout=300)
        
        micro_invoked = False
        macro_invoked = False
        debate_happened = False
        
        print("\nStreaming response...")
        
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if decoded_line.startswith("data: "):
                    json_str = decoded_line[6:]
                    try:
                        event = json.loads(json_str)
                        stage = event.get("stage")
                        status = event.get("status")
                        payload = event.get("payload", {})
                        
                        print(f"Event: {stage} ({status})")
                        
                        if stage == "agent:MicroEconomist" and status == "complete":
                            print("MicroEconomist finished")
                            micro_invoked = True
                            
                        if stage == "agent:MacroEconomist" and status == "complete":
                            print("MacroEconomist finished")
                            macro_invoked = True
                            
                        if stage == "debate" and status == "running":
                            print("Debate started...")
                            
                        if stage == "debate" and status == "complete":
                            print("Debate finished")
                            debate_happened = True
                            
                        if stage == "synthesize" and status == "complete":
                            print("\nSynthesis Complete:")
                            print("-" * 40)
                            print(payload.get("synthesis", "")[:500] + "...")
                            print("-" * 40)
                            
                    except json.JSONDecodeError:
                        pass
                        
        if micro_invoked and macro_invoked:
            print("\nSUCCESS: Both economists were invoked.")
        else:
            print("\nFAILURE: One or both economists missing.")
            if not micro_invoked: print("- MicroEconomist missing")
            if not macro_invoked: print("- MacroEconomist missing")
            
        if debate_happened:
             print("SUCCESS: Debate phase occurred.")
        else:
             print("FAILURE: Debate phase did not occur.")
             
        if micro_invoked and macro_invoked and debate_happened:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_validation()
