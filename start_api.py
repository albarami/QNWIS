"""
Start API server with .env loaded.
"""

import os
from dotenv import load_dotenv

if __name__ == "__main__":
    # Load .env file explicitly
    load_dotenv()

    # Verify environment is loaded
    print(f"Environment loaded:")
    print(f"  DATABASE_URL: {os.getenv('DATABASE_URL', 'NOT SET')[:50]}...")
    print(f"  QNWIS_LLM_PROVIDER: {os.getenv('QNWIS_LLM_PROVIDER', 'NOT SET')}")
    print(f"  QNWIS_ANTHROPIC_MODEL: {os.getenv('QNWIS_ANTHROPIC_MODEL', 'NOT SET')}")
    print(f"  QNWIS_JWT_SECRET: {os.getenv('QNWIS_JWT_SECRET', 'NOT SET')[:30]}...")
    print()

    # Now start uvicorn
    import uvicorn
    uvicorn.run(
        "src.qnwis.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
