"""
System Health Check for QNWIS Development Deployment
Verifies all components are operational
"""
import asyncio
import os
import sys
from datetime import datetime

def check_environment():
    """Check environment variables"""
    print("="*80)
    print("1. ENVIRONMENT VARIABLES")
    print("="*80)
    
    required_vars = {
        "ANTHROPIC_API_KEY": "Required for LLM",
        "QNWIS_LANGGRAPH_LLM_PROVIDER": "Should be 'anthropic'",
        "DATABASE_URL": "PostgreSQL connection"
    }
    
    optional_vars = {
        "BRAVE_API_KEY": "Search API (recommended)",
        "PERPLEXITY_API_KEY": "Real-time intelligence (recommended)",
        "OPENAI_API_KEY": "Alternative LLM (optional)",
    }
    
    all_good = True
    
    print("\nRequired:")
    for var, desc in required_vars.items():
        value = os.getenv(var)
        if value:
            masked = value[:15] + "..." if len(value) > 15 else value
            print(f"  ✅ {var}: {masked}")
        else:
            print(f"  ❌ {var}: NOT SET - {desc}")
            all_good = False
    
    print("\nOptional:")
    for var, desc in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: Configured - {desc}")
        else:
            print(f"  ⚠️  {var}: Not set - {desc}")
    
    return all_good

def check_database():
    """Check PostgreSQL database"""
    print("\n" + "="*80)
    print("2. DATABASE CONNECTION")
    print("="*80)
    
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        db_url = os.getenv("DATABASE_URL")
        if not db_url:
            print("  ❌ DATABASE_URL not set")
            return False
        
        # Parse connection string
        result = urlparse(db_url)
        
        # Connect
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        
        cursor = conn.cursor()
        
        # Check World Bank cache
        cursor.execute("SELECT COUNT(*) FROM world_bank_cache")
        count = cursor.fetchone()[0]
        
        print(f"  ✅ Database connection: SUCCESS")
        print(f"  ✅ World Bank cache: {count} indicators")
        
        if count < 100:
            print(f"  ⚠️  Expected 128 indicators, found {count}")
            print(f"      Run: python scripts/load_wb_cache.py")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"  ❌ Database error: {str(e)}")
        return False

def check_backend():
    """Check backend can start"""
    print("\n" + "="*80)
    print("3. BACKEND VALIDATION")
    print("="*80)
    
    try:
        # Try importing main modules
        from qnwis.orchestration.workflow import run_intelligence_query
        from qnwis.llm.client import LLMClient
        
        print("  ✅ Core modules: Importable")
        
        # Check LLM client
        from qnwis.orchestration.nodes._helpers import create_llm_client
        client = create_llm_client()
        
        provider = os.getenv("QNWIS_LANGGRAPH_LLM_PROVIDER", "anthropic")
        print(f"  ✅ LLM client: {provider}")
        
        if provider == "stub":
            print("  ❌ CRITICAL: Still using stub LLM!")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Backend error: {str(e)}")
        return False

def check_frontend():
    """Check frontend directory"""
    print("\n" + "="*80)
    print("4. FRONTEND STATUS")
    print("="*80)
    
    frontend_dir = "qnwis-frontend"
    
    if not os.path.exists(frontend_dir):
        print(f"  ❌ Frontend directory not found: {frontend_dir}")
        return False
    
    print(f"  ✅ Frontend directory: {frontend_dir}")
    
    # Check package.json
    package_json = os.path.join(frontend_dir, "package.json")
    if os.path.exists(package_json):
        print(f"  ✅ package.json: Found")
    else:
        print(f"  ❌ package.json: Not found")
        return False
    
    # Check node_modules
    node_modules = os.path.join(frontend_dir, "node_modules")
    if os.path.exists(node_modules):
        print(f"  ✅ node_modules: Installed")
    else:
        print(f"  ⚠️  node_modules: Not installed")
        print(f"      Run: cd {frontend_dir} && npm install")
    
    return True

async def run_test_query():
    """Run a simple test query"""
    print("\n" + "="*80)
    print("5. TEST QUERY")
    print("="*80)
    
    try:
        from qnwis.orchestration.workflow import run_intelligence_query
        
        print("  Running test query: 'What is Qatar's GDP?'")
        print("  (This may take 30-60 seconds...)")
        
        result = await run_intelligence_query("What is Qatar's GDP?")
        
        facts = len(result.get("extracted_facts", []))
        confidence = result.get("confidence_score", 0.0)
        sources = len(result.get("data_sources", []))
        
        print(f"\n  ✅ Query executed successfully")
        print(f"  📊 Facts extracted: {facts}")
        print(f"  🎯 Confidence: {confidence:.2f}")
        print(f"  📚 Sources: {sources}")
        
        if facts < 50:
            print(f"  ⚠️  Low fact count - may indicate data source issues")
        
        if confidence < 0.4:
            print(f"  ⚠️  Low confidence - check LLM configuration")
        
        return facts >= 50 and confidence >= 0.4
        
    except Exception as e:
        print(f"  ❌ Test query failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all health checks"""
    print("\n")
    print("="*80)
    print("QNWIS DEVELOPMENT SYSTEM HEALTH CHECK")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    results = {
        "Environment": check_environment(),
        "Database": check_database(),
        "Backend": check_backend(),
        "Frontend": check_frontend(),
    }
    
    # Test query (async)
    try:
        results["Test Query"] = asyncio.run(run_test_query())
    except Exception as e:
        print(f"  ❌ Test query crashed: {str(e)}")
        results["Test Query"] = False
    
    # Summary
    print("\n" + "="*80)
    print("HEALTH CHECK SUMMARY")
    print("="*80)
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {check:20s} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ ALL CHECKS PASSED - System ready for deployment")
        print("\nNext steps:")
        print("  1. Start backend: ./start_backend.sh (or .ps1 on Windows)")
        print("  2. Start frontend: ./start_frontend.sh (or .ps1 on Windows)")
        print("  3. Access system: http://localhost:3000")
    else:
        print("❌ SOME CHECKS FAILED - Review errors above")
        print("\nFix issues before deploying to stakeholders")
    print("="*80)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
