"""
Verify stub LLM is completely deleted from codebase
"""
import os
import re

def find_stub_references(directory="src"):
    """Find any remaining stub references"""
    stub_files = []
    
    for root, dirs, files in os.walk(directory):
        # Skip __pycache__ and .git
        dirs[:] = [d for d in dirs if d not in ["__pycache__", ".git", "node_modules"]]
        
        for file in files:
            if file.endswith((".py", ".ts", ".tsx", ".js", ".jsx")):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Look for stub references (case-insensitive)
                    if re.search(r'\bprovider\s*[=:]\s*["\']stub["\']', content, re.IGNORECASE) or \
                       re.search(r'_init_stub|_stream_stub|stub_token_delay', content, re.IGNORECASE):
                        stub_files.append(filepath)
    
    return stub_files

print("="*80)
print("VERIFYING STUB LLM DELETION")
print("="*80)

# Check backend
backend_stubs = find_stub_references("src")
if backend_stubs:
    print("\n❌ STUB REFERENCES FOUND IN BACKEND:")
    for file in backend_stubs:
        print(f"  - {file}")
else:
    print("\n✅ Backend: No stub references found")

# Check .env
print("\n" + "="*80)
print("CHECKING .ENV CONFIGURATION")
print("="*80)

if os.path.exists(".env"):
    with open(".env", 'r') as f:
        env_content = f.read()
        
        if "ANTHROPIC_API_KEY" in env_content:
            print("✅ ANTHROPIC_API_KEY: Set")
        else:
            print("❌ ANTHROPIC_API_KEY: Missing")
        
        if "QNWIS_LANGGRAPH_LLM_PROVIDER" in env_content:
            # Extract value
            match = re.search(r'QNWIS_LANGGRAPH_LLM_PROVIDER\s*=\s*(.+)', env_content)
            if match:
                provider = match.group(1).strip()
                if provider == "anthropic":
                    print(f"✅ LLM Provider: {provider}")
                elif provider == "stub":
                    print(f"❌ LLM Provider: {provider} (SHOULD BE 'anthropic')")
                else:
                    print(f"⚠️  LLM Provider: {provider}")
        else:
            print("⚠️  QNWIS_LANGGRAPH_LLM_PROVIDER: Not set (will default to anthropic)")
        
        if "QNWIS_LANGGRAPH_LLM_MODEL" in env_content:
            match = re.search(r'QNWIS_LANGGRAPH_LLM_MODEL\s*=\s*(.+)', env_content)
            if match:
                model = match.group(1).strip()
                print(f"✅ LLM Model: {model}")

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80)
