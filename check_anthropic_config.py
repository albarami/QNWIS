#!/usr/bin/env python3
"""Check Anthropic configuration."""
import os
from dotenv import load_dotenv

load_dotenv()

print("=" * 60)
print("ANTHROPIC CONFIGURATION CHECK")
print("=" * 60)

provider = os.getenv("QNWIS_LLM_PROVIDER", "NOT SET")
anthropic_model = os.getenv("QNWIS_ANTHROPIC_MODEL", "NOT SET")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

print(f"✓ LLM Provider: {provider}")
print(f"✓ Anthropic Model: {anthropic_model}")
print(f"✓ Anthropic API Key: {'SET ✓' if anthropic_api_key else 'NOT SET ✗'}")

if anthropic_api_key:
    print(f"  - Key starts with: {anthropic_api_key[:12]}...")
    print(f"  - Key length: {len(anthropic_api_key)}")

print("=" * 60)

# Test import
try:
    from src.qnwis.llm.config import load_llm_config
    config = load_llm_config()
    print("✓ LLM Config loaded successfully")
    print(f"  - Provider: {config.provider}")
    print(f"  - Anthropic Model: {config.anthropic_model}")
    print(f"  - API Key present: {'YES' if config.anthropic_api_key else 'NO'}")
except Exception as e:
    print(f"✗ Error loading config: {e}")

print("=" * 60)
